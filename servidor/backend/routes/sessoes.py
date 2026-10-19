"""Sessões de teste enviadas pelo RotaGuard Script (spec 026): início, fim e resumo. Idempotente: reenviar atualiza."""
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.central import parse_uid, refresh_testing, strip_cardio
from backend.database import Device, RemoteTestSession, as_utc, get_db
from backend.routes.device_api import authenticated_device
from backend.schemas import SessaoIn, UidOut

router = APIRouter(tags=["central"])

MAX_SUMMARY_BYTES = 16000


@router.put("/api/sessoes/{sessao_uid}", response_model=UidOut)
def put_session(sessao_uid: str, payload: SessaoIn, device: Device = Depends(authenticated_device),
                db: Session = Depends(get_db)):
    uid = parse_uid(sessao_uid)
    if uid is None:
        raise HTTPException(status_code=422, detail="Id de sessão inválido: use um uuid4 (32 caracteres hexadecimais).")
    started, ended = as_utc(payload.iniciada_em), as_utc(payload.encerrada_em)
    if ended is not None and ended < started:
        raise HTTPException(status_code=422, detail="A sessão não pode terminar antes de começar.")
    # Resumo sem nenhum dado de cardio (dado de saúde fica no computador).
    summary = json.dumps(strip_cardio(payload.resumo), ensure_ascii=False)
    if len(summary.encode("utf-8")) > MAX_SUMMARY_BYTES:
        raise HTTPException(status_code=413, detail=f"Resumo da sessão passou de {MAX_SUMMARY_BYTES} bytes.")

    record = db.query(RemoteTestSession).filter(RemoteTestSession.uid == uid).first()
    if record is not None and record.device_id != device.id:
        raise HTTPException(status_code=409, detail="Este id de sessão já pertence a outro aparelho.")
    if record is None:
        record = RemoteTestSession(uid=uid, company_id=device.company_id, device_id=device.id)
        db.add(record)
    record.started_at, record.ended_at = started, ended
    record.program = (payload.programa or "").strip()[:80] or None
    record.camera = (payload.camera or "").strip()[:120] or None
    record.summary = summary

    if ended is None:
        device.current_session_uid = uid
    elif device.current_session_uid == uid:
        device.current_session_uid = None
    refresh_testing(device)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Sessão registrada em paralelo por outra requisição; reenvie.")
    return UidOut(uid=uid)
