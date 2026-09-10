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

Os modelos rodam numa thread separada, algumas vezes por segundo, para não derrubar o fps da medida do rosto.
Nenhuma imagem é guardada: só o estado, a duração e a confiança.
"""
from __future__ import annotations

import logging
import math
import platform
import statistics
import threading
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from vision.drowsiness import DetectedEvent

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
PHONE_EAR_RADIUS_FACES = 0.7
HAND_ON_PHONE_MARGIN = 0.25
HAND_KEY_POINTS = (0, 4, 5, 8, 9, 12, 13, 16, 17, 20)  # punho, pontas dos dedos e articulações da base
MIN_HAND_POINTS = 3
# Evidência vale por 1,5 s. Celular só conta com pelo menos 2 detecções em 2 s: um objeto parecido num quadro não basta.
EVIDENCE_S = 1.5
CONFIRM_WINDOW_S = 2.0
CONFIRM_HITS = 2
PHONE_MEMORY_S = 10.0  # mão na orelha conta como celular se o aparelho apareceu há pouco
# O model card do Hand Landmarker põe fora do escopo a mão segurando objetos: os pontos da mão podem falhar justo
# com o celular na mão. Por isso o aparelho se mexendo também conta. Celular preso num suporte fica parado em
# relação à câmera (os dois estão presos ao veículo) e não conta. Hipótese: 8% da largura do rosto em 2 s.
PHONE_MOVE_FACES = 0.08
STATE_GAP_S = 1.0
LOOK_DOWN_PITCH_DEG = 15.0
LOOK_DOWN_GAZE = 0.25
REFERENCE_S = 30.0
REFERENCE_STEP_S = 0.5
TALKING_WINDOW_S = 2.0
TALKING_MAR_STD = 0.02  # boca mexendo: hipótese para "falando", a validar

LOOKING_ALERT_S = 2.0
EAR_ALERT_S = 3.0
HAND_ALERT_S = 3.0
EVENT_COOLDOWN_S = 120.0
ALARM_COOLDOWN_S = 30.0


def default_phone_model() -> Path:
    """int8 é mais rápido em ARM (Raspberry Pi, Apple Silicon); em x86 o float16 foi mais rápido (73 x 106 ms)."""
    return PHONE_MODEL_INT8 if platform.machine().lower() in ("aarch64", "arm64", "armv8l") else PHONE_MODEL_FLOAT16


@dataclass
class PhoneObservation:
    timestamp: float
    phones: list  # (x1, y1, x2, y2, confiança) em pixels do quadro
    hands: list  # arrays (21, 2) em pixels do quadro


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
    return any(math.hypot(center_x - ear[0], center_y - ear[1]) <= PHONE_EAR_RADIUS_FACES * face_width for ear in ears)


class PhoneDetector:
    """Roda os modelos num quadro e devolve caixas de celular e pontos das mãos."""

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
        self._next_detection = -math.inf
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._job = None
        self._result = None
        self._busy = False
        self._failures = 0
        self._phone_hits = deque()
        self._phone_centers = deque()  # (t, x, y, escala) de cada celular detectado
        self._last = dict.fromkeys(("phone", "hand_on_phone", "hand_ear", "phone_ear"), -math.inf)
        self._pitch_reference = deque()
        self._gaze_reference = deque()
        self._next_reference = -math.inf
        self._mar = deque()
        self._state = "sem_celular"
        self._episode_since = self._episode_last = None
        self._looking_since = self._looking_last = None
        self._last_event_at = {}
        self._last_alarm_at = -math.inf
        self._thread = None
        if background:
            self._thread = threading.Thread(target=self._worker, name="drivesafe-celular", daemon=True)
            self._thread.start()

    def update(self, metrics, frame=None, moving: bool = True) -> PhoneAssessment:
        t = metrics.timestamp
        face_box = getattr(metrics, "face_box", None) if metrics.face_found else None
        if frame is not None and t >= self._next_detection:
            self._next_detection = t + self.every_s
            if self.background:
                self._submit(frame, t, face_box)
            else:
                self.observe(self._run(frame, t, face_box), metrics)
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
        phones = [phone for phone in observation.phones if phone[4] >= PHONE_MIN_SCORE]
        if phones:
            self._last["phone"] = t
            self._phone_hits.append(t)
        box = getattr(metrics, "face_box", None) if metrics.face_found else None
        ears = getattr(metrics, "ear_points", None) if box is not None else None
        face_width = box[2] - box[0] if box is not None else None
        for phone in phones:
            self._phone_centers.append((t, (phone[0] + phone[2]) / 2.0, (phone[1] + phone[3]) / 2.0,
                                        face_width or (phone[2] - phone[0])))
            if any(hand_touches_phone(hand, phone) for hand in observation.hands):
                self._last["hand_on_phone"] = t
            if ears is not None and phone_near_ear(phone, ears, face_width):
                self._last["phone_ear"] = t
        if ears is not None and any(hand_near_ear(hand, ears, face_width) for hand in observation.hands):
            self._last["hand_ear"] = t

    def close(self) -> None:
        self._stop.set()
        self._wake.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        self.detector.close()

    def _assess(self, t: float, metrics, moving: bool) -> PhoneAssessment:
        while self._phone_hits and self._phone_hits[0] < t - CONFIRM_WINDOW_S:
            self._phone_hits.popleft()
        while self._phone_centers and self._phone_centers[0][0] < t - CONFIRM_WINDOW_S:
            self._phone_centers.popleft()
        confirmed = len(self._phone_hits) >= CONFIRM_HITS

        def seen(key, window=EVIDENCE_S):
            return t - self._last[key] <= window

        in_hand = confirmed and (seen("hand_on_phone") or self._phone_moving())
        at_ear = (confirmed and seen("phone_ear")) or (seen("hand_ear") and (seen("phone", PHONE_MEMORY_S) or self._talking()))
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

        episode = t - self._episode_since if state != "sem_celular" else 0.0
        looking_for = t - self._looking_since if state == "olhando_celular" else 0.0
        observation = self.last_observation
        recent = observation is not None and t - observation.timestamp <= EVIDENCE_S
        phones = observation.phones if recent else []
        assessment = PhoneAssessment(state=state, duration=round(episode, 2),
                                     phone_score=max(p[4] for p in phones) if phones else None,
                                     hands=len(observation.hands) if recent else 0, boxes=[p[:4] for p in phones])
        if not moving or state == "sem_celular":
            return assessment

        details = {"estado": state, "confianca_celular": None if assessment.phone_score is None else round(assessment.phone_score, 2),
                   "maos_detectadas": assessment.hands, "olhando_para_baixo": looking}
        if state == "olhando_celular" and looking_for >= LOOKING_ALERT_S:
            self._raise(t, assessment, 2, "olhos_no_celular", "olhando_celular", 4, looking_for, details, alarm=True)
        elif state == "celular_no_ouvido" and episode >= EAR_ALERT_S:
            self._raise(t, assessment, 2, "celular_no_ouvido", "celular_no_ouvido", 3, episode, details, alarm=True)
        elif state in ("celular_na_mao", "olhando_celular") and episode >= HAND_ALERT_S:
            self._raise(t, assessment, 1, "celular_na_mao", "celular_na_mao", 3, episode, details, alarm=False)
        return assessment

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
        mar = getattr(metrics, "mar", None)
        if mar is not None:
            self._mar.append((t, mar))
        while self._mar and self._mar[0][0] < t - TALKING_WINDOW_S:
            self._mar.popleft()
        in_use = self._episode_last is not None and t - self._episode_last <= 5.0
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

    def _talking(self) -> bool:
        values = [value for _, value in self._mar]
        return len(values) >= 15 and statistics.pstdev(values) >= TALKING_MAR_STD

    def _submit(self, frame, t: float, face_box) -> None:
        with self._lock:
            if self._busy:
                return  # ainda processando o anterior: pula este quadro
            self._job, self._busy = (frame.copy(), t, face_box), True
        self._wake.set()

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

    def _run(self, frame, t: float, face_box) -> PhoneObservation | None:
        try:
            return self.detector.detect(frame, t, face_box)
        except Exception:
            self._failures += 1
            if self._failures in (1, 100):
                logger.exception("Falha na detecção de celular (%d falhas).", self._failures)
            return None
