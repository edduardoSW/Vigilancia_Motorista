"""Visão geral, frota ao vivo e cadastro de dispositivos."""
from collections import defaultdict
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session, joinedload

from backend.alert_types import category_of
from backend.auth import Principal, audit, ensure_company_access, require_roles, scoped_company
from backend.database import Alert, Company, Device, Driver, Vehicle, get_db, utcnow
from backend.queries import (
    SYSTEM_TYPES, alerts_query, driver_stats, local_day_start_utc, risk_by_hour, today_local,
)
from backend.schemas import (
    DeviceCreatedOut, DeviceIn, DeviceOut, DevicePatch, DriverAttention, FleetItem, OverviewOut, Ref, RiskCount,
)
from backend.security import generate_device_token
from backend.serializers import alert_out, device_out, is_online

router = APIRouter(tags=["frota e dispositivos"])
manager_roles = require_roles("admin", "gestor")


def devices_query(db: Session, company_id: Optional[int]):
    query = db.query(Device).options(joinedload(Device.company), joinedload(Device.vehicle), joinedload(Device.driver))
    if company_id is not None:
        query = query.filter(Device.company_id == company_id)
    return query


@router.get("/api/overview", response_model=OverviewOut)
def overview(company_id: Optional[int] = None, principal: Principal = Depends(manager_roles),
             db: Session = Depends(get_db)):
    scope = scoped_company(principal, company_id)
    now = utcnow()
    devices = devices_query(db, scope).filter(Device.revoked_at.is_(None)).all()
    counts = RiskCount()
    for device in devices:
        if not is_online(device, now) or device.risk_level is None:
            counts.no_signal += 1
        else:
            field = ("normal", "attention", "high", "critical")[max(0, min(device.risk_level, 3))]
            setattr(counts, field, getattr(counts, field) + 1)

    alerts = db.query(Alert)
    if scope is not None:
        alerts = alerts.filter(Alert.company_id == scope)
    start = local_day_start_utc(today_local())
    today = alerts.filter(Alert.timestamp >= start, Alert.alert_type.notin_(SYSTEM_TYPES))

    drivers = db.query(Driver)
    if scope is not None:
        drivers = drivers.filter(Driver.company_id == scope)
    drivers = drivers.all()
    stats = driver_stats(db, [driver.id for driver in drivers])
    ranked = sorted(
        ((driver, stats[driver.id]) for driver in drivers if driver.id in stats and stats[driver.id]["alerts_7d"]),
        key=lambda item: (item[1]["worst_risk_7d"], item[1]["alerts_7d"]), reverse=True,
    )[:5]
    attention = [
        DriverAttention(driver=Ref(id=driver.id, name=driver.name), alerts_7d=item["alerts_7d"],
                        worst_risk=item["worst_risk_7d"],
                        top_category=max(item["categories_7d"], key=item["categories_7d"].get) if item["categories_7d"] else None)
        for driver, item in ranked
    ]
    return OverviewOut(
        now=counts,
        devices_online=sum(1 for device in devices if is_online(device, now)),
        devices_total=len(devices),
        alerts_today=today.count(),
        critical_today=today.filter(Alert.risk_level >= 3).count(),
        to_review=alerts.filter(Alert.review_status == "pendente").count(),
        drivers_attention=attention,
        latest_alerts=[alert_out(alert) for alert in alerts_query(db, company_id=scope, include_system=False).limit(8)],
    )


@router.get("/api/fleet", response_model=List[FleetItem])
def fleet(company_id: Optional[int] = None, principal: Principal = Depends(manager_roles),
          db: Session = Depends(get_db)):
    scope = scoped_company(principal, company_id)
    now = utcnow()
    devices = devices_query(db, scope).filter(Device.revoked_at.is_(None)).all()
    ids = [device.id for device in devices]
    rows = defaultdict(list)
    if ids:
        start = local_day_start_utc(today_local())
        for device_id, alert_type, risk, timestamp in (
                db.query(Alert.device_id, Alert.alert_type, Alert.risk_level, Alert.timestamp)
                .filter(Alert.device_id.in_(ids), Alert.timestamp >= start)):
            rows[device_id].append((alert_type, risk, timestamp))
    items = [
        FleetItem(device=device_out(device, now),
                  alerts_today=sum(1 for alert_type, _, _ in rows[device.id] if category_of(alert_type) != "sistema"),
                  risk_hours_today=risk_by_hour(rows[device.id]))
        for device in devices
    ]
    items.sort(key=lambda item: (not item.device.online, -(item.device.live.risk_level or 0) if item.device.live else 0,
                                 item.device.name.lower()))
    return items


# ---------- dispositivos ----------

def link_targets(db: Session, company_id: int, vehicle_id: Optional[int], driver_id: Optional[int]):
    def pick(model, value, label):
        if not value:
            return None
        record = db.get(model, value)
        if record is None or record.company_id != company_id:
            raise HTTPException(status_code=400, detail=f"{label} não pertence a esta empresa.")
        return record.id

    return pick(Vehicle, vehicle_id, "Veículo"), pick(Driver, driver_id, "Motorista")


@router.get("/api/devices", response_model=List[DeviceOut])
def list_devices(company_id: Optional[int] = None, principal: Principal = Depends(manager_roles),
                 db: Session = Depends(get_db)):
    scope = scoped_company(principal, company_id)
    now = utcnow()
    return [device_out(device, now) for device in devices_query(db, scope).order_by(Device.name).all()]


@router.post("/api/devices", response_model=DeviceCreatedOut, status_code=201)
def create_device(payload: DeviceIn, request: Request, principal: Principal = Depends(require_roles("admin")),
                  db: Session = Depends(get_db)):
    company = db.get(Company, payload.company_id)
    if company is None:
        raise HTTPException(status_code=400, detail="Escolha a empresa do dispositivo.")
    vehicle_id, driver_id = link_targets(db, company.id, payload.vehicle_id, payload.driver_id)
    token, token_hash, prefix = generate_device_token()
    device = Device(company_id=company.id, name=payload.name.strip(), token_hash=token_hash, token_prefix=prefix,
                    vehicle_id=vehicle_id, driver_id=driver_id)
    db.add(device)
    db.flush()
    audit(db, principal, "dispositivo_criado", target=f"dispositivo:{device.id}", request=request,
          company_id=company.id)
    db.commit()
    db.refresh(device)
    return DeviceCreatedOut(device=device_out(device, utcnow()), token=token)


def device_or_404(db: Session, principal: Principal, device_id: int) -> Device:
    device = db.get(Device, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Dispositivo não encontrado.")
    ensure_company_access(principal, device.company_id)
    return device


@router.patch("/api/devices/{device_id}", response_model=DeviceOut)
def update_device(device_id: int, payload: DevicePatch, request: Request, principal: Principal = Depends(manager_roles),
                  db: Session = Depends(get_db)):
    device = device_or_404(db, principal, device_id)
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("name"):
        device.name = changes["name"].strip()
    if "vehicle_id" in changes or "driver_id" in changes:
        device.vehicle_id, device.driver_id = link_targets(
            db, device.company_id, changes.get("vehicle_id", device.vehicle_id), changes.get("driver_id", device.driver_id))
    audit(db, principal, "dispositivo_alterado", target=f"dispositivo:{device.id}", details=changes, request=request,
          company_id=device.company_id)
    db.commit()
    db.refresh(device)
    return device_out(device, utcnow())


@router.post("/api/devices/{device_id}/token", response_model=DeviceCreatedOut)
def new_device_token(device_id: int, request: Request, principal: Principal = Depends(require_roles("admin")),
                     db: Session = Depends(get_db)):
    device = device_or_404(db, principal, device_id)
    token, token_hash, prefix = generate_device_token()
    device.token_hash, device.token_prefix, device.revoked_at = token_hash, prefix, None
    audit(db, principal, "dispositivo_novo_token", target=f"dispositivo:{device.id}", request=request,
          company_id=device.company_id)
    db.commit()
    db.refresh(device)
    return DeviceCreatedOut(device=device_out(device, utcnow()), token=token)


@router.post("/api/devices/{device_id}/revoke", response_model=DeviceOut)
def revoke_device(device_id: int, request: Request, principal: Principal = Depends(require_roles("admin")),
                  db: Session = Depends(get_db)):
    device = device_or_404(db, principal, device_id)
    device.revoked_at = device.revoked_at or utcnow()
    audit(db, principal, "dispositivo_revogado", target=f"dispositivo:{device.id}", request=request,
          company_id=device.company_id)
    db.commit()
    db.refresh(device)
    return device_out(device, utcnow())
