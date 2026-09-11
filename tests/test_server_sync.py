"""Servidor + app + fila do dispositivo.

Banco antigo, login (e-mail ou celular) e papéis, acessos criados só pela equipe, escopo por empresa, tokens,
reenvio, relógio, política de consentimento no heartbeat, revisão, tempo real, CSV e modo teste.

Rode com o Python que tem as dependências do servidor (servidor/requirements.txt):
    python tests/test_server_sync.py
"""
import http.cookiejar
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
SERVIDOR = PROJECT / "servidor"
sys.path.insert(0, str(PROJECT / "caixa"))
from vision.event_queue import EventStore  # noqa: E402
from vision.sync import ServerClient, SyncWorker  # noqa: E402

LEGACY_SCHEMA = """
CREATE TABLE drivers (id INTEGER NOT NULL, name VARCHAR, license_number VARCHAR, phone VARCHAR, created_at DATETIME, PRIMARY KEY (id));
CREATE TABLE vehicles (id INTEGER NOT NULL, plate VARCHAR, model VARCHAR, type VARCHAR, created_at DATETIME, PRIMARY KEY (id));
CREATE TABLE driver_vehicles (driver_id INTEGER NOT NULL, vehicle_id INTEGER NOT NULL, PRIMARY KEY (driver_id, vehicle_id));
CREATE TABLE alerts (id INTEGER NOT NULL, driver_id INTEGER, vehicle_id INTEGER, alert_type VARCHAR, risk_level INTEGER,
                     duration FLOAT, timestamp DATETIME, PRIMARY KEY (id));
INSERT INTO drivers VALUES (1, 'João Silva', 'SP123456', '11999999999', '2026-05-30 14:35:45.111578'),
                           (2, 'Maria Santos', 'RJ789012', '21988888888', '2026-05-30 14:35:45.111578');
INSERT INTO vehicles VALUES (1, 'ABC-1234', 'Volvo FH', 'Caminhão', '2026-05-30 14:35:45.111578'),
                            (2, 'DEF-5678', 'Mercedes-Benz OF', 'Ônibus', '2026-05-30 14:35:45.111578');
INSERT INTO alerts VALUES (1, 1, 1, 'possivel_sonolencia', 3, 2.0, '2026-05-30 23:13:57.923185'),
                          (2, 1, 1, 'possivel_sonolencia', 3, 2.03, '2026-05-30 23:10:23.853315');
"""
ADMIN_PASSWORD = "senha-da-equipe-2026"
TEAM_PHONE = "(11) 91234-5678"

checks = 0


def ok(message):
    global checks
    checks += 1
    print(f"OK {checks:02d} {message}")


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


work = Path(tempfile.mkdtemp(prefix="drivesafe-test-"))
database = work / "server.db"
legacy = sqlite3.connect(database)
legacy.executescript(LEGACY_SCHEMA)
legacy.close()
env = dict(os.environ, DATABASE_URL=f"sqlite:///{database}", PYTHONUTF8="1", DRIVESAFE_CONTATO_CELULAR=TEAM_PHONE)
env.pop("DRIVESAFE_SENHA_INICIAL", None)
port = free_port()
base = f"http://127.0.0.1:{port}"


class Browser:
    """Simula o app: guarda o cookie de sessão e manda o cabeçalho de segurança nas requisições."""

    def __init__(self, csrf=True):
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
        self.csrf = csrf

    def request(self, method, path, body=None, raw=None, csrf=None):
        data = raw if raw is not None else (json.dumps(body).encode("utf-8") if body is not None else None)
        request = urllib.request.Request(base + path, data=data, method=method)
        if body is not None:
            request.add_header("Content-Type", "application/json")
        if self.csrf if csrf is None else csrf:
            request.add_header("X-DriveSafe", "1")
        try:
            with self.opener.open(request, timeout=20) as response:
                return response.status, response.headers, response.read()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.headers, exc.read()

    def json(self, method, path, body=None, expect=200):
        status, _, content = self.request(method, path, body)
        assert status == expect, f"{method} {path}: esperava {expect}, veio {status}: {content[:300]!r}"
        return json.loads(content) if content else None

    def status(self, method, path, body=None, raw=None):
        return self.request(method, path, body, raw)[0]

    def cookie_header(self):
        return "; ".join(f"{cookie.name}={cookie.value}" for cookie in self.jar)


def login(identifier, password):
    browser = Browser()
    browser.json("POST", "/api/auth/login", {"login": identifier, "password": password})
    return browser


def first_access(identifier, temporary, new_password):
    browser = login(identifier, temporary)
    assert browser.json("GET", "/api/auth/me")["must_change_password"] is True
    assert browser.status("GET", "/api/alerts") == 403
    browser.json("POST", "/api/auth/password", {"current_password": temporary, "new_password": new_password}, expect=204)
    return browser


def alerts(browser, **params):
    return browser.json("GET", "/api/alerts?" + urllib.parse.urlencode(dict(params, limit=500)))


def manage(*args, password=None):
    run_env = dict(env, DRIVESAFE_SENHA_INICIAL=password) if password else env
    result = subprocess.run([sys.executable, "manage.py", *args], cwd=SERVIDOR, env=run_env,
                            capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 0, f"manage.py {args}: {result.stdout}\n{result.stderr}"
    return result.stdout


def db_value(sql, *params):
    con = sqlite3.connect(database)
    try:
        return con.execute(sql, params).fetchone()[0]
    finally:
        con.close()


log = open(work / "server.log", "w", encoding="utf-8")
server = subprocess.Popen([sys.executable, "-m", "uvicorn", "backend.main:app", "--port", str(port)],
                          cwd=SERVIDOR, env=env, stdout=log, stderr=subprocess.STDOUT)
store = None
try:
    anon = Browser(csrf=False)
    for _ in range(80):
        try:
            if anon.status("GET", "/health") == 200:
                break
        except OSError:
            time.sleep(0.5)
    else:
        raise AssertionError("servidor não subiu")

    con = sqlite3.connect(database)
    columns = {row[1] for row in con.execute("PRAGMA table_info(alerts)")}
    timestamp = con.execute("SELECT timestamp FROM alerts WHERE id = 1").fetchone()[0]
    companies = con.execute("SELECT name FROM companies").fetchall()
    review = {row[0] for row in con.execute("SELECT review_status FROM alerts")}
    con.close()
    assert {"device_id", "event_uid", "details", "received_at", "company_id", "review_status"} <= columns, columns
    assert timestamp.startswith("2026-05-31 02:13:57"), timestamp
    assert companies == [("Empresa padrão",)] and review == {"arquivado"}, (companies, review)
    ok("banco antigo migrado: colunas novas, 23:13 de Brasília virou 02:13 UTC, empresa padrão, alertas fora da revisão")

    status, headers, _ = anon.request("GET", "/health")
    assert headers["X-Content-Type-Options"] == "nosniff" and "frame-ancestors 'none'" in headers["Content-Security-Policy"]
    info = anon.json("GET", "/api/app-info")
    assert info["self_signup"] is False and info["contact"] == {
        "phone": "+55 (11) 91234-5678", "tel_url": "tel:+5511912345678", "whatsapp_url": "https://wa.me/5511912345678"}, info
    paths = anon.json("GET", "/openapi.json")["paths"]
    assert not [path for path in paths if any(word in path for word in ("register", "signup", "cadastro"))], paths
    assert anon.status("GET", "/api/devices") == 401 and anon.status("GET", "/api/alerts") == 401
    ok("sem cadastro aberto: tela de login recebe o celular da equipe; API fechada sem sessão")

    output = manage("criar-usuario", "--papel", "admin", "--nome", "Equipe Teste", "--email", "Equipe@Teste.local",
                    password=ADMIN_PASSWORD)
    assert "Senha temporária" not in output, output
    assert Browser(csrf=False).status("POST", "/api/auth/login", {"login": "equipe@teste.local", "password": ADMIN_PASSWORD}) == 403
    assert Browser().status("POST", "/api/auth/login", {"login": "equipe@teste.local", "password": "senha-errada-1"}) == 401
    admin = login("EQUIPE@teste.local", ADMIN_PASSWORD)
    me = admin.json("GET", "/api/auth/me")
    assert me["role"] == "admin" and me["email"] == "equipe@teste.local" and me["must_change_password"] is False, me
    assert admin.request("POST", "/api/companies", {"name": "Sem cabeçalho"}, csrf=False)[0] == 403
    ok("login por e-mail; sem o cabeçalho do app o login e as alterações são recusados")

    intruder = Browser()
    codes = [intruder.status("POST", "/api/auth/login", {"login": "ninguem@teste.local", "password": "x"}) for _ in range(6)]
    assert codes == [401] * 5 + [429], codes
    ok("5 senhas erradas seguidas bloqueiam novas tentativas por um tempo")

    beta = admin.json("POST", "/api/companies", {"name": "Transportadora Beta", "contact_name": "Bia",
                                                 "contact_phone": "11 98888-7777"}, expect=201)
    assert beta["contact_phone"] == "+55 (11) 98888-7777" and beta["contact_name"] == "Bia", beta
    assert admin.status("POST", "/api/users", {"name": "Sem login", "role": "gestor", "company_id": beta["id"]}) == 400
    created = admin.json("POST", "/api/users", {"name": "Gestora Beta", "phone": "(11) 98888-7777", "role": "gestor",
                                                "company_id": beta["id"]}, expect=201)
    assert created["user"]["phone"] == "+55 (11) 98888-7777" and created["user"]["email"] is None, created
    assert admin.status("POST", "/api/users", {"name": "Repetido", "phone": "11988887777", "role": "gestor",
                                               "company_id": beta["id"]}) == 409
    first_access("+55 11 98888-7777", created["temporary_password"], "gestora-beta-2026")
    gestor = login("11988887777", "gestora-beta-2026")
    ok("equipe cria o acesso por celular; senha temporária só serve para trocar a senha no primeiro acesso")

    driver_beta = gestor.json("POST", "/api/drivers", {"name": "Motorista Beta", "license_number": "BETA00001"}, expect=201)
    created = admin.json("POST", "/api/users", {"name": "Motorista Beta", "email": "mb@teste.local", "role": "motorista",
                                                "company_id": beta["id"], "driver_id": driver_beta["id"]}, expect=201)
    user_beta = created["user"]["id"]
    driver_session = first_access("mb@teste.local", created["temporary_password"], "motorista-beta-2026")
    assert gestor.status("POST", "/api/users", {"name": "X", "email": "x@teste.local", "role": "motorista",
                                                "company_id": beta["id"], "driver_id": driver_beta["id"]}) == 403
    assert gestor.status("PATCH", f"/api/users/{user_beta}", {"reset_password": True}) == 403
    assert gestor.status("PATCH", f"/api/users/{user_beta}", {"phone": "11977776666"}) == 403
    blocked = gestor.json("PATCH", f"/api/users/{user_beta}", {"active": False})
    assert blocked["user"]["active"] is False and driver_session.status("GET", "/api/auth/me") == 401
    assert gestor.status("PATCH", f"/api/users/{user_beta}", {"active": True}) == 403
    ok("gestor não cria, reativa nem altera acessos; só bloqueia, e o bloqueio derruba a sessão na hora")

    output = manage("criar-dispositivo", "--nome", "Teste", "--empresa", "1", "--veiculo", "1", "--motorista", "1")
    token = next(line.strip() for line in output.splitlines() if line.strip().startswith("dsk_"))
    device_id = int(output.split("#", 1)[1].split()[0])
    assert admin.status("POST", "/api/devices", {"name": "Beta 1", "company_id": beta["id"], "vehicle_id": 1}) == 400
    ok("manage.py criou dispositivo; a API não liga dispositivo a veículo de outra empresa")

    store = EventStore(work / "queue.db")
    for seconds in (2.1, 2.5, 3.0):
        store.add("microssono", 3, seconds, details={"fechado_s": seconds})
    assert SyncWorker(store, ServerClient(f"http://127.0.0.1:{free_port()}", token, timeout=2)).sync_once() is False
    assert store.count_pending() == 3
    assert SyncWorker(store, ServerClient(base, "dsk_errado")).sync_once() is False and store.count_pending() == 3
    ok("servidor inacessível ou token errado: eventos continuam na fila local")

    live = {"camera_ok": True, "status": {"risk_level": 1, "risk_name": "atencao", "reasons": ["piscadas longas"],
                                          "activation_mode": "enviar", "activation_index": 0.4,
                                          "activation_confidence": "baixa", "fps": 24.5}}
    policies = []
    worker = SyncWorker(store, ServerClient(base, token), status_provider=lambda: live, policy_handler=policies.append)
    assert worker.sync_once() is True and store.count_pending() == 0
    page = alerts(admin, device_id=device_id)
    assert page["total"] == 3 and all(a["vehicle"]["name"] == "ABC-1234" and a["driver"]["id"] == 1 for a in page["items"])
    assert all(a["review_status"] == "pendente" for a in page["items"]), page
    ok("eventos chegam com empresa, veículo e motorista, e entram na fila de revisão")

    con = sqlite3.connect(work / "queue.db")
    con.execute("UPDATE events SET status = 'pending'")
    con.commit()
    con.close()
    assert worker.sync_once() is True and alerts(admin, device_id=device_id)["total"] == 3
    ok("reenviar os mesmos eventos não duplica")

    uid = store.add("microssono", 3, 2.2)
    con = sqlite3.connect(work / "queue.db")
    con.execute("UPDATE events SET occurred_at = '1970-01-01T00:00:00.000+00:00' WHERE event_uid = ?", (uid,))
    con.commit()
    con.close()
    assert worker.sync_once() is True
    fixed = next(a for a in alerts(admin, device_id=device_id)["items"] if a["duration"] == 2.2)
    assert fixed["timestamp"].startswith(time.strftime("%Y-", time.gmtime())), fixed
    ok("relógio do dispositivo errado (1970) é corrigido pelo servidor")

    good, bad = store.add("microssono", 3, 2.3), store.add("microssono", 3, 2.4)
    con = sqlite3.connect(work / "queue.db")
    con.execute("UPDATE events SET alert_type = 'TIPO-INVALIDO' WHERE event_uid = ?", (bad,))
    con.commit()
    con.close()
    assert worker.sync_once() is True
    con = sqlite3.connect(work / "queue.db")
    statuses = dict(con.execute("SELECT event_uid, status FROM events WHERE event_uid IN (?, ?)", (good, bad)))
    con.close()
    assert statuses == {good: "sent", bad: "rejected"}, statuses
    ok("evento inválido é isolado e não trava a fila")

    worker._next_heartbeat = 0
    assert worker.sync_once() is True
    device = next(d for d in admin.json("GET", "/api/devices?company_id=1") if d["id"] == device_id)
    assert device["online"] and device["camera_ok"] is True and device["pending_events"] == 0, device
    assert device["live"]["risk_level"] == 1 and device["live"]["activation_index"] is None, device["live"]
    assert policies[-1] == {"driver_id": 1, "profile_consent": False, "activation_mode": "local",
                            "status_interval_s": 15}, policies
    ok("heartbeat: online e estado ao vivo; sinais de ativação descartados com a empresa em modo local")

    admin.json("PATCH", "/api/companies/1", {"activation_policy": "enviar"})
    worker._next_heartbeat = 0
    assert worker.sync_once() is True and policies[-1]["activation_mode"] == "local", policies[-1]
    for kind in ("perfil_entre_viagens", "sinais_ativacao_envio"):
        admin.json("POST", "/api/drivers/1/consents", {"kind": kind, "granted": True, "channel": "admin"}, expect=201)
    worker._next_heartbeat = 0
    assert worker.sync_once() is True
    assert policies[-1]["profile_consent"] is True and policies[-1]["activation_mode"] == "enviar", policies[-1]
    device = next(d for d in admin.json("GET", "/api/devices?company_id=1") if d["id"] == device_id)
    assert device["live"]["activation_index"] == 0.4, device["live"]
    admin.json("POST", "/api/drivers/1/consents", {"kind": "sinais_ativacao_envio", "granted": False, "channel": "admin"},
               expect=201)
    worker._next_heartbeat = 0
    assert worker.sync_once() is True and policies[-1]["activation_mode"] == "local", policies[-1]
    ok("envio de sinais de ativação só com política da empresa E consentimento; revogar volta para local")

    first_alert = page["items"][0]["id"]
    assert gestor.status("GET", "/api/devices?company_id=1") == 403 and gestor.json("GET", "/api/devices") == []
    assert gestor.status("GET", "/api/drivers/1") == 404 and gestor.status("GET", "/api/drivers/1/export") == 404
    assert gestor.status("PATCH", f"/api/alerts/{first_alert}/review", {"status": "confirmado"}) == 404
    assert alerts(gestor)["total"] == 0 and gestor.status("PATCH", "/api/companies/1", {"activation_policy": "local"}) == 404
    ok("gestor da Beta não vê nem altera nada da outra empresa")

    reviewed = admin.json("PATCH", f"/api/alerts/{first_alert}/review", {"status": "orientado", "note": "Conversa feita"})
    assert reviewed["review_status"] == "orientado" and reviewed["reviewed_by"] == "Equipe Teste", reviewed
    ok("revisão registra decisão, nota e quem revisou")

    created = admin.json("POST", "/api/users", {"name": "João Silva", "phone": "(21) 97777-6666", "role": "motorista",
                                                "company_id": 1, "driver_id": 1}, expect=201)
    joao = first_access("21977776666", created["temporary_password"], "joao-silva-2026")
    mine = alerts(joao)
    assert mine["total"] >= 5 and all(a["driver"]["id"] == 1 for a in mine["items"]), mine["total"]
    assert joao.status("GET", "/api/devices") == 403 and joao.status("GET", "/api/drivers/2") == 404
    assert joao.status("GET", "/api/drivers/1/export") == 200 and joao.status("GET", "/api/drivers/2/export") == 404
    assert joao.status("POST", "/api/drivers/1/consents", {"kind": "monitoramento", "granted": True, "channel": "admin"}) == 400
    joao.json("POST", "/api/drivers/1/consents", {"kind": "monitoramento", "granted": True, "channel": "app_motorista"},
              expect=201)
    ok("motorista vê só os próprios alertas, exporta os próprios dados e registra consentimento pelo app")

    try:
        from websockets.exceptions import InvalidStatus
        from websockets.sync.client import connect
    except ImportError:
        print("-- tempo real não testado (pacote websockets ausente neste Python)")
    else:
        def refused(**kwargs):
            try:
                connect(f"ws://127.0.0.1:{port}/ws", open_timeout=5, **kwargs).close()
            except InvalidStatus as exc:
                return exc.response.status_code == 403
            return False

        def next_of_type(ws, kind, timeout):
            deadline = time.monotonic() + timeout
            while True:
                message = json.loads(ws.recv(timeout=max(0.05, deadline - time.monotonic())))
                if message["type"] == kind:
                    return message

        assert refused() and refused(origin="http://site-malicioso.example",
                                     additional_headers={"Cookie": admin.cookie_header()})
        with connect(f"ws://127.0.0.1:{port}/ws", open_timeout=5, additional_headers={"Cookie": admin.cookie_header()}) as ws_admin, \
                connect(f"ws://127.0.0.1:{port}/ws", open_timeout=5, additional_headers={"Cookie": gestor.cookie_header()}) as ws_gestor:
            store.add("sono", 4, 3.1)
            assert worker.sync_once() is True
            message = next_of_type(ws_admin, "alert", 5)
            assert message["data"]["alert_type"] == "sono" and message["data"]["company"]["id"] == 1, message
            try:
                leaked = next_of_type(ws_gestor, "alert", 1.5)
            except TimeoutError:
                leaked = None
            assert leaked is None, leaked
        ok("tempo real: equipe recebe o alerta novo; gestor de outra empresa não; sem sessão ou outra origem, recusado")

    manage("vincular-dispositivo", str(device_id), "--veiculo", "2", "--motorista", "0")
    store.add("microssono", 3, 2.6)
    assert worker.sync_once() is True
    latest = next(a for a in alerts(admin, device_id=device_id)["items"] if a["duration"] == 2.6)
    assert latest["vehicle"]["name"] == "DEF-5678" and latest["driver"] is None, latest
    ok("troca de veículo vale para os próximos alertas")

    assert alerts(admin, start="2026-05-30", end="2026-05-30")["total"] == 2
    ok("filtro por data usa o dia no fuso local")

    status, headers, body = admin.request("GET", f"/api/alerts/export.csv?device_id={device_id}")
    lines = body.decode("utf-8-sig").strip().splitlines()
    assert status == 200 and body.startswith(b"\xef\xbb\xbf") and "attachment" in headers["Content-Disposition"]
    assert lines[0].startswith("ID;Data e hora") and "2,60" in body.decode("utf-8-sig") and "Motorista orientado" in body.decode("utf-8-sig")
    assert db_value("SELECT count(*) FROM audit_log WHERE action = 'alertas_exportados'") == 1
    assert db_value("SELECT count(*) FROM audit_log WHERE action = 'login_recusado'") >= 6
    ok(f"CSV para Excel ({len(lines) - 1} linhas) e trilha de auditoria de exportação e logins recusados")

    overview = admin.json("GET", "/api/overview?company_id=1")
    assert overview["devices_online"] == 1 and overview["alerts_today"] >= 1 and overview["to_review"] >= 1, overview
    fleet = admin.json("GET", "/api/fleet?company_id=1")
    assert len(fleet) == 1 and fleet[0]["alerts_today"] >= 1 and len(fleet[0]["risk_hours_today"]) == 24, fleet
    ok("visão geral e frota ao vivo")

    state = admin.json("GET", "/api/test-mode")
    assert "available" in state and state["running"] is False, state
    assert gestor.status("GET", "/api/test-mode") == 403
    assert admin.status("PUT", "/api/test-mode/analyses?name=nota.txt", raw=b"abc") == 400
    assert admin.status("PUT", "/api/test-mode/analyses?name=viagem.mp4", raw=b"") == 400
    ok("modo teste só para a equipe; análise recusa arquivo que não é vídeo e arquivo vazio")

    admin.json("POST", f"/api/devices/{device_id}/revoke")
    worker._next_heartbeat = 0
    assert worker.sync_once() is False
    ok("dispositivo revogado é recusado")

    assert admin.status("POST", "/api/auth/logout") == 204 and admin.status("GET", "/api/auth/me") == 401
    ok("sair encerra a sessão")

    output = manage("demo", "--com-alertas")
    assert "Empresa de demonstração" in output and "alertas de exemplo" in output, output
    listing = manage("usuarios")
    assert "+55 (11) 98888-7777" in listing and "equipe@teste.local" in listing, listing
    ok("manage.py demo e lista de usuários com login por e-mail ou celular")

    print(f"\nTODOS OS {checks} TESTES PASSARAM (Python {sys.version.split()[0]})")
except Exception:
    print((work / "server.log").read_text(encoding="utf-8", errors="replace")[-4000:])
    raise
finally:
    if store is not None:
        store.close()
    server.terminate()
    server.wait(10)
    log.close()
    shutil.rmtree(work, ignore_errors=True)
