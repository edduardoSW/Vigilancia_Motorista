"""Modo teste do app (só equipe/admin): monitoramento ao vivo neste computador e análise de vídeos enviados.

- O vídeo ao vivo não é gravado: cada quadro vira JPEG em memória e é trocado pelo próximo.
- O vídeo enviado para análise é apagado ao terminar (ficam só as planilhas de medidas), salvo DRIVESAFE_MANTER_VIDEOS=1.
- Precisa das dependências do dispositivo (requirements-device.txt) no mesmo ambiente do servidor.
"""
from __future__ import annotations

import csv
import importlib.util
import io
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
from collections import deque
from datetime import datetime
from pathlib import Path

from backend import config
from backend.database import utcnow
from backend.live import hub

logger = logging.getLogger("drivesafe.teste")

FRAME_EVERY_S = 0.1
STATE_EVERY_S = 0.25
JPEG_QUALITY = 70
CAMERA_OPEN_TIMEOUT_S = 8.0
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".m4v"}
PROGRESS_LINE = re.compile(r"^\s*(\d{1,3})%\s*$")
WINDOW_KEYS = ("perclos_3min", "piscadas_por_min", "duracao_mediana_ms", "avr_fechamento_ms",
               "fechamentos_longos_5min", "cabeceios_10min", "bocejos_10min")


def availability() -> tuple[bool, str | None]:
    missing = [name for name in ("mediapipe", "cv2") if importlib.util.find_spec(name) is None]
    if missing:
        return False, ("Este servidor não tem as dependências do dispositivo (" + ", ".join(missing)
                       + "). Para testar aqui: pip install -r requirements-device.txt")
    if not (Path(config.BASE_DIR) / "vision" / "models" / "face_landmarker.task").is_file():
        return False, "Modelo do rosto não encontrado em vision/models."
    return True, None


def _round(value, digits: int = 3):
    return None if value is None else round(float(value), digits)


class LiveTestSession:
    def __init__(self):
        self._lock = threading.Lock()
        self._frame_ready = threading.Condition()
        self.thread: threading.Thread | None = None
        self.monitor = None
        self.running = False
        self.started_at = None
        self.config: dict | None = None
        self.device_id: int | None = None
        self.error: str | None = None
        self.last: dict | None = None
        self.jpeg: bytes | None = None
        self.jpeg_seq = 0
        self.marks: list[dict] = []
        self.blinks: list[dict] = []
        self.events: deque = deque(maxlen=30)
        self._t0 = time.monotonic()
        self._next_frame = 0.0
        self._next_state = 0.0

    def state(self) -> dict:
        return {"running": self.running, "started_at": self.started_at, "config": self.config,
                "device_id": self.device_id, "last": self.last, "error": self.error, "marks": len(self.marks)}

    def start(self, cfg: dict, device_id: int, token: str, server_url: str) -> None:
        with self._lock:
            if self.running:
                raise RuntimeError("Já existe um teste rodando. Pare antes de começar outro.")
            self.running = True
            self.error = None
            self.config = cfg
            self.device_id = device_id
            self.started_at = utcnow()
            self.last = None
            self.jpeg = None
            self.marks = []
            self.blinks = []
            self.events.clear()
            self._t0 = time.monotonic()
            self.thread = threading.Thread(target=self._run, args=(cfg, token, server_url), name="drivesafe-teste",
                                           daemon=True)
            self.thread.start()

    def stop(self, wait: bool = True) -> None:
        monitor = self.monitor
        if monitor is not None:
            monitor.stop()
        thread = self.thread
        if wait and thread is not None and thread is not threading.current_thread():
            thread.join(timeout=20)

    def recalibrate(self) -> None:
        if self.monitor is not None:
            self.monitor.recalibrate()

    def elapsed(self) -> float:
        return time.monotonic() - self._t0

    def mark(self, kind: str, note: str | None) -> dict:
        if not self.running:
            raise RuntimeError("Nenhum teste rodando.")
        entry = {"t": round(self.elapsed(), 3), "kind": kind, "note": note or ""}
        self.marks.append(entry)
        return entry

    def marks_csv(self) -> str:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["tempo_s", "tipo", "nota"])
        for mark in self.marks:
            writer.writerow([f"{mark['t']:.3f}", mark["kind"], mark["note"]])
        return buffer.getvalue()

    def blinks_csv(self) -> str:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["inicio_s", "fim_s", "duracao_ms", "fechado_80_ms", "menor_abertura", "completa"])
        for blink in self.blinks:
            writer.writerow([f"{blink['start']:.3f}", f"{blink['end']:.3f}", blink["duration_ms"],
                             blink["closed_ms"], blink["min_openness"], int(blink["complete"])])
        return buffer.getvalue()

    def blink_check(self, tolerance: float) -> dict:
        """Compara as piscadas detectadas com as marcadas à mão, só no trecho em que houve marcação."""
        from vision.evaluation import match_events, precision_recall_f1

        marks = [mark["t"] for mark in self.marks if mark["kind"] == "piscada"]
        if not marks:
            return {"marked": 0, "detected": 0, "tolerance_s": tolerance}
        first, last = marks[0] - 2.0, marks[-1] + 2.0
        detected = [(b["start"], b["end"]) for b in self.blinks if first <= b["start"] <= last]
        pairs, extra, missed = match_events(detected, [(t, t) for t in marks], tolerance)
        precision, recall, f1 = precision_recall_f1(len(pairs), len(extra), len(missed))
        return {"marked": len(marks), "detected": len(detected), "matched": len(pairs), "extra": len(extra),
                "missed": len(missed), "precision": _round(precision), "recall": _round(recall), "f1": _round(f1),
                "tolerance_s": tolerance, "from_s": round(max(first, 0.0), 1), "to_s": round(last, 1)}

    def mjpeg(self):
        seq = -1
        while self.running:
            with self._frame_ready:
                self._frame_ready.wait_for(lambda: self.jpeg_seq != seq or not self.running, timeout=2.0)
                jpeg, current = self.jpeg, self.jpeg_seq
            if not self.running:
                break
            if jpeg is None or current == seq:
                continue
            seq = current
            yield (b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: " + str(len(jpeg)).encode()
                   + b"\r\n\r\n" + jpeg + b"\r\n")

    # ---------- thread do monitoramento ----------

    def _run(self, cfg: dict, token: str, server_url: str) -> None:
        sync = engine = analyzer = store = None
        try:
            from vision.alarm import Alarm
            from vision.calibration import Calibrator
            from vision.camera import open_camera
            from vision.driver_monitor import DriverMonitor
            from vision.drowsiness import DrowsinessMonitor
            from vision.engine import DriverStateEngine
            from vision.event_queue import EventStore
            from vision.face import create_face_analyzer
            from vision.remote_policy import RemotePolicy
            from vision.sync import ServerClient, SyncWorker

            data_dir = Path(config.DATA_DIR) / "teste"
            data_dir.mkdir(parents=True, exist_ok=True)
            store = EventStore(data_dir / "eventos.db")
            alarm = Alarm(data_dir / "sirene.wav")
            analyzer = create_face_analyzer(infrared=cfg["infrared"])

            def new_calibrator():
                if not analyzer.supports_calibration:
                    return None
                return Calibrator(min_seconds=cfg["calibration_min_s"],
                                  max_seconds=max(cfg["calibration_max_s"], cfg["calibration_min_s"]))

            drowsiness = DrowsinessMonitor(calibrator=new_calibrator())
            drowsiness.blink_listeners.append(self._on_blink)
            phone = None
            if cfg["phone"]:
                try:
                    from vision.phone import PhoneDetector, PhoneMonitor

                    phone = PhoneMonitor(PhoneDetector())
                except (RuntimeError, ValueError) as exc:
                    logger.warning("Teste sem detecção de celular: %s", exc)
            engine = DriverStateEngine(drowsiness, activation_mode=cfg["activation_mode"], phone=phone)
            monitor = DriverMonitor(analyzer, engine, alarm, store, calibrator_factory=new_calibrator)
            monitor.policy = RemotePolicy(engine, data_dir, calibrator_factory=new_calibrator)
            monitor.listeners.append(self._on_frame)

            camera = open_camera(cfg["camera"], 640, 480)
            deadline = time.monotonic() + CAMERA_OPEN_TIMEOUT_S
            while True:
                ok, frame = camera.read()
                if ok and frame is not None:
                    break
                if time.monotonic() >= deadline:
                    camera.release()
                    raise RuntimeError(f"Sem imagem da câmera {cfg['camera']!r}. Confira se ela está ligada e livre.")
                time.sleep(0.1)

            self.monitor = monitor
            sync = SyncWorker(store, ServerClient(server_url, token),
                              status_provider=lambda: {"camera_ok": monitor.camera_ok, "status": monitor.live_status()},
                              heartbeat_interval=5.0, policy_handler=monitor.policy.submit)
            sync.start()
            if not self.running:  # parado enquanto a câmera abria
                camera.release()
                return
            monitor.run(camera, show_window=False)
        except Exception as exc:
            self.error = str(exc) or exc.__class__.__name__
            logger.exception("O modo teste parou com erro.")
        finally:
            if sync is not None:
                sync.stop()
                sync.join(timeout=10)
            if engine is not None:
                engine.close()
            if analyzer is not None:
                analyzer.close()
            if store is not None:
                store.close()
            self.monitor = None
            self.running = False
            with self._frame_ready:
                self._frame_ready.notify_all()
            hub.publish_threadsafe({"type": "test_state", "data": {"running": False, "error": self.error}},
                                   admin_only=True)

    def _on_blink(self, _t, blink) -> None:
        complete = blink.min_openness <= 0.40 and blink.duration <= 1.0
        self.blinks.append({
            "start": round(blink.start - self._t0, 3), "end": round(blink.end - self._t0, 3),
            "duration_ms": round(blink.duration * 1000), "closed_ms": round(blink.closed_duration * 1000),
            "min_openness": round(blink.min_openness, 3), "complete": complete,
        })

    def _on_frame(self, frame, state) -> None:
        now = time.monotonic()
        for event in state.events:
            self.events.appendleft({"t": round(now - self._t0, 1), "type": event.alert_type,
                                    "risk": event.risk_level, "duration": event.duration})
        monitor = self.monitor
        if now >= self._next_frame:
            self._next_frame = now + FRAME_EVERY_S
            import cv2

            from vision.driver_monitor import draw_overlay

            image = draw_overlay(frame, state, monitor.latency.summary() if monitor is not None else None)
            ok, encoded = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
            if ok:
                with self._frame_ready:
                    self.jpeg = encoded.tobytes()
                    self.jpeg_seq += 1
                    self._frame_ready.notify_all()
        if now >= self._next_state:
            self._next_state = now + STATE_EVERY_S
            self.last = self._snapshot(now, state, monitor)
            hub.publish_threadsafe({"type": "test_state", "data": dict(self.last, running=True)}, admin_only=True)

    def _snapshot(self, now: float, state, monitor) -> dict:
        drowsy, risk, metrics = state.drowsiness, state.risk, state.metrics
        window = state.window or {}
        latency = monitor.latency.summary() if monitor is not None else None
        return {
            "t": round(now - self._t0, 2),
            "risk": {"level": risk.level, "name": risk.name, "reasons": list(risk.reasons[:4])},
            "drowsiness": {
                "status": drowsy.status, "openness": _round(drowsy.openness), "closed_for": _round(drowsy.closed_for, 2),
                "perclos_60s": drowsy.perclos_60s, "blinks_last_minute": drowsy.blinks_last_minute,
                "calibrating": drowsy.calibrating, "calibration_progress": _round(drowsy.calibration_progress),
                "face_found": drowsy.face_found,
            },
            "window": {key: window[key] for key in WINDOW_KEYS if key in window},
            "phone": None if state.phone is None else {
                "state": state.phone.state, "duration": state.phone.duration, "score": _round(state.phone.phone_score, 2)},
            "activation": None if state.activation is None else state.activation.to_details(),
            "visibility": {"ok": state.visibility.eyes_ok, "reason": state.visibility.reason},
            "pupil": {"ratio": _round(getattr(metrics, "pupil_ratio", None)),
                      "quality": getattr(metrics, "pupil_quality", None), "infrared": bool(getattr(metrics, "infrared", False))},
            "performance": {"fps": _round(drowsy.fps, 1), **(latency or {})},
            "blinks": len(self.blinks),
            "marks": len(self.marks),
            "events": list(self.events)[:10],
        }


class AnalysisJobs:
    """Vídeos enviados pelo app, analisados um de cada vez pelo analisar_video.py num processo separado."""

    PUBLIC_KEYS = ("id", "name", "status", "progress", "phone", "created_at", "finished_at", "error", "summary", "files")

    def __init__(self, root: Path):
        self.root = Path(root)
        self._lock = threading.Lock()
        self._queue_lock = threading.Lock()
        self.jobs: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        if not self.root.is_dir():
            return
        for job_file in self.root.glob("*/job.json"):
            try:
                job = json.loads(job_file.read_text(encoding="utf-8"))
            except ValueError:
                continue
            if job.get("status") in ("na_fila", "processando"):
                job["status"], job["error"] = "falhou", "O servidor reiniciou durante a análise."
                self._save(job)
            self.jobs[job["id"]] = job

    def _save(self, job: dict) -> None:
        folder = self.root / job["id"]
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "job.json").write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")

    def public(self, job: dict) -> dict:
        return {key: job.get(key) for key in self.PUBLIC_KEYS}

    def list(self) -> list[dict]:
        return [self.public(job) for job in sorted(self.jobs.values(), key=lambda j: j["created_at"], reverse=True)]

    def new(self, name: str, phone: bool) -> dict:
        extension = Path(name).suffix.lower()
        if extension not in VIDEO_EXTENSIONS:
            raise ValueError("Envie um vídeo .mp4, .avi, .mov, .mkv, .webm ou .m4v.")
        job_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
        job = {"id": job_id, "name": Path(name).name[:120], "status": "na_fila", "progress": 0.0, "phone": phone,
               "created_at": utcnow().isoformat(), "finished_at": None, "error": None, "summary": None, "files": [],
               "video": f"video{extension}"}
        with self._lock:
            self.jobs[job_id] = job
            self._save(job)
        return job

    def video_path(self, job: dict) -> Path:
        return self.root / job["id"] / job["video"]

    def discard(self, job_id: str) -> None:
        with self._lock:
            self.jobs.pop(job_id, None)
        shutil.rmtree(self.root / job_id, ignore_errors=True)

    def run(self, job_id: str) -> None:
        threading.Thread(target=self._process, args=(job_id,), name=f"drivesafe-analise-{job_id}", daemon=True).start()

    def file_path(self, job_id: str, name: str) -> Path | None:
        job = self.jobs.get(job_id)
        if job is None or name not in job.get("files", []):
            return None
        return self.root / job_id / "resultado" / name

    def _process(self, job_id: str) -> None:
        job = self.jobs[job_id]
        output = self.root / job_id / "resultado"
        with self._queue_lock:  # um vídeo por vez: a análise usa bastante CPU
            job["status"] = "processando"
            self._save(job)
            command = [sys.executable, str(Path(config.BASE_DIR) / "analisar_video.py"), str(self.video_path(job)),
                       "--saida", str(output)]
            if job["phone"]:
                command.append("--celular")
            tail: deque = deque(maxlen=15)
            try:
                process = subprocess.Popen(
                    command, cwd=config.BASE_DIR, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                    encoding="utf-8", errors="replace", env=dict(os.environ, PYTHONUTF8="1", PYTHONUNBUFFERED="1"),
                )
                for line in process.stdout:
                    line = line.rstrip()
                    tail.append(line)
                    match = PROGRESS_LINE.match(line)
                    if match:
                        job["progress"] = min(0.99, int(match.group(1)) / 100)
                        self._save(job)
                        hub.publish_threadsafe({"type": "analysis", "data": self.public(job)}, admin_only=True)
                code = process.wait()
                if code != 0:
                    raise RuntimeError("\n".join(tail)[-800:] or f"analisar_video.py terminou com código {code}")
                summaries = sorted(output.glob("*_resumo.json"))
                job["summary"] = json.loads(summaries[0].read_text(encoding="utf-8")) if summaries else None
                job["files"] = sorted(path.name for path in output.iterdir() if path.is_file())
                job["status"], job["progress"] = "concluida", 1.0
            except Exception as exc:
                job["status"], job["error"] = "falhou", str(exc)[-800:]
                logger.warning("Análise %s falhou: %s", job_id, exc)
            finally:
                if not config.KEEP_ANALYSIS_VIDEOS:
                    self.video_path(job).unlink(missing_ok=True)
                job["finished_at"] = utcnow().isoformat()
                self._save(job)
                hub.publish_threadsafe({"type": "analysis", "data": self.public(job)}, admin_only=True)
