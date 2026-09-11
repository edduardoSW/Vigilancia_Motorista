"""Fusão e alertas (módulo 4): nível de risco de 0 a 3 com histerese, regra de rebote e contexto da viagem.

0 normal, 1 atenção, 2 alto, 3 crítico. A linguagem é sempre "nível de risco" e "sinais compatíveis com":
o sistema não faz diagnóstico.

- Sonolência (módulo 1) define a base: perigo → crítico, sonolência → alto, atenção → atenção.
- Contexto (madrugada ou mais de 5 h 30 min ao volante, vision/context.py): sinais leves de sonolência que duram
  5 min viram risco alto, em vez de esperar os 10 min normais.
- Olhos esfregados (vision/face_touch.py): 3 ou mais em 10 min fazem o mesmo que o contexto. Sozinhos não mudam o
  risco (sinal leve, limiar a validar). Mão parada no rosto não pesa: é comum acordado (Ralph et al., 2022).
- Rebote: quando o efeito do estimulante passa, vêm depressão, fadiga e sono (Takitane et al., 2013, Ciência &
  Saúde Coletiva). Depois de ativação atípica sustentada por 10 min, qualquer sinal de sonolência na hora seguinte
  eleva o risco para alto na mesma hora, com alarme. Tempos e limiares são hipóteses a validar.
- Histerese: o risco sobe na hora e desce um nível por vez, só depois de o motivo sumir por 10 s (crítico) ou 60 s.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from vision.drowsiness import DetectedEvent

LEVEL_NAMES = ("normal", "atencao", "alto", "critico")
HOLD_DOWN_S = {3: 10.0, 2: 60.0, 1: 60.0}
CONTEXT_ESCALATION_S = 300.0
HAND_GESTURES_LIGHT_SIGNAL = 3
REBOUND_MIN_ACTIVATION_S = 600.0
REBOUND_GAP_S = 120.0  # intervalo tolerado sem sinais dentro de um mesmo episódio de ativação
REBOUND_WINDOW_S = 3600.0
REBOUND_HOLD_S = 300.0
REBOUND_DURATION_Z = 1.5  # piscadas mais longas que o normal da pessoa também contam como sinal de sonolência
ALARM_COOLDOWN_S = 60.0
COOLDOWN_S = {"sonolencia_abrupta": 600.0, "ativacao_atipica": 1800.0, "direcao_continua": 1800.0}
REBOUND_WINDOW_KEYS = ("perclos_60s", "perclos_3min", "duracao_mediana_ms", "fechamentos_longos_5min", "piscadas_por_min")


@dataclass
class RiskAssessment:
    level: int = 0
    name: str = "normal"
    reasons: list = field(default_factory=list)
    alarm: bool = False
    events: list = field(default_factory=list)
    activation_sustained: bool = False
    rebound: bool = False


class RiskFusion:
    def __init__(self, share_activation: bool = False):
        # False: a ativação atípica é usada só no próprio dispositivo e não aparece em nenhum evento enviado.
        self.share_activation = share_activation
        self._level = 0
        self._below_since = None
        self._mild_since = None
        self._episode_start = None
        self._episode_last = None
        self._episode_peak = 0.0
        self._sustained_last = None
        self._sustained_minutes = 0.0
        self._rebound_until = -math.inf
        self._last_event_at = {}
        self._last_alarm_at = -math.inf

    @property
    def level(self) -> int:
        return self._level

    def update(self, t: float, drowsiness, activation=None, context: dict | None = None, zscores: dict | None = None,
               window: dict | None = None, phone=None) -> RiskAssessment:
        result = RiskAssessment()
        context, zscores, window = context or {}, zscores or {}, window or {}
        target = drowsiness.level
        reasons = list(drowsiness.reasons) if drowsiness.level else []

        touch = getattr(phone, "face_touch", None)
        hand_gestures = touch is not None and touch.rubs_10min >= HAND_GESTURES_LIGHT_SIGNAL
        if drowsiness.level == 1:
            self._mild_since = t if self._mild_since is None else self._mild_since
            risky_context = context.get("madrugada") or context.get("limite_direcao_excedido")
            if hand_gestures:
                reasons.append("olhos_esfregados_repetidamente")
            if (risky_context or hand_gestures) and t - self._mild_since >= CONTEXT_ESCALATION_S:
                target = max(target, 2)
                reasons.append("sinais_leves_em_contexto_de_risco" if risky_context else "sinais_leves_com_gestos_de_sono")
        else:
            self._mild_since = None

        if context.get("limite_direcao_excedido"):
            target = max(target, 1)
            reasons.append("direcao_continua_acima_de_5h30")
            self._emit(t, result, "direcao_continua", 2, context.get("direcao_continua_h", 0.0) * 3600.0,
                       dict(context), alarm=False)

        result.activation_sustained = self._track_activation(t, activation)
        if result.activation_sustained:
            target = max(target, 1)
            reasons.append("padrao_ocular_atipico_sustentado")
            if self.share_activation:
                details = dict(activation.to_details(), duracao_min=round((t - self._episode_start) / 60.0, 1),
                               indice_max=round(self._episode_peak, 2))
                self._emit(t, result, "ativacao_atipica", 2, t - self._episode_start, details, alarm=False)

        drowsy_signs = (drowsiness.level >= 1 or (zscores.get("duracao_mediana_ms") or 0.0) >= REBOUND_DURATION_Z
                        or (window.get("fechamentos_longos_5min") or 0) >= 1)
        if drowsy_signs and self._in_rebound_window(t):
            if t >= self._rebound_until:
                details = {key: window[key] for key in REBOUND_WINDOW_KEYS if window.get(key) is not None}
                details["motivos_sonolencia"] = list(drowsiness.reasons)
                if self.share_activation:
                    details["ativacao"] = {"duracao_min": round(self._sustained_minutes, 1),
                                           "indice_max": round(self._episode_peak, 2),
                                           "min_desde_o_ultimo_sinal": round((t - self._sustained_last) / 60.0, 1)}
                self._emit(t, result, "sonolencia_abrupta", 4, 0.0, details, alarm=True)
            self._rebound_until = t + REBOUND_HOLD_S
        if t < self._rebound_until:
            target = max(target, 2)
            reasons.append("sonolencia_logo_apos_periodo_de_ativacao")
            result.rebound = True

        if phone is not None:
            if phone.risk_level:
                target = max(target, phone.risk_level)
                reasons.extend(phone.reasons)
            result.alarm = result.alarm or phone.alarm

        previous = self._level
        level = self._hysteresis(t, target)
        if level > target:
            reasons.append("reducao_gradual_do_risco")
        result.level, result.name, result.reasons = level, LEVEL_NAMES[level], reasons
        if drowsiness.alarm or (level >= 2 and previous < 2 and t - self._last_alarm_at >= ALARM_COOLDOWN_S):
            result.alarm = True
        if result.alarm:
            self._last_alarm_at = t
        return result

    def _track_activation(self, t: float, activation) -> bool:
        if activation is not None and activation.compatible:
            if self._episode_start is None or t - self._episode_last > REBOUND_GAP_S:
                self._episode_start, self._episode_peak = t, 0.0
            self._episode_last = t
            self._episode_peak = max(self._episode_peak, activation.index or 0.0)
        active = self._episode_start is not None and t - self._episode_last <= REBOUND_GAP_S
        sustained = active and self._episode_last - self._episode_start >= REBOUND_MIN_ACTIVATION_S
        if sustained:
            self._sustained_last = self._episode_last
            self._sustained_minutes = (self._episode_last - self._episode_start) / 60.0
        return sustained

    def _in_rebound_window(self, t: float) -> bool:
        return self._sustained_last is not None and t - self._sustained_last <= REBOUND_WINDOW_S

    def _hysteresis(self, t: float, target: int) -> int:
        if target >= self._level:
            self._level, self._below_since = target, None
        elif self._below_since is None:
            self._below_since = t
        elif t - self._below_since >= HOLD_DOWN_S[self._level]:
            self._level -= 1
            self._below_since = t if target < self._level else None
        return self._level

    def _emit(self, t, result, alert_type, risk_level, duration, details, alarm) -> None:
        last = self._last_event_at.get(alert_type)
        if last is not None and t - last < COOLDOWN_S.get(alert_type, 0.0):
            return
        self._last_event_at[alert_type] = t
        result.events.append(DetectedEvent(alert_type, risk_level, round(duration, 2), details))
        if alarm:
            result.alarm = True
