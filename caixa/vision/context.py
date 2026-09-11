"""Contexto da viagem: tempo contínuo ao volante, madrugada e telemetria opcional do veículo.

- CTB art. 67-C (incluído pela Lei 13.103/2015): motorista profissional não pode dirigir mais de 5 h 30 min
  seguidas; são 30 min de descanso a cada 6 h (carga) ou a cada 4 h (passageiros), com fracionamento permitido.
- Acidentes atribuídos a sono ao volante têm picos por volta de 02:00, 06:00 e 16:00 (Horne & Reyner, 1995, BMJ).

O contexto nunca dispara alerta de sonolência sozinho: só antecipa a escalada quando já há sinais.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("drivesafe.context")

MAX_CONTINUOUS_DRIVING_S = 5.5 * 3600
# Sem telemetria não dá para somar pausas fracionadas com segurança: só uma pausa inteira de 30 min zera a contagem.
REST_RESET_S = 30 * 60
NIGHT_HOURS = range(0, 7)  # 00:00 a 06:59
STOPPED_KMH = 5.0
TELEMETRY_MAX_AGE_S = 10.0
TELEMETRY_READ_EVERY_S = 1.0
MAX_STEP_S = 5.0
# Raspberry Pi sem relógio de bateria e sem internet liga com data antiga: nesse caso o horário é ignorado.
MIN_VALID_YEAR = 2024


class DrivingContext:
    """telemetry_path: arquivo JSON escrito por outro processo (GPS, OBD-II, CAN), por exemplo
    {"velocidade_kmh": 72.5, "atualizado_em": 1757520000.0}. Sem ele, rosto na câmera conta como tempo ao volante."""

    def __init__(self, telemetry_path: Path | None = None, now=None, wall_time=time.time):
        self.telemetry_path = Path(telemetry_path) if telemetry_path else None
        self._now = now or (lambda: datetime.now().astimezone())
        self._wall_time = wall_time
        self._last_t = None
        self._driving_s = 0.0
        self._rest_s = 0.0
        self._speed = None
        self._next_read = -float("inf")
        self._warned = False

    def update(self, t: float, face_found: bool) -> None:
        dt = 0.0
        if self._last_t is not None and 0 < t - self._last_t <= MAX_STEP_S:
            dt = t - self._last_t
        self._last_t = t
        if t >= self._next_read:
            self._next_read = t + TELEMETRY_READ_EVERY_S
            self._speed = self._read_speed()

        moving = self._speed >= STOPPED_KMH if self._speed is not None else face_found
        if moving:
            self._rest_s = 0.0
            self._driving_s += dt
        else:
            self._rest_s += dt
            if self._rest_s >= REST_RESET_S:
                self._driving_s = 0.0

    @property
    def stopped(self) -> bool:
        return self._speed is not None and self._speed < STOPPED_KMH

    def snapshot(self) -> dict:
        now = self._now()
        night = None if now.year < MIN_VALID_YEAR else now.hour in NIGHT_HOURS
        return {
            "direcao_continua_h": round(self._driving_s / 3600, 2),
            "limite_direcao_excedido": self._driving_s >= MAX_CONTINUOUS_DRIVING_S,
            "madrugada": night,
            "velocidade_kmh": None if self._speed is None else round(self._speed, 1),
            "fonte_tempo_direcao": "telemetria" if self._speed is not None else "camera",
        }

    def _read_speed(self) -> float | None:
        if self.telemetry_path is None:
            return None
        try:
            data = json.loads(self.telemetry_path.read_text(encoding="utf-8"))
            speed = float(data["velocidade_kmh"])
            updated = data.get("atualizado_em")
            if updated is not None and self._wall_time() - float(updated) > TELEMETRY_MAX_AGE_S:
                return None
            return speed if speed >= 0 else None
        except (OSError, ValueError, KeyError, TypeError) as exc:
            if not self._warned:
                logger.warning("Telemetria em %s ilegível (%s); usando o rosto na câmera como tempo ao volante.",
                               self.telemetry_path, exc)
                self._warned = True
            return None
