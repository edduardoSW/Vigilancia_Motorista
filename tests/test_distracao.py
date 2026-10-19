"""Spec 027, pacote 2 · olhar, distração, blendshapes, reflexo, filtro e postura.

Critérios (mesmo ID da pesquisa docs/pesquisa/2026-10-19-estado-da-arte-dms.md, §7A): DMS-01, DMS-02, DMS-03, DMS-05,
DMS-07, DMS-12, DMS-13 (porta), DMS-14, DMS-17 e DMS-18.

Usa numpy e OpenCV só para importar vision/face.py (os blendshapes); o resto é biblioteca padrão:
    python tests/test_distracao.py
"""
import math
import random
import sys
import tempfile
import json
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "caixa"))
from vision.drowsiness import DrowsinessMonitor  # noqa: E402
from vision.eyes import DriverProfile, OpennessModel, Sample  # noqa: E402

checks = 0
FPS = 30.0


def ok(message):
    global checks
    checks += 1
    print(f"OK {checks:02d} {message}")


@dataclass
class Quadro(Sample):
    """Sample com o que o módulo de distração e a postura leem do FaceMetrics."""

    roll: float | None = 0.0
    head_x_cm: float | None = None
    head_y_cm: float | None = None
    head_z_cm: float | None = None
    eyes_in_frame: bool = True


PERFIL = DriverProfile(ear_open=0.30, ear_closed=0.06, score_open=0.05, score_closed=0.90, classifier_open=0.95,
                       classifier_closed=0.05, pitch_baseline=0.0, yaw_baseline=0.0, look_down_baseline=0.10)


# ---------------------------------------------------------------------------------------------------------------
# DMS-05 · blendshapes no FaceMetrics
from vision import face as face_module  # noqa: E402

assert len(face_module.BLENDSHAPE_NAMES) == 52 and len(set(face_module.BLENDSHAPE_NAMES)) == 52
assert face_module.BLENDSHAPE_NAMES[0] == "_neutral" and "eyeLookDownLeft" in face_module.BLENDSHAPE_NAMES
scores = {name: 0.0 for name in face_module.BLENDSHAPE_NAMES}
scores.update(eyeLookDownLeft=0.6, eyeLookDownRight=0.4, eyeSquintLeft=0.2, eyeSquintRight=0.4, mouthPucker=0.3,
              noseSneerLeft=0.1, noseSneerRight=0.3, browInnerUp=0.5, eyeWideLeft=0.05, eyeWideRight=0.15)
both = face_module.blendshape_metrics(scores, right_in=True, left_in=True, width_left=30.0, width_right=30.0)
assert abs(both["eye_look_down"] - 0.5) < 1e-9 and abs(both["eye_squint"] - 0.3) < 1e-9, both
assert abs(both["mouth_pucker"] - 0.3) < 1e-9 and abs(both["nose_sneer"] - 0.2) < 1e-9 and both["brow_inner_up"] == 0.5
turned = face_module.blendshape_metrics(scores, right_in=True, left_in=True, width_left=30.0, width_right=15.0)
assert turned["eye_look_down"] == 0.6, "DMS-05a cabeça virada: vale só o olho mais visível, como combine_eyes"
only_right = face_module.blendshape_metrics(scores, right_in=True, left_in=False, width_left=0.0, width_right=30.0)
assert only_right["eye_look_down"] == 0.4
no_eye = face_module.blendshape_metrics(scores, right_in=False, left_in=False, width_left=0.0, width_right=0.0)
assert no_eye["eye_look_down"] is None and no_eye["eye_squint"] is None and no_eye["mouth_pucker"] == 0.3
assert face_module.blendshape_metrics({}, True, True, 30.0, 30.0)["eye_look_down"] is None
for campo in ("eye_look_down", "eye_look_up", "eye_look_in", "eye_look_out", "eye_squint", "eye_wide", "brow_down",
              "brow_outer_up", "brow_inner_up", "mouth_pucker", "nose_sneer"):
    assert campo in both and hasattr(face_module.FaceMetrics(0.0, True), campo), campo
assert hasattr(face_module.FaceMetrics(0.0, True), "blendshapes")
ok("DMS-05a blendshapes combinados como combine_eyes (olho mais visível com a cabeça virada), None sem olho")

sys.path.insert(0, str(ROOT / "ferramentas"))
import analisar_video  # noqa: E402

assert tuple(analisar_video.BLENDSHAPE_COLUMNS) == face_module.BLENDSHAPE_NAMES
ok("DMS-05b o _quadros.csv do analisar_video.py leva as 52 colunas com o nome do MediaPipe")


# ---------------------------------------------------------------------------------------------------------------
# DMS-03 · olhar para baixo não é olho fechado
def olhar_para_baixo(t, ear_fraction, look_down, ocec, blink=0.75, iris_fraction=None):
    ear = 0.06 + ear_fraction * 0.24
    return Quadro(timestamp=t, face_found=True, ear=ear, blink_score=blink, eye_open_prob=ocec, jaw_open=0.02,
                  pitch=0.0, yaw=0.0, eye_distance_px=90.0, eye_look_down=look_down, iris_visible_fraction=iris_fraction,
                  gaze_x=0.0, gaze_y=0.35, iris_diameter_px=12.0)


def roda(monitor, quadro, inicio, segundos):
    out = []
    for i in range(int(segundos * FPS)):
        out.append(monitor.update(quadro(inicio + i / FPS)))
    return out


for ear_fraction in (0.15, 0.35):
    m = DrowsinessMonitor(profile=PERFIL)
    roda(m, lambda t: olhar_para_baixo(t, 1.0, 0.10, 0.95, blink=0.05), 0.0, 5.0)
    out = roda(m, lambda t, f=ear_fraction: olhar_para_baixo(t, f, 0.60, 0.80), 5.0, 3.0)
    eventos = [e.alert_type for a in out for e in a.events]
    assert "microssono" not in eventos and not any(a.alarm for a in out), (ear_fraction, eventos)
    assert all(a.frame_source == "olhar_para_baixo" and a.openness is None for a in out[2:]), \
        {a.frame_source for a in out}
ok("DMS-03a 3 s com EAR a 15% e 35% do aberto, eyeLookDown 0,6 e OCEC 0,8: nenhum microssono, fonte olhar_para_baixo")

m = DrowsinessMonitor(profile=PERFIL)
roda(m, lambda t: olhar_para_baixo(t, 1.0, 0.10, 0.95, blink=0.05), 0.0, 5.0)
out = roda(m, lambda t: olhar_para_baixo(t, 0.10, 0.60, None, iris_fraction=0.55), 5.0, 3.0)
assert not any(e.alert_type == "microssono" for a in out for e in a.events)
assert out[-1].frame_source == "olhar_para_baixo"
ok("DMS-03a sem o classificador, íris com 55% da altura visível também separa olhar para baixo de olho fechado")

m = DrowsinessMonitor(profile=PERFIL)
roda(m, lambda t: olhar_para_baixo(t, 1.0, 0.10, 0.95, blink=0.05), 0.0, 5.0)
out = roda(m, lambda t: olhar_para_baixo(t, 0.0, 0.10, 0.10, blink=0.90, iris_fraction=0.05), 5.0, 3.0)
micro = [i for i, a in enumerate(out) for e in a.events if e.alert_type == "microssono"]
assert micro and abs(micro[0] / FPS - 1.0) <= 1.0 / FPS + 1e-6, micro
ok(f"DMS-03b olho fechado de verdade (eyeLookDown 0,1, OCEC 0,1): microssono em {micro[0] / FPS:.3f} s")

m = DrowsinessMonitor(profile=PERFIL)
roda(m, lambda t: olhar_para_baixo(t, 1.0, 0.10, 0.95, blink=0.05), 0.0, 5.0)
out = roda(m, lambda t: olhar_para_baixo(t, 0.0, 0.70, 0.10, blink=0.90, iris_fraction=0.05), 5.0, 3.0)
assert any(e.alert_type == "microssono" for a in out for e in a.events)
ok("DMS-03b olho fechado com eyeLookDown alto mas OCEC e íris dizendo fechado: microssono continua")


# ---------------------------------------------------------------------------------------------------------------
# DMS-07 · reflexo nos óculos tira o EAR
model = OpennessModel(PERFIL)
base = Quadro(timestamp=0.0, face_found=True, ear=0.20, blink_score=0.30, eye_open_prob=0.70, pitch=0.0, yaw=0.0,
              eye_distance_px=90.0)
sem_reflexo = model.openness(base)
com_zero = model.openness(Quadro(**{**base.__dict__, "glare_fraction": 0.0}))
com_reflexo = model.openness(Quadro(**{**base.__dict__, "glare_fraction": 0.05}))
assert "ear" in sem_reflexo[1] and com_zero == sem_reflexo, (sem_reflexo, com_zero)
assert "ear" not in com_reflexo[1] and com_reflexo[1] == "pontuacao+classificador", com_reflexo
ok(f"DMS-07a reflexo em 5% da região do olho: abertura sem o EAR ({com_reflexo[1]}); DMS-07b 0%: igual a hoje")


# ---------------------------------------------------------------------------------------------------------------
# DMS-14 · One Euro só na pose
from vision.filtros import POSE_FILTER, OneEuroFilter  # noqa: E402

filtro = OneEuroFilter(**POSE_FILTER)
saida = [filtro(i / FPS, 0.0 if i < 30 else 30.0) for i in range(60)]
atraso = next(i for i in range(30, 60) if saida[i] >= 27.0) - 30
assert atraso <= 2, f"DMS-14a degrau de 30°: atraso de {atraso} quadros"
filtro = OneEuroFilter(**POSE_FILTER)
rnd = random.Random(7)
ruido = [filtro(i / FPS, rnd.uniform(-1.0, 1.0)) for i in range(900)][30:]
rms = math.sqrt(sum(v * v for v in ruido) / len(ruido))
assert rms <= 0.3, f"DMS-14a ruído de ±1° parado: saída com {rms:.2f}° (valor eficaz)"
filtro = OneEuroFilter(**POSE_FILTER)
filtro(0.0, 10.0)
assert filtro(2.0, -20.0) == -20.0, "buraco de mais de 0,5 s recomeça o filtro (sem arrastar o valor antigo)"
ok(f"DMS-14a One Euro na pose: degrau de 30° em {atraso} quadro(s) até 90%, ruído de ±1° vira {rms:.2f}° eficaz")


# ---------------------------------------------------------------------------------------------------------------
# Quadros de olhar: "cabeca" = só a cabeça gira (owl); "olho" = só os olhos (lizard), Euro NCAP 1.2.1.
from vision.distraction import DEFAULT_ZONES, DistractionMonitor  # noqa: E402
from vision.gaze import GazeTracker  # noqa: E402

FRENTE = DriverProfile(ear_open=0.30, ear_closed=0.06, pitch_baseline=0.0, yaw_baseline=0.0, gaze_center_yaw=0.0,
                       gaze_center_pitch=0.0)


def olhar(t, dyaw=0.0, dpitch=0.0, como="olho", head=(0.0, 0.0), face=True, jaw=0.02, x_cm=0.0):
    if not face:
        return Quadro(timestamp=t, face_found=False)
    yaw, pitch = head
    gx = gy = 0.0
    if como == "cabeca":
        yaw, pitch = yaw + dyaw, pitch + dpitch
    else:
        gx = math.sin(math.radians(dyaw)) / 1.25
        gy = math.sin(math.radians(dpitch)) / 1.25
    return Quadro(timestamp=t, face_found=True, ear=0.30, jaw_open=jaw, pitch=pitch, yaw=yaw, eye_distance_px=90.0,
                  gaze_x=gx, gaze_y=gy, iris_diameter_px=12.0, head_x_cm=x_cm, head_y_cm=0.0, head_z_cm=-60.0)


def sequencia(monitor, trechos, inicio=0.0, abertura=1.0, fonte="ear", velocidade=None):
    """trechos: [(segundos, função t -> quadro)]. Devolve [(t, avaliação)]."""
    out, t = [], inicio
    for segundos, quadro in trechos:
        fim = t + segundos
        while t < fim - 1e-9:
            out.append((t, monitor.update(quadro(t), abertura, fonte, speed_kmh=velocidade)))
            t += 1.0 / FPS
    return out


def eventos(out, tipo=None):
    return [(t, e) for t, a in out for e in a.events if tipo is None or e.alert_type == tipo]


def frente(t):
    return olhar(t)


# DMS-01a · 4 s na frente + 3,2 s com Δyaw −45° (zona não ligada): 1 distracao_longa entre 3,0 e 3,1 s.
for como in ("cabeca", "olho"):
    m = DistractionMonitor(profile=FRENTE)
    out = sequencia(m, [(4.0, frente), (3.2, lambda t, c=como: olhar(t, dyaw=-45.0, como=c)), (3.0, frente)])
    longas = eventos(out, "distracao_longa")
    assert len(longas) == 1, (como, [e.alert_type for _, e in eventos(out)])
    atraso = longas[0][0] - 4.0
    assert 3.0 - 1e-6 <= atraso <= 3.1, (como, atraso)
    detalhes = longas[0][1].details
    # Com a íris visível o modo é "olhar" (cabeça + olho) nos dois casos; "cabeca" é o modo degradado, sem íris.
    assert detalhes["zona"] == "fora" and detalhes["modo"] == "olhar", detalhes
    assert detalhes["fonte_velocidade"] == "nenhuma" and detalhes["modo_velocidade"] == "sem_velocidade", detalhes
    assert any(a.alarm and a.alarm_kind == "distracao" for t, a in out if abs(t - longas[0][0]) < 1e-9)
    assert not eventos(out, "distracao_repetida")
    ok(f"DMS-01a olhar de 3,2 s a −45° só com {'a cabeça' if como == 'cabeca' else 'os olhos'}: distracao_longa "
       f"{atraso:.3f} s depois do início, aviso de distração e modo 'sem velocidade' nos detalhes")

# DMS-01a · modo degradado (óculos escuros, sem íris): +1,5 s, como o "não nominal" do ADDW.
m = DistractionMonitor(profile=FRENTE)


def sem_iris(t, dyaw=0.0):
    q = olhar(t, dyaw=dyaw, como="cabeca")
    q.gaze_x = q.gaze_y = None
    return q


out = sequencia(m, [(4.0, sem_iris), (5.0, lambda t: sem_iris(t, -45.0)), (2.0, sem_iris)])
longas = eventos(out, "distracao_longa")
assert len(longas) == 1 and 4.5 - 1e-6 <= longas[0][0] - 4.0 <= 4.6, [t - 4.0 for t, _ in longas]
assert longas[0][1].details["modo"] == "cabeca" and longas[0][1].details["limiar_s"] == 4.5
ok(f"DMS-01a sem íris (só a cabeça): distracao_longa com 1,5 s a mais ({longas[0][0] - 4.0:.2f} s)")

# DMS-01b · 3,5 s no espelho do motorista: sem aviso, olhar registrado.
m = DistractionMonitor(profile=FRENTE)
out = sequencia(m, [(4.0, frente), (3.5, lambda t: olhar(t, dyaw=50.0, como="cabeca")), (3.0, frente)])
assert not eventos(out) and not any(a.alarm for _, a in out), [e.alert_type for _, e in eventos(out)]
meio = out[int(6.0 * FPS)][1]
assert meio.zone == "espelho_motorista" and meio.zone_kind == "direcao", (meio.zone, meio.zone_kind)
registrado = m.glances[-1]
assert registrado["zona"] == "espelho_motorista" and abs(registrado["duracao_s"] - 3.5) <= 0.1, registrado
ok(f"DMS-01b 3,5 s no espelho do motorista: sem aviso; olhar registrado ({registrado['duracao_s']:.2f} s)")

# DMS-01c · olhares de 1,8 s a Δpitch +35° com 0,8 s na frente: distracao_repetida quando a soma passa de 10 s.
m = DistractionMonitor(profile=FRENTE)
trechos = [(4.0, frente)]
for _ in range(8):
    trechos += [(1.8, lambda t: olhar(t, dpitch=35.0)), (0.8, frente)]
out = sequencia(m, trechos)
repetidas = eventos(out, "distracao_repetida")
esperado = 4.0 + 5 * 2.6 + 1.0
assert repetidas and abs(repetidas[0][0] - esperado) <= 0.2, ([t for t, _ in repetidas], esperado)
assert not eventos(out, "distracao_longa"), "nenhum olhar passou de 3 s"
assert repetidas[0][1].details["soma_30s_s"] >= 10.0 and repetidas[0][1].details["zona"] == "colo"
assert repetidas[0][1].details["area3"] is True
ok(f"DMS-01c olhares de 1,8 s ao colo com 0,8 s na frente: distracao_repetida em {repetidas[0][0]:.2f} s "
   f"(esperado {esperado:.2f} s)")

# DMS-01d · os mesmos olhares com 2,5 s na frente entre eles: nenhum evento (a volta de 2 s zera a soma).
m = DistractionMonitor(profile=FRENTE)
trechos = [(4.0, frente)]
for _ in range(12):
    trechos += [(1.8, lambda t: olhar(t, dpitch=35.0)), (2.5, frente)]
out = sequencia(m, trechos)
assert not eventos(out), [e.alert_type for _, e in eventos(out)]
ok("DMS-01d olhares de 1,8 s ao colo com 2,5 s na frente entre eles: nenhum evento")

# DMS-01e · falar olhando a frente por 60 s (boca, cabeça e olhos mexendo pouco): nenhum evento.
rnd = random.Random(3)
m = DistractionMonitor(profile=FRENTE)


def falando(t):
    q = olhar(t, dyaw=rnd.uniform(-4, 4), dpitch=rnd.uniform(-3, 3), como="cabeca",
              jaw=0.25 + 0.2 * math.sin(2 * math.pi * 3 * t))
    q.gaze_x, q.gaze_y = rnd.uniform(-0.05, 0.05), rnd.uniform(-0.05, 0.05)
    return q


out = sequencia(m, [(60.0, falando)])
assert not eventos(out) and max(a.level for _, a in out) == 0
ok("DMS-01e falando e olhando a frente por 60 s: nenhum evento, canal de distração em 0")

# AttenD · o balde de 2 s esvazia fora da via e vira "atenção visual" (nível 1, sem alarme).
m = DistractionMonitor(profile=FRENTE)
out = sequencia(m, [(4.0, frente), (2.2, lambda t: olhar(t, dyaw=-45.0)), (0.5, frente)])
fora = [a for t, a in out if 4.0 <= t < 6.2]
assert fora[-1].attention_buffer_s == 0.0 and fora[-1].state == "atencao_visual" and fora[-1].level == 1
assert not any(a.alarm for _, a in out)
assert 0.0 < out[-1][1].attention_buffer_s < 2.0
ok("DMS-01 balde AttenD: 2,2 s fora esvazia o balde (atenção visual, nível 1, sem alarme) e ele volta a encher na via")


# ---------------------------------------------------------------------------------------------------------------
# DMS-17 · sem resposta pela distração
m = DistractionMonitor(profile=FRENTE)
out = sequencia(m, [(4.0, frente), (6.5, lambda t: olhar(t, dyaw=-45.0)), (2.0, frente)])
aviso = eventos(out, "distracao_longa")[0][0]
sem_resposta = eventos(out, "nao_responsivo")
assert len(sem_resposta) == 1 and abs(sem_resposta[0][0] - aviso - 3.0) <= 1.0 / FPS + 1e-6, \
    (aviso, [t for t, _ in sem_resposta])
evento = sem_resposta[0][1]
assert evento.risk_level == 5 and evento.details["origem"] == "distracao", evento
critico = [a for t, a in out if sem_resposta[0][0] <= t < 10.5]
assert all(a.alarm and a.alarm_kind == "critico" and a.level == 3 for a in critico)
assert not out[-1][1].alarm and out[-1][1].level == 0
ok(f"DMS-17a aviso de distração e olhar fora mais 3 s: nao_responsivo (nível 5) {sem_resposta[0][0] - aviso:.2f} s "
   "depois do aviso, alarme crítico até voltar")

m = DistractionMonitor(profile=FRENTE)
out = sequencia(m, [(4.0, frente), (5.0, lambda t: olhar(t, dyaw=-45.0)), (3.0, frente)])
assert not eventos(out, "nao_responsivo") and eventos(out, "distracao_longa")
ok("DMS-17a voltou à via 2 s depois do aviso: nenhum nao_responsivo")


# ---------------------------------------------------------------------------------------------------------------
# DMS-13 (porta de velocidade, sem GPS no PRD §5)
for velocidade, deve_avisar in ((10.0, False), (30.0, True)):
    m = DistractionMonitor(profile=FRENTE)
    out = sequencia(m, [(4.0, frente), (4.0, lambda t: olhar(t, dpitch=35.0)), (2.0, frente)], velocidade=velocidade)
    longas = eventos(out, "distracao_longa")
    assert bool(longas) == deve_avisar and any(a.alarm for _, a in out) == deve_avisar, (velocidade, longas)
    assert m.glances[-1]["zona"] == "colo" and m.glances[-1]["duracao_s"] >= 3.9, m.glances[-1]
    if longas:
        assert longas[0][1].details["fonte_velocidade"] == "telemetria" and longas[0][1].details["velocidade_kmh"] == 30.0
ok("DMS-13 porta: 10 km/h + 4 s olhando o colo, sem aviso e olhar registrado; 30 km/h, aviso com a velocidade")


# ---------------------------------------------------------------------------------------------------------------
# DMS-03a · olhar para baixo vira zona "colo" na distração, mesmo sem íris
m = DistractionMonitor(profile=FRENTE)
sequencia(m, [(4.0, frente)])
out = sequencia(m, [(3.5, lambda t: olhar(t))], inicio=4.0, abertura=None, fonte="olhar_para_baixo")
assert out[-1][1].zone == "colo" and out[-1][1].mode == "olhar_para_baixo", (out[-1][1].zone, out[-1][1].mode)
assert eventos(out, "distracao_longa")
ok("DMS-03a quadro 'olhar_para_baixo' conta como zona colo na distração (e avisa em 3 s)")


# ---------------------------------------------------------------------------------------------------------------
# DMS-02 · "frente" automática pela moda do olhar (Victor et al., 2005: moda e raio de 8°)
def moda_cenario(tracker, inicio, segundos, centro, rnd):
    t = inicio
    while t < inicio + segundos:
        espalhado = (t % 1.0) >= 0.7
        q = olhar(t, head=centro, como="olho",
                  dyaw=rnd.uniform(-40, 40) if espalhado else rnd.uniform(-1, 1),
                  dpitch=rnd.uniform(-30, 30) if espalhado else rnd.uniform(-1, 1))
        tracker.update(q, 1.0, "ear")
        t += 1.0 / FPS
    return t


rnd = random.Random(11)
g = GazeTracker()
fim = moda_cenario(g, 0.0, 60.0, (12.0, -5.0), rnd)
assert g.ready and g.center is not None
erro = math.hypot(g.center[0] - 12.0, g.center[1] + 5.0)
assert erro <= 2.0, (g.center, erro)
ok(f"DMS-02a 70% do tempo em (12°, −5°) e 30% espalhado: frente em ({g.center[0]:.1f}°, {g.center[1]:.1f}°) "
   f"em 60 s (erro {erro:.2f}°)")

g = GazeTracker()
fim = moda_cenario(g, 0.0, 300.0, (12.0, -5.0), rnd)
recentrou = None
t = fim
while t < fim + 120.0:
    t = moda_cenario(g, t, 1.0, (22.0, 5.0), rnd)
    if recentrou is None and math.hypot(g.center[0] - 22.0, g.center[1] - 5.0) <= 2.0:
        recentrou = t - fim
assert recentrou is not None and recentrou <= 120.0, (g.center, recentrou)
ok(f"DMS-02b banco mexido (tudo 10° deslocado) depois de 5 min: frente recentrada em {recentrou:.0f} s")

g = GazeTracker()
fim = moda_cenario(g, 0.0, 120.0, (0.0, 0.0), rnd)
t = fim
while t < fim + 180.0:  # 3 min olhando o colo (Δpitch +35°) não vira a "frente"
    q = olhar(t, dpitch=35.0, como="olho")
    g.update(q, 1.0, "ear")
    t += 1.0 / FPS
assert math.hypot(g.center[0], g.center[1]) <= 2.0, g.center
ok("DMS-02b trava: 3 min olhando o colo não mudam a frente (no máximo 20° da âncora)")

pasta = Path(tempfile.mkdtemp(prefix="rotaguard-perfil-"))
antigo = pasta / "antigo.json"
antigo.write_text(json.dumps({"ear_open": 0.3, "ear_closed": 0.06, "blinks": 40, "looked_alert": True}),
                  encoding="utf-8")
perfil_antigo = DriverProfile.load(antigo)
assert perfil_antigo is not None and perfil_antigo.gaze_center_yaw is None and perfil_antigo.gaze_zones is None
m = DistractionMonitor(profile=perfil_antigo)
assert [z.name for z in m.zones] == [z.name for z in DEFAULT_ZONES] and not m.gaze.ready
ok("DMS-02c perfil antigo sem os campos novos abre e usa as zonas padrão (frente aprendida pela moda)")

# DMS-02 · calibração guiada opcional (a tela do app chama estes métodos)
m = DistractionMonitor(profile=FRENTE)
out = sequencia(m, [(4.0, frente), (3.5, lambda t: olhar(t, dyaw=30.0, como="cabeca")), (2.0, frente)])
assert eventos(out, "distracao_longa"), "antes da calibração guiada, +30° fica fora das zonas padrão"
m = DistractionMonitor(profile=FRENTE)
sequencia(m, [(2.0, frente)])
m.start_guided_calibration()
m.guided_target("espelho_motorista")
sequencia(m, [(3.0, lambda t: olhar(t, dyaw=30.0, como="cabeca"))], inicio=2.0)
m.guided_target(None)
zonas = m.finish_guided_calibration()
assert abs(zonas["espelho_motorista"][0] - 30.0) <= 1.5, zonas
out = sequencia(m, [(4.0, frente), (3.5, lambda t: olhar(t, dyaw=30.0, como="cabeca")), (2.0, frente)], inicio=5.0)
assert not eventos(out), [e.alert_type for _, e in eventos(out)]
assert any(a.zone == "espelho_motorista" for _, a in out)
ok("DMS-02 calibração guiada: espelho medido a +30° vira zona ligada à direção (sem aviso aos 3 s)")


# ---------------------------------------------------------------------------------------------------------------
# DMS-12a · PRC (percent road centre): % do olhar a até 8° da moda, em 60 s
g = GazeTracker(profile=FRENTE)
t = 0.0
while t < 60.0:
    dentro = (t % 5.0) < 4.0
    g.update(olhar(t, dyaw=0.0 if dentro else 20.0), 1.0, "ear")
    t += 1.0 / FPS
metricas = g.window_metrics(t)
assert abs(metricas["prc_60s"] - 0.80) <= 0.03, metricas
assert metricas["desvio_olhar_yaw_graus"] > 5.0 and metricas["desvio_olhar_pitch_graus"] < 1.0, metricas
ok(f"DMS-12a 80% do olhar a até 8° da moda por 60 s: PRC = {metricas['prc_60s']:.3f}")

# DMS-12b · entropia do olhar só conta como ativação sem piscada lenta (Shiferaw et al., 2018: ela sobe com a privação
# de sono).
from vision.activation import assess_activation  # noqa: E402

z = {"entropia_transicao_bits": 2.5, "sacadas_por_min": 2.5}
livre = assess_activation(z, {}, 0.75)
assert "olhar_mais_disperso" in livre.signals, livre
for janela, zs in (({"razao_duracao": 1.2}, {}), ({}, {"duracao_mediana_ms": 1.5}), ({"fechamentos_longos_5min": 1}, {})):
    lenta = assess_activation(dict(z, **zs), janela, 0.75)
    assert "olhar_mais_disperso" not in lenta.signals and "entropia_transicao_bits" not in lenta.contributions, \
        (janela, zs, lenta)
    assert lenta.state != "sinais_compativeis"
ok("DMS-12b entropia z = +2,5 com piscada 1,2× a base (ou z da duração +1,5, ou fechamento longo): não conta como "
   "ativação")


# ---------------------------------------------------------------------------------------------------------------
# DMS-18 · postura pela translação da matriz facial
for deslocamento, espera in ((20.0, True), (5.0, False)):
    m = DistractionMonitor(profile=FRENTE)
    out = sequencia(m, [(30.0, frente), (2.5, lambda t, d=deslocamento: olhar(t, x_cm=d)), (5.0, frente)])
    postura = eventos(out, "fora_da_posicao")
    assert bool(postura) == espera, (deslocamento, postura)
    if postura:
        assert 2.0 - 1e-6 <= postura[0][0] - 30.0 <= 2.1 and postura[0][1].details["deslocamento_cm"] >= 19.0
        assert not any(a.alarm for _, a in out)
ok("DMS-18a translação lateral de 20 cm por 2 s: fora_da_posicao (sem alarme); 5 cm: nada")


# ---------------------------------------------------------------------------------------------------------------
# Integração no engine: eventos, DriverState.distraction, janela e aviso
from vision.engine import DriverStateEngine  # noqa: E402

engine = DriverStateEngine(DrowsinessMonitor(profile=FRENTE), background_baseline=False)
estados = []
for segundos, quadro, t0 in ((4.0, frente, 0.0), (3.2, lambda t: olhar(t, dyaw=-45.0, como="cabeca"), 4.0),
                             (60.0, frente, 7.2)):
    for i in range(int(round(segundos * FPS))):
        t = t0 + i / FPS
        estados.append((t, engine.update(quadro(t))))
longas = [(t, e) for t, s in estados for e in s.events if e.alert_type == "distracao_longa"]
assert len(longas) == 1 and 3.0 - 1e-6 <= longas[0][0] - 4.0 <= 3.1
detalhes = longas[0][1].details
assert "nivel_risco" in detalhes and detalhes["zona"] == "fora", detalhes
estado_aviso = next(s for t, s in estados if t == longas[0][0])
assert estado_aviso.distraction is not None and estado_aviso.distraction.alarm
assert estado_aviso.alarm, "o aviso de distração chega ao DriverState.alarm (pelo risk.py ou pela ponte do engine)"
assert estados[-1][1].distraction.zone == "via" and estados[-1][1].window.get("prc_60s") is not None
assert not any(s.alarm for t, s in estados if t > longas[0][0] + 0.2)
ok("engine: distracao_longa chega em state.events com os detalhes de risco, DriverState.distraction preenchido, "
   "aviso no quadro do evento e PRC na janela")

print(f"\n{checks} verificações passaram.")
