"""Celular: regras de tempo com um detector falso e, se o MediaPipe estiver instalado, os modelos reais.

Spec 028 (CEL-04 a CEL-14): cenas sintéticas pequenas (rosto e mão cor de pele, aparelho escuro) e um detector falso
que devolve as caixas e a confiança que o teste mandar; as verificações rodam na imagem de verdade.

Precisa de numpy e opencv (caixa/requirements.txt):
    python tests/test_celular.py
"""
import csv
import json
import math
import statistics
import sys
import tempfile
import time
import traceback
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "caixa"))
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
    landmarks: object = None  # 478 × 2 em pixels, como o FaceMetrics do MediaPipe (None = modo YuNet)


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


def simulate(script, seconds=12.0, pitch=lambda t: 0.0, mar=lambda t: 0.10, moving=True, fps=30.0, image=None,
             landmarks=None):
    """image: função do tempo que devolve o quadro (padrão: preto). landmarks: os 478 pontos do rosto ou None."""
    monitor = PhoneMonitor(FakeDetector(script), background=False)
    results = []
    for i in range(int(seconds * fps)):
        t = i / fps
        frame = Frame(timestamp=t, face_found=True, pitch=pitch(t), yaw=0.0, gaze_y=0.0, face_box=FACE_BOX,
                      ear_points=EARS, mar=mar(t), landmarks=landmarks)
        results.append(monitor.update(frame, IMAGE if image is None else image(t), moving=moving))
    return monitor, results


def run(script, seconds=12.0, **options):
    return simulate(script, seconds, **options)[1]


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

def hand_mistaken_for_phone(every):
    """Mão vazia na orelha; o detector chama a mão de celular em 1 de cada `every` detecções (teste de 14/09)."""
    calls = [0]

    def script(t):
        if t < 5.0:
            return [], []
        calls[0] += 1
        return ([HAND_AS_PHONE] if calls[0] % every == 1 else []), [hand_at(262, 175)]
    return script


HAND_AS_PHONE = (249.0, 162.0, 276.0, 190.0, 0.42)  # caixa do tamanho da mão, em cima da orelha
assert phone_near_ear(HAND_AS_PHONE, EARS, 100.0)
for every in (5, 4):
    mistaken = run(hand_mistaken_for_phone(every), seconds=20.0)
    phone_events = [e for e in events(mistaken) if e in ("celular_no_ouvido", "celular_na_mao", "olhando_celular")]
    assert not phone_events, (every, events(mistaken))
    assert all(r.state == "sem_celular" for r in mistaken), (every, {r.state for r in mistaken})
ok("CEL-01 mão vazia na orelha confundida com celular de vez em quando não vira 'no ouvido' nem 'na mão'")

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

# ---------------------------------------------------------------------------------------------------------------------
# Spec 028 · celular no ouvido sem confundir a mão vazia (CEL-04 a CEL-14)
# Rosto de 100 px (FACE_BOX), orelha esquerda da imagem em (270, 180). Cores em BGR.
# ---------------------------------------------------------------------------------------------------------------------
BACKGROUND = (60, 60, 60)
SKIN_CHEEK = (115, 140, 185)  # Y 151, Cr 152, Cb 108
SKIN_HAND = (105, 130, 190)  # um pouco mais vermelha que a bochecha, como a mão costuma ser
DARK_PHONE = (35, 30, 30)
# Bochechas (mesmos pontos de vision/cardio.py): lado esquerdo e direito da imagem.
CHEEK_POINTS = ((117, 118, 101, 36, 205, 187, 123), (346, 347, 330, 266, 425, 411, 352))
CHEEK_CENTERS = ((295.0, 200.0), (345.0, 200.0))
# 21 pontos do Hand Landmarker com o punho na origem e os dedos para cima (punho, polegar, indicador, médio, anelar,
# mínimo), em pixels para um rosto de 100 px.
HAND_SHAPE = np.array([(0, 0), (-12, -10), (-20, -22), (-25, -32), (-28, -40), (-12, -40), (-14, -55), (-15, -65),
                       (-16, -74), (-2, -42), (-2, -59), (-2, -70), (-2, -80), (8, -40), (9, -55), (10, -65), (10, -73),
                       (16, -36), (18, -47), (19, -55), (20, -62)], dtype=np.float32)
HAND_ON_EAR = HAND_SHAPE + np.array([275.0, 235.0], dtype=np.float32)  # mão vazia em concha na orelha
HAND_ON_PHONE = HAND_SHAPE + np.array([255.0, 250.0], dtype=np.float32)  # segurando o aparelho, tapa a parte de baixo
PHONE_EAR_BOX = (228.0, 120.0, 262.0, 200.0)  # 34 × 80 px: proporção 2,4; lado maior 0,8 rosto
HAND_BOX = (242.0, 150.0, 300.0, 240.0)  # caixa em volta da silhueta da mão na orelha
PHONE_EVENTS = ("celular_no_ouvido", "celular_na_mao", "olhando_celular")
CHECK_KEYS = ("fracao_pele", "fracao_fora_da_mao", "confianca_orelha", "aprovados_2s", "deteccoes_2s")


def face_landmarks():
    points = np.tile(np.array([[320.0, 185.0]], dtype=np.float32), (478, 1))
    for indices, (cx, cy) in zip(CHEEK_POINTS, CHEEK_CENTERS):
        for k, index in enumerate(indices):
            angle = 2 * math.pi * k / len(indices)
            points[index] = (cx + 6 * math.cos(angle), cy + 6 * math.sin(angle))
    return points


LANDMARKS = face_landmarks()


def scene(hand=None, phone=None, light=1.0, gray=False):
    """Quadro 640 × 480: rosto cor de pele, aparelho escuro e, por cima, a silhueta da mão (pontos + 5 px de dedo)."""
    image = np.full((480, 640, 3), BACKGROUND, dtype=np.uint8)
    cv2.ellipse(image, (320, 185), (50, 65), 0, 0, 360, SKIN_CHEEK, -1)
    if phone is not None:
        cv2.rectangle(image, (int(phone[0]), int(phone[1])), (int(phone[2]) - 1, int(phone[3]) - 1), DARK_PHONE, -1)
    if hand is not None:
        hull = cv2.convexHull(np.round(hand).astype(np.int32))
        cv2.fillConvexPoly(image, hull, SKIN_HAND)
        cv2.polylines(image, [hull], True, SKIN_HAND, 10)
    if gray:  # câmera infravermelha: sem cor
        image = cv2.cvtColor(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)
    if light != 1.0:
        image = np.clip(image.astype(np.float32) * light, 0, 255).astype(np.uint8)
    return image


def still(image):
    return lambda t: image


def phone_events(results):
    return [name for name in events(results) if name in PHONE_EVENTS]


def first_time(results, condition, fps=30.0):
    return next((i / fps for i, r in enumerate(results) if condition(r)), None)


def ear_state(r):
    return r.state == "celular_no_ouvido"


def cel04():
    """Mão vazia na orelha chamada de celular em 100% das detecções por 30 s, caixa da cor da pele."""
    image = scene(hand=HAND_ON_EAR)
    for hands, landmarks in (([], LANDMARKS), ([HAND_ON_EAR], LANDMARKS), ([], None)):  # None: bochecha pela caixa (YuNet)
        monitor, results = simulate(after(5.0)(lambda t: ([(*HAND_BOX, 0.8)], hands)), seconds=35.0, image=still(image),
                                    landmarks=landmarks)
        assert all(r.state == "sem_celular" for r in results), ({r.state for r in results}, len(hands), landmarks is None)
        assert not phone_events(results) and not any(r.alarm for r in results), phone_events(results)
        skin = monitor.last_observation.checks[0].skin_fraction
        assert skin is not None and skin >= 0.6, skin
    return "mão vazia chamada de celular em 100% das detecções por 30 s (com e sem pontos da mão e do rosto): " \
           "sempre 'sem celular', sem evento nem alarme"


def cel05():
    """Caixa dentro do contorno da mão, de qualquer cor (infravermelho sem cor, ou caixa escura em cima da mão)."""
    inside = (250.0, 165.0, 290.0, 225.0, 0.8)
    infrared = scene(hand=HAND_ON_EAR, gray=True)
    dark = scene(hand=HAND_ON_EAR)
    cv2.rectangle(dark, (250, 165), (289, 224), DARK_PHONE, -1)
    for image in (infrared, dark):
        monitor, results = simulate(after(5.0)(lambda t: ([inside], [HAND_ON_EAR])), seconds=20.0, image=still(image),
                                    landmarks=LANDMARKS)
        assert all(r.state == "sem_celular" for r in results) and not phone_events(results), phone_events(results)
        outside = monitor.last_observation.checks[0].outside_hand_fraction
        assert outside is not None and outside < 0.3, outside
    return "caixa dentro do contorno da mão (infravermelho e caixa escura): 'sem celular'"


def cel06():
    """Celular escuro na orelha, parte coberto pela mão: 'no ouvido' em até 2,5 s e evento aos 3 s."""
    image = scene(hand=HAND_ON_PHONE, phone=PHONE_EAR_BOX)
    monitor, results = simulate(after(5.0)(lambda t: ([(*PHONE_EAR_BOX, 0.7)], [HAND_ON_PHONE])), seconds=12.0,
                                image=still(image), landmarks=LANDMARKS)
    start = first_time(results, ear_state)
    event_at = first_time(results, lambda r: any(e.alert_type == "celular_no_ouvido" for e in r.events))
    assert start is not None and start - 5.0 <= 2.5, start
    assert event_at is not None and 3.0 <= event_at - start <= 3.1, (start, event_at)
    assert results[-1].state == "celular_no_ouvido" and results[-1].risk_level == 2 and any(r.alarm for r in results)
    check = monitor.last_observation.checks[0]
    assert check.skin_fraction < 0.6 and check.outside_hand_fraction >= 0.3, check
    return f"celular escuro na orelha, parte tapado pela mão: 'no ouvido' em {start - 5.0:.1f} s, evento " \
           f"{event_at - start:.1f} s depois (pele {check.skin_fraction:.2f}, fora da mão {check.outside_hand_fraction:.2f})"


def cel07():
    """Confiança 0,45: não conta na orelha; longe da orelha conta como hoje."""
    image = scene(hand=HAND_ON_PHONE, phone=PHONE_EAR_BOX)
    weak_ear = run(after(5.0)(lambda t: ([(*PHONE_EAR_BOX, 0.45)], [HAND_ON_PHONE])), seconds=12.0, image=still(image),
                   landmarks=LANDMARKS)
    assert all(r.state == "sem_celular" for r in weak_ear) and not phone_events(weak_ear), phone_events(weak_ear)
    weak_hand = run(after(5.0)(lambda t: ([(300.0, 330.0, 340.0, 400.0, 0.45)], [hand_at(320, 370)])))
    assert weak_hand[-1].state == "celular_na_mao" and events(weak_hand) == ["celular_na_mao"], events(weak_hand)
    return "confiança 0,45 na orelha não conta; longe da orelha continua 'na mão'"


def cel08():
    """Caixa quadrada, do tamanho do rosto, pequena ou grande demais na orelha: não conta."""
    boxes = {"quadrada": (240.0, 150.0, 280.0, 190.0), "rosto inteiro": (220.0, 120.0, 320.0, 250.0),
             "pequena": (250.0, 170.0, 260.0, 190.0), "grande": (200.0, 60.0, 280.0, 240.0)}
    for name, box in boxes.items():
        results = run(after(5.0)(lambda t: ([(*box, 0.8)], [])), seconds=12.0, image=still(scene(phone=box)),
                      landmarks=LANDMARKS)
        assert all(r.state == "sem_celular" for r in results) and not phone_events(results), (name, phone_events(results))
    control = run(after(5.0)(lambda t: ([(*PHONE_EAR_BOX, 0.8)], [])), seconds=12.0,
                  image=still(scene(phone=PHONE_EAR_BOX)), landmarks=LANDMARKS)
    assert control[-1].state == "celular_no_ouvido", control[-1].state
    return "caixa quadrada, do tamanho do rosto, pequena ou grande na orelha não conta (caixa de aparelho conta)"


def cel09():
    """3 aprovados em 2 s, mas só 40% das detecções: não vira 'no ouvido'."""
    image = scene(hand=HAND_ON_PHONE, phone=PHONE_EAR_BOX)
    calls = [0]

    def script(t):
        if t < 5.0:
            return [], []
        calls[0] += 1
        return ([(*PHONE_EAR_BOX, 0.7)] if calls[0] % 5 in (1, 3) else []), [HAND_ON_PHONE]

    results = run(script, seconds=25.0, image=still(image), landmarks=LANDMARKS)
    assert max((r.checks or {}).get("aprovados_2s") or 0 for r in results) >= 3  # a cena tem 3 aprovados em 2 s
    assert all(r.state == "sem_celular" for r in results) and not phone_events(results), phone_events(results)
    return "3 aprovados em 2 s com só 40% das detecções: 'sem celular'"


def cel10():
    """Aparelho confirmado na mão, se mexendo, levado à orelha: 'no ouvido' (caminho legítimo)."""
    def chest(t):
        dx = 12 * math.sin(3 * t)
        return (300.0 + dx, 330.0, 340.0 + dx, 400.0, 0.7)

    at_ear = scene(hand=HAND_ON_PHONE, phone=PHONE_EAR_BOX)
    empty = scene()

    def script(t):
        if t < 5.0:
            return [], []
        return ([chest(t)], []) if t < 8.0 else ([(*PHONE_EAR_BOX, 0.7)], [HAND_ON_PHONE])

    def image(t):
        if t < 5.0:
            return empty
        return scene(phone=chest(t)[:4]) if t < 8.0 else at_ear

    results = run(script, seconds=13.0, image=image, landmarks=LANDMARKS)
    assert results[int(7.9 * 30)].state == "celular_na_mao", results[int(7.9 * 30)].state
    start = first_time(results, ear_state)
    assert start is not None and 8.0 <= start <= 8.3, start  # na primeira detecção na orelha
    assert "celular_no_ouvido" in events(results), events(results)
    return f"aparelho na mão, se mexendo, levado à orelha: 'no ouvido' {start - 8.0:.2f} s depois de chegar"


def cel11():
    """Depois de 'no ouvido', o aparelho some e a mão fica: no máximo 5 s. Mão vazia sem aprovação: nunca."""
    with_phone = scene(hand=HAND_ON_PHONE, phone=PHONE_EAR_BOX)
    hand_only = scene(hand=HAND_ON_PHONE)

    def script(t):
        if t < 5.0:
            return [], []
        return ([(*PHONE_EAR_BOX, 0.7)], [HAND_ON_PHONE]) if t < 8.0 else ([], [HAND_ON_PHONE])

    results = run(script, seconds=20.0, image=lambda t: with_phone if t < 8.0 else hand_only, landmarks=LANDMARKS)
    assert ear_state(results[int(7.9 * 30)]) and ear_state(results[int(11.0 * 30)])
    after_5s = results[int(13.0 * 30):]
    assert all(r.state == "sem_celular" for r in after_5s), {r.state for r in after_5s}
    end = first_time(results[int(8.0 * 30):], lambda r: r.state == "sem_celular")
    assert "celular_no_ouvido" in events(results)

    def weak(t):
        if t < 5.0:
            return [], []
        return ([(*PHONE_EAR_BOX, 0.45)], [HAND_ON_PHONE]) if t < 8.0 else ([], [HAND_ON_PHONE])

    never = run(weak, seconds=20.0, image=lambda t: with_phone if t < 8.0 else hand_only, landmarks=LANDMARKS)
    assert all(r.state == "sem_celular" for r in never) and not phone_events(never), phone_events(never)
    return f"aparelho some e a mão fica: 'no ouvido' por mais {end:.1f} s (máximo 5 s); sem aprovação antes: nunca"


def cel12():
    """Iluminação mudando 30% devagar: a fração de pele da mão continua ≥ 60%."""
    lowest = {}
    for start, end in ((1.0, 0.7), (1.0, 1.3)):
        monitor = PhoneMonitor(FakeDetector(lambda t: ([(*HAND_BOX, 0.8)], [HAND_ON_EAR])), background=False)
        fractions, seen = [], None
        for i in range(int(35.0 * 30)):
            t = i / 30.0
            light = start + (end - start) * min(1.0, t / 30.0)
            frame = Frame(timestamp=t, face_found=True, pitch=0.0, yaw=0.0, gaze_y=0.0, face_box=FACE_BOX,
                          ear_points=EARS, landmarks=LANDMARKS)
            result = monitor.update(frame, scene(hand=HAND_ON_EAR, light=light))
            assert result.state == "sem_celular", (t, light)
            if monitor.last_observation is not seen:
                seen = monitor.last_observation
                fractions.append(seen.checks[0].skin_fraction)
        assert all(f is not None for f in fractions) and min(fractions) >= 0.6, min(f or 0 for f in fractions)
        lowest[f"{start:.1f}→{end:.1f}"] = round(min(fractions), 2)
    return f"luz mudando 30% devagar: fração de pele da mão no mínimo {lowest}"


def cel13():
    """Números das verificações nos detalhes do evento e no CSV do avaliar_celular.py; nenhuma imagem gravada."""
    from vision.phone import check_columns

    image = scene(hand=HAND_ON_PHONE, phone=PHONE_EAR_BOX)
    results = run(after(5.0)(lambda t: ([(*PHONE_EAR_BOX, 0.7)], [HAND_ON_PHONE])), seconds=12.0, image=still(image),
                  landmarks=LANDMARKS)
    event = next(e for r in results for e in r.events if e.alert_type == "celular_no_ouvido")
    details = event.details
    assert all(key in details for key in CHECK_KEYS), details
    assert details["fracao_pele"] < 0.6 and details["fracao_fora_da_mao"] >= 0.3 and details["confianca_orelha"] == 0.7
    assert 3 <= details["aprovados_2s"] <= details["deteccoes_2s"], details
    assert all(isinstance(value, (int, float, str, bool, type(None))) for value in details.values()), details
    json.dumps(details)
    columns = check_columns(results[-1])
    assert set(columns) == {f"celular_{key}" for key in CHECK_KEYS}, columns
    assert columns["celular_confianca_orelha"] == 0.7 and columns["celular_deteccoes_2s"] >= 3, columns

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ferramentas"))
    import avaliar_celular

    work = Path(tempfile.mkdtemp(prefix="drivesafe-cel13-"))
    results_dir = work / "resultados"
    results_dir.mkdir()
    header = ["tempo_s", "rosto", "celular", "celular_confianca", "celular_largura_rosto", "celular_altura_rosto",
              "celular_proporcao", *(f"celular_{key}" for key in CHECK_KEYS)]
    with open(results_dir / "mao_quadros.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        for i in range(600):  # 60 s a 10 quadros/s; um episódio falso de "no ouvido" de 30 a 32 s
            t = i / 10.0
            state = "celular_no_ouvido" if 30.0 <= t < 32.0 else "sem_celular"
            writer.writerow([f"{t:.3f}", 1, state, 0.8, 0.58, 0.9, 1.55, 0.82, "", 0.8, 1 if state != "sem_celular" else 0, 8])
    with open(results_dir / "celular_quadros.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        for i in range(300):  # 30 s; "no ouvido" a partir de 6 s: sensibilidade 0,8
            t = i / 10.0
            state = "celular_no_ouvido" if t >= 6.0 else "sem_celular"
            writer.writerow([f"{t:.3f}", 1, state, 0.7, 0.34, 0.8, 2.35, 0.31, 0.62, 0.7, 6, 8])
    annotation = work / "anotacao.csv"
    with open(annotation, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter=";")
        writer.writerow(["arquivo", "aparelho", "inicio_s", "fim_s", "estado", "situacao", "cena"])
        writer.writerow(["mao.mp4", "sem_aparelho", 0.0, 60.0, "sem_celular", "negativo_mao_na_orelha", ""])
        writer.writerow(["celular.mp4", "galaxy_a54", 0.0, 30.0, "celular_no_ouvido", "ouvido", "celular_real"])
    assert avaliar_celular.main([str(annotation), "--resultados", str(results_dir)]) == 0
    report = json.loads((work / "anotacao_celular.json").read_text(encoding="utf-8"))
    empty, real = report["cenas"]["mao_vazia"], report["cenas"]["celular_real"]
    assert empty["episodios_no_ouvido"] == 1 and empty["falsos_positivos_por_minuto"] == 1.0, empty
    assert empty["meta_zero_no_ouvido"] is False and empty["fracao_pele_mediana"] == 0.82, empty
    assert real["sensibilidade"] == 0.8 and real["meta_sensibilidade"] is True, real
    assert real["fracao_fora_da_mao_mediana"] == 0.62 and real["aprovacao_media"] == 0.75, real
    with open(work / "anotacao_aparelhos.csv", encoding="utf-8") as handle:
        device_header = next(csv.reader(handle))
    assert {"fracao_pele_mediana", "fracao_fora_da_mao_mediana", "confianca_orelha_mediana",
            "aprovacao_media"} <= set(device_header), device_header
    with open(work / "anotacao_cenas.csv", encoding="utf-8") as handle:
        scenes = list(csv.DictReader(handle))
    assert [row["cena"] for row in scenes] == ["mao_vazia", "celular_real"], scenes
    written = {path.suffix for path in work.rglob("*") if path.is_file()}
    assert written <= {".csv", ".json"}, written
    return "números das verificações no evento, no _quadros.csv e no avaliar_celular.py (resumo por cena); só CSV e JSON"


def cel14():
    """Custo das verificações < 2 ms por detecção em 640 × 480 (2 caixas, 2 mãos)."""
    from vision.phone import PhoneVerifier, face_snapshot

    image = scene(hand=HAND_ON_PHONE, phone=PHONE_EAR_BOX)
    face = face_snapshot(Frame(timestamp=0.0, face_found=True, face_box=FACE_BOX, ear_points=EARS, landmarks=LANDMARKS))
    verifier = PhoneVerifier()
    phones = [(*PHONE_EAR_BOX, 0.7), (*HAND_BOX, 0.6)]
    hands = [HAND_ON_PHONE, hand_at(320, 370)]
    costs = []
    for i in range(400):
        start = time.perf_counter()
        verifier.measure(image, phones, hands, face, i * 0.25)
        costs.append((time.perf_counter() - start) * 1000.0)
    median, p95 = statistics.median(costs), sorted(costs)[int(0.95 * len(costs))]
    assert median < 2.0, median
    return f"custo das verificações: mediana {median:.2f} ms, p95 {p95:.2f} ms por detecção (limite 2 ms)"


failures = []
for criterion in (cel04, cel05, cel06, cel07, cel08, cel09, cel10, cel11, cel12, cel13, cel14):
    name = criterion.__name__.upper().replace("CEL", "CEL-")
    try:
        ok(f"{name} {criterion()}")
    except Exception as exc:  # noqa: BLE001  (junta todos os critérios que falham, como num relatório de testes)
        failures.append(name)
        print(f"FALHOU {name}: {criterion.__doc__.strip()}\n    {type(exc).__name__}: {exc}")
        traceback.print_exc(limit=2)

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

if failures:
    print(f"\n{len(failures)} CRITÉRIO(S) FALHARAM: {', '.join(failures)}")
    sys.exit(1)
print(f"\nTODOS OS {checks} TESTES PASSARAM (Python {sys.version.split()[0]})")
