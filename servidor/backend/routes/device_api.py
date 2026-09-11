"""Rotas usadas pelos dispositivos (token Bearer): sinal de "estou vivo" e envio de eventos."""
import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend import config
from backend.alert_types import needs_review
from backend.database import Alert, Device, as_utc, get_db, utcnow
from backend.live import hub
from backend.queries import latest_consents
from backend.schemas import DeviceInfo, DevicePolicy, EventBatchIn, EventBatchOut, EventIn, HeartbeatIn, HeartbeatOut
from backend.security import hash_token, token_matches
from backend.serializers import alert_out, device_out

logger = logging.getLogger("drivesafe.api")
router = APIRouter(tags=["dispositivo"])
bearer_scheme = HTTPBearer(auto_error=False)

MAX_DETAILS_BYTES = 8000
MAX_PUBLISHED_ALERTS = 20


def authenticated_device(credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
                         db: Session = Depends(get_db)) -> Device:
    unauthorized = HTTPException(status_code=401, detail="Token do dispositivo ausente, inválido ou revogado",
                                 headers={"WWW-Authenticate": "Bearer"})
    if credentials is None:
        raise unauthorized
    device = db.query(Device).filter(Device.token_hash == hash_token(credentials.credentials)).first()
    if device is None or device.revoked_at is not None or not token_matches(credentials.credentials, device.token_hash):
        raise unauthorized
    return device


def touch_device(device: Device, info: DeviceInfo, request: Request) -> None:
    for field in ("hostname", "platform", "software_version", "pending_events"):
        value = getattr(info, field)
        if value is not None:
            setattr(device, field, value)
    device.last_seen_at = utcnow()
    if request.client:
        device.last_ip = request.client.host


def device_policy(db: Session, device: Device) -> DevicePolicy:
    """Modo dos sinais de ativação = política da empresa; "enviar" só vale com consentimento do motorista."""
    mode = device.company.activation_policy if device.company else "local"
    consents = latest_consents(db, [device.driver_id]).get(device.driver_id, {}) if device.driver_id else {}
    if mode == "enviar" and not consents.get("sinais_ativacao_envio"):
        mode = "local"
    return DevicePolicy(driver_id=device.driver_id, profile_consent=bool(consents.get("perfil_entre_viagens")),
                        activation_mode=mode, status_interval_s=config.DEVICE_STATUS_INTERVAL_S)


def resolve_occurred_at(event: EventIn, received_at: datetime) -> datetime:
    if event.age_seconds is not None:
        return received_at - timedelta(seconds=event.age_seconds)
    occurred = as_utc(event.occurred_at)
    if occurred > received_at + timedelta(minutes=5) or occurred < received_at - timedelta(days=365):
        # Raspberry Pi sem relógio de bateria pode ligar com a data errada.
        logger.warning("Relógio do dispositivo fora do esperado (%s); usando o horário de recebimento", occurred.isoformat())
        return received_at
    return occurred


def encode_details(event: EventIn) -> Optional[str]:
    if not event.details:
        return None
    encoded = json.dumps(event.details, ensure_ascii=False)
    if len(encoded.encode("utf-8")) > MAX_DETAILS_BYTES:
        logger.warning("details do evento %s passou de %d bytes e foi descartado", event.event_uid, MAX_DETAILS_BYTES)
        return None
    return encoded


@router.post("/api/devices/heartbeat", response_model=HeartbeatOut)
def device_heartbeat(payload: HeartbeatIn, request: Request, background_tasks: BackgroundTasks,
                     device: Device = Depends(authenticated_device), db: Session = Depends(get_db)):
    touch_device(device, payload.device, request)
    device.camera_ok = payload.camera_ok
    policy = device_policy(db, device)
    if payload.status is not None:
        status = payload.status.model_dump(exclude_none=True)
        if policy.activation_mode != "enviar":
            # Sinais de ativação não ficam no servidor sem política da empresa e consentimento do motorista.
            status.pop("activation_index", None)
            status.pop("activation_confidence", None)
        device.live_status = json.dumps(status, ensure_ascii=False)
        device.risk_level = status.get("risk_level")
        device.status_at = utcnow()
        device.fps = status.get("fps")
        device.latency_p95_ms = status.get("latency_p95_ms")
    db.commit()
    db.refresh(device)
    out = device_out(device, utcnow())
    background_tasks.add_task(hub.publish, {"type": "device", "data": out}, company_id=device.company_id,
                              driver_id=device.driver_id)
    return HeartbeatOut(**out.model_dump(), policy=policy)


@router.post("/api/events", response_model=EventBatchOut)
def ingest_events(payload: EventBatchIn, request: Request, background_tasks: BackgroundTasks,
                  device: Device = Depends(authenticated_device), db: Session = Depends(get_db)):
    touch_device(device, payload.device, request)
    received_at = utcnow()
    uids = [str(event.event_uid) for event in payload.events]
    seen = {uid for (uid,) in db.query(Alert.event_uid).filter(Alert.event_uid.in_(uids))}

    new_alerts = []
    for event, uid in zip(payload.events, uids):
        if uid in seen:
            continue
        seen.add(uid)
        alert = Alert(
            event_uid=uid, company_id=device.company_id, device_id=device.id, driver_id=device.driver_id,
            vehicle_id=device.vehicle_id, alert_type=event.alert_type, risk_level=event.risk_level,
            duration=event.duration, details=encode_details(event),
            timestamp=resolve_occurred_at(event, received_at), received_at=received_at,
            review_status="pendente" if needs_review(event.alert_type, event.risk_level) else "arquivado",
        )
        db.add(alert)
        new_alerts.append(alert)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Evento registrado em paralelo por outra requisição; reenvie o lote")

    if new_alerts:
        newest = sorted(new_alerts, key=lambda alert: as_utc(alert.timestamp))[-MAX_PUBLISHED_ALERTS:]
        for alert in newest:
            db.refresh(alert)
            background_tasks.add_task(hub.publish, {"type": "alert", "data": alert_out(alert)},
                                      company_id=alert.company_id, driver_id=alert.driver_id)
        logger.info("Dispositivo #%s enviou %d alerta(s) novo(s)", device.id, len(new_alerts))

    return EventBatchOut(accepted=len(new_alerts), duplicates=len(payload.events) - len(new_alerts))
