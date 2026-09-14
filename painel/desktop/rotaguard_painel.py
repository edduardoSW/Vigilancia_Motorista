"""RotaGuard Painel no computador (spec 013): a interface exportada do painel numa janela nativa.

A janela é do pywebview com o WebView2 do Windows. A interface (exportação estática do Next.js, com endereços
absolutos /_next/...) é servida por um servidor HTTP interno, só em 127.0.0.1 e em porta aleatória: a pessoa nunca vê
navegador, barra de endereço ou servidor.

Uso:
  python painel/desktop/rotaguard_painel.py              abre o painel
  python painel/desktop/rotaguard_painel.py --verificar  teste de fumaça com janela oculta: uma linha JSON, código 0 se ok
  python painel/desktop/rotaguard_painel.py --depurar    fora do pacote: liga as ferramentas de desenvolvedor
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import socketserver
import sys
import threading
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

from ponte import Ponte  # js_api: login, cadastros e decisões passam pela ponte, não por rota HTTP (spec 014)

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]

TITULO = "RotaGuard"
LARGURA, ALTURA = 1440, 900
LARGURA_MINIMA, ALTURA_MINIMA = 1200, 760
HOST = "127.0.0.1"
MOTOR_ESPERADO = "edgechromium"
IDIOMA_ESPERADO = "pt-BR"
AVISO_OBRIGATORIO = "dados fictícios"
TEMPO_LIMITE_VERIFICACAO_S = 60
MARGEM_FECHAMENTO_S = 5.0  # sobra do limite para fechar a janela e imprimir o resultado
SAIDA_OK, SAIDA_FALHA = 0, 1

SCRIPT_IDIOMA = "document.documentElement.lang"
SCRIPT_TEXTO = "document.body ? document.body.innerText : ''"
SCRIPT_SCRIPTS = "Boolean(window.next)"  # o app-bootstrap do Next define window.next: os scripts rodaram

MENSAGEM_SEM_WEBVIEW2 = (
    "O RotaGuard precisa do Microsoft Edge WebView2 Runtime, que não foi encontrado neste computador. "
    "Instale a versão Evergreen do WebView2 Runtime, no site da Microsoft, e abra o RotaGuard de novo."
)

TIPOS_MIME = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json",
    ".map": "application/json",
    # Payloads RSC da exportação: no modo export, o roteador do Next aceita text/plain (fetch-server-response.js).
    ".txt": "text/plain; charset=utf-8",
    ".woff2": "font/woff2",
    ".woff": "font/woff",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".ico": "image/x-icon",
    ".webmanifest": "application/manifest+json",
}
TIPO_PADRAO = "application/octet-stream"

# Só o que vem do próprio app (sem rede externa). Scripts e estilos em linha: a exportação do Next depende deles.
POLITICA_DE_CONTEUDO = "; ".join((
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:",
    "font-src 'self' data:",
    "connect-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
))


# ---------------------------------------------------------------------------------------------------------------------
# Pastas
# ---------------------------------------------------------------------------------------------------------------------
def esta_congelado() -> bool:
    return bool(getattr(sys, "frozen", False))


def _pasta_do_pacote(meipass) -> Path:
    if meipass is not None:
        return Path(meipass)
    return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))


def pasta_interface(congelado: bool | None = None, meipass=None) -> Path:
    """Exportação estática do painel: painel/app/out fora do pacote; _internal/interface (sys._MEIPASS) dentro dele."""
    if esta_congelado() if congelado is None else congelado:
        return _pasta_do_pacote(meipass) / "interface"
    return AQUI.parent / "app" / "out"


def caminho_icone(congelado: bool | None = None, meipass=None) -> Path:
    if esta_congelado() if congelado is None else congelado:
        return _pasta_do_pacote(meipass) / "rotaguard.ico"
    return RAIZ / "implantacao" / "app-teste" / "rotaguard.ico"


# ---------------------------------------------------------------------------------------------------------------------
# URL → arquivo
# ---------------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Resposta:
    status: int
    arquivo: Path | None  # None: 404 e a exportação não tem 404.html


# Barra invertida (outra forma de separar pasta no Windows), ":" (unidade de disco e fluxo alternativo do NTFS) e byte nulo.
_PROIBIDOS_NO_SEGMENTO = ("\\", ":", "\x00")


def _segmento_invalido(segmento: str) -> bool:
    return segmento in (".", "..") or any(caractere in segmento for caractere in _PROIBIDOS_NO_SEGMENTO)


def tipo_mime(caminho) -> str:
    return TIPOS_MIME.get(Path(caminho).suffix.lower(), TIPO_PADRAO)


def resolver(raiz, alvo: str) -> Resposta:
    """Mapeia o caminho pedido para um arquivo da exportação, sem nunca sair da pasta da interface.

    Pasta (com ou sem a barra final) → index.html; arquivo que não existe → <caminho>.html; o resto → 404.html.
    A consulta (?...) e o trecho (#...) são ignorados; os escapes (%20, %2e...) são decodificados antes da conferência.
    """
    raiz = Path(raiz).resolve()
    caminho = unquote(alvo.split("#", 1)[0].split("?", 1)[0])
    partes = caminho.split("/")
    if any(_segmento_invalido(parte) for parte in partes):
        return _nao_encontrado(raiz)
    segmentos = [parte for parte in partes if parte]
    candidato = raiz.joinpath(*segmentos)
    if not segmentos or caminho.endswith("/") or candidato.is_dir():
        opcoes = [candidato / "index.html"]
    else:
        opcoes = [candidato, candidato.with_name(candidato.name + ".html")]
    for opcao in opcoes:
        real = opcao.resolve()
        if real.is_relative_to(raiz) and real.is_file():
            return Resposta(200, real)
    return _nao_encontrado(raiz)


def _nao_encontrado(raiz: Path) -> Resposta:
    pagina = raiz / "404.html"
    return Resposta(404, pagina if pagina.is_file() else None)


# ---------------------------------------------------------------------------------------------------------------------
# Servidor local
# ---------------------------------------------------------------------------------------------------------------------
class ManipuladorInterface(BaseHTTPRequestHandler):
    """GET e HEAD dos arquivos da interface. Outros métodos recebem o 501 padrão da biblioteca."""

    server_version = "RotaGuard"
    sys_version = ""

    def do_GET(self) -> None:  # noqa: N802 - nome exigido pelo http.server
        self._responder(com_corpo=True)

    def do_HEAD(self) -> None:  # noqa: N802 - nome exigido pelo http.server
        self._responder(com_corpo=False)

    def _responder(self, com_corpo: bool) -> None:
        resposta = resolver(self.server.raiz, self.path)
        if resposta.arquivo is None:
            dados, tipo = "Não encontrado".encode("utf-8"), "text/plain; charset=utf-8"
        else:
            dados, tipo = resposta.arquivo.read_bytes(), tipo_mime(resposta.arquivo)
        self.send_response(resposta.status)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(dados)))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", POLITICA_DE_CONTEUDO)
        self.end_headers()
        if com_corpo:
            self.wfile.write(dados)

    def log_message(self, format, *args) -> None:  # noqa: A002 - assinatura do http.server
        """Sem registro de acesso: o executável de janela não tem console."""


class ServidorInterface(ThreadingHTTPServer):
    """Servidor da interface: só 127.0.0.1, porta escolhida pelo sistema, sem compartilhar a porta."""

    daemon_threads = True
    allow_reuse_address = False
    allow_reuse_port = False

    def __init__(self, raiz, porta: int = 0) -> None:
        self.raiz = Path(raiz).resolve()
        self.linha: threading.Thread | None = None
        super().__init__((HOST, porta), ManipuladorInterface)

    def server_bind(self) -> None:
        # No Windows, outro programa não consegue se ligar à mesma porta enquanto o painel está aberto.
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        # O HTTPServer.server_bind consulta o nome do computador (getfqdn); aqui basta o endereço local.
        socketserver.TCPServer.server_bind(self)
        self.server_name, self.server_port = HOST, self.server_address[1]

    def handle_error(self, request, client_address) -> None:
        """A janela cancela requisições ao trocar de tela; sem console, não há onde mostrar o erro."""


def iniciar_servidor(raiz, porta: int = 0) -> ServidorInterface:
    servidor = ServidorInterface(raiz, porta)
    servidor.linha = threading.Thread(target=servidor.serve_forever, kwargs={"poll_interval": 0.2},
                                      name="rotaguard-interface", daemon=True)
    servidor.linha.start()
    return servidor


def parar_servidor(servidor: ServidorInterface) -> None:
    servidor.shutdown()
    servidor.server_close()
    if servidor.linha is not None:
        servidor.linha.join(timeout=5)


def url_da_janela(porta: int) -> str:
    return f"http://{HOST}:{porta}/"


# ---------------------------------------------------------------------------------------------------------------------
# Janela
# ---------------------------------------------------------------------------------------------------------------------
def opcoes_da_janela(url: str, oculta: bool) -> dict:
    """Argumentos do webview.create_window. Seleção de texto e zoom ficam no padrão do pywebview."""
    return {"title": TITULO, "url": url, "width": LARGURA, "height": ALTURA,
            "min_size": (LARGURA_MINIMA, ALTURA_MINIMA), "hidden": oculta}


def opcoes_de_inicio(congelado: bool, depurar: bool, icone) -> dict:
    """Argumentos do webview.start: ferramentas de desenvolvedor só fora do pacote e com --depurar; modo privado."""
    opcoes = {"debug": bool(depurar and not congelado), "private_mode": True}
    if icone is not None and Path(icone).is_file():
        opcoes["icon"] = str(icone)
    return opcoes


def aceitar_motor(motor) -> bool:
    """Sem WebView2, o pywebview cai no MSHTML (Internet Explorer), que não roda a interface: só edgechromium serve."""
    return motor == MOTOR_ESPERADO


# ---------------------------------------------------------------------------------------------------------------------
# Verificação oculta (--verificar)
# ---------------------------------------------------------------------------------------------------------------------
def resultado_verificacao(idioma, texto, scripts=None) -> dict:
    """ok só com lang pt-BR e o aviso "dados fictícios" no texto (sem diferenciar maiúsculas: innerText aplica CSS)."""
    texto = texto if isinstance(texto, str) else ""
    aviso = AVISO_OBRIGATORIO in texto.casefold()
    motivos = []
    if idioma != IDIOMA_ESPERADO:
        motivos.append(f"lang={idioma!r}, esperado {IDIOMA_ESPERADO!r}")
    if not aviso:
        motivos.append(f"o texto da página não tem {AVISO_OBRIGATORIO!r}")
    resultado = {"ok": not motivos, "lang": idioma, "aviso_dados_ficticios": aviso, "caracteres": len(texto)}
    if scripts is not None:
        resultado["scripts"] = bool(scripts)
    if motivos:
        resultado["erro"] = "; ".join(motivos)
    return resultado


def verificar_janela(janela, tempo_limite_s: float) -> dict:
    if not janela.events.loaded.wait(max(0.0, tempo_limite_s)):
        return {"ok": False, "erro": f"a interface não carregou em {max(0.0, tempo_limite_s):.0f} s"}
    return resultado_verificacao(janela.evaluate_js(SCRIPT_IDIOMA), janela.evaluate_js(SCRIPT_TEXTO),
                                 janela.evaluate_js(SCRIPT_SCRIPTS))


def _verificar_e_fechar(janela, estado: dict, inicio: float) -> None:
    """Roda numa thread do pywebview enquanto a janela oculta carrega; fecha a janela no fim."""
    try:
        restante = TEMPO_LIMITE_VERIFICACAO_S - MARGEM_FECHAMENTO_S - (time.monotonic() - inicio)
        estado["resultado"] = verificar_janela(janela, restante)
    except Exception as erro:  # JavascriptException do evaluate_js, janela que não iniciou
        estado["resultado"] = {"ok": False, "erro": f"{type(erro).__name__}: {erro}"}
    finally:
        janela.destroy()


def linha_json(resultado: dict) -> str:
    return json.dumps(resultado, ensure_ascii=True)


def emitir(linha: str) -> None:
    """Saída padrão, quando existe (o executável de janela aberto sem redirecionamento não tem)."""
    if sys.stdout is not None:
        sys.stdout.write(linha + "\n")
        sys.stdout.flush()


class SaidaUnica:
    """Uma linha JSON só por execução, mesmo se o vigia estourar junto com o fim normal."""

    def __init__(self, imprimir=emitir) -> None:
        self._imprimir, self._trava, self.enviada = imprimir, threading.Lock(), False

    def enviar(self, resultado: dict) -> bool:
        with self._trava:
            if self.enviada:
                return False
            self.enviada = True
        self._imprimir(linha_json(resultado))
        return True


def iniciar_vigia(tempo_s: float, saida: SaidaUnica, encerrar=os._exit) -> threading.Timer:
    """Limite rígido da verificação: se a janela travar, imprime o erro e encerra o processo inteiro com 1."""
    def estourou() -> None:
        if saida.enviar({"ok": False, "erro": f"tempo esgotado: {tempo_s:g} s sem concluir a verificação"}):
            encerrar(SAIDA_FALHA)

    vigia = threading.Timer(tempo_s, estourou)
    vigia.daemon = True
    vigia.start()
    return vigia


# ---------------------------------------------------------------------------------------------------------------------
# Programa
# ---------------------------------------------------------------------------------------------------------------------
def avisar_usuario(mensagem: str) -> None:
    """Erro para quem abriu o app. No pacote (sem console), numa caixa de mensagem do Windows."""
    if sys.stderr is not None:
        print(mensagem, file=sys.stderr)
    if sys.platform == "win32" and esta_congelado():
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, mensagem, TITULO, 0x10)  # MB_ICONERROR


def ler_argumentos(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="RotaGuardPainel", description="Painel da empresa RotaGuard em janela própria.")
    parser.add_argument("--verificar", action="store_true",
                        help="teste de fumaça com janela oculta: imprime uma linha JSON e sai com 0 se a interface "
                             "carregou em pt-BR com o aviso de dados fictícios")
    parser.add_argument("--depurar", action="store_true",
                        help="fora do pacote: liga as ferramentas de desenvolvedor do WebView2")
    # parse_known_args: argumento desconhecido não derruba o app (o executável de janela não tem onde mostrar o erro).
    return parser.parse_known_args(argv)[0]


def _falhar(verificar: bool, saida: SaidaUnica, avisar, erro: str) -> int:
    if verificar:
        saida.enviar({"ok": False, "erro": erro})
    else:
        avisar(erro)
    return SAIDA_FALHA


def main(argv=None, webview_mod=None, raiz=None, congelado: bool | None = None, imprimir=emitir,
         avisar=avisar_usuario, ponte=None) -> int:
    args = ler_argumentos(argv)
    congelado = esta_congelado() if congelado is None else congelado
    raiz = Path(raiz) if raiz is not None else pasta_interface(congelado)
    saida = SaidaUnica(imprimir)
    if not (raiz / "index.html").is_file():
        return _falhar(args.verificar, saida, avisar,
                       f"interface do painel não encontrada em {raiz} (gere com npm run build em painel/app)")

    inicio = time.monotonic()
    estado = {"motor": None, "resultado": None, "erro": None}
    servidor = iniciar_servidor(raiz)
    url = url_da_janela(servidor.server_address[1])
    vigia = iniciar_vigia(TEMPO_LIMITE_VERIFICACAO_S, saida) if args.verificar else None
    try:
        if webview_mod is None:
            import webview as webview_mod
        ponte = ponte if ponte is not None else Ponte()  # não grava nada até a tela chamar
        janela = webview_mod.create_window(**opcoes_da_janela(url, oculta=args.verificar), js_api=ponte)
        ponte._ligar_janela(janela)  # privado de propósito: o pywebview expõe ao JavaScript só o que é público

        def conferir_motor(motor):
            estado["motor"] = motor
            return aceitar_motor(motor)  # False faz o pywebview desistir de abrir a janela

        janela.events.initialized += conferir_motor
        opcoes = opcoes_de_inicio(congelado, args.depurar, caminho_icone(congelado))
        if args.verificar:
            webview_mod.start(func=_verificar_e_fechar, args=(janela, estado, inicio), **opcoes)
        else:
            ponte._iniciar_script()  # vigia do script local (agente 2); falha nele não impede o painel
            try:
                webview_mod.start(**opcoes)
            finally:
                ponte._parar_script()
    except Exception as erro:  # pythonnet, WebView2 ou pywebview falhando: vira mensagem, não Traceback mudo
        estado["erro"] = f"{type(erro).__name__}: {erro}"
    finally:
        parar_servidor(servidor)
        if vigia is not None:
            vigia.cancel()

    falha = MENSAGEM_SEM_WEBVIEW2 if estado["motor"] is not None and not aceitar_motor(estado["motor"]) else estado["erro"]
    if not args.verificar:
        if falha:
            avisar(falha)
            return SAIDA_FALHA
        return SAIDA_OK
    resultado = estado["resultado"] or {"ok": False, "erro": falha or "a janela fechou antes da verificação"}
    resultado.update(url=url, motor=estado["motor"], segundos=round(time.monotonic() - inicio, 1))
    saida.enviar(resultado)
    return SAIDA_OK if resultado["ok"] else SAIDA_FALHA


if __name__ == "__main__":
    sys.exit(main())
