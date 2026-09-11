"""Contratos da API do servidor central."""
from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

Role =Literal["admin", "gestor", "motorista"]
ActivationPolicy = Literal["desligado", "local", "enviar"]
ReviewDecision = Literal["pendente", "confirmado", "falso_alarme", "orientado"]
ConsentKind = Literal["monitoramento", "perfil_entre_viagens", "sinais_ativacao_envio"]
ConsentChannel = Literal["app_motorista", "termo_assinado", "admin"]


class Ref(BaseModel):
    id: int
    name: str


# ---------- dispositivo (token) ----------

class DeviceInfo(BaseModel):
    """Informações que o dispositivo manda sobre si mesmo a cada contato."""

    hostname: Optional[str] = Field(None, max_length=255)
    platform: Optional[str] = Field(None, max_length=255)
    software_version: Optional[str] = Field(None, max_length=32)
    pending_events: Optional[int] = Field(None, ge=0)


class DeviceLiveStatus(BaseModel):
    """Estado ao vivo do monitoramento, mandado no sinal de "estou vivo". Nada de imagem."""

    model_config = ConfigDict(extra="ignore")

    risk_level: Optional[int] = Field(None, ge=0, le=3)
    risk_name: Optional[str] = Field(None, max_length=16)
    reasons: List[str] = Field(default_factory=list, max_length=8)
    calibrating: Optional[bool] = None
    calibration_progress: Optional[float] = Field(None, ge=0, le=1)
    face_found: Optional[bool] = None
    eyes_visible: Optional[bool] = None
    eyes_reason: Optional[str] = Field(None, max_length=32)
    phone_state: Optional[str] = Field(None, max_length=24)
    fps: Optional[float] = Field(None, ge=0, le=1000)
    latency_p95_ms: Optional[float] = Field(None, ge=0, le=600000)
    driving_hours: Optional[float] = Field(None, ge=0, le=240)
    activation_mode: Optional[str] = Field(None, max_length=12)
    activation_index: Optional[float] = Field(None, ge=0, le=1)
    activation_confidence: Optional[str] = Field(None, max_length=8)

    @field_validator("reasons")
    @classmethod
    def _short_reasons(cls, value: List[str]) -> List[str]:
        return [str(item)[:60] for item in value]


class HeartbeatIn(BaseModel):
    device: DeviceInfo
    camera_ok: Optional[bool] = None
    status: Optional[DeviceLiveStatus] = None


class DevicePolicy(BaseModel):
    """O que o servidor manda o dispositivo fazer, conforme a empresa e os consentimentos do motorista."""

    driver_id: Optional[int] = None
    profile_consent: bool = False
    activation_mode: ActivationPolicy = "local"
    status_interval_s: int = 15


class EventIn(BaseModel):
    event_uid: UUID
    alert_type: str = Field(pattern=r"^[a-z0-9_]{1,50}$")
    risk_level: int = Field(ge=1, le=5)
    duration: float = Field(ge=0, le=86400)
    # Relógio do dispositivo. Pode estar errado se o Raspberry Pi ligou sem internet.
    occurred_at: datetime
    # Segundos desde o evento, medidos com relógio monotônico. Quando vem, tem prioridade.
    age_seconds: Optional[float] = Field(None, ge=0, le=365 * 86400)
    details: Optional[Dict[str, Any]] = None


class EventBatchIn(BaseModel):
    device: DeviceInfo
    events: List[EventIn] = Field(min_length=1, max_length=500)


class EventBatchOut(BaseModel):
    accepted: int
    duplicates: int


# ---------- sessão ----------

class LoginIn(BaseModel):
    # E-mail ou celular, conforme o acesso criado pela equipe.
    login: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class PasswordChangeIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=1, max_length=256)


class MeOut(BaseModel):
    id: int
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    role: Role
    company: Optional[Ref] = None
    driver_id: Optional[int] = None
    must_change_password: bool = False


# ---------- empresas e usuários ----------

class CompanyIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    document: Optional[str] = Field(None, max_length=20)
    contact_name: Optional[str] = Field(None, max_length=120)
    contact_phone: Optional[str] = Field(None, max_length=30)
    activation_policy: ActivationPolicy = "local"


class CompanyPatch(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=120)
    document: Optional[str] = Field(None, max_length=20)
    contact_name: Optional[str] = Field(None, max_length=120)
    contact_phone: Optional[str] = Field(None, max_length=30)
    activation_policy: Optional[ActivationPolicy] = None
    active: Optional[bool] = None


class CompanyOut(BaseModel):
    id: int
    name: str
    document: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    activation_policy: ActivationPolicy
    active: bool
    created_at: datetime
    drivers: int = 0
    vehicles: int = 0
    devices: int = 0
    users: int = 0


class UserIn(BaseModel):
    """Só a equipe DriveSafe cria acessos. Precisa de e-mail ou celular (os dois servem de login)."""

    name: str = Field(min_length=2, max_length=120)
    email: Optional[str] = Field(None, max_length=254)
    phone: Optional[str] = Field(None, max_length=30)
    role: Role
    company_id: Optional[int] = None
    driver_id: Optional[int] = None
    password: Optional[str] = Field(None, max_length=256)


class UserPatch(BaseModel):
    """O gestor só pode mandar active=false (bloquear o acesso). O resto é com a equipe DriveSafe."""

    name: Optional[str] = Field(None, min_length=2, max_length=120)
    email: Optional[str] = Field(None, max_length=254)
    phone: Optional[str] = Field(None, max_length=30)
    active: Optional[bool] = None
    reset_password: bool = False


class UserOut(BaseModel):
    id: int
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    role: Role
    company: Optional[Ref] = None
    driver: Optional[Ref] = None
    active: bool
    must_change_password: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None


class UserCreatedOut(BaseModel):
    user: UserOut
    temporary_password: Optional[str] = None


class ContactOut(BaseModel):
    phone: str
    tel_url: str
    whatsapp_url: Optional[str] = None


class AppInfoOut(BaseModel):
    """Público (tela de login): não há cadastro aberto, só o contato da equipe."""

    version: str
    timezone: str
    self_signup: bool = False
    contact: Optional[ContactOut] = None


# ---------- motoristas, veículos e consentimentos ----------

class DriverIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    license_number: str = Field(min_length=3, max_length=30)
    phone: Optional[str] = Field(None, max_length=30)
    company_id: Optional[int] = None


class DriverPatch(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=120)
    license_number: Optional[str] = Field(None, min_length=3, max_length=30)
    phone: Optional[str] = Field(None, max_length=30)


class DriverOut(BaseModel):
    id: int
    name: str
    license_number: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[Ref] = None
    created_at: Optional[datetime] = None
    alerts_7d: int = 0
    alerts_30d: int = 0
    worst_risk_7d: int = 0
    categories_7d: Dict[str, int] = Field(default_factory=dict)
    consents: Dict[str, bool] = Field(default_factory=dict)
    last_alert_at: Optional[datetime] = None
    vehicle: Optional[Ref] = None
    has_login: bool = False


class TrendDay(BaseModel):
    day: date
    drowsiness: int = 0
    phone: int = 0
    other: int = 0
    worst_risk: int = 0


class ConsentIn(BaseModel):
    kind: ConsentKind
    granted: bool
    channel: ConsentChannel
    note: Optional[str] = Field(None, max_length=500)


class ConsentOut(BaseModel):
    id: int
    kind: str
    granted: bool
    term_version: str
    channel: str
    recorded_at: datetime
    recorded_by: Optional[str] = None
    note: Optional[str] = None


class DriverDetailOut(DriverOut):
    trend: List[TrendDay] = Field(default_factory=list)
    consent_history: List[ConsentOut] = Field(default_factory=list)
    devices: List[Ref] = Field(default_factory=list)


class VehicleIn(BaseModel):
    plate: str = Field(min_length=5, max_length=12)
    model: str = Field(min_length=1, max_length=60)
    type: str = Field(min_length=1, max_length=40)
    company_id: Optional[int] = None


class VehiclePatch(BaseModel):
    plate: Optional[str] = Field(None, min_length=5, max_length=12)
    model: Optional[str] = Field(None, min_length=1, max_length=60)
    type: Optional[str] = Field(None, min_length=1, max_length=40)


class VehicleOut(BaseModel):
    id: int
    plate: str
    model: Optional[str] = None
    type: Optional[str] = None
    company: Optional[Ref] = None
    created_at: Optional[datetime] = None


# ---------- dispositivos ----------

class DeviceIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    company_id: int
    vehicle_id: Optional[int] = None
    driver_id: Optional[int] = None


class DevicePatch(BaseModel):
    """vehicle_id / driver_id = 0 desvincula."""

    name: Optional[str] = Field(None, min_length=2, max_length=100)
    vehicle_id: Optional[int] = None
    driver_id: Optional[int] = None


class DeviceOut(BaseModel):
    id: int
    name: str
    token_prefix: str
    company: Optional[Ref] = None
    vehicle: Optional[Ref] = None
    driver: Optional[Ref] = None
    hostname: Optional[str] = None
    platform: Optional[str] = None
    software_version: Optional[str] = None
    camera_ok: Optional[bool] = None
    pending_events: int = 0
    last_seen_at: Optional[datetime] = None
    online: bool
    revoked: bool
    created_at: datetime
    live: Optional[DeviceLiveStatus] = None
    status_at: Optional[datetime] = None


class DeviceCreatedOut(BaseModel):
    device: DeviceOut
    token: str


class HeartbeatOut(DeviceOut):
    policy: DevicePolicy


# ---------- alertas e painel ----------

class AlertOut(BaseModel):
    id: int
    alert_type: str
    label: str
    category: str
    risk_level: int
    duration: float
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime
    received_at: Optional[datetime] = None
    company: Optional[Ref] = None
    driver: Optional[Ref] = None
    vehicle: Optional[Ref] = None
    device: Optional[Ref] = None
    review_status: str = "pendente"
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_note: Optional[str] = None


class AlertPage(BaseModel):
    items: List[AlertOut]
    total: int


class ReviewIn(BaseModel):
    status: ReviewDecision
    note: Optional[str] = Field(None, max_length=1000)


class DriverDayOut(BaseModel):
    day: date
    hours: List[int]
    alerts: List[AlertOut]


class RiskCount(BaseModel):
    normal: int = 0
    attention: int = 0
    high: int = 0
    critical: int = 0
    no_signal: int = 0


class DriverAttention(BaseModel):
    driver: Ref
    alerts_7d: int
    worst_risk: int
    top_category: Optional[str] = None


class OverviewOut(BaseModel):
    now: RiskCount
    devices_online: int
    devices_total: int
    alerts_today: int
    critical_today: int
    to_review: int
    drivers_attention: List[DriverAttention]
    latest_alerts: List[AlertOut]


class FleetItem(BaseModel):
    device: DeviceOut
    alerts_today: int = 0
    risk_hours_today: List[int] = Field(default_factory=list)


# ---------- modo teste (equipe) ----------

class TestStartIn(BaseModel):
    camera: str = Field("0", min_length=1, max_length=300)
    company_id: int
    driver_id: Optional[int] = None
    vehicle_id: Optional[int] = None
    calibration_min_s: float = Field(300.0, ge=20, le=1800)
    calibration_max_s: float = Field(600.0, ge=20, le=3600)
    phone: bool = True
    infrared: Literal["auto", "sim", "nao"] = "auto"
    activation_mode: ActivationPolicy = "local"


class TestStateOut(BaseModel):
    available: bool
    reason: Optional[str] = None
    running: bool = False
    started_at: Optional[datetime] = None
    config: Optional[Dict[str, Any]] = None
    device_id: Optional[int] = None
    last: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    marks: int = 0


class MarkIn(BaseModel):
    kind: Literal["piscada", "celular", "outro"] = "piscada"
    note: Optional[str] = Field(None, max_length=200)


class AnalysisOut(BaseModel):
    id: str
    name: str
    status: Literal["na_fila", "processando", "concluida", "falhou"]
    progress: float = 0.0
    phone: bool = False
    created_at: datetime
    finished_at: Optional[datetime] = None
    error: Optional[str] = None
    summary: Optional[Dict[str, Any]] = None
    files: List[str] = Field(default_factory=list)
