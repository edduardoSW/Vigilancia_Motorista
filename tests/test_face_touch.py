"""Gestos de sono com as mãos (coçar os olhos e mão no rosto) com um detector falso de mãos e celular.

Precisa de numpy e opencv (caixa/requirements.txt):
    python tests/test_face_touch.py
"""
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "caixa"))
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

# --- GES-xx (20/10/2026, "coçar os olhos não está pegando muito bem", teste do Matheus com a webcam do notebook) ---
# Mão com a anatomia dos 21 pontos do Hand Landmarker: punho 0, polegar 1-4, indicador 5-8, médio 9-12, anelar 13-16,
# mínimo 17-20. Pixels para o rosto de 100 px (~14 cm: 1 cm ≈ 7 px), punho na origem, dedos para cima.
OPEN_HAND = np.array([(0, 0), (-18, -10), (-30, -22), (-38, -34), (-44, -44),
                      (-20, -70), (-22, -95), (-23, -110), (-24, -122),
                      (-3, -72), (-3, -100), (-3, -116), (-3, -130),
                      (14, -68), (16, -93), (17, -107), (18, -118),
                      (28, -60), (32, -78), (34, -89), (36, -98)], dtype=np.float32)
# Punho fechado: os nós do meio (6, 10, 14, 18) na frente, as pontas dobradas para a palma.
FIST = np.array([(0, 0), (-18, -10), (-28, -25), (-26, -40), (-15, -50),
                 (-20, -70), (-22, -88), (-21, -75), (-18, -62),
                 (-3, -72), (-3, -92), (-3, -78), (-2, -64),
                 (14, -68), (15, -86), (15, -73), (14, -60),
                 (28, -60), (30, -74), (29, -64), (27, -54)], dtype=np.float32)
KNUCKLES = (6, 10)
# Apontando: indicador esticado, os outros dedos dobrados (empurrar os óculos, coçar o nariz).
POINTING = FIST.copy()
POINTING[5:9] = OPEN_HAND[5:9]


def posed(template, index, at, angle=0.0):
    """A mão girada `angle` graus, com o ponto `index` (ou a média dos pontos de `index`) em `at`."""
    indices = [index] if isinstance(index, int) else list(index)
    a = math.radians(angle)
    rotation = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]], dtype=np.float32)
    points = template @ rotation.T
    return points - points[indices].mean(axis=0) + np.array(at, dtype=np.float32)


def knuckle_rub(eye, start, end, hz=3.5, amplitude=10.0):
    """Esfregar com os nós dos dedos (punho) em cima do olho, num vai e vem horizontal."""
    return lambda t: ([posed(FIST, KNUCKLES, (eye[0] + amplitude * math.sin(2 * math.pi * hz * t), eye[1] + 2.0))]
                      if start <= t < end else [])


def rubs(results):
    return results[-1].face_touch.rubs_10min


# GES-01: o rosto some enquanto a mão cobre o olho e o vai e vem é rápido (3,5 por s, medido 3,75 vezes por s: aparece
# como um desvio lento). Hoje virava "mão no rosto". Vale a última posição do olho e a mão cobrindo o olho por 0,8 s.
_, ges01 = run(knuckle_rub(RIGHT_EYE, 5.0, 7.0), face=lambda t: not 5.3 <= t < 7.2)
assert names(ges01) == [RUBBING], ("GES-01", names(ges01))
assert events(ges01)[0].details["lado"] == "direito" and events(ges01)[0].details["fracao_olho_encoberto"] >= 0.5
ok("GES-01 esfregar com os nós dos dedos e o rosto sumindo enquanto a mão cobre o olho: conta, olho direito")

# GES-02: com o rosto à vista, esfregar a 2, 2,5, 3, 3,5 e 4 vai e vens por segundo conta sempre. Com as mãos medidas
# 3,75 vezes por s, 3,5 e 4 por s quase não mostram o vai e vem (subamostragem): a mão cobrindo o olho decide.
for hz in (2.0, 2.5, 3.0, 3.5, 4.0):
    _, ges02 = run(knuckle_rub(LEFT_EYE, 5.0, 7.0, hz=hz))
    assert names(ges02) == [RUBBING], ("GES-02", hz, names(ges02))
ok("GES-02 esfregar a 2 a 4 vai e vens por segundo, com o rosto à vista: conta em todas as frequências")

# GES-03: qualquer dedo, nó ou dorso perto do olho vale (polegar, anelar, mínimo, dorso), não só indicador e médio.
for index in (2, 3, 4, 5, 9, 13, 14, 16, 17, 18, 20):
    hand = posed(OPEN_HAND, index, RIGHT_EYE, angle=-75.0)
    assert nearest_eye(hand, centers, 100.0) == 0, ("GES-03", index)
thumb = lambda t: ([posed(OPEN_HAND, 4, (RIGHT_EYE[0] + 8.0 * math.sin(2 * math.pi * 1.5 * t), RIGHT_EYE[1]),
                          angle=-75.0)] if 5.0 <= t < 7.0 else [])
_, ges03 = run(thumb)
assert names(ges03) == [RUBBING], ("GES-03", names(ges03))
ok("GES-03 polegar esfregando o olho com a mão por cima da testa: conta; qualquer ponta, nó ou dorso vale")

# GES-04: ajeitar os óculos na ponte do nariz (rápido, olho à vista) não é coçar o olho: com a mão aberta em 0,7 s,
# e com o indicador esticado (os outros dedos dobrados) mesmo demorando 1,2 s.
glasses_push = lambda template, end: (lambda t: [posed(template, 8, (320.0, 166.0 - 6.0 * min(1.0, (t - 5.0) / (end - 5.0))))]
                                      if 5.0 <= t < end else [])
_, ges04_open = run(glasses_push(OPEN_HAND, 5.7))
_, ges04_fast = run(glasses_push(POINTING, 5.7))
_, ges04_slow = run(glasses_push(POINTING, 6.2))
assert not names(ges04_open) and not names(ges04_fast) and RUBBING not in names(ges04_slow), (
    "GES-04", names(ges04_open), names(ges04_fast), names(ges04_slow))
assert not any(r.face_touch.gesture == RUBBING for r in ges04_open + ges04_fast + ges04_slow)
ok("GES-04 ajeitar os óculos na ponte do nariz (0,7 s com a mão aberta; 0,7 s e 1,2 s apontando): não é olho esfregado")

# GES-05: coçar o lado do nariz, abaixo dos olhos, em vai e vem por 2,5 s: no máximo mão no rosto, nunca olho esfregado.
nose = lambda t: ([posed(POINTING, 8, (310.0, 200.0 + 6.0 * math.sin(2 * math.pi * 2.0 * t)))]
                  if 5.0 <= t < 7.5 else [])
_, ges05 = run(nose)
assert RUBBING not in names(ges05) and not any(r.face_touch.gesture == RUBBING for r in ges05), ("GES-05", names(ges05))
ok(f"GES-05 coçar o nariz por 2,5 s: não é olho esfregado ({names(ges05) or 'nada'})")

# GES-06: dois esfregões com o rosto sumindo, separados por 2,5 s: 2 na contagem de 10 min, 1 evento (60 s entre avisos).
two = lambda t: knuckle_rub(RIGHT_EYE, 5.0, 7.0)(t) or knuckle_rub(RIGHT_EYE, 9.5, 11.5)(t)
_, ges06 = run(two, seconds=15.0, face=lambda t: not (5.3 <= t < 7.2 or 9.8 <= t < 11.7))
assert rubs(ges06) == 2 and names(ges06) == [RUBBING], ("GES-06", ges06[-1].face_touch, names(ges06))
ok("GES-06 dois esfregões com 2,5 s de intervalo: contam 2, com 1 evento só pelo intervalo entre avisos")

# GES-07: mão no queixo e mão passando na frente dos olhos (0,6 s, rosto some na passagem) não contam.
_, ges07_chin = run(lambda t: [posed(FIST, KNUCKLES, (320.0, 262.0))] if 5.0 <= t < 8.0 else [])
_, ges07_pass = run(lambda t: [posed(OPEN_HAND, 9, (200.0 + 400.0 * (t - 5.0), 175.0))] if 5.0 <= t < 5.6 else [],
                    face=lambda t: not 5.1 <= t < 5.6)
assert not names(ges07_chin) and not names(ges07_pass), ("GES-07", names(ges07_chin), names(ges07_pass))
ok("GES-07 mão no queixo por 3 s e mão passando na frente dos olhos: nada conta")

# GES-08: o olho guardado vale por até 1,5 s antes de a mão chegar; depois disso, sem rosto, nada conta.
_, ges08_recent = run(knuckle_rub(RIGHT_EYE, 6.0, 8.0), face=lambda t: t < 5.0)
_, ges08_old = run(knuckle_rub(RIGHT_EYE, 6.8, 8.8), face=lambda t: t < 5.0)
assert names(ges08_recent) == [RUBBING] and not names(ges08_old), ("GES-08", names(ges08_recent), names(ges08_old))
ok("GES-08 rosto perdido 1 s antes da mão chegar: conta; 1,8 s antes: não conta (olho guardado só por 1,5 s)")

# GES-09: sem os pontos do olho mas com a caixa do rosto (o rosto andou 40 px), o olho sai da caixa: posição relativa
# guardada do último quadro com os olhos.
tracker = FaceTouchTracker()
moved_box = (FACE_BOX[0] + 40.0, FACE_BOX[1], FACE_BOX[2] + 40.0, FACE_BOX[3])
moved_eye = (RIGHT_EYE[0] + 40.0, RIGHT_EYE[1])
tracked = []
for i in range(int(12 * 30)):
    t = i / 30.0
    if t < 4.0:
        frame = Frame(timestamp=t, face_found=True, face_box=FACE_BOX, eye_points=EYE_POINTS)
    else:
        frame = Frame(timestamp=t, face_found=True, face_box=moved_box, eye_points=None)
    hands = knuckle_rub(moved_eye, 5.0, 7.0)(t) if i % 8 == 0 else None
    tracked += [event.alert_type for event in tracker.update(t, frame, hands).events]
assert tracked == [RUBBING], ("GES-09", tracked)
assert tracker.episodes[0]["lado"] == "direito"
ok("GES-09 sem pontos do olho, a posição do olho vem da caixa do rosto (rosto andou 40 px): conta")


def fingertip_rub(ear_during):
    """Ponta do indicador no canto de dentro do olho direito (sem a mão cobrir o centro dele), vai e vem vertical a
    3,5 por s, com o EAR do olho direito em `ear_during` durante o gesto (0,30 aberto antes)."""
    tracker, found = FaceTouchTracker(), []
    for i in range(int(12 * 30)):
        t = i / 30.0
        rubbing_now = 5.0 <= t < 7.0
        frame = FaceMetrics(timestamp=t, face_found=True, ear_right=ear_during if rubbing_now else 0.30,
                            ear_left=0.30, eye_points=EYE_POINTS, face_box=FACE_BOX, ear_points=EARS)
        hands = None
        if i % 8 == 0:
            hands = [posed(POINTING, 8, (310.0, 170.0 + 5.0 * math.sin(2 * math.pi * 3.5 * t)))] if rubbing_now else []
        found += [event.alert_type for event in tracker.update(t, frame, hands).events]
    tracker.close()
    return found, [episode["gesto"] for episode in tracker.episodes]


# GES-10: o olho fecha enquanto o dedo esfrega (EAR abaixo de 70% do aberto da pessoa): conta, mesmo com o vai e vem
# subamostrado e sem a mão cobrir o centro do olho.
closed_events, _ = fingertip_rub(0.12)
open_events, open_episodes = fingertip_rub(0.30)
assert closed_events == [RUBBING], ("GES-10", closed_events)
ok(f"GES-10 ponta do dedo no canto do olho com o olho fechando: conta (com o olho aberto: {open_episodes or 'nada'})")

# GES-11: cabeça apoiada na mão (palma na bochecha, dedos subindo pela frente do olho), parada por 3 s, com o rosto à
# vista e o olho aberto: a mão cobre o olho mas não mexe. É mão no rosto, não olho esfregado.
_, ges11 = run(lambda t: [posed(OPEN_HAND, 0, (290.0, 260.0), angle=-10.0)] if 5.0 <= t < 8.0 else [])
assert any(r.face_touch.eye_covered for r in ges11), "GES-11: a mão está mesmo na frente do olho"
assert names(ges11) == [HAND_ON_FACE], ("GES-11", names(ges11))
ok("GES-11 cabeça apoiada na mão, parada, cobrindo o olho aberto por 3 s: mão no rosto, não olho esfregado")

print(f"\nTODOS OS {checks} TESTES PASSARAM (Python {sys.version.split()[0]})")
