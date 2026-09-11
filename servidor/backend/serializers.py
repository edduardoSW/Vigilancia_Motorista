"""Converte registros do banco nas respostas da API."""
import json
import logging
from datetime import datetime
from typing import Optional

from backend import config
from backend.alert_types import category_of, label_of
from backend.database import as_utc
from backend.identifiers import format_phone
from backend.schemas import (
    AlertOut, CompanyOut, ConsentOut, DeviceLiveStatus, DeviceOut, DriverOut, MeOut, Ref, UserOut, VehicleOut,
)

logger = logging.getLogger("drivesafe.api")


def ref(obj) -> Optional[Ref]:
    return Ref(id=obj.id, name=obj.name) if obj is not None else None


def vehicle_ref(vehicle) -> Optional[Ref]:
    return Ref(id=vehicle.id, name=vehicle.plate) if vehicle is not None else None


def is_online(device, now: datetime) -> bool:
    if device.revoked_at is not None or device.last_seen_at is None:
        return False
    return (now - as_utc(device.last_seen_at)).total_seconds() <= config.DEVICE_ONLINE_SECONDS


def live_of(device) -> Optional[DeviceLiveStatus]:
    if not device.live_status:
        return None
    try:
        return DeviceLiveStatus.model_validate_json(device.live_status)
    except ValueError as exc:
        logger.warning("Estado ao vivo inválido no dispositivo %s: %s", device.id, exc)
        return None


def device_out(device, now: datetime) -> DeviceOut:
    return DeviceOut(
        id=device.id,
        name=device.name,
        token_prefix=device.token_prefix,
        company=ref(device.company),
        vehicle=vehicle_ref(device.vehicle),
        driver=ref(device.driver),
        hostname=device.hostname,
        platform=device.platform,
        software_version=device.software_version,
        camera_ok=device.camera_ok,
        pending_events=device.pending_events or 0,
        last_seen_at=as_utc(device.last_seen_at),
        online=is_online(device, now),
        revoked=device.revoked_at is not None,
        created_at=as_utc(device.created_at),
        live=live_of(device),
        status_at=as_utc(device.status_at),
    )


def alert_out(alert) -> AlertOut:
    details = None
    if alert.details:
        try:
            details = json.loads(alert.details)
        except ValueError as exc:
            logger.warning("Alerta %s tem details inválido: %s", alert.id, exc)
    return AlertOut(
        id=alert.id,
        alert_type=alert.alert_type or "",
        label=label_of(alert.alert_type),
        category=category_of(alert.alert_type),
        risk_level=alert.risk_level or 0,
        duration=alert.duration or 0.0,
        details=details,
        timestamp=as_utc(alert.timestamp),
        received_at=as_utc(alert.received_at),
        company=ref(alert.company),
        driver=ref(alert.driver),
        vehicle=vehicle_ref(alert.vehicle),
        device=ref(alert.device),
        review_status=alert.review_status or "pendente",
        reviewed_by=alert.reviewed_by.name if alert.reviewed_by else None,
        reviewed_at=as_utc(alert.reviewed_at),
        review_note=alert.review_note,
    )


def me_out(user) -> MeOut:
    return MeOut(id=user.id, name=user.name, email=user.email, phone=format_phone(user.phone), role=user.role,
                 company=ref(user.company), driver_id=user.driver_id,
                 must_change_password=bool(user.must_change_password))


def user_out(user) -> UserOut:
    return UserOut(
        id=user.id, name=user.name, email=user.email, phone=format_phone(user.phone), role=user.role,
        company=ref(user.company),
        driver=ref(user.driver), active=bool(user.active), must_change_password=bool(user.must_change_password),
        created_at=as_utc(user.created_at), last_login_at=as_utc(user.last_login_at),
    )


def company_out(company, counts: dict) -> CompanyOut:
    totals = counts.get(company.id, {})
    return CompanyOut(
        id=company.id, name=company.name, document=company.document, contact_name=company.contact_name,
        contact_phone=format_phone(company.contact_phone), activation_policy=company.activation_policy,
        active=bool(company.active), created_at=as_utc(company.created_at), drivers=totals.get("drivers", 0),
        vehicles=totals.get("vehicles", 0), devices=totals.get("devices", 0), users=totals.get("users", 0),
    )


def vehicle_out(vehicle) -> VehicleOut:
    return VehicleOut(id=vehicle.id, plate=vehicle.plate, model=vehicle.model, type=vehicle.type,
                      company=ref(vehicle.company), created_at=as_utc(vehicle.created_at))


def consent_out(consent) -> ConsentOut:
    return ConsentOut(
        id=consent.id, kind=consent.kind, granted=bool(consent.granted), term_version=consent.term_version,
        channel=consent.channel, recorded_at=as_utc(consent.recorded_at),
        recorded_by=consent.recorded_by.name if consent.recorded_by else None, note=consent.note,
    )


def driver_out(driver, stats: Optional[dict], consents: dict, vehicle: Optional[Ref], has_login: bool) -> DriverOut:
    stats = stats or {}
    return DriverOut(
        id=driver.id, name=driver.name, license_number=driver.license_number, phone=driver.phone,
        company=ref(driver.company), created_at=as_utc(driver.created_at),
        alerts_7d=stats.get("alerts_7d", 0), alerts_30d=stats.get("alerts_30d", 0),
        worst_risk_7d=stats.get("worst_risk_7d", 0), categories_7d=dict(stats.get("categories_7d", {})),
        consents=consents, last_alert_at=stats.get("last_alert_at"), vehicle=vehicle, has_login=has_login,
    )
