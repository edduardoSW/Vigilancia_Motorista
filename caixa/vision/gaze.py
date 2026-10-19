"""Direção do olhar (cabeça + olho) e "frente" do motorista pela moda do olhar (spec 027, DMS-02 e DMS-12).

Fontes:
- Victor, Harbluk & Engström, 2005 (PRC, "percent road centre"): % do olhar num círculo de 8° de raio centrado na
  MODA do olhar (o ângulo mais frequente). A moda ignora olhadas ao espelho e ao painel, ao contrário da mediana da
  calibração, e se recentra quando o motorista ajusta o banco. PRC e desvio-padrão do olhar foram mais sensíveis que
  medidas por olhar (via SWOV e arXiv 2104.05677; fonte secundária).
- Euro NCAP 2026, Safe Driving · Driver Engagement v1.2, §1.2.1: o sistema precisa pegar o olhar só com os olhos
  (*lizard*) e só com a cabeça (*owl*). Tawari, Chen & Trivedi, 2014: só a cabeça acertou 79,8% das zonas; com a íris,
  94,9%. Por isso o olhar é cabeça + olho, e sem íris o modo "cabeca" é o degradado.
- Ângulo do olho ≈ asin(1,25 × deslocamento da íris em meias larguras do olho), o mesmo de vision/activation.py
  (globo de ~12 mm e meia fenda de ~15 mm). Direção = yaw + φh, pitch + φv: aproximação aditiva, boa até ~20°.
  Hipótese: o sinal bate com rotation_to_euler (yaw + = rosto para a direita da imagem = motorista olhando para a
  esquerda dele; pitch + = para baixo); conferir girando uma foto em 3D. A matriz do MediaPipe usa câmera virtual
  de 63°: vale a variação em relação à frente, não o ângulo absoluto.
- Pose filtrada por One Euro (vision/filtros.py, DMS-14). O olho não: os pontos já saem filtrados do MediaPipe.
- PRC e desvio do olhar vão só para o registro: PRC ↑ e desvio ↓ marcam carga cognitiva (Victor 2005), e a entropia
  do olhar SOBE com a privação de sono (Shiferaw et al., 2018); nenhum dos dois dispara aviso (DMS-12).

Frente = célula de 2° de maior peso num histograma com decaimento exponencial (meia-vida 10 min), refinada pela média
ponderada da vizinhança 3×3. Um segundo histograma rápido (meia-vida 45 s) recentra a frente depois de o banco ou a
câmera mudarem (DMS-02b), mas nunca para mais de 20° da âncora (calibração ou primeira frente): olhar o colo ou o
celular por minutos não vira "frente". Só aprende com o rosto visível, olho aberto e, se houver velocidade, a partir
de 20 km/h. Todos os números de tempo e ângulo aqui são hipótese até a gravação na cabine.
"""
from __future__ import annotations

import heapq
import math
import statistics
from collections import deque
from dataclasses import dataclass

EYE_ROTATION_GAIN = 1.25
CELL_DEG = 2.0
MAX_ANGLE_DEG = 90.0
LONG_HALF_LIFE_S = 600.0
SHORT_HALF_LIFE_S = 45.0
MIN_CENTER_WEIGHT_S = 10.0
PROFILE_SEED_WEIGHT_S = 20.0
CENTER_EVERY_S = 1.0
RECENTER_MIN_SHIFT_DEG = 6.0
RECENTER_SHARE = 0.4
RECENTER_HOLD_S = 20.0
MAX_DRIFT_FROM_ANCHOR_DEG = 20.0
PEAK_CANDIDATES = 8
PEAK_POOL = 48
MIN_SPEED_TO_LEARN_KMH = 20.0
# Olho usado para a zona: não fechado e íris com tamanho mínimo (a 640 px a íris tem ~8 a 10 px; pesquisa §4.6).
MIN_OPENNESS_FOR_ZONE = 0.3
MIN_OPENNESS_TO_LEARN = 0.6
MIN_IRIS_PX = 8.0
CLOSED_OPENNESS = 0.2
GLARE_MAX_FRACTION = 0.02  # o mesmo de vision/eyes.py (DMS-07): com reflexo, a íris também não vale
PRC_RADIUS_DEG = 8.0
PRC_WINDOW_S = 60.0
PRC_SAMPLE_S = 0.2
PRC_MIN_SHARE = 0.6
GUIDED_MIN_SAMPLES = 15


def pstdev(values) -> float:
    """Desvio-padrão populacional em ponto flutuante (o do statistics usa frações exatas: lento no laço da câmera)."""
    values = list(values)
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    return math.sqrt(max(0.0, sum(v * v for v in values) / len(values) - mean * mean))


def eye_angle(offset: float, gain: float = EYE_ROTATION_GAIN) -> float:
    return math.degrees(math.asin(max(-1.0, min(1.0, gain * offset))))


def combined_gaze(yaw: float, pitch: float, gaze_x: float, gaze_y: float, gain: float = EYE_ROTATION_GAIN):
    """(yaw, pitch) do olhar em graus: cabeça + olho, no sentido de vision/face.py."""
    return yaw + eye_angle(gaze_x, gain), pitch + eye_angle(gaze_y, gain)


@dataclass
class GazeReading:
    t: float
    mode: str  # olhar, cabeca, olhar_para_baixo, olhos_fechados, sem_rosto
    ready: bool = False
    yaw: float | None = None  # direção usada (olhar ou só a cabeça), graus
    pitch: float | None = None
    delta_yaw: float | None = None  # em relação à frente; + = esquerda do motorista
    delta_pitch: float | None = None  # + = para baixo
    head_yaw: float | None = None  # pose filtrada
    head_pitch: float | None = None


class _DecayedHistogram:
    """Histograma 2D com decaimento exponencial. Pesos guardados multiplicados por e^{taxa·(t - t0)}: somar é O(1)."""

    def __init__(self, half_life_s: float):
        self.rate = math.log(2.0) / half_life_s
        self.cells: dict = {}
        self.total = 0.0
        self.t0 = None

    def _scale(self, t: float) -> float:
        return math.exp(self.rate * (t - self.t0))

    def add(self, t: float, yaw: float, pitch: float, weight: float) -> None:
        if self.t0 is None:
            self.t0 = t
        elif self.rate * (t - self.t0) > 40.0:
            self._renormalize(t)
        value = weight * self._scale(t)
        key = (round(yaw / CELL_DEG), round(pitch / CELL_DEG))
        self.cells[key] = self.cells.get(key, 0.0) + value
        self.total += value

    def weight(self, t: float) -> float:
        return 0.0 if self.t0 is None else self.total / self._scale(t)

    def _renormalize(self, t: float) -> None:
        factor = 1.0 / self._scale(t)
        floor = self.total * factor * 1e-6
        self.cells = {key: w * factor for key, w in self.cells.items() if w * factor > floor}
        self.total = sum(self.cells.values())
        self.t0 = t

    def copy_from(self, other: _DecayedHistogram, t: float) -> None:
        """Assume o conteúdo do outro histograma, reescalado para a taxa deste."""
        self.cells = {key: w / other._scale(t) for key, w in other.cells.items()}
        self.total = sum(self.cells.values())
        self.t0 = t

    def peak(self, anchor=None, max_distance: float | None = None):
        """(centro refinado, fração do peso na vizinhança 3×3) ou (None, 0). Com âncora, só células perto dela."""
        if not self.cells or self.total <= 0:
            return None, 0.0
        # Só as células mais pesadas concorrem (custo fixo, sem varrer o histograma inteiro a cada 0,5 s).
        items = heapq.nlargest(PEAK_POOL, self.cells.items(), key=lambda item: item[1])
        if anchor is not None and max_distance is not None:
            items = [(k, w) for k, w in items
                     if math.hypot(k[0] * CELL_DEG - anchor[0], k[1] * CELL_DEG - anchor[1]) <= max_distance]
            if not items:
                return None, 0.0
        best, best_sum, best_mean = None, -1.0, None
        for (i, j), _ in items[:PEAK_CANDIDATES]:
            total = sy = sp = 0.0
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    w = self.cells.get((i + di, j + dj))
                    if w:
                        total += w
                        sy += w * (i + di) * CELL_DEG
                        sp += w * (j + dj) * CELL_DEG
            if total > best_sum:
                best, best_sum, best_mean = (i, j), total, (sy / total, sp / total)
        return best_mean, best_sum / self.total


class ModeTracker:
    """Moda de (yaw, pitch) com recentragem lenta e trava em volta da âncora."""

    def __init__(self, seed=None):
        self._long = _DecayedHistogram(LONG_HALF_LIFE_S)
        self._short = _DecayedHistogram(SHORT_HALF_LIFE_S)
        self.anchor = None
        self.center = None
        self._next_center = -math.inf
        self._shift_since = None
        self._seeded = False
        if seed is not None:
            self.seed(seed)

    def seed(self, center, t: float = 0.0) -> None:
        """Frente inicial (perfil calibrado): vale até os dados mostrarem outra."""
        self.anchor = center
        self.center = center
        self._seeded = True
        for histogram in (self._long, self._short):
            histogram.add(t, center[0], center[1], PROFILE_SEED_WEIGHT_S)

    def recenter(self, center, t: float) -> None:
        """Frente medida de propósito (calibração guiada, alvo "via"): recomeça a moda nela."""
        self._long = _DecayedHistogram(LONG_HALF_LIFE_S)
        self._short = _DecayedHistogram(SHORT_HALF_LIFE_S)
        self._shift_since = None
        self.seed(center, t)

    @property
    def ready(self) -> bool:
        return self.center is not None

    def add(self, t: float, yaw: float, pitch: float, weight: float) -> None:
        yaw = max(-MAX_ANGLE_DEG, min(MAX_ANGLE_DEG, yaw))
        pitch = max(-MAX_ANGLE_DEG, min(MAX_ANGLE_DEG, pitch))
        if self._seeded and self._long.t0 is not None and t < self._long.t0:
            return
        self._long.add(t, yaw, pitch, weight)
        self._short.add(t, yaw, pitch, weight)
        if t >= self._next_center:
            self._next_center = t + CENTER_EVERY_S
            self._update_center(t)

    def _update_center(self, t: float) -> None:
        if self._long.weight(t) < MIN_CENTER_WEIGHT_S:
            return
        if self.anchor is None:
            self.anchor, _ = self._long.peak()
        center, _ = self._long.peak(self.anchor, MAX_DRIFT_FROM_ANCHOR_DEG)
        short, share = self._short.peak(self.anchor, MAX_DRIFT_FROM_ANCHOR_DEG)
        if (center is not None and short is not None and share >= RECENTER_SHARE
                and math.hypot(short[0] - center[0], short[1] - center[1]) >= RECENTER_MIN_SHIFT_DEG):
            if self._shift_since is None:
                self._shift_since = t
            elif t - self._shift_since >= RECENTER_HOLD_S:
                self._long.copy_from(self._short, t)  # banco ou câmera mudaram: a frente nova assume
                center, self._shift_since = short, None
        else:
            self._shift_since = None
        if center is not None:
            self.center = center


class GazeTracker:
    def __init__(self, profile=None, gain: float = EYE_ROTATION_GAIN):
        from vision.filtros import POSE_FILTER, OneEuroFilter

        self.gain = gain
        self._yaw_filter = OneEuroFilter(**POSE_FILTER)
        self._pitch_filter = OneEuroFilter(**POSE_FILTER)
        self._gaze_mode = ModeTracker()
        self._head_mode = ModeTracker()
        self._last_t = None
        self._prc = deque()  # (t, Δyaw, Δpitch) a 5 Hz
        self._next_prc = -math.inf
        self._guided = None
        self._guided_target = None
        self.last: GazeReading | None = None
        if profile is not None:
            self.set_profile(profile)

    def set_profile(self, profile) -> None:
        """Frente inicial pelo perfil calibrado, se a moda ainda não aprendeu sozinha."""
        t = self._last_t or 0.0
        gaze = (getattr(profile, "gaze_center_yaw", None), getattr(profile, "gaze_center_pitch", None))
        head = (getattr(profile, "yaw_baseline", None), getattr(profile, "pitch_baseline", None))
        if None not in gaze and not self._gaze_mode.ready:
            self._gaze_mode.seed(gaze, t)
        if None not in head and not self._head_mode.ready:
            self._head_mode.seed(head, t)

    @property
    def ready(self) -> bool:
        return self._gaze_mode.ready

    @property
    def center(self):
        return self._gaze_mode.center

    @property
    def head_center(self):
        return self._head_mode.center

    def update(self, metrics, openness: float | None = None, source: str = "",
               speed_kmh: float | None = None) -> GazeReading:
        t = metrics.timestamp
        dt = t - self._last_t if self._last_t is not None and 0 < t - self._last_t <= 0.5 else 0.0
        self._last_t = t
        yaw, pitch = getattr(metrics, "yaw", None), getattr(metrics, "pitch", None)
        if not metrics.face_found or yaw is None or pitch is None:
            self.last = GazeReading(t, "sem_rosto", self.ready)
            return self.last
        head_yaw, head_pitch = self._yaw_filter(t, yaw), self._pitch_filter(t, pitch)
        learn = speed_kmh is None or speed_kmh >= MIN_SPEED_TO_LEARN_KMH

        if source == "olhar_para_baixo":
            mode = "olhar_para_baixo"
        elif openness is not None and openness <= CLOSED_OPENNESS:
            mode = "olhos_fechados"
        elif self._iris_usable(metrics, openness):
            mode = "olhar"
        else:
            mode = "cabeca"

        if learn and dt > 0 and mode in ("olhar", "cabeca"):
            self._head_mode.add(t, head_yaw, head_pitch, dt)
        reading = GazeReading(t, mode, self.ready, head_yaw=head_yaw, head_pitch=head_pitch)
        if mode == "olhar":
            reading.yaw, reading.pitch = combined_gaze(head_yaw, head_pitch, metrics.gaze_x, metrics.gaze_y, self.gain)
            if learn and dt > 0 and (openness is None or openness >= MIN_OPENNESS_TO_LEARN):
                self._gaze_mode.add(t, reading.yaw, reading.pitch, dt)
            center = self.center
        else:
            reading.yaw, reading.pitch = head_yaw, head_pitch
            center = self.head_center
        reading.ready = center is not None and self.ready
        if reading.ready:
            reading.delta_yaw, reading.delta_pitch = reading.yaw - center[0], reading.pitch - center[1]
            if mode in ("olhar", "cabeca"):
                self._sample_prc(t, reading)
                if self._guided is not None and self._guided_target is not None:
                    self._guided.setdefault(self._guided_target, []).append((reading.delta_yaw, reading.delta_pitch))
        self.last = reading
        return reading

    def _iris_usable(self, metrics, openness) -> bool:
        gaze_x, gaze_y = getattr(metrics, "gaze_x", None), getattr(metrics, "gaze_y", None)
        if gaze_x is None or gaze_y is None:
            return False
        iris = getattr(metrics, "iris_diameter_px", None)
        glare = getattr(metrics, "glare_fraction", None)
        return ((iris is None or iris >= MIN_IRIS_PX) and (glare is None or glare <= GLARE_MAX_FRACTION)
                and (openness is None or openness >= MIN_OPENNESS_FOR_ZONE))

    def _sample_prc(self, t: float, reading: GazeReading) -> None:
        if t < self._next_prc:
            return
        self._next_prc = t + PRC_SAMPLE_S
        inside = math.hypot(reading.delta_yaw, reading.delta_pitch) <= PRC_RADIUS_DEG
        self._prc.append((t, reading.delta_yaw, reading.delta_pitch, inside))
        while self._prc and self._prc[0][0] < t - PRC_WINDOW_S:
            self._prc.popleft()

    def window_metrics(self, t: float) -> dict:
        """DMS-12: PRC e desvio-padrão do olhar nos últimos 60 s (None com menos de 60% do tempo medido)."""
        while self._prc and self._prc[0][0] < t - PRC_WINDOW_S:
            self._prc.popleft()
        result = {"prc_60s": None, "desvio_olhar_yaw_graus": None, "desvio_olhar_pitch_graus": None}
        if len(self._prc) < PRC_MIN_SHARE * PRC_WINDOW_S / PRC_SAMPLE_S:
            return result
        inside = sum(1 for sample in self._prc if sample[3])
        result["prc_60s"] = round(inside / len(self._prc), 3)
        result["desvio_olhar_yaw_graus"] = round(pstdev(sample[1] for sample in self._prc), 1)
        result["desvio_olhar_pitch_graus"] = round(pstdev(sample[2] for sample in self._prc), 1)
        return result

    # Calibração guiada (opcional, ~30 s no app de teste ou na instalação): "olhe para o espelho esquerdo...".
    @property
    def guided_active(self) -> bool:
        return self._guided is not None

    def start_guided_calibration(self) -> None:
        self._guided, self._guided_target = {}, None

    def guided_target(self, name: str | None) -> None:
        """Alvo que a tela está pedindo agora (None = pausa entre um alvo e outro)."""
        self._guided_target = name

    def finish_guided_calibration(self) -> dict:
        """{alvo: [Δyaw, Δpitch]} medianos, só dos alvos com amostras suficientes. "via" recentra a frente."""
        collected, self._guided, self._guided_target = self._guided or {}, None, None
        result = {}
        for name, values in collected.items():
            if len(values) >= GUIDED_MIN_SAMPLES:
                result[name] = [round(statistics.median(v[0] for v in values), 1),
                                round(statistics.median(v[1] for v in values), 1)]
        if "via" in result and self.center is not None:
            dy, dp = result["via"]
            self._gaze_mode.recenter((self.center[0] + dy, self.center[1] + dp), self._last_t or 0.0)
        return result
