"""Gestos de sono com as mãos: coçar ou esfregar os olhos e mão no rosto (pedido de 10/09/2026).

Os pontos das mãos vêm do Hand Landmarker que já roda para o celular (vision/phone.py), na mesma thread: nenhum
modelo a mais. Os pontos do rosto vêm do Face Landmarker (vision/face.py).

Base (hipótese, a confirmar): escalas de sonolência avaliada por observador, como a ORD (Wierwille e Ellsworth,
1994), citam esfregar os olhos e o rosto como sinal comportamental. Por isso o gesto é sinal leve: sozinho não vira
alerta e só pesa no risco junto com outro sinal de sono (vision/risk.py).

Regras (limiares iniciais, a validar com vídeos anotados, como as piscadas em vision/evaluation.py):
- Esfregar ou coçar o olho: ponta ou nó do indicador ou do médio perto de um olho (raio proporcional à largura do
  rosto), em vai e vem (2 inversões de direção em até 2 s), por 0,5 s a 5 s. Mais que isso é mão no rosto.
- Mão no rosto: pontos da mão na parte de cima do rosto (testa, olhos, bochechas) por pelo menos 1 s. A faixa da
  boca fica de fora (comer, beber, tapar a boca no bocejo) e as bordas laterais também (mão na orelha).
- Gestos separados por menos de 1,5 s formam um episódio só.
- Mão segurando o celular não conta, nem nada enquanto o celular está no ouvido.
- Mão tapando o rosto: se os pontos do rosto somem, vale o último rosto visto (até 2 s antes de a mão chegar, e
  enquanto a mão continuar ali). O gesto conta como mão no rosto e não gera o aviso de rosto não detectado
  (vision/drowsiness.py). Enquanto a mão está no olho, vision/engine.py desliga as medidas do olho, como nos óculos
  escuros: o olho tapado não vira piscada, PERCLOS nem microssono.

Limitações conhecidas:
- As mãos são medidas cerca de 4 vezes por segundo (DETECT_EVERY_S do celular). Um vai e vem rápido pode ser
  subamostrado; por isso as 2 inversões valem numa janela de 2 s, e não de 1 s.
- O olho "sumir ou fechar" durante o gesto fica só como detalhe do evento (fracao_olho_encoberto), não como
  exigência: com a mão em cima, os pontos do olho costumam continuar "abertos".

Nenhuma imagem é guardada: só contagens, duração e o lado do olho.
"""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field

import numpy as np

from vision.drowsiness import DetectedEvent

RUB_POINTS = (6, 8, 10, 12)  # nó do meio e ponta do indicador e do médio
CONTACT_POINTS = (4, 5, 8, 9, 12, 13, 16, 17, 20)  # pontas e articulações da base: palma e dedos
MIN_CONTACT_POINTS = 3
EYE_RADIUS_FACES = 0.2
CONTACT_INSET_FACES = 0.1  # bordas laterais do rosto fora do contato: mão na orelha não é mão no rosto
UPPER_FACE_FRACTION = 0.62  # da testa até acima da boca
RUB_MIN_REVERSALS = 2
RUB_WINDOW_S = 2.0
# Tremor dos pontos parados fica em poucos pixels; um vai e vem de coçar o olho passa de 0,1 rosto.
RUB_MIN_AMPLITUDE_FACES = 0.06
RUB_MIN_S = 0.5
RUB_MAX_S = 5.0
HAND_ON_FACE_MIN_S = 1.0
MERGE_GAP_S = 1.5
FACE_MEMORY_S = 2.0
EYE_COVER_S = 0.5
COUNT_WINDOW_S = 600.0
EVENT_COOLDOWN_S = 60.0

RUBBING = "olhos_esfregados"
HAND_ON_FACE = "mao_no_rosto"
WINDOW_KEYS = {RUBBING: "coceiras_olhos_10min", HAND_ON_FACE: "maos_no_rosto_10min"}
SIDES = ("direito", "esquerdo")  # olho do motorista, na ordem de vision/face.py (RIGHT_EYE e depois LEFT_EYE)
EYE_OPENNESS_FIELDS = ("ear_right", "ear_left")


@dataclass
class FaceTouchAssessment:
    gesture: str | None = None  # gesto em andamento: olhos_esfregados, mao_no_rosto ou None
    eye_covered: bool = False  # mão no olho agora: as medidas do olho não valem
    face_hidden: bool = False  # rosto perdido com a mão na frente: não é "rosto não detectado"
    rubs_10min: int = 0
    touches_10min: int = 0
    events: list = field(default_factory=list)

    @property
    def episodes_10min(self) -> int:
        return self.rubs_10min + self.touches_10min


def eye_centers(metrics) -> list | None:
    points = getattr(metrics, "eye_points", None)
    if points is None or len(points) == 0:
        return None
    points = np.asarray(points, dtype=np.float32)
    if len(points) == 2:  # YuNet: um ponto por olho
        return [points[0], points[1]]
    half = len(points) // 2
    return [points[:half].mean(axis=0), points[half:].mean(axis=0)]


def touches_upper_face(hand: np.ndarray, box) -> bool:
    x1, y1, x2, y2 = box
    inset = CONTACT_INSET_FACES * (x2 - x1)
    key = hand[list(CONTACT_POINTS)]
    inside = ((key[:, 0] >= x1 + inset) & (key[:, 0] <= x2 - inset)
              & (key[:, 1] >= y1) & (key[:, 1] <= y1 + UPPER_FACE_FRACTION * (y2 - y1)))
    return int(inside.sum()) >= MIN_CONTACT_POINTS


def nearest_eye(hand: np.ndarray, eyes, face_width: float) -> int | None:
    """Olho (0 direito, 1 esquerdo) com um dedo dentro do raio; o mais próximo, se forem os dois."""
    tips = hand[list(RUB_POINTS)]
    best, best_distance = None, EYE_RADIUS_FACES * face_width
    for index, eye in enumerate(eyes):
        distance = float(np.hypot(tips[:, 0] - eye[0], tips[:, 1] - eye[1]).min())
        if distance <= best_distance:
            best, best_distance = index, distance
    return best


def reversal_times(samples, face_width: float) -> list:
    """Instantes em que os dedos invertem a direção no eixo principal do movimento, com amplitude mínima."""
    if len(samples) < 3:
        return []
    points = np.array([(x, y) for _, x, y in samples], dtype=np.float64)
    centered = points - points.mean(axis=0)
    _, _, axes = np.linalg.svd(centered, full_matrices=False)
    positions = centered @ axes[0]
    amplitude = RUB_MIN_AMPLITUDE_FACES * face_width
    times, direction = [], 0
    extreme, extreme_t = positions[0], samples[0][0]
    for (t, _, _), position in zip(samples[1:], positions[1:]):
        if direction == 0:
            if abs(position - extreme) >= amplitude:
                direction, extreme, extreme_t = (1 if position > extreme else -1), position, t
        elif direction * (position - extreme) > 0:
            extreme, extreme_t = position, t
        elif abs(position - extreme) >= amplitude:
            times.append(extreme_t)
            direction, extreme, extreme_t = -direction, position, t
    return times


def repeated_motion(times) -> bool:
    return any(times[i + RUB_MIN_REVERSALS - 1] - times[i] <= RUB_WINDOW_S
               for i in range(len(times) - RUB_MIN_REVERSALS + 1))


@dataclass
class _Episode:
    start: float
    last: float
    face_width: float
    samples: list = field(default_factory=list)  # (t, x, y) dos dedos perto do olho
    sides: list = field(default_factory=list)
    hidden: int = 0


class FaceTouchTracker:
    """Junta as mãos no tempo, fecha os episódios e conta os gestos dos últimos 10 min."""

    def __init__(self):
        self.totals = {RUBBING: 0, HAND_ON_FACE: 0}
        self._episode: _Episode | None = None
        self._done = deque()  # (fim, gesto)
        self._face = None  # (t, caixa, centros dos olhos) do último rosto visto
        self._last_eye_touch = -math.inf
        self._last_event_at = {}
        self._pending = []

    def update(self, t: float, metrics, hands=None, observed_at: float | None = None,
               blocked: bool = False) -> FaceTouchAssessment:
        """hands: mãos livres (sem celular) de uma observação nova, ou None se não chegou observação neste quadro."""
        box = getattr(metrics, "face_box", None) if metrics.face_found else None
        if box is not None:
            self._face = (t, box, eye_centers(metrics))
        episode = self._episode
        if episode is not None and t - episode.last > MERGE_GAP_S:
            self._finish(episode)
            self._episode = None
        if hands is not None and not blocked:
            self._observe(t if observed_at is None else observed_at, t, metrics, hands)

        while self._done and self._done[0][0] < t - COUNT_WINDOW_S:
            self._done.popleft()
        assessment = FaceTouchAssessment(eye_covered=t - self._last_eye_touch <= EYE_COVER_S)
        assessment.rubs_10min = sum(1 for _, gesture in self._done if gesture == RUBBING)
        assessment.touches_10min = len(self._done) - assessment.rubs_10min
        if self._episode is not None:
            assessment.gesture = self._classify(self._episode)
            assessment.face_hidden = not metrics.face_found
        assessment.events, self._pending = self._pending, []
        return assessment

    def window_metrics(self, t: float) -> dict:
        recent = [gesture for end, gesture in self._done if end >= t - COUNT_WINDOW_S]
        return {key: recent.count(gesture) for gesture, key in WINDOW_KEYS.items()}

    def _observe(self, observed_at: float, now: float, metrics, hands) -> None:
        if self._face is None or (now - self._face[0] > FACE_MEMORY_S and self._episode is None):
            return
        _, box, eyes = self._face
        width = box[2] - box[0]
        if width <= 0:
            return
        contact, near = False, None
        for hand in hands:
            side = nearest_eye(hand, eyes, width) if eyes is not None else None
            if side is not None and near is None:
                near = (side, hand)
            contact = contact or side is not None or touches_upper_face(hand, box)
        if not contact:
            return
        episode = self._episode
        if episode is None:
            episode = self._episode = _Episode(start=observed_at, last=observed_at, face_width=width)
        episode.last = observed_at
        if near is not None:
            side, hand = near
            x, y = hand[list(RUB_POINTS)].mean(axis=0)
            episode.samples.append((observed_at, float(x), float(y)))
            episode.sides.append(side)
            episode.hidden += int(not metrics.face_found or getattr(metrics, EYE_OPENNESS_FIELDS[side], 0.0) is None)
            self._last_eye_touch = now

    def _classify(self, episode: _Episode) -> str | None:
        near_s = episode.samples[-1][0] - episode.samples[0][0] if len(episode.samples) >= 2 else 0.0
        if RUB_MIN_S <= near_s <= RUB_MAX_S and repeated_motion(reversal_times(episode.samples, episode.face_width)):
            return RUBBING
        if episode.last - episode.start >= HAND_ON_FACE_MIN_S:
            return HAND_ON_FACE
        return None

    def _finish(self, episode: _Episode) -> None:
        gesture = self._classify(episode)
        if gesture is None:
            return
        end = episode.last
        self._done.append((end, gesture))
        self.totals[gesture] += 1
        last = self._last_event_at.get(gesture)
        if last is not None and end - last < EVENT_COOLDOWN_S:
            return
        self._last_event_at[gesture] = end
        duration = end - episode.start
        details = {"duracao_s": round(duration, 1),
                   WINDOW_KEYS[gesture]: sum(1 for t, g in self._done if g == gesture and t >= end - COUNT_WINDOW_S)}
        if episode.samples:
            details["lado"] = SIDES[max(set(episode.sides), key=episode.sides.count)]
            details["fracao_olho_encoberto"] = round(episode.hidden / len(episode.samples), 2)
        if gesture == RUBBING:
            details["inversoes"] = len(reversal_times(episode.samples, episode.face_width))
        self._pending.append(DetectedEvent(gesture, 1, round(duration, 2), details))
