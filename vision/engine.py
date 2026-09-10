"""Orquestra os módulos a cada quadro. Não abre câmera nem toca som (isso fica em vision/driver_monitor.py).

Ordem: visibilidade dos olhos → sonolência (módulo 1) → sinais de ativação (módulo 2) → linha de base e
z-scores (módulo 3) → contexto, celular, fusão e alertas (módulo 4).

Privacidade (LGPD): no modo "local", os sinais de ativação só influenciam o risco dentro do dispositivo, e nenhum
evento leva essas métricas. Só no modo "enviar", que exige base legal e consentimento, elas vão ao servidor.
"""
from __future__ import annotations

import logging
import math
import threading
from dataclasses import dataclass, field

from vision.activation import ActivationAssessment, ActivationMonitor, assess_activation
from vision.baseline import (
    MIN_TRIPS_FOR_ACCUMULATED,
    MIN_WINDOWS,
    MODULE2_METRICS,
    SUSPECT_QUALITY,
    TRIP_QUALITY,
    Baseline,
    BaselineStore,
    build_trip_baseline,
)
from vision.context import DrivingContext
from vision.drowsiness import Assessment, DrowsinessMonitor
from vision.risk import RiskAssessment, RiskFusion
from vision.visibility import EyeVisibility, Visibility, mask_eye_signals

logger = logging.getLogger("drivesafe.engine")

ACTIVATION_MODES = ("desligado", "local", "enviar")
EVALUATE_EVERY_S = 1.0
EYES_HIDDEN_EVENT_S = 10.0
EYES_HIDDEN_COOLDOWN_S = 600.0
MIN_CALIBRATION_SAMPLES = 100
PRIVATE_KEYS = frozenset(MODULE2_METRICS) | {"pupila_faixa_luz", "pupila_fonte_luz", "pupila_motivo", "ativacao",
                                              "fracao_valida_60s"}


@dataclass
class DriverState:
    metrics: object
    drowsiness: Assessment
    risk: RiskAssessment
    visibility: Visibility
    activation: ActivationAssessment | None = None
    phone: object | None = None
    window: dict = field(default_factory=dict)
    zscores: dict = field(default_factory=dict)
    baseline_source: str | None = None
    events: list = field(default_factory=list)
    context: dict = field(default_factory=dict)

    @property
    def alarm(self) -> bool:
        return self.risk.alarm


class DriverStateEngine:
    def __init__(self, drowsiness: DrowsinessMonitor, activation_mode: str = "local",
                 baseline_store: BaselineStore | None = None, context: DrivingContext | None = None,
                 visibility: EyeVisibility | None = None, phone=None, background_baseline: bool = True):
        if activation_mode not in ACTIVATION_MODES:
            raise ValueError(f"modo dos sinais de ativação inválido: {activation_mode!r}")
        self.drowsiness = drowsiness
        self.activation_mode = activation_mode
        self.activation = ActivationMonitor() if activation_mode != "desligado" else None
        self.fusion = RiskFusion(share_activation=activation_mode == "enviar")
        self.context = context or DrivingContext()
        self.visibility = visibility or EyeVisibility()
        self.phone = phone
        self.baseline_store = baseline_store
        self.background_baseline = background_baseline
        self.accumulated = baseline_store.load() if baseline_store is not None else None
        if self.accumulated is not None:
            logger.info("Linha de base acumulada carregada (%d viagens).", self.accumulated.trips)
        self.trip_baseline: Baseline | None = None
        self._next_evaluation = -math.inf
        self._window: dict = {}
        self._zscores: dict = {}
        self._context: dict = {}
        self._activation: ActivationAssessment | None = None
        self._last_hidden_event = None

    @property
    def baseline(self) -> Baseline | None:
        accumulated = self.accumulated
        if accumulated is not None and accumulated.trips >= MIN_TRIPS_FOR_ACCUMULATED:
            return accumulated
        return self.trip_baseline

    def update(self, metrics, frame=None) -> DriverState:
        t = metrics.timestamp
        visibility = self.visibility.update(metrics)
        measured = metrics if visibility.eyes_ok else mask_eye_signals(metrics)
        drowsy = self.drowsiness.update(measured)
        if self.drowsiness.last_calibration is not None:
            self._start_trip_baseline()
        if self.activation is not None:
            self.activation.observe(measured, drowsy.openness)
        self.context.update(t, metrics.face_found)
        # Parado segundo a telemetria (estacionado, por exemplo): uso de celular não é alerta.
        phone = self.phone.update(metrics, frame, moving=not self.context.stopped) if self.phone is not None else None

        events = list(drowsy.events)
        self._eyes_hidden_event(t, visibility, events)
        if phone is not None:
            events.extend(phone.events)
        if t >= self._next_evaluation:
            self._next_evaluation = t + EVALUATE_EVERY_S
            self._evaluate(t, drowsy)

        risk = self.fusion.update(t, drowsy, self._activation, self._context, self._zscores, self._window, phone)
        events.extend(risk.events)
        baseline = self.baseline
        for event in events:
            event.details = self._decorate(event.details, risk, baseline)
        return DriverState(metrics, drowsy, risk, visibility, self._activation, phone, self._window, self._zscores,
                           baseline.source if baseline is not None else None, events, self._context)

    def set_activation_mode(self, mode: str) -> None:
        """Troca o modo dos sinais de ativação em execução (ex.: consentimento registrado no app)."""
        if mode not in ACTIVATION_MODES:
            raise ValueError(f"modo dos sinais de ativação inválido: {mode!r}")
        if mode == self.activation_mode:
            return
        logger.info("Sinais de ativação atípica: modo %s -> %s.", self.activation_mode, mode)
        self.activation_mode = mode
        if mode == "desligado":
            self.activation = None
            self._activation = None
        elif self.activation is None:
            self.activation = ActivationMonitor()
        self.fusion.share_activation = mode == "enviar"

    def set_baseline_store(self, store: BaselineStore | None) -> None:
        """Liga ou desliga a linha de base acumulada (depende do consentimento do motorista)."""
        self.baseline_store = store
        self.accumulated = store.load() if store is not None else None

    def close(self) -> None:
        if self.phone is not None:
            self.phone.close()

    def _evaluate(self, t: float, drowsy: Assessment) -> None:
        window = dict(self.drowsiness.details)
        if self.activation is not None:
            window.update(self.activation.window_metrics(t, drowsy.fps))
        baseline = self.baseline
        self._zscores = baseline.zscores(window) if baseline is not None else {}
        self._window = window
        if self.activation is not None:
            quality = baseline.quality if baseline is not None else 0.0
            self._activation = assess_activation(self._zscores, window, quality, drowsy.level, drowsy.fps)
        self._context = self.context.snapshot()

    def _start_trip_baseline(self) -> None:
        calibrator = self.drowsiness.last_calibration
        self.drowsiness.last_calibration = None
        samples, calibrator.samples = calibrator.samples, []
        profile = self.drowsiness.profile
        if profile is None or len(samples) < MIN_CALIBRATION_SAMPLES:
            return
        suspicious = calibrator.result is None or not calibrator.result.looked_alert
        factory = ActivationMonitor if self.activation is not None else None

        def build():
            try:
                trip = build_trip_baseline(samples, profile, factory, SUSPECT_QUALITY if suspicious else TRIP_QUALITY)
                self._install_trip_baseline(trip, suspicious)
            except Exception:
                logger.exception("Falha ao montar a linha de base da viagem.")

        if self.background_baseline:
            # Reprocessar 5 a 10 min de quadros leva alguns segundos: fora do loop da câmera.
            threading.Thread(target=build, name="drivesafe-linha-de-base", daemon=True).start()
        else:
            build()

    def _install_trip_baseline(self, trip: Baseline, suspicious: bool) -> None:
        accumulated = self.accumulated
        atypical = False
        if self.activation is not None and accumulated is not None and accumulated.trips >= MIN_TRIPS_FOR_ACCUMULATED:
            reference = trip.reference_window()
            atypical = assess_activation(accumulated.zscores(reference), reference, 1.0).state == "sinais_compativeis"
            if atypical:
                trip.quality = SUSPECT_QUALITY
                logger.warning("Calibração com padrão ocular fora do habitual deste motorista: a linha de base desta "
                               "viagem vale menos e não entra na acumulada.")
        self.trip_baseline = trip
        if len(trip.windows) < MIN_WINDOWS:
            logger.warning("Calibração curta demais para a linha de base (%d janelas; precisa de ~2 min ou mais): "
                           "sem z-scores e sem sinais de ativação nesta viagem.", len(trip.windows))
        else:
            logger.info("Linha de base da viagem pronta (%d janelas).", len(trip.windows))
        if self.baseline_store is not None and trip.windows and not suspicious and not atypical:
            self.accumulated = self.baseline_store.merge(trip)
            logger.info("Linha de base acumulada atualizada (%d viagens).", self.accumulated.trips)

    def _eyes_hidden_event(self, t: float, visibility: Visibility, events: list) -> None:
        if visibility.eyes_ok or visibility.hidden_for < EYES_HIDDEN_EVENT_S:
            return
        if self._last_hidden_event is not None and t - self._last_hidden_event < EYES_HIDDEN_COOLDOWN_S:
            return
        from vision.drowsiness import DetectedEvent

        self._last_hidden_event = t
        events.append(DetectedEvent("olhos_nao_visiveis", 1, round(visibility.hidden_for, 1),
                                    {"motivo": visibility.reason}))

    def _decorate(self, details: dict | None, risk: RiskAssessment, baseline: Baseline | None) -> dict:
        details = dict(details or {})
        share = self.activation_mode == "enviar"
        if not share:
            for key in PRIVATE_KEYS & details.keys():
                del details[key]
        details.setdefault("nivel_risco", risk.level)
        details.setdefault("nivel_risco_nome", risk.name)
        zscores = {name: z for name, z in self._zscores.items() if share or name not in MODULE2_METRICS}
        if zscores:
            details.setdefault("z", zscores)
            details.setdefault("linha_de_base", baseline.source if baseline is not None else None)
        return details
