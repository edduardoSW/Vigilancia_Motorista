"""Alarme sonoro multiplataforma: Windows, macOS, Linux e Raspberry Pi (alto-falante ou buzzer)."""
from __future__ import annotations

import logging
import math
import shutil
import subprocess
import sys
import threading
import wave
from array import array
from pathlib import Path

logger = logging.getLogger("drivesafe.alarm")

SAMPLE_RATE = 22050
AMPLITUDE = 0.8 * 32767
# Mesmo padrão da sirene original: 5 ciclos de 2000 Hz e 1000 Hz, 150 ms cada, com 50 ms de pausa.
SIREN_CYCLES = 5
TONE_SECONDS = 0.15
GAP_SECONDS = 0.05

LINUX_PLAYERS = (
    ("aplay", ["aplay", "-q"]),
    ("paplay", ["paplay"]),
    ("pw-play", ["pw-play"]),
    ("ffplay", ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"]),
)


def write_siren_wav(path: Path) -> None:
    samples = array("h")
    tone_frames = int(SAMPLE_RATE * TONE_SECONDS)
    gap = [0] * int(SAMPLE_RATE * GAP_SECONDS)
    for _ in range(SIREN_CYCLES):
        for frequency in (2000, 1000):
            step = 2 * math.pi * frequency / SAMPLE_RATE
            samples.extend(int(AMPLITUDE * math.sin(step * i)) for i in range(tone_frames))
            samples.extend(gap)
    if sys.byteorder == "big":
        samples.byteswap()
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(samples.tobytes())


class Alarm:
    """Toca a sirene em segundo plano sem travar a leitura da câmera."""

    def __init__(self, sound_path: Path, buzzer_pin: int | None = None, muted: bool = False):
        self.muted = muted
        self._playing = False
        self._lock = threading.Lock()
        self._sound_path = Path(sound_path)
        self._buzzer = None
        self._command = None

        if muted:
            logger.info("Alarme sonoro desligado (--mute).")
            return

        if buzzer_pin is not None:
            try:
                from gpiozero import Buzzer  # vem instalado no Raspberry Pi OS
            except ImportError as exc:
                raise RuntimeError(
                    "Buzzer pedido, mas gpiozero não está disponível. No Raspberry Pi OS crie o venv com "
                    "--system-site-packages ou rode: pip install gpiozero lgpio"
                ) from exc
            self._buzzer = Buzzer(buzzer_pin)
            logger.info("Alarme pelo buzzer no GPIO %s.", buzzer_pin)
            return

        write_siren_wav(self._sound_path)
        self._command = self._find_player()

    @property
    def is_playing(self) -> bool:
        return self._playing

    def _find_player(self):
        if sys.platform == "win32":
            logger.info("Alarme pelo alto-falante (winsound).")
            return None
        if sys.platform == "darwin":
            logger.info("Alarme pelo alto-falante (afplay).")
            return ["afplay", str(self._sound_path)]
        for name, command in LINUX_PLAYERS:
            if shutil.which(name):
                logger.info("Alarme pelo alto-falante (%s).", name)
                return command + [str(self._sound_path)]
        logger.warning(
            "Nenhum player de áudio encontrado (aplay, paplay, pw-play, ffplay). "
            "No Raspberry Pi OS instale com: sudo apt install alsa-utils. Usando só o bipe do terminal."
        )
        return None

    def trigger(self) -> None:
        if self.muted:
            return
        with self._lock:
            if self._playing:
                return
            self._playing = True
        threading.Thread(target=self._play, name="drivesafe-alarm", daemon=True).start()

    def _play(self) -> None:
        try:
            if self._buzzer is not None:
                self._buzzer.beep(on_time=TONE_SECONDS, off_time=GAP_SECONDS, n=SIREN_CYCLES * 2, background=False)
            elif sys.platform == "win32":
                import winsound

                winsound.PlaySound(str(self._sound_path), winsound.SND_FILENAME)
            elif self._command:
                subprocess.run(self._command, check=True, timeout=10,
                               stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            else:
                sys.stdout.write("\a")
                sys.stdout.flush()
        except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
            stderr = getattr(exc, "stderr", None)
            detail = stderr.decode("utf-8", "replace").strip() if stderr else str(exc)
            logger.warning("Falha ao tocar o alarme: %s", detail)
            sys.stdout.write("\a")
            sys.stdout.flush()
        finally:
            with self._lock:
                self._playing = False
