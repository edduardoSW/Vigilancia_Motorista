"""Fontes de vídeo: webcam/arquivo/URL pelo OpenCV ou Pi Camera Module pelo picamera2."""
from __future__ import annotations

import logging
from collections import deque

import cv2

logger = logging.getLogger("drivesafe.camera")

# O picamera2 informa a luz estimada da cena ("Lux"). Em algumas câmeras o valor vem fixo (issue #824 do
# picamera2): se não mudar nada em ~10 s de quadros, é tratado como indisponível.
LUX_CHECK_FRAMES = 300


class OpenCVCamera:
    """Índice de webcam (0, 1...), caminho (/dev/video0, video.mp4) ou URL (rtsp://...)."""

    def __init__(self, source: str, width: int = 640, height: int = 480):
        self._source = int(source) if str(source).isdigit() else source
        self._size = (width, height)
        self._cap = None
        self.open()

    def describe(self) -> str:
        return f"OpenCV {self._source!r}"

    def open(self) -> bool:
        self.release()
        self._cap = cv2.VideoCapture(self._source)
        if not self._cap.isOpened():
            logger.error("Não foi possível abrir a câmera %s.", self.describe())
            return False
        if isinstance(self._source, int):
            # Resolução menor deixa a detecção viável no Raspberry Pi.
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._size[0])
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._size[1])
        logger.info("Câmera aberta: %s.", self.describe())
        return True

    def read(self):
        if self._cap is None or not self._cap.isOpened():
            return False, None
        return self._cap.read()

    def ambient_lux(self) -> float | None:
        return None  # webcams pelo OpenCV não informam a luz da cena de forma confiável

    def release(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None


class Picamera2Camera:
    """Pi Camera Module (libcamera). Precisa do pacote do sistema: sudo apt install python3-picamera2."""

    def __init__(self, width: int = 640, height: int = 480):
        try:
            from picamera2 import Picamera2
        except ImportError as exc:
            raise RuntimeError(
                "picamera2 não encontrado. No Raspberry Pi OS: sudo apt install python3-picamera2 "
                "e crie o venv com --system-site-packages."
            ) from exc
        self._factory = Picamera2
        self._size = (width, height)
        self._camera = None
        self._lux = deque(maxlen=LUX_CHECK_FRAMES)
        self.open()

    def describe(self) -> str:
        return "Pi Camera Module (picamera2)"

    def open(self) -> bool:
        self.release()
        try:
            camera = self._factory()
            # "RGB888" no picamera2 entrega os pixels na ordem B, G, R, que é a do OpenCV.
            camera.configure(camera.create_video_configuration(main={"format": "RGB888", "size": self._size}))
            camera.start()
        except Exception as exc:
            logger.error("Não foi possível abrir a %s: %s", self.describe(), exc)
            return False
        self._camera = camera
        logger.info("Câmera aberta: %s.", self.describe())
        return True

    def read(self):
        if self._camera is None:
            return False, None
        try:
            request = self._camera.capture_request()
            try:
                frame = request.make_array("main")
                lux = request.get_metadata().get("Lux")
            finally:
                request.release()
        except Exception as exc:
            logger.warning("Falha ao capturar da %s: %s", self.describe(), exc)
            return False, None
        if lux is not None:
            self._lux.append(float(lux))
        return True, frame

    def ambient_lux(self) -> float | None:
        if not self._lux:
            return None
        if len(self._lux) == LUX_CHECK_FRAMES and max(self._lux) == min(self._lux):
            return None
        return self._lux[-1]

    def release(self) -> None:
        if self._camera is not None:
            try:
                self._camera.stop()
                self._camera.close()
            except Exception as exc:
                logger.warning("Falha ao fechar a %s: %s", self.describe(), exc)
            self._camera = None


def open_camera(source: str, width: int = 640, height: int = 480):
    if str(source).lower() == "picamera2":
        return Picamera2Camera(width, height)
    return OpenCVCamera(source, width, height)
