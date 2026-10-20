"""Gestos de sono com as mãos: coçar ou esfregar os olhos e mão no rosto (pedido de 10/09/2026).

Os pontos das mãos vêm do Hand Landmarker que já roda para o celular (vision/phone.py), na mesma thread: nenhum
modelo a mais. Os pontos do rosto vêm do Face Landmarker (vision/face.py).

Base:
- A escala de sonolência avaliada por observador de Wierwille e Ellsworth (1994, Accid. Anal. Prev. 26(5):571-581),
  nas descrições reproduzidas por Wiegand et al. (VTTI, 2009), põe "rubbing the face or eyes" entre os maneirismos do
  nível moderadamente sonolento: contramedida de fase intermediária, que nem todos apresentam, sem peso numérico.
  Conferido só na fonte secundária (o artigo de 1994 não abriu).
- Tocar o rosto é comum acordado: 26,4 toques por hora em direção normal, mais com carga de trabalho baixa (Ralph et
  al., 2022, Ergonomics 65(7):943-959; lido só o resumo). Por isso só olhos esfregados pesam no risco, e como sinal
  leve: sozinhos não viram alerta, só junto com outro sinal de sono (vision/risk.py). Mão parada no rosto é contada
  e mostrada, mas não pesa.

Revisão de 20/10/2026 (GES-01 a GES-11 em tests/test_face_touch.py, Matheus testando com a webcam do notebook: "coçar os olhos não está pegando
muito bem"). Causas achadas, por simulação com os limiares de antes (os quadros reais não foram gravados):
- Subamostragem: as mãos são medidas a cada 0,25 s (3,75 vezes por s a 30 fps; menos com a CPU ocupada, porque o
  quadro é pulado quando a detecção anterior não acabou). Esfregar é rápido: a 3,5 ou 4 vai e vens por s, medidos 3,75
  vezes por s, o vai e vem aparece como um desvio lento e a regra de "2 inversões em 2 s" falhava em todas as fases;
  medidos 3 vezes por s, falhava de 2,5 a 3,5 por s. O gesto caía em "mão no rosto" (1 s ou mais) ou em nada.
- Só 4 pontos valiam perto do olho (nó e ponta do indicador e do médio, raio de 0,2 rosto): esfregar com o polegar,
  com os nós do punho fechado, com o anelar ou com o dorso dos dedos não contava, nem a palma tapando o olho.
- Sem os pontos do olho (caixa do rosto sem olhos) não havia olho para medir distância.
Regras de agora (limiares iniciais, a validar com vídeos anotados em ferramentas/avaliar_gestos.py):
- Dedo no olho: qualquer ponto do polegar e dos quatro dedos (1 a 20: pontas, nós e dorso) dentro da região do olho,
  uma elipse no eixo dos olhos com 0,2 rosto para fora, 0,15 para cima e para baixo e só 0,13 para dentro (a ponte do
  nariz fica a ~0,21 de cada olho: ajeitar os óculos não é coçar o olho), sem as bordas laterais do rosto (orelha); ou
  o centro do olho dentro do contorno da mão (envoltória dos 21 pontos alargada em meia largura de dedo, 0,06 rosto).
- Esfregar ou coçar o olho: dedo no olho por 0,5 s a 5 s, e (a) vai e vem: 2 inversões de direção em até 2 s, com
  amplitude de 0,05 rosto, nas pontas, nos nós ou na mão inteira, medidos em relação ao olho; ou (b) olho tapado em
  3 medidas ou mais seguidas por 0,8 s ou mais: rosto perdido, olho sem medida, olho fechado (EAR abaixo de 70% do
  aberto da própria pessoa), ou a mão cobrindo o centro do olho E mexendo (desvio robusto da posição de 0,02 rosto ou
  mais: a mão parada na frente do olho aberto, cabeça apoiada, é só mão no rosto). (b) independe da frequência do vai
  e vem, por isso pega o gesto mesmo subamostrado. Mais que 5 s é mão no rosto.
- Mão no rosto: pontos da mão na parte de cima do rosto (testa, olhos, bochechas) por pelo menos 1 s. A faixa da
  boca fica de fora (comer, beber, tapar a boca no bocejo) e as bordas laterais também (mão na orelha).
- Gestos separados por menos de 1,5 s formam um episódio só.
- Mão segurando o celular não conta, nem nada enquanto o celular está no ouvido.
- Mão tapando o rosto: se os pontos do rosto somem, vale a última posição dos olhos e da caixa do rosto (até 1,5 s
  antes de a mão chegar, e enquanto a mão continuar ali). Com a caixa do rosto mas sem os pontos dos olhos, os olhos
  saem da caixa atual na posição relativa do último quadro com olhos. O gesto conta como mão no rosto e não gera o
  aviso de rosto não detectado (vision/drowsiness.py). Enquanto a mão está no olho, vision/engine.py desliga as
  medidas do olho, como nos óculos escuros: o olho tapado não vira piscada, PERCLOS nem microssono.

Limitações conhecidas:
- As mãos continuam medidas cerca de 4 vezes por segundo (DETECT_EVERY_S do celular, vision/phone.py): coçar o olho
  rápido com a ponta do dedo, com o olho aberto e sem a mão cobrir o centro dele, ainda pode passar; e um vai e vem
  exatamente na frequência da medida (3,75 por s) parece mão parada.
- Mão parada tapando o olho por 0,8 s a 5 s com o rosto perdido (ou o olho medido fechado) conta como olho esfregado.
- Coçar a sobrancelha com o dedo vindo de baixo, cruzando o olho na imagem, conta como olho esfregado (na imagem a mão
  está mesmo na frente do olho).
- O Hand Landmarker pode perder a mão encostada no rosto; e a mão que o detector de celular chama de celular (caixa
  recusada na orelha pela spec 028) é tirada dos gestos em vision/phone.py (PhoneMonitor.observe).

Nenhuma imagem é guardada: só contagens, duração e o lado do olho.
"""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field

import cv2
import numpy as np

from vision.drowsiness import DetectedEvent

EYE_TOUCH_POINTS = tuple(range(1, 21))  # polegar (1-4) e os quatro dedos (5-20): pontas, nós e dorso; sem o punho
RUB_POINTS = EYE_TOUCH_POINTS  # nome antigo
CONTACT_POINTS = (4, 5, 8, 9, 12, 13, 16, 17, 20)  # pontas e articulações da base: palma e dedos
MIN_CONTACT_POINTS = 3
# Região do olho em larguras do rosto, no eixo que liga os olhos (vale com a cabeça inclinada).
EYE_REGION_OUT_FACES = 0.2  # para fora e, até EYE_INNER_FACES, para dentro
EYE_REGION_UP_DOWN_FACES = 0.15  # sobrancelha e maçã do rosto ficam perto da borda
EYE_INNER_FACES = 0.13  # canto de dentro do olho a ~0,1; ponte do nariz a ~0,21 (fora)
EYE_RADIUS_FACES = EYE_REGION_OUT_FACES  # nome antigo
HAND_HALF_WIDTH_FACES = 0.06  # os 21 pontos ficam no meio dos dedos: o contorno é alargado em meia largura de dedo
CONTACT_INSET_FACES = 0.1  # bordas laterais do rosto fora do contato: mão na orelha não é mão no rosto
UPPER_FACE_FRACTION = 0.62  # da testa até acima da boca
RUB_MIN_REVERSALS = 2
RUB_WINDOW_S = 2.0
# Tremor dos pontos parados: poucos pixels (estimativa ~0,01 a 0,02 rosto); um vai e vem de coçar o olho passa de 0,1.
RUB_MIN_AMPLITUDE_FACES = 0.05
# Mão mexendo em cima do olho: desvio da posição (em relação ao olho, robusto) de 0,02 rosto ou mais. Um vai e vem de
# 0,05 rosto de amplitude dá ~0,035 mesmo subamostrado; a mão parada (cabeça apoiada) fica no tremor (estimativa).
RUB_MIN_SPREAD_FACES = 0.02
# Sinais do vai e vem: pontas dos dedos, nós (polegar e dedos) e a mão inteira, cada um pela média dos seus pontos.
MOTION_GROUPS = ((4, 8, 12, 16, 20), (2, 3, 6, 7, 10, 11, 14, 15, 18, 19), tuple(range(21)))
RUB_MIN_S = 0.5
RUB_MAX_S = 5.0
# Olho tapado por 0,8 s: 3 medidas ou mais, sem buraco maior que 0,6 s (uma medida perdida a ~4 por s).
COVER_MIN_S = 0.8
COVER_MIN_SAMPLES = 3
COVER_GAP_S = 0.6
# Olho fechado: EAR abaixo de 70% da mediana dos últimos quadros com o olho livre (5 s a 30 fps).
EYE_CLOSED_FRACTION = 0.7
OPEN_REFERENCE_FRAMES = 150
OPEN_REFERENCE_MIN = 15
HAND_ON_FACE_MIN_S = 1.0
MERGE_GAP_S = 1.5
FACE_MEMORY_S = 1.5  # última posição do rosto e dos olhos, antes de a mão chegar
EYE_COVER_S = 0.5
COUNT_WINDOW_S = 600.0
EVENT_COOLDOWN_S = 60.0
EPISODE_HISTORY = 5000  # episódios guardados para o _gestos.csv do analisar_video.py

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


def points_on_eye(points: np.ndarray, eye, other, face_width: float, box=None) -> np.ndarray:
    """Quais pontos caem na região do olho `eye` (`other` é o outro olho, que dá o lado de dentro)."""
    eye = np.asarray(eye, dtype=np.float32)
    inward = None
    if other is not None:
        axis = np.asarray(other, dtype=np.float32) - eye
        length = float(np.hypot(axis[0], axis[1]))
        if length > 0:
            inward = axis / length
    if inward is None:  # um olho só: para dentro é para o meio do rosto
        middle = (box[0] + box[2]) / 2.0 if box is not None else eye[0] + 1.0
        inward = np.array((1.0 if middle >= eye[0] else -1.0, 0.0), dtype=np.float32)
    relative = points - eye
    along = relative @ inward  # positivo = para o nariz
    across = relative @ np.array((-inward[1], inward[0]), dtype=np.float32)
    inside = ((along / (EYE_REGION_OUT_FACES * face_width)) ** 2
              + (across / (EYE_REGION_UP_DOWN_FACES * face_width)) ** 2 <= 1.0) & (along <= EYE_INNER_FACES * face_width)
    if box is not None:
        inset = CONTACT_INSET_FACES * (box[2] - box[0])
        inside &= (points[:, 0] >= box[0] + inset) & (points[:, 0] <= box[2] - inset)
    return inside


def hand_covers(hand: np.ndarray, point, face_width: float) -> bool:
    """O ponto fica dentro do contorno da mão (envoltória dos 21 pontos, alargada em meia largura de dedo)?"""
    hull = cv2.convexHull(np.ascontiguousarray(hand, dtype=np.float32))
    distance = cv2.pointPolygonTest(hull, (float(point[0]), float(point[1])), True)
    return distance >= -HAND_HALF_WIDTH_FACES * face_width


def eye_touch(hand: np.ndarray, eyes, face_width: float, box=None) -> tuple[int, float, bool] | None:
    """(olho, distância do ponto da mão mais perto dele, mão cobrindo o centro do olho), ou None se nenhum olho."""
    points = hand[list(EYE_TOUCH_POINTS)]
    best = None
    for index, eye in enumerate(eyes):
        other = eyes[1 - index] if len(eyes) == 2 else None
        covers = hand_covers(hand, eye, face_width)
        if not covers and not points_on_eye(points, eye, other, face_width, box).any():
            continue
        distance = float(np.hypot(points[:, 0] - eye[0], points[:, 1] - eye[1]).min())
        if best is None or distance < best[1]:
            best = (index, distance, covers)
    return best


def nearest_eye(hand: np.ndarray, eyes, face_width: float, box=None) -> int | None:
    """Olho (0 direito, 1 esquerdo) com a mão nele; o mais próximo, se forem os dois."""
    touch = eye_touch(np.asarray(hand, dtype=np.float32), eyes, face_width, box)
    return None if touch is None else touch[0]


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


def covered_time(marks) -> float:
    """Maior trecho com o olho tapado: (t, tapado) em ordem; 3 medidas tapadas ou mais, sem buraco maior que 0,6 s."""
    best, start, last, count = 0.0, None, None, 0
    for t, covered in marks:
        if not covered:
            continue
        if last is None or t - last > COVER_GAP_S:
            start, count = t, 0
        last, count = t, count + 1
        if count >= COVER_MIN_SAMPLES:
            best = max(best, last - start)
    return best


@dataclass
class _Episode:
    start: float
    last: float
    face_width: float
    # (t, olho sem medida ou fechado, mão cobrindo o centro do olho) de cada medida com a mão no olho
    marks: list = field(default_factory=list)
    sides: list = field(default_factory=list)
    tracks: tuple = field(default_factory=lambda: tuple([] for _ in MOTION_GROUPS))  # (t, x, y) em relação ao olho

    def reversals(self) -> list:
        """Inversões do sinal com mais vai e vem (pontas, nós ou mão inteira)."""
        found = [reversal_times(track, self.face_width) for track in self.tracks]
        return max(found, key=lambda times: (repeated_motion(times), len(times)))

    def spread(self) -> float:
        """Quanto a mão mexe em cima do olho: maior desvio da posição, robusto (mediana dos desvios × 1,4826, que vale
        o desvio-padrão num ruído normal): a mão chegando ou saindo, uma medida ou duas, não conta como mexer."""
        best = 0.0
        for track in self.tracks:
            if len(track) < 3:
                continue
            points = np.array([(x, y) for _, x, y in track], dtype=np.float64)
            deviation = np.median(np.abs(points - np.median(points, axis=0)), axis=0) * 1.4826
            best = max(best, float(np.hypot(deviation[0], deviation[1])))
        return best

    def covered(self) -> list:
        """(t, olho tapado): sem medida, fechado, ou com a mão cobrindo o centro dele e mexendo (esfregando)."""
        moving = self.spread() >= RUB_MIN_SPREAD_FACES * self.face_width
        return [(t, hidden or (covers and moving)) for t, hidden, covers in self.marks]

    @property
    def hidden(self) -> int:
        return sum(1 for _, covered in self.covered() if covered)


class FaceTouchTracker:
    """Junta as mãos no tempo, fecha os episódios e conta os gestos dos últimos 10 min."""

    def __init__(self):
        self.totals = {RUBBING: 0, HAND_ON_FACE: 0}
        self.episodes = deque(maxlen=EPISODE_HISTORY)  # cada episódio fechado, para comparar com anotação manual
        self._episode: _Episode | None = None
        self._done = deque()  # (fim, gesto)
        self._face = None  # (t, caixa, centros dos olhos) do último rosto visto
        self._eye_layout = None  # olhos em frações da caixa do rosto, do último quadro com os pontos dos olhos
        self._open = (deque(maxlen=OPEN_REFERENCE_FRAMES), deque(maxlen=OPEN_REFERENCE_FRAMES))  # EAR com o olho livre
        self._last_eye_touch = -math.inf
        self._last_event_at = {}
        self._pending = []

    def update(self, t: float, metrics, hands=None, observed_at: float | None = None,
               blocked: bool = False) -> FaceTouchAssessment:
        """hands: mãos livres (sem celular) de uma observação nova, ou None se não chegou observação neste quadro."""
        self._remember_face(t, metrics)
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

    def close(self) -> None:
        """Fecha o episódio em andamento (fim do vídeo): ele entra na contagem e em episodes."""
        if self._episode is not None:
            self._finish(self._episode)
            self._episode = None

    def _remember_face(self, t: float, metrics) -> None:
        box = getattr(metrics, "face_box", None) if metrics.face_found else None
        if box is None:
            return
        width, height = box[2] - box[0], box[3] - box[1]
        eyes = eye_centers(metrics)
        if width > 0 and height > 0:
            if eyes is not None:
                self._eye_layout = [((float(eye[0]) - box[0]) / width, (float(eye[1]) - box[1]) / height) for eye in eyes]
            elif self._eye_layout is not None:  # caixa sem os pontos dos olhos: olhos na posição relativa guardada
                eyes = [np.array((box[0] + fx * width, box[1] + fy * height), dtype=np.float32)
                        for fx, fy in self._eye_layout]
        self._face = (t, box, eyes)
        if self._episode is None and t - self._last_eye_touch > EYE_COVER_S:
            for side, name in enumerate(EYE_OPENNESS_FIELDS):
                value = getattr(metrics, name, None)
                if value is not None:
                    self._open[side].append(float(value))

    def _eye_hidden(self, metrics, side: int) -> bool:
        """Rosto perdido, ou olho sem medida ou fechado em relação ao aberto da própria pessoa (EAR medido antes)."""
        if not metrics.face_found:
            return True
        name = EYE_OPENNESS_FIELDS[side]
        if not hasattr(metrics, name):
            return False  # fonte sem abertura por olho: não dá para saber
        value, reference = getattr(metrics, name), self._open[side]
        if len(reference) < OPEN_REFERENCE_MIN:
            return False  # sem o aberto da pessoa (YuNet não mede EAR por olho, ou começo da viagem): não dá para saber
        return value is None or value < EYE_CLOSED_FRACTION * float(np.median(reference))

    def _observe(self, observed_at: float, now: float, metrics, hands) -> None:
        if self._face is None or (now - self._face[0] > FACE_MEMORY_S and self._episode is None):
            return
        _, box, eyes = self._face
        width = box[2] - box[0]
        if width <= 0:
            return
        contact, near = False, None
        for hand in hands:
            hand = np.asarray(hand, dtype=np.float32)
            if hand.ndim != 2 or len(hand) < 21:
                continue
            hand = hand[:, :2]
            touch = eye_touch(hand, eyes, width, box) if eyes is not None else None
            if touch is not None and (near is None or touch[1] < near[0][1]):
                near = (touch, hand)
            contact = contact or touch is not None or touches_upper_face(hand, box)
        if not contact:
            return
        episode = self._episode
        if episode is None:
            episode = self._episode = _Episode(start=observed_at, last=observed_at, face_width=width)
        episode.last = observed_at
        if near is not None:
            (side, _, covers), hand = near
            eye = np.asarray(eyes[side], dtype=np.float32)
            for track, group in zip(episode.tracks, MOTION_GROUPS):
                x, y = hand[list(group)].mean(axis=0) - eye
                track.append((observed_at, float(x), float(y)))
            episode.marks.append((observed_at, self._eye_hidden(metrics, side), covers))
            episode.sides.append(side)
            self._last_eye_touch = now

    def _classify(self, episode: _Episode) -> str | None:
        near_s = episode.marks[-1][0] - episode.marks[0][0] if len(episode.marks) >= 2 else 0.0
        if RUB_MIN_S <= near_s <= RUB_MAX_S and (covered_time(episode.covered()) >= COVER_MIN_S
                                                 or repeated_motion(episode.reversals())):
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
        described = {}
        if episode.marks:
            described["lado"] = SIDES[max(set(episode.sides), key=episode.sides.count)]
            described["fracao_olho_encoberto"] = round(episode.hidden / len(episode.marks), 2)
        if gesture == RUBBING:
            described["inversoes"] = len(episode.reversals())
        # As chaves do episódio são as colunas fixas do _gestos.csv (ferramentas/analisar_video.py): nada novo aqui.
        self.episodes.append(dict(inicio_s=round(episode.start, 2), fim_s=round(end, 2), gesto=gesture, **described))
        if gesture == RUBBING:
            described["olho_tapado_s"] = round(covered_time(episode.covered()), 2)  # só no evento
        last = self._last_event_at.get(gesture)
        if last is not None and end - last < EVENT_COOLDOWN_S:
            return
        self._last_event_at[gesture] = end
        duration = end - episode.start
        details = {"duracao_s": round(duration, 1),
                   WINDOW_KEYS[gesture]: sum(1 for t, g in self._done if g == gesture and t >= end - COUNT_WINDOW_S),
                   **described}
        self._pending.append(DetectedEvent(gesture, 1, round(duration, 2), details))
