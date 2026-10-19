"""Spec 027, pacote 2 · ALM-01 e ALM-02: microssono com o rosto perdido.

Cenário do experimento `exp_cabeca.py` da pesquisa (docs/pesquisa/2026-10-19-alarme-calibracao-e-registro.md, §0.2):
o olho fecha, a cabeça cai e o rosto sai da imagem 0,6 a 0,9 s depois. Antes da correção, nada tocava.

Só usa a biblioteca padrão (não precisa de câmera, OpenCV nem MediaPipe):
    python tests/test_rosto_perdido.py
"""
import sys
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "caixa"))
from vision.drowsiness import DrowsinessMonitor  # noqa: E402
from vision.eyes import DriverProfile  # noqa: E402

checks = 0
FPS = 30.0
CRITICOS = {"microssono", "sono", "nao_responsivo", "sono_rosto_perdido"}


def ok(message):
    global checks
    checks += 1
    print(f"OK {checks:02d} {message}")


def frame(t, face, ear=0.30, pitch=0.0):
    return NS(timestamp=t, face_found=face, ear=ear if face else None, blink_score=None, eye_open_prob=None,
              jaw_open=0.02 if face else None, pitch=pitch if face else None, yaw=0.0 if face else None,
              eye_distance_px=80.0)


def monitor():
    return DrowsinessMonitor(profile=DriverProfile(ear_open=0.30, ear_closed=0.06, pitch_baseline=0.0, yaw_baseline=0.0))


def run(scenario, seconds=12.0):
    """scenario(t) -> quadro. Devolve [(t, assessment)]."""
    m, out, t = monitor(), [], 0.0
    while t < seconds:
        out.append((t, m.update(scenario(t))))
        t += 1.0 / FPS
    return out


def criticos(out):
    return [(t, e.alert_type) for t, a in out for e in a.events if e.alert_type in CRITICOS]


def primeiro_alarme_critico(out, depois=0.0):
    return next((t for t, a in out if t >= depois and a.alarm and a.level == 3), None)


# ALM-01 · olho fechado, cabeça descendo e rosto perdido 0,6 s e 0,9 s depois: alarme crítico em até 2,0 s do
# fechamento e evento sono_rosto_perdido (antes: 0 alarmes e 0 eventos nos 4 s seguintes).
for perde in (0.6, 0.9):
    def cabeca_cai(t, perde=perde):
        if t < 5.0:
            return frame(t, True)
        fechado = t - 5.0
        if fechado >= perde:
            return frame(t, False)
        return frame(t, True, ear=0.06, pitch=min(20.0, fechado * 30))

    out = run(cabeca_cai)
    alarme = primeiro_alarme_critico(out, 5.0)
    assert alarme is not None and alarme - 5.0 <= 2.0, f"ALM-01 sem alarme crítico em 2 s (rosto some {perde} s): {alarme}"
    tipos = [tipo for _, tipo in criticos(out)]
    assert "sono_rosto_perdido" in tipos, f"ALM-01 sem evento sono_rosto_perdido: {tipos}"
    assert tipos.count("sono_rosto_perdido") == 1, f"ALM-01 evento repetido: {tipos}"
    evento = next(e for _, a in out for e in a.events if e.alert_type == "sono_rosto_perdido")
    assert evento.details["fechado_antes_de_perder_s"] >= 0.5 and evento.details["cabeca_desceu_graus"] > 5, evento.details
    # O alarme continua enquanto o rosto não volta (não é um bipe só).
    assert all(a.alarm for t, a in out if t >= alarme + 0.1), f"ALM-01 alarme parou com o rosto ainda fora ({perde} s)"
    ok(f"ALM-01 rosto some {perde} s depois de fechar: alarme crítico {alarme - 5.0:.2f} s após o fechamento e "
       f"evento sono_rosto_perdido")


# ALM-01 · o rosto volta com o olho aberto: o alarme para na hora.
def volta_acordado(t):
    if t < 5.0 or t >= 8.0:
        return frame(t, True)
    if t - 5.0 >= 0.6:
        return frame(t, False)
    return frame(t, True, ear=0.06, pitch=(t - 5.0) * 30)


out = run(volta_acordado)
assert primeiro_alarme_critico(out, 5.0) is not None
assert not any(a.alarm for t, a in out if t >= 8.0 + 2 / FPS), "ALM-01 alarme continuou com o olho aberto"
ok("ALM-01 rosto volta com o olho aberto: o alarme para no quadro seguinte")


# ALM-02 · olhos abertos, a cabeça desce e o rosto some 3 s (pegar algo no chão): nenhum alarme crítico.
def pega_no_chao(t):
    if t < 5.0 or t >= 9.0:
        return frame(t, True)
    if t < 6.0:
        return frame(t, True, pitch=(t - 5.0) * 40)  # passa de 25°: EAR descartado pela inclinação
    return frame(t, False)


out = run(pega_no_chao)
assert not criticos(out) and primeiro_alarme_critico(out) is None, criticos(out)
ok("ALM-02 olhos abertos, cabeça desce e rosto some 3 s: nenhum alarme crítico nem evento")


# ALM-02 · piscada normal no instante em que o rosto some: nada.
def piscada_e_some(t):
    if 5.0 <= t < 5.12:
        return frame(t, True, ear=0.06, pitch=(t - 5.0) * 30)
    if 5.12 <= t < 8.0:
        return frame(t, False)
    return frame(t, True)


out = run(piscada_e_some)
assert not criticos(out) and primeiro_alarme_critico(out) is None, criticos(out)
ok("ALM-02 piscada de 120 ms e o rosto some logo depois: nenhum alarme")


# ALM-02 · fechamento de 0,45 s sem a cabeça descer e rosto fora por 2 s: abaixo do fechamento longo, nada.
def fechamento_curto(t):
    if 5.0 <= t < 5.45:
        return frame(t, True, ear=0.06)
    if 5.45 <= t < 7.45:
        return frame(t, False)
    return frame(t, True)


out = run(fechamento_curto)
assert not criticos(out) and primeiro_alarme_critico(out) is None, criticos(out)
ok("ALM-02 fechamento de 0,45 s com a cabeça parada e rosto fora 2 s: nenhum alarme")


# ALM-01 · rosto fora só 0,3 s e de volta com o olho aberto antes de completar 1 s: nada (abriu a tempo).
def some_pouco(t):
    if 5.0 <= t < 5.6:
        return frame(t, True, ear=0.06, pitch=(t - 5.0) * 30)
    if 5.6 <= t < 5.9:
        return frame(t, False)
    return frame(t, True)


out = run(some_pouco)
assert primeiro_alarme_critico(out) is None, criticos(out)
ok("ALM-01 rosto fora 0,3 s e de volta com o olho aberto antes de 1 s de fechamento: sem alarme")


# ALM-01 · a cabeça cai além de 25° (EAR descartado pela inclinação) sem o rosto sumir: mesmo caso.
def cabeca_muito_baixa(t):
    if t < 5.0:
        return frame(t, True)
    fechado = t - 5.0
    return frame(t, True, ear=0.06, pitch=min(45.0, fechado * 40))


out = run(cabeca_muito_baixa)
alarme = primeiro_alarme_critico(out, 5.0)
assert alarme is not None and alarme - 5.0 <= 2.0, alarme
ok(f"ALM-01 cabeça cai além de 25° com o olho fechado (sem medida do olho): alarme crítico em {alarme - 5.0:.2f} s")

print(f"\n{checks} verificações passaram.")
