"""Aplica no dispositivo a política mandada pelo servidor: motorista vinculado, consentimento e sinais de ativação.

Com servidor configurado, o registro de consentimentos do app é a fonte da verdade:
- consentimento para guardar perfil ausente ou revogado apaga o perfil e a linha de base guardados deste motorista;
- motorista trocado no servidor dispara nova calibração;
- o modo dos sinais de ativação segue a empresa (e "enviar" só com consentimento do motorista).

A política chega pela thread de sincronização e é aplicada no loop da câmera, entre um quadro e outro.
"""
from __future__ import annotations

import logging
import re
import threading
from pathlib import Path

from vision.baseline import BaselineStore
from vision.engine import ACTIVATION_MODES

logger = logging.getLogger("drivesafe.policy")


def driver_key_for(driver_id: int | None, fallback: str) -> str:
    return f"motorista-{int(driver_id)}" if driver_id else (re.sub(r"[^A-Za-z0-9_-]+", "_", fallback).strip("_") or "padrao")


class RemotePolicy:
    def __init__(self, engine, data_dir: Path, fallback_key: str = "padrao", calibrator_factory=None):
        self.engine = engine
        self.data_dir = Path(data_dir)
        self.fallback_key = fallback_key
        self.calibrator_factory = calibrator_factory
        self.current: dict | None = None
        self.driver_key: str | None = None
        self._pending: dict | None = None
        self._lock = threading.Lock()

    def submit(self, policy: dict) -> None:
        """Chamado pela thread de sincronização."""
        with self._lock:
            self._pending = dict(policy)

    def profile_path(self, key: str) -> Path:
        return self.data_dir / "perfis" / f"{key}.json"

    def baseline_path(self, key: str) -> Path:
        return self.data_dir / "linhas_de_base" / f"{key}.json"

    def apply_pending(self) -> bool:
        """Chamado pelo loop da câmera. Retorna True se algo mudou."""
        with self._lock:
            policy, self._pending = self._pending, None
        if policy is None or policy == self.current:
            return False

        key = driver_key_for(policy.get("driver_id"), self.fallback_key)
        if self.driver_key is not None and key != self.driver_key:
            logger.info("Motorista trocado no servidor (%s -> %s): começando nova calibração.", self.driver_key, key)
            if self.calibrator_factory is not None:
                calibrator = self.calibrator_factory()
                if calibrator is not None:
                    self.engine.drowsiness.recalibrate(calibrator)
        self.driver_key = key

        drowsiness = self.engine.drowsiness
        if policy.get("profile_consent"):
            drowsiness.profile_path = self.profile_path(key)
            self.engine.set_baseline_store(BaselineStore(self.baseline_path(key)))
        else:
            drowsiness.profile_path = None
            self.engine.set_baseline_store(None)
            removed = [path for path in (self.profile_path(key), self.baseline_path(key)) if path.exists()]
            for path in removed:
                path.unlink()
            if removed:
                logger.info("Sem consentimento para guardar perfil de %s: perfil e linha de base apagados.", key)

        mode = policy.get("activation_mode", "local")
        if mode not in ACTIVATION_MODES:
            # Valor estranho vindo da rede não pode parar o monitoramento: fica no modo local.
            logger.warning("Modo dos sinais de ativação desconhecido na política do servidor (%r); usando local.", mode)
            mode = "local"
        self.engine.set_activation_mode(mode)
        logger.info("Política do servidor aplicada: %s, perfil entre viagens %s, sinais de ativação %s.", key,
                    "guardado" if policy.get("profile_consent") else "não guardado", self.engine.activation_mode)
        self.current = policy
        return True
