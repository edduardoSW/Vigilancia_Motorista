"""Servidor local da tela (spec 023, decisão 2): só em 127.0.0.1, porta livre e token aleatório em todas as rotas.

- GET  /, /index.html, /app.css, /app.js  arquivos de web/ (lista fechada; o token entra no HTML na hora)
- GET  /estado                              JSON com a fase e tudo o que o motor mediu no último quadro
- GET  /video.mjpg                          vídeo com a malha (multipart/x-mixed-replace, até 25 quadros/s)
- GET  /legal                               privacidade, LGPD, termos e licenças (caixa/textos_legais.py)
- GET  /trecho/<uid>                        trecho de vídeo da sessão (spec 026), com Range para o player
- GET  /trecho/<uid>/indice e /quadro/<n>   índice e quadros de um trecho .rgclip (tocado por canvas)
- POST /acao                                {"acao": ..., ...}; Origin precisa ser o próprio endereço

Token na query (?t=) ou no cabeçalho X-RotaGuard-Token. O Host também é conferido (ataque de DNS rebinding).
Nenhum outro programa ou aparelho da rede lê a câmera.
"""
from __future__ import annotations

import hmac
import json
import logging
import re
import secrets
import zipfile
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

import app_teste
import textos_legais
from tela_teste import PASTA_WEB

logger = logging.getLogger("drivesafe.tela.servidor")

HOST = "127.0.0.1"
CABECALHO_TOKEN = "X-RotaGuard-Token"
MARCA_TOKEN = "__TOKEN__"
ARQUIVOS = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/app.css": ("app.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
}
POLITICA = ("default-src 'self'; img-src 'self' data: blob:; style-src 'self'; script-src 'self'; "
            "connect-src 'self'; font-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
FRONTEIRA = "quadro"
MAX_CORPO = 65_536
TIPOS_TRECHO = {"webm": "video/webm", "mp4": "video/mp4", "rgclip": "application/zip"}
ROTA_TRECHO = re.compile(r"^/trecho/([0-9a-f]{32})(?:/(indice|quadro/(\d{1,6})))?$")


class Manipulador(BaseHTTPRequestHandler):
    tela: "ServidorTela"
    server_version = "RotaGuardScript"
    sys_version = ""

    def log_message(self, formato, *args):  # noqa: D401 - sem linha por pedido no registro
        logger.debug("%s %s", self.address_string(), formato % args)

    # ------------------------------------------------------------------ conferências
    def _host_ok(self) -> bool:
        host = (self.headers.get("Host") or "").strip().lower()
        porta = self.tela.porta
        return host in (f"127.0.0.1:{porta}", f"localhost:{porta}")

    def _token_ok(self, consulta: dict) -> bool:
        recebido = (consulta.get("t") or [""])[0] or self.headers.get(CABECALHO_TOKEN, "")
        return bool(recebido) and hmac.compare_digest(recebido.encode("utf-8"), self.tela.token.encode("utf-8"))

    def _origem_ok(self) -> bool:
        origem = self.headers.get("Origin")
        if origem is None:
            return True  # pedido sem navegador (testes, verificação do pacote): o token basta
        porta = self.tela.porta
        return origem in (f"http://127.0.0.1:{porta}", f"http://localhost:{porta}")

    def _autorizar(self):
        partes = urlsplit(self.path)
        consulta = parse_qs(partes.query)
        if not self._host_ok() or not self._token_ok(consulta):
            self._responder(HTTPStatus.FORBIDDEN, b"Acesso negado.", "text/plain; charset=utf-8")
            return None
        self.tela.ultimo_pedido = time.monotonic()
        return partes.path

    # ------------------------------------------------------------------ respostas
    def _cabecalhos(self, status, tipo: str, tamanho: int | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", tipo)
        if tamanho is not None:
            self.send_header("Content-Length", str(tamanho))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", POLITICA)
        self.end_headers()

    def _responder(self, status, corpo: bytes, tipo: str) -> None:
        self._cabecalhos(status, tipo, len(corpo))
        self.wfile.write(corpo)

    def _json(self, status, dados) -> None:
        self._responder(status, json.dumps(dados, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    # ------------------------------------------------------------------ rotas
    def do_GET(self):  # noqa: N802 - nome do http.server
        caminho = self._autorizar()
        if caminho is None:
            return
        try:
            if caminho in ARQUIVOS:
                self._arquivo(*ARQUIVOS[caminho])
            elif caminho == "/estado":
                self._json(HTTPStatus.OK, self.tela.sessao.estado())
            elif caminho == "/video.mjpg":
                self._video()
            elif caminho == "/legal":
                self._json(HTTPStatus.OK, self.tela.textos_legais())
            elif ROTA_TRECHO.fullmatch(caminho):
                self._trecho(*ROTA_TRECHO.fullmatch(caminho).groups())
            else:
                self._responder(HTTPStatus.NOT_FOUND, b"Nada aqui.", "text/plain; charset=utf-8")
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def do_POST(self):  # noqa: N802
        caminho = self._autorizar()
        if caminho is None:
            return
        if caminho != "/acao":
            self._responder(HTTPStatus.NOT_FOUND, b"Nada aqui.", "text/plain; charset=utf-8")
            return
        if not self._origem_ok():
            self._responder(HTTPStatus.FORBIDDEN, b"Origem recusada.", "text/plain; charset=utf-8")
            return
        try:
            tamanho = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            tamanho = -1
        if not 0 < tamanho <= MAX_CORPO:
            self._json(HTTPStatus.BAD_REQUEST, {"ok": False, "erro": "Pedido vazio ou grande demais."})
            return
        try:
            dados = json.loads(self.rfile.read(tamanho).decode("utf-8"))
            if not isinstance(dados, dict) or not isinstance(dados.get("acao"), str):
                raise ValueError("Pedido sem ação.")
            resultado = self.tela.sessao.acao(dados["acao"], dados)
        except (ValueError, UnicodeDecodeError) as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"ok": False, "erro": str(exc)})
            return
        except OSError as exc:
            logger.warning("Ação %s falhou: %s", dados.get("acao"), exc)
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "erro": str(exc)})
            return
        except Exception as exc:  # noqa: BLE001 - erro na ação vira resposta, nunca servidor parado
            logger.exception("Ação %s falhou.", dados.get("acao"))
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "erro": f"{exc.__class__.__name__}: {exc}"})
            return
        self._json(HTTPStatus.OK, {"ok": True, **resultado})

    def _arquivo(self, nome: str, tipo: str) -> None:
        corpo = (PASTA_WEB / nome).read_bytes()
        if nome == "index.html":
            corpo = corpo.replace(MARCA_TOKEN.encode(), self.tela.token.encode())
        self._responder(HTTPStatus.OK, corpo, tipo)

    def _trecho(self, uid: str, parte: str | None, numero: str | None) -> None:
        achado = self.tela.sessao.arquivo_trecho(uid)
        if achado is None:
            self._responder(HTTPStatus.NOT_FOUND, "Trecho não encontrado.".encode("utf-8"), "text/plain; charset=utf-8")
            return
        arquivo, meta = achado
        if parte is not None:
            if meta.get("formato") != "rgclip":
                self._responder(HTTPStatus.NOT_FOUND, b"Nada aqui.", "text/plain; charset=utf-8")
                return
            with zipfile.ZipFile(arquivo) as pacote:
                indice = json.loads(pacote.read("indice.json"))
                if parte == "indice":
                    self._json(HTTPStatus.OK, indice)
                    return
                posicao = int(numero)
                if not 0 <= posicao < len(indice["quadros"]):
                    self._responder(HTTPStatus.NOT_FOUND, b"Nada aqui.", "text/plain; charset=utf-8")
                    return
                self._responder(HTTPStatus.OK, pacote.read(indice["quadros"][posicao]["arquivo"]), "image/jpeg")
            return
        dados = arquivo.read_bytes()
        tipo = TIPOS_TRECHO.get(meta.get("formato"), "application/octet-stream")
        intervalo = re.fullmatch(r"bytes=(\d+)-(\d*)", (self.headers.get("Range") or "").strip())
        if intervalo:
            inicio = int(intervalo.group(1))
            fim = min(int(intervalo.group(2)) if intervalo.group(2) else len(dados) - 1, len(dados) - 1)
            if inicio > fim:
                self.send_response(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
                self.send_header("Content-Range", f"bytes */{len(dados)}")
                self.end_headers()
                return
            parte_dados = dados[inicio:fim + 1]
            self.send_response(HTTPStatus.PARTIAL_CONTENT)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(parte_dados)))
            self.send_header("Content-Range", f"bytes {inicio}-{fim}/{len(dados)}")
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(parte_dados)
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(dados)))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(dados)

    def _video(self) -> None:
        sessao = self.tela.sessao
        self._cabecalhos(HTTPStatus.OK, f"multipart/x-mixed-replace; boundary={FRONTEIRA}")
        visto = -1
        while not self.tela.parando.is_set():
            proximo = sessao.renderizador.proximo(visto, espera=1.0)
            if proximo is None:
                if not sessao.transmitindo:
                    break
                continue
            visto, jpeg = proximo
            self.wfile.write(f"--{FRONTEIRA}\r\nContent-Type: image/jpeg\r\nContent-Length: {len(jpeg)}\r\n\r\n"
                             .encode("ascii") + jpeg + b"\r\n")
            self.wfile.flush()


class ServidorTela:
    def __init__(self, sessao, porta: int = 0, token: str | None = None):
        self.sessao = sessao
        self.token = token or secrets.token_urlsafe(24)
        self.parando = threading.Event()
        self.ultimo_pedido = time.monotonic()
        manipulador = type("ManipuladorDaTela", (Manipulador,), {"tela": self})
        self.httpd = ThreadingHTTPServer((HOST, porta), manipulador)
        self.httpd.daemon_threads = True
        self._thread: threading.Thread | None = None

    @property
    def porta(self) -> int:
        return int(self.httpd.server_address[1])

    @property
    def url(self) -> str:
        return f"http://{HOST}:{self.porta}/?t={self.token}"

    def textos_legais(self) -> dict:
        secoes = textos_legais.secoes(self.sessao.pasta, app_teste.avisos_de_terceiros())
        return {"versao": textos_legais.VERSAO_TEXTOS, "compilacao": getattr(self.sessao, "compilacao", None),
                "secoes": [{"titulo": titulo, "texto": texto} for titulo, texto in secoes]}

    def iniciar(self) -> None:
        self._thread = threading.Thread(target=self.httpd.serve_forever, kwargs={"poll_interval": 0.2},
                                        name="rotaguard-tela-http", daemon=True)
        self._thread.start()
        logger.info("Tela do teste servida em http://%s:%d/ (só este computador).", HOST, self.porta)

    def parar(self) -> None:
        self.parando.set()
        self.sessao.renderizador.limpar()
        self.httpd.shutdown()
        self.httpd.server_close()
        if self._thread is not None:
            self._thread.join(timeout=3)
