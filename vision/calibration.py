"""Calibração individual: aprende o olho aberto, o olho fechado e o padrão de piscada de cada motorista.

Base:
- Linha de base por motorista melhora a detecção (Friedrichs & Yang, 2010; Ghoddoosian et al., 2019).
- Aprendizado de até 10 min no início da viagem (Euro NCAP 2026, Driver Engagement).
- Calibração feita com o motorista já sonolento vira referência errada: por isso a checagem absoluta
  de PERCLOS e de fechamento longo no fim (Mulhall et al., 2020; Cori et al., 2023; Lin et al., 2012).
"""
from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass, replace
from datetime import datetime, timezone

from vision.eyes import (
    MAX_FRAME_GAP_S,
    MIN_FPS_FOR_VELOCITY,
    P80_OPENNESS,
    Blink,
    DriverProfile,
    EyeStateTracker,
    OpennessModel,
    Sample,
)

logger = logging.getLogger("drivesafe.calibration")

# Fechamentos mais curtos não entram no PERCLOS (a literatura usa cortes de 250 a 500 ms; Abe, 2023).
SHORT_CLOSURE_S = 0.25
# Acima disso não é piscada, é fechamento longo.
MAX_BLINK_S = 1.0
# Piscada "completa": fechou pelo menos 60% da amplitude da pessoa.
COMPLETE_BLINK_OPENNESS = 0.40
MIN_BLINKS_FOR_CLOSED_REFERENCE = 10
# Calibração com PERCLOS acima de ~10% ou fechamento de 1 s não representa o motorista alerta.
ALERT_MAX_PERCLOS = 0.10
ALERT_MAX_CLOSURE_S = 1.0


@dataclass
class BlinkObservation:
    blink: Blink
    min_ear: float | None
    max_score: float | None
    min_open_prob: float | None

    @property
    def complete(self) -> bool:
        return self.blink.min_openness <= COMPLETE_BLINK_OPENNESS and self.blink.duration <= MAX_BLINK_S


def _median(values):
    values = [v for v in values if v is not None]
    return statistics.median(values) if values else None


class Calibrator:
    def __init__(self, min_seconds: float = 300.0, max_seconds: float = 600.0, target_blinks: int = 100):
        self.min_seconds = min_seconds
        self.max_seconds = max(max_seconds, min_seconds)
        self.target_blinks = target_blinks
        self.samples: list[Sample] = []
        self.result: DriverProfile | None = None  # perfil construído ao terminar (preenchido pelo monitor)
        self.valid_seconds = 0.0
        self.live_blinks = 0
        self._last_t = None
        self._live_model = OpennessModel()
        self._live_tracker = EyeStateTracker()

    @property
    def progress(self) -> float:
        return min(1.0, self.valid_seconds / self.min_seconds) if self.min_seconds > 0 else 1.0

    def add(self, metrics) -> None:
        sample = Sample.from_metrics(metrics)
        self.samples.append(sample)
        if self._last_t is not None and sample.face_found:
            dt = sample.timestamp - self._last_t
            if 0 < dt <= MAX_FRAME_GAP_S:
                self.valid_seconds += dt
        self._last_t = sample.timestamp

        openness, _ = self._live_model.openness(sample)
        blink = self._live_tracker.update(sample.timestamp, openness)
        if blink is not None and blink.min_openness <= COMPLETE_BLINK_OPENNESS and blink.duration <= MAX_BLINK_S:
            self.live_blinks += 1

    def done(self) -> bool:
        if self.valid_seconds < self.min_seconds:
            return False
        return self.live_blinks >= self.target_blinks or self.valid_seconds >= self.max_seconds

    def build_profile(self) -> DriverProfile | None:
        valid = [s for s in self.samples if s.face_found and s.ear is not None]
        if len(valid) < 100:
            logger.warning("Calibração com poucos quadros válidos (%d).", len(valid))
            return None

        # 1) Olho aberto habitual: mediana do EAR (a maior parte do tempo o olho está aberto).
        ear_open = statistics.median(s.ear for s in valid)
        pitch_baseline = _median(s.pitch for s in valid)
        yaw_baseline = _median(s.yaw for s in valid)
        provisional = DriverProfile(
            ear_open=ear_open, ear_closed=0.3 * ear_open,
            pitch_baseline=pitch_baseline, yaw_baseline=yaw_baseline,
        )

        # 2) Referências de fechado a partir das piscadas medidas só pela geometria do olho (EAR),
        #    o sinal mais estável; pontuação e classificador são lidos no fundo dessas piscadas.
        observations, _, _, _ = self._replay(provisional, ear_only=True)
        complete = [o for o in observations if o.complete and o.min_ear is not None]
        enough = len(complete) >= MIN_BLINKS_FOR_CLOSED_REFERENCE
        ear_closed = min(statistics.median(o.min_ear for o in complete), 0.6 * ear_open) if enough else 0.3 * ear_open

        score_open = _median(s.blink_score for s in valid)
        score_closed = None
        if score_open is not None:
            closed_scores = [o.max_score for o in complete if o.max_score is not None]
            if len(closed_scores) >= MIN_BLINKS_FOR_CLOSED_REFERENCE:
                score_closed = statistics.median(closed_scores)
            else:
                score_closed = min(1.0, score_open + 0.5)

        classifier_open = _median(s.eye_open_prob for s in valid)
        classifier_closed = None
        if classifier_open is not None:
            closed_probs = [o.min_open_prob for o in complete if o.min_open_prob is not None]
            if len(closed_probs) >= MIN_BLINKS_FOR_CLOSED_REFERENCE:
                classifier_closed = statistics.median(closed_probs)

        profile = DriverProfile(
            ear_open=ear_open,
            ear_closed=ear_closed,
            score_open=score_open,
            score_closed=score_closed,
            classifier_open=classifier_open,
            classifier_closed=classifier_closed,
            jaw_open_baseline=_median(s.jaw_open for s in valid),
            pitch_baseline=pitch_baseline,
            yaw_baseline=yaw_baseline,
            ear_closed_estimated=not enough,
        )

        # 3) Estatísticas finais medidas com o perfil completo e todos os sinais.
        observations, perclos, longest, valid_time = self._replay(profile)
        complete = [o.blink for o in observations if o.complete]
        durations = [blink.duration for blink in complete]
        if len(durations) >= 5:
            profile.blink_duration_median_s = statistics.median(durations)
        if len(durations) >= 10:
            profile.blink_duration_p90_s = statistics.quantiles(durations, n=10)[-1]
        if valid_time > 0:
            profile.blink_rate_per_min = len(durations) / (valid_time / 60.0)
        profile.perclos_baseline = perclos
        profile.longest_closure_s = longest
        profile.blinks = len(durations)
        profile.valid_seconds = valid_time
        span = self.samples[-1].timestamp - self.samples[0].timestamp
        profile.fps = (len(self.samples) - 1) / span if span > 0 else None
        if profile.fps is not None and profile.fps >= MIN_FPS_FOR_VELOCITY:
            closing = [blink.closing_avr for blink in complete if blink.closing_avr is not None]
            opening = [blink.opening_avr for blink in complete if blink.opening_avr is not None]
            if len(closing) >= MIN_BLINKS_FOR_CLOSED_REFERENCE:
                profile.blink_closing_avr_median_s = statistics.median(closing)
            if len(opening) >= MIN_BLINKS_FOR_CLOSED_REFERENCE:
                profile.blink_opening_avr_median_s = statistics.median(opening)
        profile.looked_alert = perclos <= ALERT_MAX_PERCLOS and longest < ALERT_MAX_CLOSURE_S
        profile.created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        return profile

    def _replay(self, profile: DriverProfile, ear_only: bool = False):
        """Reprocessa os quadros guardados. Retorna (observações de piscada, perclos, maior fechamento, tempo válido)."""
        model = OpennessModel(profile)
        tracker = EyeStateTracker()
        observations = []
        valid_time = closed_time = pending = longest = 0.0
        last_t = None
        min_ear = max_score = min_prob = None

        for sample in self.samples:
            measured = replace(sample, blink_score=None, eye_open_prob=None) if ear_only else sample
            openness, _ = model.openness(measured)
            dt = 0.0
            if last_t is not None and 0 < sample.timestamp - last_t <= MAX_FRAME_GAP_S:
                dt = sample.timestamp - last_t
            last_t = sample.timestamp
            if openness is not None:
                valid_time += dt

            blink = tracker.update(sample.timestamp, openness)
            if tracker.in_blink and openness is not None:
                if sample.ear is not None and (min_ear is None or sample.ear < min_ear):
                    min_ear = sample.ear
                if sample.blink_score is not None and (max_score is None or sample.blink_score > max_score):
                    max_score = sample.blink_score
                if sample.eye_open_prob is not None and (min_prob is None or sample.eye_open_prob < min_prob):
                    min_prob = sample.eye_open_prob

            if openness is not None and openness <= P80_OPENNESS:
                pending += dt
                if tracker.closed_for >= SHORT_CLOSURE_S:
                    closed_time += pending
                    pending = 0.0
            elif openness is not None:
                pending = 0.0

            longest = max(longest, tracker.closed_for)
            if blink is not None:
                longest = max(longest, blink.closed_duration)
                observations.append(BlinkObservation(blink, min_ear, max_score, min_prob))
                min_ear = max_score = min_prob = None

        perclos = closed_time / valid_time if valid_time > 0 else 0.0
        return observations, perclos, longest, valid_time
