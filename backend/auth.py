"""Login com sessão em cookie, papéis (admin, gestor, motorista) e escopo por empresa.

- Cookie httpOnly e SameSite=Lax; Secure quando a conexão é HTTPS.
- Toda requisição que altera dados precisa do cabeçalho `X-DriveSafe: 1`: um site de terceiro não consegue
  mandar esse cabeçalho sem passar pelo CORS, e o servidor não libera CORS.
- O escopo é checado no servidor: gestor e motorista nunca veem dados de outra empresa, nem se pedirem.
"""
import json
import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from backend.database import AuditLog, User, UserSession, as_utc, get_db, utcnow
from backend.security import LoginThrottle, generate_session_token, hash_password, hash_token, verify_password

logger = logging.getLogger("drivesafe.auth")

SESSION_COOKIE = "drivesafe_sessao"
SESSION_TTL = timedelta(hours=12)
SESSION_TOUCH_EVERY = timedelta(minutes=1)
CSRF_HEADER = "x-drivesafe"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
# Com senha temporária (criada pela equipe), só dá para ver quem é, trocar a senha ou sair.
PASSWORD_CHANGE_PATHS = {"/api/auth/me", "/api/auth/password", "/api/auth/logout"}

throttle = LoginThrottle()
_dummy_hash: Optional[str] = None


@dataclass
class Principal:
    user: User
    session: UserSession

    @property
    def role(self) -> str:
        return self.user.role

    @property
    def is_admin(self) -> bool:
        return self.user.role == "admin"

    @property
    def company_id(self) -> Optional[int]:
        return self.user.company_id

    @property
    def driver_id(self) -> Optional[int]:
        return self.user.driver_id


def client_ip(request: Request) -> Optional[str]:
    return request.client.host if request.client else None


def check_password_safely(user: Optional[User], password: str) -> bool:
    """Compara a senha gastando o mesmo tempo quando o usuário não existe (não revela quais logins existem)."""
    global _dummy_hash
    if user is None:
        if _dummy_hash is None:
            _dummy_hash = hash_password("senha-inexistente-para-igualar-tempo")
        verify_password(password, _dummy_hash)
        return False
    return verify_password(password, user.password_hash)


def start_session(db: Session, user: User, request: Request, response: Response) -> None:
    token, token_hash = generate_session_token()
    now = utcnow()
    db.add(UserSession(
        token_hash=token_hash, user_id=user.id, created_at=now, expires_at=now + SESSION_TTL, last_seen_at=now,
        ip=client_ip(request), user_agent=(request.headers.get("user-agent") or "")[:255],
    ))
    user.last_login_at = now
    response.set_cookie(
        SESSION_COOKIE, token, max_age=int(SESSION_TTL.total_seconds()), httponly=True, samesite="lax",
        secure=request.url.scheme == "https", path="/",
    )


def end_session(db: Session, principal: "Principal", response: Response) -> None:
    db.delete(principal.session)
    response.delete_cookie(SESSION_COOKIE, path="/")


def principal_from_token(db: Session, token: Optional[str]) -> Optional[Principal]:
    if not token:
        return None
    session = db.query(UserSession).filter(UserSession.token_hash == hash_token(token)).first()
    if session is None or as_utc(session.expires_at) <= utcnow():
        return None
    user = session.user
    if user is None or not user.active:
        return None
    if user.role != "admin" and (user.company is None or not user.company.active):
        return None
    return Principal(user, session)


def current_principal(request: Request, db: Session = Depends(get_db)) -> Principal:
    principal = principal_from_token(db, request.cookies.get(SESSION_COOKIE))
    if principal is None:
        raise HTTPException(status_code=401, detail="Sessão encerrada. Entre de novo.")
    if request.method not in SAFE_METHODS and request.headers.get(CSRF_HEADER) != "1":
        raise HTTPException(status_code=403, detail="Requisição sem o cabeçalho de segurança do app.")
    if principal.user.must_change_password and request.url.path not in PASSWORD_CHANGE_PATHS:
        raise HTTPException(status_code=403, detail="Troque a senha temporária antes de continuar.")
    now = utcnow()
    last_seen = as_utc(principal.session.last_seen_at)
    if last_seen is None or now - last_seen >= SESSION_TOUCH_EVERY:
        principal.session.last_seen_at = now
        db.commit()
    return principal


def require_roles(*roles: str):
    def dependency(principal: Principal = Depends(current_principal)) -> Principal:
        if principal.role not in roles:
            raise HTTPException(status_code=403, detail="Seu perfil não tem acesso a esta área.")
        return principal

    return dependency


def scoped_company(principal: Principal, requested: Optional[int]) -> Optional[int]:
    """Empresa que a consulta enxerga. Admin: a pedida, ou todas (None). Gestor e motorista: sempre a própria."""
    if principal.is_admin:
        return requested
    if requested is not None and requested != principal.company_id:
        raise HTTPException(status_code=403, detail="Você só acessa dados da sua empresa.")
    return principal.company_id


def ensure_company_access(principal: Principal, company_id: Optional[int]) -> None:
    """404 em vez de 403: não revela que o registro existe em outra empresa."""
    if not principal.is_admin and company_id != principal.company_id:
        raise HTTPException(status_code=404, detail="Registro não encontrado.")


def ensure_driver_access(principal: Principal, driver) -> None:
    if driver is None:
        raise HTTPException(status_code=404, detail="Motorista não encontrado.")
    ensure_company_access(principal, driver.company_id)
    if principal.role == "motorista" and principal.driver_id != driver.id:
        raise HTTPException(status_code=404, detail="Motorista não encontrado.")


def audit(db: Session, principal: Optional[Principal], action: str, target: Optional[str] = None,
          details: Optional[dict] = None, request: Optional[Request] = None, company_id: Optional[int] = None,
          user_id: Optional[int] = None) -> None:
    db.add(AuditLog(
        user_id=user_id if user_id is not None else (principal.user.id if principal else None),
        company_id=company_id if company_id is not None else (principal.company_id if principal else None),
        action=action, target=target,
        details=json.dumps(details, ensure_ascii=False) if details else None,
        ip=client_ip(request) if request else None,
    ))
