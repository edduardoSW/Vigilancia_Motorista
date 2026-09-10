"""Medidas do rosto por quadro.

Núcleo: MediaPipe Face Landmarker (Apache 2.0): 478 pontos, pontuação de piscada e pose da cabeça.
Segunda opinião: classificador de olho OCEC (vision/eye_state.py).
Alternativa sem MediaPipe (ex.: macOS Intel): detector de rosto YuNet (MIT) do OpenCV + classificador de olho.

Convenções conferidas com o MediaPipe 1.0.1:
- Pontos do olho e da íris: FACE_LANDMARKS_LEFT_EYE / RIGHT_EYE / LEFT_IRIS / RIGHT_IRIS em
  mediapipe/tasks/python/vision/face_landmarker.py (linhas 158-230). O centro 468 fica a menos de 0,2 px
  da média do anel 469-472, e o 473 da média do anel 474-477, medido em duas fotos de teste.
- Pose: pitch positivo = cabeça baixa (queixo para o peito); yaw positivo = rosto virando para a direita da
  imagem. Conferido girando em 3D uma foto de teste (±35°).
"""
from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from vision.eye_state import EyeStateClassifier, eye_box_from_corners
from vision.pupil import InfraredDetector, measure_pupil

logger = logging.getLogger("drivesafe.face")

MODELS_DIR = Path(__file__).resolve().parent / "models"
DEFAULT_MODEL = MODELS_DIR / "face_landmarker.task"
YUNET_MODEL = MODELS_DIR / "face_detection_yunet_2026may.onnx"
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"

# Seis pontos por olho no padrão do EAR (Soukupová & Čech, 2016): canto, 2 de cima, canto, 2 de baixo.
RIGHT_EYE = (33, 160, 158, 133, 153, 144)
LEFT_EYE = (362, 385, 387, 263, 373, 380)
# Anel da íris (direita, cima, esquerda, baixo na imagem) e centro.
RIGHT_IRIS = (469, 470, 471, 472)
LEFT_IRIS = (474, 475, 476, 477)
RIGHT_IRIS_CENTER = 468
LEFT_IRIS_CENTER = 473
# Canto esquerdo, lábio superior interno, canto direito, lábio inferior interno.
MOUTH = (78, 13, 308, 14)
# Lados do contorno do rosto na altura das orelhas (FACE_LANDMARKS_FACE_OVAL, face_landmarker.py linhas 240-261).
FACE_SIDES = (234, 454)

# Quando um olho aparece com menos de 70% da largura do outro, o rosto está virado
# e o olho do fundo distorce a medida: vale só o olho mais visível.
EYE_WIDTH_RATIO_FOR_SINGLE_EYE = 0.7

# Regiões de luminância, em larguras do olho: a do olho e a da bochecha logo abaixo dele.
# Óculos escuros deixam a região do olho bem mais escura que a bochecha (vision/visibility.py).
EYE_PATCH_HEIGHT = 0.5
CHEEK_OFFSET = 1.0
CHEEK_PATCH = (0.8, 0.4)
GLARE_LEVEL = 250

# YuNet dá só o centro de cada olho. Largura da caixa do olho ≈ 0,48 da distância entre os olhos
# (proporção típica do rosto adulto) x 1,2 de margem, como no recorte a partir dos cantos. A ajustar.
YUNET_EYE_WIDTH_FACTOR = 0.48
YUNET_EYE_BOX_FACTOR = 0.57
# YuNet detecta rostos de ~10 a ~300 px: o quadro é reduzido para essa largura só na detecção.
YUNET_DETECTION_WIDTH = 320


def combine_eyes(left, right, width_left: float, width_right: float):
    """Média dos dois olhos, ou só o mais visível quando a cabeça está virada."""
    if left is None or right is None:
        return left if right is None else right
    widest = max(width_left, width_right)
    narrowest = min(width_left, width_right)
    if widest > 0 and narrowest / widest < EYE_WIDTH_RATIO_FOR_SINGLE_EYE:
        return left if width_left >= width_right else right
    return (left + right) / 2.0


@dataclass
class FaceMetrics:
    timestamp: float
    face_found: bool
    ear_left: float | None = None
    ear_right: float | None = None
    eye_width_left: float = 0.0
    eye_width_right: float = 0.0
    blink_score: float | None = None  # blendshape eyeBlink do MediaPipe: 0 aberto, 1 fechado
    eye_open_prob: float | None = None  # classificador OCEC: 1 aberto, 0 fechado
    jaw_open: float | None = None
    mar: float | None = None
    pitch: float | None = None
    yaw: float | None = None
    roll: float | None = None
    eye_distance_px: float | None = None
    eye_points: np.ndarray | None = None
    # Íris em relação ao centro do olho, em meias larguras do olho: + = direita e para baixo na imagem.
    gaze_x: float | None = None
    gaze_y: float | None = None
    iris_diameter_px: float | None = None
    pupil_ratio: float | None = None  # só com câmera infravermelha e medida de boa qualidade
    pupil_quality: str | None = None
    eye_luminance: float | None = None  # média de cinza (0 a 255) na região dos olhos
    cheek_luminance: float | None = None
    eye_contrast: float | None = None  # desvio-padrão do cinza na região dos olhos
    glare_fraction: float | None = None  # fração de pixels saturados na região dos olhos (reflexo em óculos)
    eyes_in_frame: bool = True  # pelo menos um olho inteiro dentro da imagem
    infrared: bool = False
    ambient_lux: float | None = None  # luz ambiente informada pela câmera, quando ela informa
    face_box: tuple | None = None  # (x1, y1, x2, y2) em pixels
    ear_points: np.ndarray | None = None  # lados do rosto na altura das orelhas, em pixels

    @property
    def ear(self) -> float | None:
        return combine_eyes(self.ear_left, self.ear_right, self.eye_width_left, self.eye_width_right)


def _distance(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.linalg.norm(a - b))


def eye_aspect_ratio(points: np.ndarray, indices: tuple) -> tuple[float | None, float]:
    p1, p2, p3, p4, p5, p6 = (points[i] for i in indices)
    width = _distance(p1, p4)
    if width < 1e-6:
        return None, 0.0
    return (_distance(p2, p6) + _distance(p3, p5)) / (2.0 * width), width


def rotation_to_euler(matrix: np.ndarray) -> tuple[float, float, float]:
    """Pitch, yaw e roll em graus a partir da matriz de transformação facial (4x4)."""
    r = matrix[:3, :3]
    sy = math.hypot(r[2, 1], r[2, 2])
    pitch = math.degrees(math.atan2(r[2, 1], r[2, 2]))
    yaw = math.degrees(math.atan2(-r[2, 0], sy))
    roll = math.degrees(math.atan2(r[1, 0], r[0, 0]))
    return pitch, yaw, roll


def _patch(gray: np.ndarray, center, width: float, height: float) -> np.ndarray | None:
    frame_height, frame_width = gray.shape[:2]
    x1 = max(0, int(round(center[0] - width / 2)))
    x2 = min(frame_width, int(round(center[0] + width / 2)))
    y1 = max(0, int(round(center[1] - height / 2)))
    y2 = min(frame_height, int(round(center[1] + height / 2)))
    if x2 - x1 < 3 or y2 - y1 < 2:
        return None
    return gray[y1:y2, x1:x2]


def _mean_of(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def eye_region(gray: np.ndarray, center, width: float, down: np.ndarray) -> dict:
    """Luminância, contraste e reflexo na região do olho, e luminância da bochecha logo abaixo."""
    eye = _patch(gray, center, width, width * EYE_PATCH_HEIGHT)
    cheek = _patch(gray, np.asarray(center) + down * width * CHEEK_OFFSET, width * CHEEK_PATCH[0], width * CHEEK_PATCH[1])
    return {
        "eye_luminance": float(eye.mean()) if eye is not None else None,
        "eye_contrast": float(eye.std()) if eye is not None else None,
        "glare_fraction": float((eye >= GLARE_LEVEL).mean()) if eye is not None else None,
        "cheek_luminance": float(cheek.mean()) if cheek is not None else None,
    }


def _inside(points: np.ndarray, indices, width: int, height: int) -> bool:
    return all(0 <= points[i][0] < width and 0 <= points[i][1] < height for i in indices)


def _eye_features(points, gray, eye, iris, iris_center, infrared: bool, eye_open: bool) -> dict:
    corner_a, corner_b = points[eye[0]], points[eye[3]]
    if corner_b[0] < corner_a[0]:
        corner_a, corner_b = corner_b, corner_a  # eixo sempre para a direita da imagem
    width = _distance(corner_a, corner_b)
    right = (corner_b - corner_a) / width
    down = np.array([-right[1], right[0]], dtype=np.float32)
    center = (corner_a + corner_b) / 2.0
    offset = points[iris_center] - center
    iris_diameter = (_distance(points[iris[0]], points[iris[2]]) + _distance(points[iris[1]], points[iris[3]])) / 2.0

    features = eye_region(gray, center, width, down)
    features.update(
        gaze_x=float(offset @ right) / (width / 2.0),
        gaze_y=float(offset @ down) / (width / 2.0),
        iris_diameter_px=iris_diameter,
        pupil_ratio=None,
        pupil_quality="camera_rgb",
    )
    if infrared:
        if eye_open:
            features["pupil_ratio"], features["pupil_quality"] = measure_pupil(gray, points[iris_center], iris_diameter)
        else:
            features["pupil_quality"] = "olho_fechando"
    return features


class FaceAnalyzer:
    supports_calibration = True
    name = "MediaPipe"

    def __init__(self, model_path: Path = DEFAULT_MODEL, classifier: EyeStateClassifier | None = None,
                 infrared: str = "auto"):
        try:
            import mediapipe as mp
            from mediapipe.tasks import python as mp_python
            from mediapipe.tasks.python import vision as mp_vision
        except ImportError as exc:
            raise RuntimeError(f"MediaPipe não está instalado ({exc})") from exc

        model_path = Path(model_path)
        if not model_path.is_file():
            raise RuntimeError(f"Modelo do MediaPipe não encontrado em {model_path}. Baixe de {MODEL_URL}")

        self._mp = mp
        self._classifier = classifier
        self._infrared = InfraredDetector(infrared)
        options = mp_vision.FaceLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=str(model_path)),
            running_mode=mp_vision.RunningMode.VIDEO,
            num_faces=1,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            min_tracking_confidence=0.5,
            output_face_blendshapes=True,
            output_facial_transformation_matrixes=True,
        )
        self._landmarker = mp_vision.FaceLandmarker.create_from_options(options)
        self._last_timestamp_ms = -1
        logger.info("MediaPipe %s carregado (%s)%s.", mp.__version__, model_path.name,
                    " com classificador de olho" if classifier else "")

    def analyze(self, frame_bgr: np.ndarray, timestamp: float | None = None) -> FaceMetrics:
        """timestamp em segundos: relógio monotônico ao vivo, ou tempo do quadro num arquivo de vídeo."""
        timestamp = time.monotonic() if timestamp is None else timestamp
        # O modo VIDEO exige carimbos de tempo estritamente crescentes.
        timestamp_ms = max(int(timestamp * 1000), self._last_timestamp_ms + 1)
        self._last_timestamp_ms = timestamp_ms
        infrared = self._infrared.update(frame_bgr)

        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
        result = self._landmarker.detect_for_video(image, timestamp_ms)
        if not result.face_landmarks:
            return FaceMetrics(timestamp=timestamp, face_found=False, infrared=infrared)

        height, width = frame_bgr.shape[:2]
        points = np.array([(lm.x * width, lm.y * height) for lm in result.face_landmarks[0]], dtype=np.float32)
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)

        # Olho com algum ponto fora da imagem não é medido: o MediaPipe inventa a forma dele.
        right_in = _inside(points, RIGHT_EYE, width, height)
        left_in = _inside(points, LEFT_EYE, width, height)
        ear_right, width_right = eye_aspect_ratio(points, RIGHT_EYE) if right_in else (None, 0.0)
        ear_left, width_left = eye_aspect_ratio(points, LEFT_EYE) if left_in else (None, 0.0)

        mouth_left, lip_top, mouth_right, lip_bottom = (points[i] for i in MOUTH)
        mouth_width = _distance(mouth_left, mouth_right)
        mar = _distance(lip_top, lip_bottom) / mouth_width if mouth_width > 1e-6 else None

        scores = {c.category_name: c.score for c in result.face_blendshapes[0]} if result.face_blendshapes else {}
        blink_values = [scores[name] for name in ("eyeBlinkLeft", "eyeBlinkRight") if name in scores]
        blink_score = sum(blink_values) / len(blink_values) if blink_values and (right_in or left_in) else None

        pitch = yaw = roll = None
        if result.facial_transformation_matrixes:
            pitch, yaw, roll = rotation_to_euler(np.asarray(result.facial_transformation_matrixes[0]))

        eye_open_prob = None
        if self._classifier is not None and (right_in or left_in):
            right_prob, left_prob = self._classifier.open_probabilities(frame_bgr, [
                eye_box_from_corners(points[RIGHT_EYE[0]], points[RIGHT_EYE[3]]) if right_in else (0.0, 0.0, 0.0),
                eye_box_from_corners(points[LEFT_EYE[0]], points[LEFT_EYE[3]]) if left_in else (0.0, 0.0, 0.0),
            ])
            eye_open_prob = combine_eyes(left_prob, right_prob, width_left, width_right)

        eye_open = blink_score is None or blink_score < 0.5
        right = _eye_features(points, gray, RIGHT_EYE, RIGHT_IRIS, RIGHT_IRIS_CENTER, infrared, eye_open) if right_in else {}
        left = _eye_features(points, gray, LEFT_EYE, LEFT_IRIS, LEFT_IRIS_CENTER, infrared, eye_open) if left_in else {}

        def both(key):
            return combine_eyes(left.get(key), right.get(key), width_left, width_right)

        qualities = [side.get("pupil_quality") for side in (right, left) if side]
        return FaceMetrics(
            timestamp=timestamp,
            face_found=True,
            ear_left=ear_left,
            ear_right=ear_right,
            eye_width_left=width_left,
            eye_width_right=width_right,
            blink_score=blink_score,
            eye_open_prob=eye_open_prob,
            jaw_open=scores.get("jawOpen"),
            mar=mar,
            pitch=pitch,
            yaw=yaw,
            roll=roll,
            eye_distance_px=_distance(points[RIGHT_EYE[0]], points[LEFT_EYE[3]]),
            eye_points=points[list(RIGHT_EYE) + list(LEFT_EYE)],
            gaze_x=both("gaze_x"),
            gaze_y=both("gaze_y"),
            iris_diameter_px=both("iris_diameter_px"),
            pupil_ratio=both("pupil_ratio"),
            pupil_quality="ok" if "ok" in qualities else (qualities[0] if qualities else "olhos_fora_do_quadro"),
            eye_luminance=_mean_of([right.get("eye_luminance"), left.get("eye_luminance")]),
            cheek_luminance=_mean_of([right.get("cheek_luminance"), left.get("cheek_luminance")]),
            eye_contrast=_mean_of([right.get("eye_contrast"), left.get("eye_contrast")]),
            glare_fraction=_mean_of([right.get("glare_fraction"), left.get("glare_fraction")]),
            eyes_in_frame=right_in or left_in,
            infrared=infrared,
            face_box=(float(points[:, 0].min()), float(points[:, 1].min()),
                      float(points[:, 0].max()), float(points[:, 1].max())),
            ear_points=points[list(FACE_SIDES)],
        )

    def close(self) -> None:
        self._landmarker.close()


class YuNetFaceAnalyzer:
    """Modo alternativo sem MediaPipe: rosto e olhos pelo YuNet; olho aberto ou fechado só pelo classificador.
    Detecta olho fechado e microssono. Não mede pose da cabeça, bocejo, íris nem calibra o EAR."""

    supports_calibration = False
    name = "YuNet"

    def __init__(self, classifier: EyeStateClassifier, model_path: Path = YUNET_MODEL, score_threshold: float = 0.8,
                 infrared: str = "auto"):
        model_path = Path(model_path)
        if not model_path.is_file():
            raise RuntimeError(f"Modelo YuNet não encontrado em {model_path}.")
        if not hasattr(cv2, "FaceDetectorYN"):
            raise RuntimeError("Esta versão do OpenCV não tem cv2.FaceDetectorYN.")
        self._detector = cv2.FaceDetectorYN.create(str(model_path), "", (YUNET_DETECTION_WIDTH, 240),
                                                   score_threshold, 0.3, 5000)
        self._input_size = None
        self._classifier = classifier
        self._infrared = InfraredDetector(infrared)
        logger.info("Modo alternativo: YuNet (%s) com classificador de olho.", model_path.name)

    def analyze(self, frame_bgr: np.ndarray, timestamp: float | None = None) -> FaceMetrics:
        timestamp = time.monotonic() if timestamp is None else timestamp
        infrared = self._infrared.update(frame_bgr)
        height, width = frame_bgr.shape[:2]
        scale = min(1.0, YUNET_DETECTION_WIDTH / width)
        small = cv2.resize(frame_bgr, (int(width * scale), int(height * scale))) if scale < 1.0 else frame_bgr
        size = (small.shape[1], small.shape[0])
        if self._input_size != size:
            self._detector.setInputSize(size)
            self._input_size = size

        _, faces = self._detector.detect(small)
        if faces is None or len(faces) == 0:
            return FaceMetrics(timestamp=timestamp, face_found=False, infrared=infrared)

        face = max(faces, key=lambda f: f[2] * f[3]) / scale  # maior rosto = motorista
        right_eye = face[4:6].astype(np.float32)
        left_eye = face[6:8].astype(np.float32)
        distance = _distance(right_eye, left_eye)
        box_width = distance * YUNET_EYE_BOX_FACTOR
        right_prob, left_prob = self._classifier.open_probabilities(frame_bgr, [
            (float(right_eye[0]), float(right_eye[1]), box_width),
            (float(left_eye[0]), float(left_eye[1]), box_width),
        ])

        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        axis = (left_eye - right_eye) / max(distance, 1e-6)
        if axis[0] < 0:
            axis = -axis
        down = np.array([-axis[1], axis[0]], dtype=np.float32)
        eye_width = distance * YUNET_EYE_WIDTH_FACTOR
        regions = [eye_region(gray, center, eye_width, down) for center in (right_eye, left_eye)]
        in_frame = any(0 <= c[0] < width and 0 <= c[1] < height for c in (right_eye, left_eye))
        return FaceMetrics(
            timestamp=timestamp,
            face_found=True,
            eye_open_prob=combine_eyes(left_prob, right_prob, 1.0, 1.0),
            eye_distance_px=distance,
            eye_points=np.array([right_eye, left_eye], dtype=np.float32),
            pupil_quality="sem_pontos_da_iris",
            eye_luminance=_mean_of([r["eye_luminance"] for r in regions]),
            cheek_luminance=_mean_of([r["cheek_luminance"] for r in regions]),
            eye_contrast=_mean_of([r["eye_contrast"] for r in regions]),
            glare_fraction=_mean_of([r["glare_fraction"] for r in regions]),
            eyes_in_frame=in_frame,
            infrared=infrared,
            face_box=(float(face[0]), float(face[1]), float(face[0] + face[2]), float(face[1] + face[3])),
            ear_points=np.array([(face[0], (right_eye[1] + left_eye[1]) / 2),
                                 (face[0] + face[2], (right_eye[1] + left_eye[1]) / 2)], dtype=np.float32),
        )

    def close(self) -> None:
        pass


def create_face_analyzer(backend: str = "auto", use_classifier: bool = True, infrared: str = "auto"):
    """backend: auto (MediaPipe e, se faltar, YuNet), mediapipe ou yunet. infrared: auto, sim ou nao."""
    classifier = None
    if use_classifier or backend == "yunet":
        try:
            classifier = EyeStateClassifier()
        except (RuntimeError, cv2.error) as exc:
            logger.warning("Classificador de olho indisponível (%s); seguindo sem a segunda opinião.", exc)

    if backend in ("auto", "mediapipe"):
        try:
            return FaceAnalyzer(classifier=classifier if use_classifier else None, infrared=infrared)
        except RuntimeError as exc:
            if backend == "mediapipe" or classifier is None:
                raise
            logger.warning("MediaPipe indisponível (%s). Usando o modo alternativo YuNet: detecta olhos "
                           "fechados e microssono, sem pose da cabeça, bocejo nem calibração individual.", exc)
    if classifier is None:
        raise RuntimeError("O modo YuNet precisa do classificador de olho (vision/models/ocec_s.onnx).")
    return YuNetFaceAnalyzer(classifier, infrared=infrared)
