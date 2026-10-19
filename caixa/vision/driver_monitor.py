"""Loop do dispositivo: câmera → medidas do rosto → módulos (vision/engine.py) → alarme, fila de eventos e janela."""
from __future__ import annotations

import logging
import time
from collections import deque

import cv2
import numpy as np

from vision.engine import DriverState, DriverStateEngine

logger = logging.getLogger("drivesafe.monitor")

WINDOW_TITLE = "RotaGuard - Monitoramento"
FONT = cv2.FONT_HERSHEY_SIMPLEX
CAMERA_REOPEN_AFTER_FAILURES = 30
CAMERA_OK_WINDOW_S = 5.0
PERFORMANCE_LOG_S = 60.0
RISK_COLORS = {0: (0, 200, 0), 1: (0, 200, 255), 2: (0, 140, 255), 3: (0, 0, 255)}
NO_FACE_COLOR = (150, 150, 150)
# As fontes do OpenCV não têm acentos: textos da janela sem acentuação.
RISK_TEXT = {0: "RISCO NORMAL", 1: "RISCO: ATENCAO", 2: "RISCO ALTO", 3: "RISCO CRITICO"}
PHONE_TEXT = {"celular_na_mao": "Celular na mao", "celular_no_ouvido": "Celular no ouvido",
              "olhando_celular": "Olhando o celular"}
GESTURE_TEXT = {"olhos_esfregados": "Esfregando os olhos", "mao_no_rosto": "Mao no rosto"}
VISIBILITY_TEXT = {"oculos_escuros": "Olhos nao visiveis (oculos escuros)", "olhos_fora_da_imagem": "Olhos fora da imagem"}
PUPIL_TEXT = {"camera_rgb": "nao confiavel (camera RGB)", "iris_pequena": "iris pequena na imagem",
              "sem_contraste": "sem contraste", "olho_fechando": "olho fechando", "sem_pontos_da_iris": "sem iris (YuNet)"}

# Malha do rosto (spec 023, decisão 4, refeita pela spec 029). Tecla M alterna os modos, na tela do app e na janela
# do OpenCV. Regras da 029: nada preenchido sobre a pele; nada dentro do olho (as marcas dos olhos ficam do lado de
# fora, como colchetes); lima só no que está medindo, o resto em branco translúcido.
# - discreta (padrão): pontos do contorno do rosto, contorno tracejado, colchetes dos olhos, contorno externo da boca
#   tracejado e os cantos das regiões do pulso;
# - completa: o mesmo e os 478 pontos, menos os de dentro e de perto dos olhos e das regiões do pulso;
# - desligada ("Só o rosto"): nada.
MESH_MODES = ("discreta", "completa", "desligada")
MESH_LABELS = {"discreta": "Discreta", "completa": "Completa", "desligada": "Só o rosto"}
WINDOW_MESH_MODE = "discreta"
# Contornos do Face Mesh, em ordem de traço, a partir de FaceLandmarksConnections
# (mediapipe/tasks/python/vision/face_landmarker.py, conferido no MediaPipe 1.0.1, que não tem mediapipe.solutions).
FACE_OVAL_PATH = (10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148,
                  176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109)
RIGHT_EYE_PATH = (33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246)
LEFT_EYE_PATH = (263, 249, 390, 373, 374, 380, 381, 382, 362, 398, 384, 385, 386, 387, 388, 466)
LIPS_OUTER_PATH = (61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 409, 270, 269, 267, 0, 37, 39, 40, 185)
LIPS_INNER_PATH = (78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308, 415, 310, 311, 312, 13, 82, 81, 80, 191)
BROW_PATHS = ((46, 53, 52, 65, 55), (70, 63, 105, 66, 107), (276, 283, 282, 295, 285), (300, 293, 334, 296, 336))
# Íris: anel de 4 pontos e centro (o mesmo que vision/face.py usa para o olhar).
IRISES = (((469, 470, 471, 472), 468), ((474, 475, 476, 477), 473))
# 21 pontos da mão do Hand Landmarker (vision/phone.py): punho, polegar e os quatro dedos.
HAND_CONNECTIONS = ((0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (5, 9), (9, 10), (10, 11),
                    (11, 12), (9, 13), (13, 14), (14, 15), (15, 16), (13, 17), (17, 18), (18, 19), (19, 20), (0, 17))
# Cores em BGR: branco translúcido no que só situa (pontos, contorno, boca); lima (#d5f669) no que mede (olhos e, com
# leitura pronta, as regiões do pulso); celular em laranja (#f4a259), a cor de aviso da tela.
MESH_DOT = (236, 242, 234)
MESH_LIME = (105, 246, 213)
MESH_PHONE = (89, 162, 244)
MESH_HAND = (196, 232, 206)
# Opacidades (spec 029, decisão 2): pontos do contorno a 25%, os 478 da completa a 40%, contorno tracejado a 30%,
# boca a 40%, colchetes dos olhos a 90% (100% com o olho fechado) e cantos do pulso de 35% a 70% no ritmo da onda
# (menores e mais apagados que os colchetes: o olho é o que mais importa ver).
EDGE_DOT_ALPHA = 0.25
FULL_DOT_ALPHA = 0.4
OVAL_ALPHA = 0.3
LIPS_ALPHA = 0.4
BRACKET_ALPHA = 0.9
ROI_IDLE_ALPHA = 0.35
HAND_ALPHA = 0.55
DOT_RADIUS = 1.0
# Antisserrilhado sem cauda: a parte do pixel com peso final abaixo de 4% (mudança de até 4 níveis em 255, invisível)
# não é tocada. O traço continua suave e o rosto fica com menos pixels mexidos (MAL-03).
MIN_STROKE_WEIGHT = 0.04
OVAL_DASH = (0.38, 0.62)  # traço curto no meio de um segmento do contorno sim e outro não
LIPS_DASH_PX = (2.0, 4.0)  # boca: traço de 2 px e espaço de 4 px (no quadro de 640)
CLOSED_EYE_OPENNESS = 0.2  # abaixo disso o colchete do olho fica mais forte (o limiar do PERCLOS, vision/eyes.py)
EYE_KEEP_OUT_PX = 3.0  # nenhum ponto a menos disso do olho
SHIFT = 4  # coordenadas com 4 bits de fração: traço antisserrilhado no lugar certo, sem arredondar para o pixel
ONE = 1 << SHIFT
MIN_FACE_POINTS = 468
# Pontos da pálpebra e da íris: nunca desenhados (MAL-01).
EYE_INDICES = frozenset(RIGHT_EYE_PATH + LEFT_EYE_PATH + tuple(i for ring, c in IRISES for i in ring + (c,)))


def next_mesh_mode(mode: str) -> str:
    index = MESH_MODES.index(mode) if mode in MESH_MODES else -1
    return MESH_MODES[(index + 1) % len(MESH_MODES)]


def _fixed(points, scale: float = 1.0) -> np.ndarray:
    return np.round(np.asarray(points, dtype=np.float32).reshape(-1, 2) * (scale * ONE)).astype(np.int32)


def _pulse(cardio) -> float:
    """Intensidade de 0 a 1 das regiões do pulso, no ritmo da onda medida (só com leitura pronta)."""
    wave = getattr(cardio, "onda", None) if cardio is not None else None
    if getattr(cardio, "estado", None) != "pronto" or not wave:
        return 0.35
    return min(1.0, max(0.0, (float(wave[-1]) + 1.0) / 2.0))


_DOT_STEPS = 8  # posição do centro dentro do pixel, em oitavos (antisserrilhado de subpixel)
_DOT_TABLES: dict = {}


def _dot_table(radius: float):
    """Pesos (0 a 256) dos pixels em volta de um ponto, para cada posição de subpixel do centro: peso em tenda pela
    distância ao centro. Calculado uma vez por raio; depois cada quadro só consulta a tabela."""
    key = round(radius, 3)
    if key not in _DOT_TABLES:
        span = int(np.ceil(2 * radius))
        fractions = (np.arange(_DOT_STEPS) + 0.5) / _DOT_STEPS
        # Primeiro pixel cujo centro pode cair dentro do raio, relativo ao pixel do centro.
        starts = (np.floor(fractions - 0.5 - radius) + 1).astype(np.int32)
        grid = np.arange(span)
        weights = np.zeros((_DOT_STEPS, _DOT_STEPS, span * span), dtype=np.int32)
        for qy in range(_DOT_STEPS):
            for qx in range(_DOT_STEPS):
                px = starts[qx] + np.tile(grid, span) + 0.5 - fractions[qx]
                py = starts[qy] + np.repeat(grid, span) + 0.5 - fractions[qy]
                weights[qy, qx] = np.round(np.clip(1.0 - np.hypot(px, py) / radius, 0.0, 1.0) * 256)
        _DOT_TABLES[key] = (starts, np.tile(grid, span).astype(np.int32), np.repeat(grid, span).astype(np.int32),
                            weights.reshape(_DOT_STEPS * _DOT_STEPS, span * span))
    return _DOT_TABLES[key]


def _splat_dots(image, fixed: np.ndarray, color, alpha: float, radius: float = 1.25) -> None:
    """Pontos redondos e antisserrilhados, todos de uma vez: uma leitura e uma escrita vetorizadas, com os pesos de
    uma tabela por posição de subpixel (um cv2.circle por ponto custava ~1 ms nos 478 pontos)."""
    if fixed.size == 0:
        return
    height, width = image.shape[:2]
    starts, offsets_x, offsets_y, table = _dot_table(radius)
    pixel = fixed >> SHIFT
    step = (fixed & (ONE - 1)) * _DOT_STEPS >> SHIFT
    xs = np.clip((pixel[:, 0] + starts[step[:, 0]])[:, None] + offsets_x, 0, width - 1)
    ys = np.clip((pixel[:, 1] + starts[step[:, 1]])[:, None] + offsets_y, 0, height - 1)
    weight = ((table[step[:, 1] * _DOT_STEPS + step[:, 0]] * int(round(alpha * 256))) >> 8).reshape(-1, 1)
    if not image.flags.c_contiguous:  # recorte do quadro (o retângulo do rosto): índices 2D
        pixels = image[ys, xs].reshape(-1, 3).astype(np.int32)
        image[ys.ravel(), xs.ravel()] = (pixels + (((np.asarray(color, dtype=np.int32) - pixels) * weight) >> 8)).astype(np.uint8)
        return
    flat = image.reshape(-1, 3)
    index = (ys * width + xs).ravel()
    pixels = flat[index].astype(np.int32)
    flat[index] = (pixels + (((np.asarray(color, dtype=np.int32) - pixels) * weight) >> 8)).astype(np.uint8)


def _corner_box(image, box, scale: float, color) -> None:
    x1, y1, x2, y2 = (float(v) * scale for v in box[:4])
    arm = max(6.0, min(x2 - x1, y2 - y1) * 0.22)
    for (cx, cy), (dx, dy) in (((x1, y1), (1, 1)), ((x2, y1), (-1, 1)), ((x1, y2), (1, -1)), ((x2, y2), (-1, -1))):
        corner = _fixed([(cx + dx * arm, cy), (cx, cy), (cx, cy + dy * arm)])
        cv2.polylines(image, [corner], False, color, 2, cv2.LINE_AA, SHIFT)


def _draw_hands(image, hands, scale: float) -> None:
    """Mãos translúcidas, no retângulo de cada mão (o vídeo continua aparecendo por baixo)."""
    height, width = image.shape[:2]
    for hand in hands or ():
        points = np.asarray(hand, dtype=np.float32).reshape(-1, 2)
        if points.shape[0] < 21:
            continue
        points = points * scale
        x1, y1 = (max(0, int(v) - 4) for v in points.min(axis=0))
        x2, y2 = min(width, int(points[:, 0].max()) + 5), min(height, int(points[:, 1].max()) + 5)
        if x2 - x1 < 2 or y2 - y1 < 2:
            continue
        region = image[y1:y2, x1:x2]
        layer = region.copy()
        fixed = _fixed(points - np.array([x1, y1], dtype=np.float32))
        cv2.polylines(layer, [np.array([fixed[a], fixed[b]]) for a, b in HAND_CONNECTIONS], False, MESH_HAND, 1,
                      cv2.LINE_AA, SHIFT)
        for x, y in fixed.tolist():
            cv2.circle(layer, (x, y), int(1.2 * ONE), MESH_HAND, -1, cv2.LINE_AA, SHIFT)
        cv2.addWeighted(layer, HAND_ALPHA, region, 1.0 - HAND_ALPHA, 0, dst=region)


_KERNEL3 = np.ones((3, 3), dtype=np.uint8)


def _eye_guard(image, eyes) -> list:
    """Pixels de dentro de cada olho (polígono da pálpebra e mais 1 px), guardados antes de desenhar e devolvidos no
    fim: garantia de que nada do desenho (nem mão nem celular) cobre o olho (MAL-01)."""
    height, width = image.shape[:2]
    guards = []
    for eye in eyes:
        x1, y1 = (max(0, int(np.floor(v)) - 2) for v in eye.min(axis=0))
        x2 = min(width, int(np.ceil(eye[:, 0].max())) + 3)
        y2 = min(height, int(np.ceil(eye[:, 1].max())) + 3)
        if x2 <= x1 or y2 <= y1:
            continue
        mask = np.zeros((y2 - y1, x2 - x1), dtype=np.uint8)
        cv2.fillPoly(mask, [_fixed(eye - np.array([x1, y1], dtype=np.float32))], 1, cv2.LINE_8, SHIFT)
        ys, xs = np.nonzero(cv2.dilate(mask, _KERNEL3))
        ys, xs = ys + y1, xs + x1
        guards.append((ys, xs, image[ys, xs].copy()))
    return guards


class _Strokes:
    """Traços de uma cor, misturados de uma vez no recorte do rosto. Linhas viram amostras com peso bilinear nos 4
    pixels em volta (antisserrilhado); traços retos (colchetes e cantos) são pixels inteiros, nítidos. Onde dois se
    cruzam, o pixel fica com a maior opacidade, sem escurecer o encontro. Sem máscara do tamanho do rosto: só os
    pixels tocados são ordenados e misturados."""

    def __init__(self):
        self._points: list = []
        self._alphas: list = []
        self._rows: list = []
        self._columns: list = []
        self._run_alphas: list = []

    def segments(self, starts: np.ndarray, ends: np.ndarray, alpha: float, step: float = 0.5) -> None:
        """Linhas retas de starts[k] a ends[k], com uma amostra a cada `step` px."""
        if not len(starts):
            return
        delta = ends - starts
        counts = np.maximum(1, np.ceil(np.hypot(delta[:, 0], delta[:, 1]) / step).astype(np.int32)) + 1
        which = np.repeat(np.arange(len(starts)), counts)
        first = np.repeat(np.cumsum(counts) - counts, counts)
        fraction = ((np.arange(counts.sum()) - first) / np.repeat(counts - 1, counts)).astype(np.float32)
        self._points.append(starts[which] + delta[which] * fraction[:, None])
        self._alphas.append((alpha, int(counts.sum())))

    def run(self, rows, columns, alpha: float) -> None:
        """Pixels inteiros (listas de linhas e colunas): traço reto, um pixel de largura."""
        self._rows += rows
        self._columns += columns
        self._run_alphas += [alpha] * len(rows)

    def blend(self, region, color) -> None:
        height, width = region.shape[:2]
        flats, weights = [], []
        if self._points:
            points = np.concatenate(self._points) - 0.5  # centro do pixel em (i + 0,5, j + 0,5)
            alphas = np.repeat(np.array([a for a, _ in self._alphas], dtype=np.float32),
                               [n for _, n in self._alphas])
            base = np.floor(points).astype(np.int32)
            fx, fy = (points - base).T
            gx, gy = 1.0 - fx, 1.0 - fy
            xs = np.concatenate([base[:, 0], base[:, 0] + 1, base[:, 0], base[:, 0] + 1])
            ys = np.concatenate([base[:, 1], base[:, 1], base[:, 1] + 1, base[:, 1] + 1])
            w = np.concatenate([gx * gy, fx * gy, gx * fy, fx * fy]) * np.tile(alphas, 4)
            keep = (w >= MIN_STROKE_WEIGHT) & (xs >= 0) & (xs < width) & (ys >= 0) & (ys < height)
            flats.append(ys[keep] * width + xs[keep])
            weights.append(w[keep])
        if self._rows:
            rows = np.array(self._rows, dtype=np.int32)
            columns = np.array(self._columns, dtype=np.int32)
            keep = (columns >= 0) & (columns < width) & (rows >= 0) & (rows < height)
            flats.append(rows[keep] * width + columns[keep])
            weights.append(np.array(self._run_alphas, dtype=np.float32)[keep])
        if not flats:
            return
        flat = np.concatenate(flats)
        weight = np.concatenate(weights)
        if not flat.size:
            return
        order = np.lexsort((weight, flat))  # por pixel e, dentro dele, do peso menor para o maior
        flat, weight = flat[order], weight[order]
        last = np.ones(flat.size, dtype=bool)
        last[:-1] = flat[1:] != flat[:-1]  # fica a última de cada pixel: a de maior peso
        flat, weight = flat[last], np.round(weight[last] * 256).astype(np.int32)[:, None]
        ys, xs = np.divmod(flat, width)
        pixels = region[ys, xs].astype(np.int32)
        region[ys, xs] = (pixels + (((np.asarray(color, dtype=np.int32) - pixels) * weight) >> 8)).astype(np.uint8)


def _dash_segments(path: np.ndarray, closed: bool, dash: float, gap: float):
    """Começo e fim de cada traço de `dash` px, com `gap` px de espaço, ao longo de uma linha."""
    points = np.vstack([path, path[:1]]) if closed else path
    lengths = np.hypot(*np.diff(points, axis=0).T)
    cumulative = np.concatenate([[0.0], np.cumsum(lengths)])
    total = float(cumulative[-1])
    if total <= dash:
        return points[:1], points[-1:]
    begin = np.arange(gap / 2.0, total - 0.5, dash + gap)
    end = np.minimum(begin + dash, total)

    def along(distance):
        return np.stack([np.interp(distance, cumulative, points[:, 0]), np.interp(distance, cumulative, points[:, 1])],
                        axis=1).astype(np.float32)

    return along(begin), along(end)


def _eye_box(eye: np.ndarray):
    x0, y0 = eye.min(axis=0)
    x1, y1 = eye.max(axis=0)
    return float(x0), float(y0), float(x1), float(y1)


def _eye_brackets(strokes: _Strokes, box, scale: float, closed: bool) -> None:
    """Dois colchetes finos nos cantos do olho, do lado de fora: "[" antes de um canto e "]" depois do outro.
    A altura vem da largura do olho (não pisca junto com a pálpebra); os ganchos não chegam ao olho (MAL-01)."""
    x0, y0, x1, y1 = box
    width = max(x1 - x0, 4.0)
    margin = max(3.0 * scale, 0.2 * width)
    hook = min(max(2.0 * scale, 0.1 * width), margin - 1.0)
    half = max(0.2 * width, 2.0 * scale)
    middle = (y0 + y1) / 2.0
    top, bottom = int(round(middle - half)), int(round(middle + half))
    thickness = max(1, int(round(scale))) + (1 if closed else 0)
    rows, columns = [], []
    for x, direction in ((x0 - margin, 1), (x1 + margin, -1)):
        column = int(round(x))
        for k in range(thickness):
            rows += range(top, bottom + 1)
            columns += [column - direction * k] * (bottom - top + 1)
        tip = int(round(x + direction * hook))
        span = range(min(column, tip), max(column, tip) + 1)
        for row in (top, bottom):
            rows += [row] * len(span)
            columns += span
    strokes.run(rows, columns, 1.0 if closed else BRACKET_ALPHA)


def _roi_corners(strokes: _Strokes, polygon: np.ndarray, scale: float, alpha: float) -> tuple:
    """Só os cantos da região do pulso, por fora da caixa dela: sem preenchimento e sem contorno inteiro (MAL-02)."""
    x0, y0 = polygon.min(axis=0).tolist()
    x1, y1 = polygon.max(axis=0).tolist()
    out = 2.0 * scale
    arm = int(round(max(2.0 * scale, 0.1 * min(x1 - x0, y1 - y0))))
    rows, columns = [], []
    for cx, cy, dx, dy in ((x0 - out, y0 - out, 1, 1), (x1 + out, y0 - out, -1, 1), (x0 - out, y1 + out, 1, -1),
                           (x1 + out, y1 + out, -1, -1)):
        cx, cy = int(round(cx)), int(round(cy))
        rows += [cy] * (arm + 1) + [cy + dy * k for k in range(1, arm + 1)]
        columns += [cx + dx * k for k in range(arm + 1)] + [cx] * arm
    strokes.run(rows, columns, alpha)
    return x0, y0, x1, y1


def draw_face_mesh(image, state, mode: str = "discreta", hands=(), scale: float = 1.0):
    """Desenha a malha no quadro (no lugar). scale: o quadro foi ampliado em relação aos pontos medidos.

    discreta: pontos do contorno, contorno tracejado, colchetes dos olhos, boca tracejada e cantos do pulso;
    completa: o mesmo e os 478 pontos (menos os do olho e das regiões do pulso); desligada: nada.
    Celular (cantos da caixa) e mãos aparecem nos dois modos visíveis. Sem os 478 pontos (YuNet), marca os olhos por
    fora. Em todos os modos, os pixels de dentro dos olhos ficam como estavam (MAL-01)."""
    if mode not in MESH_MODES:
        raise ValueError(f"modo de malha desconhecido: {mode!r}")
    if mode == "desligada":
        return image
    metrics = getattr(state, "metrics", None)
    face_found = bool(getattr(metrics, "face_found", False))
    landmarks = getattr(metrics, "landmarks", None) if face_found else None
    guards = []

    if landmarks is not None and len(landmarks) >= MIN_FACE_POINTS:
        points = np.asarray(landmarks, dtype=np.float32).reshape(len(landmarks), -1)[:, :2] * scale
        eyes = [points[list(RIGHT_EYE_PATH)], points[list(LEFT_EYE_PATH)]]
        guards = _eye_guard(image, eyes)
        openness = getattr(getattr(state, "drowsiness", None), "openness", None)
        _draw_face(image, points, eyes, mode, getattr(state, "cardio", None), scale,
                   eyes_closed=openness is not None and openness < CLOSED_EYE_OPENNESS)
    elif face_found and getattr(metrics, "eye_points", None) is not None:
        _draw_eye_points(image, np.asarray(metrics.eye_points, dtype=np.float32).reshape(-1, 2) * scale, scale)

    phone = getattr(state, "phone", None)
    for box in getattr(phone, "boxes", None) or ():
        _corner_box(image, box, scale, MESH_PHONE)
    _draw_hands(image, hands, scale)
    for ys, xs, saved in guards:
        image[ys, xs] = saved
    return image


def _draw_eye_points(image, points: np.ndarray, scale: float) -> None:
    """Modo YuNet (sem os 478 pontos): colchetes ao lado de cada olho, nunca um ponto em cima dele."""
    if len(points) == 2:
        distance = float(np.hypot(*(points[1] - points[0]))) or 40.0 * scale
        half_w, half_h = 0.22 * distance, 0.07 * distance
        boxes = [(x - half_w, y - half_h, x + half_w, y + half_h) for x, y in points.tolist()]
    else:
        boxes = [_eye_box(points)]
    lime = _Strokes()
    for box in boxes:
        _eye_brackets(lime, box, scale, closed=False)
    lime.blend(image, MESH_LIME)


def _draw_face(image, points: np.ndarray, eyes: list, mode: str, cardio, scale: float, eyes_closed: bool = False) -> None:
    # Só no retângulo do rosto, com folga para os colchetes e os cantos do pulso.
    height, width = image.shape[:2]
    pad = int(10 * scale) + 6
    x1 = max(0, int(points[:, 0].min()) - pad)
    y1 = max(0, int(points[:, 1].min()) - pad)
    x2 = min(width, int(points[:, 0].max()) + pad + 1)
    y2 = min(height, int(points[:, 1].max()) + pad + 1)
    if x2 - x1 < 4 or y2 - y1 < 4:
        return
    region = image[y1:y2, x1:x2]
    offset = np.array([x1, y1], dtype=np.float32)
    local = points - offset
    white, lime = _Strokes(), _Strokes()

    # Contorno do rosto: traço curto no meio de um segmento sim e outro não.
    oval = local[list(FACE_OVAL_PATH)]
    following = np.roll(oval, -1, axis=0)
    white.segments((oval + (following - oval) * OVAL_DASH[0])[::2], (oval + (following - oval) * OVAL_DASH[1])[::2],
                   OVAL_ALPHA)
    # Boca: só o contorno de fora, tracejado.
    dash, gap = (size * max(1.0, scale) for size in LIPS_DASH_PX)
    white.segments(*_dash_segments(local[list(LIPS_OUTER_PATH)], True, dash, gap), LIPS_ALPHA)
    # Olhos: colchetes por fora, em lima (é o que está medindo).
    eye_boxes = [_eye_box(eye - offset) for eye in eyes]
    for box in eye_boxes:
        _eye_brackets(lime, box, scale, eyes_closed)
    # Regiões do pulso: só os cantos; lima pulsando com leitura pronta, branco enquanto mede.
    roi_boxes = []
    rois = (getattr(cardio, "rois", None) or {}) if cardio is not None else {}
    ready = getattr(cardio, "estado", None) == "pronto"
    for polygon in rois.values():
        if polygon is None or len(polygon) < 3:
            continue
        polygon = np.asarray(polygon, dtype=np.float32).reshape(-1, 2) * scale - offset
        roi_boxes.append(_roi_corners(lime if ready else white, polygon, scale,
                                      (0.35 + 0.35 * _pulse(cardio)) if ready else ROI_IDLE_ALPHA))
    white.blend(region, MESH_DOT)
    lime.blend(region, MESH_LIME)

    # Pontos: na discreta, só os do contorno; na completa, todos menos os do olho, os de perto dele e os de dentro das
    # regiões do pulso (que ficam limpas para a pele aparecer).
    radius = DOT_RADIUS * max(1.0, scale ** 0.5)
    if mode == "discreta":
        _splat_dots(region, _fixed(local[list(FACE_OVAL_PATH)]), MESH_DOT, EDGE_DOT_ALPHA, radius=radius)
        return
    keep = np.ones(len(local), dtype=bool)
    keep[[i for i in EYE_INDICES if i < len(local)]] = False
    xs, ys = local[:, 0], local[:, 1]
    reach = EYE_KEEP_OUT_PX * scale + radius
    for bx0, by0, bx1, by1 in eye_boxes:
        keep &= ~((xs > bx0 - reach) & (xs < bx1 + reach) & (ys > by0 - reach) & (ys < by1 + reach))
    for bx0, by0, bx1, by1 in roi_boxes:
        keep &= ~((xs > bx0 - radius) & (xs < bx1 + radius) & (ys > by0 - radius) & (ys < by1 + radius))
    _splat_dots(region, _fixed(local[keep]), MESH_DOT, FULL_DOT_ALPHA, radius=radius)


def recent_hands(phone_monitor, now: float | None = None, max_age_s: float = 1.0) -> list:
    """Pontos das mãos da última detecção (vision/phone.py), se ela for recente. Para desenhar, nunca para gravar."""
    observation = getattr(phone_monitor, "last_observation", None) if phone_monitor is not None else None
    if observation is None:
        return []
    if now is not None and now - observation.timestamp > max_age_s:
        return []
    return list(observation.hands)


class LatencyMeter:
    """Tempo por quadro (análise do rosto + módulos), para medir e reportar desempenho."""

    def __init__(self, size: int = 300):
        self._values = deque(maxlen=size)

    def add(self, milliseconds: float) -> None:
        self._values.append(milliseconds)

    def summary(self) -> dict | None:
        if not self._values:
            return None
        ordered = sorted(self._values)
        return {
            "media_ms": round(sum(ordered) / len(ordered), 1),
            "p95_ms": round(ordered[min(len(ordered) - 1, int(0.95 * len(ordered)))], 1),
            "max_ms": round(ordered[-1], 1),
        }


def draw_text_block(display, entries, x: int, y: int, padding: int = 8) -> None:
    """Escreve linhas (texto, escala, espessura, cor) sobre uma faixa escura, legível até em fundo claro."""
    sizes = [cv2.getTextSize(text, FONT, scale, thickness) for text, scale, thickness, _ in entries]
    block_width = max(size[0][0] for size in sizes) + 2 * padding
    block_height = sum(size[0][1] + size[1] + padding for size in sizes) + padding
    x2 = min(display.shape[1], x + block_width)
    y2 = min(display.shape[0], y + block_height)
    region = display[y:y2, x:x2]
    display[y:y2, x:x2] = cv2.addWeighted(region, 0.35, region, 0.0, 0)

    cursor = y + padding
    for (text, scale, thickness, color), ((_, text_height), baseline) in zip(entries, sizes):
        cursor += text_height
        cv2.putText(display, text, (x + padding, cursor), FONT, scale, color, thickness, cv2.LINE_AA)
        cursor += baseline + padding


def draw_overlay(frame, state: DriverState, latency: dict | None = None, mesh_mode: str = WINDOW_MESH_MODE,
                 hands=()):
    display = frame.copy()
    height, width = display.shape[:2]
    metrics, drowsy, risk = state.metrics, state.drowsiness, state.risk

    draw_face_mesh(display, state, mesh_mode, hands=hands)

    color = RISK_COLORS.get(risk.level, NO_FACE_COLOR)
    if risk.level == 0 and not drowsy.face_found:
        color = NO_FACE_COLOR
    white = (255, 255, 255)
    warning = (0, 200, 255)
    entries = [(RISK_TEXT[risk.level], 0.8, 2, color), (drowsy.status, 0.5, 1, white)]
    if not state.visibility.eyes_ok:
        entries.append((VISIBILITY_TEXT.get(state.visibility.reason, "Olhos nao visiveis"), 0.5, 1, warning))
    if drowsy.openness is not None:
        entries.append((f"Abertura do olho: {drowsy.openness * 100:.0f}%", 0.5, 1, white))
    if drowsy.closed_for > 0:
        entries.append((f"Fechado ha: {drowsy.closed_for:.1f}s", 0.5, 1, white))
    if drowsy.perclos_60s is not None:
        entries.append((f"PERCLOS 60s: {drowsy.perclos_60s * 100:.1f}%", 0.5, 1, white))
    entries.append((f"Piscadas no ultimo minuto: {drowsy.blinks_last_minute}", 0.5, 1, white))
    if state.phone is not None and state.phone.state != "sem_celular":
        entries.append((f"{PHONE_TEXT[state.phone.state]} ({state.phone.duration:.0f}s)", 0.5, 1, warning))
    touch = state.phone.face_touch if state.phone is not None else None
    if touch is not None:
        if touch.gesture is not None:
            entries.append((GESTURE_TEXT[touch.gesture], 0.5, 1, warning))
        entries.append((f"Em 10 min: olhos esfregados {touch.rubs_10min}, mao no rosto {touch.touches_10min}",
                        0.45, 1, (200, 200, 200)))
    if metrics.pupil_ratio is not None:
        entries.append((f"Pupila/iris: {metrics.pupil_ratio:.2f}", 0.5, 1, white))
    elif metrics.face_found and metrics.pupil_quality:
        entries.append((f"Pupila: {PUPIL_TEXT.get(metrics.pupil_quality, metrics.pupil_quality)}", 0.45, 1, (200, 200, 200)))
    if state.activation is not None:
        activation = state.activation
        text = ("Sinais de ativacao: sem linha de base" if activation.index is None else
                f"Sinais de ativacao: {activation.index:.2f} (confianca {activation.confidence_label})")
        entries.append((text, 0.45, 1, (200, 200, 200)))
    performance = [f"FPS: {drowsy.fps:.0f}"] if drowsy.fps else []
    if latency:
        performance.append(f"latencia {latency['media_ms']:.0f} ms (p95 {latency['p95_ms']:.0f})")
    if performance:
        entries.append(("  ".join(performance), 0.45, 1, white))
    if risk.reasons:
        entries.append(("Motivo: " + ", ".join(risk.reasons[:3]), 0.45, 1, white))
    draw_text_block(display, entries, x=8, y=8)

    if drowsy.calibrating:
        filled = int((width - 20) * drowsy.calibration_progress)
        cv2.rectangle(display, (10, height - 58), (width - 10, height - 48), (40, 40, 40), -1)
        cv2.rectangle(display, (10, height - 58), (10 + filled, height - 48), (0, 200, 255), -1)

    draw_text_block(display, [("q ou Esc: sair   c: recalibrar   m: malha", 0.45, 1, (220, 220, 220))],
                    x=8, y=height - 36)
    return display


class DriverMonitor:
    def __init__(self, analyzer, engine: DriverStateEngine, alarm, events, calibrator_factory=None, policy=None):
        self.analyzer = analyzer
        self.engine = engine
        self.alarm = alarm
        self.events = events
        self.calibrator_factory = calibrator_factory
        # Política do servidor (vision/remote_policy.py), aplicada entre um quadro e outro.
        self.policy = policy
        # Funções chamadas a cada quadro com (quadro, estado): o gancho que entrega o quadro à tela do app de teste
        # (caixa/tela_teste, spec 023) e ao modo teste do servidor. O quadro não pode ser alterado por elas.
        self.listeners = []
        # Malha na janela do OpenCV (tecla M).
        self.mesh_mode = WINDOW_MESH_MODE
        # Pedidos de outra thread (ex.: recalibrar pela tela), executados no loop entre um quadro e outro.
        self._requests = deque()
        # Funções (evento, t) → detalhes extras, chamadas antes de o evento entrar na fila local (spec 026: a tela do
        # app de teste põe sessao_uid e trecho_uid).
        self.event_hooks = []
        self.latency = LatencyMeter()
        self.last_state: DriverState | None = None
        self._running = False
        self._last_frame_at = None
        # True quando run() desistiu por falta de imagem (espera_camera_s); run_monitor sai com código 3.
        self.sem_imagem = False
        self._window_seen = False
        self._created_at = time.monotonic()
        self._next_performance_log = self._created_at + PERFORMANCE_LOG_S
        self._listener_failures = 0

    @property
    def camera_ok(self) -> bool | None:
        """None enquanto a câmera ainda está abrindo; depois, se chegou imagem nos últimos segundos."""
        now = time.monotonic()
        if self._last_frame_at is None:
            return None if now - self._created_at < CAMERA_OK_WINDOW_S * 2 else False
        return now - self._last_frame_at <= CAMERA_OK_WINDOW_S

    def stop(self) -> None:
        self._running = False

    @property
    def running(self) -> bool:
        return self._running

    def request(self, action) -> None:
        """Agenda uma função para rodar na thread do monitor, antes do próximo quadro (sem disputar o motor)."""
        self._requests.append(action)

    def _run_requests(self) -> None:
        while self._requests:
            action = self._requests.popleft()
            try:
                action()
            except Exception:
                logger.exception("Falha num pedido ao monitor.")

    def recalibrate(self) -> None:
        if self.calibrator_factory is None:
            return
        calibrator = self.calibrator_factory()
        if calibrator is None:
            return
        logger.info("Recalibrando: o perfil atual vale até a nova calibração terminar.")
        self.engine.drowsiness.recalibrate(calibrator)

    def process_frame(self, frame, timestamp: float | None = None, ambient_lux: float | None = None) -> DriverState:
        started = time.perf_counter()
        metrics = self.analyzer.analyze(frame, timestamp)
        metrics.ambient_lux = ambient_lux
        state = self.engine.update(metrics, frame)
        self.latency.add((time.perf_counter() - started) * 1000.0)
        self.last_state = state
        for event in state.events:
            details = event.details
            for hook in self.event_hooks:
                try:
                    extra = hook(event, metrics.timestamp)
                except Exception:  # noqa: BLE001 - gancho da tela nunca derruba a detecção
                    logger.exception("Falha num gancho de evento.")
                    extra = None
                if extra:
                    details = {**(details or {}), **extra}
            event.details = details
            self.events.add(event.alert_type, event.risk_level, event.duration, details=details)
        if self.alarm is not None:
            # Spec 027, pacote 1: quatro sinais (info, distracao, sonolencia, critico) e corte do crítico quando o olho
            # abre. Risco da versão antiga (só `alarm`) continua tocando como antes.
            risk = getattr(state, "risk", None)
            if risk is not None and (getattr(risk, "alarm_kind", None) or getattr(risk, "parar_alarme", False)):
                self.alarm.update(risk)
            elif getattr(state, "alarm", False):
                self.alarm.trigger()
        return state

    def live_status(self) -> dict:
        """Resumo do estado atual para o servidor. Sinais de ativação só saem no modo "enviar"."""
        state = self.last_state
        if state is None:
            return {}
        drowsy, risk = state.drowsiness, state.risk
        latency = self.latency.summary()
        status = {
            "risk_level": risk.level,
            "risk_name": risk.name,
            "reasons": list(risk.reasons[:5]),
            "calibrating": drowsy.calibrating,
            "calibration_progress": round(drowsy.calibration_progress, 3),
            "face_found": drowsy.face_found,
            "eyes_visible": state.visibility.eyes_ok,
            "eyes_reason": state.visibility.reason,
            "phone_state": state.phone.state if state.phone is not None else None,
            "fps": round(drowsy.fps, 1) if drowsy.fps else None,
            "latency_p95_ms": latency["p95_ms"] if latency else None,
            "driving_hours": state.context.get("direcao_continua_h"),
            "activation_mode": self.engine.activation_mode,
        }
        if self.engine.activation_mode == "enviar" and state.activation is not None and state.activation.index is not None:
            status["activation_index"] = round(state.activation.index, 3)
            status["activation_confidence"] = state.activation.confidence_label
        return status

    def run(self, camera, show_window: bool, espera_camera_s: float | None = None) -> None:
        """espera_camera_s: sem imagem por esse tempo (nunca chegou ou parou), desiste com sem_imagem=True.
        None mantém o comportamento da caixa: tenta reabrir para sempre."""
        self._running = True
        self.sem_imagem = False
        self._window_seen = False
        failures = 0
        last_image = time.monotonic()
        logger.info("Monitoramento iniciado%s.", " (janela: q ou Esc sai, c recalibra)" if show_window else " sem janela")
        try:
            while self._running:
                ok, frame = camera.read()
                if not ok or frame is None:
                    if getattr(camera, "terminou", False):
                        logger.info("Fim do vídeo %s.", camera.describe())
                        break
                    failures += 1
                    if failures == 1:
                        logger.warning("Sem imagem da câmera %s.", camera.describe())
                    if espera_camera_s and time.monotonic() - last_image >= espera_camera_s:
                        logger.error("Nenhuma imagem da câmera %s em %.0f s. Confira se ela está conectada e se outro "
                                     "programa (Teams, Zoom, navegador) não está usando.", camera.describe(), espera_camera_s)
                        self.sem_imagem = True
                        break
                    if failures % CAMERA_REOPEN_AFTER_FAILURES == 0:
                        logger.warning("Tentando reabrir a câmera...")
                        camera.open()
                    time.sleep(0.1)
                    continue
                if failures:
                    logger.info("Imagem da câmera voltou.")
                failures = 0
                self._last_frame_at = last_image = time.monotonic()

                if self.policy is not None:
                    self.policy.apply_pending()
                self._run_requests()
                try:
                    state = self.process_frame(frame, ambient_lux=camera.ambient_lux())
                except Exception:
                    logger.exception("Erro ao analisar o quadro.")
                    continue

                for listener in list(self.listeners):
                    try:
                        listener(frame, state)
                    except Exception:
                        self._listener_failures += 1
                        if self._listener_failures in (1, 100):
                            logger.exception("Falha num ouvinte do quadro (%d falhas).", self._listener_failures)
                self._log_performance(state)
                if show_window:
                    show_window = self._show(frame, state)
        finally:
            camera.release()
            if show_window:
                cv2.destroyAllWindows()
        logger.info("Monitoramento finalizado.")

    def _log_performance(self, state: DriverState) -> None:
        now = time.monotonic()
        if now < self._next_performance_log:
            return
        self._next_performance_log = now + PERFORMANCE_LOG_S
        latency = self.latency.summary()
        if latency is not None:
            logger.info("Desempenho: %s fps, %.0f ms por quadro em média (p95 %.0f ms, máximo %.0f ms).",
                        f"{state.drowsiness.fps:.1f}" if state.drowsiness.fps else "?",
                        latency["media_ms"], latency["p95_ms"], latency["max_ms"])

    def _show(self, frame, state: DriverState) -> bool:
        try:
            moment = getattr(getattr(state, "metrics", None), "timestamp", None)
            hands = recent_hands(getattr(self.engine, "phone", None), moment)
            cv2.imshow(WINDOW_TITLE, draw_overlay(frame, state, self.latency.summary(), mesh_mode=self.mesh_mode,
                                                  hands=hands))
            key = cv2.waitKey(1) & 0xFF
        except cv2.error as exc:
            logger.warning("Janela indisponível (%s). Seguindo sem janela.", exc)
            return False
        if key in (ord("q"), ord("Q"), 27) or self._window_closed():
            self._running = False
        elif key in (ord("c"), ord("C")):
            self.recalibrate()
        elif key in (ord("m"), ord("M")):
            self.mesh_mode = next_mesh_mode(self.mesh_mode)
        return True

    def _window_closed(self) -> bool:
        """Fechar no X encerra. Só vale depois de o backend dizer que a janela estava visível: onde a propriedade não
        existe (pode ser o caso no macOS) ela volta -1 sempre, e aí só q ou Esc encerram."""
        try:
            visible = cv2.getWindowProperty(WINDOW_TITLE, cv2.WND_PROP_VISIBLE)
        except cv2.error:
            return self._window_seen
        if visible >= 1:
            self._window_seen = True
            return False
        if self._window_seen:
            logger.info("Janela da câmera fechada: encerrando o monitoramento.")
        return self._window_seen


if __name__ == "__main__":
    import os
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from run_monitor import main

    main()
