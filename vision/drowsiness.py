"""Níveis de sonolência, eventos e alarme a partir das piscadas, dos fechamentos do olho e da cabeça (módulo 1).

Gatilhos iniciais (a ajustar com vídeos reais da frota):
- Críticos: 1 s de olhos fechados = microssono, 3 s = sono, 6 s = sem resposta (Euro NCAP 2026, Driver Engagement).
- Fechamento longo a partir de 500 ms (Mulhall et al., 2020).
- Duração da piscada em relação à linha de base: +10% no KSS 7, +23% no KSS 8, +32% no KSS 9 (Ingre et al., 2006).
- PERCLOS de 3 min a partir de 12% como sonolento (Owens et al., 2018, AAA Foundation).
- Duração da piscada só é confiável a partir de ~25 fps (Navascues-Cornago et al., 2026).
- AVR (Johns et al., 2003 e 2005) cresce com a sonolência. Aqui entra só como sinal de atenção, a partir de 28 fps.
- Bocejo é sinal complementar, nunca gatilho crítico (FG 2018, Universidade de Cambridge).
- Cabeceio: queda rápida da cabeça seguida de volta. Sistemas publicados usam de 15° a 20° de inclinação;
  os limiares abaixo são iniciais e não foram validados com a câmera do veículo.
"""
from __future__ import annotations

import logging
import math
import statistics
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

from vision.calibration import COMPLETE_BLINK_OPENNESS, MAX_BLINK_S, SHORT_CLOSURE_S, Calibrator
from vision.eyes import MAX_FRAME_GAP_S, MIN_FPS_FOR_VELOCITY, P80_OPENNESS, DriverProfile, EyeStateTracker, OpennessModel

logger = logging.getLogger("drivesafe.drowsiness")

MICROSLEEP_S = 1.0
SLEEP_S = 3.0
UNRESPONSIVE_S = 6.0
LONG_CLOSURE_S = 0.5

ALERT_DURATION_RATIO = 1.25
ALERT_PERCLOS = 0.12
ALERT_LONG_CLOSURES_5MIN = 3
ALERT_NODS_10MIN = 3
ATTENTION_PERSIST_S = 600.0

ATTENTION_DURATION_RATIO = 1.15
ATTENTION_PERCLOS_MIN = 0.08
ATTENTION_PERCLOS_FACTOR = 1.5
ATTENTION_YAWNS_10MIN = 2
ATTENTION_NODS_10MIN = 2
ATTENTION_AVR_RATIO = 1.30

MIN_FPS_FOR_DURATION = 24.0
MIN_BLINKS_FOR_DURATION = 15
PERCLOS_MIN_VALID_FRACTION = 0.5

YAWN_MIN_S = 2.0
YAWN_JAW_MIN = 0.45
YAWN_JAW_ABOVE_BASELINE = 0.30

# Cabeceio: pitch sobe (cabeça baixa) pelo menos 15° em até 1 s, fica baixo de 0,3 a 3 s e volta.
# Olhar para baixo devagar, ou por mais tempo, não conta.
NOD_MIN_DEG = 15.0
NOD_NEAR_REFERENCE_DEG = 5.0
NOD_RECOVERED_DEG = 7.0
NOD_MAX_FALL_S = 1.0
NOD_MIN_DOWN_S = 0.3
NOD_MAX_DOWN_S = 3.0
NOD_REFERENCE_S = 10.0
NOD_REFERENCE_STEP_S = 0.2
NOD_RECENT_S = 1.5

# Euro NCAP: avisar em até 10 s que o sistema não consegue monitorar.
FACE_MISSING_EVENT_S = 10.0
EVALUATE_EVERY_S = 1.0
COOLDOWN_S = {"atencao": 300.0, "sonolencia": 120.0, "rosto_nao_detectado": 600.0}

CRITICAL_STAGES = (
    (MICROSLEEP_S, "microssono", 3),
    (SLEEP_S, "sono", 4),
    (UNRESPONSIVE_S, "nao_responsivo", 5),
)


@dataclass
class DetectedEvent:
    alert_type: str
    risk_level: int
    duration: float
    details: dict


@dataclass
class Assessment:
    level: int = 0  # 0 normal, 1 atenção, 2 sonolência, 3 perigo
    status: str = "ACORDADO"
    calibrating: bool = False
    calibration_progress: float = 1.0
    face_found: bool = False
    openness: float | None = None
    frame_source: str = ""
    closed_for: float = 0.0
    perclos_60s: float | None = None
    blinks_last_minute: int = 0
    fps: float | None = None
    reasons: list = field(default_factory=list)
    alarm: bool = False
    events: list = field(default_factory=list)


class PerclosWindow:
    """Tempo válido e tempo com olho pelo menos 80% fechado, em baldes de 1 s."""

    def __init__(self, keep_seconds: float = 900.0):
        self.keep_seconds = keep_seconds
        self._buckets = deque()  # [segundo, tempo válido, tempo fechado]

    def _bucket(self, t: float) -> list:
        second = math.floor(t)
        if not self._buckets or self._buckets[-1][0] != second:
            self._buckets.append([second, 0.0, 0.0])
            while self._buckets and self._buckets[0][0] < second - self.keep_seconds:
                self._buckets.popleft()
        return self._buckets[-1]

    def add_valid(self, t: float, dt: float) -> None:
        if dt > 0:
            self._bucket(t)[1] += dt

    def add_closed(self, t: float, dt: float) -> None:
        if dt > 0:
            self._bucket(t)[2] += dt

    def valid_seconds(self, now: float, window: float) -> float:
        valid = 0.0
        for second, bucket_valid, _ in reversed(self._buckets):
            if second < now - window:
                break
            valid += bucket_valid
        return valid

    def value(self, now: float, window: float) -> float | None:
        valid = closed = 0.0
        for second, bucket_valid, bucket_closed in reversed(self._buckets):
            if second < now - window:
                break
            valid += bucket_valid
            closed += bucket_closed
        if valid < window * PERCLOS_MIN_VALID_FRACTION:
            return None
        return min(1.0, closed / valid)


def _count_since(times, now: float, window: float) -> int:
    return sum(1 for moment in times if now - moment <= window)


class NodTracker:
    """Detecta cabeceios pelo pitch (positivo = cabeça baixa), com referência móvel dos últimos 10 s."""

    def __init__(self):
        self._recent = deque()  # (t, pitch) do último segundo e meio
        self._reference = deque()  # pitch a ~5 Hz, só fora de cabeceio
        self._next_reference = -math.inf
        self._down_since = None
        self._fell_fast = False
        self._waiting_return = False

    def update(self, t: float, pitch: float | None) -> bool:
        """True no quadro em que um cabeceio termina."""
        if pitch is None:
            self._recent.clear()
            self._down_since = None
            self._waiting_return = False
            return False
        if not self._reference:
            self._add_reference(t, pitch)
            self._remember(t, pitch)
            return False

        reference = statistics.median(value for _, value in self._reference)
        deviation = pitch - reference
        nod = False
        if self._waiting_return:
            self._waiting_return = deviation > NOD_RECOVERED_DEG
        elif self._down_since is None:
            if deviation >= NOD_MIN_DEG:
                near = [moment for moment, value in self._recent if value - reference <= NOD_NEAR_REFERENCE_DEG]
                self._down_since = t
                self._fell_fast = bool(near) and t - near[-1] <= NOD_MAX_FALL_S
            else:
                self._add_reference(t, pitch)
        elif deviation <= NOD_RECOVERED_DEG:
            nod = self._fell_fast and NOD_MIN_DOWN_S <= t - self._down_since <= NOD_MAX_DOWN_S
            self._down_since = None
        elif t - self._down_since > NOD_MAX_DOWN_S:
            self._down_since = None
            self._waiting_return = True
        self._remember(t, pitch)
        return nod

    def _remember(self, t: float, pitch: float) -> None:
        self._recent.append((t, pitch))
        while self._recent and self._recent[0][0] < t - NOD_RECENT_S:
            self._recent.popleft()

    def _add_reference(self, t: float, pitch: float) -> None:
        if t < self._next_reference:
            return
        self._next_reference = t + NOD_REFERENCE_STEP_S
        self._reference.append((t, pitch))
        while self._reference and self._reference[0][0] < t - NOD_REFERENCE_S:
            self._reference.popleft()


class DrowsinessMonitor:
    def __init__(self, profile: DriverProfile | None = None, calibrator: Calibrator | None = None,
                 profile_path: Path | None = None):
        self.previous_profile = profile
        self.profile = profile
        self.calibrator = calibrator
        self.profile_path = Path(profile_path) if profile_path else None
        # Calibração recém-terminada, para a linha de base usar os mesmos quadros (vision/engine.py).
        self.last_calibration: Calibrator | None = None
        self._model = OpennessModel(profile)
        self._tracker = EyeStateTracker()
        self._perclos = PerclosWindow()
        self._blinks = deque()  # (fim, Blink)
        self._long_closures = deque()
        self._yawns = deque()
        self._nods = deque()
        self._nod_tracker = NodTracker()
        # Chamadas a cada piscada detectada com (t, Blink): o modo teste do app compara com a marcação manual.
        self.blink_listeners = []
        self._frame_times = deque(maxlen=120)
        self._pending_closed = 0.0
        self._last_t = None
        self._critical_stage = 0
        self._closure_pitch = None
        self._yawn_start = None
        self._yawn_counted = False
        self._face_missing_since = None
        self._last_event_at = {}
        self._attention_since = None
        self._next_evaluation = -math.inf
        self._level = 0
        self._reasons = []
        self._details = {}

    @property
    def fps(self) -> float | None:
        if len(self._frame_times) < 10:
            return None
        span = self._frame_times[-1] - self._frame_times[0]
        return (len(self._frame_times) - 1) / span if span > 0 else None

    @property
    def details(self) -> dict:
        """Métricas de janela da última avaliação (uma vez por segundo)."""
        return self._details

    def recalibrate(self, calibrator: Calibrator) -> None:
        """Nova calibração (ex.: troca de motorista). O perfil atual segue valendo até ela terminar."""
        self.previous_profile = self.profile
        self.calibrator = calibrator

    def update(self, metrics) -> Assessment:
        t = metrics.timestamp
        assessment = Assessment(face_found=metrics.face_found)
        dt = 0.0
        if self._last_t is not None and 0 < t - self._last_t <= MAX_FRAME_GAP_S:
            dt = t - self._last_t
        self._last_t = t
        self._frame_times.append(t)
        assessment.fps = self.fps

        if self.calibrator is not None:
            self.calibrator.add(metrics)
            assessment.calibrating = True
            assessment.calibration_progress = self.calibrator.progress
            if self.calibrator.done():
                self._finish_calibration(assessment)

        openness, source = self._model.openness(metrics)
        assessment.openness = openness
        assessment.frame_source = source
        self._track_face_missing(t, metrics.face_found, assessment)

        if openness is not None:
            self._perclos.add_valid(t, dt)
        blink = self._tracker.update(t, openness)
        closed_for = self._tracker.closed_for
        assessment.closed_for = closed_for

        # No PERCLOS, o fechamento só conta depois de passar de 250 ms.
        if openness is not None and openness <= P80_OPENNESS:
            self._pending_closed += dt
            if closed_for >= SHORT_CLOSURE_S:
                self._perclos.add_closed(t, self._pending_closed)
                self._pending_closed = 0.0
        elif openness is not None:
            self._pending_closed = 0.0

        if blink is not None:
            self._on_blink(t, blink)
        self._track_yawn(t, metrics)
        if self._nod_tracker.update(t, metrics.pitch if metrics.face_found else None):
            self._nods.append(t)
        self._check_critical(t, closed_for, metrics, assessment)

        if t >= self._next_evaluation:
            self._next_evaluation = t + EVALUATE_EVERY_S
            self._level, self._reasons, self._details = self._evaluate(t)
            level_details = dict(self._details, motivos=list(self._reasons))
            if self._level == 2:
                self._emit(t, "sonolencia", 3, 0.0, assessment, alarm=True, details=level_details)
            elif self._level == 1:
                self._emit(t, "atencao", 2, 0.0, assessment, alarm=False, details=level_details)

        assessment.perclos_60s = self._details.get("perclos_60s")
        assessment.blinks_last_minute = sum(1 for end, _ in self._blinks if t - end <= 60.0)
        if assessment.level < 3:
            assessment.level = self._level
            assessment.reasons = list(self._reasons)
        assessment.status = self._status(assessment)
        return assessment

    def _status(self, assessment: Assessment) -> str:
        if assessment.level == 3:
            return "PERIGO: OLHOS FECHADOS"
        if assessment.level == 2:
            return "SONOLENCIA"
        if assessment.level == 1:
            return "ATENCAO"
        if not assessment.face_found:
            return "ROSTO NAO ENCONTRADO"
        if assessment.calibrating:
            return f"CALIBRANDO {int(assessment.calibration_progress * 100)}%"
        return "ACORDADO"

    def _emit(self, t, alert_type, risk_level, duration, assessment, alarm, details) -> None:
        last = self._last_event_at.get(alert_type)
        if last is not None and t - last < COOLDOWN_S.get(alert_type, 0.0):
            return
        self._last_event_at[alert_type] = t
        assessment.events.append(DetectedEvent(alert_type, risk_level, round(duration, 2), details))
        if alarm:
            assessment.alarm = True

    def _check_critical(self, t, closed_for, metrics, assessment) -> None:
        if closed_for <= 0.0:
            self._critical_stage = 0
            self._closure_pitch = None
            return
        if self._closure_pitch is None:
            self._closure_pitch = metrics.pitch

        for stage, (threshold, alert_type, risk_level) in enumerate(CRITICAL_STAGES, start=1):
            if closed_for >= threshold and self._critical_stage < stage:
                self._critical_stage = stage
                details = {
                    "fechado_s": round(closed_for, 2),
                    "calibrando": assessment.calibrating,
                    "medida": assessment.frame_source,
                }
                if metrics.pitch is not None and self._closure_pitch is not None:
                    details["variacao_cabeca_graus"] = round(metrics.pitch - self._closure_pitch, 1)
                details.update(self._window_details(t))
                assessment.events.append(DetectedEvent(alert_type, risk_level, round(closed_for, 2), details))

        if closed_for >= MICROSLEEP_S:
            assessment.level = 3
            assessment.alarm = True
            assessment.reasons = [CRITICAL_STAGES[self._critical_stage - 1][1]]

    def _on_blink(self, t, blink) -> None:
        for listener in self.blink_listeners:
            listener(t, blink)
        if blink.closed_duration >= LONG_CLOSURE_S:
            self._long_closures.append(t)
        if blink.min_openness <= COMPLETE_BLINK_OPENNESS and blink.duration <= MAX_BLINK_S:
            self._blinks.append((t, blink))
        horizon = t - 900.0
        for times in (self._long_closures, self._yawns, self._nods):
            while times and times[0] < horizon:
                times.popleft()
        while self._blinks and self._blinks[0][0] < horizon:
            self._blinks.popleft()

    def _track_yawn(self, t, metrics) -> None:
        jaw = metrics.jaw_open if metrics.face_found else None
        baseline = self.profile.jaw_open_baseline if self.profile and self.profile.jaw_open_baseline else 0.0
        threshold = max(YAWN_JAW_MIN, baseline + YAWN_JAW_ABOVE_BASELINE)
        if jaw is not None and jaw >= threshold:
            if self._yawn_start is None:
                self._yawn_start = t
                self._yawn_counted = False
            elif not self._yawn_counted and t - self._yawn_start >= YAWN_MIN_S:
                self._yawns.append(t)
                self._yawn_counted = True
        elif jaw is None or jaw < threshold - 0.1:
            self._yawn_start = None

    def _track_face_missing(self, t, face_found, assessment) -> None:
        if face_found:
            self._face_missing_since = None
            return
        if self._face_missing_since is None:
            self._face_missing_since = t
            return
        missing = t - self._face_missing_since
        if missing >= FACE_MISSING_EVENT_S:
            self._emit(t, "rosto_nao_detectado", 1, missing, assessment, alarm=False,
                       details={"sem_rosto_s": round(missing, 1)})

    def window_details(self, t) -> dict:
        return self._window_details(t)

    def _window_details(self, t) -> dict:
        fps = self.fps
        recent = [blink for end, blink in self._blinks if t - end <= 300.0]
        valid_5min = self._perclos.valid_seconds(t, 300.0)
        details = {
            "piscadas_5min": len(recent),
            "piscadas_60s": sum(1 for end, _ in self._blinks if t - end <= 60.0),
            "piscadas_por_min": round(len(recent) / (valid_5min / 60.0), 1) if valid_5min >= 60.0 else None,
            "fechamentos_longos_5min": _count_since(self._long_closures, t, 300.0),
            "bocejos_10min": _count_since(self._yawns, t, 600.0),
            "cabeceios_10min": _count_since(self._nods, t, 600.0),
            "fps": round(fps, 1) if fps else None,
        }
        if fps is not None and fps >= MIN_FPS_FOR_DURATION and len(recent) >= MIN_BLINKS_FOR_DURATION:
            details["duracao_mediana_ms"] = round(statistics.median(b.duration for b in recent) * 1000)
            amplitudes = [b.amplitude for b in recent if b.amplitude is not None]
            if len(amplitudes) >= MIN_BLINKS_FOR_DURATION:
                details["amplitude_mediana"] = round(statistics.median(amplitudes), 3)
        if fps is not None and fps >= MIN_FPS_FOR_VELOCITY:
            for key, values in (("avr_fechamento_ms", [b.closing_avr for b in recent]),
                                ("avr_abertura_ms", [b.opening_avr for b in recent])):
                values = [v for v in values if v is not None]
                if len(values) >= MIN_BLINKS_FOR_DURATION:
                    details[key] = round(statistics.median(values) * 1000, 1)
        perclos_3min = self._perclos.value(t, 180.0)
        details["perclos_3min"] = round(perclos_3min, 3) if perclos_3min is not None else None
        perclos_60s = self._perclos.value(t, 60.0)
        details["perclos_60s"] = round(perclos_60s, 3) if perclos_60s is not None else None
        if self.profile is not None:
            if self.profile.blink_duration_median_s:
                details["duracao_base_ms"] = round(self.profile.blink_duration_median_s * 1000)
            if self.profile.blink_closing_avr_median_s:
                details["avr_fechamento_base_ms"] = round(self.profile.blink_closing_avr_median_s * 1000, 1)
            details["perclos_base"] = round(self.profile.perclos_baseline, 3)
        return details

    def _evaluate(self, t):
        details = self._window_details(t)
        if self.profile is None:
            return 0, [], details  # sem linha de base individual, só os gatilhos críticos valem

        strong, mild = [], []
        base_ms = details.get("duracao_base_ms")
        median_ms = details.get("duracao_mediana_ms")
        if base_ms and median_ms:
            ratio = median_ms / base_ms
            details["razao_duracao"] = round(ratio, 2)
            if ratio >= ALERT_DURATION_RATIO:
                strong.append("piscadas_mais_longas")
            elif ratio >= ATTENTION_DURATION_RATIO:
                mild.append("piscadas_mais_longas")

        base_avr = details.get("avr_fechamento_base_ms")
        avr = details.get("avr_fechamento_ms")
        if base_avr and avr:
            ratio = avr / base_avr
            details["razao_avr_fechamento"] = round(ratio, 2)
            if ratio >= ATTENTION_AVR_RATIO:
                mild.append("palpebra_mais_lenta")

        perclos_3min = details.get("perclos_3min")
        if perclos_3min is not None:
            if perclos_3min >= ALERT_PERCLOS:
                strong.append("olhos_fechados_por_mais_tempo")
            elif perclos_3min >= max(ATTENTION_PERCLOS_MIN, ATTENTION_PERCLOS_FACTOR * self.profile.perclos_baseline):
                mild.append("olhos_fechados_acima_do_normal")

        long_closures = details["fechamentos_longos_5min"]
        if long_closures >= ALERT_LONG_CLOSURES_5MIN:
            strong.append("fechamentos_longos")
        elif long_closures >= 1:
            mild.append("fechamento_longo")

        nods = details["cabeceios_10min"]
        if nods >= ALERT_NODS_10MIN:
            strong.append("cabeceios")
        elif nods >= ATTENTION_NODS_10MIN:
            mild.append("cabeceios")

        if details["bocejos_10min"] >= ATTENTION_YAWNS_10MIN:
            mild.append("bocejos")

        if strong or mild:
            if self._attention_since is None:
                self._attention_since = t
        else:
            self._attention_since = None

        if strong:
            return 2, strong, details
        if mild and t - self._attention_since >= ATTENTION_PERSIST_S:
            return 2, mild + ["atencao_persistente"], details
        if mild:
            return 1, mild, details
        return 0, [], details

    def _finish_calibration(self, assessment: Assessment) -> None:
        calibrator, self.calibrator = self.calibrator, None
        self.last_calibration = calibrator
        assessment.calibrating = False
        assessment.calibration_progress = 1.0
        profile = calibrator.result = calibrator.build_profile()
        if profile is None:
            logger.warning("Calibração sem dados suficientes; seguindo com %s.",
                           "o perfil anterior" if self.previous_profile else "a referência adaptativa")
            return

        details = {"perfil": profile.summary(), "usando_perfil_anterior": False}
        if profile.looked_alert or self.previous_profile is None:
            self._activate(profile)
            if profile.looked_alert and self.profile_path is not None:
                profile.save(self.profile_path)
        else:
            details["usando_perfil_anterior"] = True

        if profile.looked_alert:
            assessment.events.append(DetectedEvent("calibracao_concluida", 1, round(profile.valid_seconds, 1), details))
            logger.info("Calibração concluída: EAR aberto %.3f, fechado %.3f, %d piscadas, duração mediana %s ms.",
                        profile.ear_open, profile.ear_closed, profile.blinks,
                        round(profile.blink_duration_median_s * 1000) if profile.blink_duration_median_s else "?")
        else:
            assessment.events.append(DetectedEvent("calibracao_suspeita", 2, round(profile.valid_seconds, 1), details))
            logger.warning("Calibração suspeita: o motorista pode já estar sonolento (PERCLOS %.1f%%, maior fechamento %.2f s).",
                           profile.perclos_baseline * 100, profile.longest_closure_s)

    def _activate(self, profile: DriverProfile) -> None:
        self.profile = profile
        self._model = OpennessModel(profile)
        self._tracker.reset()
        self._pending_closed = 0.0
