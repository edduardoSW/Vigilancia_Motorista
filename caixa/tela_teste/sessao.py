"""Sessão da tela do app de teste: fases, câmeras, monitor numa thread, vídeo com a malha e resumo (spec 023).

Fases: inicio → abrindo → calibrando/rodando → resumo (ou erro). "calibrando" é o teste rodando durante a calibração.
O monitoramento é o mesmo do run_monitor (classe Monitoramento), sem janela do OpenCV: a tela recebe cada quadro pelo
gancho DriverMonitor.listeners e desenha a malha numa thread própria, para não atrasar a detecção.
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
import threading
import time
import uuid
from collections import deque
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import run_monitor  # noqa: F401 - define as variáveis do OpenCV no Windows antes de abrir qualquer câmera
import cv2

import app_teste
from tela_teste import resumo as resumo_mod
from tela_teste.central import CentralDoTeste
from tela_teste.estado import medidas, rotulo_evento
from vision import __version__
from vision.camera import CameraIndisponivel, OpenCVCamera
from vision.driver_monitor import MESH_LABELS, MESH_MODES, draw_face_mesh, recent_hands
from vision.risk import HOLD_DOWN_S
from vision.trechos import FPS_TRECHO, LARGURA_TRECHO, GravadorTrechos

logger = logging.getLogger("drivesafe.tela")

FASES = ("inicio", "abrindo", "calibrando", "rodando", "resumo", "erro")
FASES_ATIVAS = ("abrindo", "calibrando", "rodando")
INDICES_CAMERA = range(5)
MALHA_PADRAO = "discreta"  # spec 029: o rosto e o olho aparecem; a completa fica na escolha
CAMERA_IR = ("auto", "sim", "nao")
SERIE_S = 60.0
SERIE_PASSO_S = 0.1
FPS_VIDEO = 25.0  # limite do vídeo para a tela
QUALIDADE_JPEG = 80
LARGURA_VIDEO = 960  # quadro ampliado antes da malha: traço fino e nítido na janela
# Croma 4:4:4: no 4:2:0 (padrão) o traço de 1 px em lima perdia a cor (saturação 140 → 66, medido em 19/10);
# custa ~33 → 49 KB por quadro, só em 127.0.0.1.
PARAMETROS_JPEG = [int(cv2.IMWRITE_JPEG_QUALITY), QUALIDADE_JPEG]
if hasattr(cv2, "IMWRITE_JPEG_SAMPLING_FACTOR"):
    PARAMETROS_JPEG += [int(cv2.IMWRITE_JPEG_SAMPLING_FACTOR), int(cv2.IMWRITE_JPEG_SAMPLING_FACTOR_444)]

DICAS_CAMERA = [
    "Confira se a câmera está conectada e ligada.",
    "Feche Teams, Zoom, Meet ou o navegador se algum deles estiver usando a câmera.",
    "Escolha outra câmera na lista ou um vídeo gravado.",
]


def listar_cameras(indices=INDICES_CAMERA, factory=None, leituras: int = 6, pausa: float = 0.05) -> list[dict]:
    """Câmeras dos índices 0 a 4: "livre" quando abre e manda imagem, "ocupada" quando abre sem imagem (em uso por
    outro programa). As que não abrem ficam de fora. Mesma regra da câmera automática (vision/camera.py)."""
    factory = factory or OpenCVCamera
    encontradas = []
    for indice in indices:
        try:
            camera = factory(str(indice), 640, 480, avisar=False)
        except Exception:  # noqa: BLE001 - driver de câmera estranho não pode derrubar a lista
            continue
        try:
            if not camera.aberta:
                continue
            situacao = "ocupada"
            for _ in range(leituras):
                ok, quadro = camera.read()
                if ok and quadro is not None:
                    situacao = "livre"
                    break
                if pausa:
                    time.sleep(pausa)
            encontradas.append({"valor": str(indice), "nome": f"Câmera {indice + 1}", "situacao": situacao})
        finally:
            camera.release()
    return encontradas


def segundos_para_baixar(fusao, agora: float) -> float | None:
    """Quanto falta para o risco descer um nível se nada mudar (histerese de vision/risk.py). Só leitura: o motor
    guarda em _below_since quando o motivo sumiu; a tela usa para explicar por que o risco não cai na hora."""
    nivel = getattr(fusao, "level", 0) or 0
    desde = getattr(fusao, "_below_since", None)
    if nivel <= 0 or desde is None or nivel not in HOLD_DOWN_S:
        return None
    return max(0.0, HOLD_DOWN_S[nivel] - (agora - desde))


def soltar_arquivos(pasta: Path) -> Callable[[], None]:
    """Fecha o que este processo mantém aberto dentro da pasta (registro do logging e a saída padrão, que no executável
    sem console vai para o registro). No Windows, arquivo aberto não se apaga. Devolve a função que reabre tudo."""
    pasta = Path(pasta).resolve()

    def dentro(nome) -> bool:
        try:
            return isinstance(nome, str) and pasta in Path(nome).resolve().parents
        except (OSError, ValueError):
            return False

    raiz = logging.getLogger()
    soltos = []
    for manipulador in list(raiz.handlers):
        if isinstance(manipulador, logging.FileHandler) and dentro(manipulador.baseFilename):
            raiz.removeHandler(manipulador)
            manipulador.close()
            soltos.append(manipulador)
    fluxos: dict[str, str] = {}
    fechados = set()
    for nome in ("stdout", "stderr"):
        fluxo = getattr(sys, nome, None)
        if fluxo is not None and dentro(getattr(fluxo, "name", None)):
            fluxos[nome] = fluxo.name
            setattr(sys, nome, open(os.devnull, "w", encoding="utf-8"))  # noqa: SIM115
            if id(fluxo) not in fechados:
                fechados.add(id(fluxo))
                fluxo.close()

    def reabrir() -> None:
        for antigo in soltos:
            novo = logging.FileHandler(antigo.baseFilename, encoding=antigo.encoding or "utf-8")
            novo.setFormatter(antigo.formatter)
            novo.setLevel(antigo.level)
            raiz.addHandler(novo)
        abertos: dict[str, object] = {}
        for nome, caminho in fluxos.items():
            vazio = getattr(sys, nome)
            if caminho not in abertos:
                abertos[caminho] = open(caminho, "a", encoding="utf-8", buffering=1)  # noqa: SIM115
            setattr(sys, nome, abertos[caminho])
            vazio.close()

    return reabrir


def fps_do_video(caminho: str) -> float:
    captura = cv2.VideoCapture(caminho)
    try:
        fps = float(captura.get(cv2.CAP_PROP_FPS) or 0.0)
    finally:
        captura.release()
    return fps if 1.0 <= fps <= 240.0 else 30.0


def eh_arquivo(fonte: str) -> bool:
    try:
        return Path(fonte).is_file()
    except (OSError, ValueError):
        return False


class CameraDaTela:
    """Câmera do monitor com duas coisas a mais: vídeo gravado toca no tempo dele (as medidas usam o relógio; sem
    isso, um vídeo de 1 min passava em segundos) e marca quando foi liberada."""

    def __init__(self, camera, fps: float | None = None):
        self.camera = camera
        self.liberada = False
        self._intervalo = 1.0 / fps if fps else None
        self._proximo: float | None = None

    def read(self):
        if self._intervalo:
            agora = time.monotonic()
            if self._proximo is None:
                self._proximo = agora
            if self._proximo > agora:
                time.sleep(self._proximo - agora)
            # Atrasou (análise lenta)? Segue do agora, sem acelerar para compensar.
            self._proximo = max(self._proximo + self._intervalo, time.monotonic() - self._intervalo)
        return self.camera.read()

    def release(self) -> None:
        self.liberada = True
        self.camera.release()

    def __getattr__(self, nome):
        return getattr(self.camera, nome)


def desenhar_jpeg(quadro, estado, maos, modo: str) -> tuple[bytes | None, float]:
    """Quadro ampliado para LARGURA_VIDEO, malha por cima e JPEG. Devolve também o tempo da malha em ms."""
    altura, largura = quadro.shape[:2]
    escala = LARGURA_VIDEO / largura if largura < LARGURA_VIDEO else 1.0
    if escala != 1.0:
        imagem = cv2.resize(quadro, (round(largura * escala), round(altura * escala)), interpolation=cv2.INTER_LINEAR)
    else:
        imagem = quadro.copy()
    inicio = time.perf_counter()
    draw_face_mesh(imagem, estado, modo, hands=maos, scale=escala)
    malha_ms = (time.perf_counter() - inicio) * 1000.0
    ok, codificado = cv2.imencode(".jpg", imagem, PARAMETROS_JPEG)
    return (codificado.tobytes() if ok else None), malha_ms


def jpeg_limpo(quadro) -> bytes | None:
    """O quadro como a câmera mandou, sem nada desenhado, reduzido a LARGURA_TRECHO: é o que vai para os trechos."""
    altura, largura = quadro.shape[:2]
    if largura > LARGURA_TRECHO:
        nova_altura = int(round(altura * LARGURA_TRECHO / largura / 2)) * 2
        quadro = cv2.resize(quadro, (LARGURA_TRECHO, nova_altura), interpolation=cv2.INTER_AREA)
    ok, codificado = cv2.imencode(".jpg", quadro, [int(cv2.IMWRITE_JPEG_QUALITY), QUALIDADE_JPEG])
    return codificado.tobytes() if ok else None


class Renderizador:
    """Desenha a malha e codifica o JPEG numa thread própria, no máximo FPS_VIDEO quadros por segundo.
    Fica sempre com o quadro mais novo: se a tela não der conta, pula quadros em vez de acumular atraso."""

    def __init__(self, modo: Callable[[], str]):
        self._modo = modo
        self._pendente = None
        self._novo = threading.Event()
        self._parar = threading.Event()
        self._condicao = threading.Condition()
        self._thread: threading.Thread | None = None
        self._falhas = 0
        self.jpeg: bytes | None = None
        self.seq = 0
        self.malha_ms: float | None = None
        # Recebe (t, jpeg) do quadro LIMPO, sem a malha (spec 029, MAL-05): o trecho gravado mostra o rosto como a câmera
        # viu; a malha fica só na tela ao vivo. No máximo FPS_TRECHO por segundo, até LARGURA_TRECHO de largura.
        self.ouvinte: Callable[[float, bytes], None] | None = None
        self._ultimo_trecho = -1e9

    def entregar(self, quadro, estado, maos) -> None:
        self._pendente = (quadro, estado, maos)
        if self._thread is None or not self._thread.is_alive():
            self._parar.clear()
            self._thread = threading.Thread(target=self._laco, name="rotaguard-tela-video", daemon=True)
            self._thread.start()
        self._novo.set()

    def _laco(self) -> None:
        ultimo = 0.0
        while not self._parar.is_set():
            if not self._novo.wait(0.5):
                continue
            self._novo.clear()
            espera = 1.0 / FPS_VIDEO - (time.monotonic() - ultimo)
            if espera > 0 and self._parar.wait(espera):
                break
            pendente, self._pendente = self._pendente, None
            if pendente is None:
                continue
            ultimo = time.monotonic()
            try:
                jpeg, malha_ms = desenhar_jpeg(*pendente, modo=self._modo())
            except Exception:  # noqa: BLE001 - falha no desenho não pode parar o teste
                self._falhas += 1
                if self._falhas in (1, 100):
                    logger.exception("Falha ao desenhar o quadro da tela (%d falhas).", self._falhas)
                continue
            if jpeg is None:
                continue
            with self._condicao:
                self.jpeg, self.malha_ms = jpeg, malha_ms
                self.seq += 1
                self._condicao.notify_all()
            ouvinte = self.ouvinte
            if ouvinte is not None:
                try:
                    t = pendente[1].metrics.timestamp
                    if t - self._ultimo_trecho >= 0.9 / FPS_TRECHO:
                        limpo = jpeg_limpo(pendente[0])
                        if limpo is not None:
                            self._ultimo_trecho = t
                            ouvinte(t, limpo)
                except Exception:  # noqa: BLE001
                    logger.exception("Falha ao entregar o quadro ao gravador de trechos.")

    def proximo(self, visto: int, espera: float = 1.0):
        """(seq, jpeg) do quadro mais novo depois de `visto`, ou None se nada chegou no tempo."""
        with self._condicao:
            self._condicao.wait_for(lambda: (self.seq != visto and self.jpeg is not None) or self._parar.is_set(),
                                    timeout=espera)
            if self.seq != visto and self.jpeg is not None:
                return self.seq, self.jpeg
        return None

    def limpar(self) -> None:
        with self._condicao:
            self.jpeg = None
            self.malha_ms = None
            self._condicao.notify_all()

    def parar(self) -> None:
        self._parar.set()
        self._novo.set()
        with self._condicao:
            self._condicao.notify_all()
        if self._thread is not None:
            self._thread.join(timeout=3)


class SessaoTeste:
    def __init__(self, pasta: Path, listar_cameras: Callable[[], list] = listar_cameras,
                 criar_monitoramento: Callable | None = None):
        self.pasta = Path(pasta)
        self._listar = listar_cameras
        self._criar = criar_monitoramento or run_monitor.Monitoramento
        self._trava = threading.RLock()
        self.fase = "inicio"
        self.etapa: str | None = None
        self.erro: dict | None = None
        self.aviso: str | None = None
        self.opcoes = app_teste.OpcoesTeste()
        self.malha = MALHA_PADRAO
        self.som = True
        self.cameras: list[dict] = []
        self.procurando = False
        self._thread_cameras: threading.Thread | None = None
        self._thread: threading.Thread | None = None
        self._executando = False  # a thread do monitor desliga ao terminar de fechar tudo
        self._parar_pedido = False
        self.monitoramento = None
        self.resumo: resumo_mod.ResumoSessao | None = None
        self.resumo_final: dict | None = None
        self.salvo: dict | None = None
        self.ultima_camera: CameraDaTela | None = None
        self.camera_nome: str | None = None
        self.video_gravado = False
        self._ultimo = None
        self._serie = deque()
        self._trava_serie = threading.Lock()
        self.renderizador = Renderizador(lambda: self.malha)
        # Spec 026: conexão com a empresa (envio em segundo plano) e trechos de vídeo da sessão conectada.
        self.sessao_uid: str | None = None
        self.sessao_iniciada_em: str | None = None
        self.gravador: GravadorTrechos | None = None
        self._cabeceios = 0
        self.central = CentralDoTeste(self.pasta, status=self._status_central)
        # Ganchos da janela (tela_teste/janela.py): diálogo de arquivo, tela cheia e fechar.
        self.escolher_arquivo: Callable[[], str | None] | None = None
        self.alternar_tela_cheia: Callable[[], None] | None = None
        self.ao_sair: Callable[[], None] | None = None
        self.procurar_cameras()

    # ------------------------------------------------------------------ estado
    @property
    def rodando(self) -> bool:
        return self._executando

    @property
    def transmitindo(self) -> bool:
        return self.fase in FASES_ATIVAS

    def estado(self) -> dict:
        with self._trava:
            fase = self.fase
            dados = {
                "fase": fase,
                "etapa": self.etapa,
                "erro": self.erro,
                "aviso": self.aviso,
                "cameras": {"procurando": self.procurando, "lista": list(self.cameras)},
                "opcoes": asdict(self.opcoes),
                "malha": self.malha,
                "modos_malha": list(MESH_MODES),
                "modos_malha_rotulos": [{"id": modo, "rotulo": MESH_LABELS[modo]} for modo in MESH_MODES],
                "som": self.som,
                "pasta": str(self.pasta),
                "versao": __version__,
                "espelhar": not self.video_gravado,
                "salvo": self.salvo,
                "central": self.central.estado(),
                "enviando_sessao": self.sessao_uid is not None,
                "gravando_trecho": bool(self.gravador is not None and self.gravador.gravando),
            }
            resumo = self.resumo
            ultimo = self._ultimo
            monitoramento = self.monitoramento
        if resumo is not None:
            dados["sessao"] = {"inicio": resumo.inicio_em.isoformat(timespec="seconds") if resumo.inicio_em else None,
                               "duracao_s": round(resumo.duracao_s, 1), "camera": self.camera_nome,
                               "quadros": resumo.quadros}
            dados["eventos"] = list(reversed(list(resumo.eventos)[-80:]))
        if fase == "resumo":
            dados["resumo"] = self.resumo_final
        if fase in ("calibrando", "rodando") and ultimo is not None:
            monitor = getattr(monitoramento, "monitor", None)
            latencia = monitor.latency.summary() if monitor is not None else None
            motor = getattr(monitoramento, "engine", None)
            drowsiness = getattr(monitoramento, "drowsiness", None)
            dados.update(medidas(ultimo, latencia, self.renderizador.malha_ms,
                                 calibrador=getattr(drowsiness, "calibrator", None),
                                 baixa_em_s=segundos_para_baixar(getattr(motor, "fusion", None),
                                                                 ultimo.metrics.timestamp),
                                 pontos_rosto=getattr(getattr(monitoramento, "analyzer", None), "name", "") != "YuNet"))
            dados["series"] = self._serie_abertura()
        return dados

    def _serie_abertura(self) -> dict:
        """Abertura do olho nos últimos 60 s em passos de 0,1 s; o menor valor de cada passo, para a piscada aparecer."""
        with self._trava_serie:
            pontos = list(self._serie)
        total = int(SERIE_S / SERIE_PASSO_S)
        valores: list[float | None] = [None] * total
        if pontos:
            fim = pontos[-1][0]
            for t, abertura in pontos:
                indice = total - 1 - int((fim - t) / SERIE_PASSO_S)
                if 0 <= indice < total and abertura is not None:
                    atual = valores[indice]
                    valores[indice] = round(abertura, 3) if atual is None else min(atual, round(abertura, 3))
        return {"janela_s": SERIE_S, "passo_s": SERIE_PASSO_S, "abertura": valores}

    # ------------------------------------------------------------------ ações
    def acao(self, nome: str, dados: dict) -> dict:
        acoes = {
            "iniciar": lambda: self.iniciar(dados.get("opcoes") or {}),
            "parar": self.parar,
            "recalibrar": self.recalibrar,
            "malha": lambda: self.definir_malha(dados.get("modo")),
            "som": lambda: self.definir_som(dados.get("ligado")),
            "opcoes": lambda: self.definir_opcoes(dados.get("opcoes") or {}),
            "procurar_cameras": self.procurar_cameras,
            "salvar_resumo": self.salvar_resumo,
            "novo_teste": self.novo_teste,
            "apagar_dados": self.apagar_dados,
            "abrir_pasta": self.abrir_pasta,
            "escolher_video": self.escolher_video,
            "tela_cheia": self.tela_cheia,
            "sair": self.sair,
            "conectar": lambda: self._conectar(dados.get("endereco"), dados.get("codigo")),
            "desconectar": self._desconectar,
            "enviar": lambda: self._definir_envio(dados.get("ligado")),
        }
        if nome not in acoes:
            raise ValueError(f"ação desconhecida: {nome!r}")
        return acoes[nome]() or {}

    def _opcoes_de(self, dados: dict) -> app_teste.OpcoesTeste:
        if not isinstance(dados, dict):
            raise ValueError("opções inválidas")
        atual = self.opcoes
        camera = str(dados.get("camera", atual.camera) or "auto").strip()[:1024] or "auto"
        camera_ir = str(dados.get("camera_ir", atual.camera_ir) or "auto")
        if camera_ir not in CAMERA_IR:
            raise ValueError(f"câmera infravermelha inválida: {camera_ir!r}")
        booleanos = {}
        for chave in ("celular", "som", "calibracao_rapida", "cardio"):
            valor = dados.get(chave, getattr(atual, chave))
            if not isinstance(valor, bool):
                raise ValueError(f"{chave} precisa ser verdadeiro ou falso")
            booleanos[chave] = valor
        return replace(atual, camera=camera, camera_ir=camera_ir, **booleanos)

    def definir_opcoes(self, dados: dict) -> dict:
        with self._trava:
            self.opcoes = self._opcoes_de(dados)
            self.som = self.opcoes.som
        return {"opcoes": asdict(self.opcoes)}

    def iniciar(self, dados: dict) -> dict:
        with self._trava:
            if self.rodando or self.fase in FASES_ATIVAS:
                raise ValueError("O teste já está rodando.")
            opcoes = self._opcoes_de(dados)
            self.opcoes = opcoes
            self.som = opcoes.som
            self.fase, self.etapa = "abrindo", "Preparando o teste"
            self.erro = self.aviso = self.resumo_final = self.salvo = None
            self._parar_pedido = False
            self._ultimo = None
            with self._trava_serie:
                self._serie.clear()
            self.camera_nome = None
            self.video_gravado = eh_arquivo(opcoes.camera)
            self.resumo = resumo_mod.ResumoSessao(versao=__version__)
            self.renderizador.limpar()
            self._comecar_envio_da_sessao()
            self._executando = True
            self._thread = threading.Thread(target=self._executar, args=(opcoes,), name="rotaguard-tela-monitor",
                                            daemon=True)
            self._thread.start()
        logger.info("Teste iniciado pela tela (câmera %s).", "vídeo gravado" if self.video_gravado else opcoes.camera)
        return {"fase": "abrindo"}

    def parar(self, esperar: float = 0.0) -> dict:
        with self._trava:
            self._parar_pedido = True
            monitor = getattr(self.monitoramento, "monitor", None)
        if monitor is not None:
            monitor.stop()
        if esperar and self._thread is not None:
            self._thread.join(timeout=esperar)
        return {"fase": self.fase}

    def recalibrar(self) -> dict:
        monitor = getattr(self.monitoramento, "monitor", None)
        if monitor is None or self.fase not in ("calibrando", "rodando"):
            raise ValueError("Só dá para recalibrar com o teste rodando.")
        monitor.request(monitor.recalibrate)
        return {"recalibrando": True}

    def definir_malha(self, modo) -> dict:
        if modo not in MESH_MODES:
            raise ValueError(f"modo de malha desconhecido: {modo!r}")
        self.malha = modo
        return {"malha": modo}

    def definir_som(self, ligado) -> dict:
        self.som = (not self.som) if ligado is None else bool(ligado)
        alarme = getattr(self.monitoramento, "alarm", None)
        if alarme is not None:
            alarme.muted = not self.som
        return {"som": self.som}

    def procurar_cameras(self) -> dict:
        with self._trava:
            if self.procurando or self.rodando:
                return {"procurando": self.procurando}
            self.procurando = True
            self._thread_cameras = threading.Thread(target=self._procurar, name="rotaguard-tela-cameras", daemon=True)
            self._thread_cameras.start()
        return {"procurando": True}

    def _procurar(self) -> None:
        try:
            cameras = self._listar()
        except Exception:  # noqa: BLE001
            logger.exception("Falha ao procurar câmeras.")
            cameras = []
        with self._trava:
            self.cameras = cameras
            self.procurando = False
        logger.info("Câmeras encontradas: %s.", ", ".join(f"{c['nome']} ({c['situacao']})" for c in cameras) or "nenhuma")

    def salvar_resumo(self) -> dict:
        if self.resumo_final is None:
            raise ValueError("Ainda não há resumo para salvar.")
        caminho_json, caminho_csv = resumo_mod.salvar(self.resumo_final, self.pasta)
        self.salvo = {"json": str(caminho_json), "csv": str(caminho_csv), "pasta": str(caminho_json.parent)}
        logger.info("Resumo do teste salvo em %s.", caminho_json.parent)
        return dict(self.salvo)

    def novo_teste(self) -> dict:
        with self._trava:
            if self.rodando or self.fase in FASES_ATIVAS:
                raise ValueError("Encerre o teste antes de começar outro.")
            self.fase, self.etapa, self.erro, self.aviso = "inicio", None, None, None
            self.resumo = self.resumo_final = self.salvo = None
            self._ultimo = None
        if not self.cameras:
            self.procurar_cameras()
        return {"fase": "inicio"}

    def apagar_dados(self) -> dict:
        if self.rodando or self.fase in FASES_ATIVAS:
            raise ValueError("Encerre o teste antes de apagar os dados.")
        # Tudo roda neste processo: a fila da central e o registro ficam abertos. Fecha, apaga e reabre. Apagar também
        # desconecta da empresa (o token fica em central.json, dentro da pasta).
        self.central.encerrar()
        reabrir = soltar_arquivos(self.pasta)
        try:
            removidos = app_teste.apagar_dados(self.pasta)
        finally:
            reabrir()
            self.central = CentralDoTeste(self.pasta, status=self._status_central)
        self.salvo = None
        logger.info("Dados do teste apagados pela tela (%d arquivos).", removidos)
        return {"removidos": removidos}

    def abrir_pasta(self) -> dict:
        app_teste.abrir_pasta(self.pasta)
        return {}

    def escolher_video(self) -> dict:
        if self.escolher_arquivo is None:
            return {"caminho": None, "manual": True}
        caminho = self.escolher_arquivo()
        return {"caminho": caminho, "manual": False}

    def tela_cheia(self) -> dict:
        if self.alternar_tela_cheia is None:
            return {"feito": False}
        self.alternar_tela_cheia()
        return {"feito": True}

    def sair(self) -> dict:
        self.parar()
        if self.ao_sair is not None:
            threading.Timer(0.2, self.ao_sair).start()
        return {}

    def encerrar(self) -> None:
        """Janela fechada: para o teste, espera a thread e solta câmera, anúncio e modelos."""
        self.parar()
        if self._thread is not None:
            self._thread.join(timeout=20)
        if self._thread_cameras is not None:
            self._thread_cameras.join(timeout=10)
        self.renderizador.parar()
        self.central.encerrar()

    # ------------------------------------------------------------------ thread do monitor
    def _ao_quadro(self, quadro, estado) -> None:
        resumo = self.resumo
        if resumo is not None:
            resumo.quadro(estado)
        t = estado.metrics.timestamp
        with self._trava_serie:
            self._serie.append((t, estado.drowsiness.openness))
            while self._serie and self._serie[0][0] < t - SERIE_S - 1.0:
                self._serie.popleft()
        self._ultimo = estado
        with self._trava:
            if self.fase in FASES_ATIVAS and not self._parar_pedido:
                self.fase = "calibrando" if estado.drowsiness.calibrating else "rodando"
                self.etapa = None
        motor = getattr(self.monitoramento, "engine", None)
        self.renderizador.entregar(quadro, estado, recent_hands(getattr(motor, "phone", None), t))
        gravador = self.gravador
        if gravador is not None:  # cabeceio não vira evento: o gatilho é o contador de 10 min do motor subir
            cabeceios = int((getattr(estado, "window", None) or {}).get("cabeceios_10min") or 0)
            if cabeceios > self._cabeceios and self.central.enviando:
                gravador.gatilho("cabeceio", t)
            self._cabeceios = cabeceios

    @staticmethod
    def _erro(titulo: str, detalhe: str, dicas: list | None = None) -> dict:
        return {"titulo": titulo, "detalhe": detalhe, "dicas": list(dicas or [])}

    def _executar(self, opcoes: app_teste.OpcoesTeste) -> None:
        resumo = self.resumo
        monitoramento = None
        codigo = erro = None
        try:
            if self._thread_cameras is not None:
                self._thread_cameras.join(timeout=15)  # a busca da lista pode estar segurando uma câmera
            # Som: o alarme deixa os sons preparados mesmo mudo, e a tela liga ou desliga na hora (tecla S). Com o som
            # desligado nas opções, o autoteste do alarme (spec 027, ALM-05) também fica quieto.
            argumentos = app_teste.argumentos_monitor(replace(opcoes, som=self.som), self.pasta, janela=False)
            args = run_monitor.parse_args(argumentos)
            self.etapa = "Carregando a detecção"
            monitoramento = self._criar(args)
            with self._trava:
                self.monitoramento = monitoramento
            monitoramento.montar()
            monitoramento.alarm.muted = not self.som
            if monitoramento.drowsiness is not None and resumo is not None:
                monitoramento.drowsiness.blink_listeners.append(resumo.piscada)
            monitoramento.monitor.listeners.append(self._ao_quadro)
            if self.gravador is not None:
                monitoramento.monitor.event_hooks.append(self._gancho_evento)
                monitoramento.monitor.events = EventosComEnvio(monitoramento.monitor.events, self)
                self.renderizador.ouvinte = self.gravador.quadro
            if self._parar_pedido:
                return
            self.etapa = "Abrindo a câmera" if not self.video_gravado else "Abrindo o vídeo"
            camera = monitoramento.abrir_camera()
            self.camera_nome = monitoramento.anuncio.dados.get("camera") if monitoramento.anuncio else None
            if resumo is not None:
                resumo.camera = self.camera_nome
            camera = CameraDaTela(camera, fps_do_video(opcoes.camera) if self.video_gravado else None)
            self.ultima_camera = camera
            if self._parar_pedido:
                camera.release()
                return
            self.etapa = "Esperando a primeira imagem"
            codigo = monitoramento.rodar(camera, False)
        except CameraIndisponivel as exc:
            logger.error("%s", exc)
            if self.video_gravado or (opcoes.camera not in ("auto",) and not opcoes.camera.isdigit()):
                erro = self._erro("O vídeo não abriu", "O arquivo escolhido não pôde ser lido. Confira se ele existe e se é "
                           "um vídeo (MP4, AVI, MOV, MKV ou WEBM).", ["Escolha outro vídeo ou volte para a câmera."])
            elif opcoes.camera == "auto":
                erro = self._erro("Nenhuma câmera respondeu", "Nenhuma câmera deste computador abriu e mandou imagem. Ela "
                           "pode estar desconectada ou ocupada por outro programa.", DICAS_CAMERA)
            else:
                erro = self._erro("A câmera escolhida não abriu", f"A Câmera {int(opcoes.camera) + 1} não abriu. Ela pode "
                           "estar desconectada ou ocupada por outro programa.", DICAS_CAMERA)
        except RuntimeError as exc:
            logger.error("%s", exc)
            erro = self._erro("Não foi possível carregar a detecção", str(exc),
                       ["Feche e abra o app de novo.", "Se continuar, envie o registro (pasta de dados) para a equipe."])
        except Exception as exc:  # noqa: BLE001 - qualquer falha vira tela de erro, nunca app fechado
            logger.exception("O teste parou com erro.")
            erro = self._erro("O teste parou com erro", f"{exc.__class__.__name__}: {exc}",
                       ["Tente de novo.", "Se continuar, envie o registro (pasta de dados) para a equipe."])
        finally:
            self.renderizador.ouvinte = None
            if monitoramento is not None:
                monitoramento.fechar()
            self.renderizador.limpar()
            sessao_uid, gravador = self.sessao_uid, self.gravador
            inicio_da_sessao = (self.sessao_iniciada_em, self.camera_nome)
            trechos = self._fechar_gravador()
            self._terminar(resumo, codigo, erro)
            self._fechar_envio_da_sessao(sessao_uid, gravador, trechos, *inicio_da_sessao)

    def _terminar(self, resumo, codigo, erro: dict | None) -> None:
        """Fim da thread, depois de soltar câmera, anúncio e modelos: só agora a fase sai de "abrindo"/"rodando"."""
        with self._trava:  # fase nova e fim da execução juntos: quem lê a fase já pode começar outro teste
            try:
                self._definir_fim(resumo, codigo, erro)
            finally:
                self._executando = False

    def _definir_fim(self, resumo, codigo, erro: dict | None) -> None:
        with self._trava:
            self.monitoramento = None
            self._ultimo = None
            if erro is not None:
                self.fase, self.etapa, self.erro = "erro", None, erro
                return
            quadros = resumo.quadros if resumo is not None else 0
            if codigo == run_monitor.SAIDA_SEM_CAMERA and quadros == 0:
                self.fase, self.etapa = "erro", None
                self.erro = {"titulo": "A câmera não mandou imagem",
                             "detalhe": f"A câmera abriu, mas ficou {app_teste.ESPERA_CAMERA_S} s sem imagem. Ela pode "
                                        "estar ocupada por outro programa.",
                             "dicas": DICAS_CAMERA}
                return
            if quadros == 0:
                self.fase, self.etapa = "inicio", None  # parado antes da primeira imagem
                self.resumo = None
                return
            if codigo == run_monitor.SAIDA_SEM_CAMERA:
                self.aviso = "A câmera parou de mandar imagem e o teste terminou. O resumo vai até esse momento."
            elif self.video_gravado and not self._parar_pedido:
                self.aviso = "O vídeo terminou."
            resumo.finalizar()
            self.resumo_final = resumo.dados()
            self.resumo_final["trechos"] = self._trechos_para_tela()
            self.fase, self.etapa = "resumo", None
        logger.info("Teste encerrado pela tela: %.0f s, %d eventos.", resumo.duracao_s,
                    self.resumo_final["total_eventos"])

    # ------------------------------------------------------------------ central e trechos (spec 026)
    def _conectar(self, endereco, codigo) -> dict:
        if self.rodando or self.fase in FASES_ATIVAS:
            raise ValueError("Encerre o teste antes de conectar.")
        return {"central": self.central.conectar(str(endereco or ""), str(codigo or ""))}

    def _desconectar(self) -> dict:
        if self.rodando or self.fase in FASES_ATIVAS:
            raise ValueError("Encerre o teste antes de desconectar.")
        return {"central": self.central.desconectar()}

    def _definir_envio(self, ligado) -> dict:
        if not isinstance(ligado, bool):
            raise ValueError("ligado precisa ser verdadeiro ou falso")
        return {"central": self.central.definir_envio(ligado)}

    def _status_central(self) -> dict:
        """Sinal de vida para a central: só o estado do teste, nada de imagem nem de cardio."""
        ultimo = self._ultimo
        status = {"sessao_uid": self.sessao_uid if self.rodando else None}
        if ultimo is not None:
            status.update(risk_level=int(ultimo.risk.level), risk_name=str(ultimo.risk.name),
                          face_found=bool(ultimo.metrics.face_found),
                          calibrating=bool(ultimo.drowsiness.calibrating),
                          calibration_progress=round(float(ultimo.drowsiness.calibration_progress or 0.0), 3))
        return status

    def _payload_sessao(self, encerrada_em: str | None = None, resumo: dict | None = None,
                        iniciada_em: str | None = None, camera: str | None = None) -> dict:
        return {"iniciada_em": iniciada_em or self.sessao_iniciada_em, "encerrada_em": encerrada_em,
                "programa": f"RotaGuard Teste {__version__}", "camera": camera or self.camera_nome,
                "resumo": resumo or {}}

    def _comecar_envio_da_sessao(self) -> None:
        """Conectado e com o envio ligado: a sessão ganha uid, vai para a fila e grava trechos dos alertas."""
        self._cabeceios = 0
        if not self.central.enviando:
            self.sessao_uid = self.gravador = None
            return
        self.sessao_uid = uuid.uuid4().hex
        self.sessao_iniciada_em = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        self.gravador = GravadorTrechos(self.pasta, self.sessao_uid, ao_gravar=self._trecho_gravado)
        self.central.abrir_fila().salvar_sessao(self.sessao_uid, self._payload_sessao())
        self.central.avisar()

    def _gancho_evento(self, evento, t: float) -> dict:
        extra = {"sessao_uid": self.sessao_uid}
        gravador = self.gravador
        if gravador is not None and self.central.enviando:
            trecho = gravador.gatilho(evento.alert_type, t)
            if trecho:
                extra["trecho_uid"] = trecho
        return extra

    def _trecho_gravado(self, meta: dict) -> None:
        if self.central.enviando:
            self.central.abrir_fila().adicionar_trecho(meta, self.pasta / "trechos")
            self.central.avisar()

    def _fechar_gravador(self) -> list:
        gravador = self.gravador
        if gravador is None:
            return []
        if self.fase in FASES_ATIVAS:
            self.etapa = "Gravando o último trecho"
        return gravador.finalizar()

    def _fechar_envio_da_sessao(self, uid: str | None, gravador, trechos: list, iniciada_em: str | None = None,
                                camera: str | None = None) -> None:
        """Sessão encerrada: o resumo (sem cardio) vai para a fila. Só limpa o que é desta sessão (outra já pode ter
        começado depois que a fase virou "resumo")."""
        if uid is None:
            return
        dados = self.resumo_final or {}
        resumo_central = {
            "duracao_s": dados.get("duracao_s"),
            "eventos_por_tipo": dados.get("eventos_por_tipo") or {},
            "perclos_medio": dados.get("perclos_medio"),
            "piscadas_por_minuto": dados.get("piscadas_por_min"),
            "trechos": len(trechos),
            "fps_medio": dados.get("fps_medio"),
            "tempo_por_nivel_s": dados.get("tempo_por_nivel_s") or {},
        }
        encerrada = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        self.central.abrir_fila().salvar_sessao(uid, self._payload_sessao(encerrada, resumo_central, iniciada_em, camera))
        self.central.avisar()
        with self._trava:
            if self.sessao_uid == uid:
                self.sessao_uid = None
            if self.gravador is gravador:
                self.gravador = None

    def _trechos_para_tela(self) -> list:
        gravador = self.gravador
        if gravador is None:
            return []
        return [{"uid": meta["uid"], "tipo": meta["tipo"], "rotulo": rotulo_evento(meta["tipo"]),
                 "inicio": meta["inicio"], "duracao_s": meta["duracao_s"], "formato": meta["formato"]}
                for meta in gravador.trechos]

    def arquivo_trecho(self, uid: str) -> tuple[Path, dict] | None:
        """Arquivo e metadado de um trecho desta pasta de dados, para o player do resumo. Só uid de 32 hexadecimais."""
        if not re.fullmatch(r"[0-9a-f]{32}", uid or ""):
            return None
        raiz = (self.pasta / "trechos").resolve()
        for metadado in raiz.glob(f"*/{uid}.json"):
            try:
                meta = json.loads(metadado.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return None
            arquivo = (metadado.parent / str(meta.get("arquivo") or "")).resolve()
            if arquivo.parent == metadado.parent.resolve() and arquivo.is_file() and raiz in arquivo.parents:
                return arquivo, meta
        return None


class EventosComEnvio:
    """Fila local de eventos do monitor com uma cópia para a central (só da sessão conectada, sem cardio)."""

    def __init__(self, fila_local, sessao: "SessaoTeste"):
        self._fila_local = fila_local
        self._sessao = sessao

    def add(self, alert_type: str, risk_level: int, duration: float, details: dict | None = None) -> str:
        uid = self._fila_local.add(alert_type, risk_level, duration, details=details)
        sessao = self._sessao
        if sessao.sessao_uid is None or not sessao.central.enviando:
            return uid
        fila = sessao.central.abrir_fila()
        fila.adicionar_evento({"event_uid": uid, "alert_type": alert_type, "risk_level": int(risk_level),
                               "duration": float(duration),
                               "occurred_at": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
                               "details": details or {}})
        trecho = (details or {}).get("trecho_uid")
        if trecho:
            if sessao.gravador is not None:
                sessao.gravador.ligar_evento(trecho, uid)
            fila.ligar_evento_ao_trecho(trecho, uid)
        sessao.central.avisar()
        return uid

    def __getattr__(self, nome):
        return getattr(self._fila_local, nome)
