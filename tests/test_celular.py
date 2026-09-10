"""Celular: regras de tempo com um detector falso e, se o MediaPipe estiver instalado, os modelos reais.

Precisa de numpy e opencv (requirements-device.txt):
    python tests/test_celular.py
"""
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from vision.eyes import Sample  # noqa: E402
from vision.phone import (  # noqa: E402
    PhoneMonitor,
    PhoneObservation,
    driver_roi,
    hand_near_ear,
    hand_touches_phone,
    phone_near_ear,
)

checks = 0


def ok(message):
    global checks
    checks += 1
    print(f"OK {checks:02d} {message}")


@dataclass
class Frame(Sample):
    face_box: tuple | None = None
    ear_points: object = None
    mar: float | None = None


FACE_BOX = (270.0, 120.0, 370.0, 250.0)  # rosto de 100 px de largura
EARS = np.array([(270.0, 180.0), (370.0, 180.0)], dtype=np.float32)
IMAGE = np.zeros((480, 640, 3), dtype=np.uint8)
PHONE_IN_HAND = (300.0, 330.0, 340.0, 400.0, 0.7)
PHONE_AT_EAR = (240.0, 150.0, 275.0, 215.0, 0.6)


def hand_at(x, y):
    offsets = np.array([(dx, dy) for dx in (-12, -8, -4, 0, 4, 8, 12) for dy in (-10, 0, 10)], dtype=np.float32)
    return offsets + np.array([x, y], dtype=np.float32)


class FakeDetector:
    def __init__(self, script):
        self.script = script
        self.calls = 0

    def detect(self, frame, timestamp, face_box=None):
        self.calls += 1
        phones, hands = self.script(timestamp)
        return PhoneObservation(timestamp, phones, hands)

    def close(self):
        pass


def run(script, seconds=12.0, pitch=lambda t: 0.0, mar=lambda t: 0.10, moving=True, fps=30.0):
    monitor = PhoneMonitor(FakeDetector(script), background=False)
    results = []
    for i in range(int(seconds * fps)):
        t = i / fps
        frame = Frame(timestamp=t, face_found=True, pitch=pitch(t), yaw=0.0, gaze_y=0.0, face_box=FACE_BOX,
                      ear_points=EARS, mar=mar(t))
        results.append(monitor.update(frame, IMAGE, moving=moving))
    return results


def events(results):
    return [event.alert_type for result in results for event in result.events]


def after(start):
    return lambda script: (lambda t: script(t) if t >= start else ([], []))


assert hand_touches_phone(hand_at(320, 370), PHONE_IN_HAND) and not hand_touches_phone(hand_at(500, 370), PHONE_IN_HAND)
assert hand_near_ear(hand_at(262, 175), EARS, 100.0) and not hand_near_ear(hand_at(320, 380), EARS, 100.0)
assert driver_roi(FACE_BOX, IMAGE.shape) == (160, 42, 480, 480) and driver_roi(None, IMAGE.shape) == (0, 0, 640, 480)
ok("geometria: mão no aparelho, mão na orelha e recorte do motorista")

nothing = run(lambda t: ([], []))
assert all(r.state == "sem_celular" and r.risk_level == 0 for r in nothing) and not events(nothing)
ok("sem celular: nenhum estado, risco ou evento")

holding = run(after(5.0)(lambda t: ([PHONE_IN_HAND], [hand_at(320, 370)])))
assert holding[-1].state == "celular_na_mao" and holding[-1].risk_level == 1 and events(holding) == ["celular_na_mao"]
assert not any(r.alarm for r in holding) and holding[int(7.5 * 30)].risk_level == 0
ok("celular na mão por mais de 3 s: evento e risco de atenção, sem alarme")

looking = run(after(5.0)(lambda t: ([PHONE_IN_HAND], [hand_at(320, 370)])), pitch=lambda t: 25.0 if t >= 5.0 else 0.0)
first_alarm = next(i for i, r in enumerate(looking) if r.alarm) / 30.0
assert looking[-1].state == "olhando_celular" and looking[-1].risk_level == 2 and "olhando_celular" in events(looking)
assert 7.0 <= first_alarm <= 7.6, first_alarm
ok(f"olhando o celular com a cabeça baixa: alarme em {first_alarm - 5.0:.1f} s (limite de 2 s da NHTSA)")

at_ear = run(after(5.0)(lambda t: ([PHONE_AT_EAR], [hand_at(262, 175)])))
assert at_ear[-1].state == "celular_no_ouvido" and at_ear[-1].risk_level == 2 and events(at_ear) == ["celular_no_ouvido"]
assert any(r.alarm for r in at_ear)
ok("celular no ouvido por mais de 3 s: evento, risco alto e alarme")

scratching = run(after(5.0)(lambda t: ([], [hand_at(262, 175)])))
assert all(r.state == "sem_celular" for r in scratching)
talking = run(after(5.0)(lambda t: ([], [hand_at(262, 175)])), mar=lambda t: 0.1 + 0.08 * ((int(t * 6) % 2) * 2 - 1))
assert all(r.state == "sem_celular" for r in talking)
put_away = run(lambda t: ([PHONE_IN_HAND], [hand_at(320, 370)]) if 5.0 <= t < 6.0
               else ([], [hand_at(262, 175)]) if t >= 6.0 else ([], []))
assert put_away[-1].state == "sem_celular" and "celular_no_ouvido" not in events(put_away), events(put_away)
ok("mão vazia na orelha não é celular: nem falando, nem logo depois de guardar o aparelho")

covered = run(lambda t: ([PHONE_AT_EAR], [hand_at(262, 175)]) if 5.0 <= t < 6.5
              else ([], [hand_at(262, 175)]) if t >= 6.5 else ([], []))
assert "celular_no_ouvido" in events(covered), events(covered)
ok("celular visto na orelha e depois tapado pela mão continua 'no ouvido' por alguns segundos")

switch = run(lambda t: ([PHONE_IN_HAND], [hand_at(320, 370)]) if 5.0 <= t < 7.9
             else ([PHONE_AT_EAR], [hand_at(262, 175)]) if t >= 7.9 else ([], []), seconds=13.0)
ear_alert_at = next(i for i, r in enumerate(switch) if any(e.alert_type == "celular_no_ouvido" for e in r.events)) / 30.0
assert "celular_na_mao" not in events(switch) and ear_alert_at >= 10.8, (events(switch), ear_alert_at)
ok(f"da mão (2,9 s) para o ouvido: cada estado conta o próprio tempo; 'no ouvido' só {ear_alert_at - 7.9:.1f} s depois")

PHONE_AT_CHIN = (240.0, 208.0, 275.0, 268.0, 0.6)  # na mão, do lado do rosto, na altura do queixo
assert phone_near_ear(PHONE_AT_EAR, EARS, 100.0) and not phone_near_ear(PHONE_AT_CHIN, EARS, 100.0)
chin = run(after(5.0)(lambda t: ([PHONE_AT_CHIN], [hand_at(257, 238)])))
assert chin[-1].state == "celular_na_mao" and events(chin) == ["celular_na_mao"], events(chin)
other_hand = run(after(5.0)(lambda t: ([PHONE_IN_HAND], [hand_at(320, 370), hand_at(262, 175)])))
assert other_hand[-1].state == "celular_na_mao" and events(other_hand) == ["celular_na_mao"], events(other_hand)
ok("celular na mão na altura do queixo, ou com a outra mão na orelha, continua 'na mão'")

mounted = run(after(5.0)(lambda t: ([PHONE_IN_HAND], [])))
assert all(r.state == "sem_celular" for r in mounted)
shaking = run(after(5.0)(lambda t: ([(300.0 + 12 * math.sin(3 * t), 330.0, 340.0 + 12 * math.sin(3 * t), 400.0, 0.7)], [])))
assert shaking[-1].state == "celular_na_mao"
ok("celular parado sem mão (suporte) não conta; celular se mexendo conta mesmo sem achar a mão")

flicker = run(lambda t: ([PHONE_IN_HAND], [hand_at(320, 370)]) if 5.0 <= t < 5.2 else ([], []))
assert all(r.state == "sem_celular" for r in flicker)
parked = run(after(5.0)(lambda t: ([PHONE_IN_HAND], [hand_at(320, 370)])), pitch=lambda t: 25.0, moving=False)
assert not events(parked) and not any(r.risk_level or r.alarm for r in parked)
ok("uma detecção solta não confirma celular; veículo parado pela telemetria não gera alerta")

detector = FakeDetector(lambda t: ([PHONE_IN_HAND], [hand_at(320, 370)]))
monitor = PhoneMonitor(detector, background=True, every_s=0.05)
start = time.monotonic()
while time.monotonic() - start < 1.5 and monitor.last_observation is None:
    t = time.monotonic() - start
    monitor.update(Frame(timestamp=t, face_found=True, pitch=0.0, face_box=FACE_BOX, ear_points=EARS), IMAGE)
    time.sleep(0.01)
monitor.close()
assert monitor.last_observation is not None and detector.calls >= 1
ok("detecção em thread separada devolve resultado ao loop principal")

try:
    from vision.phone import PhoneDetector
    real = PhoneDetector()
except RuntimeError as exc:
    print(f"-- modelos reais não testados ({exc})")
else:
    observation = real.detect(IMAGE, 0.0, FACE_BOX)
    real.close()
    assert observation.phones == [] and observation.hands == []
    ok("modelos reais (EfficientDet-Lite0 + Hand Landmarker) carregam e rodam num quadro vazio")

print(f"\nTODOS OS {checks} TESTES PASSARAM (Python {sys.version.split()[0]})")
