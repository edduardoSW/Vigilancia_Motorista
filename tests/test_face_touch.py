"""Gestos de sono com as mãos (coçar os olhos e mão no rosto) com um detector falso de mãos e celular.

Precisa de numpy e opencv (requirements-device.txt):
    python tests/test_face_touch.py
"""
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from vision.drowsiness import Assessment, DrowsinessMonitor  # noqa: E402
from vision.engine import DriverStateEngine  # noqa: E402
from vision.eyes import Sample  # noqa: E402
from vision.face import FaceMetrics  # noqa: E402
from vision.face_touch import (  # noqa: E402
    HAND_ON_FACE,
    RUBBING,
    FaceTouchAssessment,
    FaceTouchTracker,
    eye_centers,
    nearest_eye,
    reversal_times,
    touches_upper_face,
)
from vision.phone import PhoneAssessment, PhoneMonitor, PhoneObservation  # noqa: E402
from vision.risk import RiskFusion  # noqa: E402

checks = 0


def ok(message):
    global checks
    checks += 1
    print(f"OK {checks:02d} {message}")


@dataclass
class Frame(Sample):
    face_box: tuple | None = None
    ear_points: object = None
    eye_points: object = None
    mar: float | None = None


FACE_BOX = (270.0, 120.0, 370.0, 250.0)  # rosto de 100 px de largura
EARS = np.array([(270.0, 180.0), (370.0, 180.0)], dtype=np.float32)
RIGHT_EYE, LEFT_EYE = (300.0, 170.0), (340.0, 170.0)
EYE_POINTS = np.array([(cx + 8 * math.cos(a), cy + 3 * math.sin(a)) for cx, cy in (RIGHT_EYE, LEFT_EYE)
                       for a in np.linspace(0, 2 * math.pi, 6, endpoint=False)], dtype=np.float32)
IMAGE = np.zeros((480, 640, 3), dtype=np.uint8)
PHONE_AT_EAR = (240.0, 150.0, 275.0, 215.0, 0.6)


def hand_at(x, y):
    """Mão falsa com os 21 pontos do Hand Landmarker (o formato real: com 20 pontos já deu IndexError)."""
    offsets = np.array([(dx, dy) for dx in (-12, -8, -4, 0, 4, 8, 12) for dy in (-10, 0, 10)], dtype=np.float32)
    return offsets + np.array([x, y], dtype=np.float32)


def rubbing(x, y, start, end, hz=1.5, amplitude=12.0):
    return lambda t: [hand_at(x + amplitude * math.sin(2 * math.pi * hz * t), y)] if start <= t < end else []


class FakeDetector:
    def __init__(self, script):
        self.script = script

    def detect(self, frame, timestamp, face_box=None):
        phones, hands = self.script(timestamp)
        return PhoneObservation(timestamp, phones, hands)

    def close(self):
        pass


def run(hands, seconds=12.0, phones=lambda t: [], face=lambda t: True, fps=30.0):
    monitor = PhoneMonitor(FakeDetector(lambda t: (phones(t), hands(t))), background=False)
    results = []
    for i in range(int(seconds * fps)):
        t = i / fps
        frame = Frame(timestamp=t, face_found=face(t), pitch=0.0, yaw=0.0, gaze_y=0.0, face_box=FACE_BOX,
                      ear_points=EARS, eye_points=EYE_POINTS)
        results.append(monitor.update(frame, IMAGE))
    return monitor, results


def events(results, types=(RUBBING, HAND_ON_FACE)):
    return [event for result in results for event in result.events if event.alert_type in types]


def names(results):
    return [event.alert_type for event in events(results)]


centers = eye_centers(Frame(timestamp=0.0, face_found=True, eye_points=EYE_POINTS))
assert np.allclose(centers[0], RIGHT_EYE, atol=0.5) and np.allclose(centers[1], LEFT_EYE, atol=0.5)
assert nearest_eye(hand_at(300, 172), centers, 100.0) == 0 and nearest_eye(hand_at(340, 172), centers, 100.0) == 1
assert nearest_eye(hand_at(320, 135), centers, 100.0) is None
assert touches_upper_face(hand_at(320, 135), FACE_BOX)
assert not touches_upper_face(hand_at(262, 175), FACE_BOX) and not touches_upper_face(hand_at(320, 225), FACE_BOX)
zigzag = [(i * 0.25, 300 + 10 * math.sin(2 * math.pi * 1.5 * i * 0.25), 172.0) for i in range(8)]
straight = [(i * 0.25, 300 + 5.0 * i, 172.0) for i in range(8)]
still = [(i * 0.25, 300 + (1.5 if i % 2 else -1.5), 172.0) for i in range(8)]
assert len(reversal_times(zigzag, 100.0)) >= 2 and reversal_times(straight, 100.0) == []
assert reversal_times(still, 100.0) == []
ok("geometria: dedo perto de cada olho, contato na testa e fora na orelha e na boca, vai e vem x tremor")

monitor, rub = run(rubbing(300, 172, 5.0, 7.0))
assert names(rub) == [RUBBING], names(rub)
assert rub[-1].face_touch.rubs_10min == 1 and rub[-1].face_touch.touches_10min == 0
assert any(r.face_touch.gesture == RUBBING and r.face_touch.eye_covered for r in rub)
assert not rub[-1].face_touch.eye_covered and rub[-1].state == "sem_celular"
event = events(rub)[0]
assert event.risk_level == 1 and event.details["lado"] == "direito" and event.details["inversoes"] >= 2
assert monitor.face_touch.window_metrics(12.0) == {"coceiras_olhos_10min": 1, "maos_no_rosto_10min": 0}
ok(f"esfregar o olho direito por 2 s: 1 episódio, {event.details['inversoes']} inversões, olho marcado como tapado")

_, forehead = run(lambda t: [hand_at(320, 135)] if 5.0 <= t < 8.0 else [])
assert names(forehead) == [HAND_ON_FACE] and forehead[-1].face_touch.touches_10min == 1
assert not any(r.face_touch.eye_covered for r in forehead)
ok("mão parada na testa por 3 s: mão no rosto, sem desligar as medidas do olho")

_, glasses = run(lambda t: [hand_at(320, 160)] if 5.0 <= t < 5.8 else [])
_, eating = run(lambda t: [hand_at(320, 225)] if t >= 5.0 else [])
_, ear = run(lambda t: [hand_at(262 + 5 * math.sin(6 * t), 175)] if t >= 5.0 else [])
_, wipe = run(lambda t: [hand_at(360 - 80 * (t - 5.0), 135)] if 5.0 <= t < 5.8 else [])
assert not names(glasses) and not names(eating) and not names(ear) and not names(wipe), (
    names(glasses), names(eating), names(ear), names(wipe))
ok("não contam: ajustar os óculos (0,8 s), comer ou beber, coçar a orelha, passar a mão na testa")

_, on_phone = run(lambda t: [hand_at(262, 175), hand_at(320, 135)] if t >= 5.0 else [],
                  phones=lambda t: [PHONE_AT_EAR] if t >= 5.0 else [])
assert on_phone[-1].state == "celular_no_ouvido" and not names(on_phone), names(on_phone)
_, holding = run(lambda t: [hand_at(300, 172)] if t >= 5.0 else [],
                 phones=lambda t: [(280.0, 150.0, 320.0, 200.0, 0.7)] if t >= 5.0 else [])
assert not names(holding) and not any(r.face_touch.eye_covered for r in holding), names(holding)
ok("com o celular no ouvido, ou com a mão segurando o celular perto do olho, nada conta")

_, merged = run(lambda t: rubbing(300, 172, 5.0, 6.5)(t) or rubbing(300, 172, 7.5, 9.0)(t), seconds=14.0)
_, apart = run(lambda t: rubbing(300, 172, 5.0, 6.5)(t) or rubbing(300, 172, 9.5, 11.0)(t), seconds=15.0)
assert merged[-1].face_touch.rubs_10min == 1, merged[-1].face_touch
assert apart[-1].face_touch.rubs_10min == 2 and names(apart) == [RUBBING], (apart[-1].face_touch, names(apart))
ok("gestos a 1 s de distância viram 1 episódio; a 3 s, 2 episódios (e 1 evento só, pelo intervalo entre avisos)")

_, long_rub = run(rubbing(300, 172, 5.0, 12.0), seconds=16.0)
assert names(long_rub) == [HAND_ON_FACE], names(long_rub)
ok("vai e vem no olho por mais de 5 s conta como mão no rosto, não como coçar")

_, covered = run(rubbing(340, 172, 5.0, 7.0), face=lambda t: not 5.5 <= t < 6.5)
assert names(covered) == [RUBBING], names(covered)
assert events(covered)[0].details["lado"] == "esquerdo" and events(covered)[0].details["fracao_olho_encoberto"] > 0
ok("mão tapando o rosto (pontos do rosto perdidos por 1 s) continua contando, com o olho marcado como encoberto")

fusion_with, fusion_without, fusion_alone = RiskFusion(), RiskFusion(), RiskFusion()
mild = Assessment(face_found=True)
mild.level, mild.reasons = 1, ["bocejos"]
awake = Assessment(face_found=True)
gestures = PhoneAssessment(face_touch=FaceTouchAssessment(rubs_10min=3))
touches_only = PhoneAssessment(face_touch=FaceTouchAssessment(rubs_10min=2, touches_10min=6))
fusion_touches = RiskFusion()
levels = {}
for second in range(0, 331):
    levels["com"] = fusion_with.update(float(second), mild, phone=gestures).level
    levels["sem"] = fusion_without.update(float(second), mild, phone=PhoneAssessment(face_touch=FaceTouchAssessment())).level
    levels["sozinho"] = fusion_alone.update(float(second), awake, phone=gestures).level
    levels["mao_no_rosto"] = fusion_touches.update(float(second), mild, phone=touches_only).level
assert levels == {"com": 2, "sem": 1, "sozinho": 0, "mao_no_rosto": 1}, levels
ok("3 olhos esfregados em 10 min com sinal leve de sono: risco alto em 5 min; mão parada no rosto não pesa; sozinhos, nada")

def engine_alerts(hands, face, seconds=20.0, fps=15.0):
    engine = DriverStateEngine(DrowsinessMonitor(), activation_mode="desligado", background_baseline=False,
                               phone=PhoneMonitor(FakeDetector(lambda t: ([], hands(t))), background=False))
    alerts = []
    for i in range(int(seconds * fps)):
        t = i / fps
        found = face(t)
        metrics = FaceMetrics(timestamp=t, face_found=found, ear_left=0.3 if found else None,
                              ear_right=0.3 if found else None, pitch=0.0 if found else None,
                              yaw=0.0 if found else None, eye_points=EYE_POINTS if found else None,
                              face_box=FACE_BOX if found else None, ear_points=EARS if found else None)
        alerts += [event.alert_type for event in engine.update(metrics, IMAGE).events]
    return alerts


hidden = engine_alerts(lambda t: [hand_at(320, 150)] if 2.0 <= t < 15.0 else [], face=lambda t: not 3.0 <= t < 16.0)
lost = engine_alerts(lambda t: [], face=lambda t: not 3.0 <= t < 16.0)
assert "rosto_nao_detectado" not in hidden and HAND_ON_FACE in hidden, hidden
assert "rosto_nao_detectado" in lost, lost
ok("mão tapando o rosto por 13 s é mão no rosto, não 'rosto não detectado'; sem mão, o aviso sai em 10 s")

episodes = list(monitor.face_touch.episodes)
assert len(episodes) == 1 and episodes[0]["gesto"] == RUBBING and episodes[0]["lado"] == "direito"
assert episodes[0]["inicio_s"] < episodes[0]["fim_s"] and episodes[0]["inversoes"] >= 2
open_monitor, _ = run(lambda t: [hand_at(320, 135)] if t >= 10.0 else [])
assert not open_monitor.face_touch.episodes
open_monitor.close()
assert [episode["gesto"] for episode in open_monitor.face_touch.episodes] == [HAND_ON_FACE]
ok("episódios fechados ficam guardados para o _gestos.csv; o que está aberto no fim do vídeo fecha no close()")

tracker = FaceTouchTracker()
frame = Frame(timestamp=0.0, face_found=True, face_box=FACE_BOX, eye_points=EYE_POINTS)
assert tracker.update(0.0, frame, None).episodes_10min == 0 and tracker.window_metrics(0.0)["maos_no_rosto_10min"] == 0
ok("rastreador sem mãos: nenhum gesto e métricas da janela zeradas")

print(f"\nTODOS OS {checks} TESTES PASSARAM (Python {sys.version.split()[0]})")
