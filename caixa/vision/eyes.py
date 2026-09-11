"""Abertura relativa do olho, perfil individual do motorista e detecção de piscadas e fechamentos.

Base:
- EAR (eye aspect ratio): Soukupová & Čech, 2016.
- PERCLOS P80 (olho pelo menos 80% fechado): Wierwille et al., 1994; Dinges et al., 1998 (NHTSA).
- Início e fim da piscada a meia amplitude: Ingre et al., 2006.
- Razão amplitude/velocidade (AVR) do fechamento e da reabertura: Johns et al., 2003 e 2005. Tem dimensão de
  tempo, então vale mesmo sem calibrar a escala da medida; cresce quando a pálpebra fica lenta com o sono.
"""
from __future__ import annotations

import json
import logging
import statistics
from collections import deque
from dataclasses import asdict, dataclass, fields
from pathlib import Path

logger = logging.getLogger("drivesafe.eyes")

P80_OPENNESS = 0.20
BLINK_START_OPENNESS = 0.50
BLINK_END_OPENNESS = 0.60  # histerese: evita piscada "dupla" quando a abertura oscila perto de 50%
# Abaixo de ~20 px entre os olhos o erro do EAR dispara (Soukupová & Čech); 30 px dá margem.
MIN_EYE_DISTANCE_PX = 30.0
MAX_YAW_DEVIATION_DEG = 30.0
# Cabeça muito inclinada distorce o EAR; nesses quadros valem só os outros sinais.
MAX_PITCH_DEVIATION_DEG = 25.0
MAX_FRAME_GAP_S = 0.5
# Sinal que quase não muda entre aberto e fechado nessa pessoa é ignorado.
MIN_SIGNAL_SPAN = 0.15
# Abertura "de antes" da piscada: mediana do último meio segundo com o olho aberto.
PRE_BLINK_WINDOW_S = 0.5
# Velocidade da pálpebra só é medida em fechamentos de até ~20 s a 30 fps.
MAX_TRACE_SAMPLES = 600
# O fechamento da pálpebra dura ~100 ms: abaixo de ~28 fps sobram 2 quadros e o pico de velocidade some.
MIN_FPS_FOR_VELOCITY = 28.0


@dataclass
class Sample:
    """Medidas mínimas de um quadro. Aceita FaceMetrics ou dados lidos de um arquivo."""

    timestamp: float
    face_found: bool
    ear: float | None = None
    blink_score: float | None = None
    eye_open_prob: float | None = None
    jaw_open: float | None = None
    pitch: float | None = None
    yaw: float | None = None
    eye_distance_px: float | None = None
    gaze_x: float | None = None
    gaze_y: float | None = None
    iris_diameter_px: float | None = None
    pupil_ratio: float | None = None
    eye_luminance: float | None = None
    ambient_lux: float | None = None

    @classmethod
    def from_metrics(cls, metrics) -> Sample:
        return cls(**{f.name: getattr(metrics, f.name, None) for f in fields(cls)})


@dataclass
class DriverProfile:
    """Padrão individual aprendido na calibração."""

    ear_open: float
    ear_closed: float
    score_open: float | None = None
    score_closed: float | None = None
    classifier_open: float | None = None
    classifier_closed: float | None = None
    blink_duration_median_s: float | None = None
    blink_duration_p90_s: float | None = None
    blink_rate_per_min: float | None = None
    blink_closing_avr_median_s: float | None = None
    blink_opening_avr_median_s: float | None = None
    perclos_baseline: float = 0.0
    jaw_open_baseline: float | None = None
    pitch_baseline: float | None = None
    yaw_baseline: float | None = None
    longest_closure_s: float = 0.0
    blinks: int = 0
    valid_seconds: float = 0.0
    fps: float | None = None
    looked_alert: bool = True
    ear_closed_estimated: bool = False
    created_at: str = ""

    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(path)

    @classmethod
    def load(cls, path: Path) -> DriverProfile | None:
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except ValueError as exc:
            logger.warning("Perfil %s ilegível (%s); ignorando.", path, exc)
            return None
        known = {f.name for f in fields(cls)}
        try:
            return cls(**{key: value for key, value in data.items() if key in known})
        except TypeError as exc:
            logger.warning("Perfil %s incompleto (%s); ignorando.", path, exc)
            return None

    def summary(self) -> dict:
        def rounded(value, digits=3):
            return round(value, digits) if isinstance(value, float) else value

        return {key: rounded(value) for key, value in asdict(self).items()}


def _deviation(value: float | None, baseline: float | None) -> float | None:
    if value is None or baseline is None:
        return None
    return abs(value - baseline)


def _scaled(value: float, open_reference: float | None, closed_reference: float | None) -> float | None:
    """Posição do valor entre a referência de fechado (0) e a de aberto (1)."""
    if open_reference is None or closed_reference is None or abs(open_reference - closed_reference) < MIN_SIGNAL_SPAN:
        return None
    return (value - closed_reference) / (open_reference - closed_reference)


class OpennessModel:
    """Combina EAR, pontuação de piscada do MediaPipe e classificador de olho em abertura relativa:
    1 = aberto habitual da pessoa, 0 = fechado."""

    def __init__(self, profile: DriverProfile | None = None):
        self.profile = profile
        # Sem perfil ainda: referência adaptativa dos últimos ~20 s (a 30 fps).
        self._recent_ear = deque(maxlen=600)
        self._recent_score = deque(maxlen=600)

    def openness(self, sample) -> tuple[float | None, str]:
        """Retorna (abertura, sinais usados). Abertura None = quadro sem medida confiável."""
        if not sample.face_found:
            return None, "sem_rosto"
        if sample.eye_distance_px is not None and sample.eye_distance_px < MIN_EYE_DISTANCE_PX:
            return None, "rosto_pequeno"

        profile = self.profile
        yaw_deviation = _deviation(sample.yaw, profile.yaw_baseline if profile else None)
        if yaw_deviation is not None and yaw_deviation > MAX_YAW_DEVIATION_DEG:
            return None, "rosto_virado"
        pitch_deviation = _deviation(sample.pitch, profile.pitch_baseline if profile else None)
        ear_usable = sample.ear is not None and (pitch_deviation is None or pitch_deviation <= MAX_PITCH_DEVIATION_DEG)

        refs = self._references(sample)
        signals = []
        if ear_usable and refs["ear_open"] is not None:
            span = max(refs["ear_open"] - refs["ear_closed"], 1e-6)
            signals.append(((sample.ear - refs["ear_closed"]) / span, "ear"))
        if sample.blink_score is not None:
            # Pontuação cresce quando o olho fecha: invertida para virar abertura.
            value = _scaled(sample.blink_score, refs["score_open"], refs["score_closed"])
            if value is not None:
                signals.append((value, "pontuacao"))
        if sample.eye_open_prob is not None:
            value = _scaled(sample.eye_open_prob, refs["classifier_open"], refs["classifier_closed"])
            # Sem calibração do classificador, a própria probabilidade de aberto já é uma abertura de 0 a 1.
            signals.append((sample.eye_open_prob if value is None else value, "classificador"))

        if not signals:
            return None, "sem_referencia"
        values = [value for value, _ in signals]
        if len(values) == 1:
            combined = values[0]
        elif len(values) == 2:
            # Os dois sinais precisam concordar que o olho fechou: evita tratar um olho
            # naturalmente pequeno (EAR baixo) como fechado.
            combined = max(values)
        else:
            # Três sinais: vale a maioria, então um sinal falhando sozinho não decide.
            combined = statistics.median(values)
        return max(0.0, min(combined, 1.5)), "+".join(name for _, name in signals)

    def _references(self, sample) -> dict:
        if self.profile is not None:
            p = self.profile
            return {
                "ear_open": p.ear_open, "ear_closed": p.ear_closed,
                "score_open": p.score_open, "score_closed": p.score_closed,
                "classifier_open": p.classifier_open, "classifier_closed": p.classifier_closed,
            }

        refs = dict.fromkeys(("ear_open", "ear_closed", "score_open", "score_closed", "classifier_open", "classifier_closed"))
        if sample.ear is not None and (sample.blink_score is None or sample.blink_score < 0.3):
            self._recent_ear.append(sample.ear)
        if sample.blink_score is not None:
            self._recent_score.append(sample.blink_score)
        if len(self._recent_ear) >= 30:
            refs["ear_open"] = statistics.median(self._recent_ear)
            refs["ear_closed"] = 0.3 * refs["ear_open"]
        if len(self._recent_score) >= 30:
            refs["score_open"] = statistics.median(self._recent_score)
            refs["score_closed"] = min(1.0, refs["score_open"] + 0.5)
        return refs


@dataclass
class Blink:
    start: float
    end: float
    duration: float  # entre as passagens por 50% (fechando) e 60% (reabrindo) de abertura
    closed_duration: float  # tempo com o olho pelo menos 80% fechado
    min_openness: float
    amplitude: float | None = None  # abertura antes da piscada menos a menor abertura
    closing_velocity: float | None = None  # pico de velocidade fechando, em abertura por segundo
    opening_velocity: float | None = None  # pico de velocidade reabrindo

    @property
    def closing_avr(self) -> float | None:
        """AVR do fechamento em segundos (amplitude ÷ pico de velocidade). Maior = pálpebra mais lenta."""
        if self.amplitude is None or not self.closing_velocity:
            return None
        return self.amplitude / self.closing_velocity

    @property
    def opening_avr(self) -> float | None:
        if self.amplitude is None or not self.opening_velocity:
            return None
        return self.amplitude / self.opening_velocity


def _crossing(t0: float | None, o0: float | None, t1: float, o1: float, level: float) -> float:
    """Momento interpolado em que a abertura cruzou `level` entre dois quadros."""
    if t0 is None or o0 is None or o0 == o1:
        return t1
    fraction = min(max((o0 - level) / (o0 - o1), 0.0), 1.0)
    return t0 + fraction * (t1 - t0)


def _eyelid_speeds(trace, pre_level: float | None):
    """(amplitude, pico de velocidade fechando, pico reabrindo) a partir dos quadros da piscada."""
    if not trace or len(trace) < 3 or pre_level is None:
        return None, None, None
    lowest = min(range(len(trace)), key=lambda i: trace[i][1])
    amplitude = max(0.0, pre_level - trace[lowest][1])
    closing = opening = None
    for i in range(1, len(trace)):
        dt = trace[i][0] - trace[i - 1][0]
        if dt <= 0:
            continue
        speed = (trace[i][1] - trace[i - 1][1]) / dt
        if i <= lowest and speed < 0:
            closing = max(closing or 0.0, -speed)
        elif i > lowest and speed > 0:
            opening = max(opening or 0.0, speed)
    return amplitude, closing, opening


class EyeStateTracker:
    def __init__(self):
        self.reset()

    def reset(self) -> None:
        self._last_t = None
        self._last_o = None
        self._blink_start = None
        self._closed_start = None
        self._closed_total = 0.0
        self._min_o = 1.0
        self._history = deque()  # (t, abertura) do último meio segundo fora de piscada
        self._trace = None
        self._pre_level = None

    @property
    def in_blink(self) -> bool:
        return self._blink_start is not None

    @property
    def closed_for(self) -> float:
        """Há quanto tempo o olho está continuamente pelo menos 80% fechado."""
        if self._closed_start is None or self._last_t is None:
            return 0.0
        return max(0.0, self._last_t - self._closed_start)

    def update(self, t: float, openness: float | None) -> Blink | None:
        if openness is None:
            if self._last_t is not None and t - self._last_t > MAX_FRAME_GAP_S:
                self.reset()
            return None

        prev_t, prev_o = self._last_t, self._last_o
        if prev_t is not None and t - prev_t > MAX_FRAME_GAP_S:
            self.reset()
            prev_t = prev_o = None

        finished = None
        if self._blink_start is None and openness < BLINK_START_OPENNESS:
            self._blink_start = _crossing(prev_t, prev_o, t, openness, BLINK_START_OPENNESS)
            self._min_o = openness
            opened = [o for _, o in self._history if o >= BLINK_END_OPENNESS]
            self._pre_level = statistics.median(opened) if opened else prev_o
            self._trace = list(self._history)

        if self._blink_start is not None:
            if self._trace is not None:
                self._trace.append((t, openness))
                if len(self._trace) > MAX_TRACE_SAMPLES:
                    self._trace = None
            self._min_o = min(self._min_o, openness)
            if openness <= P80_OPENNESS and self._closed_start is None:
                self._closed_start = _crossing(prev_t, prev_o, t, openness, P80_OPENNESS)
            elif openness > P80_OPENNESS and self._closed_start is not None:
                self._closed_total += _crossing(prev_t, prev_o, t, openness, P80_OPENNESS) - self._closed_start
                self._closed_start = None

            if openness > BLINK_END_OPENNESS:
                end = _crossing(prev_t, prev_o, t, openness, BLINK_END_OPENNESS)
                amplitude, closing, opening = _eyelid_speeds(self._trace, self._pre_level)
                finished = Blink(
                    start=self._blink_start,
                    end=end,
                    duration=max(0.0, end - self._blink_start),
                    closed_duration=max(0.0, self._closed_total),
                    min_openness=self._min_o,
                    amplitude=amplitude,
                    closing_velocity=closing,
                    opening_velocity=opening,
                )
                self._blink_start = None
                self._closed_total = 0.0
                self._min_o = 1.0
                self._trace = None
                self._pre_level = None
                self._history.clear()

        if self._blink_start is None:
            self._history.append((t, openness))
            while self._history and self._history[0][0] < t - PRE_BLINK_WINDOW_S:
                self._history.popleft()

        self._last_t, self._last_o = t, openness
        return finished
