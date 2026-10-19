"""Pareamento por código (spec 026): o painel gera um código curto; o RotaGuard Script de outro computador troca o código
por um token de aparelho da mesma empresa, sem ninguém copiar token na mão.

- O código vale 30 minutos, serve uma vez só e fica no banco só como HMAC (segredo fora do banco).
- A troca é pública, com limite de tentativas erradas por IP (10 por minuto → 429).
- O token do aparelho é igual ao do `manage.py criar-dispositivo` (dsk_…, guardado só como hash) e só envia dados.
"""
import math
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import func, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend import config
from backend.auth import Principal, audit, client_ip, ensure_company_access, require_roles
from backend.central import generate_pairing_code, normalize_pairing_code, pairing_code_hash, parse_uid
from backend.database import Company, Device, PairingCode, as_utc, get_db, new_uid, utcnow
from backend.schemas import CodigoIn, CodigoOut, EmpresaRef, TrocaIn, TrocaOut
from backend.security import LoginThrottle, generate_device_token

router = APIRouter(prefix="/api/pareamento", tags=["central"])
manager_roles = require_roles("admin", "gestor")
exchange_throttle = LoginThrottle(max_failures=config.PAIRING_MAX_FAILURES, window_s=config.PAIRING_WINDOW_S)

INVALID_CODE = "Código inválido, vencido ou já usado. Gere um código novo no painel."


@router.post("/codigos", response_model=CodigoOut, status_code=201)
def create_code(payload: CodigoIn, request: Request, principal: Principal = Depends(manager_roles),
                db: Session = Depends(get_db)):
    if principal.is_admin:
        company = db.get(Company, payload.company_id) if payload.company_id else None
        if company is None:
            raise HTTPException(status_code=400, detail="Escolha a empresa do computador (company_id).")
    else:
        if payload.company_id not in (None, principal.company_id):
            raise HTTPException(status_code=403, detail="Você só gera código para a sua empresa.")
        company = principal.user.company
    if company is None or not company.active:
        raise HTTPException(status_code=400, detail="Empresa inativa.")

    now = utcnow()
    active = (db.query(func.count(PairingCode.id))
              .filter(PairingCode.company_id == company.id, PairingCode.used_at.is_(None),
                      PairingCode.cancelled_at.is_(None), PairingCode.expires_at > now).scalar())
    if active >= config.PAIRING_MAX_ACTIVE:
        raise HTTPException(status_code=429, detail="Há códigos demais ainda válidos. Use um deles ou espere vencer.")

    name = (payload.nome or "").strip()[:100] or None
    company_id, user_id = company.id, principal.user.id
    for _ in range(5):
        code = generate_pairing_code()
        record = PairingCode(code_hash=pairing_code_hash(code), company_id=company_id, created_by_user_id=user_id,
                             device_uid=new_uid(), device_name=name, created_at=now,
                             expires_at=now + timedelta(minutes=config.PAIRING_CODE_MINUTES))
        db.add(record)
        try:
            db.flush()
            break
        except IntegrityError:  # código igual a outro (1 em 10^12): sorteia de novo
            db.rollback()
    else:
        raise HTTPException(status_code=503, detail="Não consegui gerar um código agora. Tente de novo.")
    audit(db, principal, "codigo_pareamento_gerado", target=f"aparelho:{record.device_uid}",
          details={"nome": name} if name else None, request=request, company_id=company_id)
    db.commit()
    return CodigoOut(codigo=code, expira_em=as_utc(record.expires_at), aparelho_uid=record.device_uid)


@router.post("/trocar", response_model=TrocaOut)
def exchange_code(payload: TrocaIn, request: Request, db: Session = Depends(get_db)):
    ip = client_ip(request) or "-"
    wait = exchange_throttle.blocked_for(ip)
    if wait > 0:
        raise HTTPException(status_code=429, headers={"Retry-After": str(max(1, math.ceil(wait)))},
                            detail=f"Muitas tentativas com código errado. Tente de novo em {max(1, math.ceil(wait))} s.")

    now = utcnow()
    code = normalize_pairing_code(payload.codigo)
    record = db.query(PairingCode).filter(PairingCode.code_hash == pairing_code_hash(code)).first() if code else None
    usable = (record is not None and record.used_at is None and record.cancelled_at is None
              and as_utc(record.expires_at) > now and record.company is not None and record.company.active)
    if usable:
        # Uso único mesmo com duas trocas do mesmo código ao mesmo tempo: só uma consegue marcar como usado.
        claimed = db.execute(update(PairingCode)
                             .where(PairingCode.id == record.id, PairingCode.used_at.is_(None),
                                    PairingCode.cancelled_at.is_(None))
                             .values(used_at=now)).rowcount
        usable = claimed == 1
    if not usable:
        db.rollback()
        exchange_throttle.fail(ip)
        audit(db, None, "codigo_pareamento_recusado", request=request,
              company_id=record.company_id if record is not None else None)
        db.commit()
        raise HTTPException(status_code=400, detail=INVALID_CODE)

    company = record.company
    computer = (payload.computador or "").strip()[:100] or None
    token, token_hash, prefix = generate_device_token()
    device = Device(uid=record.device_uid, company_id=company.id, name=record.device_name or computer or "Computador pareado",
                    token_hash=token_hash, token_prefix=prefix, paired_at=now, computer_name=computer,
                    program_name=(payload.programa or "").strip()[:80] or None, last_ip=ip if ip != "-" else None)
    db.add(device)
    db.flush()
    audit(db, None, "aparelho_pareado", target=f"aparelho:{device.uid}", details={"computador": computer},
          request=request, company_id=company.id, user_id=record.created_by_user_id)
    db.commit()
    return TrocaOut(token=token, aparelho_uid=device.uid, empresa=EmpresaRef(uid=company.uid, nome=company.name))


@router.delete("/aparelhos/{aparelho_uid}", status_code=204)
def unpair(aparelho_uid: str, request: Request, principal: Principal = Depends(manager_roles),
           db: Session = Depends(get_db)):
    """Desconecta o computador: o token deixa de valer na hora. Código ainda não usado é anulado."""
    uid = parse_uid(aparelho_uid)
    if uid is None:
        raise HTTPException(status_code=404, detail="Aparelho não encontrado.")
    now = utcnow()
    device = db.query(Device).filter(Device.uid == uid).first()
    if device is not None:
        ensure_company_access(principal, device.company_id)
        if not principal.is_admin and device.paired_at is None:
            # Dispositivo de frota (criado pela equipe) não é desligado pelo painel.
            raise HTTPException(status_code=403, detail="Este dispositivo só é desligado pela equipe RotaGuard.")
        device.revoked_at = device.revoked_at or now
        device.current_session_uid = None
        device.testing_now = False
        audit(db, principal, "aparelho_desconectado", target=f"aparelho:{device.uid}", request=request,
              company_id=device.company_id)
        db.commit()
        return Response(status_code=204)

    record = db.query(PairingCode).filter(PairingCode.device_uid == uid).first()
    if record is None:
        raise HTTPException(status_code=404, detail="Aparelho não encontrado.")
    ensure_company_access(principal, record.company_id)
    if record.used_at is None and record.cancelled_at is None:
        record.cancelled_at = now
    audit(db, principal, "codigo_pareamento_cancelado", target=f"aparelho:{uid}", request=request,
          company_id=record.company_id)
    db.commit()
    return Response(status_code=204)
