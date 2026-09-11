"""Sinais compatíveis com ativação atípica (módulo 2). Não detecta droga e nunca deve ser apresentado assim.

O que se sabe, e o que não:
- Pupila: lisdexanfetamina dilatou a pupila nas duas luzes testadas, medida como desvio da linha de base de cada
  pessoa (Kuijpers et al., 2025). É o sinal com melhor evidência, mas só é medido com câmera infravermelha
  (vision/pupil.py) e só é comparado dentro da mesma faixa de luz.
- Frequência de piscadas: a relação com estimulantes e drogas dopaminérgicas é inconsistente na literatura, com
  estudos de aumento, sem mudança e de redução (ver THIRD_PARTY_NOTICES.md). Por isso entra o desvio nos dois
  sentidos, com peso baixo.
- Piscadas mais curtas que o normal da pessoa e olhar mais agitado (mais sacadas, maior entropia de transição do
  olhar) são hipóteses coerentes com ativação, sem validação para estimulantes. O álcool, depressor, reduziu a
  entropia do olhar (Shiferaw et al., 2019). Aumento acima do normal é associado a interferência, como ansiedade.
- Estresse, cafeína, pouca luz, conversa e medicamentos causam os mesmos sinais. Por isso vários sinais precisam
  convergir, tudo é comparado com a linha de base da própria pessoa e a saída traz nível de confiança.

Sem dados de motoristas sob efeito de anfetamina, pesos e limiares são hipóteses de trabalho. Validar exige coleta
com aprovação de comitê de ética (CEP/CONEP).
"""
from __future__ import annotations

import math
import statistics
from bisect import bisect_right
from collections import Counter, deque
from dataclasses import dataclass, field

# Peso de cada sinal no índice. Pupila com faixa de luz vinda da própria imagem (sem sensor de luz) pesa menos:
# a câmera ajusta a exposição e, no infravermelho, a imagem mostra o iluminador, não a luz ambiente.
WEIGHTS = {
    "pupila_iris": 0.40,
    "piscadas_por_min": 0.15,
    "duracao_mediana_ms": 0.15,
    "sacadas_por_min": 0.15,
    "entropia_transicao_bits": 0.15,
}
PUPIL_WEIGHT_IMAGE_LIGHT = 0.25
# +1 = acima do normal conta, -1 = abaixo do normal conta, 0 = desvio nos dois sentidos conta.
DIRECTION = {
    "pupila_iris": 1,
    "piscadas_por_min": 0,
    "duracao_mediana_ms": -1,
    "sacadas_por_min": 1,
    "entropia_transicao_bits": 1,
}
SIGNAL_NAMES = {
    "pupila_iris": "pupila_maior_que_o_normal_na_mesma_luz",
    "piscadas_por_min": "frequencia_de_piscadas_fora_do_normal",
    "duracao_mediana_ms": "piscadas_mais_curtas_que_o_normal",
    "sacadas_por_min": "mais_movimentos_rapidos_dos_olhos",
    "entropia_transicao_bits": "olhar_mais_disperso",
}
Z_FULL = 2.5  # z a partir do qual o sinal contribui por inteiro
Z_SIGNAL = 1.5  # z a partir do qual o sinal conta como presente
MIN_CONVERGENT = 2
INDEX_MILD = 0.35
INDEX_COMPATIBLE = 0.55
MIN_CONFIDENCE = 0.35
CONFIDENCE_LABELS = ((0.6, "alta"), (0.35, "media"), (0.0, "baixa"))
MIN_FPS_FULL_CONFIDENCE = 25.0

WINDOW_S = 60.0
GAZE_SAMPLE_S = 0.2  # 5 Hz: aproxima uma amostra por fixação para a entropia de transição
GAZE_CELL_DEG = 5.0
GAZE_RANGE_DEG = 40.0
MIN_GAZE_SHARE = 0.6
MIN_OPENNESS_FOR_GAZE = 0.6
MIN_OPENNESS_FOR_PUPIL = 0.7
MIN_IRIS_PX_FOR_GAZE = 10.0
# Ângulo do olho ≈ asin(1,25 × deslocamento da íris em meias larguras do olho): globo de ~12 mm de raio e meia
# fenda palpebral de ~15 mm. Aproximação: só a variação em relação à própria pessoa importa.
EYE_ROTATION_GAIN = 1.25
# Sacada vista a 30 fps: salto de pelo menos 5° a 100°/s ou mais entre quadros, com a cabeça parada, e o olhar
# fica no novo ponto. Só as sacadas maiores aparecem nessa taxa de quadros.
SACCADE_MIN_DEG = 5.0
SACCADE_MIN_SPEED_DEG_S = 100.0
SACCADE_MAX_HEAD_DEG = 2.0
SACCADE_HOLD_FRAMES = 2
SACCADE_MAX_STEP_S = 0.1
MIN_FPS_FOR_SACCADES = 25.0
MIN_PUPIL_SAMPLES = 30
LUX_BANDS = (10.0, 50.0, 200.0, 1000.0)
IMAGE_BANDS = (50.0, 90.0, 130.0, 170.0)


@dataclass
class ActivationAssessment:
    index: float | None = None
    confidence: float = 0.0
    confidence_label: str = "baixa"
    state: str = "sem_dados"  # sem_dados, sem_sinais, sinais_leves, sinais_compativeis
    signals: list = field(default_factory=list)
    contributions: dict = field(default_factory=dict)
    reason: str | None = None

    @property
    def compatible(self) -> bool:
        return self.state == "sinais_compativeis" and self.confidence >= MIN_CONFIDENCE

    def to_details(self) -> dict:
        return {
            "indice": None if self.index is None else round(self.index, 2),
            "confianca": round(self.confidence, 2),
            "confianca_nivel": self.confidence_label,
            "estado": self.state,
            "sinais": list(self.signals),
            "motivo": self.reason,
        }


def confidence_label(value: float) -> str:
    return next(label for limit, label in CONFIDENCE_LABELS if value >= limit)


def light_band(ambient_lux: float | None, eye_luminance: float | None) -> tuple[str | None, str | None]:
    """(faixa de luz, fonte). Prefere a luz informada pela câmera; senão, a luminância da região dos olhos."""
    if ambient_lux is not None and ambient_lux > 0:
        return f"lux{bisect_right(LUX_BANDS, ambient_lux)}", "lux"
    if eye_luminance is not None:
        return f"img{bisect_right(IMAGE_BANDS, eye_luminance)}", "imagem"
    return None, None


def eye_angle(offset: float) -> float:
    return math.degrees(math.asin(max(-1.0, min(1.0, EYE_ROTATION_GAIN * offset))))


def _entropy(counts) -> float:
    total = sum(counts.values())
    if not total:
        return 0.0
    return max(0.0, -sum((n / total) * math.log2(n / total) for n in counts.values() if n))


def gaze_transition_entropy(cells) -> float | None:
    """Entropia de transição do olhar (bits): incerteza de para onde o olhar vai a partir de onde está."""
    rows: dict = {}
    for origin, destination in cells:
        rows.setdefault(origin, Counter())[destination] += 1
    total = sum(sum(row.values()) for row in rows.values())
    if not total:
        return None
    return sum(sum(row.values()) / total * _entropy(row) for row in rows.values())


class ActivationMonitor:
    """Acumula pupila, olhar e sacadas por quadro e resume numa janela de 60 s."""

    def __init__(self):
        self._pupil = deque()  # (t, razão, faixa de luz, fonte da luz)
        self._gaze = deque()  # (t, célula) a 5 Hz
        self._saccades = deque()
        self._frames = deque()  # [segundo, quadros com olho medido, quadros com rosto]
        self._next_gaze_sample = -math.inf
        self._previous = None  # (t, olho_h, olho_v, yaw, pitch)
        self._candidate = None  # (início, olho_h, olho_v, quadros parado, já estendida)
        self._last_quality = None

    def observe(self, metrics, openness: float | None) -> None:
        t = metrics.timestamp
        self._count_frame(t, metrics.face_found, openness is not None)
        quality = getattr(metrics, "pupil_quality", None)
        if quality:
            self._last_quality = quality

        ratio = getattr(metrics, "pupil_ratio", None)
        if ratio is not None and openness is not None and openness >= MIN_OPENNESS_FOR_PUPIL:
            band, source = light_band(getattr(metrics, "ambient_lux", None), getattr(metrics, "eye_luminance", None))
            if band is not None:
                self._pupil.append((t, ratio, band, source))

        gaze_x, gaze_y = getattr(metrics, "gaze_x", None), getattr(metrics, "gaze_y", None)
        iris = getattr(metrics, "iris_diameter_px", None)
        usable = (metrics.face_found and gaze_x is not None and gaze_y is not None and openness is not None
                  and openness >= MIN_OPENNESS_FOR_GAZE and (iris is None or iris >= MIN_IRIS_PX_FOR_GAZE))
        if usable:
            eye_h, eye_v = eye_angle(gaze_x), eye_angle(gaze_y)
            self._track_saccade(t, eye_h, eye_v, metrics.yaw, metrics.pitch)
            if t >= self._next_gaze_sample and metrics.yaw is not None and metrics.pitch is not None:
                self._next_gaze_sample = t + GAZE_SAMPLE_S
                # yaw positivo = rosto para a direita da imagem e pitch positivo = cabeça baixa (vision/face.py),
                # no mesmo sentido do deslocamento da íris.
                self._gaze.append((t, self._cell(metrics.yaw + eye_h, metrics.pitch + eye_v)))
        else:
            self._previous = None
            self._candidate = None
        self._trim(t)

    def window_metrics(self, t: float, fps: float | None = None) -> dict:
        self._trim(t)
        window = {"fracao_valida_60s": self._valid_fraction()}

        by_band = Counter(band for _, _, band, _ in self._pupil)
        if by_band:
            band, _ = by_band.most_common(1)[0]
            chosen = [(ratio, source) for _, ratio, b, source in self._pupil if b == band]
            if len(chosen) >= MIN_PUPIL_SAMPLES:
                window["pupila_iris"] = round(statistics.median(r for r, _ in chosen), 3)
                window["pupila_faixa_luz"] = band
                window["pupila_fonte_luz"] = chosen[-1][1]
        if "pupila_iris" not in window:
            window["pupila_motivo"] = "poucas_medidas" if by_band else (self._last_quality or "sem_medida")

        samples = list(self._gaze)
        if len(samples) >= MIN_GAZE_SHARE * WINDOW_S / GAZE_SAMPLE_S:
            window["entropia_olhar_bits"] = round(_entropy(Counter(cell for _, cell in samples)), 3)
            pairs = [(c0, c1) for (t0, c0), (t1, c1) in zip(samples, samples[1:]) if t1 - t0 <= 2.5 * GAZE_SAMPLE_S]
            transition = gaze_transition_entropy(pairs)
            if transition is not None:
                window["entropia_transicao_bits"] = round(transition, 3)
            if fps is not None and fps >= MIN_FPS_FOR_SACCADES:
                gaze_minutes = len(samples) * GAZE_SAMPLE_S / 60.0
                window["sacadas_por_min"] = round(len(self._saccades) / gaze_minutes, 1)
        return window

    def _cell(self, horizontal: float, vertical: float) -> tuple[int, int]:
        def index(angle):
            angle = max(-GAZE_RANGE_DEG, min(GAZE_RANGE_DEG - 1e-6, angle))
            return int((angle + GAZE_RANGE_DEG) // GAZE_CELL_DEG)

        return index(horizontal), index(vertical)

    def _track_saccade(self, t, eye_h, eye_v, yaw, pitch) -> None:
        if self._candidate is not None:
            start, h, v, held, extended = self._candidate
            if math.hypot(eye_h - h, eye_v - v) <= SACCADE_MIN_DEG / 2:
                held += 1
                if held >= SACCADE_HOLD_FRAMES:
                    self._saccades.append(start)
                    self._candidate = None
                else:
                    self._candidate = (start, h, v, held, extended)
            elif not extended and held == 0:
                # Sacada longa que ocupou dois quadros: o ponto de chegada é o deste quadro.
                self._candidate = (start, eye_h, eye_v, 0, True)
            else:
                self._candidate = None

        previous = self._previous
        if self._candidate is None and previous is not None and 0 < t - previous[0] <= SACCADE_MAX_STEP_S:
            amplitude = math.hypot(eye_h - previous[1], eye_v - previous[2])
            head = 0.0
            if None not in (yaw, pitch, previous[3], previous[4]):
                head = max(abs(yaw - previous[3]), abs(pitch - previous[4]))
            if (amplitude >= SACCADE_MIN_DEG and amplitude / (t - previous[0]) >= SACCADE_MIN_SPEED_DEG_S
                    and head <= SACCADE_MAX_HEAD_DEG):
                self._candidate = (t, eye_h, eye_v, 0, False)
        self._previous = (t, eye_h, eye_v, yaw, pitch)

    def _count_frame(self, t: float, face: bool, measured: bool) -> None:
        second = math.floor(t)
        if not self._frames or self._frames[-1][0] != second:
            self._frames.append([second, 0, 0])
        bucket = self._frames[-1]
        bucket[1] += 1 if measured else 0
        bucket[2] += 1 if face else 0

    def _valid_fraction(self) -> float:
        total = sum(bucket[2] for bucket in self._frames)
        return round(sum(bucket[1] for bucket in self._frames) / total, 3) if total else 0.0

    def _trim(self, t: float) -> None:
        horizon = t - WINDOW_S
        for items in (self._pupil, self._gaze):
            while items and items[0][0] < horizon:
                items.popleft()
        while self._saccades and self._saccades[0] < horizon:
            self._saccades.popleft()
        while self._frames and self._frames[0][0] < math.floor(horizon):
            self._frames.popleft()


def assess_activation(zscores: dict, window: dict, baseline_quality: float, drowsiness_level: int = 0,
                      fps: float | None = None) -> ActivationAssessment:
    """Índice de 0 a 1, confiança de 0 a 1 e estado. Precisa de linha de base individual."""
    if baseline_quality <= 0:
        return ActivationAssessment(reason="sem_linha_de_base")
    weights = dict(WEIGHTS)
    if window.get("pupila_fonte_luz") == "imagem":
        weights["pupila_iris"] = PUPIL_WEIGHT_IMAGE_LIGHT
    available = {name: z for name, z in zscores.items() if name in weights and z is not None}
    if not available:
        return ActivationAssessment(reason="sem_metricas_comparaveis")

    directional = {name: abs(z) if DIRECTION[name] == 0 else DIRECTION[name] * z for name, z in available.items()}
    contributions = {name: max(0.0, min(value / Z_FULL, 1.0)) for name, value in directional.items()}
    used_weight = sum(weights[name] for name in available)
    index = sum(weights[name] * contributions[name] for name in available) / used_weight

    coverage = used_weight / sum(WEIGHTS.values())
    valid = window.get("fracao_valida_60s", 1.0) or 0.0
    fps_factor = 1.0 if fps is None or fps >= MIN_FPS_FULL_CONFIDENCE else 0.8
    confidence = coverage * baseline_quality * min(1.0, valid / 0.8) * fps_factor
    signals = [SIGNAL_NAMES[name] for name, value in directional.items() if value >= Z_SIGNAL]

    assessment = ActivationAssessment(round(index, 3), round(confidence, 3), confidence_label(confidence),
                                      "sem_sinais", signals, {k: round(v, 2) for k, v in contributions.items()})
    if drowsiness_level >= 1:
        assessment.reason = "sinais_de_sonolencia_presentes"
    elif len(signals) >= MIN_CONVERGENT and index >= INDEX_COMPATIBLE and confidence >= MIN_CONFIDENCE:
        assessment.state = "sinais_compativeis"
    elif len(signals) >= MIN_CONVERGENT and index >= INDEX_MILD:
        assessment.state = "sinais_leves"
    return assessment
