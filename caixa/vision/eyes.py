"""Abertura relativa do olho, perfil individual do motorista e detecção de piscadas e fechamentos.

Base:
- EAR (eye aspect ratio): Soukupová & Čech, 2016.
- PERCLOS P80 (olho pelo menos 80% fechado): Wierwille et al., 1994; Dinges et al., 1998 (NHTSA).
- Início e fim da piscada a meia amplitude: Ingre et al., 2006.
- Razão amplitude/velocidade (AVR) do fechamento e da reabertura: Johns et al., 2003 e 2005. Tem dimensão de
  tempo, então vale mesmo sem calibrar a escala da medida; cresce quando a pálpebra fica lenta com o sono.
- Tempo de fechamento e de reabertura da pálpebra (Schleicher et al., 2008, 129 pessoas: o atraso da reabertura
  está entre os melhores indicadores de sono). Medidos entre 10% e 90% da amplitude da piscada e divididos por 0,8
  (estimativa do movimento inteiro), o que não depende da fase em que o quadro pegou o fundo da piscada.
- Olhar para baixo não é olho fechado (spec 027, DMS-03): olhando o colo a pálpebra desce e o EAR cai sem o olho
  fechar (patente RE39539). Com eyeLookDown do MediaPipe 0,35 acima do normal da pessoa e o classificador (OCEC) ou
  a íris dizendo "aberto", o quadro fica sem abertura (fonte olhar_para_baixo) e vai para a zona "colo" do módulo de
  distração. Limiares da pesquisa; hipótese a confirmar com vídeo real.
- Reflexo nos óculos (DMS-07): pixels saturados na região do olho tiram o EAR daquele quadro. O Euro NCAP 2026
  (§1.1.1) exige funcionar com óculos claros; o limiar de 2% é hipótese.
"""
from __future__ import annotations

import json
import logging
import statistics
from collections import deque
from dataclasses import asdict, dataclass, field, fields
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
# Tempos da pálpebra entre 10% e 90% da amplitude (DMS-06); a reabertura espera até 1 s depois do fim da piscada.
EYELID_LOW_FRACTION = 0.10
EYELID_HIGH_FRACTION = 0.90
REOPENING_WAIT_S = 1.0
# DMS-03: eyeLookDown acima do normal da pessoa e olho dado como aberto pelo classificador ou pela íris.
LOOK_DOWN_ABOVE_BASELINE = 0.35
LOOK_DOWN_DEFAULT_BASELINE = 0.10
LOOK_DOWN_MIN_OPEN_PROB = 0.6
LOOK_DOWN_MIN_IRIS_FRACTION = 0.4
# DMS-07: fração de pixels saturados na região do olho acima da qual o EAR do quadro é descartado.
GLARE_MAX_FRACTION = 0.02


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
    eye_look_down: float | None = None  # blendshape eyeLookDown (vision/face.py), DMS-03
    iris_visible_fraction: float | None = None  # fenda do olho ÷ diâmetro da íris, DMS-03
    glare_fraction: float | None = None  # reflexo nos óculos, DMS-07

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
    # Spec 027. Todos com padrão: perfil salvo antes destes campos continua abrindo (DMS-02c).
    blink_closing_median_s: float | None = None  # DMS-06
    blink_reopening_median_s: float | None = None  # DMS-06
    look_down_baseline: float | None = None  # mediana do eyeLookDown na calibração, DMS-03
    gaze_center_yaw: float | None = None  # "frente" inicial do olhar (cabeça + olho), DMS-02
    gaze_center_pitch: float | None = None
    gaze_zones: dict | None = None  # calibração guiada: {zona: [Δyaw, Δpitch]}, DMS-02
    calibration_quality: str | None = None  # boa, taxa_de_quadros_baixa, poucas_piscadas (CAL-01)
    suspect_reasons: list = field(default_factory=list)  # por que a calibração ficou suspeita (CAL-02)

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
        self._recent_look_down = deque(maxlen=600)

    def looking_down(self, sample) -> bool:
        """DMS-03: olhar para baixo com o olho aberto (eyeLookDown alto e OCEC ou íris dizendo aberto)."""
        look_down = getattr(sample, "eye_look_down", None)
        if look_down is None:
            return False
        profile = self.profile
        if profile is not None and profile.look_down_baseline is not None:
            baseline = profile.look_down_baseline
        else:
            self._recent_look_down.append(look_down)
            baseline = (statistics.median(self._recent_look_down) if len(self._recent_look_down) >= 30
                        else LOOK_DOWN_DEFAULT_BASELINE)
        if look_down < baseline + LOOK_DOWN_ABOVE_BASELINE:
            return False
        open_prob = getattr(sample, "eye_open_prob", None)
        iris = getattr(sample, "iris_visible_fraction", None)
        return ((open_prob is not None and open_prob >= LOOK_DOWN_MIN_OPEN_PROB)
                or (iris is not None and iris >= LOOK_DOWN_MIN_IRIS_FRACTION))

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
        if self.looking_down(sample):
            return None, "olhar_para_baixo"
        pitch_deviation = _deviation(sample.pitch, profile.pitch_baseline if profile else None)
        glare = getattr(sample, "glare_fraction", None)
        ear_usable = (sample.ear is not None and (pitch_deviation is None or pitch_deviation <= MAX_PITCH_DEVIATION_DEG)
                      and (glare is None or glare <= GLARE_MAX_FRACTION))

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
            # Cabeça muito baixa tira o EAR e não sobra outro sinal: o rosto está caindo para fora da medida
            # (vision/drowsiness.py trata como rosto perdido se o olho já estava fechado; ALM-01).
            if (sample.ear is not None and pitch_deviation is not None and pitch_deviation > MAX_PITCH_DEVIATION_DEG
                    and sample.pitch > profile.pitch_baseline):  # pitch positivo = cabeça baixa (vision/face.py)
                return None, "cabeca_baixa"
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
    # DMS-06 (Schleicher et al., 2008): tempo de 90% a 10% fechando e de 10% a 90% reabrindo, ÷ 0,8. A reabertura
    # é preenchida até 1 s depois do fim da piscada (o olho passa de 60% antes de chegar a 90%).
    closing_s: float | None = None
    reopening_s: float | None = None

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


def _eyelid_levels(trace, pre_level: float | None):
    """(índice do fundo, nível de 10%, nível de 90%) da piscada, ou None sem traço ou amplitude."""
    if not trace or len(trace) < 3 or pre_level is None:
        return None
    lowest = min(range(len(trace)), key=lambda i: trace[i][1])
    amplitude = pre_level - trace[lowest][1]
    if amplitude <= 0:
        return None
    floor = trace[lowest][1]
    return (lowest, floor + EYELID_LOW_FRACTION * amplitude, floor + EYELID_HIGH_FRACTION * amplitude)


def _closing_time(trace, levels) -> float | None:
    """Tempo de 90% a 10% da amplitude descendo, ÷ 0,8 (estimativa do fechamento inteiro)."""
    if levels is None:
        return None
    lowest, low, high = levels
    t_low = t_high = None
    for i in range(lowest, 0, -1):
        (t0, o0), (t1, o1) = trace[i - 1], trace[i]
        if t_low is None and o0 >= low > o1:
            t_low = _crossing(t0, o0, t1, o1, low)
        if t_low is not None and o0 >= high > o1:
            t_high = _crossing(t0, o0, t1, o1, high)
            break
    if t_low is None or t_high is None:
        return None
    return max(0.0, t_low - t_high) / (EYELID_HIGH_FRACTION - EYELID_LOW_FRACTION)


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
        self._reopening = None  # piscada terminada esperando o olho chegar a 90% (DMS-06)

    @property
    def in_blink(self) -> bool:
        return self._blink_start is not None

    @property
    def closed_for(self) -> float:
        """Há quanto tempo o olho está continuamente pelo menos 80% fechado."""
        if self._closed_start is None or self._last_t is None:
            return 0.0
        return max(0.0, self._last_t - self._closed_start)

    @property
    def closed_since(self) -> float | None:
        """Instante (interpolado) em que o olho passou de 80% fechado, ou None se não está fechado agora."""
        return self._closed_start

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
        if self._reopening is not None:
            self._track_reopening(prev_t, prev_o, t, openness)
        if self._blink_start is None and openness < BLINK_START_OPENNESS:
            self._reopening = None  # outra piscada antes de reabrir a 90%: sem medida
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
                levels = _eyelid_levels(self._trace, self._pre_level)
                finished = Blink(
                    start=self._blink_start,
                    end=end,
                    duration=max(0.0, end - self._blink_start),
                    closed_duration=max(0.0, self._closed_total),
                    min_openness=self._min_o,
                    amplitude=amplitude,
                    closing_velocity=closing,
                    opening_velocity=opening,
                    closing_s=_closing_time(self._trace, levels),
                )
                self._start_reopening(finished, levels, t)
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

    def _start_reopening(self, blink: Blink, levels, t: float) -> None:
        """Procura no traço a subida por 10% e deixa a de 90% para os próximos quadros."""
        self._reopening = None
        if levels is None or self._trace is None:
            return
        lowest, low, high = levels
        state = {"blink": blink, "low": low, "high": high, "t_low": None, "deadline": t + REOPENING_WAIT_S}
        trace = self._trace
        for i in range(lowest + 1, len(trace)):
            (t0, o0), (t1, o1) = trace[i - 1], trace[i]
            if state["t_low"] is None and o0 < low <= o1:
                state["t_low"] = _crossing(t0, o0, t1, o1, low)
            if state["t_low"] is not None and o0 < high <= o1:
                blink.reopening_s = (_crossing(t0, o0, t1, o1, high) - state["t_low"]) / (
                    EYELID_HIGH_FRACTION - EYELID_LOW_FRACTION)
                return
        self._reopening = state

    def _track_reopening(self, prev_t, prev_o, t: float, openness: float) -> None:
        state = self._reopening
        if t > state["deadline"] or prev_t is None:
            self._reopening = None
            return
        if state["t_low"] is None and openness >= state["low"]:
            state["t_low"] = _crossing(prev_t, prev_o, t, openness, state["low"])
        if state["t_low"] is not None and openness >= state["high"]:
            state["blink"].reopening_s = max(0.0, _crossing(prev_t, prev_o, t, openness, state["high"]) - state["t_low"]) / (
                EYELID_HIGH_FRACTION - EYELID_LOW_FRACTION)
            self._reopening = None
