"""Calibração, sinais do olho e níveis de sonolência com sinais sintéticos.

Só usa a biblioteca padrão (não precisa de câmera, OpenCV nem MediaPipe):
    python tests/test_detector.py
"""
import math
import random
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from vision.calibration import Calibrator  # noqa: E402
from vision.drowsiness import DrowsinessMonitor  # noqa: E402
from vision.eyes import DriverProfile, OpennessModel, Sample  # noqa: E402

checks = 0


def ok(message):
    global checks
    checks += 1
    print(f"OK {checks:02d} {message}")


class Person:
    def __init__(self, ear_open, ear_closed, score_open=0.05, score_closed=0.9):
        self.ear_open, self.ear_closed = ear_open, ear_closed
        self.score_open, self.score_closed = score_open, score_closed


def openness_at(t, events):
    """events: (início, duração, tipo). 'piscada' = mergulho sin²; 'fechamento' = rampa, platô fechado, rampa."""
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


def blink_schedule(start, seconds, rng, every=3.5, duration=0.30, duration_jitter=0.05):
    events, t = [], start + 1.0
    while t < start + seconds - 1.0:
        events.append((t, max(0.12, rng.gauss(duration, duration_jitter)), "piscada"))
        t += max(1.0, rng.gauss(every, 0.8))
    return events


def run(monitor, person, start, seconds, events, fps=30.0, pitch=0.0, face=True,
        score_override=None, ear_scale=1.0, signals=("ear", "score")):
    assessments = []
    for i in range(int(seconds * fps)):
        t = start + i / fps
        o = openness_at(t, events)
        ear = (person.ear_closed + o * (person.ear_open - person.ear_closed)) * ear_scale
        score = person.score_open + (1.0 - o) * (person.score_closed - person.score_open)
        if score_override is not None:
            score = score_override
        sample = Sample(
            timestamp=t, face_found=face,
            ear=ear if face and "ear" in signals else None,
            blink_score=score if face and "score" in signals else None,
            eye_open_prob=(0.05 + 0.93 * o) if face and "classifier" in signals else None,
            jaw_open=0.02 if face else None, pitch=pitch if face else None, yaw=0.0 if face else None,
            eye_distance_px=90.0 if face else None,
        )
        assessments.append(monitor.update(sample))
    return assessments


def events_of(assessments):
    return [event for a in assessments for event in a.events]


rng = random.Random(42)
small_eyes = Person(ear_open=0.20, ear_closed=0.05)

calibrator = Calibrator(min_seconds=300, max_seconds=600, target_blinks=80)
profile_path = Path(tempfile.mkdtemp()) / "perfis" / "teste.json"
monitor = DrowsinessMonitor(calibrator=calibrator, profile_path=profile_path)
schedule = blink_schedule(0.0, 320.0, rng)
result = run(monitor, small_eyes, 0.0, 320.0, schedule)
calibration_events = [e for e in events_of(result) if e.alert_type.startswith("calibracao")]
assert [e.alert_type for e in calibration_events] == ["calibracao_concluida"], calibration_events
profile = monitor.profile
assert abs(profile.ear_open - 0.20) < 0.01, profile.ear_open
assert profile.ear_closed < 0.09 and not profile.ear_closed_estimated, profile.ear_closed
generated = sorted(duration for start, duration, _kind in schedule if start < 300)
expected_ms = 0.532 * generated[len(generated) // 2] * 1000  # medido entre 50% fechando e 60% reabrindo
measured_ms = profile.blink_duration_median_s * 1000
assert abs(measured_ms - expected_ms) < 34, (measured_ms, expected_ms)
assert 13 <= profile.blink_rate_per_min <= 21, profile.blink_rate_per_min
assert profile.perclos_baseline < 0.02 and profile.looked_alert
assert profile_path.is_file() and DriverProfile.load(profile_path).ear_open == profile.ear_open
ok(f"calibração de olho pequeno: aberto {profile.ear_open:.3f}, fechado {profile.ear_closed:.3f}, "
   f"{profile.blink_rate_per_min:.1f} piscadas/min, duração {measured_ms:.0f} ms (esperado {expected_ms:.0f})")

normal = run(monitor, small_eyes, 400.0, 120.0, [])
assert all(a.closed_for == 0 for a in normal) and not events_of(normal)
assert all(a.level == 0 for a in normal)
ok("olho pequeno aberto: nenhum quadro fechado e nenhum alerta em 2 min (limiar fixo de EAR 0,2 falharia)")

for seconds, expected in ((1.5, ["microssono"]), (3.5, ["microssono", "sono"]),
                          (6.5, ["microssono", "sono", "nao_responsivo"])):
    start = 600.0 + seconds * 100
    out = run(monitor, small_eyes, start, seconds + 3.0, [(start + 1.0, seconds, "fechamento")])
    critical = [e.alert_type for e in events_of(out) if e.alert_type in ("microssono", "sono", "nao_responsivo")]
    assert critical == expected, (seconds, critical)
    assert any(a.level == 3 and a.alarm for a in out)
ok("fechamentos de 1,5 s / 3,5 s / 6,5 s geram microssono / +sono / +sem resposta, com alarme")

fresh = DrowsinessMonitor(calibrator=Calibrator())
out = run(fresh, small_eyes, 0.0, 15.0, [(10.0, 1.3, "fechamento")])
assert [e.alert_type for e in events_of(out)] == ["microssono"], events_of(out)
assert out[-1].calibrating
ok("durante a calibração, sem perfil, um fechamento de 1,3 s já dispara microssono")

out = run(monitor, small_eyes, 2000.0, 10.0, [], pitch=35.0, ear_scale=0.3, score_override=0.08)
assert all(a.closed_for == 0 for a in out) and not events_of(out)
ok("cabeça baixa com EAR distorcido e olho aberto pela pontuação: não conta como fechado")

drowsy = blink_schedule(3000.0, 300.0, rng, duration=0.435)
drowsy += [(3100.0, 0.6, "fechamento"), (3180.0, 0.6, "fechamento"), (3260.0, 0.6, "fechamento")]
out = run(monitor, small_eyes, 3000.0, 300.0, sorted(drowsy))
level_events = [e for e in events_of(out) if e.alert_type in ("atencao", "sonolencia")]
assert any(e.alert_type == "sonolencia" for e in level_events), level_events
ok("piscadas 45% mais longas por 5 min viram alerta de sonolência")

out = run(monitor, small_eyes, 5000.0, 12.0, [], face=False)
assert [e.alert_type for e in events_of(out)] == ["rosto_nao_detectado"]
ok("rosto sumido por mais de 10 s gera aviso de sistema sem visão")

low = DrowsinessMonitor(profile=profile)
run(low, small_eyes, 0.0, 330.0, blink_schedule(0.0, 330.0, rng), fps=15.0)
assert "duracao_mediana_ms" not in low._window_details(330.0)
ok("a 15 fps a duração da piscada não é usada como gatilho")

tired = DrowsinessMonitor(calibrator=Calibrator(min_seconds=120, max_seconds=120, target_blinks=999))
out = run(tired, small_eyes, 0.0, 130.0, [(t, 0.45, "fechamento") for t in range(2, 125, 3)])
assert [e.alert_type for e in events_of(out) if e.alert_type.startswith("calibracao")] == ["calibracao_suspeita"]
ok("calibração com olhos fechando demais é marcada como suspeita")

classifier_only = DrowsinessMonitor()
out = run(classifier_only, small_eyes, 0.0, 6.0, [(3.0, 1.3, "fechamento")], signals=("classifier",))
assert [e.alert_type for e in events_of(out)] == ["microssono"], events_of(out)
ok("modo só com classificador (YuNet): fechamento de 1,3 s dispara microssono")

model = OpennessModel(DriverProfile(ear_open=0.20, ear_closed=0.05, score_open=0.05, score_closed=0.9))
closed_by_two = Sample(timestamp=0, face_found=True, ear=0.05, blink_score=0.9, eye_open_prob=0.95, eye_distance_px=90)
open_by_two = Sample(timestamp=0, face_found=True, ear=0.20, blink_score=0.05, eye_open_prob=0.05, eye_distance_px=90)
assert model.openness(closed_by_two)[0] <= 0.2 and model.openness(open_by_two)[0] >= 0.9
ok("três sinais: vale a maioria (um sinal discordando sozinho não decide)")

print(f"\nTODOS OS {checks} TESTES PASSARAM (Python {sys.version.split()[0]})")
