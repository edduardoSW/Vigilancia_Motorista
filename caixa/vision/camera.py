"""Fontes de vídeo: webcam/arquivo/URL pelo OpenCV ou Pi Camera Module pelo picamera2."""
from __future__ import annotations

import logging
import time
from collections import deque
from pathlib import Path

import cv2

logger = logging.getLogger("drivesafe.camera")

# O picamera2 informa a luz estimada da cena ("Lux"). Em algumas câmeras o valor vem fixo (issue #824 do
# picamera2): se não mudar nada em ~10 s de quadros, é tratado como indisponível.
LUX_CHECK_FRAMES = 300
# Câmera automática: índices testados em ordem. Índice que não existe responde em ~0,05 s (medido em 14/09).
AUTO_CAMERA_INDICES = range(6)
AUTO_CAMERA_READS = 10


class CameraIndisponivel(RuntimeError):
    """Nenhuma câmera abriu ou mandou imagem."""


class OpenCVCamera:
    """Índice de webcam (0, 1...), caminho (/dev/video0, video.mp4) ou URL (rtsp://...)."""

    def __init__(self, source: str, width: int = 640, height: int = 480, avisar: bool = True):
        self._source = int(source) if str(source).isdigit() else source
        self._size = (width, height)
        self._cap = None
        self._avisar = avisar
        # Arquivo de vídeo tem fim: quando acaba, o monitoramento termina em vez de reabrir e recomeçar.
        self._arquivo = isinstance(self._source, str) and Path(self._source).is_file()
        self.terminou = False
        self.aberta = False
        self.open()

    def describe(self) -> str:
        return f"OpenCV {self._source!r}"

    def open(self) -> bool:
        self.release()
        self._cap = cv2.VideoCapture(self._source)
        self.aberta = self._cap.isOpened()
        if not self.aberta:
            if self._avisar:
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
        ok, frame = self._cap.read()
        if (not ok or frame is None) and self._arquivo:
            self.terminou = True
        return ok, frame

    def ambient_lux(self) -> float | None:
        return None  # webcams pelo OpenCV não informam a luz da cena de forma confiável

    def release(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None


class Picamera2Camera:
    """Pi Camera Module (libcamera). Precisa do pacote do sistema: sudo apt install python3-picamera2."""

    terminou = False  # câmera ao vivo não tem fim
    aberta = False

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
            self.aberta = False
            return False
        self._camera = camera
        self.aberta = True
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


def find_camera(width: int = 640, height: int = 480, indices=AUTO_CAMERA_INDICES, factory=None,
                leituras: int = AUTO_CAMERA_READS, pausa: float = 0.05):
    """Primeira webcam que abre e manda imagem. Aberta mas sem imagem (em uso por outro programa) passa para a próxima."""
    factory = factory or OpenCVCamera
    for index in indices:
        camera = factory(str(index), width, height, avisar=False)
        if camera.aberta:
            for _ in range(leituras):
                ok, frame = camera.read()
                if ok and frame is not None:
                    logger.info("Câmera encontrada automaticamente: índice %s.", index)
                    return camera
                if pausa:
                    time.sleep(pausa)
        camera.release()
    raise CameraIndisponivel(f"Nenhuma câmera respondeu (índices {indices[0]} a {indices[-1]}). Confira se ela está "
                             "conectada e se outro programa (Teams, Zoom, navegador) não está usando.")


def open_camera(source: str, width: int = 640, height: int = 480):
    if str(source).strip().lower() == "picamera2":
        return Picamera2Camera(width, height)
    if str(source).strip().lower() == "auto":
        return find_camera(width, height)
    return OpenCVCamera(source, width, height)
