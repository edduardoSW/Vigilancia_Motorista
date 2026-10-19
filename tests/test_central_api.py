"""Central na VPS (spec 026): pareamento por código, sessões, trechos e novidades para o painel executável.

Critérios CEN-01 a CEN-12, mais migração de banco da versão 0.3.0, login do painel com token, retenção de trechos e
desconexão de aparelho. Sobe o servidor de verdade (uvicorn) com banco e pasta de trechos temporários.

Rode com o Python que tem as dependências do servidor (servidor/requirements.txt):
    python tests/test_central_api.py
"""
import base64
import hashlib
import http.client
import io
import json
import os
import re
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
import uuid
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
SERVIDOR = PROJECT / "servidor"

ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
TOKEN_ANTIGO = "dsk_tokenAntigoDoRaspberry0123456789abcdefghijk"
SENHA_ANA = "gestora-ana-central-2026"
SENHA_BETO = "gestor-beto-central-2026"
SENHA_EQUIPE = "equipe-rotaguard-2026"
SENHA_MOTORISTA = "motorista-ana-2026"
LIMITE_TRECHO = 25 * 1024 * 1024
TRECHOS_POR_DIA = 5  # teto diário por aparelho, baixo só no teste (padrão 100)

# Esquema exato da versão 0.3.0 do servidor (antes da spec 026), com dados que precisam sobreviver à migração.
ESQUEMA_V030 = f"""
CREATE TABLE companies (id INTEGER NOT NULL, name VARCHAR(120) NOT NULL, document VARCHAR(20), contact_name VARCHAR(120),
    contact_phone VARCHAR(20), activation_policy VARCHAR(12) NOT NULL, active BOOLEAN NOT NULL, created_at DATETIME NOT NULL,
    PRIMARY KEY (id));
CREATE TABLE drivers (id INTEGER NOT NULL, company_id INTEGER, name VARCHAR, license_number VARCHAR, phone VARCHAR,
    created_at DATETIME, PRIMARY KEY (id), FOREIGN KEY(company_id) REFERENCES companies (id));
CREATE TABLE vehicles (id INTEGER NOT NULL, company_id INTEGER, plate VARCHAR, model VARCHAR, type VARCHAR, created_at DATETIME,
    PRIMARY KEY (id), FOREIGN KEY(company_id) REFERENCES companies (id));
CREATE TABLE driver_vehicles (driver_id INTEGER NOT NULL, vehicle_id INTEGER NOT NULL, PRIMARY KEY (driver_id, vehicle_id));
CREATE TABLE devices (id INTEGER NOT NULL, company_id INTEGER, name VARCHAR(100) NOT NULL, token_hash VARCHAR(64) NOT NULL,
    token_prefix VARCHAR(16) NOT NULL, vehicle_id INTEGER, driver_id INTEGER, hostname VARCHAR(255), platform VARCHAR(255),
    software_version VARCHAR(32), camera_ok BOOLEAN, pending_events INTEGER NOT NULL, last_seen_at DATETIME,
    last_ip VARCHAR(45), created_at DATETIME NOT NULL, revoked_at DATETIME, live_status TEXT, risk_level INTEGER,
    status_at DATETIME, fps FLOAT, latency_p95_ms FLOAT, PRIMARY KEY (id));
CREATE TABLE alerts (id INTEGER NOT NULL, company_id INTEGER, driver_id INTEGER, vehicle_id INTEGER, device_id INTEGER,
    event_uid VARCHAR(36), alert_type VARCHAR, risk_level INTEGER, duration FLOAT, details TEXT, timestamp DATETIME,
    received_at DATETIME, review_status VARCHAR(16), reviewed_by_user_id INTEGER, reviewed_at DATETIME, review_note TEXT,
    PRIMARY KEY (id));
CREATE TABLE users (id INTEGER NOT NULL, email VARCHAR(254), phone VARCHAR(20), name VARCHAR(120) NOT NULL,
    password_hash VARCHAR(255) NOT NULL, role VARCHAR(12) NOT NULL, company_id INTEGER, driver_id INTEGER,
    active BOOLEAN NOT NULL, must_change_password BOOLEAN NOT NULL, created_at DATETIME NOT NULL, last_login_at DATETIME,
    PRIMARY KEY (id));
CREATE TABLE user_sessions (id INTEGER NOT NULL, token_hash VARCHAR(64) NOT NULL, user_id INTEGER NOT NULL,
    created_at DATETIME NOT NULL, expires_at DATETIME NOT NULL, last_seen_at DATETIME, ip VARCHAR(45),
    user_agent VARCHAR(255), PRIMARY KEY (id));
CREATE TABLE consents (id INTEGER NOT NULL, driver_id INTEGER NOT NULL, kind VARCHAR(40) NOT NULL, granted BOOLEAN NOT NULL,
    term_version VARCHAR(20) NOT NULL, channel VARCHAR(20) NOT NULL, recorded_at DATETIME NOT NULL,
    recorded_by_user_id INTEGER, note TEXT, PRIMARY KEY (id));
CREATE TABLE audit_log (id INTEGER NOT NULL, at DATETIME NOT NULL, user_id INTEGER, company_id INTEGER,
    action VARCHAR(60) NOT NULL, target VARCHAR(120), details TEXT, ip VARCHAR(45), PRIMARY KEY (id));
CREATE UNIQUE INDEX ix_alerts_event_uid ON alerts (event_uid);
CREATE UNIQUE INDEX ix_devices_token_hash ON devices (token_hash);
CREATE UNIQUE INDEX ix_users_email ON users (email);
CREATE UNIQUE INDEX ix_users_phone ON users (phone);
CREATE UNIQUE INDEX ix_user_sessions_token_hash ON user_sessions (token_hash);
INSERT INTO companies VALUES (1, 'Transportadora Antiga', NULL, NULL, NULL, 'local', 1, '2026-09-01 10:00:00.000000');
INSERT INTO devices (id, company_id, name, token_hash, token_prefix, pending_events, created_at)
    VALUES (1, 1, 'Raspberry antigo', '{hashlib.sha256(TOKEN_ANTIGO.encode()).hexdigest()}', 'dsk_tokenA', 0,
            '2026-09-01 10:00:00.000000');
INSERT INTO alerts VALUES (1, 1, NULL, NULL, 1, '11111111-1111-4111-8111-111111111111', 'microssono', 3, 2.0,
    '{{"fechado_s": 2.0, "bpm": 71}}', '2026-09-30 12:00:00.000000', '2026-09-30 12:00:01.000000', 'arquivado',
    NULL, NULL, NULL);
"""

checks = 0
segredos = []  # nada disto pode aparecer no registro do servidor


def ok(message):
    global checks
    checks += 1
    print(f"OK {checks:02d} {message}")


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def agora():
    return datetime.now(timezone.utc)


def iso(value):
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def ler_iso(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def sql_utc(value):
    """Formato em que o SQLAlchemy grava datas no SQLite (UTC sem fuso)."""
    return value.astimezone(timezone.utc).replace(tzinfo=None).isoformat(" ", timespec="microseconds")


def novo_uid():
    return uuid.uuid4().hex


def longo(path):
    """No Windows, caminho com mais de 260 caracteres só abre com o prefixo \\\\?\\ (sem LongPathsEnabled)."""
    return Path("\\\\?\\" + os.path.abspath(path)) if os.name == "nt" else Path(path)


work = Path(tempfile.mkdtemp(prefix="rotaguard-central-"))
database = work / "central.db"
# Pasta funda de propósito: com os dois uids, o caminho do trecho passa de 260 caracteres (bug visto no Windows).
pasta_trechos = work / ("pasta-funda-" + "x" * 50) / ("y" * 60) / ("z" * 60) / "trechos"
legado = sqlite3.connect(database)
legado.executescript(ESQUEMA_V030)
legado.close()

env = dict(os.environ, DATABASE_URL=f"sqlite:///{database}", PYTHONUTF8="1", DRIVESAFE_TRECHOS_DIR=str(pasta_trechos),
           DRIVESAFE_SEGREDO_ARQUIVO=str(work / "segredo-central.key"),
           DRIVESAFE_TRECHOS_POR_DIA=str(TRECHOS_POR_DIA))
env.pop("DRIVESAFE_SENHA_INICIAL", None)
env.pop("DRIVESAFE_SEGREDO_CENTRAL", None)
port = free_port()
base = f"http://127.0.0.1:{port}"


def call(method, path, body=None, raw=None, headers=None, token=None, timeout=60):
    data = raw if raw is not None else (json.dumps(body).encode("utf-8") if body is not None else None)
    request = urllib.request.Request(base + path, data=data, method=method)
    if body is not None:
        request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    for name, value in (headers or {}).items():
        request.add_header(name, value)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.headers, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers, exc.read()


def jcall(method, path, body=None, expect=200, **kwargs):
    status, _, content = call(method, path, body, **kwargs)
    assert status == expect, f"{method} {path}: esperava {expect}, veio {status}: {content[:400]!r}"
    return json.loads(content) if content else None


def status_of(method, path, body=None, **kwargs):
    return call(method, path, body, **kwargs)[0]


def manage(*args, password=None, expect_ok=True):
    run_env = dict(env, DRIVESAFE_SENHA_INICIAL=password) if password else env
    result = subprocess.run([sys.executable, "manage.py", *args], cwd=SERVIDOR, env=run_env, capture_output=True,
                            text=True, encoding="utf-8")
    if expect_ok:
        assert result.returncode == 0, f"manage.py {args}: {result.stdout}\n{result.stderr}"
    return result


def db_rows(sql, *params):
    con = sqlite3.connect(database)
    con.row_factory = sqlite3.Row
    try:
        return con.execute(sql, params).fetchall()
    finally:
        con.close()


def db_exec(sql, *params):
    con = sqlite3.connect(database)
    try:
        con.execute(sql, params)
        con.commit()
    finally:
        con.close()


def login_painel(login, password, via="cabecalho"):
    headers = {"X-RotaGuard-Cliente": "painel"} if via == "cabecalho" else {}
    body = {"login": login, "password": password}
    if via == "corpo":
        body["token"] = True
    status, response_headers, content = call("POST", "/api/auth/login", body, headers=headers)
    assert status == 200, f"login {login}: {status} {content[:300]!r}"
    data = json.loads(content)
    assert data.get("token") and "set-cookie" not in {key.lower() for key in response_headers.keys()}, data
    segredos.append(data["token"])
    return data


def gerar_codigo(token, nome="Notebook da Ana", **extra):
    return jcall("POST", "/api/pareamento/codigos", {"nome": nome, **extra}, expect=201, token=token)


def trocar(codigo, ip, computador="Notebook da Ana", programa="RotaGuard Script 0.9"):
    return call("POST", "/api/pareamento/trocar", {"codigo": codigo, "computador": computador, "programa": programa},
                headers={"X-Forwarded-For": ip})


def novidades(token, desde="", limite=500, **extra):
    query = urllib.parse.urlencode({"desde": desde, "limite": limite, **extra})
    return jcall("GET", f"/api/sync/novidades?{query}", token=token)


def heartbeat(token, status=None):
    payload = {"device": {"hostname": "notebook-ana", "software_version": "0.9"}, "camera_ok": True}
    if status is not None:
        payload["status"] = status
    return call("POST", "/api/devices/heartbeat", payload, token=token)


def enviar_eventos(token, *events):
    return jcall("POST", "/api/events", {"device": {"hostname": "notebook-ana"}, "events": list(events)}, token=token)


def evento(alert_type="microssono", details=None, risk=3, duration=1.4):
    return {"event_uid": str(uuid.uuid4()), "alert_type": alert_type, "risk_level": risk, "duration": duration,
            "occurred_at": iso(agora()), "details": details or {}}


def conteudo(formato, tamanho=3000):
    if formato == "mp4":
        return b"\x00\x00\x00\x20ftypisom" + os.urandom(tamanho)
    if formato == "webm":
        return b"\x1a\x45\xdf\xa3" + os.urandom(tamanho)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as clip:
        clip.writestr("indice.json", json.dumps({"quadros": ["0001.jpg"], "fps": 15}))
        clip.writestr("0001.jpg", os.urandom(tamanho))
    return buffer.getvalue()


def cabecalhos_trecho(formato, content, sessao, sha=None, tipo="microssono", evento_uid=None):
    headers = {"X-RotaGuard-Sessao": sessao, "X-RotaGuard-Tipo": tipo, "X-RotaGuard-Inicio": "2026-10-19T12:00:00Z",
               "X-RotaGuard-Fim": "2026-10-19T12:00:16Z", "X-RotaGuard-Formato": formato,
               "X-RotaGuard-Sha256": sha or hashlib.sha256(content).hexdigest(),
               "Content-Type": "application/octet-stream"}
    if evento_uid:
        headers["X-RotaGuard-Evento"] = evento_uid
    return headers


def put_trecho(token, uid, content, formato="mp4", sessao=None, **kwargs):
    return call("PUT", f"/api/trechos/{uid}", raw=content, token=token,
                headers=cabecalhos_trecho(formato, content, sessao or novo_uid(), **kwargs))


def put_bruto(token, uid, headers, partes, content_length=None):
    """PUT com http.client: corpo em pedaços (chunked) ou anunciando um Content-Length maior do que manda."""
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=120)
    conn.putrequest("PUT", f"/api/trechos/{uid}")
    conn.putheader("Authorization", f"Bearer {token}")
    for name, value in headers.items():
        conn.putheader(name, value)
    conn.putheader("Content-Length" if content_length is not None else "Transfer-Encoding",
                   str(content_length) if content_length is not None else "chunked")
    conn.endheaders()
    try:
        for parte in partes:
            conn.send(parte if content_length is not None else b"%x\r\n" % len(parte) + parte + b"\r\n")
        if content_length is None:
            conn.send(b"0\r\n\r\n")
    except OSError:
        pass  # o servidor pode fechar a conexão depois de responder 413
    response = conn.getresponse()
    status = response.status
    response.read()
    conn.close()
    return status


def chaves(lista):
    return [item["uid"] for item in lista]


log = open(work / "server.log", "w", encoding="utf-8")
server = subprocess.Popen([sys.executable, "-m", "uvicorn", "backend.main:app", "--port", str(port)],
                          cwd=SERVIDOR, env=env, stdout=log, stderr=subprocess.STDOUT)
try:
    for _ in range(80):
        try:
            if status_of("GET", "/health") == 200:
                break
        except OSError:
            time.sleep(0.5)
    else:
        raise AssertionError("servidor não subiu")

    # ---------- migração e saúde ----------
    con = sqlite3.connect(database)
    colunas = {table: {row[1] for row in con.execute(f"PRAGMA table_info({table})")}
               for table in ("companies", "devices", "alerts", "user_sessions")}
    tabelas = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    empresa_antiga = con.execute("SELECT name, uid FROM companies WHERE id = 1").fetchone()
    aparelho_antigo = con.execute("SELECT name, uid, token_hash FROM devices WHERE id = 1").fetchone()
    alerta_antigo = con.execute("SELECT details, sync_seq FROM alerts WHERE id = 1").fetchone()
    con.close()
    assert {"uid"} <= colunas["companies"], colunas
    assert {"uid", "paired_at", "computer_name", "program_name", "current_session_uid", "testing_now", "sync_seq",
            "changed_at"} <= colunas["devices"], colunas
    assert {"session_uid", "clip_uid", "sync_seq", "changed_at"} <= colunas["alerts"], colunas
    assert "client" in colunas["user_sessions"], colunas
    assert {"test_sessions", "clips", "pairing_codes", "sync_state"} <= tabelas, tabelas
    assert empresa_antiga[0] == "Transportadora Antiga" and re.fullmatch(r"[0-9a-f]{32}", empresa_antiga[1] or "")
    assert aparelho_antigo[0] == "Raspberry antigo" and re.fullmatch(r"[0-9a-f]{32}", aparelho_antigo[1] or "")
    assert aparelho_antigo[2] == hashlib.sha256(TOKEN_ANTIGO.encode()).hexdigest() and alerta_antigo[1] is not None
    assert heartbeat(TOKEN_ANTIGO)[0] == 200
    ok("migração da 0.3.0: tabelas e colunas novas, uid em empresa e aparelho, dados e token antigo preservados")

    status, headers, content = call("GET", "/api/health")
    assert status == 200 and json.loads(content)["status"] == "ok", content
    assert headers["Cache-Control"] == "no-store" and status_of("GET", "/health") == 200
    ok("GET /api/health (para o Caddy) e /health respondem; API com Cache-Control: no-store")

    # ---------- empresas e usuários pelo manage.py ----------
    saida = manage("criar-empresa", "--nome", "Empresa Ana").stdout
    assert "#2" in saida and re.search(r"[0-9a-f]{32}", saida), saida
    manage("criar-empresa", "--nome", "Empresa Beto")
    manage("criar-usuario", "--papel", "gestor", "--nome", "Gestora Ana", "--email", "ana@central.local",
           "--empresa", "empresa ana", password=SENHA_ANA)
    manage("criar-usuario", "--papel", "gestor", "--nome", "Gestor Beto", "--email", "beto@central.local",
           "--empresa", "3", password=SENHA_BETO)
    manage("criar-usuario", "--papel", "admin", "--nome", "Equipe", "--email", "equipe@central.local",
           password=SENHA_EQUIPE)
    manage("criar-motorista", "--nome", "Motorista Ana", "--cnh", "ANA0001", "--empresa", "Empresa Ana")
    manage("criar-usuario", "--papel", "motorista", "--nome", "Motorista Ana", "--email", "mot@central.local",
           "--empresa", "Empresa Ana", "--motorista", "1", password=SENHA_MOTORISTA)
    errado = manage("criar-usuario", "--papel", "gestor", "--nome", "X", "--email", "x@central.local", "--empresa",
                    "Empresa Que Não Existe", password=SENHA_ANA, expect_ok=False)
    assert errado.returncode != 0 and "Empresa" in (errado.stdout + errado.stderr), errado
    segredos.extend([SENHA_ANA, SENHA_BETO, SENHA_EQUIPE, SENHA_MOTORISTA])
    ok("manage.py: empresa mostra o uid; usuário ligado à empresa pelo nome ou pelo id; nome errado é recusado")

    # ---------- login do painel com token ----------
    assert status_of("POST", "/api/auth/login", {"login": "ana@central.local", "password": SENHA_ANA}) == 403
    status, headers, content = call("POST", "/api/auth/login", {"login": "ana@central.local", "password": SENHA_ANA},
                                    headers={"X-DriveSafe": "1"})
    assert status == 200 and "drivesafe_sessao=" in (headers.get("Set-Cookie") or "")
    assert json.loads(content).get("token") is None
    ana = login_painel("ana@central.local", SENHA_ANA)
    assert ana["role"] == "gestor" and ana["company"]["name"] == "Empresa Ana", ana
    assert ler_iso(ana["expira_em"]) > agora() + timedelta(days=29), ana["expira_em"]
    beto = login_painel("beto@central.local", SENHA_BETO, via="corpo")
    equipe = login_painel("equipe@central.local", SENHA_EQUIPE)
    motorista = login_painel("mot@central.local", SENHA_MOTORISTA)
    assert status_of("POST", "/api/auth/login", {"login": "ana@central.local", "password": "senha-errada-123"},
                     headers={"X-RotaGuard-Cliente": "painel"}) == 401
    assert jcall("GET", "/api/auth/me", token=ana["token"])["email"] == "ana@central.local"
    assert status_of("GET", "/api/auth/me", token="token-que-nao-existe") == 401
    assert status_of("GET", "/api/alerts", token=ana["token"]) == 200
    sessao_painel = db_rows("SELECT client, expires_at FROM user_sessions WHERE token_hash = ?",
                            hashlib.sha256(ana["token"].encode()).hexdigest())[0]
    assert sessao_painel["client"] == "painel", dict(sessao_painel)
    ok("login do painel (cabeçalho X-RotaGuard-Cliente ou \"token\": true) devolve token de 30 dias sem cookie; "
       "login antigo do app web continua com cookie; Bearer aceito nas rotas de usuário")

    # ---------- CEN-01 ----------
    codigo = gerar_codigo(ana["token"])
    assert re.fullmatch(f"[{ALFABETO}]{{8}}", codigo["codigo"]), codigo
    minutos = (ler_iso(codigo["expira_em"]) - agora()).total_seconds() / 60
    assert 29.5 < minutos <= 30.1 and re.fullmatch(r"[0-9a-f]{32}", codigo["aparelho_uid"]), (minutos, codigo)
    segredos.append(codigo["codigo"])
    guardado = json.dumps([dict(row) for row in db_rows("SELECT * FROM pairing_codes")], default=str)
    assert codigo["codigo"] not in guardado and codigo["codigo"].lower() not in guardado, guardado
    assert status_of("POST", "/api/pareamento/codigos", {"nome": "x"}, token=motorista["token"]) == 403
    assert status_of("POST", "/api/pareamento/codigos", {"nome": "x"}, token=equipe["token"]) == 400
    gerar_codigo(equipe["token"], nome="Teste da equipe", company_id=3)
    assert status_of("POST", "/api/pareamento/codigos", {"nome": "x"}) == 401
    ok("CEN-01 gestor gera código de 8 caracteres sem ambíguos, válido por 30 min, guardado só como hash; "
       "motorista não gera; equipe escolhe a empresa")

    # ---------- CEN-02 ----------
    digitado = f"{codigo['codigo'][:4].lower()}-{codigo['codigo'][4:].lower()}"
    status, _, content = trocar(digitado, "198.51.100.10")
    assert status == 200, content
    pareado = json.loads(content)
    token_ana = pareado["token"]
    segredos.append(token_ana)
    assert token_ana.startswith("dsk_") and pareado["aparelho_uid"] == codigo["aparelho_uid"], pareado
    assert pareado["empresa"]["nome"] == "Empresa Ana" and re.fullmatch(r"[0-9a-f]{32}", pareado["empresa"]["uid"])
    linha = db_rows("SELECT token_hash, company_id, name, computer_name, program_name FROM devices WHERE uid = ?",
                    pareado["aparelho_uid"])[0]
    assert linha["token_hash"] == hashlib.sha256(token_ana.encode()).hexdigest() and linha["company_id"] == 2
    assert linha["computer_name"] == "Notebook da Ana" and linha["program_name"] == "RotaGuard Script 0.9", dict(linha)
    assert token_ana not in json.dumps([dict(row) for row in db_rows("SELECT * FROM devices")], default=str)
    assert trocar(digitado, "198.51.100.10")[0] == 400
    assert heartbeat(token_ana)[0] == 200
    ok("CEN-02 código (com hífen e minúsculas) vira token dsk_ uma vez só; aparelho na empresa de quem gerou, "
       "token guardado só como hash")

    # ---------- CEN-03 ----------
    vencido = gerar_codigo(ana["token"], nome="Vencido")
    db_exec("UPDATE pairing_codes SET expires_at = ? WHERE device_uid = ?", sql_utc(agora() - timedelta(minutes=1)),
            vencido["aparelho_uid"])
    assert trocar(vencido["codigo"], "198.51.100.11")[0] == 400
    valido = gerar_codigo(ana["token"], nome="Notebook do Caio")
    segredos.append(valido["codigo"])
    tentativas = [trocar(errado, "203.0.113.7")[0] for errado in ["ZZZZ-ZZZ2", "123", "", "AAAA-AAAA", "IIII-OOOO",
                                                                 "XXXXXXXX", "abcd-efgh", "2222-2222", "QQQQQQQQ",
                                                                 "MMMM-MMMM"]]
    assert tentativas == [400] * 10, tentativas
    assert trocar(valido["codigo"], "203.0.113.7")[0] == 429
    status, _, content = trocar(valido["codigo"], "203.0.113.8", computador="Notebook do Caio")
    assert status == 200, content
    token_caio = json.loads(content)["token"]
    segredos.append(token_caio)
    sys.path.insert(0, str(SERVIDOR))
    os.environ.update(DATABASE_URL=env["DATABASE_URL"], DRIVESAFE_TRECHOS_DIR=env["DRIVESAFE_TRECHOS_DIR"])
    from starlette.requests import Request  # noqa: E402
    from backend.auth import client_ip  # noqa: E402

    def ip_de(peer, forwarded=None):
        headers = [(b"x-forwarded-for", forwarded.encode())] if forwarded else []
        return client_ip(Request({"type": "http", "client": (peer, 50000), "headers": headers}))

    assert ip_de("8.8.8.8", "1.2.3.4") == "8.8.8.8"
    assert ip_de("172.18.0.5", "203.0.113.9") == "203.0.113.9"
    assert ip_de("127.0.0.1", "10.0.0.1, 198.51.100.4") == "198.51.100.4"
    assert ip_de("10.1.2.3", "isto-nao-e-ip") == "10.1.2.3" and ip_de("172.18.0.5") == "172.18.0.5"
    ok("CEN-03 código vencido ou errado falha; 10 erros por minuto do mesmo IP bloqueiam (429) até código certo; "
       "outro IP segue; X-Forwarded-For só vale vindo de rede privada")

    # ---------- CEN-04 ----------
    sessao = novo_uid()
    corpo = {"iniciada_em": "2026-10-19T12:00:00Z", "encerrada_em": None, "programa": "RotaGuard Script 0.9",
             "camera": "Webcam integrada", "resumo": {"duracao_s": 0}}
    assert jcall("PUT", f"/api/sessoes/{sessao}", corpo, token=token_ana) == {"uid": sessao}
    corpo.update(encerrada_em="2026-10-19T12:30:00Z",
                 resumo={"duracao_s": 1800, "eventos_por_tipo": {"microssono": 2}, "perclos_medio": 0.12,
                         "piscadas_por_minuto": 14.5, "trechos": 1, "fps_medio": 24.8, "bpm": 72,
                         "cardio_media": 70, "respiracao_rpm": 15})
    assert jcall("PUT", f"/api/sessoes/{sessao}", corpo, token=token_ana) == {"uid": sessao}
    vistas = novidades(ana["token"])
    minha = next(item for item in vistas["sessoes"] if item["uid"] == sessao)
    assert minha["aparelho_uid"] == pareado["aparelho_uid"] and minha["encerrada_em"] == "2026-10-19T12:30:00Z"
    assert minha["resumo"]["perclos_medio"] == 0.12 and minha["programa"] == "RotaGuard Script 0.9", minha
    assert not {"bpm", "cardio_media", "respiracao_rpm"} & set(minha["resumo"]), minha["resumo"]
    assert minha["alterado_em"].endswith("Z") and minha["camera"] == "Webcam integrada"
    assert sessao not in chaves(novidades(beto["token"])["sessoes"])
    assert status_of("PUT", f"/api/sessoes/{sessao}", corpo, token=token_caio) == 409
    assert status_of("PUT", "/api/sessoes/nao-e-uid", corpo, token=token_ana) == 422
    assert status_of("PUT", f"/api/sessoes/{novo_uid()}", corpo, token=ana["token"]) == 401
    ok("CEN-04 aparelho envia e atualiza a sessão (idempotente, sem cardio no resumo); só a empresa dele vê")

    # ---------- CEN-05 ----------
    trecho = novo_uid()
    mp4 = conteudo("mp4")
    status, _, content = put_trecho(token_ana, trecho, mp4, sessao=sessao)
    assert status == 201 and json.loads(content) == {"uid": trecho, "tamanho": len(mp4)}, content
    arquivo = longo(pasta_trechos / pareado["empresa"]["uid"] / f"{trecho}.mp4")
    assert len(str(arquivo)) > 264 and arquivo.read_bytes() == mp4, len(str(arquivo))
    status, _, content = put_trecho(token_ana, trecho, mp4, sessao=sessao)
    assert status == 200 and json.loads(content)["uid"] == trecho
    assert put_trecho(token_ana, trecho, conteudo("mp4"), sessao=sessao)[0] == 409
    errado = novo_uid()
    assert put_trecho(token_ana, errado, mp4, sessao=sessao, sha="0" * 64)[0] == 422
    assert put_trecho(token_ana, novo_uid(), mp4, formato="avi", sessao=sessao)[0] == 422
    assert put_trecho(token_ana, novo_uid(), mp4, formato="webm", sessao=sessao)[0] == 422
    assert put_trecho(token_ana, novo_uid(), mp4, sessao=sessao, tipo="Tipo Inválido")[0] == 422
    assert put_trecho(token_ana, "../../fora", mp4, sessao=sessao)[0] in (404, 422)
    grande = cabecalhos_trecho("mp4", b"", sessao, sha="1" * 64)
    assert put_bruto(token_ana, novo_uid(), grande, [mp4[:1000]], content_length=LIMITE_TRECHO + 1) == 413
    pedacos = [conteudo("mp4", 1024 * 1024 - 12)] + [b"\0" * (1024 * 1024)] * 24 + [b"\0"]
    assert sum(map(len, pedacos)) == LIMITE_TRECHO + 1
    assert put_bruto(token_ana, novo_uid(), grande, pedacos) == 413
    sobras = [name for _, _, names in os.walk(longo(pasta_trechos)) for name in names if name != arquivo.name]
    assert sobras == [], sobras
    assert put_trecho(ana["token"], novo_uid(), mp4)[0] == 401
    sem_sessao = cabecalhos_trecho("mp4", mp4, sessao)
    del sem_sessao["X-RotaGuard-Sessao"]
    assert call("PUT", f"/api/trechos/{novo_uid()}", raw=mp4, token=token_ana, headers=sem_sessao)[0] == 422
    ok("CEN-05 trecho com SHA-256 certo grava (201, repetido 200); SHA errado 422; acima de 25 MB 413 (anunciado ou "
       "em streaming); formato, tipo, sessão e conteúdo conferidos; nada sobra na pasta")

    envios_caio = [put_trecho(token_caio, novo_uid(), conteudo("mp4", 500), sessao=novo_uid())[0]
                   for _ in range(TRECHOS_POR_DIA + 1)]
    assert envios_caio == [201] * TRECHOS_POR_DIA + [429], envios_caio
    ok(f"teto diário por aparelho ({TRECHOS_POR_DIA} trechos em 24 h no teste) mesmo trocando de sessão: 429")

    webm, clip = conteudo("webm"), conteudo("rgclip")
    trecho_webm, trecho_clip = novo_uid(), novo_uid()
    assert put_trecho(token_ana, trecho_webm, webm, formato="webm", sessao=sessao)[0] == 201
    assert put_trecho(token_ana, trecho_clip, clip, formato="rgclip", sessao=sessao, tipo="celular_na_mao")[0] == 201

    # ---------- CEN-06 ----------
    assert status_of("GET", "/api/sync/novidades", token=token_ana) == 403
    assert status_of("GET", f"/api/trechos/{trecho}/arquivo", token=token_ana) == 403
    assert status_of("POST", "/api/pareamento/codigos", {"nome": "x"}, token=token_ana) == 403
    assert status_of("GET", "/api/alerts", token=token_ana) == 403
    ok("CEN-06 token de aparelho não lê novidades, não baixa trecho e não gera código (403)")

    # ---------- CEN-07 ----------
    assert status_of("GET", f"/api/trechos/{trecho}/arquivo", token=beto["token"]) == 404
    vistas_beto = novidades(beto["token"])
    assert not set(chaves(vistas_beto["trechos"])) & {trecho, trecho_webm, trecho_clip}, vistas_beto["trechos"]
    assert pareado["aparelho_uid"] not in chaves(vistas_beto["aparelhos"])
    assert status_of("GET", f"/api/trechos/{novo_uid()}/arquivo", token=ana["token"]) == 404
    assert status_of("GET", "/api/sync/novidades", token=motorista["token"]) == 403
    assert status_of("GET", "/api/sync/novidades?company_id=3", token=ana["token"]) == 403
    vistas_equipe = novidades(equipe["token"])
    assert {trecho, trecho_webm, trecho_clip} <= set(chaves(vistas_equipe["trechos"]))
    assert status_of("GET", f"/api/trechos/{trecho}/arquivo", token=equipe["token"]) == 200
    ok("CEN-07 gestor de outra empresa não vê nem baixa (404); motorista sem acesso; equipe vê todas as empresas")

    # ---------- CEN-09 ----------
    antes = len(db_rows("SELECT id FROM audit_log WHERE action = 'trecho_baixado'"))
    status, headers, content = call("GET", f"/api/trechos/{trecho}/arquivo", token=ana["token"])
    assert status == 200 and content == mp4 and headers["Content-Type"] == "video/mp4", (status, headers)
    assert headers["X-RotaGuard-Sha256"] == hashlib.sha256(mp4).hexdigest() and headers["Cache-Control"] == "no-store"
    for uid, dados, tipo in ((trecho_webm, webm, "video/webm"), (trecho_clip, clip, "application/zip")):
        status, headers, content = call("GET", f"/api/trechos/{uid}/arquivo", token=ana["token"])
        assert status == 200 and content == dados and headers["Content-Type"] == tipo, (uid, headers)
    auditoria = db_rows("SELECT user_id, company_id, target, ip FROM audit_log WHERE action = 'trecho_baixado' "
                        "ORDER BY id")
    assert len(auditoria) == antes + 3 and auditoria[-3]["target"] == f"trecho:{trecho}", [dict(r) for r in auditoria]
    assert auditoria[-1]["user_id"] == ana["id"] and auditoria[-1]["company_id"] == 2
    ok("CEN-09 download confere SHA-256 e Content-Type (mp4, webm, rgclip como zip) e grava auditoria de quem baixou")

    # ---------- CEN-10 ----------
    vinculado = evento(details={"perclos": 0.31, "fechado_s": 1.4, "bpm": 72, "cardio": {"snr_db": 4},
                                "cardio_qualidade": "boa", "Cardio_Extra": 1, "frequencia_cardiaca": 70, "rppg": [1, 2],
                                "respiracao_rpm": 14, "rmssd_ms": 41, "snr_db": 3.2,
                                "medidas": {"bpm": 71, "ear": 0.18}, "lista": [{"rmssd_ms": 1, "ok": True}],
                                "sessao_uid": sessao, "trecho_uid": trecho})
    assert enviar_eventos(token_ana, vinculado)["accepted"] == 1
    guardado = db_rows("SELECT details, session_uid, clip_uid FROM alerts WHERE event_uid = ?", vinculado["event_uid"])[0]
    texto = guardado["details"].lower()
    for chave in ("bpm", "cardio", "frequencia_cardiaca", "rppg", "respiracao_rpm", "rmssd_ms", "snr_db"):
        assert chave not in texto, (chave, texto)
    assert guardado["session_uid"] == sessao and guardado["clip_uid"] == trecho, dict(guardado)
    item = next(e for e in novidades(ana["token"])["eventos"] if e["uid"] == vinculado["event_uid"])
    assert item["detalhes"]["perclos"] == 0.31 and item["detalhes"]["medidas"] == {"ear": 0.18}, item
    assert item["detalhes"]["lista"] == [{"ok": True}] and item["sessao_uid"] == sessao and item["trecho_uid"] == trecho
    assert item["aparelho_uid"] == pareado["aparelho_uid"] and item["tipo"] == "microssono" and item["nivel_risco"] == 3
    antigo = next(e for e in novidades(equipe["token"])["eventos"] if e["uid"] == "11111111-1111-4111-8111-111111111111")
    assert antigo["detalhes"] == {"fechado_s": 2.0}, antigo
    ok("CEN-10 chaves de cardio removidas do evento (até aninhadas) antes de gravar e também na saída; "
       "sessao_uid e trecho_uid guardados para o painel")

    trecho_ligado = next(t for t in novidades(ana["token"])["trechos"] if t["uid"] == trecho)
    assert trecho_ligado["evento_uid"] == vinculado["event_uid"] and trecho_ligado["sessao_uid"] == sessao
    assert trecho_ligado["formato"] == "mp4" and trecho_ligado["tamanho"] == len(mp4) and trecho_ligado["duracao_s"] == 16
    assert trecho_ligado["sha256"] == hashlib.sha256(mp4).hexdigest() and trecho_ligado["tipo"] == "microssono"
    assert trecho_ligado["inicio"] == "2026-10-19T12:00:00Z" and trecho_ligado["fim"] == "2026-10-19T12:00:16Z"
    evento_antes = evento(alert_type="celular_na_mao")
    assert enviar_eventos(token_ana, evento_antes)["accepted"] == 1
    trecho_depois = novo_uid()
    assert put_trecho(token_ana, trecho_depois, conteudo("mp4"), sessao=sessao, tipo="celular_na_mao",
                      evento_uid=evento_antes["event_uid"])[0] == 201
    item = next(e for e in novidades(ana["token"])["eventos"] if e["uid"] == evento_antes["event_uid"])
    assert item["trecho_uid"] == trecho_depois, item
    ok("trecho e evento se ligam nos dois sentidos (trecho_uid no evento ou X-RotaGuard-Evento no trecho)")

    # ---------- CEN-08 ----------
    tudo = novidades(ana["token"])
    assert tudo["mais"] is False and set(tudo) >= {"cursor", "mais", "aparelhos", "sessoes", "eventos", "trechos"}
    esperado = {(tipo, uid) for tipo in ("aparelhos", "sessoes", "eventos", "trechos") for uid in chaves(tudo[tipo])}
    vistos, cursor, paginas = [], "", 0
    while True:
        pagina = novidades(ana["token"], desde=cursor, limite=2)
        itens = [(tipo, uid) for tipo in ("aparelhos", "sessoes", "eventos", "trechos") for uid in chaves(pagina[tipo])]
        assert len(itens) <= 2, itens
        for tipo in ("aparelhos", "sessoes", "eventos", "trechos"):
            datas = [item["alterado_em"] for item in pagina[tipo]]
            assert datas == sorted(datas), datas
        vistos += itens
        cursor, paginas = pagina["cursor"], paginas + 1
        if not pagina["mais"]:
            break
        assert itens, "mais=true sem itens"
    assert len(vistos) == len(set(vistos)) and set(vistos) == esperado, (vistos, esperado)
    assert paginas >= len(esperado) // 2, paginas
    parado = novidades(ana["token"], desde=cursor)
    assert not any(parado[t] for t in ("aparelhos", "sessoes", "eventos", "trechos")) and parado["mais"] is False
    novo = evento(alert_type="olhos_esfregados", risk=2)
    enviar_eventos(token_ana, novo)
    depois = novidades(ana["token"], desde=parado["cursor"])
    assert chaves(depois["eventos"]) == [novo["event_uid"]] and not depois["sessoes"] and not depois["trechos"], depois
    assert chaves(depois["aparelhos"]) == [pareado["aparelho_uid"]], depois["aparelhos"]
    assert status_of("GET", "/api/sync/novidades?desde=isto-nao-e-cursor", token=ana["token"]) == 400
    ok(f"CEN-08 cursor: {len(esperado)} itens em {paginas} páginas de 2, em ordem e sem repetir; depois só o que mudou")

    # ---------- CEN-11 ----------
    aberta = novo_uid()
    cursor = depois["cursor"]
    assert heartbeat(token_ana, {"risk_level": 2, "sessao_uid": aberta})[0] == 200
    pagina = novidades(ana["token"], desde=cursor)
    aparelho = next(a for a in pagina["aparelhos"] if a["uid"] == pareado["aparelho_uid"])
    assert aparelho["testando_agora"] is True and aparelho["risco_atual"] == 2, aparelho
    assert aparelho["sessao_atual_uid"] == aberta and aparelho["computador"] == "Notebook da Ana", aparelho
    assert aparelho["programa"] == "RotaGuard Script 0.9" and aparelho["pareado_em"].endswith("Z"), aparelho
    assert ler_iso(aparelho["ultimo_sinal"]) > agora() - timedelta(seconds=10), aparelho
    db_exec("UPDATE devices SET last_seen_at = ? WHERE uid = ?", sql_utc(agora() - timedelta(seconds=31)),
            pareado["aparelho_uid"])
    pagina = novidades(ana["token"], desde=pagina["cursor"])
    aparelho = next(a for a in pagina["aparelhos"] if a["uid"] == pareado["aparelho_uid"])
    assert aparelho["testando_agora"] is False, aparelho
    assert heartbeat(token_ana, {"risk_level": 1, "sessao_uid": None})[0] == 200
    aparelho = next(a for a in novidades(ana["token"], desde=pagina["cursor"])["aparelhos"]
                    if a["uid"] == pareado["aparelho_uid"])
    assert aparelho["testando_agora"] is False and aparelho["sessao_atual_uid"] is None, aparelho
    assert heartbeat(token_ana, {"risk_level": 1, "sessao_uid": aberta})[0] == 200
    corpo.update(encerrada_em=iso(agora()), resumo={"duracao_s": 30})
    jcall("PUT", f"/api/sessoes/{aberta}", corpo, token=token_ana)
    aparelho = next(a for a in novidades(ana["token"])["aparelhos"] if a["uid"] == pareado["aparelho_uid"])
    assert aparelho["testando_agora"] is False and aparelho["sessao_atual_uid"] is None, aparelho
    ok("CEN-11 \"testando agora\" com sinal de vida de menos de 30 s e sessão aberta; passa a falso sozinho "
       "(e chega pelo cursor) quando o sinal some ou a sessão encerra")

    # ---------- retenção ----------
    db_exec("UPDATE clips SET received_at = ? WHERE uid = ?", sql_utc(agora() - timedelta(days=31)), trecho_webm)
    cursor = novidades(ana["token"])["cursor"]
    parte_velha = longo(pasta_trechos / pareado["empresa"]["uid"] / ".velho0123456789.part")
    parte_nova = longo(pasta_trechos / pareado["empresa"]["uid"] / ".novo0123456789a.part")
    for parte in (parte_velha, parte_nova):
        parte.write_bytes(b"envio interrompido")
    os.utime(parte_velha, (time.time() - 2 * 86400, time.time() - 2 * 86400))
    saida = manage("apagar-trechos-antigos", "--dias", "30").stdout
    assert "1 trecho" in saida and "1 envio(s) interrompido(s)" in saida, saida
    assert not parte_velha.exists() and parte_nova.exists()
    parte_nova.unlink()
    assert not longo(pasta_trechos / pareado["empresa"]["uid"] / f"{trecho_webm}.webm").exists() and arquivo.exists()
    assert status_of("GET", f"/api/trechos/{trecho_webm}/arquivo", token=ana["token"]) == 410
    apagado = novidades(ana["token"], desde=cursor)["trechos"]
    assert chaves(apagado) == [trecho_webm] and apagado[0]["apagado_em"], apagado
    assert put_trecho(token_ana, trecho_webm, webm, formato="webm", sessao=sessao)[0] == 409
    ok("manage.py apagar-trechos-antigos --dias 30: apaga o arquivo, avisa o painel (apagado_em) e o download dá 410")

    # ---------- desconectar aparelho ----------
    assert status_of("DELETE", f"/api/pareamento/aparelhos/{pareado['aparelho_uid']}", token=beto["token"]) == 404
    assert status_of("DELETE", f"/api/pareamento/aparelhos/{pareado['aparelho_uid']}", token=token_ana) == 403
    assert status_of("DELETE", f"/api/pareamento/aparelhos/{pareado['aparelho_uid']}", token=ana["token"]) == 204
    assert heartbeat(token_ana)[0] == 401
    revogado = next(a for a in novidades(ana["token"])["aparelhos"] if a["uid"] == pareado["aparelho_uid"])
    assert revogado["revogado_em"] and revogado["testando_agora"] is False, revogado
    pendente = gerar_codigo(ana["token"], nome="Nunca conectou")
    segredos.append(pendente["codigo"])
    assert status_of("DELETE", f"/api/pareamento/aparelhos/{pendente['aparelho_uid']}", token=ana["token"]) == 204
    assert trocar(pendente["codigo"], "198.51.100.30")[0] == 400
    assert status_of("DELETE", f"/api/pareamento/aparelhos/{aparelho_antigo[1]}", token=ana["token"]) == 404
    ok("desconectar: token do aparelho deixa de valer na hora e o painel recebe revogado_em; código pendente é anulado")

    assert status_of("POST", "/api/auth/logout", token=beto["token"]) == 204
    assert status_of("GET", "/api/auth/me", token=beto["token"]) == 401
    ok("sair pelo painel (Bearer) encerra o token")

    # ---------- CEN-12 ----------
    for script in ("test_server_sync.py", "test_politica_remota.py"):
        result = subprocess.run([sys.executable, str(PROJECT / "tests" / script)], cwd=PROJECT, capture_output=True,
                                text=True, encoding="utf-8", env=dict(os.environ, PYTHONUTF8="1"))
        assert result.returncode == 0, f"{script}:\n{result.stdout[-3000:]}\n{result.stderr[-3000:]}"
    ok("CEN-12 testes antigos do servidor (test_server_sync.py, test_politica_remota.py) continuam passando")

    server.terminate()
    server.wait(10)
    log.flush()
    registro = (work / "server.log").read_text(encoding="utf-8", errors="replace")
    vazados = [segredo[:6] + "…" for segredo in segredos if segredo and segredo in registro]
    assert not vazados, vazados
    ok(f"nenhuma senha, token ou código ({len(segredos)} segredos) aparece no registro do servidor")

    print(f"\nTODOS OS {checks} TESTES PASSARAM (Python {sys.version.split()[0]})")
except Exception:
    print((work / "server.log").read_text(encoding="utf-8", errors="replace")[-5000:])
    raise
finally:
    if server.poll() is None:
        server.terminate()
        server.wait(10)
    log.close()
    shutil.rmtree(longo(work), ignore_errors=True)
