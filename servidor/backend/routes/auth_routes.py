"""Entrar, sair, quem sou eu e troca de senha."""
import math

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.auth import (
    CSRF_HEADER, Principal, audit, check_password_safely, client_ip, current_principal, end_session, start_session,
    throttle,
)
from backend.database import User, UserSession, get_db
from backend.identifiers import normalize_email, normalize_phone
from backend.schemas import LoginIn, MeOut, PasswordChangeIn
from backend.security import hash_password, password_problem, verify_password
from backend.serializers import me_out

router = APIRouter(prefix="/api/auth", tags=["sessão"])


@router.post("/login", response_model=MeOut)
def login(payload: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    if request.headers.get(CSRF_HEADER) != "1":
        raise HTTPException(status_code=403, detail="Requisição sem o cabeçalho de segurança do app.")
    typed = payload.login.strip()
    if "@" in typed:
        identifier = normalize_email(typed)
        lookup = func.lower(User.email) == identifier
    else:
        identifier = normalize_phone(typed)
        lookup = (User.phone == identifier) if identifier else None
    key = f"{client_ip(request) or '-'}|{identifier or typed.lower()}"
    wait = throttle.blocked_for(key)
    if wait > 0:
        raise HTTPException(status_code=429,
                            detail=f"Muitas tentativas erradas. Tente de novo em {max(1, math.ceil(wait / 60))} min.")

    user = db.query(User).filter(lookup).first() if lookup is not None else None
    allowed = (check_password_safely(user, payload.password) and user.active
               and (user.role == "admin" or (user.company is not None and user.company.active)))
    if not allowed:
        throttle.fail(key)
        audit(db, None, "login_recusado", target=(identifier or typed)[:120], request=request,
              company_id=user.company_id if user else None, user_id=user.id if user else None)
        db.commit()
        raise HTTPException(status_code=401, detail="Login ou senha incorretos.")

    throttle.clear(key)
    start_session(db, user, request, response)
    audit(db, None, "login", target=identifier, request=request, company_id=user.company_id, user_id=user.id)
    db.commit()
    return me_out(user)


@router.post("/logout", status_code=204)
def logout(response: Response, principal: Principal = Depends(current_principal), db: Session = Depends(get_db)):
    end_session(db, principal, response)
    db.commit()


@router.get("/me", response_model=MeOut)
def me(principal: Principal = Depends(current_principal)):
    return me_out(principal.user)


@router.post("/password", status_code=204)
def change_password(payload: PasswordChangeIn, request: Request, principal: Principal = Depends(current_principal),
                    db: Session = Depends(get_db)):
    user = principal.user
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="A senha atual não confere.")
    problem = password_problem(payload.new_password)
    if problem:
        raise HTTPException(status_code=400, detail=problem)
    user.password_hash = hash_password(payload.new_password)
    user.must_change_password = False
    # Outras sessões abertas com a senha antiga são encerradas.
    (db.query(UserSession).filter(UserSession.user_id == user.id, UserSession.id != principal.session.id)
     .delete(synchronize_session=False))
    audit(db, principal, "senha_trocada", target=user.email or user.phone, request=request)
    db.commit()
