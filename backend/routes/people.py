"""Motoristas, consentimentos (LGPD) e veículos."""
import json
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import desc, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from backend.auth import (
    Principal, audit, current_principal, ensure_company_access, ensure_driver_access, require_roles, scoped_company,
)
from backend.database import CONSENT_TERM_VERSION, Company, Consent, Device, Driver, Vehicle, get_db, utcnow
from backend.queries import (
    alerts_query, current_vehicles, driver_stats, drivers_with_login, latest_consents, risk_by_hour, today_local, trend,
)
from backend.schemas import (
    ConsentIn, ConsentOut, DriverDayOut, DriverDetailOut, DriverIn, DriverOut, DriverPatch, Ref, VehicleIn, VehicleOut,
    VehiclePatch,
)
from backend.serializers import alert_out, consent_out, driver_out, vehicle_out

router = APIRouter(tags=["motoristas e veículos"])

CHANNELS_BY_ROLE = {"motorista": {"app_motorista"}, "gestor": {"termo_assinado"}, "admin": {"termo_assinado", "admin"}}


def company_for_new_record(principal: Principal, requested: Optional[int], db: Session) -> int:
    company_id = requested if principal.is_admin else principal.company_id
    if company_id is None or db.get(Company, company_id) is None:
        raise HTTPException(status_code=400, detail="Escolha a empresa.")
    return company_id


def driver_list(db: Session, drivers: list) -> List[DriverOut]:
    ids = [driver.id for driver in drivers]
    stats = driver_stats(db, ids)
    consents = latest_consents(db, ids)
    vehicles = current_vehicles(db, ids)
    logins = drivers_with_login(db, ids)
    return [driver_out(driver, stats.get(driver.id), consents.get(driver.id, {}), vehicles.get(driver.id),
                       driver.id in logins) for driver in drivers]


# ---------- motoristas ----------

@router.get("/api/drivers", response_model=List[DriverOut])
def list_drivers(company_id: Optional[int] = None, search: Optional[str] = Query(None, max_length=60),
                 principal: Principal = Depends(current_principal), db: Session = Depends(get_db)):
    query = db.query(Driver).options(joinedload(Driver.company)).order_by(Driver.name)
    if principal.role == "motorista":
        query = query.filter(Driver.id == principal.driver_id)
    else:
        scope = scoped_company(principal, company_id)
        if scope is not None:
            query = query.filter(Driver.company_id == scope)
    if search and search.strip():
        like = f"%{search.strip()}%"
        query = query.filter(or_(Driver.name.ilike(like), Driver.license_number.ilike(like)))
    return driver_list(db, query.limit(2000).all())


@router.post("/api/drivers", response_model=DriverOut, status_code=201)
def create_driver(payload: DriverIn, request: Request, principal: Principal = Depends(require_roles("admin", "gestor")),
                  db: Session = Depends(get_db)):
    company_id = company_for_new_record(principal, payload.company_id, db)
    driver = Driver(company_id=company_id, name=payload.name.strip(),
                    license_number=payload.license_number.strip().upper(), phone=(payload.phone or "").strip() or None)
    db.add(driver)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Já existe um motorista cadastrado com esta CNH.")
    audit(db, principal, "motorista_criado", target=f"motorista:{driver.id}", request=request, company_id=company_id)
    db.commit()
    db.refresh(driver)
    return driver_list(db, [driver])[0]


@router.get("/api/drivers/{driver_id}", response_model=DriverDetailOut)
def get_driver(driver_id: int, principal: Principal = Depends(current_principal), db: Session = Depends(get_db)):
    driver = db.get(Driver, driver_id)
    ensure_driver_access(principal, driver)
    base = driver_list(db, [driver])[0]
    history = (db.query(Consent).options(joinedload(Consent.recorded_by)).filter(Consent.driver_id == driver.id)
               .order_by(desc(Consent.recorded_at), desc(Consent.id)).all())
    devices = db.query(Device).filter(Device.driver_id == driver.id, Device.revoked_at.is_(None)).all()
    return DriverDetailOut(**base.model_dump(), trend=trend(db, driver.id, 30),
                           consent_history=[consent_out(consent) for consent in history],
                           devices=[Ref(id=device.id, name=device.name) for device in devices])


@router.patch("/api/drivers/{driver_id}", response_model=DriverOut)
def update_driver(driver_id: int, payload: DriverPatch, request: Request,
                  principal: Principal = Depends(require_roles("admin", "gestor")), db: Session = Depends(get_db)):
    driver = db.get(Driver, driver_id)
    ensure_driver_access(principal, driver)
    changes = payload.model_dump(exclude_unset=True)
    if "name" in changes and changes["name"]:
        driver.name = changes["name"].strip()
    if "license_number" in changes and changes["license_number"]:
        driver.license_number = changes["license_number"].strip().upper()
    if "phone" in changes:
        driver.phone = (changes["phone"] or "").strip() or None
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Já existe um motorista cadastrado com esta CNH.")
    audit(db, principal, "motorista_alterado", target=f"motorista:{driver.id}", request=request,
          company_id=driver.company_id)
    db.commit()
    db.refresh(driver)
    return driver_list(db, [driver])[0]


@router.get("/api/drivers/{driver_id}/day", response_model=DriverDayOut)
def driver_day(driver_id: int, day: Optional[date] = Query(None, description="AAAA-MM-DD no fuso local"),
               principal: Principal = Depends(current_principal), db: Session = Depends(get_db)):
    driver = db.get(Driver, driver_id)
    ensure_driver_access(principal, driver)
    day = day or today_local()
    alerts = alerts_query(db, driver_id=driver.id, start=day, end=day).all()
    hours = risk_by_hour((alert.alert_type, alert.risk_level, alert.timestamp) for alert in alerts)
    return DriverDayOut(day=day, hours=hours, alerts=[alert_out(alert) for alert in alerts])


@router.post("/api/drivers/{driver_id}/consents", response_model=ConsentOut, status_code=201)
def record_consent(driver_id: int, payload: ConsentIn, request: Request,
                   principal: Principal = Depends(current_principal), db: Session = Depends(get_db)):
    driver = db.get(Driver, driver_id)
    ensure_driver_access(principal, driver)
    if payload.channel not in CHANNELS_BY_ROLE[principal.role]:
        raise HTTPException(status_code=400, detail="Este canal de registro não vale para o seu perfil.")
    consent = Consent(driver_id=driver.id, kind=payload.kind, granted=payload.granted,
                      term_version=CONSENT_TERM_VERSION, channel=payload.channel,
                      recorded_by_user_id=principal.user.id, note=(payload.note or "").strip() or None)
    db.add(consent)
    audit(db, principal, "consentimento_registrado", target=f"motorista:{driver.id}",
          details={"tipo": payload.kind, "concedido": payload.granted, "canal": payload.channel}, request=request,
          company_id=driver.company_id)
    db.commit()
    db.refresh(consent)
    return consent_out(consent)


@router.get("/api/drivers/{driver_id}/export")
def export_driver_data(driver_id: int, request: Request, principal: Principal = Depends(current_principal),
                       db: Session = Depends(get_db)):
    """Todos os dados do motorista num arquivo (LGPD, art. 18: acesso e portabilidade)."""
    driver = db.get(Driver, driver_id)
    ensure_driver_access(principal, driver)
    consents = db.query(Consent).filter(Consent.driver_id == driver.id).order_by(Consent.recorded_at).all()
    payload = {
        "gerado_em": utcnow().isoformat(timespec="seconds"),
        "motorista": {"id": driver.id, "nome": driver.name, "cnh": driver.license_number, "telefone": driver.phone,
                      "empresa": driver.company.name if driver.company else None},
        "consentimentos": [consent_out(consent).model_dump(mode="json") for consent in consents],
        "alertas": [alert_out(alert).model_dump(mode="json") for alert in alerts_query(db, driver_id=driver.id).all()],
        "observacao": "O DriveSafe não grava nem envia imagens: só métricas e eventos.",
    }
    audit(db, principal, "dados_exportados", target=f"motorista:{driver.id}", request=request,
          company_id=driver.company_id)
    db.commit()
    return Response(
        json.dumps(payload, ensure_ascii=False, indent=2), media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="drivesafe-dados-motorista-{driver.id}.json"'},
    )


# ---------- veículos ----------

@router.get("/api/vehicles", response_model=List[VehicleOut])
def list_vehicles(company_id: Optional[int] = None, principal: Principal = Depends(require_roles("admin", "gestor")),
                  db: Session = Depends(get_db)):
    scope = scoped_company(principal, company_id)
    query = db.query(Vehicle).options(joinedload(Vehicle.company)).order_by(Vehicle.plate)
    if scope is not None:
        query = query.filter(Vehicle.company_id == scope)
    return [vehicle_out(vehicle) for vehicle in query.all()]


@router.post("/api/vehicles", response_model=VehicleOut, status_code=201)
def create_vehicle(payload: VehicleIn, request: Request,
                   principal: Principal = Depends(require_roles("admin", "gestor")), db: Session = Depends(get_db)):
    company_id = company_for_new_record(principal, payload.company_id, db)
    vehicle = Vehicle(company_id=company_id, plate=payload.plate.strip().upper(), model=payload.model.strip(),
                      type=payload.type.strip())
    db.add(vehicle)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Já existe um veículo com esta placa.")
    audit(db, principal, "veiculo_criado", target=vehicle.plate, request=request, company_id=company_id)
    db.commit()
    db.refresh(vehicle)
    return vehicle_out(vehicle)


@router.patch("/api/vehicles/{vehicle_id}", response_model=VehicleOut)
def update_vehicle(vehicle_id: int, payload: VehiclePatch, request: Request,
                   principal: Principal = Depends(require_roles("admin", "gestor")), db: Session = Depends(get_db)):
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=404, detail="Veículo não encontrado.")
    ensure_company_access(principal, vehicle.company_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        if value:
            setattr(vehicle, field, value.strip().upper() if field == "plate" else value.strip())
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Já existe um veículo com esta placa.")
    audit(db, principal, "veiculo_alterado", target=vehicle.plate, request=request, company_id=vehicle.company_id)
    db.commit()
    db.refresh(vehicle)
    return vehicle_out(vehicle)
