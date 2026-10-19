"""Calibração individual: aprende o olho aberto, o olho fechado e o padrão de piscada de cada motorista.

Base:
- Linha de base por motorista melhora a detecção (Friedrichs & Yang, 2010; Ghoddoosian et al., 2019).
- Aprendizado de até 10 min no início da viagem (Euro NCAP 2026, Driver Engagement).
- Calibração feita com o motorista já sonolento vira referência errada: por isso a checagem absoluta
  de PERCLOS e de fechamento longo no fim (Mulhall et al., 2020; Cori et al., 2023; Lin et al., 2012).

Spec 027 (pesquisa docs/pesquisa/2026-10-19-alarme-calibracao-e-registro.md, §2.3):
- CAL-01: a referência de olho fechado era a mediana do menor EAR de cada piscada. A 10 fps a piscada de ~100 ms
  tem 1 ou 2 quadros e o "menor EAR" raramente pega o fundo (+57% de erro no experimento exp_calib.py). Agora é um
  percentil dos mínimos que cai com a taxa de quadros (P50 a 30 fps, igual ao de antes; ~P17 a 10 fps): a fração de
  piscadas cujo quadro pega o fundo cai na mesma proporção. Abaixo de 20 fps a referência fica marcada como estimada
  e a qualidade da calibração não é "boa". Hipótese: confirmar com vídeo real gravado a 10 e a 30 fps.
- CAL-02: calibração com sono moderado passava como alerta (exp_calib2.py). Agora fica suspeita com fechamento de
  0,5 s ou mais (microssono comportamental de Mulhall et al., 2020) ou com a piscada mediana 1,5 desvio acima da
  linha de base acumulada da pessoa (≥ 3 viagens; Ingre et al., 2006: a duração sobe com o sono). Suspeita não
  salva o perfil se houver um salvo e não entra na acumulada (vision/drowsiness.py e vision/engine.py).
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
from vision.gaze import MIN_IRIS_PX, combined_gaze

logger = logging.getLogger("drivesafe.calibration")

# Fechamentos mais curtos não entram no PERCLOS (a literatura usa cortes de 250 a 500 ms; Abe, 2023).
SHORT_CLOSURE_S = 0.25
# Acima disso não é piscada, é fechamento longo.
MAX_BLINK_S = 1.0
# Piscada "completa": fechou pelo menos 60% da amplitude da pessoa.
COMPLETE_BLINK_OPENNESS = 0.40
MIN_BLINKS_FOR_CLOSED_REFERENCE = 10
# Calibração com PERCLOS acima de ~10% ou um fechamento de 0,5 s (Mulhall et al., 2020) não representa o
# motorista alerta (CAL-02; antes o corte era 1 s).
ALERT_MAX_PERCLOS = 0.10
ALERT_MAX_CLOSURE_S = 0.5
# CAL-02: piscada mediana acima da linha de base acumulada (z) aponta a calibração.
SUSPECT_DURATION_Z = 1.5
# CAL-01: percentil dos menores EAR das piscadas = 0,5 × fps / 30, entre 0,15 e 0,5.
CLOSED_REFERENCE_FPS = 30.0
MIN_CLOSED_PERCENTILE = 0.15
MIN_FPS_FOR_GOOD_CALIBRATION = 20.0


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


def _percentile(values, fraction: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def closed_reference_percentile(fps: float | None) -> float:
    """CAL-01: com menos quadros por piscada, menos piscadas têm um quadro no fundo; o percentil cai junto."""
    if not fps:
        return 0.5
    return max(MIN_CLOSED_PERCENTILE, min(0.5, 0.5 * fps / CLOSED_REFERENCE_FPS))


class Calibrator:
    def __init__(self, min_seconds: float = 300.0, max_seconds: float = 600.0, target_blinks: int = 100):
        self.min_seconds = min_seconds
        self.max_seconds = max(max_seconds, min_seconds)
        self.target_blinks = target_blinks
        self.samples: list[Sample] = []
        self.result: DriverProfile | None = None  # perfil construído ao terminar (preenchido pelo monitor)
        # CAL-02: (média, desvio) da piscada mediana em ms na linha de base acumulada, posto pelo vision/engine.py
        # quando há ≥ 3 viagens. None = sem comparação.
        self.duration_reference: tuple | None = None
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
        span = self.samples[-1].timestamp - self.samples[0].timestamp
        fps = (len(self.samples) - 1) / span if span > 0 else None

        # 2) Referências de fechado a partir das piscadas medidas só pela geometria do olho (EAR),
        #    o sinal mais estável; pontuação e classificador são lidos no fundo dessas piscadas.
        observations, _, _, _ = self._replay(provisional, ear_only=True)
        complete = [o for o in observations if o.complete and o.min_ear is not None]
        enough = len(complete) >= MIN_BLINKS_FOR_CLOSED_REFERENCE
        ear_closed = (min(_percentile([o.min_ear for o in complete], closed_reference_percentile(fps)), 0.6 * ear_open)
                      if enough else 0.3 * ear_open)
        slow_camera = fps is not None and fps < MIN_FPS_FOR_GOOD_CALIBRATION

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
            ear_closed_estimated=not enough or slow_camera,
            look_down_baseline=_median(getattr(s, "eye_look_down", None) for s in valid),
            calibration_quality="poucas_piscadas" if not enough else ("taxa_de_quadros_baixa" if slow_camera else "boa"),
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
        profile.fps = fps
        if profile.fps is not None and profile.fps >= MIN_FPS_FOR_VELOCITY:
            for attribute, values in (
                    ("blink_closing_avr_median_s", [blink.closing_avr for blink in complete]),
                    ("blink_opening_avr_median_s", [blink.opening_avr for blink in complete]),
                    ("blink_closing_median_s", [blink.closing_s for blink in complete]),
                    ("blink_reopening_median_s", [blink.reopening_s for blink in complete])):
                values = [value for value in values if value is not None]
                if len(values) >= MIN_BLINKS_FOR_CLOSED_REFERENCE:
                    setattr(profile, attribute, statistics.median(values))
        profile.gaze_center_yaw, profile.gaze_center_pitch = self._gaze_center(valid, profile)
        profile.suspect_reasons = self._suspect_reasons(profile, perclos, longest)
        profile.looked_alert = not profile.suspect_reasons
        profile.created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        return profile

    def _suspect_reasons(self, profile: DriverProfile, perclos: float, longest: float) -> list:
        """CAL-02: por que esta calibração não representa o motorista alerta (lista vazia = alerta)."""
        reasons = []
        if perclos > ALERT_MAX_PERCLOS:
            reasons.append("perclos_alto")
        if longest >= ALERT_MAX_CLOSURE_S:
            reasons.append("fechamento_longo")
        if self.duration_reference is not None and profile.blink_duration_median_s:
            mean_ms, std_ms = self.duration_reference
            if std_ms and (profile.blink_duration_median_s * 1000.0 - mean_ms) / std_ms >= SUSPECT_DURATION_Z:
                reasons.append("piscadas_mais_longas_que_o_habitual")
        return reasons

    @staticmethod
    def _gaze_center(valid, profile: DriverProfile):
        """DMS-02: valor inicial da "frente" = mediana do olhar (cabeça + olho) com o olho aberto. A moda do
        vision/gaze.py assume depois."""
        model = OpennessModel(profile)
        yaws, pitches = [], []
        for sample in valid[::3]:  # 10 Hz basta para a mediana
            if None in (sample.yaw, sample.pitch, sample.gaze_x, sample.gaze_y):
                continue
            if sample.iris_diameter_px is not None and sample.iris_diameter_px < MIN_IRIS_PX:
                continue
            openness, _ = model.openness(sample)
            if openness is None or openness < 0.6:
                continue
            yaw, pitch = combined_gaze(sample.yaw, sample.pitch, sample.gaze_x, sample.gaze_y)
            yaws.append(yaw)
            pitches.append(pitch)
        if len(yaws) < 30:
            return None, None
        return round(statistics.median(yaws), 2), round(statistics.median(pitches), 2)

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
