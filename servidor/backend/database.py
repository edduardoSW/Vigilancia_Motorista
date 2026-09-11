"""Banco do servidor central: empresas, usuários, motoristas, veículos, dispositivos, alertas e consentimentos.

Tudo em UTC. SQLite em modo WAL por padrão, ou Postgres via DATABASE_URL.
"""
import logging
import os
from datetime import datetime, timezone

import pytz
from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text,
    bindparam, create_engine, event, inspect, select, text, update,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from backend import config

logger = logging.getLogger("drivesafe.database")

TZ = pytz.timezone(config.TIMEZONE)

ROLES = ("admin", "gestor", "motorista")
ACTIVATION_POLICIES = ("desligado", "local", "enviar")
REVIEW_STATUSES = ("pendente", "confirmado", "falso_alarme", "orientado", "arquivado")
CONSENT_KINDS = ("monitoramento", "perfil_entre_viagens", "sinais_ativacao_envio")
CONSENT_CHANNELS = ("app_motorista", "termo_assinado", "admin")
CONSENT_TERM_VERSION = "2026-09"


def utcnow():
    return datetime.now(timezone.utc)


def as_utc(value):
    """O banco guarda UTC. SQLite devolve datetime sem fuso; Postgres devolve com fuso."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def format_local(value):
    value = as_utc(value)
    return value.astimezone(TZ).strftime("%d/%m/%Y %H:%M:%S") if value else None


_is_sqlite = config.DATABASE_URL.startswith("sqlite")
engine = create_engine(
    config.DATABASE_URL,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
)

if _is_sqlite:
    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_connection, _record):
        # WAL + busy_timeout: vários dispositivos gravando ao mesmo tempo sem "database is locked".
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class Company(Base):
    """Transportadora cliente. Cada gestor e motorista só enxerga os dados da própria empresa."""

    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    document = Column(String(20))
    # Responsável na transportadora. O contato com o cliente é pelo celular (só dígitos, com código do país).
    contact_name = Column(String(120))
    contact_phone = Column(String(20))
    # Sinais de ativação atípica: desligado, local (só no dispositivo) ou enviar (exige consentimento do motorista).
    activation_policy = Column(String(12), nullable=False, default="local")
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    drivers = relationship("Driver", back_populates="company")
    vehicles = relationship("Vehicle", back_populates="company")
    devices = relationship("Device", back_populates="company")
    users = relationship("User", back_populates="company")


class Driver(Base):
    __tablename__ = "drivers"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True)
    name = Column(String, index=True)
    license_number = Column(String, unique=True, index=True)
    phone = Column(String)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    company = relationship("Company", back_populates="drivers")
    alerts = relationship("Alert", back_populates="driver")
    devices = relationship("Device", back_populates="driver")
    vehicles = relationship("Vehicle", secondary="driver_vehicles", back_populates="drivers")
    consents = relationship("Consent", back_populates="driver", order_by="Consent.recorded_at")


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True)
    plate = Column(String, unique=True, index=True)
    model = Column(String)
    type = Column(String)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    company = relationship("Company", back_populates="vehicles")
    alerts = relationship("Alert", back_populates="vehicle")
    devices = relationship("Device", back_populates="vehicle")
    drivers = relationship("Driver", secondary="driver_vehicles", back_populates="vehicles")


class DriverVehicle(Base):
    __tablename__ = "driver_vehicles"

    driver_id = Column(Integer, ForeignKey("drivers.id"), primary_key=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), primary_key=True)


class Device(Base):
    """Equipamento de monitoramento (ex.: Raspberry Pi instalado em um veículo)."""

    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True)
    name = Column(String(100), nullable=False)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    token_prefix = Column(String(16), nullable=False)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"))
    driver_id = Column(Integer, ForeignKey("drivers.id"))
    hostname = Column(String(255))
    platform = Column(String(255))
    software_version = Column(String(32))
    camera_ok = Column(Boolean)
    pending_events = Column(Integer, nullable=False, default=0)
    last_seen_at = Column(DateTime(timezone=True))
    last_ip = Column(String(45))
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    revoked_at = Column(DateTime(timezone=True))
    # Estado ao vivo mandado no sinal de "estou vivo": nível de risco, calibração, celular, desempenho.
    live_status = Column(Text)
    risk_level = Column(Integer)
    status_at = Column(DateTime(timezone=True))
    fps = Column(Float)
    latency_p95_ms = Column(Float)

    company = relationship("Company", back_populates="devices")
    vehicle = relationship("Vehicle", back_populates="devices")
    driver = relationship("Driver", back_populates="devices")
    alerts = relationship("Alert", back_populates="device")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True)
    driver_id = Column(Integer, ForeignKey("drivers.id"))
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"))
    device_id = Column(Integer, ForeignKey("devices.id"), index=True)
    # Gerado pelo dispositivo: reenviar o mesmo evento não duplica o registro.
    event_uid = Column(String(36), unique=True, index=True)
    alert_type = Column(String, index=True)
    risk_level = Column(Integer)
    duration = Column(Float)
    # Métricas do detector no momento do evento, em JSON.
    details = Column(Text)
    # Momento em que o evento aconteceu no veículo (UTC).
    timestamp = Column(DateTime(timezone=True), default=utcnow, index=True)
    received_at = Column(DateTime(timezone=True), default=utcnow)
    # Revisão pelo gestor: confirma, marca alarme falso ou registra a orientação dada ao motorista.
    review_status = Column(String(16), default="pendente", index=True)
    reviewed_by_user_id = Column(Integer, ForeignKey("users.id"))
    reviewed_at = Column(DateTime(timezone=True))
    review_note = Column(Text)

    company = relationship("Company")
    driver = relationship("Driver", back_populates="alerts")
    vehicle = relationship("Vehicle", back_populates="alerts")
    device = relationship("Device", back_populates="alerts")
    reviewed_by = relationship("User")


class User(Base):
    """Acesso ao app. Não há cadastro aberto: a equipe DriveSafe cria cada login (e-mail e/ou celular)."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(254), unique=True, index=True)
    # O celular também serve de login: só dígitos, com código do país (ex.: 5511987654321).
    phone = Column(String(20), unique=True, index=True)
    name = Column(String(120), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(12), nullable=False)  # admin, gestor ou motorista
    company_id = Column(Integer, ForeignKey("companies.id"), index=True)
    driver_id = Column(Integer, ForeignKey("drivers.id"))
    active = Column(Boolean, nullable=False, default=True)
    must_change_password = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    last_login_at = Column(DateTime(timezone=True))

    company = relationship("Company", back_populates="users")
    driver = relationship("Driver")


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    token_hash = Column(String(64), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_seen_at = Column(DateTime(timezone=True))
    ip = Column(String(45))
    user_agent = Column(String(255))

    user = relationship("User")


class Consent(Base):
    """Histórico de consentimentos do motorista. Nunca é apagado: revogar é um registro novo com granted=False."""

    __tablename__ = "consents"

    id = Column(Integer, primary_key=True, index=True)
    driver_id = Column(Integer, ForeignKey("drivers.id"), index=True, nullable=False)
    kind = Column(String(40), nullable=False)
    granted = Column(Boolean, nullable=False)
    term_version = Column(String(20), nullable=False)
    channel = Column(String(20), nullable=False)
    recorded_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    recorded_by_user_id = Column(Integer, ForeignKey("users.id"))
    note = Column(Text)

    driver = relationship("Driver", back_populates="consents")
    recorded_by = relationship("User")


class AuditLog(Base):
    """Quem fez o quê com dados pessoais: login, exportação, revisão, consentimento, cadastro de usuário."""

    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    at = Column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    company_id = Column(Integer, index=True)
    action = Column(String(60), nullable=False)
    target = Column(String(120))
    details = Column(Text)
    ip = Column(String(45))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    if _is_sqlite:
        os.makedirs(config.DATA_DIR, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    _upgrade_schema()
    _assign_default_company()


# Colunas que bancos de versões anteriores não têm. ALTER TABLE só adiciona; nada é apagado.
_ADDED_COLUMNS = {
    "companies": ("contact_name", "contact_phone"),
    "users": ("phone",),
    "drivers": ("company_id",),
    "vehicles": ("company_id",),
    "devices": ("company_id", "live_status", "risk_level", "status_at", "fps", "latency_p95_ms"),
    "alerts": ("device_id", "event_uid", "details", "received_at", "company_id", "review_status",
               "reviewed_by_user_id", "reviewed_at", "review_note"),
}
_INDEXES = (
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_alerts_event_uid ON alerts (event_uid)",
    "CREATE INDEX IF NOT EXISTS ix_alerts_device_id ON alerts (device_id)",
    "CREATE INDEX IF NOT EXISTS ix_alerts_timestamp ON alerts (timestamp)",
    "CREATE INDEX IF NOT EXISTS ix_alerts_company_id ON alerts (company_id)",
    "CREATE INDEX IF NOT EXISTS ix_alerts_review_status ON alerts (review_status)",
    "CREATE INDEX IF NOT EXISTS ix_drivers_company_id ON drivers (company_id)",
    "CREATE INDEX IF NOT EXISTS ix_vehicles_company_id ON vehicles (company_id)",
    "CREATE INDEX IF NOT EXISTS ix_devices_company_id ON devices (company_id)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_phone ON users (phone)",
)


def _upgrade_schema():
    inspector = inspect(engine)
    added = {}
    with engine.begin() as conn:
        for table_name, columns in _ADDED_COLUMNS.items():
            existing = {column["name"] for column in inspector.get_columns(table_name)}
            table = Base.metadata.tables[table_name]
            missing = [name for name in columns if name not in existing]
            for name in missing:
                column_type = table.c[name].type.compile(dialect=engine.dialect)
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {name} {column_type}"))
            if missing:
                added[table_name] = missing
        for statement in _INDEXES:
            conn.execute(text(statement))

        alert_columns = added.get("alerts", [])
        converted = 0
        if "received_at" in alert_columns:
            # A primeira versão gravava o horário local de config.TIMEZONE sem fuso. Converte para UTC uma vez.
            table = Alert.__table__
            params = []
            for row in conn.execute(select(table.c.id, table.c.timestamp)).all():
                if row.timestamp is None:
                    continue
                utc_value = TZ.localize(row.timestamp.replace(tzinfo=None)).astimezone(timezone.utc)
                params.append({"b_id": row.id, "b_ts": utc_value, "b_received": utc_value})
            if params:
                conn.execute(
                    update(table)
                    .where(table.c.id == bindparam("b_id"))
                    .values(timestamp=bindparam("b_ts"), received_at=bindparam("b_received")),
                    params,
                )
            converted = len(params)
        if "review_status" in alert_columns:
            # Alertas anteriores à revisão não entram na fila do gestor.
            conn.execute(text("UPDATE alerts SET review_status = 'arquivado' WHERE review_status IS NULL"))

    for table_name, columns in added.items():
        logger.info("Banco atualizado: %s ganhou %s.", table_name, ", ".join(columns))
    if converted:
        logger.info("%d alerta(s) antigo(s) convertido(s) para UTC.", converted)


def _assign_default_company():
    """Registros sem empresa (banco de versão anterior ou cadastro pela linha de comando) vão para a empresa única."""
    db = SessionLocal()
    try:
        models = (Driver, Vehicle, Device, Alert)
        if not any(db.query(model.id).filter(model.company_id.is_(None)).first() for model in models):
            return
        companies = db.query(Company).order_by(Company.id).limit(2).all()
        if len(companies) > 1:
            logger.warning("Há motoristas, veículos, dispositivos ou alertas sem empresa. Vincule pelo app ou pelo manage.py.")
            return
        company = companies[0] if companies else Company(name="Empresa padrão")
        if not companies:
            db.add(company)
            db.flush()
        for model in models:
            db.query(model).filter(model.company_id.is_(None)).update({model.company_id: company.id},
                                                                      synchronize_session=False)
        db.commit()
        logger.info('Registros sem empresa vinculados a "%s".', company.name)
    finally:
        db.close()
