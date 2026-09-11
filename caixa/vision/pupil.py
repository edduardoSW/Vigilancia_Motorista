"""Razão pupila/íris, medida só em câmera infravermelha.

Em câmera RGB comum a íris escura quase não se distingue da pupila, e na resolução típica (íris com 8 a
16 px) não há como medir. Nesses casos a medida fica desligada e marcada como não confiável: nenhum
valor é estimado.

A pupila responde muito mais à luz do que a qualquer substância. Por isso a razão só é comparada com a
linha de base da própria pessoa em faixa de luz parecida (vision/activation.py).
Base: Kuijpers et al., 2025 (Front. Neurosci., doi:10.3389/fnins.2024.1492246). Pupila maior após
lisdexanfetamina nas duas luzes testadas (~50 e ~500 lux), medida como desvio da linha de base de cada pessoa.
"""
from __future__ import annotations

import math
from collections import deque

import cv2
import numpy as np

# Íris humana tem ~11,7 mm (MediaPipe Iris). Com menos de ~24 px de diâmetro a pupila fica com 5 a 10 px,
# e 1 px de erro já muda a razão em 10% ou mais. Ponto de partida, a ajustar com a câmera do veículo.
MIN_IRIS_DIAMETER_PX = 24.0
# Faixa fisiológica aproximada: pupila de ~2 a ~8 mm numa íris de ~11,7 mm.
MIN_RATIO, MAX_RATIO = 0.15, 0.75
# Pupila pelo menos 20% mais escura que o anel da íris (pupila escura com iluminador fora do eixo).
MIN_CONTRAST = 0.20
MAX_CENTER_OFFSET = 0.35  # centro da pupila a no máximo 35% do raio a partir do centro da íris
GLINT_LEVEL = 235  # reflexo do iluminador na córnea
CROP_SIZE = 64

# Câmera infravermelha entrega imagem sem cor. Decide pela maioria dos últimos quadros para não oscilar.
IR_MAX_SATURATION = 25.0
# Pixels muito escuros (faixas pretas, sombra) não têm cor definida e ficam fora da conta: sem isso, uma foto
# colorida com bordas pretas passou por imagem sem cor num teste.
IR_MIN_VALUE = 40
IR_MIN_LIT_SHARE = 0.1
IR_DECISION_FRAMES = 90
IR_MIN_SHARE = 0.9


def is_monochrome(frame_bgr: np.ndarray) -> bool:
    if frame_bgr.ndim == 2 or frame_bgr.shape[2] == 1:
        return True
    small = cv2.resize(frame_bgr, (80, 60), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    lit = hsv[:, :, 2] > IR_MIN_VALUE
    if lit.mean() < IR_MIN_LIT_SHARE:
        return False  # escuro demais para decidir
    return float(hsv[:, :, 1][lit].mean()) < IR_MAX_SATURATION


class InfraredDetector:
    """mode: 'sim' (câmera infravermelha), 'nao' (RGB) ou 'auto' (maioria dos últimos quadros sem cor)."""

    def __init__(self, mode: str = "auto"):
        if mode not in ("auto", "sim", "nao"):
            raise ValueError(f"modo de câmera infravermelha inválido: {mode!r}")
        self.mode = mode
        self._recent = deque(maxlen=IR_DECISION_FRAMES)

    def update(self, frame_bgr: np.ndarray) -> bool:
        if self.mode != "auto":
            return self.mode == "sim"
        self._recent.append(is_monochrome(frame_bgr))
        return len(self._recent) >= 10 and sum(self._recent) >= IR_MIN_SHARE * len(self._recent)


def measure_pupil(gray: np.ndarray, center, iris_diameter: float | None) -> tuple[float | None, str]:
    """(razão pupila/íris ou None, qualidade). gray: quadro em tons de cinza; center: centro da íris em px."""
    if iris_diameter is None or iris_diameter < MIN_IRIS_DIAMETER_PX:
        return None, "iris_pequena"
    radius = iris_diameter / 2.0
    center_x, center_y = float(center[0]), float(center[1])
    half = radius * 1.15
    x1, y1 = int(math.floor(center_x - half)), int(math.floor(center_y - half))
    x2, y2 = int(math.ceil(center_x + half)), int(math.ceil(center_y + half))
    height, width = gray.shape[:2]
    if x1 < 0 or y1 < 0 or x2 > width or y2 > height:
        return None, "fora_do_quadro"

    crop = cv2.resize(gray[y1:y2, x1:x2], (CROP_SIZE, CROP_SIZE), interpolation=cv2.INTER_CUBIC)
    scale_x = CROP_SIZE / (x2 - x1)
    scale_y = CROP_SIZE / (y2 - y1)
    cx, cy = (center_x - x1) * scale_x, (center_y - y1) * scale_y
    r = radius * (scale_x + scale_y) / 2.0
    yy, xx = np.mgrid[0:CROP_SIZE, 0:CROP_SIZE]
    dist = np.hypot(xx - cx, yy - cy)
    inside = dist <= 0.95 * r

    glint = (crop >= GLINT_LEVEL) & (dist <= r)
    if glint.any():
        mask = cv2.dilate(glint.astype(np.uint8), np.ones((3, 3), np.uint8))
        crop = cv2.inpaint(crop, mask, 3, cv2.INPAINT_TELEA)
    blurred = cv2.GaussianBlur(crop, (5, 5), 0)

    ring = (dist >= 0.70 * r) & inside
    ring_level = float(np.median(blurred[ring]))
    darkest = float(np.percentile(blurred[inside], 3))
    if ring_level <= 1.0 or (ring_level - darkest) / ring_level < MIN_CONTRAST:
        return None, "sem_contraste"

    # Borda da pupila a meia altura entre o fundo escuro e o anel da íris.
    binary = ((blurred <= (darkest + ring_level) / 2.0) & inside).astype(np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    count, labels, stats, centroids = cv2.connectedComponentsWithStats(binary)
    best = None
    for label in range(1, count):
        offset = math.hypot(centroids[label][0] - cx, centroids[label][1] - cy) / r
        area = int(stats[label, cv2.CC_STAT_AREA])
        if offset <= MAX_CENTER_OFFSET and (best is None or area > best[0]):
            best = (area, label)
    if best is None:
        return None, "pupila_nao_encontrada"

    contours, _ = cv2.findContours((labels == best[1]).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    contour = max(contours, key=cv2.contourArea)
    if len(contour) >= 5:
        # Maior eixo da elipse: resiste à pálpebra cobrindo o topo da pupila.
        _, axes, _ = cv2.fitEllipse(contour)
        diameter = max(axes)
    else:
        diameter = 2.0 * math.sqrt(best[0] / math.pi)
    ratio = diameter / (2.0 * r)
    if not MIN_RATIO <= ratio <= MAX_RATIO:
        return None, "fora_da_faixa"
    return ratio, "ok"
