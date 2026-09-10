"""Servidor central DriveSafe AI: API, app instalável (PWA) e avisos em tempo real."""
import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from urllib.parse import urlparse

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.datastructures import MutableHeaders

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import config  # noqa: E402
from backend.auth import SESSION_COOKIE, principal_from_token  # noqa: E402
from backend.database import Device, SessionLocal, User, init_db  # noqa: E402
from backend.identifiers import format_phone, normalize_phone  # noqa: E402
from backend.live import Subscriber, hub  # noqa: E402
from backend.routes import admin, alerts, auth_routes, device_api, fleet, people, test_mode  # noqa: E402
from backend.schemas import AppInfoOut, ContactOut  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("drivesafe.api")

CSP = ("default-src 'self'; img-src 'self' data: blob:; style-src 'self'; script-src 'self'; font-src 'self'; "
       "connect-src 'self' {websocket}; manifest-src 'self'; worker-src 'self'; base-uri 'self'; form-action 'self'; "
       "frame-ancestors 'none'; object-src 'none'")
DOCS_PATHS = ("/docs", "/redoc", "/openapi.json")


class SecurityHeaders:
    """Cabeçalhos de segurança em toda resposta HTTP (sem bufferizar o vídeo ao vivo do modo teste)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        host = dict(scope.get("headers") or []).get(b"host", b"").decode("latin-1")

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers.setdefault("X-Content-Type-Options", "nosniff")
                headers.setdefault("Referrer-Policy", "same-origin")
                headers.setdefault("X-Frame-Options", "DENY")
                headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
                if not path.startswith(DOCS_PATHS):
                    websocket = f"ws://{host} wss://{host}" if host else ""
                    headers.setdefault("Content-Security-Policy", CSP.format(websocket=websocket))
            await send(message)

        await self.app(scope, receive, send_with_headers)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    hub.attach_loop(asyncio.get_running_loop())
    db = SessionLocal()
    try:
        if db.query(User.id).first() is None:
            logger.warning('Nenhum usuário cadastrado. Crie o primeiro administrador: python manage.py criar-usuario '
                           '--papel admin --nome "Seu nome" --email voce@exemplo.com (ou --celular "(11) 98765-4321")')
        if not normalize_phone(config.CONTACT_PHONE):
            logger.warning("DRIVESAFE_CONTATO_CELULAR não definido: a tela de login não mostra o celular da equipe.")
        if db.query(Device.id).first() is None:
            logger.warning("Nenhum dispositivo cadastrado. Crie pelo app (Dispositivos) ou com manage.py criar-dispositivo.")
    finally:
        db.close()
    yield
    test_mode.shutdown()


app = FastAPI(title="DriveSafe AI", version=config.APP_VERSION, lifespan=lifespan)
app.add_middleware(SecurityHeaders)
for router in (device_api.router, auth_routes.router, admin.router, people.router, fleet.router, alerts.router,
               test_mode.router):
    app.include_router(router)


@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok", "version": config.APP_VERSION}


@app.get("/api/app-info", response_model=AppInfoOut, tags=["sessão"])
def app_info():
    """Público: a tela de login não tem cadastro, só o celular da equipe para pedir acesso."""
    phone = normalize_phone(config.CONTACT_PHONE)
    contact = None
    if phone:
        contact = ContactOut(phone=format_phone(phone), tel_url=f"tel:+{phone}",
                             whatsapp_url=f"https://wa.me/{phone}" if config.CONTACT_WHATSAPP else None)
    return AppInfoOut(version=config.APP_VERSION, timezone=config.TIMEZONE, self_signup=False, contact=contact)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    origin = websocket.headers.get("origin")
    if origin and urlparse(origin).netloc != websocket.headers.get("host"):
        await websocket.close(code=4403)
        return
    db = SessionLocal()
    try:
        principal = principal_from_token(db, websocket.cookies.get(SESSION_COOKIE))
        subscriber = None
        if principal is not None and not principal.user.must_change_password:
            subscriber = Subscriber(websocket, principal.role, principal.company_id, principal.driver_id)
    finally:
        db.close()
    if subscriber is None:
        await websocket.close(code=4401)
        return
    await websocket.accept()
    hub.add(subscriber)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        hub.remove(subscriber)


# ---------- app instalável ----------

def webapp_file(name: str, media_type: str, headers: dict | None = None) -> FileResponse:
    return FileResponse(os.path.join(config.WEBAPP_DIR, name), media_type=media_type, headers=headers)


@app.get("/", include_in_schema=False)
def index():
    return webapp_file("index.html", "text/html; charset=utf-8", {"Cache-Control": "no-cache"})


@app.get("/manifest.webmanifest", include_in_schema=False)
def manifest():
    return webapp_file("manifest.webmanifest", "application/manifest+json", {"Cache-Control": "no-cache"})


@app.get("/sw.js", include_in_schema=False)
def service_worker():
    return webapp_file("sw.js", "text/javascript; charset=utf-8",
                       {"Cache-Control": "no-cache", "Service-Worker-Allowed": "/"})


@app.get("/offline.html", include_in_schema=False)
def offline():
    return webapp_file("offline.html", "text/html; charset=utf-8")


app.mount("/assets", StaticFiles(directory=os.path.join(config.WEBAPP_DIR, "assets"), check_dir=False), name="assets")
