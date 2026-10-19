"""Spec 027, pacote 2 · calibração robusta e dinâmica da piscada.

CAL-01, CAL-02, CAL-03 (docs/pesquisa/2026-10-19-alarme-calibracao-e-registro.md, §2.3 e §6.1) e DMS-06
(docs/pesquisa/2026-10-19-estado-da-arte-dms.md, §7A). Os cenários são os dos experimentos exp_calib.py e
exp_calib2.py da pesquisa, copiados aqui para virar teste.

Só usa a biblioteca padrão:
    python tests/test_calibracao_robusta.py
"""
import json
import math
import random
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "caixa"))
from vision.baseline import BaselineStore  # noqa: E402
from vision.calibration import Calibrator  # noqa: E402
from vision.drowsiness import DrowsinessMonitor  # noqa: E402
from vision.engine import DriverStateEngine  # noqa: E402
from vision.eyes import DriverProfile, EyeStateTracker, Sample  # noqa: E402

checks = 0
EAR_OPEN, EAR_CLOSED = 0.30, 0.06


def ok(message):
    global checks
    checks += 1
    print(f"OK {checks:02d} {message}")


@dataclass
class Quadro(Sample):
    eyes_in_frame: bool = True


# --- cenário do exp_calib.py ------------------------------------------------------------------------------------
def blink_ear(t_rel, close_s, hold_s, open_s):
    """Fechamento linear, platô fechado e reabertura linear."""
    if t_rel < 0:
        return EAR_OPEN
    if t_rel < close_s:
        return EAR_OPEN - (EAR_OPEN - EAR_CLOSED) * t_rel / close_s
    if t_rel < close_s + hold_s:
        return EAR_CLOSED
    if t_rel < close_s + hold_s + open_s:
        return EAR_CLOSED + (EAR_OPEN - EAR_CLOSED) * (t_rel - close_s - hold_s) / open_s
    return EAR_OPEN


def quadros(fps, seconds, blink_params, seed, every=(2.0, 5.0)):
    """Quadros sintéticos como no experimento: piscadas em instantes aleatórios e ruído gaussiano de 0,006 no EAR."""
    rnd = random.Random(seed)
    blinks, t_next = [], 2.0
    while t_next < seconds:
        blinks.append((t_next, blink_params(rnd)))
        t_next += rnd.uniform(*every)
    i, dt = 0, 1.0 / fps
    t = rnd.uniform(0, dt)
    while t < seconds:
        while i + 1 < len(blinks) and t > blinks[i][0] + sum(blinks[i][1]) + 0.05:
            i += 1
        b0, p = blinks[i]
        ear = blink_ear(t - b0, *p) + rnd.gauss(0, 0.006)
        yield Quadro(timestamp=t, face_found=True, ear=ear, jaw_open=0.02, pitch=0.0, yaw=0.0, eye_distance_px=80.0)
        t += dt


def alerta(rnd):
    return rnd.uniform(0.07, 0.10), rnd.uniform(0.0, 0.04), rnd.uniform(0.12, 0.18)


def moderado(rnd):
    """exp_calib2.py: piscadas ~48% mais longas e, em 3% delas, fechamento de 0,4 a 0,7 s."""
    if rnd.random() < 0.97:
        return rnd.uniform(0.09, 0.12), rnd.uniform(0.03, 0.08), rnd.uniform(0.17, 0.23)
    return 0.12, rnd.uniform(0.4, 0.7), 0.25


def moderado_sem_fechamento_longo(rnd):
    return rnd.uniform(0.09, 0.12), rnd.uniform(0.03, 0.08), rnd.uniform(0.17, 0.23)


def calibra(fps, seconds, params, seed, reference=None):
    calibrator = Calibrator(min_seconds=seconds, max_seconds=seconds, target_blinks=10 ** 6)
    if reference is not None:
        calibrator.duration_reference = reference
    for quadro in quadros(fps, seconds, params, seed):
        calibrator.add(quadro)
    return calibrator.build_profile()


# CAL-01 · referência de olho fechado robusta à taxa de quadros (antes: +57% de erro a 10 fps).
resultados = {}
for fps in (10, 15, 30):
    for seed in (1, 2, 3):
        profile = calibra(fps, 300, alerta, seed)
        erro = abs(profile.ear_closed - EAR_CLOSED)
        assert erro <= 0.012, f"CAL-01 {fps} fps semente {seed}: ear_closed {profile.ear_closed:.4f}"
        resultados.setdefault(fps, []).append(profile)
    qualidade = {p.calibration_quality for p in resultados[fps]}
    if fps < 20:  # pesquisa §2.3 a: abaixo de 20 fps a referência fica marcada como estimada
        assert "boa" not in qualidade and all(p.ear_closed_estimated for p in resultados[fps]), qualidade
    else:
        assert qualidade == {"boa"} and not any(p.ear_closed_estimated for p in resultados[fps]), qualidade
ok("CAL-01 ear_closed a 10, 15 e 30 fps (3 sementes): " + ", ".join(
    f"{fps} fps {min(p.ear_closed for p in ps):.3f}–{max(p.ear_closed for p in ps):.3f}" for fps, ps in resultados.items())
   + f"; a 10 fps qualidade '{resultados[10][0].calibration_quality}'")

# CAL-02 · calibração com sono moderado (exp_calib2.py) vira suspeita.
moderada = calibra(30, 300, moderado, 2)
assert not moderada.looked_alert, moderada.summary()
assert "fechamento_longo" in moderada.suspect_reasons, moderada.suspect_reasons
ok(f"CAL-02 calibração com piscadas mais longas e fechamento de {moderada.longest_closure_s:.2f} s: suspeita "
   f"({', '.join(moderada.suspect_reasons)})")

alerta_30 = calibra(30, 300, alerta, 1)
referencia = (alerta_30.blink_duration_median_s * 1000.0, 20.0)
sem_longo = calibra(30, 300, moderado_sem_fechamento_longo, 4, reference=referencia)
assert not sem_longo.looked_alert and "piscadas_mais_longas_que_o_habitual" in sem_longo.suspect_reasons, \
    (sem_longo.blink_duration_median_s, referencia, sem_longo.suspect_reasons)
sem_referencia = calibra(30, 300, moderado_sem_fechamento_longo, 4)
assert sem_referencia.looked_alert, "sem linha de base acumulada, só a duração não basta para apontar"
ok(f"CAL-02 piscada mediana {sem_longo.blink_duration_median_s * 1000:.0f} ms contra {referencia[0]:.0f} ms da "
   "linha de base acumulada: suspeita (z ≥ 1,5); sem acumulada, não")


# CAL-02/CAL-03 pelo caminho real: DrowsinessMonitor + engine + perfil salvo + linha de base acumulada.
def viagem_com_calibracao(params, seed, perfil_anterior=None):
    pasta = Path(tempfile.mkdtemp(prefix="rotaguard-cal-"))
    perfil_path = pasta / "perfil.json"
    if perfil_anterior is not None:
        perfil_anterior.save(perfil_path)
    antes = perfil_path.read_text(encoding="utf-8") if perfil_path.exists() else None
    store = BaselineStore(pasta / "linha_de_base.json")
    monitor = DrowsinessMonitor(profile=perfil_anterior, calibrator=Calibrator(300, 300, 10 ** 6), profile_path=perfil_path)
    engine = DriverStateEngine(monitor, baseline_store=store, background_baseline=False)
    eventos = []
    for quadro in quadros(30, 330, params, seed):
        eventos.extend(e.alert_type for e in engine.update(quadro).events)
    return monitor, store, perfil_path, antes, eventos


anterior = alerta_30
monitor, store, perfil_path, antes, eventos = viagem_com_calibracao(moderado, 2, perfil_anterior=anterior)
assert "calibracao_suspeita" in eventos and "calibracao_concluida" not in eventos, eventos
assert monitor.profile is anterior, "com perfil salvo, o perfil salvo continua valendo"
assert perfil_path.read_text(encoding="utf-8") == antes, "o arquivo do perfil não pode mudar"
assert store.load() is None, "a linha de base acumulada não pode mudar"
ok("CAL-02 pelo engine: evento calibracao_suspeita, perfil salvo continua (arquivo intacto), acumulada intacta")

monitor, store, perfil_path, antes, eventos = viagem_com_calibracao(alerta, 1)
assert "calibracao_concluida" in eventos and "calibracao_suspeita" not in eventos, eventos
assert monitor.profile.looked_alert and monitor.profile.calibration_quality == "boa"
assert DriverProfile.load(perfil_path).ear_closed == monitor.profile.ear_closed
assert store.load() is not None and store.load().trips == 1
ok("CAL-03 calibração alerta: concluída, perfil salvo e linha de base acumulada atualizada, como antes")

# CAL-02 · o engine passa a duração da linha de base acumulada (≥ 3 viagens) para a calibração.
pasta = Path(tempfile.mkdtemp(prefix="rotaguard-cal-acum-"))
acumulada = {"versao": 1, "viagens": 3, "metricas": {"duracao_mediana_ms": {"n": 30, "media": 150.0, "variancia": 100.0}}}
(pasta / "acumulada.json").write_text(json.dumps(acumulada), encoding="utf-8")
calibrador = Calibrator(300, 300, 10 ** 6)
engine = DriverStateEngine(DrowsinessMonitor(calibrator=calibrador), baseline_store=BaselineStore(pasta / "acumulada.json"),
                           background_baseline=False)
engine.update(Quadro(timestamp=0.0, face_found=True, ear=0.3, pitch=0.0, yaw=0.0, eye_distance_px=80.0))
assert calibrador.duration_reference == (150.0, 20.0), calibrador.duration_reference
ok("CAL-02 o engine entrega à calibração a duração da acumulada (média 150 ms, desvio com piso de 20 ms)")


# --- DMS-06 · dinâmica da piscada --------------------------------------------------------------------------------
def piscada_linear(t, inicio, fechamento, reabertura, platô=0.0):
    tau = t - inicio
    if tau < 0:
        return 1.0
    if tau < fechamento:
        return 1.0 - tau / fechamento
    if tau < fechamento + platô:
        return 0.0
    if tau < fechamento + platô + reabertura:
        return (tau - fechamento - platô) / reabertura
    return 1.0


medidas = []
for fase in (0.0, 0.008, 0.017, 0.025):
    tracker = EyeStateTracker()
    blinks = []
    t = fase
    while t < 3.0:
        blink = tracker.update(t, piscada_linear(t, 1.0, 0.08, 0.30))
        if blink is not None:
            blinks.append(blink)
        t += 1 / 30
    assert len(blinks) == 1
    assert blinks[0].reopening_s is not None and abs(blinks[0].reopening_s - 0.30) <= 0.04, blinks[0]
    assert blinks[0].closing_s is not None and abs(blinks[0].closing_s - 0.08) <= 0.03, blinks[0]
    medidas.append(blinks[0].reopening_s)
ok("DMS-06a piscada a 30 fps com fechamento de 80 ms e reabertura de 300 ms: reabertura_s "
   f"{min(medidas):.3f}–{max(medidas):.3f} s em 4 fases do quadro")


def perfil_dinamica(**extra):
    base = dict(ear_open=0.30, ear_closed=0.06, pitch_baseline=0.0, yaw_baseline=0.0, perclos_baseline=0.0,
                blink_duration_median_s=0.208, blink_closing_avr_median_s=0.08, blink_reopening_median_s=0.200,
                blink_closing_median_s=0.08, blink_rate_per_min=15.0, blink_duration_p90_s=0.25)
    base.update(extra)
    return DriverProfile(**base)


def roda_piscadas(monitor, fps, segundos, fechamento, reabertura, every=4.0):
    out = []
    t = 0.0
    while t < segundos:
        inicio = math.floor(t / every) * every + 1.0
        o = piscada_linear(t, inicio, fechamento, reabertura)
        ear = EAR_CLOSED + o * (EAR_OPEN - EAR_CLOSED)
        out.append((t, monitor.update(Quadro(timestamp=t, face_found=True, ear=ear, jaw_open=0.02, pitch=0.0, yaw=0.0,
                                             eye_distance_px=80.0))))
        t += 1.0 / fps
    return out


VELOCIDADE = ("avr_fechamento_ms", "avr_abertura_ms", "fechamento_mediano_ms", "reabertura_mediana_ms",
              "avr_fechamento_desvio_ms")
lento = DrowsinessMonitor(profile=perfil_dinamica())
roda_piscadas(lento, 20.0, 300.0, 0.08, 0.28)
assert not any(chave in lento.details for chave in VELOCIDADE), sorted(lento.details)
rapido = DrowsinessMonitor(profile=perfil_dinamica())
roda_piscadas(rapido, 30.0, 300.0, 0.08, 0.28)
assert all(chave in rapido.details for chave in VELOCIDADE), sorted(rapido.details)
assert "fracao_acima_p90" in rapido.details and "razao_frequencia_piscadas" in rapido.details, sorted(rapido.details)
ok("DMS-06b abaixo de 28 fps nenhum campo de velocidade da pálpebra na janela; a 30 fps, reabertura, fechamento, "
   "desvio do AVR, fração acima do p90 e frequência contra a base")

# A base da reabertura sai do mesmo cálculo (como na calibração): piscadas com reabertura de 200 ms.
base = DrowsinessMonitor(profile=perfil_dinamica())
roda_piscadas(base, 30.0, 300.0, 0.08, 0.20)
reabertura_base_s = base.details["reabertura_mediana_ms"] / 1000.0
monitor = DrowsinessMonitor(profile=perfil_dinamica(blink_reopening_median_s=reabertura_base_s))
out = roda_piscadas(monitor, 30.0, 660.0, 0.08, 0.28)
depois_de_5min = [a for t, a in out if t >= 300.0]
assert any("reabertura_lenta" in a.reasons and a.level == 1 for a in depois_de_5min), monitor.details
assert max(a.level for _, a in out) == 1, "reabertura lenta sozinha nunca vira nível 2"
assert abs(monitor.details["razao_reabertura"] - 1.4) <= 0.07, monitor.details.get("razao_reabertura")
ok(f"DMS-06c reabertura mediana {monitor.details['razao_reabertura']:.2f}× a base por 11 min: motivo leve "
   "reabertura_lenta (nível 1) e nunca nível 2 sozinho")

print(f"\n{checks} verificações passaram.")
