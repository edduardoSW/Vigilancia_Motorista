"""Consultas usadas por várias rotas: alertas filtrados, estatísticas de motoristas, consentimentos e horas do dia."""
from collections import defaultdict
from datetime import date, datetime, time as dt_time, timedelta, timezone
from typing import Optional

from sqlalchemy import desc, func
from sqlalchemy.orm import Session, joinedload

from backend.alert_types import category_of, types_in
from backend.database import TZ, Alert, Consent, Device, Driver, User, Vehicle, as_utc, utcnow
from backend.schemas import Ref, TrendDay

SYSTEM_TYPES = sorted(types_in("sistema"))


def local_day_start_utc(day: date) -> datetime:
    return TZ.localize(datetime.combine(day, dt_time.min)).astimezone(timezone.utc)


def today_local() -> date:
    return datetime.now(TZ).date()


def alerts_query(db: Session, company_id: Optional[int] = None, driver_id: Optional[int] = None,
                 device_id: Optional[int] = None, vehicle_id: Optional[int] = None, start: Optional[date] = None,
                 end: Optional[date] = None, alert_type: Optional[str] = None, category: Optional[str] = None,
                 review_status: Optional[str] = None, include_system: bool = True):
    query = db.query(Alert).options(
        joinedload(Alert.driver), joinedload(Alert.vehicle), joinedload(Alert.device),
        joinedload(Alert.company), joinedload(Alert.reviewed_by),
    )
    if company_id is not None:
        query = query.filter(Alert.company_id == company_id)
    if start is not None:
        query = query.filter(Alert.timestamp >= local_day_start_utc(start))
    if end is not None:
        query = query.filter(Alert.timestamp < local_day_start_utc(end + timedelta(days=1)))
    for value, column in ((driver_id, Alert.driver_id), (device_id, Alert.device_id), (vehicle_id, Alert.vehicle_id),
                          (alert_type, Alert.alert_type), (review_status, Alert.review_status)):
        if value is not None:
            query = query.filter(column == value)
    if category:
        query = query.filter(Alert.alert_type.in_(sorted(types_in(category))))
    if not include_system:
        query = query.filter(Alert.alert_type.notin_(SYSTEM_TYPES))
    return query.order_by(desc(Alert.timestamp), desc(Alert.id))


def driver_stats(db: Session, driver_ids: list) -> dict:
    """Alertas de 7 e 30 dias, pior risco e categorias por motorista. Avisos de sistema não contam."""
    if not driver_ids:
        return {}
    now = utcnow()
    week = now - timedelta(days=7)
    rows = (db.query(Alert.driver_id, Alert.alert_type, Alert.risk_level, Alert.timestamp)
            .filter(Alert.driver_id.in_(driver_ids), Alert.timestamp >= now - timedelta(days=30)).all())
    stats = defaultdict(lambda: {"alerts_7d": 0, "alerts_30d": 0, "worst_risk_7d": 0,
                                 "categories_7d": defaultdict(int), "last_alert_at": None})
    for driver_id, alert_type, risk, timestamp in rows:
        category = category_of(alert_type)
        if category == "sistema":
            continue
        timestamp = as_utc(timestamp)
        item = stats[driver_id]
        item["alerts_30d"] += 1
        if timestamp >= week:
            item["alerts_7d"] += 1
            item["worst_risk_7d"] = max(item["worst_risk_7d"], risk or 0)
            item["categories_7d"][category] += 1
        if item["last_alert_at"] is None or timestamp > item["last_alert_at"]:
            item["last_alert_at"] = timestamp
    return stats


def latest_consents(db: Session, driver_ids: list) -> dict:
    """{motorista: {tipo: concedido}} com o registro mais recente de cada tipo."""
    if not driver_ids:
        return {}
    result = defaultdict(dict)
    rows = db.query(Consent).filter(Consent.driver_id.in_(driver_ids)).order_by(Consent.recorded_at, Consent.id)
    for consent in rows:
        result[consent.driver_id][consent.kind] = bool(consent.granted)
    return result


def current_vehicles(db: Session, driver_ids: list) -> dict:
    if not driver_ids:
        return {}
    result = {}
    devices = (db.query(Device).options(joinedload(Device.vehicle))
               .filter(Device.driver_id.in_(driver_ids), Device.revoked_at.is_(None), Device.vehicle_id.isnot(None)))
    for device in devices:
        result[device.driver_id] = Ref(id=device.vehicle.id, name=device.vehicle.plate)
    return result


def drivers_with_login(db: Session, driver_ids: list) -> set:
    if not driver_ids:
        return set()
    return {driver_id for (driver_id,) in db.query(User.driver_id).filter(User.driver_id.in_(driver_ids))}


def risk_by_hour(rows) -> list:
    """Pior nível de risco por hora local. rows: (tipo, risco, horário)."""
    hours = [0] * 24
    for alert_type, risk, timestamp in rows:
        if category_of(alert_type) == "sistema" or timestamp is None:
            continue
        hour = as_utc(timestamp).astimezone(TZ).hour
        hours[hour] = max(hours[hour], risk or 0)
    return hours


def trend(db: Session, driver_id: int, days: int = 30) -> list:
    first = today_local() - timedelta(days=days - 1)
    buckets = {first + timedelta(days=i): TrendDay(day=first + timedelta(days=i)) for i in range(days)}
    rows = (db.query(Alert.alert_type, Alert.risk_level, Alert.timestamp)
            .filter(Alert.driver_id == driver_id, Alert.timestamp >= local_day_start_utc(first)).all())
    for alert_type, risk, timestamp in rows:
        category = category_of(alert_type)
        bucket = buckets.get(as_utc(timestamp).astimezone(TZ).date())
        if category == "sistema" or bucket is None:
            continue
        if category == "sonolencia":
            bucket.drowsiness += 1
        elif category == "celular":
            bucket.phone += 1
        else:
            bucket.other += 1
        bucket.worst_risk = max(bucket.worst_risk, risk or 0)
    return list(buckets.values())


def company_counts(db: Session, company_ids: list) -> dict:
    counts = defaultdict(dict)
    if not company_ids:
        return counts
    for key, model in (("drivers", Driver), ("vehicles", Vehicle), ("devices", Device), ("users", User)):
        query = db.query(model.company_id, func.count(model.id)).filter(model.company_id.in_(company_ids))
        if model is Device:
            query = query.filter(Device.revoked_at.is_(None))
        for company_id, total in query.group_by(model.company_id):
            counts[company_id][key] = total
    return counts
