"""Login com sessão em cookie (app web) ou token no cabeçalho (painel executável), papéis e escopo por empresa.

- Cookie httpOnly e SameSite=Lax; Secure quando a conexão é HTTPS.
- Toda requisição com cookie que altera dados precisa do cabeçalho `X-DriveSafe: 1`: um site de terceiro não consegue
  mandar esse cabeçalho sem passar pelo CORS, e o servidor não libera CORS.
- Painel executável (spec 026): `Authorization: Bearer <token de sessão>`. Navegador nenhum manda esse cabeçalho
  sozinho, então não há CSRF a conferir. Token de aparelho (`dsk_…`) nunca lê nada: 403.
- O escopo é checado no servidor: gestor e motorista nunca veem dados de outra empresa, nem se pedirem.
"""
import ipaddress
import json
import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from backend import config
from backend.database import AuditLog, User, UserSession, as_utc, get_db, utcnow
from backend.security import (
    TOKEN_PREFIX, LoginThrottle, generate_session_token, hash_password, hash_token, verify_password,
)

logger = logging.getLogger("drivesafe.auth")

SESSION_COOKIE = "drivesafe_sessao"
SESSION_TTL = timedelta(hours=12)
PANEL_CLIENT = "painel"
PANEL_SESSION_TTL = timedelta(days=config.PANEL_SESSION_DAYS)
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


def _parse_ip(value: str):
    try:
        return ipaddress.ip_address(value.strip())
    except ValueError:
        return None


# Redes de onde um proxy da casa (Caddy na rede docker, ou o próprio computador) fala com a central. Lista explícita:
# o is_private do Python também marca faixas de documentação e de CGNAT, que são endereços de cliente.
_INTERNAL_NETWORKS = tuple(ipaddress.ip_network(network) for network in (
    "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "127.0.0.0/8", "169.254.0.0/16", "::1/128", "fc00::/7",
    "fe80::/10",
))


def _is_internal(address) -> bool:
    mapped = getattr(address, "ipv4_mapped", None)
    if mapped is not None:
        address = mapped
    return any(address in network for network in _INTERNAL_NETWORKS if network.version == address.version)


def client_ip(request: Request) -> Optional[str]:
    """IP de quem fez a requisição. Atrás do Caddy (rede docker privada) vale o X-Forwarded-For; vindo direto da
    internet, o cabeçalho é ignorado (qualquer um poderia inventar). Do X-Forwarded-For vale o último endereço que não
    é de rede interna: os proxies da casa acrescentam no fim, o que vem antes é do cliente e pode ser falso."""
    peer = request.client.host if request.client else None
    peer_address = _parse_ip(peer) if peer else None
    if peer_address is None or not _is_internal(peer_address):
        return peer
    forwarded = [_parse_ip(part) for part in (request.headers.get("x-forwarded-for") or "").split(",")]
    forwarded = [address for address in forwarded if address is not None]
    for address in reversed(forwarded):
        if not _is_internal(address):
            return str(address)
    return str(forwarded[0]) if forwarded else peer


def bearer_token(request: Request) -> Optional[str]:
    scheme, _, value = (request.headers.get("authorization") or "").partition(" ")
    if scheme.lower() != "bearer" or not value.strip():
        return None
    return value.strip()


def check_password_safely(user: Optional[User], password: str) -> bool:
    """Compara a senha gastando o mesmo tempo quando o usuário não existe (não revela quais logins existem)."""
    global _dummy_hash
    if user is None:
        if _dummy_hash is None:
            _dummy_hash = hash_password("senha-inexistente-para-igualar-tempo")
        verify_password(password, _dummy_hash)
        return False
    return verify_password(password, user.password_hash)


def start_session(db: Session, user: User, request: Request, response: Response, client: Optional[str] = None):
    """Abre a sessão. App web: token só no cookie. Painel (client="painel"): devolve (token, expira_em) para ir no
    corpo da resposta, sem cookie."""
    token, token_hash = generate_session_token()
    now = utcnow()
    ttl = PANEL_SESSION_TTL if client == PANEL_CLIENT else SESSION_TTL
    db.add(UserSession(
        token_hash=token_hash, user_id=user.id, created_at=now, expires_at=now + ttl, last_seen_at=now,
        ip=client_ip(request), user_agent=(request.headers.get("user-agent") or "")[:255], client=client,
    ))
    user.last_login_at = now
    if client == PANEL_CLIENT:
        return token, now + ttl
    response.set_cookie(
        SESSION_COOKIE, token, max_age=int(SESSION_TTL.total_seconds()), httponly=True, samesite="lax",
        secure=request.url.scheme == "https", path="/",
    )
    return None, None


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
    bearer = bearer_token(request)
    if bearer is not None and bearer.startswith(TOKEN_PREFIX):
        raise HTTPException(status_code=403, detail="Token de aparelho só envia dados. Para ler, entre com um usuário.")
    principal = principal_from_token(db, bearer if bearer is not None else request.cookies.get(SESSION_COOKIE))
    if principal is None:
        raise HTTPException(status_code=401, detail="Sessão encerrada. Entre de novo.",
                            headers={"WWW-Authenticate": "Bearer"} if bearer is not None else None)
    if bearer is None and request.method not in SAFE_METHODS and request.headers.get(CSRF_HEADER) != "1":
        raise HTTPException(status_code=403, detail="Requisição sem o cabeçalho de segurança do app.")
    if principal.user.must_change_password and request.url.path not in PASSWORD_CHANGE_PATHS:
        raise HTTPException(status_code=403, detail="Troque a senha temporária antes de continuar.")
    now = utcnow()
    last_seen = as_utc(principal.session.last_seen_at)
    if last_seen is None or now - last_seen >= SESSION_TOUCH_EVERY:
        principal.session.last_seen_at = now
        if principal.session.client == PANEL_CLIENT:
            # Painel aberto todo dia não pede a senha de novo; parado 30 dias, pede.
            principal.session.expires_at = now + PANEL_SESSION_TTL
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
