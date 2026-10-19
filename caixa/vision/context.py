"""Contexto da viagem: hora do dia, tempo ao volante e telemetria opcional do veículo (spec 027, CTX-02 a CTX-04).

- CTB art. 67-C (incluído pela Lei 13.103/2015): ninguém dirige mais de 5 h 30 min seguidas (caput). Descanso de
  30 min a cada 6 h na carga (§1º) e a cada 4 h no transporte de passageiros (§1º-A), com fracionamento. "Tempo de
  direção" é só o período efetivamente ao volante (§4º).
- Sem telemetria (velocidade, ignição ou IMU) o script não sabe se o veículo anda: motorista de caminhão descansa e
  come dentro da cabine, com o rosto na câmera. Então o limite legal não é afirmado (`limite_direcao_excedido` = None)
  e o que se publica é `tempo_com_rosto_h`, uma estimativa.
- Hora do dia: acidentes ligados ao sono têm picos de 02h a 06h e de 14h a 16h (Horne & Reyner, 1995; SWOV); dirigir
  entre 2h e 5h teve OR 5,6 (Connor et al., 2002). A janela "forte" antecipa a escalada de sinais leves em
  vision/risk.py (como a madrugada fazia); a "moderada" só vai para o registro.

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
# Sem somar pausas fracionadas: só uma pausa inteira de 30 min zera a contagem (conservador).
REST_RESET_S = 30 * 60
# Descanso previsto (CTB art. 67-C, §1º-A): passageiros a cada 4 h. Na carga, o limite de 5 h 30 contínuas chega antes
# do descanso de 6 h e já vira `limite_direcao_excedido`.
REST_DUE_S = {"carga": None, "passageiros": 4 * 3600}
VEHICLE_TYPES = tuple(REST_DUE_S)
# Janelas circadianas (hora local): forte 02:00 a 05:59, moderada 14:00 a 15:59.
CIRCADIAN_STRONG = range(2, 6)
CIRCADIAN_MODERATE = range(14, 16)
STOPPED_KMH = 5.0
TELEMETRY_MAX_AGE_S = 10.0
TELEMETRY_READ_EVERY_S = 1.0
MAX_STEP_S = 5.0
# Raspberry Pi sem relógio de bateria e sem internet liga com data antiga: nesse caso o horário é ignorado.
MIN_VALID_YEAR = 2024


def janela_circadiana(hora: int) -> str | None:
    """'forte' de 02h a 06h, 'moderado' de 14h a 16h, None no resto do dia."""
    if hora in CIRCADIAN_STRONG:
        return "forte"
    if hora in CIRCADIAN_MODERATE:
        return "moderado"
    return None


class DrivingContext:
    """telemetry_path: arquivo JSON escrito por outro processo (OBD-II, CAN, ignição ou IMU no Pi), por exemplo
    {"velocidade_kmh": 72.5, "atualizado_em": 1757520000.0}. Sem ele, só o tempo com o rosto na câmera é medido.
    tipo_veiculo: "carga" (padrão) ou "passageiros" (descanso previsto a cada 4 h)."""

    def __init__(self, telemetry_path: Path | None = None, now=None, wall_time=time.time, tipo_veiculo: str = "carga"):
        if tipo_veiculo not in VEHICLE_TYPES:
            raise ValueError(f"tipo de veículo inválido: {tipo_veiculo!r} (use {', '.join(VEHICLE_TYPES)})")
        self.telemetry_path = Path(telemetry_path) if telemetry_path else None
        self.tipo_veiculo = tipo_veiculo
        self._now = now or (lambda: datetime.now().astimezone())
        self._wall_time = wall_time
        self._last_t = None
        self._driving_s = 0.0  # só com telemetria: veículo andando
        self._rest_s = 0.0
        self._face_s = 0.0  # rosto na câmera, sem pausa de 30 min (estimativa, não é tempo de direção)
        self._face_absent_s = 0.0
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

        if face_found:
            self._face_absent_s = 0.0
            self._face_s += dt
        else:
            self._face_absent_s += dt
            if self._face_absent_s >= REST_RESET_S:
                self._face_s = 0.0

        if self._speed is None:
            return  # telemetria ausente ou velha: o tempo de direção fica parado, sem chutar
        if self._speed >= STOPPED_KMH:
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
        circadian = None if now.year < MIN_VALID_YEAR else janela_circadiana(now.hour)
        telemetry = self._speed is not None
        rest_due = REST_DUE_S[self.tipo_veiculo]
        return {
            "direcao_continua_h": round(self._driving_s / 3600, 2) if telemetry else None,
            "limite_direcao_excedido": self._driving_s >= MAX_CONTINUOUS_DRIVING_S if telemetry else None,
            "tempo_com_rosto_h": round(self._face_s / 3600, 2),
            "madrugada": None if now.year < MIN_VALID_YEAR else circadian == "forte",
            "circadiano": circadian,
            "velocidade_kmh": None if self._speed is None else round(self._speed, 1),
            "parado": self.stopped,
            "fonte_tempo_direcao": "telemetria" if telemetry else "camera",
            "tipo_veiculo": self.tipo_veiculo,
            "descanso_previsto_h": None if rest_due is None else rest_due / 3600,
            "descanso_previsto_excedido": (self._driving_s >= rest_due) if telemetry and rest_due is not None else None,
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
                logger.warning("Telemetria em %s ilegível (%s); sem ela o limite legal de direção não é calculado.",
                               self.telemetry_path, exc)
                self._warned = True
            return None
