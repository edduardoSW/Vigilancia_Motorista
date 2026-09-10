"""Segunda opinião sobre olho aberto ou fechado: classificador OCEC rodando no OpenCV DNN.

Modelo: OCEC, de Katsuya Hyodo (https://github.com/PINTO0309/OCEC), licença MIT.
Treinado com o dataset closed-open-eyes, de Michał Młodawski (ODC-By 1.0). Ver THIRD_PARTY_NOTICES.md.
Entrada 1x3x24x40 em RGB, escala 0 a 1. Saída: probabilidade de o olho estar aberto.
Roda pelo OpenCV, sem onnxruntime, então funciona também no macOS Intel.
"""
from __future__ import annotations

import logging
import math
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger("drivesafe.eye_state")

DEFAULT_MODEL = Path(__file__).resolve().parent / "models" / "ocec_s.onnx"
INPUT_SIZE = (40, 24)  # largura, altura

# Caixa do olho: largura = distância entre os cantos x 1,2 e proporção 1,85:1, próxima das caixas
# usadas no treino do modelo. Valores iniciais: ajustar com vídeos reais da câmera do veículo.
CORNER_WIDTH_FACTOR = 1.2
BOX_ASPECT = 1.85
MIN_EYE_WIDTH_PX = 8.0


def eye_box_from_corners(corner_a, corner_b) -> tuple[float, float, float]:
    """(centro_x, centro_y, largura da caixa) a partir dos dois cantos do olho."""
    center_x = (float(corner_a[0]) + float(corner_b[0])) / 2.0
    center_y = (float(corner_a[1]) + float(corner_b[1])) / 2.0
    width = math.hypot(float(corner_a[0]) - float(corner_b[0]), float(corner_a[1]) - float(corner_b[1]))
    return center_x, center_y, width * CORNER_WIDTH_FACTOR


class EyeStateClassifier:
    def __init__(self, model_path: Path = DEFAULT_MODEL):
        model_path = Path(model_path)
        if not model_path.is_file():
            raise RuntimeError(f"Modelo do classificador de olho não encontrado em {model_path}.")
        self._net = cv2.dnn.readNetFromONNX(str(model_path))
        logger.info("Classificador de olho carregado (%s).", model_path.name)

    def open_probabilities(self, frame_bgr: np.ndarray, boxes) -> list[float | None]:
        """boxes: (centro_x, centro_y, largura) de cada olho. Devolve a probabilidade de aberto de cada um."""
        frame_height, frame_width = frame_bgr.shape[:2]
        crops, positions = [], []
        for position, (center_x, center_y, width) in enumerate(boxes):
            if width < MIN_EYE_WIDTH_PX:
                continue
            height = width / BOX_ASPECT
            x1 = max(0, int(round(center_x - width / 2)))
            x2 = min(frame_width, int(round(center_x + width / 2)))
            y1 = max(0, int(round(center_y - height / 2)))
            y2 = min(frame_height, int(round(center_y + height / 2)))
            if x2 - x1 < 4 or y2 - y1 < 2:
                continue
            crops.append(frame_bgr[y1:y2, x1:x2])
            positions.append(position)

        probabilities: list[float | None] = [None] * len(boxes)
        if not crops:
            return probabilities
        blob = cv2.dnn.blobFromImages(crops, 1 / 255.0, INPUT_SIZE, (0, 0, 0), swapRB=True, crop=False)
        self._net.setInput(blob)
        # Conforme o motor do OpenCV a saída vem (N,) ou (N, 1).
        for position, value in zip(positions, np.asarray(self._net.forward()).ravel()):
            probabilities[position] = float(value)
        return probabilities
