"""Peças da central (spec 026) usadas por várias rotas: ids públicos, limpeza de cardio, cursor, códigos e trechos."""
import base64
import binascii
import hashlib
import hmac
import os
import re
import secrets
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from backend import config
from backend.database import as_utc, utcnow

# ---------- ids públicos ----------

ALERT_TYPE_RE = re.compile(r"^[a-z0-9_]{1,50}$")


def parse_uid(value: Optional[str]) -> Optional[str]:
    """Qualquer forma de UUID → 32 caracteres hexadecimais minúsculos. None se não for UUID."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return uuid.UUID(value.strip()).hex
    except ValueError:
        return None


def parse_event_uid(value: Optional[str]) -> Optional[str]:
    """Id de evento no formato que o servidor já guarda (UUID com hífens, como o script gera)."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return str(uuid.UUID(value.strip()))
    except ValueError:
        return None


def iso_z(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


# ---------- "testando agora" ----------

def signal_is_fresh(device, now: Optional[datetime] = None) -> bool:
    last = as_utc(device.last_seen_at)
    if last is None or device.revoked_at is not None:
        return False
    return ((now or utcnow()) - last).total_seconds() < config.TESTING_WINDOW_S


def refresh_testing(device, now: Optional[datetime] = None) -> None:
    """Sessão aberta e sinal de vida recente. Guardado no aparelho para a mudança chegar ao painel pelo cursor."""
    device.testing_now = bool(device.current_session_uid) and signal_is_fresh(device, now)


# ---------- cardio: dado de saúde não sai do computador (RNF-16, RNF-17) ----------

CARDIO_KEYS = frozenset({"bpm", "cardio", "frequencia_cardiaca", "rppg", "respiracao_rpm", "rmssd_ms", "snr_db"})


def is_cardio_key(key: Any) -> bool:
    name = str(key).strip().lower()
    return name in CARDIO_KEYS or name.startswith("cardio_")


def strip_cardio(value: Any) -> Any:
    """Cópia sem nenhuma chave de cardio, em qualquer nível de dicionário ou lista."""
    if isinstance(value, dict):
        return {key: strip_cardio(item) for key, item in value.items() if not is_cardio_key(key)}
    if isinstance(value, list):
        return [strip_cardio(item) for item in value]
    return value


# ---------- cursor das novidades ----------

CURSOR_VERSION = "v1"


def encode_cursor(seq: int) -> str:
    return base64.urlsafe_b64encode(f"{CURSOR_VERSION}:{int(seq)}".encode("ascii")).decode("ascii").rstrip("=")


def decode_cursor(raw: Optional[str]) -> int:
    """'' ou None = desde o começo. ValueError se o cursor não veio desta central."""
    if raw is None or not raw.strip():
        return 0
    text = raw.strip()
    try:
        decoded = base64.urlsafe_b64decode(text + "=" * (-len(text) % 4)).decode("ascii")
    except (binascii.Error, UnicodeDecodeError, ValueError) as exc:
        raise ValueError("cursor inválido") from exc
    version, _, number = decoded.partition(":")
    if version != CURSOR_VERSION or not number.isdigit():
        raise ValueError("cursor inválido")
    return int(number)


# ---------- códigos de pareamento ----------

# Sem 0/O, 1/I/L: o código é lido de uma tela e digitado em outro computador.
PAIRING_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
PAIRING_LENGTH = 8
_secret_cache: Optional[bytes] = None
_secret_lock = threading.Lock()


def generate_pairing_code() -> str:
    return "".join(secrets.choice(PAIRING_ALPHABET) for _ in range(PAIRING_LENGTH))


def normalize_pairing_code(raw: Optional[str]) -> Optional[str]:
    """'abcd-2345' → 'ABCD2345'. None se não tiver o formato (conta como tentativa errada)."""
    if not isinstance(raw, str):
        return None
    code = re.sub(r"[\s-]", "", raw).upper()
    if len(code) != PAIRING_LENGTH or any(char not in PAIRING_ALPHABET for char in code):
        return None
    return code


def server_secret() -> bytes:
    """Segredo da central: variável de ambiente ou arquivo na pasta de dados (criado uma vez, só o dono lê)."""
    global _secret_cache
    if _secret_cache:
        return _secret_cache
    with _secret_lock:
        if _secret_cache:
            return _secret_cache
        if config.SECRET:
            data = config.SECRET.encode("utf-8")
        else:
            path = config.SECRET_FILE
            data = b""
            if os.path.exists(path):
                with open(path, "rb") as handle:
                    data = handle.read().strip()
            else:
                os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
                data = secrets.token_hex(32).encode("ascii")
                try:
                    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                except FileExistsError:  # outro processo criou ao mesmo tempo
                    with open(path, "rb") as handle:
                        data = handle.read().strip()
                else:
                    with os.fdopen(descriptor, "wb") as handle:
                        handle.write(data)
        if len(data) < 32:
            raise RuntimeError("Segredo da central curto demais (DRIVESAFE_SEGREDO_CENTRAL ou arquivo de segredo).")
        _secret_cache = data
    return _secret_cache


def pairing_code_hash(code: str) -> str:
    return hmac.new(server_secret(), code.encode("ascii"), hashlib.sha256).hexdigest()


# ---------- trechos ----------

# formato → (Content-Type na hora de baixar, extensão do arquivo)
CLIP_FORMATS = {"mp4": ("video/mp4", "mp4"), "webm": ("video/webm", "webm"), "rgclip": ("application/zip", "rgclip")}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
MAGIC_BYTES_NEEDED = 12


def clips_root() -> Path:
    return Path(config.CLIPS_DIR).resolve()


def long_path(path: Path) -> Path:
    """Windows sem caminhos longos ligados para em 260 caracteres; uid da empresa + uid do trecho já gastam 70."""
    if os.name == "nt" and not str(path).startswith("\\\\?\\"):
        return Path("\\\\?\\" + os.path.abspath(path))
    return path


def clip_file(relative: str) -> Path:
    """Caminho do arquivo do trecho, sempre dentro da pasta de trechos (o caminho relativo é gerado pela central)."""
    root = clips_root()
    path = (root / relative).resolve()
    if root not in path.parents:
        raise ValueError("caminho de trecho fora da pasta de trechos")
    return long_path(path)


def looks_like(clip_format: str, head: bytes) -> bool:
    """Confere a assinatura do arquivo: o que é servido como vídeo é vídeo (ou o zip do .rgclip)."""
    if clip_format == "mp4":
        return len(head) >= 8 and head[4:8] == b"ftyp"
    if clip_format == "webm":
        return head[:4] == b"\x1a\x45\xdf\xa3"
    if clip_format == "rgclip":
        return head[:4] == b"PK\x03\x04"
    return False
