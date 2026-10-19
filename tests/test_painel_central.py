"""Spec 026: o painel executável recebe da central (PCE-01 a PCE-10).

Central de mentira com http.server local (127.0.0.1, porta aleatória) seguindo o "Contrato da central (v1)" da spec.
Sem janela: a Ponte é chamada direto, com relógio falso, scrypt barato e pasta temporária. Senhas descartáveis, só daqui.
    python tests/test_painel_central.py
"""
import base64
import hashlib
import io
import json
import os
import sys
import tempfile
import threading
import time
import urllib.request
import zipfile
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "painel" / "desktop"))
import central as modulo_central  # noqa: E402
import rotaguard_painel as rp  # noqa: E402
from ponte import Ponte  # noqa: E402

checks = 0
CUSTO_TESTE = (2**4, 8, 1)
SENHA_ADM = "frase comprida de teste um"
SENHA_SUP = "frase comprida de teste dois"
SENHA_CON = "frase comprida de teste tres"
SENHA_CENTRAL = "senha-da-central-de-teste-91"
TOKEN = "tok_" + "a1" * 20
ADMIN = {"nome": "Marina Lopes", "usuario": "marina.lopes", "senha": SENHA_ADM}
EMPRESA = "Transportes Lima"  # spec 030: ativar sem arquivo cria a empresa com o nome digitado
abrir_url = urllib.request.build_opener(urllib.request.ProxyHandler({})).open


def ok(message):
    global checks
    checks += 1
    print(f"OK {checks:02d} {message}")


def dados(resposta, contexto=""):
    assert resposta.get("ok") is True, f"{contexto}: {resposta}"
    return resposta["dados"]


def erro(resposta, codigo, contexto=""):
    assert resposta.get("ok") is False and resposta.get("codigo") == codigo, f"{contexto}: esperava {codigo}, veio {resposta}"
    return resposta


def iso(segundos):
    return datetime.fromtimestamp(segundos, timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def uid(n):
    return f"{n:032x}"


# Trechos de teste ---------------------------------------------------------------------------------------------------------
MP4 = b"\x00\x00\x00\x18ftypmp42" + bytes(40) + b"trecho-mp4-de-teste"
JPEG = [b"\xff\xd8\xff\xe0" + bytes(12) + f"quadro-{i}".encode() + b"\xff\xd9" for i in range(3)]


def rgclip():
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w") as pacote:
        pacote.writestr("indice.json", json.dumps({"formato": "rotaguard-rgclip/1", "fps": 15, "largura": 640,
                                                  "altura": 360, "quadros": [{"arquivo": f"q{i:05d}.jpg", "t": i / 15}
                                                                             for i in range(3)]}))
        for i, quadro in enumerate(JPEG):
            pacote.writestr(f"q{i:05d}.jpg", quadro)
    return memoria.getvalue()


RGCLIP = rgclip()
T0 = datetime(2026, 10, 19, 14, 0, tzinfo=timezone.utc).timestamp()
APARELHOS = [
    {"uid": uid(1), "nome": "Notebook da Ana", "computador": "ANA-PC", "programa": "RotaGuard Teste 0.4",
     "pareado_em": iso(T0 - 86400), "ultimo_sinal": iso(T0 - 5), "testando_agora": True, "risco_atual": 2,
     "sessao_atual_uid": uid(11), "alterado_em": iso(T0 - 5)},
    {"uid": uid(2), "nome": "Desktop da garagem", "computador": "GARAGEM", "programa": "RotaGuard Teste 0.4",
     "pareado_em": iso(T0 - 7200), "ultimo_sinal": iso(T0 - 3600), "testando_agora": False, "risco_atual": None,
     "sessao_atual_uid": None, "alterado_em": iso(T0 - 3600)},
]
RESUMO = {"duracao_s": 1200, "eventos_por_tipo": {"microssono": 1, "uso_celular": 1}, "perclos_medio": 0.08,
          "piscadas_por_minuto": 14.5, "trechos": 2, "fps_medio": 24.8}
SESSOES = [
    {"uid": uid(11), "aparelho_uid": uid(1), "iniciada_em": iso(T0 - 1200), "encerrada_em": None,
     "programa": "RotaGuard Teste 0.4", "camera": "Webcam HD", "resumo": RESUMO, "alterado_em": iso(T0 - 60)},
    {"uid": uid(12), "aparelho_uid": uid(2), "iniciada_em": iso(T0 - 7200), "encerrada_em": iso(T0 - 5400),
     "programa": "RotaGuard Teste 0.4", "camera": "USB", "resumo": {**RESUMO, "duracao_s": 1800, "trechos": 0},
     "alterado_em": iso(T0 - 5400)},
]
EVENTOS = [
    {"uid": "0b7c2c1e-1111-4a0b-9c1d-000000000001", "aparelho_uid": uid(1), "sessao_uid": uid(11),
     "tipo": "microssono", "nivel_risco": 3, "duracao_s": 1.4, "ocorrido_em": iso(T0 - 900),
     "detalhes": {"olho": 0.1, "cardio_bpm": 88, "frequencia_cardiaca": 90}, "trecho_uid": uid(21),
     "alterado_em": iso(T0 - 900)},
    {"uid": "0b7c2c1e-1111-4a0b-9c1d-000000000002", "aparelho_uid": uid(1), "sessao_uid": uid(11),
     "tipo": "uso_celular", "nivel_risco": 2, "duracao_s": 4.0, "ocorrido_em": iso(T0 - 600), "detalhes": {},
     "trecho_uid": uid(22), "alterado_em": iso(T0 - 600)},
    {"uid": "0b7c2c1e-1111-4a0b-9c1d-000000000003", "aparelho_uid": uid(2), "sessao_uid": uid(12),
     "tipo": "atencao", "nivel_risco": 1, "duracao_s": None, "ocorrido_em": iso(T0 - 6000), "detalhes": None,
     "trecho_uid": None, "alterado_em": iso(T0 - 6000)},
]
TRECHOS = [
    {"uid": uid(21), "aparelho_uid": uid(1), "sessao_uid": uid(11), "evento_uid": EVENTOS[0]["uid"],
     "tipo": "microssono", "inicio": iso(T0 - 908), "fim": iso(T0 - 892), "duracao_s": 16.0, "formato": "mp4",
     "tamanho": len(MP4), "sha256": hashlib.sha256(MP4).hexdigest(), "recebido_em": iso(T0 - 880),
     "alterado_em": iso(T0 - 880)},
    {"uid": uid(22), "aparelho_uid": uid(1), "sessao_uid": uid(11), "evento_uid": EVENTOS[1]["uid"],
     "tipo": "uso_celular", "inicio": iso(T0 - 608), "fim": iso(T0 - 592), "duracao_s": 16.0, "formato": "rgclip",
     "tamanho": len(RGCLIP), "sha256": hashlib.sha256(RGCLIP).hexdigest(), "recebido_em": iso(T0 - 580),
     "alterado_em": iso(T0 - 580)},
]
ARQUIVOS = {uid(21): (MP4, "video/mp4"), uid(22): (RGCLIP, "application/zip")}


class Central:
    """Estado da central de mentira: pedidos recebidos e comportamentos ligáveis."""

    def __init__(self):
        self.pedidos = []
        self.corromper = set()  # trechos que vêm errados na próxima vez
        self.token_no_corpo = False
        self.funcao = "gestor"
        self.paginas = {"": ({"aparelhos": APARELHOS, "sessoes": SESSOES}, "c1", True),
                        "c1": ({"eventos": EVENTOS, "trechos": TRECHOS}, "c2", False),
                        "c2": ({}, "c2", False)}
        self.trava = threading.Lock()

    def contar(self, rota):
        with self.trava:
            return sum(1 for pedido in self.pedidos if pedido[1].startswith(rota))


ESTADO = Central()


class Manipulador(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _json(self, status, corpo, cabecalhos=None):
        bruto = json.dumps(corpo).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(bruto)))
        for chave, valor in (cabecalhos or {}).items():
            self.send_header(chave, valor)
        self.end_headers()
        self.wfile.write(bruto)

    def _autorizado(self):
        return self.headers.get("Authorization") == f"Bearer {TOKEN}"

    def _corpo(self):
        tamanho = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(tamanho) or b"{}")

    def do_POST(self):  # noqa: N802
        with ESTADO.trava:
            ESTADO.pedidos.append(("POST", self.path, {k.lower(): v for k, v in self.headers.items()}))
        if self.path == "/api/auth/login":
            if self.headers.get("X-DriveSafe") != "1":
                return self._json(403, {"detail": "Requisição sem o cabeçalho de segurança do app."})
            corpo = self._corpo()
            if corpo.get("login") != "gestor@viacao.test" or corpo.get("password") != SENHA_CENTRAL:
                return self._json(401, {"detail": "Login ou senha incorretos."})
            me = {"id": 7, "name": "Gestor da Viação", "email": "gestor@viacao.test", "role": ESTADO.funcao,
                  "company": {"id": 3, "name": "Viação Teste"}, "must_change_password": False}
            if ESTADO.token_no_corpo:
                me["token"] = TOKEN
                return self._json(200, me)
            return self._json(200, me, {"Set-Cookie": f"drivesafe_sessao={TOKEN}; HttpOnly; Path=/; SameSite=lax"})
        if self.path == "/api/auth/logout":
            return self._json(204 if self._autorizado() else 401, {})
        if self.path == "/api/pareamento/codigos":
            if not self._autorizado():
                return self._json(401, {"detail": "Sessão encerrada. Entre de novo."})
            corpo = self._corpo()
            return self._json(201, {"codigo": "ABCD2345", "expira_em": iso(time.time() + 1800),
                                    "aparelho_uid": uid(99), "nome_recebido": corpo.get("nome")})
        return self._json(404, {"detail": "não existe"})

    def do_GET(self):  # noqa: N802
        with ESTADO.trava:
            ESTADO.pedidos.append(("GET", self.path, {k.lower(): v for k, v in self.headers.items()}))
        if not self._autorizado():
            return self._json(401, {"detail": "Sessão encerrada. Entre de novo."})
        if self.path.startswith("/api/sync/novidades"):
            desde = self.path.split("desde=", 1)[1].split("&", 1)[0] if "desde=" in self.path else ""
            itens, cursor, mais = ESTADO.paginas.get(desde, ({}, desde, False))
            corpo = {"cursor": cursor, "mais": mais, "aparelhos": [], "sessoes": [], "eventos": [], "trechos": []}
            corpo.update(itens)
            return self._json(200, corpo)
        if self.path.startswith("/api/trechos/") and self.path.endswith("/arquivo"):
            trecho = self.path.split("/")[3]
            if trecho not in ARQUIVOS:
                return self._json(404, {"detail": "Trecho não encontrado."})
            bruto, tipo = ARQUIVOS[trecho]
            sha = hashlib.sha256(bruto).hexdigest()
            if trecho in ESTADO.corromper:
                ESTADO.corromper.discard(trecho)
                bruto = bruto[:-3] + b"xyz"
            self.send_response(200)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(bruto)))
            self.send_header("X-RotaGuard-Sha256", sha)
            self.end_headers()
            self.wfile.write(bruto)
            return None
        return self._json(404, {"detail": "não existe"})


def subir_central():
    servidor = ThreadingHTTPServer(("127.0.0.1", 0), Manipulador)
    threading.Thread(target=servidor.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
    return servidor


class ScriptFalso:
    def estado(self):
        return {"aberto": False}

    def eventos(self, desde_id):
        return []

    def iniciar(self):
        pass

    def parar(self):
        pass


def nova_ponte(pasta, relogio, intervalo_s=30.0):
    return Ponte(pasta, relogio=lambda: relogio[0], custo_scrypt=CUSTO_TESTE, script_local=ScriptFalso(),
                 central=modulo_central.Central(pasta, relogio=lambda: relogio[0], intervalo_s=intervalo_s))


def entrar_como(ponte, usuario, senha):
    dados(ponte.sair())
    dados(ponte.entrar(usuario, senha), f"entrar {usuario}")


def bytes_da_pasta(pasta):
    return b"".join(p.read_bytes() for p in Path(pasta).rglob("*") if p.is_file())


central_http = subir_central()
ENDERECO = f"http://127.0.0.1:{central_http.server_address[1]}"
tmp = tempfile.mkdtemp(prefix="rg-central-")
pasta = Path(tmp) / "dados"
relogio = [T0]
ponte = nova_ponte(pasta, relogio)
dados(ponte.ativar_local(EMPRESA, ADMIN), "ativar")
adicionado = dados(ponte.equipe_adicionar({"nome": "Paulo Reis", "usuario": "paulo.reis", "funcao": "supervisor"}))
dados(ponte.equipe_adicionar({"nome": "Ana Souza", "usuario": "ana.souza", "funcao": "consulta"}))

# PCE-08 -------------------------------------------------------------------------------------------------------------------
NOVOS = ("central_estado", "central_conectar", "central_desconectar", "central_gerar_codigo", "remotos_listar",
         "remotos_sessao", "remotos_trecho")
texto_bridge = (RAIZ / "painel" / "app" / "src" / "lib" / "bridge.ts").read_text(encoding="utf-8")
bloco = texto_bridge[texto_bridge.index("const NOMES = ["):texto_bridge.index("] as const satisfies")]
for nome in NOVOS:
    assert f'"{nome}"' in bloco, f"PCE-08 {nome} fora da lista NOMES do bridge.ts"
    assert callable(getattr(ponte, nome, None)), f"PCE-08 Ponte sem {nome}"
# Spec 030: a demonstração em memória saiu do app e virou fixture dos testes da tela.
demo = (RAIZ / "painel" / "app" / "scripts" / "testes" / "fixtures" / "demo-backend.ts").read_text(encoding="utf-8")
assert all(f"async {nome}(" in demo for nome in NOVOS), "PCE-08 fixture da tela sem os métodos novos"
assert not [n for n in vars(ponte) if not n.startswith("_")], "a Ponte não expõe atributo público ao JavaScript"
ok("PCE-08 central_* e remotos_* na Ponte, na lista NOMES do bridge.ts e no fixture dos testes da tela")

# Antes de conectar: nada criado, estado claro ------------------------------------------------------------------------------
estado = dados(ponte.central_estado())
assert estado["conectado"] is False and estado["endereco"] == modulo_central.ENDERECO_PADRAO
assert estado["endereco_padrao"] == "https://rotaguard.acexpartners.com.br"
listado = dados(ponte.remotos_listar())
assert listado["aparelhos"] == [] and listado["sessoes"] == [] and listado["central"]["conectado"] is False
assert not (pasta / modulo_central.ARQUIVO_TOKEN).exists()
for invalido in ("rotaguard.acexpartners.com.br", "ftp://x", "http://exemplo.com", "https://user:x@exemplo.com",
                 "https://exemplo.com/?a=1", ""):
    resposta = erro(ponte.central_conectar(invalido, "gestor@viacao.test", SENHA_CENTRAL), "invalido", invalido)
    assert resposta.get("campo") == "endereco", resposta
assert ESTADO.contar("/api/auth/login") == 0, "endereço inválido não chega a pedir nada"
ok("antes de conectar: endereço padrão https://rotaguard.acexpartners.com.br; endereço sem https (fora do 127.0.0.1) é recusado")

# PCE-02 -------------------------------------------------------------------------------------------------------------------
recusa = erro(ponte.central_conectar(ENDERECO, "gestor@viacao.test", "senha errada da central"), "invalido", "PCE-02")
assert recusa.get("campo") == "senha" and "incorret" in recusa["erro"], recusa
assert dados(ponte.central_estado())["conectado"] is False
assert not (pasta / modulo_central.ARQUIVO_TOKEN).exists(), "PCE-02 senha errada não guarda token"
assert b"senha errada da central" not in bytes_da_pasta(pasta)
entrar_como(ponte, "paulo.reis", adicionado["senha_temporaria"])
erro(ponte.central_conectar(ENDERECO, "gestor@viacao.test", SENHA_CENTRAL), "sem_permissao", "supervisor conecta")
dados(ponte.trocar_senha(adicionado["senha_temporaria"], SENHA_SUP))
entrar_como(ponte, "marina.lopes", SENHA_ADM)
ok("PCE-02 senha errada: erro no campo senha, nada guardado; só o administrador (configurações) conecta")

# PCE-01 -------------------------------------------------------------------------------------------------------------------
ESTADO.funcao = "motorista"
recusa = erro(ponte.central_conectar(ENDERECO, "gestor@viacao.test", SENHA_CENTRAL), "sem_permissao", "motorista")
assert not (pasta / modulo_central.ARQUIVO_TOKEN).exists()
ESTADO.funcao = "gestor"
conectado = dados(ponte.central_conectar(ENDERECO + "/", "gestor@viacao.test", SENHA_CENTRAL), "PCE-01")
assert conectado["conectado"] is True and conectado["usuario"]["nome"] == "Gestor da Viação"
assert conectado["empresa"]["nome"] == "Viação Teste" and conectado["endereco"] == ENDERECO
login = [p for p in ESTADO.pedidos if p[1] == "/api/auth/login"][-1]
assert login[2].get("x-drivesafe") == "1" and login[2].get("x-rotaguard-cliente") == "painel"
guardado = (pasta / modulo_central.ARQUIVO_TOKEN).read_bytes()
assert TOKEN.encode() not in guardado or not conectado["token_protegido"], "PCE-01 token protegido no Windows"
if sys.platform == "win32":
    assert conectado["token_protegido"] is True and guardado.startswith(b"dpapi:"), "PCE-01 DPAPI no Windows"
tudo = bytes_da_pasta(pasta)
assert SENHA_CENTRAL.encode() not in tudo and SENHA_CENTRAL.encode("utf-16-le") not in tudo, "PCE-01 senha gravada"
assert modulo_central.desproteger(guardado.decode("ascii")) == TOKEN.encode()
ok(f"PCE-01 conectar guarda só o token ({'DPAPI' if conectado['token_protegido'] else 'sem proteção'}); "
   "a senha não aparece em nenhum arquivo da pasta; gestor ou administrador da central")

# PCE-03 -------------------------------------------------------------------------------------------------------------------
resultado = ponte._central().buscar()
assert resultado["ok"] and ESTADO.contar("/api/sync/novidades") == 2, resultado
novidades = [p for p in ESTADO.pedidos if p[1].startswith("/api/sync/novidades")]
assert all(p[2].get("authorization") == f"Bearer {TOKEN}" for p in novidades) and "desde=c1" in novidades[1][1]
listado = dados(ponte.remotos_listar())
assert [a["uid"] for a in listado["aparelhos"]] == [uid(1), uid(2)], listado["aparelhos"]
assert listado["aparelhos"][0]["testando_agora"] is True and listado["aparelhos"][0]["risco_atual"] == 2
assert [s["uid"] for s in listado["sessoes"]] == [uid(11), uid(12)], "sessões da mais nova para a mais velha"
primeira = listado["sessoes"][0]
assert primeira["eventos"] == 2 and primeira["trechos"] == 2 and primeira["aparelho_nome"] == "Notebook da Ana"
assert primeira["resumo"]["perclos_medio"] == 0.08 and primeira["em_andamento"] is True
for _ in range(2):  # sem o cursor, a central devolve tudo de novo: nada pode duplicar
    ponte._central()._cursor_zerar()
    assert ponte._central().buscar()["ok"]
banco = ponte._central()._banco()
for tabela, total in (("aparelhos", 2), ("sessoes", 2), ("eventos", 3), ("trechos", 2)):
    assert banco.um(f"SELECT COUNT(*) AS n FROM central_{tabela}")["n"] == total, f"PCE-03 {tabela} duplicou"
sessao = dados(ponte.remotos_sessao(uid(11)))
assert [e["tipo"] for e in sessao["eventos"]] == ["microssono", "uso_celular"], "linha do tempo em ordem"
assert sessao["eventos"][0]["detalhes"] == {"olho": 0.1}, "dado de cardio não fica no painel"
assert [t["uid"] for t in sessao["trechos"]] == [uid(21), uid(22)] and sessao["pode_ver_trechos"] is True
erro(ponte.remotos_sessao("../../etc"), "nao_encontrado")
mudado = {**APARELHOS[1], "nome": "Desktop da oficina", "alterado_em": iso(T0 + 10)}
ESTADO.paginas["c2"] = ({"aparelhos": [mudado], "eventos": [EVENTOS[0]]}, "c3", False)
assert ponte._central().buscar()["ok"]
listado = dados(ponte.remotos_listar())
assert listado["aparelhos"][1]["nome"] == "Desktop da oficina"
assert banco.um("SELECT COUNT(*) AS n FROM central_eventos")["n"] == 3
ok("PCE-03 busca com cursor (Bearer) grava aparelhos, sessões, eventos e trechos sem duplicar; mudança atualiza; "
   "chaves de cardio descartadas")

# PCE-04 -------------------------------------------------------------------------------------------------------------------
arquivo_mp4 = pasta / "trechos" / f"{uid(21)}.mp4"
arquivo_clip = pasta / "trechos" / f"{uid(22)}.rgclip"
assert arquivo_mp4.read_bytes() == MP4 and arquivo_clip.read_bytes() == RGCLIP, "trechos baixados"
arquivo_mp4.unlink()
ESTADO.corromper.add(uid(21))
banco.executar("UPDATE central_trechos SET arquivo = NULL, sha_local = NULL WHERE uid = ?", (uid(21),))
assert ponte._central().buscar()["ok"]
linha = banco.um("SELECT * FROM central_trechos WHERE uid = ?", (uid(21),))
assert not arquivo_mp4.exists() and linha["arquivo"] is None and linha["tentativas"] == 1 and linha["erro"], dict(linha)
assert not list((pasta / "trechos").glob("*.parte")), "sobra de download descartada"
visto = dados(ponte.remotos_trecho(uid(21)))
assert visto["disponivel"] is False and visto["motivo"], visto
assert ponte._central().buscar()["ok"]
assert arquivo_mp4.read_bytes() == MP4 and banco.um("SELECT erro FROM central_trechos WHERE uid = ?",
                                                     (uid(21),))["erro"] is None
ok("PCE-04 trecho com SHA-256 diferente é descartado e baixado de novo na busca seguinte")

# Trecho no player: endereço do servidor da janela, com segredo; .rgclip vira quadros ------------------------------------------
visto = dados(ponte.remotos_trecho(uid(21)))
assert visto["disponivel"] and visto["formato"] == "mp4" and visto["mime"] == "video/mp4"
segredo = ponte._rota_trechos()["segredo"]
assert visto["url"] == f"/__trechos/{segredo}/{uid(21)}.mp4", visto["url"]
clip = dados(ponte.remotos_trecho(uid(22)))
assert clip["formato"] == "rgclip" and [q["t"] for q in clip["quadros"]] == [0, 1 / 15, 2 / 15]
assert clip["quadros"][1]["url"] == f"/__trechos/{segredo}/{uid(22)}/q/1.jpg" and clip["largura"] == 640
interface = Path(tmp) / "out"
interface.mkdir()
(interface / "index.html").write_text("<html lang='pt-BR'><body>painel</body></html>", encoding="utf-8")
servidor = rp.iniciar_servidor(interface)
servidor.trechos = ponte._rota_trechos()
base = f"http://127.0.0.1:{servidor.server_address[1]}"
try:
    with abrir_url(base + visto["url"]) as resposta:
        assert resposta.status == 200 and resposta.read() == MP4 and resposta.headers["Content-Type"] == "video/mp4"
        assert resposta.headers["Cache-Control"] == "no-store" and resposta.headers["Accept-Ranges"] == "bytes"
    pedido = urllib.request.Request(base + visto["url"], headers={"Range": "bytes=4-11"})
    with abrir_url(pedido) as resposta:
        assert resposta.status == 206 and resposta.read() == MP4[4:12]
        assert resposta.headers["Content-Range"] == f"bytes 4-11/{len(MP4)}"
    with abrir_url(base + clip["quadros"][2]["url"]) as resposta:
        assert resposta.read() == JPEG[2] and resposta.headers["Content-Type"] == "image/jpeg"
    for ruim in (f"/__trechos/{'x' * len(segredo)}/{uid(21)}.mp4", f"/__trechos/{segredo}/../central.db",
                 f"/__trechos/{segredo}/{uid(21)}.rgclip", f"/__trechos/{segredo}/{uid(22)}/q/9.jpg",
                 f"/__trechos/{segredo}/%2e%2e%5ccentral.token", "/__trechos/", f"/__trechos/{segredo}/{uid(99)}.mp4"):
        try:
            abrir_url(base + ruim)
            raise AssertionError(f"servidor entregou {ruim}")
        except urllib.error.HTTPError as falha:
            assert falha.code == 404, (ruim, falha.code)
    with abrir_url(base + "/") as resposta:
        assert b"painel" in resposta.read(), "a interface continua sendo servida"
finally:
    rp.parar_servidor(servidor)
atividades = dados(ponte.atividades_listar({}))["itens"]
assert any(a["acao"] == "abriu trecho" for a in atividades)
ok("trecho tocável: MP4 com Range e .rgclip em quadros JPEG pelo servidor da janela, só com o segredo; "
   "caminho estranho dá 404; abrir registra atividade")

# PCE-07 -------------------------------------------------------------------------------------------------------------------
entrar_como(ponte, "paulo.reis", SENHA_SUP)
assert dados(ponte.remotos_trecho(uid(21)))["disponivel"] is True, "supervisor vê trecho"
erro(ponte.central_gerar_codigo("Outro"), "sem_permissao", "supervisor não gera código")
entrar_como(ponte, "marina.lopes", SENHA_ADM)
ana = next(p for p in dados(ponte.equipe_listar()) if p["usuario"] == "ana.souza")
temporaria = dados(ponte.equipe_nova_senha(ana["id"]))["senha_temporaria"]
entrar_como(ponte, "ana.souza", temporaria)
dados(ponte.trocar_senha(temporaria, SENHA_CON))
assert dados(ponte.remotos_listar())["sessoes"], "Consulta vê as sessões"
sessao_consulta = dados(ponte.remotos_sessao(uid(11)))
assert sessao_consulta["pode_ver_trechos"] is False and sessao_consulta["trechos"] == [], sessao_consulta
assert sessao_consulta["eventos"], "Consulta vê a linha do tempo"
erro(ponte.remotos_trecho(uid(21)), "sem_permissao", "PCE-07 consulta abre trecho")
erro(ponte.central_conectar(ENDERECO, "gestor@viacao.test", SENHA_CENTRAL), "sem_permissao", "consulta conecta")
entrar_como(ponte, "marina.lopes", SENHA_ADM)
ok("PCE-07 supervisor (ver_video) abre trecho; Consulta vê computadores, sessões e linha do tempo, mas não os "
   "trechos; nenhum dos dois conecta nem gera código")

# PCE-06 -------------------------------------------------------------------------------------------------------------------
codigo = dados(ponte.central_gerar_codigo("Notebook da Ana"), "PCE-06")
assert codigo["codigo"] == "ABCD-2345" and codigo["validade_min"] == 30 and codigo["expira_em"].endswith("Z")
pedido = [p for p in ESTADO.pedidos if p[1] == "/api/pareamento/codigos"][-1]
assert pedido[2].get("authorization") == f"Bearer {TOKEN}" and pedido[2].get("x-drivesafe") == "1"
atividades = dados(ponte.atividades_listar({}))["itens"]
gerou = next(a for a in atividades if a["acao"] == "gerou código para outro computador")
assert gerou["alvo"] == "Notebook da Ana" and "ABCD" not in json.dumps(gerou), "o código não vai para o registro"
erro(ponte.central_gerar_codigo("x" * 200), "invalido", "nome comprido")
ok("PCE-06 gerar código mostra ABCD-2345, a validade de 30 min e o horário; o código não fica no registro")

# PCE-05 -------------------------------------------------------------------------------------------------------------------
central_http.shutdown()
central_http.server_close()
resultado = ponte._central().buscar()
assert resultado["ok"] is False
estado = dados(ponte.central_estado())
assert estado["conectado"] is True and estado["sem_conexao"] is True and estado["ultimo_erro"], estado
listado = dados(ponte.remotos_listar())
assert listado["central"]["sem_conexao"] is True and len(listado["sessoes"]) == 2, "PCE-05 mostra o que já baixou"
assert dados(ponte.remotos_trecho(uid(21)))["disponivel"] is True, "trecho baixado toca sem a central"
relogio[0] += 120
assert not any(a["testando_agora"] for a in dados(ponte.remotos_listar())["aparelhos"]), "sinal velho não é 'testando'"
erro(ponte.central_gerar_codigo("Outro"), "invalido", "gerar código sem conexão")
assert not ponte._falhas, ponte._falhas
ok("PCE-05 central fora do ar: estado sem_conexao, os dados e trechos já baixados continuam; nada quebra")

# PCE-09 -------------------------------------------------------------------------------------------------------------------
central_http = subir_central()
ENDERECO2 = f"http://127.0.0.1:{central_http.server_address[1]}"
ESTADO.paginas["c3"] = ({}, "c3", False)
relogio2 = [T0]
outra_pasta = Path(tmp) / "outra"
vigiada = nova_ponte(outra_pasta, relogio2, intervalo_s=0.05)
dados(vigiada.ativar_local(EMPRESA, ADMIN))
vigiada._iniciar_central()
time.sleep(0.3)
antes = ESTADO.contar("/api/sync/novidades")
time.sleep(0.3)
assert ESTADO.contar("/api/sync/novidades") == antes, "sem token, a vigia não busca"
dados(vigiada.central_conectar(ENDERECO2, "gestor@viacao.test", SENHA_CENTRAL))
for _ in range(100):
    if ESTADO.contar("/api/sync/novidades") >= antes + 3:
        break
    time.sleep(0.05)
assert ESTADO.contar("/api/sync/novidades") >= antes + 3, "PCE-09 vigia busca sozinha quando conectado"
assert dados(vigiada.remotos_listar())["sessoes"], "a vigia gravou"
dados(vigiada.central_desconectar(), "PCE-09")
time.sleep(0.2)
parado = ESTADO.contar("/api/sync/novidades")
time.sleep(0.4)
assert ESTADO.contar("/api/sync/novidades") == parado, "PCE-09 depois de desconectar a busca para"
assert not (outra_pasta / modulo_central.ARQUIVO_TOKEN).exists(), "PCE-09 token apagado"
assert any(p[1] == "/api/auth/logout" for p in ESTADO.pedidos), "avisa a central que saiu"
estado = dados(vigiada.central_estado())
assert estado["conectado"] is False and estado["endereco"] == ENDERECO2
assert dados(vigiada.remotos_listar())["sessoes"], "PCE-09 mantém o que já foi baixado"
assert (outra_pasta / "trechos" / f"{uid(21)}.mp4").exists()
acoes = [a["acao"] for a in dados(vigiada.atividades_listar({}))["itens"]]
assert "conectou à central" in acoes and "desconectou da central" in acoes
vigiada._parar_central()
assert not vigiada._central()._linha_viva(), "vigia parou"
ok("PCE-09 desconectar apaga o token e para a vigia (30 s; aqui 0,05 s), mantendo sessões e trechos baixados")

# Token vindo no corpo do login e token que expirou ----------------------------------------------------------------------
ESTADO.token_no_corpo = True
dados(vigiada.central_conectar(ENDERECO2, "gestor@viacao.test", SENHA_CENTRAL), "token no corpo")
ESTADO.token_no_corpo = False
vigiada._central()._token_trocar("tok_que_expirou")
resultado = vigiada._central().buscar()
estado = dados(vigiada.central_estado())
assert resultado["ok"] is False and estado["conectado"] is False and "de novo" in (estado["ultimo_erro"] or ""), estado
ok("token no corpo do login também vale; sessão vencida na central desconecta e pede para conectar de novo")

# Leitura do .rgclip é tolerante e segura --------------------------------------------------------------------------------------
pasta_clip = Path(tmp) / "clips"
pasta_clip.mkdir()
sem_indice = pasta_clip / "a.rgclip"
with zipfile.ZipFile(sem_indice, "w") as pacote:
    for i, quadro in enumerate(JPEG):
        pacote.writestr(f"{i:04d}.jpg", quadro)
    pacote.writestr("../fora.jpg", JPEG[0])
lido = modulo_central.ler_rgclip(sem_indice)
assert [q["arquivo"] for q in lido["quadros"]] == ["0000.jpg", "0001.jpg", "0002.jpg"] and lido["fps"] == 15
com_strings = pasta_clip / "b.rgclip"
with zipfile.ZipFile(com_strings, "w") as pacote:
    pacote.writestr("indice.json", json.dumps({"fps": 10, "quadros": ["x.jpg", "nao-existe.jpg", "y.jpg"]}))
    pacote.writestr("x.jpg", JPEG[0])
    pacote.writestr("y.jpg", JPEG[1])
assert [(q["arquivo"], q["t"]) for q in modulo_central.ler_rgclip(com_strings)["quadros"]] == [("x.jpg", 0.0),
                                                                                                ("y.jpg", 0.2)]
ok(".rgclip: indice.json com objetos ou nomes, ou só os JPEGs em ordem; nome de fora do pacote é ignorado")

central_http.shutdown()
central_http.server_close()
print(f"\n{checks} verificações OK")
