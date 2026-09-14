"""Anúncio de que o script está aberto neste computador (spec 018).

Ao iniciar, o monitor grava `em_execucao.json` na pasta de dados dele, renova `ultimo_sinal` a cada poucos segundos e
apaga o arquivo ao sair normalmente. O painel da empresa só lê esse arquivo: sinal com menos de 15 s e processo vivo
significa "aberto". Só biblioteca padrão; falha aqui nunca derruba o monitoramento.
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
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

logger = logging.getLogger("drivesafe.em_execucao")

ARQUIVO_ANUNCIO = "em_execucao.json"
FORMATO = "rotaguard-em-execucao/1"
# Renova o sinal a cada 3 s (no máximo 5 s); o painel considera fechado depois de 15 s sem sinal.
INTERVALO_S = 3.0
INTERVALO_MAX_S = 5.0


def agora_iso(relogio: Callable[[], datetime] | None = None) -> str:
    agora = relogio() if relogio is not None else datetime.now(timezone.utc)
    if agora.tzinfo is None:
        agora = agora.replace(tzinfo=timezone.utc)
    return agora.astimezone(timezone.utc).isoformat(timespec="milliseconds")


def nome_do_programa(congelado: bool | None = None, argv0: str | None = None) -> str:
    congelado = bool(getattr(sys, "frozen", False)) if congelado is None else congelado
    argv0 = (sys.argv[0] if sys.argv else "") if argv0 is None else argv0
    if congelado or "app_teste" in Path(argv0).name.lower():
        return "RotaGuard Teste"
    return "RotaGuard (run_monitor.py)"


def descrever_camera(camera=None, fonte: str | None = None) -> str | None:
    """Texto curto da câmera. O OpenCV não informa o nome do aparelho: o índice 0 vira "Câmera 1".
    Vídeo mostra só o nome do arquivo e endereço de rede nunca aparece (pode ter usuário e senha)."""
    texto = camera.describe() if camera is not None and hasattr(camera, "describe") else str(fonte or "")
    indice = re.fullmatch(r"OpenCV (\d+)", texto) or re.fullmatch(r"(\d+)", texto)
    if indice:
        return f"Câmera {int(indice.group(1)) + 1}"
    caminho = re.fullmatch(r"OpenCV '(.*)'", texto)
    valor = caminho.group(1) if caminho else texto
    if "://" in valor:
        return "Câmera de rede"
    if valor.lower().startswith("/dev/video"):
        return f"Câmera {valor}"
    if caminho:
        return f"Vídeo {Path(valor).name}"
    return texto or None


class AnuncioExecucao:
    def __init__(self, pasta: Path, programa: str, intervalo_s: float = INTERVALO_S,
                 relogio: Callable[[], datetime] | None = None, pid: int | None = None):
        self.caminho = Path(pasta) / ARQUIVO_ANUNCIO
        self._relogio = relogio
        self._intervalo = max(0.01, min(float(intervalo_s), INTERVALO_MAX_S))
        self._parar = threading.Event()
        self._trava = threading.Lock()
        self._linha: threading.Thread | None = None
        self.dados = {
            "formato": FORMATO,
            "sessao": uuid.uuid4().hex,
            "pid": int(pid if pid is not None else os.getpid()),
            "programa": programa,
            "iniciado_em": agora_iso(relogio),
            "camera": None,
            "ultimo_sinal": None,
            "pasta": str(Path(pasta)),
        }

    def renovar(self) -> bool:
        """Grava o arquivo inteiro de uma vez (temporário + troca), para o painel nunca ler meio arquivo."""
        with self._trava:
            self.dados["ultimo_sinal"] = agora_iso(self._relogio)
            temporario = self.caminho.with_name(f".{ARQUIVO_ANUNCIO}.{self.dados['pid']}.tmp")
            try:
                self.caminho.parent.mkdir(parents=True, exist_ok=True)
                temporario.write_text(json.dumps(self.dados, ensure_ascii=False, indent=2), encoding="utf-8")
                for _ in range(10):
                    try:
                        os.replace(temporario, self.caminho)
                        return True
                    except PermissionError:  # Windows: o painel pode estar lendo neste instante
                        time.sleep(0.02)
            except OSError as exc:
                logger.debug("Não foi possível renovar %s: %s", self.caminho, exc)
            try:
                temporario.unlink(missing_ok=True)
            except OSError:
                pass
            return False

    def definir_camera(self, texto: str | None) -> None:
        self.dados["camera"] = texto
        self.renovar()

    def iniciar(self) -> None:
        self.renovar()
        self._parar.clear()
        self._linha = threading.Thread(target=self._vigiar, name="rotaguard-em-execucao", daemon=True)
        self._linha.start()

    def _vigiar(self) -> None:
        while not self._parar.wait(self._intervalo):
            self.renovar()

    def parar(self) -> None:
        """Encerramento normal: para de renovar e apaga o anúncio, só se ainda for desta sessão."""
        self._parar.set()
        if self._linha is not None:
            self._linha.join(timeout=2)
        with self._trava:
            try:
                atual = json.loads(self.caminho.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return
            if isinstance(atual, dict) and atual.get("sessao") == self.dados["sessao"]:
                try:
                    self.caminho.unlink()
                except OSError as exc:
                    logger.debug("Não foi possível apagar %s: %s", self.caminho, exc)
