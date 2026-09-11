"""Alertas: lista filtrada, revisão pelo gestor e exportação para Excel."""
import csv
import io
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from backend import config
from backend.alert_types import ALERT_TYPE_LABELS, CATEGORIES, category_of, label_of
from backend.auth import Principal, audit, current_principal, ensure_company_access, require_roles, scoped_company
from backend.database import TZ, REVIEW_STATUSES, Alert, as_utc, format_local, get_db, utcnow
from backend.live import hub
from backend.queries import alerts_query
from backend.schemas import AlertOut, AlertPage, ReviewIn
from backend.serializers import alert_out

router = APIRouter(tags=["alertas"])

CSV_LIMIT = 50000
REVIEW_LABELS = {"pendente": "Pendente", "confirmado": "Confirmado", "falso_alarme": "Alarme falso",
                 "orientado": "Motorista orientado", "arquivado": "Sem revisão"}


class AlertFilters:
    def __init__(self, company_id: Optional[int] = None,
                 start: Optional[date] = Query(None, description="Data inicial (AAAA-MM-DD), fuso local"),
                 end: Optional[date] = Query(None, description="Data final (AAAA-MM-DD), inclusiva"),
                 device_id: Optional[int] = None, vehicle_id: Optional[int] = None, driver_id: Optional[int] = None,
                 alert_type: Optional[str] = Query(None, max_length=50), category: Optional[str] = None,
                 review_status: Optional[str] = None):
        if category is not None and category not in CATEGORIES:
            raise HTTPException(status_code=400, detail="Categoria desconhecida.")
        if review_status is not None and review_status not in REVIEW_STATUSES:
            raise HTTPException(status_code=400, detail="Situação de revisão desconhecida.")
        self.values = dict(company_id=company_id, start=start, end=end, device_id=device_id, vehicle_id=vehicle_id,
                           driver_id=driver_id, alert_type=alert_type, category=category, review_status=review_status)

    def query(self, db: Session, principal: Principal):
        values = dict(self.values)
        if principal.role == "motorista":
            values["driver_id"] = principal.driver_id
        values["company_id"] = scoped_company(principal, values["company_id"])
        return alerts_query(db, **values)


@router.get("/api/alert-types")
def alert_types(principal: Principal = Depends(current_principal)):
    """Nomes em português e categoria de cada tipo de evento (o app usa no modo teste e nos filtros)."""
    return {"types": {alert_type: {"label": label, "category": category_of(alert_type)}
                      for alert_type, label in ALERT_TYPE_LABELS.items()},
            "categories": sorted(CATEGORIES)}


@router.get("/api/alerts", response_model=AlertPage)
def list_alerts(filters: AlertFilters = Depends(), skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=500),
                principal: Principal = Depends(current_principal), db: Session = Depends(get_db)):
    query = filters.query(db, principal)
    total = query.order_by(None).count()
    return AlertPage(items=[alert_out(alert) for alert in query.offset(skip).limit(limit).all()], total=total)


@router.patch("/api/alerts/{alert_id}/review", response_model=AlertOut)
def review_alert(alert_id: int, payload: ReviewIn, request: Request, background_tasks: BackgroundTasks,
                 principal: Principal = Depends(require_roles("admin", "gestor")), db: Session = Depends(get_db)):
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alerta não encontrado.")
    ensure_company_access(principal, alert.company_id)
    alert.review_status = payload.status
    alert.review_note = (payload.note or "").strip() or None
    alert.reviewed_by_user_id = None if payload.status == "pendente" else principal.user.id
    alert.reviewed_at = None if payload.status == "pendente" else utcnow()
    audit(db, principal, "alerta_revisado", target=f"alerta:{alert.id}", details={"situacao": payload.status},
          request=request, company_id=alert.company_id)
    db.commit()
    db.refresh(alert)
    out = alert_out(alert)
    background_tasks.add_task(hub.publish, {"type": "alert_review", "data": out}, company_id=alert.company_id,
                              driver_id=alert.driver_id)
    return out


def csv_cell(value) -> str:
    """Evita que o Excel interprete o conteúdo como fórmula."""
    text_value = "" if value is None else str(value)
    return "'" + text_value if text_value[:1] in ("=", "+", "-", "@", "\t", "\r") else text_value


@router.get("/api/alerts/export.csv")
def export_alerts_csv(request: Request, filters: AlertFilters = Depends(),
                      principal: Principal = Depends(require_roles("admin", "gestor")), db: Session = Depends(get_db)):
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow([
        "ID", f"Data e hora ({config.TIMEZONE})", "Data e hora (UTC)", "Tipo de alerta", "Nível de risco", "Duração (s)",
        "Empresa", "Motorista", "CNH", "Veículo (placa)", "Dispositivo", "Revisão", "Revisado por", "Nota da revisão",
        "Detalhes", "ID do evento",
    ])
    rows = 0
    for alert in filters.query(db, principal).limit(CSV_LIMIT):
        occurred = as_utc(alert.timestamp)
        writer.writerow([
            alert.id, format_local(occurred), occurred.strftime("%Y-%m-%d %H:%M:%S") if occurred else "",
            csv_cell(label_of(alert.alert_type)), alert.risk_level, f"{alert.duration or 0:.2f}".replace(".", ","),
            csv_cell(alert.company.name if alert.company else ""), csv_cell(alert.driver.name if alert.driver else ""),
            csv_cell(alert.driver.license_number if alert.driver else ""),
            csv_cell(alert.vehicle.plate if alert.vehicle else ""), csv_cell(alert.device.name if alert.device else ""),
            REVIEW_LABELS.get(alert.review_status or "pendente", alert.review_status),
            csv_cell(alert.reviewed_by.name if alert.reviewed_by else ""), csv_cell(alert.review_note or ""),
            csv_cell(alert.details or ""), alert.event_uid or "",
        ])
        rows += 1
    audit(db, principal, "alertas_exportados", details={"linhas": rows, **{k: str(v) for k, v in filters.values.items() if v is not None}},
          request=request)
    db.commit()
    filename = f"drivesafe-alertas-{datetime.now(TZ):%Y%m%d-%H%M}.csv"
    return Response(
        content=b"\xef\xbb\xbf" + buffer.getvalue().encode("utf-8"),  # BOM: o Excel abre os acentos corretamente
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
