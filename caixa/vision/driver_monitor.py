"""Loop do dispositivo: câmera → medidas do rosto → módulos (vision/engine.py) → alarme, fila de eventos e janela."""
from __future__ import annotations

import logging
import time
from collections import deque

import cv2

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


def draw_overlay(frame, state: DriverState, latency: dict | None = None):
    display = frame.copy()
    height, width = display.shape[:2]
    metrics, drowsy, risk = state.metrics, state.drowsiness, state.risk

    if metrics.face_found and metrics.eye_points is not None:
        for x, y in metrics.eye_points:
            cv2.circle(display, (int(x), int(y)), 2, (0, 255, 255), -1)
    if state.phone is not None:
        for x1, y1, x2, y2 in state.phone.boxes:
            cv2.rectangle(display, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 255), 2)

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

    draw_text_block(display, [("q ou Esc: sair   c: recalibrar", 0.45, 1, (220, 220, 220))], x=8, y=height - 36)
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
        # Funções chamadas a cada quadro com (quadro, estado): usadas pelo modo teste do app.
        self.listeners = []
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
            self.events.add(event.alert_type, event.risk_level, event.duration, details=event.details)
        if state.alarm:
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
            cv2.imshow(WINDOW_TITLE, draw_overlay(frame, state, self.latency.summary()))
            key = cv2.waitKey(1) & 0xFF
        except cv2.error as exc:
            logger.warning("Janela indisponível (%s). Seguindo sem janela.", exc)
            return False
        if key in (ord("q"), ord("Q"), 27) or self._window_closed():
            self._running = False
        elif key in (ord("c"), ord("C")):
            self.recalibrate()
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
