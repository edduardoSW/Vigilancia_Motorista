"""Trechos de vídeo (spec 026): o aparelho envia, o painel da mesma empresa baixa.

- Envio: corpo binário em streaming para um arquivo temporário na mesma pasta; tamanho (25 MB), assinatura do formato e
  SHA-256 conferidos antes de virar `trechos/<uid da empresa>/<uid do trecho>.<formato>`. Nome gerado pela central.
- Reenviar o mesmo trecho (mesmo uid e mesmo SHA-256) não grava de novo: 200.
- Download só para usuário da empresa (ou a equipe), com `X-RotaGuard-Sha256` e registro na auditoria.
"""
import asyncio
import hashlib
import os
import secrets
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from pydantic import TypeAdapter, ValidationError
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend import config
from backend.auth import Principal, audit, ensure_company_access, require_roles
from backend.central import (
    ALERT_TYPE_RE, CLIP_FORMATS, MAGIC_BYTES_NEEDED, SHA256_RE, clip_file, looks_like, parse_event_uid, parse_uid,
)
from backend.database import Alert, Clip, Device, as_utc, get_db, utcnow
from backend.routes.device_api import authenticated_device
from backend.schemas import TrechoRecebidoOut

router = APIRouter(tags=["central"])
manager_roles = require_roles("admin", "gestor")
_datetime = TypeAdapter(datetime)
MAX_DURATION_S = 600


@dataclass
class ClipMeta:
    uid: str
    format: str
    sha256: str
    alert_type: str
    session_uid: Optional[str]
    event_uid: Optional[str]
    started_at: datetime
    ended_at: datetime

    @property
    def duration_s(self) -> float:
        return round((self.ended_at - self.started_at).total_seconds(), 3)


class _UidLocks:
    """Um envio por trecho de cada vez (o servidor roda num processo só): dois envios do mesmo uid não se atropelam."""

    def __init__(self):
        self._locks: dict = {}
        self._waiting: dict = {}

    @asynccontextmanager
    async def hold(self, key: str):
        lock = self._locks.setdefault(key, asyncio.Lock())
        self._waiting[key] = self._waiting.get(key, 0) + 1
        try:
            async with lock:
                yield
        finally:
            self._waiting[key] -= 1
            if not self._waiting[key]:
                del self._waiting[key]
                del self._locks[key]


_locks = _UidLocks()


def _unprocessable(detail: str) -> HTTPException:
    return HTTPException(status_code=422, detail=detail)


def _header_datetime(request: Request, name: str) -> datetime:
    raw = (request.headers.get(name) or "").strip()
    if not raw:
        raise _unprocessable(f"Cabeçalho {name} obrigatório (data ISO 8601).")
    try:
        return as_utc(_datetime.validate_python(raw))
    except ValidationError:
        raise _unprocessable(f"Cabeçalho {name} não é uma data ISO 8601.")


def parse_meta(raw_uid: str, request: Request) -> ClipMeta:
    headers = request.headers
    uid = parse_uid(raw_uid)
    if uid is None:
        raise _unprocessable("Id de trecho inválido: use um uuid4 (32 caracteres hexadecimais).")
    clip_format = (headers.get("x-rotaguard-formato") or "").strip().lower()
    if clip_format not in CLIP_FORMATS:
        raise _unprocessable("X-RotaGuard-Formato deve ser mp4, webm ou rgclip.")
    sha256 = (headers.get("x-rotaguard-sha256") or "").strip().lower()
    if not SHA256_RE.match(sha256):
        raise _unprocessable("X-RotaGuard-Sha256 deve ter 64 caracteres hexadecimais.")
    alert_type = (headers.get("x-rotaguard-tipo") or "").strip()
    if not ALERT_TYPE_RE.match(alert_type):
        raise _unprocessable("X-RotaGuard-Tipo deve ser o tipo do evento (letras minúsculas, números e _).")
    raw_session, raw_event = headers.get("x-rotaguard-sessao"), headers.get("x-rotaguard-evento")
    session_uid = parse_uid(raw_session)
    if session_uid is None:
        raise _unprocessable("X-RotaGuard-Sessao obrigatório: o uid da sessão de teste do trecho.")
    event_uid = parse_event_uid(raw_event) if raw_event else None
    if raw_event and event_uid is None:
        raise _unprocessable("X-RotaGuard-Evento inválido: use o uid do evento.")
    meta = ClipMeta(uid=uid, format=clip_format, sha256=sha256, alert_type=alert_type, session_uid=session_uid,
                    event_uid=event_uid, started_at=_header_datetime(request, "x-rotaguard-inicio"),
                    ended_at=_header_datetime(request, "x-rotaguard-fim"))
    if not 0 <= meta.duration_s <= MAX_DURATION_S:
        raise _unprocessable(f"O trecho precisa terminar depois de começar e durar até {MAX_DURATION_S} s.")
    return meta


def _too_big() -> HTTPException:
    return HTTPException(status_code=413, detail=f"Trecho maior que {config.CLIP_MAX_BYTES // (1024 * 1024)} MB.")


def precheck(db: Session, device: Device, meta: ClipMeta):
    """(trecho já registrado ou None, caminho relativo do arquivo)."""
    existing = db.query(Clip).filter(Clip.uid == meta.uid).first()
    if existing is not None:
        if existing.device_id != device.id or existing.sha256 != meta.sha256 or existing.deleted_at is not None:
            raise HTTPException(status_code=409, detail="Já existe um trecho com este id e outro conteúdo.")
        return existing, existing.path
    count = (db.query(func.count(Clip.id))
             .filter(Clip.device_id == device.id, Clip.session_uid == meta.session_uid).scalar())
    if count >= config.CLIPS_PER_SESSION:
        raise HTTPException(status_code=409, detail=f"Limite de {config.CLIPS_PER_SESSION} trechos por sessão.")
    today = (db.query(func.count(Clip.id))
             .filter(Clip.device_id == device.id, Clip.received_at > utcnow() - timedelta(days=1)).scalar())
    if today >= config.CLIPS_PER_DEVICE_DAY:
        raise HTTPException(status_code=429, headers={"Retry-After": "3600"},
                            detail=f"Limite de {config.CLIPS_PER_DEVICE_DAY} trechos por dia deste computador.")
    return None, f"{device.company.uid}/{meta.uid}.{CLIP_FORMATS[meta.format][1]}"


async def receive_file(request: Request, final_path: Path, meta: ClipMeta) -> int:
    final_path.parent.mkdir(parents=True, exist_ok=True)
    # Nome curto: no Windows o caminho inteiro não pode passar de 260 caracteres.
    temp = final_path.with_name(f".{secrets.token_hex(8)}.part")
    digest, size, head, checked = hashlib.sha256(), 0, b"", False
    try:
        with open(temp, "xb") as handle:
            async for chunk in request.stream():
                if not chunk:
                    continue
                size += len(chunk)
                if size > config.CLIP_MAX_BYTES:
                    raise _too_big()
                if not checked:
                    head += chunk[:MAGIC_BYTES_NEEDED - len(head)]
                    if len(head) >= MAGIC_BYTES_NEEDED:
                        if not looks_like(meta.format, head):
                            raise _unprocessable(f"O arquivo não tem a assinatura de um {meta.format}.")
                        checked = True
                digest.update(chunk)
                handle.write(chunk)
        if size == 0:
            raise _unprocessable("O trecho chegou vazio.")
        if not checked and not looks_like(meta.format, head):
            raise _unprocessable(f"O arquivo não tem a assinatura de um {meta.format}.")
        if digest.hexdigest() != meta.sha256:
            raise _unprocessable("SHA-256 não confere: o arquivo chegou diferente do enviado. Envie de novo.")
        os.replace(temp, final_path)
    except BaseException:
        temp.unlink(missing_ok=True)
        raise
    return size


def save(db: Session, device: Device, meta: ClipMeta, existing: Optional[Clip], relative: str, size: int) -> int:
    if existing is not None:  # registro já existia e o arquivo tinha sumido: arquivo restaurado
        existing.size = size
        db.commit()
        return 200
    clip = Clip(uid=meta.uid, company_id=device.company_id, device_id=device.id, session_uid=meta.session_uid,
                event_uid=meta.event_uid, alert_type=meta.alert_type, started_at=meta.started_at,
                ended_at=meta.ended_at, duration_s=meta.duration_s, format=meta.format, size=size,
                sha256=meta.sha256, path=relative, received_at=utcnow())
    db.add(clip)
    # Liga ao evento, chegue qual chegar primeiro (sempre do mesmo aparelho).
    if meta.event_uid:
        alert = db.query(Alert).filter(Alert.event_uid == meta.event_uid, Alert.device_id == device.id).first()
        if alert is not None and alert.clip_uid is None:
            alert.clip_uid = meta.uid
    else:
        alert = db.query(Alert).filter(Alert.clip_uid == meta.uid, Alert.device_id == device.id).first()
        if alert is not None:
            clip.event_uid = alert.event_uid
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        again = db.query(Clip).filter(Clip.uid == meta.uid).first()
        if again is not None and again.device_id == device.id and again.sha256 == meta.sha256:
            return 200
        raise HTTPException(status_code=409, detail="Já existe um trecho com este id e outro conteúdo.")
    return 201


@router.put("/api/trechos/{trecho_uid}", response_model=TrechoRecebidoOut, status_code=201)
async def put_clip(trecho_uid: str, request: Request, response: Response,
                   device: Device = Depends(authenticated_device), db: Session = Depends(get_db)):
    meta = parse_meta(trecho_uid, request)
    declared = (request.headers.get("content-length") or "").strip()
    if declared.isdigit() and int(declared) > config.CLIP_MAX_BYTES:
        raise _too_big()
    async with _locks.hold(meta.uid):
        existing, relative = await run_in_threadpool(precheck, db, device, meta)
        path = clip_file(relative)
        if existing is not None and path.is_file():
            response.status_code = 200
            return TrechoRecebidoOut(uid=meta.uid, tamanho=existing.size)
        size = await receive_file(request, path, meta)
        response.status_code = await run_in_threadpool(save, db, device, meta, existing, relative, size)
    return TrechoRecebidoOut(uid=meta.uid, tamanho=size)


@router.get("/api/trechos/{trecho_uid}/arquivo")
def download_clip(trecho_uid: str, request: Request, principal: Principal = Depends(manager_roles),
                  db: Session = Depends(get_db)):
    uid = parse_uid(trecho_uid)
    clip = db.query(Clip).filter(Clip.uid == uid).first() if uid else None
    if clip is None:
        raise HTTPException(status_code=404, detail="Trecho não encontrado.")
    ensure_company_access(principal, clip.company_id)
    path = clip_file(clip.path)
    if clip.deleted_at is not None or not path.is_file():
        raise HTTPException(status_code=410, detail="Trecho apagado da central pelo prazo de guarda.")
    audit(db, principal, "trecho_baixado", target=f"trecho:{clip.uid}", details={"tamanho": clip.size},
          request=request, company_id=clip.company_id)
    db.commit()
    media_type, extension = CLIP_FORMATS[clip.format]
    return FileResponse(path, media_type=media_type, filename=f"{clip.uid}.{extension}",
                        headers={"X-RotaGuard-Sha256": clip.sha256, "Cache-Control": "no-store"})
