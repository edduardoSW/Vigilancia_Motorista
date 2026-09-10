"""Módulos 1 a 4: velocidade da pálpebra (AVR), cabeceio, olhos não visíveis, linha de base e z-scores,
sinais de ativação, fusão com histerese e rebote, contexto da viagem e privacidade dos eventos.

Só usa a biblioteca padrão (não precisa de câmera, OpenCV nem MediaPipe):
    python tests/test_modulos.py
"""
import json
import math
import random
import statistics
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from vision.activation import (  # noqa: E402
    ActivationAssessment,
    ActivationMonitor,
    assess_activation,
    gaze_transition_entropy,
)
from vision.baseline import Baseline, BaselineStore, RunningStats, build_trip_baseline  # noqa: E402
from vision.calibration import Calibrator  # noqa: E402
from vision.context import DrivingContext  # noqa: E402
from vision.drowsiness import Assessment, DrowsinessMonitor, NodTracker  # noqa: E402
from vision.engine import DriverStateEngine  # noqa: E402
from vision.eyes import DriverProfile, EyeStateTracker, Sample  # noqa: E402
from vision.risk import RiskAssessment, RiskFusion  # noqa: E402
from vision.visibility import EyeVisibility, mask_eye_signals  # noqa: E402

checks = 0
work = Path(tempfile.mkdtemp(prefix="drivesafe-modulos-"))


def ok(message):
    global checks
    checks += 1
    print(f"OK {checks:02d} {message}")


@dataclass
class Frame(Sample):
    """Sample com as medidas de imagem usadas pela checagem de óculos escuros."""

    cheek_luminance: float | None = None
    eye_contrast: float | None = None
    eyes_in_frame: bool = True


def openness_at(t, events):
    for start, duration, kind in events:
        if start <= t < start + duration:
            tau = t - start
            if kind == "piscada":
                return 1.0 - math.sin(math.pi * tau / duration) ** 2
            ramp = 0.08
            if tau < ramp:
                return 1.0 - tau / ramp
            if tau > duration - ramp:
                return (tau - (duration - ramp)) / ramp
            return 0.0
    return 1.0


def blink_schedule(start, seconds, rng, every=3.5, duration=0.30):
    events, t = [], start + 1.0
    while t < start + seconds - 1.0:
        events.append((t, max(0.12, rng.gauss(duration, 0.05)), "piscada"))
        t += max(1.0, rng.gauss(every, 0.8))
    return events


def person_frame(t, events, ear_open=0.20, ear_closed=0.05, **extra):
    o = openness_at(t, events)
    return Frame(timestamp=t, face_found=True, ear=ear_closed + o * (ear_open - ear_closed),
                 blink_score=0.05 + (1.0 - o) * 0.85, jaw_open=0.02, pitch=0.0, yaw=0.0, eye_distance_px=90.0, **extra)


# 1. Velocidade da pálpebra: AVR = amplitude ÷ pico de velocidade (Johns et al.).
def linear_blink(closing_s, opening_s, fps=60.0):
    tracker, blinks = EyeStateTracker(), []
    total = closing_s + 0.05 + opening_s
    for i in range(int((total + 0.8) * fps)):
        t = i / fps
        tau = t - 0.4
        if tau < 0 or tau > total:
            o = 1.0
        elif tau < closing_s:
            o = 1.0 - tau / closing_s
        elif tau < closing_s + 0.05:
            o = 0.0
        else:
            o = (tau - closing_s - 0.05) / opening_s
        blink = tracker.update(t, o)
        if blink:
            blinks.append(blink)
    assert len(blinks) == 1, blinks
    return blinks[0]


fast, slow = linear_blink(0.08, 0.15), linear_blink(0.16, 0.30)
assert abs(fast.amplitude - 1.0) < 0.05 and abs(fast.closing_avr - 0.08) < 0.015, (fast.amplitude, fast.closing_avr)
assert slow.closing_avr > 1.8 * fast.closing_avr and slow.opening_avr > 1.8 * fast.opening_avr
ok(f"AVR: fechamento {fast.closing_avr * 1000:.0f} ms na piscada rápida e {slow.closing_avr * 1000:.0f} ms na lenta")


# 2. Cabeceio.
def count_nods(pitch_of, seconds=30.0, fps=30.0):
    tracker = NodTracker()
    return sum(tracker.update(i / fps, pitch_of(i / fps)) for i in range(int(seconds * fps)))


def fast_nod(t):
    if 15.0 <= t < 15.3:
        return 25.0 * (t - 15.0) / 0.3
    if 15.3 <= t < 16.1:
        return 25.0
    if 16.1 <= t < 16.4:
        return 25.0 * (1.0 - (t - 16.1) / 0.3)
    return math.sin(t)


def slow_look(t):
    if 15.0 <= t < 18.0:
        return 25.0 * (t - 15.0) / 3.0
    if 18.0 <= t < 20.0:
        return 25.0
    if 20.0 <= t < 21.0:
        return 25.0 * (21.0 - t)
    return 0.0


def long_look(t):
    if 15.0 <= t < 15.3:
        return 25.0 * (t - 15.0) / 0.3
    return 25.0 if 15.3 <= t < 22.0 else 0.0


assert count_nods(fast_nod) == 1 and count_nods(slow_look) == 0 and count_nods(long_look) == 0
ok("cabeceio: queda rápida e volta conta; olhar para baixo devagar ou por 7 s não conta")


# 3. Óculos escuros: medidas do olho desligadas, sem microssono falso, e aviso depois de 10 s.
visibility = EyeVisibility()
dark = dict(eye_luminance=30.0, cheek_luminance=120.0, eye_contrast=8.0)
assert not visibility.update(person_frame(0.0, [], **dark)).eyes_ok
assert EyeVisibility().update(person_frame(0.0, [], eye_luminance=90.0, cheek_luminance=120.0, eye_contrast=40.0)).eyes_ok
masked = mask_eye_signals(person_frame(0.0, []))
assert masked.ear is None and masked.blink_score is None and masked.face_found

profile = DriverProfile(ear_open=0.20, ear_closed=0.05, score_open=0.05, score_closed=0.9, pitch_baseline=0.0, yaw_baseline=0.0)
engine = DriverStateEngine(DrowsinessMonitor(profile=profile), activation_mode="local")
events = []
for i in range(15 * 30):
    t = i / 30
    # Por trás da lente o MediaPipe "vê" um olho fechado: sem a checagem, isso viraria microssono.
    frame = person_frame(t, [], ear_open=0.05, **dark)
    frame.blink_score = 0.9
    events += engine.update(frame).events
assert [e.alert_type for e in events] == ["olhos_nao_visiveis"], [e.alert_type for e in events]
assert events[0].details["motivo"] == "oculos_escuros"
ok("óculos escuros: nenhum microssono falso e aviso de olhos não visíveis após 10 s")


# 4. Linha de base e z-scores.
values = [1.0, 2.0, 3.0, 4.0, 5.0]
stats = RunningStats()
for value in values:
    stats.add(value)
assert abs(stats.mean - 3.0) < 1e-9 and abs(stats.var - statistics.pvariance(values)) < 1e-9

baseline = Baseline("viagem", 0.75)
for rate in (14, 16, 15, 17, 13):
    baseline.add_window({"piscadas_por_min": rate, "pupila_iris": 0.40, "pupila_faixa_luz": "lux2"})
z = baseline.zscores({"piscadas_por_min": 30, "pupila_iris": 0.50, "pupila_faixa_luz": "lux2"})
assert z["piscadas_por_min"] == 5.0 and abs(z["pupila_iris"] - 3.33) < 0.01, z
assert "pupila_iris" not in baseline.zscores({"pupila_iris": 0.50, "pupila_faixa_luz": "lux4"})

store = BaselineStore(work / "linhas" / "motorista.json")
store.merge(baseline)
accumulated = store.merge(baseline)
loaded = store.load()
assert accumulated.trips == loaded.trips == 2 and loaded.stats["piscadas_por_min"].n == 10
ok("z-score com piso de desvio, pupila só na mesma faixa de luz e linha de base acumulada salva (2 viagens)")

rng = random.Random(7)
schedule = blink_schedule(0.0, 240.0, rng)
samples = [person_frame(i / 30, schedule) for i in range(240 * 30)]
trip = build_trip_baseline(samples, profile, ActivationMonitor)
reference = trip.reference_window()
assert len(trip.windows) >= 5 and 13 <= reference["piscadas_por_min"] <= 21, (len(trip.windows), reference)
assert all(abs(value) < 1.0 for value in trip.zscores(reference).values())
ok(f"linha de base da viagem: {len(trip.windows)} janelas, {reference['piscadas_por_min']:.1f} piscadas/min")


# 5. Sinais de ativação.
monitor = ActivationMonitor()
for i in range(60 * 30):
    t = i / 30
    monitor.observe(Sample(timestamp=t, face_found=True, gaze_x=0.0, gaze_y=0.0, yaw=0.0, pitch=0.0,
                           iris_diameter_px=14.0), 1.0)
still = monitor.window_metrics(60.0, fps=30.0)
assert still["entropia_olhar_bits"] == 0.0 and still["sacadas_por_min"] == 0.0, still

monitor = ActivationMonitor()
for i in range(60 * 30):
    t = i / 30
    gaze = -0.3 if int(t / 0.5) % 2 == 0 else 0.3
    monitor.observe(Sample(timestamp=t, face_found=True, gaze_x=gaze, gaze_y=0.0, yaw=0.0, pitch=0.0,
                           iris_diameter_px=14.0), 1.0)
scanning = monitor.window_metrics(60.0, fps=30.0)
assert 110 <= scanning["sacadas_por_min"] <= 125 and scanning["entropia_olhar_bits"] > 0.9, scanning
assert "pupila_iris" not in scanning and scanning["pupila_motivo"] == "sem_medida"
assert gaze_transition_entropy([("a", "b"), ("b", "a")] * 10) == 0.0
ok(f"olhar: parado 0 bits e 0 sacadas; varrendo {scanning['sacadas_por_min']:.0f} sacadas/min e "
   f"{scanning['entropia_olhar_bits']:.2f} bits")

rgb = assess_activation({"piscadas_por_min": 3.0, "duracao_mediana_ms": -2.5, "sacadas_por_min": 2.0,
                         "entropia_transicao_bits": 2.0}, {"fracao_valida_60s": 0.95}, 0.75, 0, 30.0)
assert rgb.state == "sinais_compativeis" and rgb.confidence_label == "media" and abs(rgb.confidence - 0.45) < 1e-6, rgb
assert assess_activation({"piscadas_por_min": 4.0}, {}, 0.75).state == "sem_sinais"
assert assess_activation(dict(rgb.contributions, piscadas_por_min=3.0, duracao_mediana_ms=-3.0, sacadas_por_min=3.0),
                         {}, 0.75, drowsiness_level=1).state == "sem_sinais"
assert assess_activation({"piscadas_por_min": 4.0}, {}, 0.0).state == "sem_dados"
lux = assess_activation({"pupila_iris": 3.0, "piscadas_por_min": 2.0}, {"pupila_fonte_luz": "lux"}, 1.0)
image = assess_activation({"pupila_iris": 3.0, "piscadas_por_min": 2.0}, {"pupila_fonte_luz": "imagem"}, 1.0)
assert lux.state == "sinais_compativeis" and image.confidence < lux.confidence
ok("ativação: 4 sinais convergindo em câmera RGB = compatível com confiança média; 1 sinal só, sonolência "
   "presente ou sem linha de base = nada")


# 6. Fusão: histerese, contexto e rebote.
def drowsy(level, reasons=(), alarm=False):
    return Assessment(level=level, reasons=list(reasons), alarm=alarm)


fusion = RiskFusion()
levels = [fusion.update(float(t), drowsy(2 if t < 10 else 0, ["x"])).level for t in range(200)]
assert levels[5] == 2 and levels[69] == 2 and levels[70] == 1 and levels[129] == 1 and levels[130] == 0, levels[60:135]
ok("histerese: risco alto cai para atenção 60 s depois do motivo sumir e para normal mais 60 s depois")

fusion = RiskFusion()
night = [fusion.update(float(t), drowsy(1, ["fechamento_longo"]), context={"madrugada": True}) for t in range(400)]
assert night[299].level == 1 and night[300].level == 2 and night[300].alarm
assert "sinais_leves_em_contexto_de_risco" in night[300].reasons
ok("madrugada: sinais leves por 5 min viram risco alto com alarme")

compatible = ActivationAssessment(index=0.8, confidence=0.5, confidence_label="media", state="sinais_compativeis",
                                  signals=["a", "b"])
calm = ActivationAssessment(index=0.1, confidence=0.5, confidence_label="media", state="sem_sinais")


def rebound(share):
    fusion = RiskFusion(share_activation=share)
    events = []
    for t in range(700):
        result = fusion.update(float(t), drowsy(0), activation=compatible)
        events += result.events
    sustained = result
    for t in range(700, 1900):
        fusion.update(float(t), drowsy(0), activation=calm)
    result = fusion.update(1900.0, drowsy(1, ["fechamento_longo"]), activation=calm)
    return sustained, events, result


sustained, early_events, result = rebound(share=False)
assert sustained.activation_sustained and sustained.level == 1 and not early_events
assert result.level == 2 and result.alarm and [e.alert_type for e in result.events] == ["sonolencia_abrupta"]
assert "ativacao" not in result.events[0].details
plain = RiskFusion().update(1900.0, drowsy(1, ["fechamento_longo"]))
assert plain.level == 1 and not plain.events
_, shared_events, shared = rebound(share=True)
assert [e.alert_type for e in shared_events] == ["ativacao_atipica"] and "ativacao" in shared.events[0].details
ok("rebote: 11 min de ativação e sonolência 20 min depois = risco alto na hora, com alarme; sem ativação fica em atenção")


# 7. Contexto da viagem.
telemetry = work / "telemetria.json"
clock = {"now": 1000.0}
context = DrivingContext(telemetry_path=telemetry, now=lambda: datetime(2026, 9, 10, 3, 0, tzinfo=timezone.utc),
                         wall_time=lambda: clock["now"])
t = 0.0
telemetry.write_text(json.dumps({"velocidade_kmh": 80, "atualizado_em": 999.0}), encoding="utf-8")
while t < 6 * 3600:
    context.update(t, face_found=False)
    t += 5.0
snapshot = context.snapshot()
assert snapshot["limite_direcao_excedido"] and snapshot["madrugada"] and snapshot["fonte_tempo_direcao"] == "telemetria"
telemetry.write_text(json.dumps({"velocidade_kmh": 0, "atualizado_em": 999.0}), encoding="utf-8")
end = t + 31 * 60
while t < end:
    context.update(t, face_found=True)
    t += 5.0
assert context.stopped and context.snapshot()["direcao_continua_h"] == 0.0
telemetry.write_text(json.dumps({"velocidade_kmh": 80, "atualizado_em": 100.0}), encoding="utf-8")
context.update(t + 5.0, face_found=True)
assert context.snapshot()["fonte_tempo_direcao"] == "camera"
assert DrivingContext(now=lambda: datetime(2000, 1, 1, 3, 0)).snapshot()["madrugada"] is None
ok("contexto: 6 h a 80 km/h passa do limite de 5 h 30; 30 min parado zera; telemetria velha é ignorada")


# 8. Privacidade e linha de base montada no fim da calibração.
def run_engine(mode, store=None):
    drowsiness = DrowsinessMonitor(calibrator=Calibrator(min_seconds=120, max_seconds=120, target_blinks=999))
    engine = DriverStateEngine(drowsiness, activation_mode=mode, baseline_store=store, background_baseline=False)
    schedule = blink_schedule(0.0, 150.0, random.Random(3)) + [(140.0, 1.5, "fechamento")]
    events = []
    for i in range(150 * 30):
        events += engine.update(person_frame(i / 30, sorted(schedule))).events
    return engine, events


store = BaselineStore(work / "consentido" / "motorista.json")
engine, events = run_engine("local", store)
assert engine.trip_baseline is not None and len(engine.trip_baseline.windows) >= 2
assert store.load() is not None and store.load().trips == 1
microsleep = next(e for e in events if e.alert_type == "microssono")
assert microsleep.details["nivel_risco"] == 3 and microsleep.details["nivel_risco_nome"] == "critico"
private = {"pupila_iris": 0.4, "entropia_olhar_bits": 2.0, "perclos_60s": 0.01}
assert set(engine._decorate(private, RiskAssessment(), None)) >= {"perclos_60s", "nivel_risco"}
assert not {"pupila_iris", "entropia_olhar_bits"} & set(engine._decorate(private, RiskAssessment(), None))
sharing, _ = run_engine("enviar")
assert "pupila_iris" in sharing._decorate(private, RiskAssessment(), None)
assert run_engine("desligado")[0].activation is None
ok("linha de base da viagem montada ao fim da calibração e salva com consentimento; eventos com nível de risco; "
   "métricas de ativação só saem no modo enviar")

legacy = work / "perfil_antigo.json"
legacy.write_text(json.dumps({"ear_open": 0.3, "ear_closed": 0.1, "blink_duration_median_s": 0.2}), encoding="utf-8")
assert DriverProfile.load(legacy).blink_closing_avr_median_s is None
ok("perfil salvo pela versão anterior continua abrindo")

print(f"\nTODOS OS {checks} TESTES PASSARAM (Python {sys.version.split()[0]})")
