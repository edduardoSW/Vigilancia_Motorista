"""Uso de celular pelo motorista: segurando, no ouvido ou olhando para o aparelho.

Modelos (Apache 2.0), no mesmo MediaPipe que já mede o rosto:
- EfficientDet-Lite0, treinado no COCO 2017, classe "cell phone": acha o aparelho num recorte ao redor do motorista.
- Hand Landmarker: 21 pontos por mão, para saber se a mão está no aparelho ou perto da orelha.

Base das regras (limiares iniciais, a validar com vídeos da frota):
- Segurar ou manusear celular dirigindo é infração gravíssima (CTB, art. 252, parágrafo único, incluído pela
  Lei 13.281/2016).
- Olhadas para longe da via de até 2 s (diretrizes visual-manuais da NHTSA, 2013).
- Discar, digitar e navegar com o celular na mão multiplicaram o risco de colisão de 2,7 a 12,2 vezes no estudo
  naturalístico SHRP 2 (Dingus et al., 2016, PNAS).

Celular no ouvido (spec 028, pedido do Matheus em 19/10/2026: "a pessoa estava com a mão no ouvido e o script detectava
como celular, isso não pode acontecer"). Na orelha, celular só existe com prova de objeto que não é a mão: o detector
propõe e três verificações independentes confirmam. Na dúvida, "sem celular", mesmo que algum celular real demore mais.
1. Pele: caixa com 60% ou mais dos pixels na cor da pele da própria pessoa (referência nas bochechas) é a mão.
2. Mão: com a mão encostada, pelo menos 30% da caixa fica fora do contorno dela (envoltória dos 21 pontos, dilatada).
3. Forma: confiança maior na orelha (0,55) e caixa com proporção e tamanho de aparelho.
"No ouvido" exige a maioria das detecções dos últimos 2 s aprovadas. O model card do Hand Landmarker põe a mão segurando
objetos fora do escopo: os pontos da mão podem falhar justo com o celular real, por isso a mão sozinha não prova nada.

Os modelos rodam numa thread separada, algumas vezes por segundo, para não derrubar o fps da medida do rosto. As
verificações 1 e 2 rodam na mesma thread, logo depois do detector, com o quadro em memória (PhoneVerifier); a decisão
(PhoneMonitor.observe e _assess) só usa os números. Nenhuma imagem é guardada: só o estado, a duração, a confiança e os
números das verificações.
"""
from __future__ import annotations

import logging
import math
import platform
import statistics
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from vision.drowsiness import DetectedEvent
from vision.face_touch import FaceTouchAssessment, FaceTouchTracker

logger = logging.getLogger("drivesafe.phone")

MODELS_DIR = Path(__file__).resolve().parent / "models"
PHONE_MODEL_INT8 = MODELS_DIR / "efficientdet_lite0_int8.tflite"
PHONE_MODEL_FLOAT16 = MODELS_DIR / "efficientdet_lite0_float16.tflite"
HAND_MODEL = MODELS_DIR / "hand_landmarker.task"
PHONE_LABEL = "cell phone"

DETECT_EVERY_S = 0.25
PHONE_MIN_SCORE = 0.35
# Recorte do motorista, em larguras e alturas do rosto: pega orelhas, mãos perto do rosto e o peito.
# No recorte o celular ficou maior para o modelo (0,60 → 0,77 de confiança numa foto de teste).
ROI_HALF_WIDTH_FACES = 1.6
ROI_ABOVE_FACES = 0.6
ROI_BELOW_FACES = 2.4
EAR_RADIUS_FACES = 0.45
# Celular no ouvido: centro do aparelho numa elipse em volta da orelha, mais larga que alta. Um raio de 0,7 rosto
# pegava o aparelho na mão na altura do queixo, do lado do rosto.
PHONE_EAR_DX_FACES = 0.7
PHONE_EAR_DY_FACES = 0.5
HAND_ON_PHONE_MARGIN = 0.25
HAND_KEY_POINTS = (0, 4, 5, 8, 9, 12, 13, 16, 17, 20)  # punho, pontas dos dedos e articulações da base
MIN_HAND_POINTS = 3
# Evidência vale por 1,5 s. Celular só conta com pelo menos 2 detecções em 2 s: um objeto parecido num quadro não basta.
EVIDENCE_S = 1.5
CONFIRM_WINDOW_S = 2.0
CONFIRM_HITS = 2
# Mão na orelha só mantém "no ouvido" se o aparelho foi APROVADO na orelha (verificações abaixo) há pouco: no máximo
# 5 s depois da última aprovação, já contando a tolerância de falha de STATE_GAP_S (spec 028, decisão 5 e CEL-11).
# Mão vazia na orelha não conta, nem com a boca mexendo: dava falso positivo (teste de 10/09).
PHONE_EAR_MEMORY_S = 5.0
# O model card do Hand Landmarker põe fora do escopo a mão segurando objetos: os pontos da mão podem falhar justo
# com o celular na mão. Por isso o aparelho se mexendo também conta. Celular preso num suporte fica parado em
# relação à câmera (os dois estão presos ao veículo) e não conta. Hipótese: 8% da largura do rosto em 2 s.
PHONE_MOVE_FACES = 0.08
STATE_GAP_S = 1.0
LOOK_DOWN_PITCH_DEG = 15.0
LOOK_DOWN_GAZE = 0.25
REFERENCE_S = 30.0
REFERENCE_STEP_S = 0.5

LOOKING_ALERT_S = 2.0
EAR_ALERT_S = 3.0
HAND_ALERT_S = 3.0
EVENT_COOLDOWN_S = 120.0
ALARM_COOLDOWN_S = 30.0

# --- Spec 028: verificações do aparelho na orelha. Limiares iniciais, a calibrar com as gravações da equipe (CEL-03,
# ferramentas/avaliar_celular.py). O detector do COCO chamava a própria mão de celular perto do rosto (testes de 14/09
# e 19/10): subir só o número de detecções (spec 009) não bastou, a 4 detecções por segundo a mão parada passava.
# Decisão 3: exigência maior perto da orelha (fora dela continua PHONE_MIN_SCORE).
EAR_MIN_SCORE = 0.55
EAR_ASPECT_RANGE = (1.3, 3.2)  # lado maior ÷ lado menor da caixa
EAR_LONG_SIDE_FACES = (0.35, 1.6)  # lado maior, em larguras do rosto
# Complemento da decisão 3 (CEL-08): uma caixa do tamanho do rosto (1,0 × 1,3 rosto) passa nas duas regras acima. O
# aparelho tem ~7 cm de largura e o rosto ~14 cm: o lado menor fica perto de 0,5 rosto. Com 0,8 sobra folga para o
# aparelho inclinado (15 × 7 cm inclinado 30° dá uma caixa de 0,66 rosto no lado menor). Hipótese, calibrar.
EAR_MAX_SHORT_SIDE_FACES = 0.8
# Decisão 1: caixa com 60% ou mais dos pixels na cor da pele da pessoa é a mão.
SKIN_MAX_FRACTION = 0.60
# Decisão 2: com a mão encostada, pelo menos 30% da caixa fora do contorno da mão. Os 21 pontos ficam nas juntas e a
# pele passa deles (meia largura de dedo ≈ 0,06 rosto): o contorno é dilatado em 10% da largura do rosto.
OUTSIDE_HAND_MIN_FRACTION = 0.30
HAND_HULL_DILATION_FACES = 0.10
# Decisão 4: "no ouvido" com 60% das detecções dos últimos 2 s aprovadas, e pelo menos 3 aprovadas.
EAR_MAJORITY = 0.60
EAR_CONFIRM_HITS = 3
# Referência de pele (decisão 1): mediana de quadrados nas bochechas, em YCrCb, renovada por média exponencial.
CHEEK_LANDMARKS = ((117, 118, 101, 36, 205, 187, 123), (346, 347, 330, 266, 425, 411, 352))  # os de vision/cardio.py
CHEEK_IN_FACE_BOX = ((0.28, 0.62), (0.72, 0.62))  # modo YuNet (sem pontos): posição fixa na caixa do rosto
CHEEK_PATCH_FACES = 0.12  # lado do quadrado de amostra
SKIN_REFERENCE_TAU_S = 5.0  # acompanha a luz mudando devagar (30% em 30 s fica a ~5% da cor atual)
SKIN_REFERENCE_MAX_AGE_S = 10.0  # sem bochecha visível por mais tempo, a referência caduca
# Pele plausível em YCrCb: a faixa de Chai e Ngan (1999, IEEE TCSVT 9(4):551-564; Cr 133-173, Cb 77-127), com folga.
# Fora dela (câmera infravermelha sem cor, escuro, bochecha tapada) não há referência e a verificação 1 fica de fora;
# seguram a 2 e a 3 (riscos da spec 028).
SKIN_PLAUSIBLE_Y_MIN = 45.0
SKIN_PLAUSIBLE_CR = (133.0, 180.0)
SKIN_PLAUSIBLE_CB = (70.0, 130.0)
SKIN_MIN_CHROMA = 12.0  # distância mínima ao cinza (Cr 128, Cb 128)
# Pixel na cor da pele: croma perto da referência e luminância na faixa dela (mão na sombra ou no sol). A tolerância do
# croma é uma fração da distância da referência ao cinza: preto, cinza e branco nunca contam como pele.
SKIN_CHROMA_TOLERANCE = (0.55, 8.0, 18.0)  # fração, mínimo e máximo
SKIN_LUMA_RANGE = (0.45, 1.9)
SKIN_SAMPLE_FULL_PIXELS = 1600  # caixa maior que isso (40 × 40 px) é amostrada 1 pixel a cada 2
# Números das verificações no evento e no _quadros.csv (CEL-13). Nunca imagem.
CHECK_KEYS = ("fracao_pele", "fracao_fora_da_mao", "confianca_orelha", "aprovados_2s", "deteccoes_2s")


def default_phone_model() -> Path:
    """int8 é mais rápido em ARM (Raspberry Pi, Apple Silicon); em x86 o float16 foi mais rápido (73 x 106 ms)."""
    return PHONE_MODEL_INT8 if platform.machine().lower() in ("aarch64", "arm64", "armv8l") else PHONE_MODEL_FLOAT16


@dataclass
class PhoneCheck:
    """Verificações 1 e 2 da spec 028 para uma caixa. None = não deu para medir."""
    skin_fraction: float | None = None  # fração da caixa na cor da pele da pessoa (None: sem referência de pele)
    outside_hand_fraction: float | None = None  # fração da caixa fora do contorno das mãos (None: nenhuma mão)


@dataclass
class PhoneObservation:
    timestamp: float
    phones: list  # (x1, y1, x2, y2, confiança) em pixels do quadro
    hands: list  # arrays (21, 2) em pixels do quadro
    checks: list | None = None  # um PhoneCheck por caixa, na ordem de phones (spec 028); None = ainda não medido


@dataclass
class PhoneAssessment:
    state: str = "sem_celular"  # sem_celular, celular_na_mao, celular_no_ouvido, olhando_celular
    duration: float = 0.0
    risk_level: int = 0  # contribuição para a fusão: 0 a 2
    reasons: list = field(default_factory=list)
    alarm: bool = False
    events: list = field(default_factory=list)
    phone_score: float | None = None
    hands: int = 0
    boxes: list = field(default_factory=list)  # caixas de celular recentes, para desenhar na janela
    face_touch: FaceTouchAssessment | None = None  # olhos esfregados e mão no rosto (vision/face_touch.py)
    # Spec 028: números das verificações na orelha (chaves de CHECK_KEYS; None sem candidato recente na orelha) e as
    # caixas recusadas na orelha (a mão chamada de celular), para a tela poder mostrá-las de outro jeito ou escondê-las.
    checks: dict = field(default_factory=dict)
    rejected_boxes: list = field(default_factory=list)


@dataclass
class FaceSnapshot:
    """O que as verificações precisam do rosto, copiado no loop principal (a detecção roda em outra thread)."""
    box: tuple  # (x1, y1, x2, y2)
    cheeks: list  # quadrados (x1, y1, x2, y2) de amostra da pele nas bochechas

    @property
    def width(self) -> float:
        return self.box[2] - self.box[0]


def check_columns(assessment) -> dict:
    """Números das verificações para o _quadros.csv do analisar_video.py (colunas celular_*, avaliar_celular.py)."""
    checks = getattr(assessment, "checks", None)
    if checks is None:
        return {}
    return {f"celular_{key}": checks.get(key) for key in CHECK_KEYS}


def driver_roi(face_box, frame_shape) -> tuple[int, int, int, int]:
    height, width = frame_shape[:2]
    if face_box is None:
        return 0, 0, width, height
    x1, y1, x2, y2 = face_box
    face_width, face_height, center = x2 - x1, y2 - y1, (x1 + x2) / 2.0
    return (max(0, int(center - ROI_HALF_WIDTH_FACES * face_width)), max(0, int(y1 - ROI_ABOVE_FACES * face_height)),
            min(width, int(center + ROI_HALF_WIDTH_FACES * face_width)), min(height, int(y2 + ROI_BELOW_FACES * face_height)))


def hand_touches_phone(hand: np.ndarray, phone) -> bool:
    x1, y1, x2, y2 = phone[:4]
    margin_x, margin_y = (x2 - x1) * HAND_ON_PHONE_MARGIN, (y2 - y1) * HAND_ON_PHONE_MARGIN
    inside = ((hand[:, 0] >= x1 - margin_x) & (hand[:, 0] <= x2 + margin_x)
              & (hand[:, 1] >= y1 - margin_y) & (hand[:, 1] <= y2 + margin_y))
    return int(inside.sum()) >= MIN_HAND_POINTS


def hand_near_ear(hand: np.ndarray, ears, face_width: float) -> bool:
    key = hand[list(HAND_KEY_POINTS)]
    radius = EAR_RADIUS_FACES * face_width
    return any(int((np.hypot(key[:, 0] - ear[0], key[:, 1] - ear[1]) <= radius).sum()) >= MIN_HAND_POINTS for ear in ears)


def phone_near_ear(phone, ears, face_width: float) -> bool:
    center_x, center_y = (phone[0] + phone[2]) / 2.0, (phone[1] + phone[3]) / 2.0
    return any(((center_x - ear[0]) / (PHONE_EAR_DX_FACES * face_width)) ** 2
               + ((center_y - ear[1]) / (PHONE_EAR_DY_FACES * face_width)) ** 2 <= 1.0 for ear in ears)


def face_snapshot(metrics) -> FaceSnapshot | None:
    """Caixa do rosto e quadrados das bochechas: pelos 478 pontos (MediaPipe) ou por posição fixa na caixa (YuNet)."""
    box = getattr(metrics, "face_box", None) if getattr(metrics, "face_found", False) else None
    if box is None or box[2] <= box[0] or box[3] <= box[1]:
        return None
    width, height = box[2] - box[0], box[3] - box[1]
    landmarks = getattr(metrics, "landmarks", None)
    if landmarks is not None and len(landmarks) > max(max(indices) for indices in CHEEK_LANDMARKS):
        points = np.asarray(landmarks, dtype=np.float32)
        centers = [points[list(indices), :2].mean(axis=0) for indices in CHEEK_LANDMARKS]
    else:
        centers = [(box[0] + fx * width, box[1] + fy * height) for fx, fy in CHEEK_IN_FACE_BOX]
    half = CHEEK_PATCH_FACES * width / 2.0
    cheeks = [(float(cx) - half, float(cy) - half, float(cx) + half, float(cy) + half) for cx, cy in centers]
    return FaceSnapshot(tuple(float(value) for value in box[:4]), cheeks)


def _crop(frame: np.ndarray, box) -> np.ndarray | None:
    height, width = frame.shape[:2]
    x1, y1 = max(0, int(math.floor(box[0]))), max(0, int(math.floor(box[1])))
    x2, y2 = min(width, int(math.ceil(box[2]))), min(height, int(math.ceil(box[3])))
    if x2 - x1 < 2 or y2 - y1 < 2:
        return None
    return frame[y1:y2, x1:x2]


def _overlaps(a, b) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _hand_box(hand: np.ndarray, radius: float) -> tuple:
    return (float(hand[:, 0].min()) - radius, float(hand[:, 1].min()) - radius,
            float(hand[:, 0].max()) + radius, float(hand[:, 1].max()) + radius)


def plausible_skin(ycrcb) -> bool:
    y, cr, cb = (float(value) for value in ycrcb)
    return (y >= SKIN_PLAUSIBLE_Y_MIN and SKIN_PLAUSIBLE_CR[0] <= cr <= SKIN_PLAUSIBLE_CR[1]
            and SKIN_PLAUSIBLE_CB[0] <= cb <= SKIN_PLAUSIBLE_CB[1] and math.hypot(cr - 128.0, cb - 128.0) >= SKIN_MIN_CHROMA)


def skin_fraction(frame: np.ndarray, box, reference) -> float | None:
    """Fração dos pixels da caixa na cor da pele da referência (Y, Cr, Cb)."""
    crop = _crop(frame, box)
    if crop is None:
        return None
    if crop.shape[0] * crop.shape[1] > SKIN_SAMPLE_FULL_PIXELS:
        crop = crop[::2, ::2]  # é uma fração: 1 pixel a cada 2 em cada eixo basta e custa 4 vezes menos (CEL-14)
    ycrcb = cv2.cvtColor(crop, cv2.COLOR_BGR2YCrCb).astype(np.float32)
    ref_y, ref_cr, ref_cb = (float(value) for value in reference)
    factor, low, high = SKIN_CHROMA_TOLERANCE
    tolerance = min(high, max(low, factor * math.hypot(ref_cr - 128.0, ref_cb - 128.0)))
    chroma = (ycrcb[..., 1] - ref_cr) ** 2 + (ycrcb[..., 2] - ref_cb) ** 2 <= tolerance * tolerance
    luma = (ycrcb[..., 0] >= SKIN_LUMA_RANGE[0] * ref_y) & (ycrcb[..., 0] <= SKIN_LUMA_RANGE[1] * ref_y)
    return float(np.count_nonzero(chroma & luma)) / chroma.size


def outside_hand_fraction(box, hands, radius: float) -> float | None:
    """Fração da caixa fora do contorno das mãos (envoltória convexa dos pontos, dilatada em `radius` pixels)."""
    if hands is None or len(hands) == 0:
        return None
    x1, y1 = int(math.floor(box[0])), int(math.floor(box[1]))
    x2, y2 = int(math.ceil(box[2])), int(math.ceil(box[3]))
    if x2 - x1 < 1 or y2 - y1 < 1:
        return None
    mask = np.zeros((y2 - y1, x2 - x1), dtype=np.uint8)
    reach = max(0, int(math.ceil(radius)))
    for hand in hands:
        points = np.asarray(hand, dtype=np.float32)[:, :2]
        if (points[:, 0].max() + reach < x1 or points[:, 0].min() - reach > x2
                or points[:, 1].max() + reach < y1 or points[:, 1].min() - reach > y2):
            continue  # mão longe da caixa
        hull = cv2.convexHull(np.round(points - np.array([x1, y1], dtype=np.float32)).astype(np.int32))
        cv2.fillConvexPoly(mask, hull, 1)
        if reach > 0:  # borda grossa com pontas redondas = envoltória dilatada
            cv2.polylines(mask, [hull], True, 1, thickness=2 * reach + 1)
    return 1.0 - float(np.count_nonzero(mask)) / mask.size


def ear_candidate_ok(phone, check: PhoneCheck | None, face_width: float) -> bool:
    """Verificações 1 a 3 da spec 028 para uma caixa perto da orelha. Sem os números (falha ao medir): não conta."""
    if check is None or phone[4] < EAR_MIN_SCORE or not face_width:
        return False
    width, height = phone[2] - phone[0], phone[3] - phone[1]
    long_side, short_side = max(width, height), min(width, height)
    if short_side <= 0 or not EAR_ASPECT_RANGE[0] <= long_side / short_side <= EAR_ASPECT_RANGE[1]:
        return False
    if not EAR_LONG_SIDE_FACES[0] <= long_side / face_width <= EAR_LONG_SIDE_FACES[1]:
        return False
    if short_side / face_width > EAR_MAX_SHORT_SIDE_FACES:
        return False
    if check.skin_fraction is not None and check.skin_fraction >= SKIN_MAX_FRACTION:
        return False
    return check.outside_hand_fraction is None or check.outside_hand_fraction >= OUTSIDE_HAND_MIN_FRACTION


class SkinReference:
    """Cor da pele da própria pessoa (Y, Cr, Cb): mediana de quadrados nas bochechas, renovada aos poucos."""

    def __init__(self):
        self.value: np.ndarray | None = None
        self.updated_at = -math.inf

    def update(self, frame: np.ndarray, patches, blockers, t: float) -> None:
        samples = []
        for patch in patches:
            if any(_overlaps(patch, other) for other in blockers):
                continue  # bochecha tapada pela mão ou pelo aparelho: a amostra seria deles
            crop = _crop(frame, patch)
            if crop is None:
                continue
            median = np.median(cv2.cvtColor(crop, cv2.COLOR_BGR2YCrCb).reshape(-1, 3), axis=0)
            if plausible_skin(median):
                samples.append(median.astype(np.float64))
        if not samples:
            return
        sample = np.mean(samples, axis=0)
        if self.value is None or t - self.updated_at > SKIN_REFERENCE_MAX_AGE_S:
            self.value = sample
        else:
            alpha = 1.0 - math.exp(-max(0.0, t - self.updated_at) / SKIN_REFERENCE_TAU_S)
            self.value = self.value + alpha * (sample - self.value)
        self.updated_at = t

    def current(self, t: float) -> np.ndarray | None:
        if self.value is None or t - self.updated_at > SKIN_REFERENCE_MAX_AGE_S:
            return None
        return self.value


class PhoneVerifier:
    """Verificações 1 (pele) e 2 (fora da mão) da spec 028 num quadro em memória, para cada caixa do detector.
    Roda na thread da detecção, logo depois do detector; com frame=None mede só o contorno da mão."""

    def __init__(self):
        self.skin = SkinReference()
        self._face_width: float | None = None

    def measure(self, frame, phones, hands, face: FaceSnapshot | None, timestamp: float) -> list[PhoneCheck]:
        if face is not None:
            self._face_width = face.width
        radius = HAND_HULL_DILATION_FACES * self._face_width if self._face_width else 0.0
        reference = None
        if frame is not None:
            if face is not None:
                blockers = [phone[:4] for phone in phones] + [_hand_box(np.asarray(hand), radius) for hand in hands]
                self.skin.update(frame, face.cheeks, blockers, timestamp)
            reference = self.skin.current(timestamp)
        return [PhoneCheck(skin_fraction=None if reference is None else skin_fraction(frame, phone, reference),
                           outside_hand_fraction=outside_hand_fraction(phone, hands, radius)) for phone in phones]


def _rounded(value, digits: int = 2):
    return None if value is None else round(float(value), digits)


class PhoneDetector:
    """Roda os modelos num quadro e devolve caixas de celular e pontos das mãos.
    As verificações da spec 028 (PhoneVerifier) rodam depois, no PhoneMonitor, para valer com qualquer detector."""

    def __init__(self, phone_model: Path | None = None, hand_model: Path = HAND_MODEL, use_hands: bool = True):
        try:
            import mediapipe as mp
            from mediapipe.tasks import python as mp_python
            from mediapipe.tasks.python import vision as mp_vision
        except ImportError as exc:
            raise RuntimeError(f"MediaPipe não está instalado ({exc})") from exc
        phone_model = Path(phone_model or default_phone_model())
        for path in (phone_model, Path(hand_model)) if use_hands else (phone_model,):
            if not path.is_file():
                raise RuntimeError(f"Modelo de detecção de celular não encontrado em {path}.")

        self._mp = mp
        self._objects = mp_vision.ObjectDetector.create_from_options(mp_vision.ObjectDetectorOptions(
            base_options=mp_python.BaseOptions(model_asset_path=str(phone_model)),
            running_mode=mp_vision.RunningMode.IMAGE,
            score_threshold=PHONE_MIN_SCORE,
            category_allowlist=[PHONE_LABEL],
            max_results=3,
        ))
        self._hands = None
        if use_hands:
            self._hands = mp_vision.HandLandmarker.create_from_options(mp_vision.HandLandmarkerOptions(
                base_options=mp_python.BaseOptions(model_asset_path=str(hand_model)),
                running_mode=mp_vision.RunningMode.VIDEO,
                num_hands=2,
            ))
        self._last_ms = -1
        logger.info("Detecção de celular carregada (%s%s).", phone_model.name, " + mãos" if use_hands else "")

    def detect(self, frame_bgr: np.ndarray, timestamp: float, face_box=None) -> PhoneObservation:
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        x1, y1, x2, y2 = driver_roi(face_box, frame_bgr.shape)
        phones = []
        if x2 - x1 >= 32 and y2 - y1 >= 32:
            crop = np.ascontiguousarray(rgb[y1:y2, x1:x2])
            result = self._objects.detect(self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=crop))
            for detection in result.detections:
                box = detection.bounding_box
                phones.append((x1 + box.origin_x, y1 + box.origin_y, x1 + box.origin_x + box.width,
                               y1 + box.origin_y + box.height, float(detection.categories[0].score)))
        hands = []
        if self._hands is not None:
            self._last_ms = max(int(timestamp * 1000), self._last_ms + 1)
            result = self._hands.detect_for_video(self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb),
                                                  self._last_ms)
            height, width = frame_bgr.shape[:2]
            for landmarks in result.hand_landmarks:
                hands.append(np.array([(p.x * width, p.y * height) for p in landmarks], dtype=np.float32))
        return PhoneObservation(timestamp, phones, hands)

    def close(self) -> None:
        self._objects.close()
        if self._hands is not None:
            self._hands.close()


class PhoneMonitor:
    """Junta as detecções no tempo e decide o estado. background=False roda os modelos no próprio quadro (vídeos)."""

    def __init__(self, detector, background: bool = True, every_s: float = DETECT_EVERY_S):
        self.detector = detector
        self.background = background
        self.every_s = every_s
        self.last_observation: PhoneObservation | None = None
        self.verifier = PhoneVerifier()
        self.verify_ms: float | None = None  # custo da última verificação (CEL-14)
        self._next_detection = -math.inf
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._job = None
        self._result = None
        self._busy = False
        self._failures = 0
        self._check_failures = 0
        self._ear_checks = deque()  # (momento, aprovado) de cada detecção com rosto: base da maioria de 2 s
        self._away_hits = deque()  # momentos com celular longe da orelha (ou sem rosto para saber)
        self._phone_centers = deque()  # (t, x, y, escala) de cada celular detectado longe da orelha
        self._last = dict.fromkeys(("phone", "hand_on_phone", "hand_ear", "phone_ear", "phone_away", "ear_confirmed",
                                    "ear_approved"), -math.inf)
        self._ear_numbers = None  # (momento, números do melhor candidato na orelha)
        self._rejected = (-math.inf, [])  # (momento, caixas recusadas na orelha)
        self._state_since = {}
        self._state_last = {}
        self._pitch_reference = deque()
        self._gaze_reference = deque()
        self._next_reference = -math.inf
        self._state = "sem_celular"
        self._episode_since = self._episode_last = None
        self._looking_since = self._looking_last = None
        self._last_event_at = {}
        self._last_alarm_at = -math.inf
        # Os mesmos pontos das mãos servem para os gestos de sono: nenhum modelo a mais.
        self.face_touch = FaceTouchTracker()
        self._touch_hands = None
        self._thread = None
        if background:
            self._thread = threading.Thread(target=self._worker, name="drivesafe-celular", daemon=True)
            self._thread.start()

    def update(self, metrics, frame=None, moving: bool = True) -> PhoneAssessment:
        t = metrics.timestamp
        if frame is not None and t >= self._next_detection:
            face = face_snapshot(metrics)
            if self.background:
                # GES-12: com a detecção anterior ainda rodando, o quadro é recusado e o próximo tenta de novo. Antes o
                # intervalo avançava mesmo assim e as mãos caíam para ~2 por segundo (olhos esfregados se perdiam).
                if self._submit(frame, t, face) is not False:
                    self._next_detection = t + self.every_s
            else:
                self._next_detection = t + self.every_s
                self.observe(self._run(frame, t, face), metrics)
        if self.background:
            with self._lock:
                observation, self._result = self._result, None
            self.observe(observation, metrics)
        self._track_face(t, metrics)
        return self._assess(t, metrics, moving)

    def observe(self, observation: PhoneObservation | None, metrics) -> None:
        if observation is None:
            return
        self.last_observation = observation
        t = observation.timestamp
        checks = getattr(observation, "checks", None)
        if checks is None or len(checks) != len(observation.phones):
            # Sem os números (quem chamou não tinha o quadro): mede só o contorno da mão. Se falhar, na orelha não conta.
            try:
                checks = self.verifier.measure(None, observation.phones, observation.hands, face_snapshot(metrics), t)
            except Exception:
                checks = [None] * len(observation.phones)
            observation.checks = checks
        phones = [(phone, check) for phone, check in zip(observation.phones, checks) if phone[4] >= PHONE_MIN_SCORE]
        if phones:
            self._last["phone"] = t
        box = getattr(metrics, "face_box", None) if metrics.face_found else None
        ears = getattr(metrics, "ear_points", None) if box is not None else None
        face_width = box[2] - box[0] if box is not None else None
        at_ear = away = False
        candidates = []  # (aprovado, confiança, números, caixa) de cada candidato na orelha
        for phone, check in phones:
            if ears is not None and phone_near_ear(phone, ears, face_width):
                at_ear = True
                candidates.append((ear_candidate_ok(phone, check, face_width), phone[4], check, phone[:4]))
                continue
            # Longe da orelha (ou sem rosto para saber): é o que confirma o aparelho na mão e o movimento dele.
            away = True
            self._phone_centers.append((t, (phone[0] + phone[2]) / 2.0, (phone[1] + phone[3]) / 2.0,
                                        face_width or (phone[2] - phone[0])))
            if any(hand_touches_phone(hand, phone) for hand in observation.hands):
                self._last["hand_on_phone"] = t
        if ears is not None:
            approved = any(candidate[0] for candidate in candidates)
            self._ear_checks.append((t, approved))
            if approved:
                self._last["ear_approved"] = t
            if candidates:
                _, score, check, _ = max(candidates, key=lambda candidate: (candidate[0], candidate[1]))
                self._ear_numbers = (t, {"fracao_pele": _rounded(getattr(check, "skin_fraction", None)),
                                         "fracao_fora_da_mao": _rounded(getattr(check, "outside_hand_fraction", None)),
                                         "confianca_orelha": _rounded(score)})
            self._rejected = (t, [candidate[3] for candidate in candidates if not candidate[0]])
        if at_ear:
            self._last["phone_ear"] = t
        if away:
            self._away_hits.append(t)
            if ears is not None:
                self._last["phone_away"] = t
        if ears is not None and any(hand_near_ear(hand, ears, face_width) for hand in observation.hands):
            self._last["hand_ear"] = t
        # Mão segurando o celular não é gesto de sono. GES-13: caixa que é a própria mão (na cor da pele da pessoa,
        # spec 028) não tira a mão dos gestos, senão esfregar o olho virava "celular na mão". Só a cor decide aqui: um
        # celular de verdade segurado perto do olho também fica quase todo dentro do contorno da mão.
        def pode_ser_aparelho(check) -> bool:
            pele = getattr(check, "skin_fraction", None) if check is not None else None
            return not (pele is not None and pele >= SKIN_MAX_FRACTION)

        aparelhos = [phone for phone, check in phones if pode_ser_aparelho(check)]
        self._touch_hands = (t, [hand for hand in observation.hands
                                 if not any(hand_touches_phone(hand, phone) for phone in aparelhos)])

    def close(self) -> None:
        self.face_touch.close()
        self._stop.set()
        self._wake.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        self.detector.close()

    def _assess(self, t: float, metrics, moving: bool) -> PhoneAssessment:
        while self._away_hits and self._away_hits[0] < t - CONFIRM_WINDOW_S:
            self._away_hits.popleft()
        while self._ear_checks and self._ear_checks[0][0] < t - CONFIRM_WINDOW_S:
            self._ear_checks.popleft()
        while self._phone_centers and self._phone_centers[0][0] < t - CONFIRM_WINDOW_S:
            self._phone_centers.popleft()
        confirmed = len(self._away_hits) >= CONFIRM_HITS  # aparelho confirmado longe da orelha
        detections = len(self._ear_checks)
        approved = sum(1 for _, ok in self._ear_checks if ok)

        def seen(key, window=EVIDENCE_S):
            return t - self._last[key] <= window

        in_hand = confirmed and (seen("hand_on_phone") or self._phone_moving())
        # Aparelho à vista agora longe da orelha (na mão, no colo): outra mão encostada na orelha não vira "no ouvido".
        phone_away = seen("phone_away") and not seen("phone_ear")
        # "No ouvido" (spec 028): na orelha só vale caixa aprovada nas verificações 1 a 3. Direto: aprovada em pelo menos
        # 60% das detecções dos últimos 2 s, e em 3 ou mais (detecção solta não segura o estado); ou aprovada agora logo
        # depois de o aparelho ser confirmado longe da orelha (pegou e atendeu: já foi provado objeto, decisão 6).
        # Depois disso a mão na orelha segura o estado até PHONE_EAR_MEMORY_S depois da última aprovação (decisão 5).
        majority = approved >= EAR_CONFIRM_HITS and approved >= EAR_MAJORITY * detections
        ear_now = majority or (confirmed and seen("ear_approved"))
        if ear_now:
            self._last["ear_confirmed"] = t
        held = (seen("hand_ear") and not phone_away and seen("ear_confirmed", PHONE_EAR_MEMORY_S)
                and seen("ear_approved", PHONE_EAR_MEMORY_S - STATE_GAP_S))
        at_ear = ear_now or held
        looking = self._looking_down(metrics, in_hand)
        if looking and (in_hand or confirmed):
            state = "olhando_celular"
        elif at_ear:
            state = "celular_no_ouvido"
        elif in_hand:
            state = "celular_na_mao"
        else:
            state = "sem_celular"

        if state != "sem_celular":
            if self._episode_last is None or t - self._episode_last > STATE_GAP_S:
                self._episode_since = t
            self._episode_last, self._state = t, state
        elif self._episode_last is not None and t - self._episode_last <= STATE_GAP_S:
            state = self._state  # falha de um instante no meio do uso
        if state == "olhando_celular":
            if self._looking_last is None or t - self._looking_last > STATE_GAP_S:
                self._looking_since = t
            self._looking_last = t

        # Cada estado conta o próprio tempo. Antes o tempo do episódio inteiro valia para os dois: 3 s com o celular
        # na mão e um instante perto da orelha disparavam "celular no ouvido" junto com "celular na mão".
        ear_for = self._time_in("ouvido", state == "celular_no_ouvido", t)
        hand_for = self._time_in("mao", state in ("celular_na_mao", "olhando_celular"), t)
        looking_for = t - self._looking_since if state == "olhando_celular" else 0.0
        observation = self.last_observation
        recent = observation is not None and t - observation.timestamp <= EVIDENCE_S
        phones = observation.phones if recent else []
        numbers_at, numbers = self._ear_numbers or (-math.inf, {})
        checks = dict.fromkeys(CHECK_KEYS)
        checks.update(numbers if t - numbers_at <= EVIDENCE_S else {}, aprovados_2s=approved, deteccoes_2s=detections)
        rejected_at, rejected = self._rejected
        assessment = PhoneAssessment(state=state, duration=round(ear_for if state == "celular_no_ouvido" else hand_for, 2),
                                     phone_score=max(p[4] for p in phones) if phones else None,
                                     hands=len(observation.hands) if recent else 0, boxes=[p[:4] for p in phones],
                                     checks=checks, rejected_boxes=list(rejected) if t - rejected_at <= EVIDENCE_S else [])
        touch, self._touch_hands = self._touch_hands, None
        assessment.face_touch = self.face_touch.update(t, metrics, touch[1] if touch else None,
                                                       touch[0] if touch else None, blocked=state == "celular_no_ouvido")
        assessment.events.extend(assessment.face_touch.events)
        if not moving or state == "sem_celular":
            return assessment

        details = {"estado": state, "confianca_celular": None if assessment.phone_score is None else round(assessment.phone_score, 2),
                   "maos_detectadas": assessment.hands, "olhando_para_baixo": looking}
        # Números das verificações na orelha (CEL-13): os do último candidato visto na orelha, se recente.
        details.update(dict.fromkeys(CHECK_KEYS), **(numbers if t - numbers_at <= PHONE_EAR_MEMORY_S else {}))
        details.update(aprovados_2s=approved, deteccoes_2s=detections)
        if state == "olhando_celular" and looking_for >= LOOKING_ALERT_S:
            self._raise(t, assessment, 2, "olhos_no_celular", "olhando_celular", 4, looking_for, details, alarm=True)
        elif state == "celular_no_ouvido" and ear_for >= EAR_ALERT_S:
            self._raise(t, assessment, 2, "celular_no_ouvido", "celular_no_ouvido", 3, ear_for, details, alarm=True)
        elif state in ("celular_na_mao", "olhando_celular") and hand_for >= HAND_ALERT_S:
            self._raise(t, assessment, 1, "celular_na_mao", "celular_na_mao", 3, hand_for, details, alarm=False)
        return assessment

    def _time_in(self, key: str, active: bool, t: float) -> float:
        """Tempo seguido num estado, aceitando falhas de até STATE_GAP_S no meio."""
        if not active:
            return 0.0
        last = self._state_last.get(key)
        if last is None or t - last > STATE_GAP_S:
            self._state_since[key] = t
        self._state_last[key] = t
        return t - self._state_since[key]

    def _raise(self, t, assessment, risk, reason, alert_type, event_risk, duration, details, alarm) -> None:
        assessment.risk_level = risk
        assessment.reasons.append(reason)
        last = self._last_event_at.get(alert_type)
        if last is None or t - last >= EVENT_COOLDOWN_S:
            self._last_event_at[alert_type] = t
            assessment.events.append(DetectedEvent(alert_type, event_risk, round(duration, 2),
                                                   dict(details, duracao_s=round(duration, 1))))
        if alarm and t - self._last_alarm_at >= ALARM_COOLDOWN_S:
            self._last_alarm_at = t
            assessment.alarm = True

    def _looking_down(self, metrics, in_hand: bool) -> bool:
        if not metrics.face_found:
            # Rosto perdido com o celular na mão: na maioria das vezes é a cabeça baixa (hipótese, a validar).
            return in_hand
        pitch, gaze_y = metrics.pitch, getattr(metrics, "gaze_y", None)
        if pitch is not None and self._pitch_reference:
            if pitch - statistics.median(p for _, p in self._pitch_reference) >= LOOK_DOWN_PITCH_DEG:
                return True
        if gaze_y is not None and self._gaze_reference:
            return gaze_y - statistics.median(g for _, g in self._gaze_reference) >= LOOK_DOWN_GAZE
        return False

    def _track_face(self, t: float, metrics) -> None:
        if not metrics.face_found:
            return
        in_use =self._episode_last is not None and t - self._episode_last <= 5.0
        if not in_use and t >= self._next_reference:
            self._next_reference = t + REFERENCE_STEP_S
            if metrics.pitch is not None:
                self._pitch_reference.append((t, metrics.pitch))
            if getattr(metrics, "gaze_y", None) is not None:
                self._gaze_reference.append((t, metrics.gaze_y))
        for reference in (self._pitch_reference, self._gaze_reference):
            while reference and reference[0][0] < t - REFERENCE_S:
                reference.popleft()

    def _phone_moving(self) -> bool:
        if len(self._phone_centers) < CONFIRM_HITS:
            return False
        _, first_x, first_y, _ = self._phone_centers[0]
        return any(math.hypot(x - first_x, y - first_y) >= PHONE_MOVE_FACES * scale
                   for _, x, y, scale in self._phone_centers)

    def _submit(self, frame, t: float, face) -> bool:
        """False quando ainda processa o anterior: o quadro é pulado e o próximo tenta de novo (GES-12)."""
        with self._lock:
            if self._busy:
                return False
            self._job, self._busy = (frame.copy(), t, face), True
        self._wake.set()
        return True

    def _worker(self) -> None:
        while not self._stop.is_set():
            if not self._wake.wait(0.5):
                continue
            self._wake.clear()
            with self._lock:
                job, self._job = self._job, None
            if job is None:
                continue
            observation = self._run(*job)
            with self._lock:
                if observation is not None:
                    self._result = observation
                self._busy = False

    def _run(self, frame, t: float, face: FaceSnapshot | None) -> PhoneObservation | None:
        """Detector e, em seguida, as verificações da spec 028 no mesmo quadro (o quadro não sai daqui)."""
        try:
            observation = self.detector.detect(frame, t, face.box if face is not None else None)
        except Exception:
            self._failures += 1
            if self._failures in (1, 100):
                logger.exception("Falha na detecção de celular (%d falhas).", self._failures)
            return None
        if observation is not None and getattr(observation, "checks", None) is None:
            try:
                start = time.perf_counter()
                observation.checks = self.verifier.measure(frame, observation.phones, observation.hands, face,
                                                           observation.timestamp)
                self.verify_ms = (time.perf_counter() - start) * 1000.0
            except Exception:
                self._check_failures += 1
                if self._check_failures in (1, 100):
                    logger.exception("Falha nas verificações do celular na orelha (%d falhas).", self._check_failures)
                observation.checks = [None] * len(observation.phones)  # na orelha não conta; longe dela, como antes
        return observation
