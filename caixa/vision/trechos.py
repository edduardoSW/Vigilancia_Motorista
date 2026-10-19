"""Trechos de vídeo dos momentos relevantes (spec 026, decisão 5; spec 002 aplicada ao app de teste).

- Buffer circular dos últimos 8 s em memória com os quadros JPEG LIMPOS da câmera (spec 029: sem a malha; para
  investigação, a imagem é a prova), amostrados a ~15 por segundo: nada é decodificado enquanto não há gatilho.
- Gatilhos: olhos fechados por 1 s ou mais (microssono, sono, sem resposta), celular (na mão, no ouvido, olhando) já
  confirmado pelo motor, olhos esfregados e cabeceio. Grava 8 s antes + 8 s depois (16 s).
- No máximo 20 trechos por sessão e 30 s entre dois gatilhos: o segundo gatilho dentro desse tempo fica no trecho que
  já está sendo gravado (ou é ignorado), nunca vira outro.
- Formato: WebM VP8, que toca no WebView2 do painel e no Chromium. O OpenCV do pacote não grava H.264 (`avc1` pede a
  OpenH264, que não vai junto) e o VP9 levou 75 s para 16 s de vídeo, contra 6 s do VP8 (medido em 19/10/2026). Se nem
  o VP8 abrir, `.rgclip`: zip com `indice.json` e os JPEGs, tocado quadro a quadro.
- Faixa fina com "RotaGuard", data, hora e tipo num rodapé ACRESCENTADO embaixo do quadro (spec 029): nenhum pixel
  da imagem, e portanto do rosto, é coberto. A fonte do OpenCV não tem acento: o texto vai sem acento.
- Metadado JSON ao lado do arquivo, com SHA-256. Nenhum dado de cardio entra aqui.
"""
from __future__ import annotations

import bisect
import hashlib
import json
import logging
import math
import os
import tempfile
import threading
import time
import unicodedata
import uuid
import zipfile
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

import cv2
import numpy as np

logger = logging.getLogger("drivesafe.trechos")

GATILHOS = frozenset({"microssono", "sono", "nao_responsivo", "celular_na_mao", "celular_no_ouvido",
                      "olhando_celular", "olhos_esfregados", "cabeceio"})
ANTES_S = 8.0
DEPOIS_S = 8.0
MAX_TRECHOS = 20
INTERVALO_S = 30.0
FPS_TRECHO = 15.0
LARGURA_TRECHO = 640
QUALIDADE_JPEG = 80
FORMATO_INDICE = "rotaguard-trecho/1"
FAIXA_PX = 22  # altura do rodapé com hora e tipo (par: o VP8 pede altura par)
COR_FAIXA = (16, 20, 18)
EXTENSOES = {"webm": "webm", "rgclip": "rgclip"}
ROTULOS = {
    "microssono": "Microssono (olhos fechados 1 s)",
    "sono": "Sono (olhos fechados 3 s)",
    "nao_responsivo": "Sem resposta (olhos fechados 6 s)",
    "celular_na_mao": "Celular na mao",
    "celular_no_ouvido": "Celular no ouvido",
    "olhando_celular": "Olhando o celular",
    "olhos_esfregados": "Olhos esfregados",
    "cabeceio": "Cabeceio",
}

_formato: str | None = None
_formato_trava = threading.Lock()


def formato_de_video() -> str:
    """'webm' se o OpenCV desta instalação grava VP8; senão 'rgclip'. Conferido uma vez por processo."""
    global _formato
    with _formato_trava:
        if _formato is None:
            _formato = "rgclip"
            with tempfile.TemporaryDirectory() as tmp:
                caminho = Path(tmp) / "prova.webm"
                try:
                    escritor = cv2.VideoWriter(str(caminho), cv2.CAP_FFMPEG, cv2.VideoWriter_fourcc(*"VP80"),
                                               FPS_TRECHO, (64, 48))
                    if escritor.isOpened():
                        for _ in range(3):
                            escritor.write(np.zeros((48, 64, 3), dtype=np.uint8))
                    escritor.release()
                    if caminho.exists() and caminho.stat().st_size > 0:
                        _formato = "webm"
                except cv2.error:
                    pass
            logger.info("Trechos de vídeo em %s.", "WebM VP8" if _formato == "webm" else ".rgclip (quadros JPEG)")
    return _formato


def marca_dagua(tipo: str) -> str:
    """Texto do tipo sem acento (a fonte Hershey do OpenCV não desenha acentos)."""
    texto = ROTULOS.get(tipo) or tipo.replace("_", " ").capitalize()
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")


def iso_utc(momento: datetime) -> str:
    return momento.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


@dataclass
class _Trecho:
    uid: str
    tipo: str
    t_gatilho: float
    inicio: float
    fim: float
    evento_uid: str | None = None
    quadros: list = field(default_factory=list)  # (t, jpeg)


class GravadorTrechos:
    """Um gravador por sessão de teste. quadro() recebe o JPEG da tela; gatilho() decide se começa um trecho."""

    def __init__(self, pasta_dados: Path, sessao_uid: str, formato: str | None = None,
                 ao_gravar: Callable[[dict], None] | None = None, em_thread: bool = True,
                 relogio: Callable[[], float] = time.monotonic,
                 agora_utc: Callable[[], datetime] = lambda: datetime.now(timezone.utc)):
        self.sessao_uid = sessao_uid
        self.pasta = Path(pasta_dados) / "trechos" / sessao_uid
        self.formato = formato or formato_de_video()
        self.ao_gravar = ao_gravar
        self.em_thread = em_thread
        self.trechos: list[dict] = []
        self._trava = threading.RLock()
        self._buffer: deque = deque()
        self._ultimo_t = -math.inf
        self._ativo: _Trecho | None = None
        self._ultimo_gatilho = -math.inf
        self._iniciados = 0
        self._threads: list[threading.Thread] = []
        # O relógio dos quadros é o monotônico (o mesmo dos eventos); a hora de parede sai desta referência.
        self._t_ref = relogio()
        self._utc_ref = agora_utc()

    @property
    def gravando(self) -> bool:
        return self._ativo is not None

    def _utc(self, t: float) -> datetime:
        return self._utc_ref + timedelta(seconds=t - self._t_ref)

    def quadro(self, t: float, jpeg: bytes) -> None:
        concluido = None
        with self._trava:
            if t - self._ultimo_t < 0.9 / FPS_TRECHO:
                return
            self._ultimo_t = t
            self._buffer.append((t, jpeg))
            while self._buffer and self._buffer[0][0] < t - ANTES_S - 0.5:
                self._buffer.popleft()
            ativo = self._ativo
            if ativo is not None:
                ativo.quadros.append((t, jpeg))
                if t >= ativo.fim:
                    self._ativo, concluido = None, ativo
        if concluido is not None:
            self._gravar_depois(concluido)

    def gatilho(self, tipo: str, t: float, evento_uid: str | None = None) -> str | None:
        """uid do trecho que cobre este momento (novo ou o que já está gravando), ou None se não vai haver trecho."""
        with self._trava:
            if tipo not in GATILHOS:
                return None
            ativo = self._ativo
            if ativo is not None:
                return ativo.uid if t <= ativo.fim else None
            if self._iniciados >= MAX_TRECHOS or t - self._ultimo_gatilho < INTERVALO_S:
                return None
            self._ultimo_gatilho = t
            self._iniciados += 1
            inicio = max(t - ANTES_S, self._buffer[0][0]) if self._buffer else t
            self._ativo = _Trecho(uuid.uuid4().hex, tipo, t, inicio, t + DEPOIS_S, evento_uid,
                                  [quadro for quadro in self._buffer if quadro[0] >= inicio])
            logger.info("Gravando trecho de %s (8 s antes e 8 s depois).", tipo)
            return self._ativo.uid

    def ligar_evento(self, trecho_uid: str, evento_uid: str) -> None:
        """Liga o trecho ao evento que o disparou (o uid do evento só existe depois de ele entrar na fila local)."""
        with self._trava:
            if self._ativo is not None and self._ativo.uid == trecho_uid:
                self._ativo.evento_uid = self._ativo.evento_uid or evento_uid
                return
            for meta in self.trechos:
                if meta["uid"] == trecho_uid and not meta.get("evento_uid"):
                    meta["evento_uid"] = evento_uid
                    _gravar_json(self.pasta / f"{trecho_uid}.json", meta)

    def finalizar(self, esperar: float = 60.0) -> list[dict]:
        """Fim da sessão: o trecho em andamento é gravado com o que já juntou; espera as gravações em segundo plano."""
        with self._trava:
            ativo, self._ativo = self._ativo, None
        if ativo is not None and ativo.quadros:
            ativo.fim = ativo.quadros[-1][0]
            self._gravar(ativo)
        for linha in list(self._threads):
            linha.join(timeout=esperar)
        with self._trava:
            return list(self.trechos)

    def _gravar_depois(self, trecho: _Trecho) -> None:
        if not self.em_thread:
            self._gravar(trecho)
            return
        linha = threading.Thread(target=self._gravar, args=(trecho,), name="rotaguard-trecho", daemon=True)
        self._threads.append(linha)
        linha.start()

    def _gravar(self, trecho: _Trecho) -> None:
        try:
            meta = self._escrever(trecho)
        except Exception:  # noqa: BLE001 - falha num trecho não para o teste
            logger.exception("Falha ao gravar o trecho %s.", trecho.uid)
            return
        with self._trava:
            self.trechos.append(meta)
        logger.info("Trecho gravado: %s, %.1f s, %s.", trecho.tipo, meta["duracao_s"], meta["formato"])
        if self.ao_gravar is not None:
            try:
                self.ao_gravar(meta)
            except Exception:  # noqa: BLE001
                logger.exception("Falha ao avisar o trecho gravado.")

    # ------------------------------------------------------------------ arquivo
    def _quadros_no_tempo(self, trecho: _Trecho) -> list[tuple[float, int]]:
        """Linha do tempo a 15 por segundo do início ao fim, com o quadro mais recente de cada instante (o vídeo
        dura o tempo real mesmo quando a câmera mandou menos quadros)."""
        tempos = [t for t, _ in trecho.quadros]
        total = max(1, round((trecho.fim - trecho.inicio) * FPS_TRECHO))
        saida = []
        for k in range(total):
            instante = trecho.inicio + k / FPS_TRECHO
            indice = max(0, bisect.bisect_right(tempos, instante) - 1)
            saida.append((instante, indice))
        return saida

    def _imagem(self, jpeg: bytes) -> np.ndarray:
        imagem = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
        altura, largura = imagem.shape[:2]
        if largura > LARGURA_TRECHO:
            nova_altura = int(round(altura * LARGURA_TRECHO / largura / 2)) * 2
            imagem = cv2.resize(imagem, (LARGURA_TRECHO, nova_altura), interpolation=cv2.INTER_AREA)
        return imagem

    def _marcar(self, imagem: np.ndarray, instante: float, tipo: str) -> np.ndarray:
        """Quadro intacto e, embaixo dele, a faixa com "RotaGuard", data, hora e tipo (MAL-05)."""
        altura, largura = imagem.shape[:2]
        faixa = FAIXA_PX + altura % 2  # altura total par
        saida = np.empty((altura + faixa, largura, 3), dtype=np.uint8)
        saida[:altura] = imagem
        saida[altura:] = COR_FAIXA
        hora = self._utc(instante).astimezone().strftime("%d/%m/%Y %H:%M:%S")
        texto = f"RotaGuard  {hora}  {marca_dagua(tipo)}"
        escala = 0.42 if largura >= 560 else 0.34
        cv2.putText(saida, texto, (8, altura + faixa - 7), cv2.FONT_HERSHEY_SIMPLEX, escala, (233, 240, 236), 1,
                    cv2.LINE_AA)
        return saida

    def _escrever(self, trecho: _Trecho) -> dict:
        self.pasta.mkdir(parents=True, exist_ok=True)
        linha = self._quadros_no_tempo(trecho)
        imagens: dict[int, np.ndarray] = {}

        def quadro_marcado(instante: float, indice: int) -> np.ndarray:
            if indice not in imagens:
                imagens[indice] = self._imagem(trecho.quadros[indice][1])
            return self._marcar(imagens[indice], instante, trecho.tipo)

        formato = self.formato
        arquivo = self.pasta / f"{trecho.uid}.{EXTENSOES[formato]}"
        if formato == "webm" and not self._escrever_webm(arquivo, linha, quadro_marcado):
            formato = "rgclip"
            arquivo = self.pasta / f"{trecho.uid}.rgclip"
        if formato == "rgclip":
            self._escrever_rgclip(arquivo, linha, quadro_marcado, trecho)
        dados = arquivo.read_bytes()
        primeiro = quadro_marcado(*linha[0])
        meta = {
            "uid": trecho.uid,
            "sessao_uid": self.sessao_uid,
            "tipo": trecho.tipo,
            "evento_uid": trecho.evento_uid,
            "inicio": iso_utc(self._utc(trecho.inicio)),
            "fim": iso_utc(self._utc(trecho.fim)),
            "duracao_s": round(trecho.fim - trecho.inicio, 2),
            "antes_s": round(trecho.t_gatilho - trecho.inicio, 2),
            "formato": formato,
            "arquivo": arquivo.name,
            "tamanho": len(dados),
            "sha256": hashlib.sha256(dados).hexdigest(),
            "quadros": len(linha),
            "fps": FPS_TRECHO,
            "largura": int(primeiro.shape[1]),
            "altura": int(primeiro.shape[0]),
            "criado_em": iso_utc(datetime.now(timezone.utc)),
            "enviado": False,
        }
        _gravar_json(arquivo.with_suffix(".json"), meta)
        return meta

    @staticmethod
    def _escrever_webm(arquivo: Path, linha, quadro_marcado) -> bool:
        primeiro = quadro_marcado(*linha[0])
        altura, largura = primeiro.shape[:2]
        escritor = cv2.VideoWriter(str(arquivo), cv2.CAP_FFMPEG, cv2.VideoWriter_fourcc(*"VP80"), FPS_TRECHO,
                                   (largura, altura))
        if not escritor.isOpened():
            escritor.release()
            arquivo.unlink(missing_ok=True)
            return False
        try:
            for instante, indice in linha:
                escritor.write(quadro_marcado(instante, indice))
        finally:
            escritor.release()
        if not arquivo.exists() or arquivo.stat().st_size == 0:
            arquivo.unlink(missing_ok=True)
            return False
        return True

    @staticmethod
    def _escrever_rgclip(arquivo: Path, linha, quadro_marcado, trecho: _Trecho) -> None:
        indice = {"formato": FORMATO_INDICE, "fps": FPS_TRECHO, "tipo": trecho.tipo, "quadros": []}
        temporario = arquivo.with_suffix(".tmp")
        with zipfile.ZipFile(temporario, "w", zipfile.ZIP_STORED) as pacote:
            for numero, (instante, posicao) in enumerate(linha, start=1):
                nome = f"{numero:06d}.jpg"
                ok, jpeg = cv2.imencode(".jpg", quadro_marcado(instante, posicao),
                                        [int(cv2.IMWRITE_JPEG_QUALITY), QUALIDADE_JPEG])
                pacote.writestr(nome, jpeg.tobytes())
                indice["quadros"].append({"arquivo": nome, "t": round(instante - linha[0][0], 3)})
            primeiro = cv2.imdecode(np.frombuffer(pacote.read(indice["quadros"][0]["arquivo"]), np.uint8), 1)
            indice["largura"], indice["altura"] = int(primeiro.shape[1]), int(primeiro.shape[0])
            pacote.writestr("indice.json", json.dumps(indice, ensure_ascii=False))
        os.replace(temporario, arquivo)


def _gravar_json(caminho: Path, dados: dict) -> None:
    temporario = caminho.with_suffix(".json.tmp")
    temporario.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporario, caminho)


def ler_rgclip(caminho: Path) -> tuple[dict, list[bytes]]:
    """Índice e JPEGs de um .rgclip (para tocar ou conferir)."""
    with zipfile.ZipFile(caminho) as pacote:
        indice = json.loads(pacote.read("indice.json"))
        return indice, [pacote.read(quadro["arquivo"]) for quadro in indice["quadros"]]


__all__ = ["FAIXA_PX", "GATILHOS", "GravadorTrechos", "formato_de_video", "marca_dagua", "ler_rgclip"]
