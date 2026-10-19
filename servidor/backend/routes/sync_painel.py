"""Novidades para o painel executável (spec 026): o que mudou desde o cursor, da empresa de quem está logado.

O cursor é o número de sincronização (`sync_seq`) do último item entregue, codificado. Cada criação ou alteração de
aparelho, sessão, evento ou trecho ganha um número maior (database._stamp_sync_seq), então "depois do cursor" é
exatamente "o que mudou desde a última busca", em ordem e sem repetir.
"""
import json
import logging
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from backend import config
from backend.auth import Principal, require_roles, scoped_company
from backend.central import decode_cursor, encode_cursor, signal_is_fresh, strip_cardio
from backend.database import Alert, Clip, Device, RemoteTestSession, as_utc, get_db, utcnow
from backend.schemas import AparelhoNovidade, EventoNovidade, NovidadesOut, SessaoNovidade, TrechoNovidade

logger = logging.getLogger("drivesafe.api")
router = APIRouter(tags=["central"])


def _json_object(raw: Optional[str], what: str, row_id: int) -> Optional[dict]:
    if not raw:
        return None
    try:
        value = json.loads(raw)
    except ValueError:
        logger.warning("%s %s com JSON inválido", what, row_id)
        return None
    return strip_cardio(value) if isinstance(value, dict) else None


def device_item(device: Device, now) -> AparelhoNovidade:
    return AparelhoNovidade(
        uid=device.uid, nome=device.name, computador=device.computer_name or device.hostname,
        programa=device.program_name or device.software_version, pareado_em=as_utc(device.paired_at),
        ultimo_sinal=as_utc(device.last_seen_at),
        testando_agora=bool(device.testing_now) and signal_is_fresh(device, now),
        risco_atual=device.risk_level, sessao_atual_uid=device.current_session_uid,
        revogado_em=as_utc(device.revoked_at), alterado_em=as_utc(device.changed_at or device.created_at),
    )


def session_item(record: RemoteTestSession, _now) -> SessaoNovidade:
    return SessaoNovidade(
        uid=record.uid, aparelho_uid=record.device.uid if record.device else None,
        iniciada_em=as_utc(record.started_at), encerrada_em=as_utc(record.ended_at), programa=record.program,
        camera=record.camera, resumo=_json_object(record.summary, "Sessão", record.id) or {},
        alterado_em=as_utc(record.changed_at or record.received_at),
    )


def event_item(alert: Alert, _now) -> EventoNovidade:
    occurred = as_utc(alert.timestamp or alert.received_at)
    return EventoNovidade(
        uid=alert.event_uid or f"legado-{alert.id}", aparelho_uid=alert.device.uid if alert.device else None,
        sessao_uid=alert.session_uid, tipo=alert.alert_type or "", nivel_risco=alert.risk_level or 0,
        duracao_s=alert.duration or 0.0, ocorrido_em=occurred,
        detalhes=_json_object(alert.details, "Alerta", alert.id), trecho_uid=alert.clip_uid,
        alterado_em=as_utc(alert.changed_at or alert.received_at or alert.timestamp),
    )


def clip_item(clip: Clip, _now) -> TrechoNovidade:
    return TrechoNovidade(
        uid=clip.uid, aparelho_uid=clip.device.uid if clip.device else None, sessao_uid=clip.session_uid,
        evento_uid=clip.event_uid, tipo=clip.alert_type, inicio=as_utc(clip.started_at), fim=as_utc(clip.ended_at),
        duracao_s=clip.duration_s, formato=clip.format, tamanho=clip.size, sha256=clip.sha256,
        recebido_em=as_utc(clip.received_at), apagado_em=as_utc(clip.deleted_at),
        alterado_em=as_utc(clip.changed_at or clip.received_at),
    )


COLLECTIONS = (
    ("aparelhos", Device, (), device_item),
    ("sessoes", RemoteTestSession, (joinedload(RemoteTestSession.device),), session_item),
    ("eventos", Alert, (joinedload(Alert.device),), event_item),
    ("trechos", Clip, (joinedload(Clip.device),), clip_item),
)


def expire_testing(db: Session, company_id: Optional[int], now) -> None:
    """Quem parou de mandar sinal de vida deixa de estar "testando agora"; a mudança ganha número e chega ao painel."""
    cutoff = now - timedelta(seconds=config.TESTING_WINDOW_S)
    query = db.query(Device).filter(Device.testing_now.is_(True),
                                    or_(Device.last_seen_at.is_(None), Device.last_seen_at < cutoff,
                                        Device.revoked_at.isnot(None)))
    if company_id is not None:
        query = query.filter(Device.company_id == company_id)
    stale = query.all()
    if stale:
        for device in stale:
            device.testing_now = False
        db.commit()


@router.get("/api/sync/novidades", response_model=NovidadesOut)
def novidades(desde: str = Query("", max_length=200, description="Cursor da última busca; vazio = tudo"),
              limite: int = Query(500, ge=1, le=1000), company_id: Optional[int] = None,
              principal: Principal = Depends(require_roles("admin", "gestor")), db: Session = Depends(get_db)):
    try:
        since = decode_cursor(desde)
    except ValueError:
        raise HTTPException(status_code=400, detail="Cursor inválido. Busque desde o começo (desde vazio).")
    scope = scoped_company(principal, company_id)
    now = utcnow()
    expire_testing(db, scope, now)

    found = []
    for kind, model, options, _ in COLLECTIONS:
        query = db.query(model).filter(model.sync_seq > since)
        if scope is not None:
            query = query.filter(model.company_id == scope)
        found += [(row.sync_seq, kind, row) for row in query.options(*options).order_by(model.sync_seq).limit(limite + 1)]
    # Os `limite` menores números entre as quatro listas: nada fica para trás na próxima página.
    found.sort(key=lambda item: item[0])
    page = found[:limite]
    serializers = {kind: serializer for kind, _, _, serializer in COLLECTIONS}
    items = {kind: [] for kind, _, _, _ in COLLECTIONS}
    for _, kind, row in page:
        items[kind].append(serializers[kind](row, now))
    return NovidadesOut(cursor=encode_cursor(page[-1][0] if page else since), mais=len(found) > limite, agora=now,
                        **items)
