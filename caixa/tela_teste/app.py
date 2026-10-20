"""Liga sessão, servidor e janela (spec 023). executar() é a tela do app; verificar() é o teste de fumaça do build."""
from __future__ import annotations

import json
import logging
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

from tela_teste.servidor import CABECALHO_TOKEN, ServidorTela
from tela_teste.sessao import SessaoTeste

logger = logging.getLogger("drivesafe.tela")

NOME_APP = "RotaGuard Script"
TAMANHO = (1360, 860)
TAMANHO_MINIMO = (1024, 640)
COR_FUNDO = "#fafcf7"  # papel do RotaGuard, enquanto a página carrega
# No navegador (sem pywebview) não há aviso de "janela fechada": sem nenhum pedido por 5 min e sem teste, o app sai.
# Aba escondida pode ter os temporizadores reduzidos a 1 por minuto (Chrome), por isso 5 min e não segundos.
NAVEGADOR_OCIOSO_S = 300.0
TIPOS_VIDEO = ("Vídeos (*.mp4;*.avi;*.mov;*.mkv;*.webm)", "Todos os arquivos (*.*)")


def _janela_pywebview(servidor: ServidorTela, sessao: SessaoTeste) -> bool:
    """Abre a janela do pywebview (WebView2 no Windows) e bloqueia até ela fechar. False se não deu para abrir."""
    try:
        import webview
    except ImportError as exc:
        logger.info("pywebview indisponível (%s): a tela abre no navegador padrão.", exc)
        return False
    try:
        # Notebook de 1366 × 768: a janela de 1360 × 860 não cabe; abre maximizada (o vídeo ganha a altura toda).
        try:
            menor = min((tela.height for tela in webview.screens), default=None)
        except Exception:  # noqa: BLE001 - sem a lista de telas, segue o tamanho padrão
            menor = None
        janela = webview.create_window(NOME_APP, servidor.url, width=TAMANHO[0], height=TAMANHO[1],
                                       min_size=TAMANHO_MINIMO, background_color=COR_FUNDO, text_select=True,
                                       maximized=menor is not None and menor < TAMANHO[1] + 60)

        def escolher_arquivo():
            escolhidos = janela.create_file_dialog(webview.FileDialog.OPEN, allow_multiple=False,
                                                   file_types=TIPOS_VIDEO)
            return str(escolhidos[0]) if escolhidos else None

        sessao.escolher_arquivo = escolher_arquivo
        sessao.alternar_tela_cheia = janela.toggle_fullscreen
        sessao.ao_sair = janela.destroy
        webview.start()
        return True
    except Exception as exc:  # noqa: BLE001 - sem WebView2 ou sem GTK/Qt no Linux: segue no navegador
        logger.warning("Janela do pywebview indisponível (%s): a tela abre no navegador padrão.", exc)
        sessao.escolher_arquivo = sessao.alternar_tela_cheia = sessao.ao_sair = None
        return False


def _navegador(servidor: ServidorTela, sessao: SessaoTeste) -> None:
    fechar = threading.Event()
    sessao.ao_sair = fechar.set
    if not webbrowser.open(servidor.url):
        logger.error("Não foi possível abrir o navegador. Abra este endereço: %s", servidor.url)
    try:
        while not fechar.wait(1.0):
            ocioso = time.monotonic() - servidor.ultimo_pedido
            if ocioso >= NAVEGADOR_OCIOSO_S and not sessao.rodando:
                logger.info("Nenhum pedido da tela em %.0f s: encerrando.", ocioso)
                break
    except KeyboardInterrupt:
        logger.info("Interrompido pelo usuário.")


def executar(pasta: Path) -> int:
    sessao = SessaoTeste(Path(pasta))
    servidor = ServidorTela(sessao)
    servidor.iniciar()
    try:
        if not _janela_pywebview(servidor, sessao):
            _navegador(servidor, sessao)
    finally:
        sessao.encerrar()
        servidor.parar()
    logger.info("Tela do teste fechada.")
    return 0


def _pedir(servidor: ServidorTela, caminho: str, corpo: dict | None = None, token: bool = True):
    cabecalhos = {CABECALHO_TOKEN: servidor.token} if token else {}
    dados = None
    if corpo is not None:
        dados = json.dumps(corpo).encode("utf-8")
        cabecalhos.update({"Content-Type": "application/json", "Origin": f"http://127.0.0.1:{servidor.porta}"})
    pedido = urllib.request.Request(f"http://127.0.0.1:{servidor.porta}{caminho}", data=dados, headers=cabecalhos)
    try:
        with urllib.request.urlopen(pedido, timeout=10) as resposta:
            return resposta.status, resposta.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def verificar(pasta: Path) -> int:
    """TEL-16: no pacote, a página, o CSS, o JS e o estado respondem, e sem token nada responde. Não abre câmera."""
    sessao = SessaoTeste(Path(pasta), listar_cameras=lambda: [])
    servidor = ServidorTela(sessao)
    servidor.iniciar()
    falhas = []
    try:
        status, corpo = _pedir(servidor, "/")
        if status != 200 or servidor.token.encode() not in corpo or b"app.js" not in corpo:
            falhas.append(f"página inicial ({status})")
        for caminho in ("/app.css", "/app.js", "/legal"):
            status, corpo = _pedir(servidor, caminho)
            if status != 200 or not corpo:
                falhas.append(f"{caminho} ({status})")
        status, corpo = _pedir(servidor, "/estado")
        if status != 200 or json.loads(corpo).get("fase") != "inicio":
            falhas.append(f"/estado ({status})")
        if _pedir(servidor, "/estado", token=False)[0] != 403:
            falhas.append("/estado sem token não respondeu 403")
        status, corpo = _pedir(servidor, "/acao", {"acao": "malha", "modo": "completa"})
        if status != 200 or json.loads(corpo).get("malha") != "completa":
            falhas.append(f"/acao ({status})")
    finally:
        sessao.encerrar()
        servidor.parar()
    if falhas:
        logger.error("Verificação da tela falhou: %s.", "; ".join(falhas))
        print("Verificação da tela falhou: " + "; ".join(falhas))
        return 1
    logger.info("Verificação da tela OK.")
    print("Verificação da tela OK.")
    return 0
