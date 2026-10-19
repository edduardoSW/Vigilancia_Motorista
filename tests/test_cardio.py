"""Spec 022 · frequência cardíaca pela face (rPPG): critérios CAR-01 a CAR-14.

O número só aparece depois do aquecimento (AQUECIMENTO_S, 15 s de dados bons: ~3 janelas de 10 s seguidas, pedido da
coordenação a partir da pesquisa rPPG de 19/10/2026); por isso as séries têm 16,5 s. A janela do espectro continua 10 s
e a primeira estimativa interna sai com 6 s (spec 022).

Quadros sintéticos de pele com pulso, luz, respiração e ruído, e pontos do rosto sintéticos. CAR-11 e CAR-13 usam uma
foto real de rosto (grace_hopper.jpg, que vem com o matplotlib) e o Face Landmarker do MediaPipe; sem a foto ou sem o
modelo, esses dois critérios aparecem como PULADO (não contam como aprovados).
    python tests/test_cardio.py
"""
from __future__ import annotations

import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "caixa"))
from vision.cardio import (  # noqa: E402
    AQUECIMENTO_S,
    LIMIAR_MOVIMENTO,
    LIMIAR_SNR_DB,
    ROI_BOCHECHA_DIR,
    ROI_BOCHECHA_ESQ,
    ROI_TESTA,
    SEM_ROSTO_S,
    CardioMonitor,
    CardioReading,
    canal_unico,
    estimar_bpm,
    media_das_rois,
    pos,
    reamostrar,
    remover_tendencia,
)
from vision.drowsiness import DrowsinessMonitor  # noqa: E402
from vision.engine import CARDIO_KEYS, PRIVATE_KEYS, DriverStateEngine  # noqa: E402
from vision.eyes import DriverProfile, Sample  # noqa: E402
from vision.risk import RiskAssessment  # noqa: E402

checks = 0
pulados = []


def ok(message):
    global checks
    checks += 1
    print(f"OK {checks:02d} {message}")


def pulado(message):
    pulados.append(message)
    print(f"PULADO {message}")


# Pele em BGR e pulsatilidade relativa R, G, B = 0,33 / 0,77 / 0,53 (Wang et al., 2017), aqui em BGR com G = 1:
# o pulso é maior no verde que no vermelho e no azul. O sangue absorve luz, então a pele escurece a cada batimento.
PELE_BGR = np.array([100.0, 130.0, 180.0])
PULSO_BGR = np.array([0.53, 0.77, 0.33]) / 0.77
CINZA_IR = 120.0


def rosto(caixa=(0, 0, 64, 48), desvio=(0.0, 0.0)):
    """478 pontos sintéticos: ROIs em elipses (na ordem das tuplas), cantos externos dos olhos e nariz; o resto no
    centro do rosto."""
    x0, y0, w, h = caixa
    pts = np.zeros((478, 2), np.float32)
    pts[:] = (x0 + w / 2, y0 + h / 2)

    def elipse(indices, cx, cy, rx, ry):
        for k, i in enumerate(indices):
            a = 2 * math.pi * k / len(indices)
            pts[i] = (x0 + (cx + rx * math.cos(a)) * w, y0 + (cy + ry * math.sin(a)) * h)

    elipse(ROI_TESTA, 0.50, 0.20, 0.25, 0.10)
    elipse(ROI_BOCHECHA_ESQ, 0.27, 0.65, 0.13, 0.15)  # "esq" = lado esquerdo da imagem
    elipse(ROI_BOCHECHA_DIR, 0.73, 0.65, 0.13, 0.15)
    pts[33] = (x0 + 0.22 * w, y0 + 0.42 * h)
    pts[263] = (x0 + 0.78 * w, y0 + 0.42 * h)
    pts[1] = (x0 + 0.50 * w, y0 + 0.55 * h)
    return pts + np.asarray(desvio, np.float32)


def serie(bpm, segundos=16.5, fps=30.0, amp=0.003, ruido_px=1.5, ruido_quadro=0.08, luz=None, resp_rpm=None,
          resp_amp=0.0, mono=False, tempos=None, semente=0, tamanho=(48, 64)):
    """Gera (t, quadro BGR uint8): pele uniforme com pulso (e 2º harmônico), luz, respiração, ruído por quadro e por
    pixel. O ruído por pixel também desfaz o degrau de 1 nível do uint8, como o ruído do sensor numa câmera real.
    Padrão = pessoa parada com boa luz: pulso de 0,3% no verde e ruído de ~0,13 nível por canal na média de cada ROI
    (~200 px). Com o dobro do ruído o SNR fica perto do limiar de 0 dB e o monitor passa a dizer "sinal fraco" em parte
    das janelas, que é o comportamento esperado (ver LIMIAR_SNR_DB no vision/cardio.py)."""
    rng = np.random.default_rng(semente)
    if tempos is None:
        tempos = np.arange(int(round(segundos * fps))) / fps
    fase = rng.uniform(0.0, 2 * math.pi)
    altura, largura = tamanho
    for t in tempos:
        pulso = 0.0
        if bpm is not None:
            angulo = 2 * math.pi * bpm / 60.0 * t + fase
            pulso = math.sin(angulo) + 0.3 * math.sin(2 * angulo + 0.5)
        ganho = luz(t) if luz is not None else 1.0
        if resp_rpm:
            ganho *= 1.0 + resp_amp * math.sin(2 * math.pi * resp_rpm / 60.0 * t)
        if mono:
            cor = CINZA_IR * ganho * (1.0 - amp * pulso) + rng.normal(0.0, ruido_quadro)
            imagem = np.repeat(cor + rng.normal(0.0, ruido_px, (altura, largura, 1)), 3, axis=2)
        else:
            cor = PELE_BGR * ganho * (1.0 - amp * pulso * PULSO_BGR) + rng.normal(0.0, ruido_quadro, 3)
            imagem = cor + rng.normal(0.0, ruido_px, (altura, largura, 3))
        yield float(t), np.clip(np.rint(imagem), 0, 255).astype(np.uint8)


def medir(quadros, monitor=None, pontos=None, infrared=False):
    monitor = monitor or CardioMonitor()
    pontos = rosto() if pontos is None else pontos
    leituras = [monitor.update(imagem, pontos, t, infrared=infrared) for t, imagem in quadros]
    return monitor, leituras


# ---------------------------------------------------------------------------------------------------------------
# Funções puras: reamostragem pelo horário e POS anulando mudança só de intensidade (base de CAR-03 e CAR-06).
ts = np.cumsum(np.random.default_rng(1).uniform(0.022, 0.034, 200))
grade, valores = reamostrar(ts, np.stack([3.0 * ts + 1.0, -ts], axis=1), 30.0)
assert abs(np.diff(grade).mean() - 1 / 30.0) < 1e-9 and grade[0] >= ts[0] and grade[-1] <= ts[-1]
assert np.allclose(valores[:, 0], 3.0 * grade + 1.0) and np.allclose(valores[:, 1], -grade)
t30 = np.arange(300) / 30.0
so_luz = np.outer(1.0 + 0.3 * t30 / 10.0 + 0.05 * np.sin(2 * np.pi * 1.2 * t30), [180.0, 130.0, 100.0])
assert np.abs(pos(so_luz, 30.0)).max() < 1e-9, "POS deveria anular variação só de intensidade"
limpo = np.sin(2 * np.pi * 1.2 * t30)
bpm_limpo, snr_limpo = estimar_bpm(limpo, 30.0)
assert abs(bpm_limpo - 72.0) < 0.5 and snr_limpo > 20.0, (bpm_limpo, snr_limpo)


def pos_do_artigo(rgb, fs):
    """Algoritmo 1 de Wang et al. 2017, linha a linha (laço), para conferir a versão em O(N)."""
    n, comprimento = len(rgb), int(math.ceil(1.6 * fs))
    saida = np.zeros(n)
    projecao = np.array([[0.0, 1.0, -1.0], [-2.0, 1.0, 1.0]])
    for fim in range(comprimento, n + 1):
        janela = rgb[fim - comprimento:fim]
        s = (janela / janela.mean(axis=0)) @ projecao.T
        h = s[:, 0] + s[:, 0].std() / s[:, 1].std() * s[:, 1]
        saida[fim - comprimento:fim] += h - h.mean()
    return saida


aleatorio = np.random.default_rng(2)
amostra = np.array([180.0, 130.0, 100.0]) * (1 + 0.01 * aleatorio.normal(size=(400, 3)))
assert np.allclose(pos(amostra, 30.0), pos_do_artigo(amostra, 30.0), rtol=1e-7, atol=1e-9), "POS O(N) ≠ artigo"
cinza = 120.0 * (1 + 0.01 * aleatorio.normal(size=400))
referencia = np.zeros(400)
for fim in range(48, 401):
    janela = cinza[fim - 48:fim]
    referencia[fim - 48:fim] += janela / janela.mean() - 1.0
assert np.allclose(canal_unico(cinza, 30.0), referencia, atol=1e-9), "canal único O(N) ≠ laço"
# Tarvainen em banda = fórmula densa; corte de -3 dB perto de 0,34 Hz com lambda 300 a 30 Hz; pulso de 42 bpm passa.
d2 = np.diff(np.eye(300), 2, axis=0)
densa = amostra[:300, 1] - np.linalg.solve(np.eye(300) + 300.0 ** 2 * d2.T @ d2, amostra[:300, 1])
assert np.allclose(remover_tendencia(amostra[:300, 1]), densa, atol=1e-8), "Tarvainen em banda ≠ fórmula densa"


def ganho(frequencia):
    x = np.sin(2 * np.pi * frequencia * t30)
    return remover_tendencia(x)[75:225].std() / x[75:225].std()


assert ganho(0.25) < 0.707 < ganho(0.45) and ganho(0.7) > 0.9, (ganho(0.25), ganho(0.45), ganho(0.7))
ok("reamostrar pelo horário é exato numa reta; POS O(N) igual ao laço do artigo e anula variação só de intensidade; "
   f"Tarvainen igual à fórmula densa, corte entre 0,25 e 0,45 Hz, ganho {ganho(0.7):.2f} em 42 bpm; senoide limpa de "
   f"72 bpm dá {bpm_limpo:.1f} bpm com SNR {snr_limpo:.1f} dB")


# CAR-01 · 72 bpm, pulso maior no verde, ruído branco: erro ≤ 2 bpm (janela de 10 s, depois do aquecimento).
rng = np.random.default_rng(11)
fase = rng.uniform(0, 2 * math.pi)
pulso30 = np.sin(2 * np.pi * 1.2 * t30 + fase)
# Ruído branco de 0,1 nível por canal: média de uma ROI de ~1.000 px com ruído de sensor de σ ≈ 3 níveis.
rgb = np.array([180.0, 130.0, 100.0]) * (1 - 0.003 * pulso30[:, None] * PULSO_BGR[::-1]) + rng.normal(0, 0.1, (300, 3))
bpm_puro, snr_puro = estimar_bpm(pos(rgb, 30.0), 30.0)
assert abs(bpm_puro - 72.0) <= 2.0 and snr_puro >= LIMIAR_SNR_DB, ("CAR-01 funções puras", bpm_puro, snr_puro)
monitor, leituras = medir(serie(72))
final = leituras[-1]
assert isinstance(final, CardioReading)
assert final.estado == "pronto" and abs(final.bpm - 72.0) <= 2.0, ("CAR-01", final.estado, final.bpm, final.snr_db)
assert final.canal == "rgb" and 0.0 < final.confianca <= 1.0 and final.snr_db >= LIMIAR_SNR_DB, "CAR-01"
assert set(final.rois) == {"testa", "bochecha_esq", "bochecha_dir"}, "CAR-01 rois"
assert all(len(p) >= 3 and all(isinstance(v, int) for xy in p for v in xy) for p in final.rois.values()), "CAR-01"
assert 150 <= len(final.onda) <= 200 and max(abs(v) for v in final.onda) <= 1.0 + 1e-9, ("CAR-01 onda", len(final.onda))
assert final.historico_bpm and final.ultimo_bpm == final.bpm and final.progresso == 1.0, "CAR-01"
ok(f"CAR-01 72 bpm sintético: funções puras {bpm_puro:.1f} bpm; monitor {final.bpm:.1f} bpm, "
   f"SNR {final.snr_db:.1f} dB, "
   f"confiança {final.confianca:.2f}, onda de {len(final.onda)} pontos")


# CAR-02 · 55, 90 e 140 bpm: erro ≤ 3 bpm em cada (três sementes por frequência).
erros = {}
for bpm in (55, 90, 140):
    for semente in (1, 2, 3):
        final = medir(serie(bpm, semente=semente))[1][-1]
        assert final.estado == "pronto" and abs(final.bpm - bpm) <= 3.0, \
            ("CAR-02", bpm, semente, final.estado, final.bpm)
        erros[bpm] = max(erros.get(bpm, 0.0), abs(final.bpm - bpm))
ok("CAR-02 55, 90 e 140 bpm com 3 sementes: maior erro " + ", ".join(f"{b} bpm → {e:.1f}" for b, e in erros.items()))


# CAR-03 · taxa irregular (quadros entre 22 e 34 ms): erro ≤ 3 bpm.
for semente in (4, 5):
    passos = np.random.default_rng(semente).uniform(0.022, 0.034, 800)
    tempos = np.cumsum(passos)
    tempos = tempos[tempos <= 16.5]
    final = medir(serie(72, tempos=tempos, semente=semente))[1][-1]
    assert final.estado == "pronto" and abs(final.bpm - 72.0) <= 3.0, ("CAR-03", semente, final.estado, final.bpm)
ok(f"CAR-03 quadros a cada 22 a 34 ms: {final.bpm:.1f} bpm")


# CAR-04 · só ruído: "sinal_fraco" e bpm None (nenhuma leitura "pronto" no caminho).
snrs = []
for semente in range(1, 7):
    monitor, leituras = medir(serie(None, semente=semente))
    final = leituras[-1]
    assert final.estado == "sinal_fraco" and final.bpm is None, ("CAR-04", semente, final.estado, final.snr_db)
    assert not any(leitura.estado == "pronto" for leitura in leituras) and not final.historico_bpm, ("CAR-04", semente)
    snrs.append(final.snr_db)
ok(f"CAR-04 só ruído (6 sementes): sempre sinal fraco, SNR máximo {max(snrs):.1f} dB (limiar {LIMIAR_SNR_DB} dB)")


# CAR-05 · antes de 6 s (e até o fim do aquecimento): "medindo" e progresso crescendo entre 0 e 1.
monitor = CardioMonitor()
progresso_anterior, aos_6s = -1.0, None
for t, imagem in serie(72, segundos=16.0):
    leitura = monitor.update(imagem, rosto(), t)
    if t < AQUECIMENTO_S - 0.01:
        assert leitura.estado == "medindo" and leitura.bpm is None, ("CAR-05", t, leitura.estado)
        assert 0.0 <= leitura.progresso < 1.0 and leitura.progresso >= progresso_anterior, \
            ("CAR-05", t, leitura.progresso)
        progresso_anterior = leitura.progresso
        if t < 6.0:
            aos_6s = leitura.progresso
assert progresso_anterior >= 0.95, ("CAR-05 progresso perto do fim do aquecimento", progresso_anterior)
assert leitura.estado == "pronto" and leitura.progresso == 1.0, ("CAR-05 depois do aquecimento", leitura.estado)
ok(f"CAR-05 medindo antes de 6 s (progresso {aos_6s:.2f}) e até {AQUECIMENTO_S:.0f} s (progresso até "
   f"{progresso_anterior:.2f}); pronto em seguida ({leitura.bpm:.1f} bpm)")


# CAR-06 · rampa de luz de 30% em 10 s não muda o bpm em mais de 3.
estavel = medir(serie(72, semente=8))[1][-1]
# +30% nos últimos 10 s (a janela do espectro inteira em rampa); mais que isso satura o vermelho (>= 250 sai da média).
rampa = medir(serie(72, semente=8, luz=lambda t: 1.0 + 0.3 * max(0.0, t - 6.5) / 10.0))[1][-1]
assert rampa.estado == "pronto" and abs(rampa.bpm - estavel.bpm) <= 3.0 and abs(rampa.bpm - 72.0) <= 3.0, \
    ("CAR-06", estavel.bpm, rampa.estado, rampa.bpm)
ok(f"CAR-06 rampa de luz de 30%: {rampa.bpm:.1f} bpm contra {estavel.bpm:.1f} bpm com luz estável")


# CAR-07 · pontos andando mais que o limiar: "movimento"; tremor pequeno dos pontos não pausa.
caixa = (32, 24, 64, 48)
base = rosto(caixa)
distancia_olhos = float(np.linalg.norm(base[263] - base[33]))
tremor = np.random.default_rng(3)
monitor = CardioMonitor()
estados = {}
for t, imagem in serie(72, segundos=22.0, tamanho=(96, 128), semente=6):
    if t < 17.0:
        pontos = base + tremor.uniform(-0.3, 0.3, base.shape).astype(np.float32)
    elif t < 18.0:
        pontos = base + np.float32([40.0 * (t - 17.0), 0.0])  # 40 px/s, ~1,1 distância entre os olhos por segundo
    else:
        pontos = base + np.float32([40.0, 0.0])
    leitura = monitor.update(imagem, pontos, t)
    if 16.5 <= t < 17.0:
        estados.setdefault("parado", []).append(leitura.estado)
    elif 17.3 <= t < 18.0:
        estados.setdefault("andando", []).append(leitura)
    if leitura.estado == "pronto" and t < 17.3:
        bom = leitura.bpm  # último número mostrado antes de virar "movimento"
assert set(estados["parado"]) == {"pronto"}, ("CAR-07 tremor de ±0,3 px não é movimento", set(estados["parado"]))
assert all(r.estado == "movimento" and r.bpm is None and r.ultimo_bpm is not None for r in estados["andando"]), \
    ("CAR-07", [(r.estado, r.bpm) for r in estados["andando"]])
assert abs(estados["andando"][-1].ultimo_bpm - bom) < 1e-9, "CAR-07 último bpm bom guardado"
assert leitura.estado == "pronto" and abs(leitura.bpm - 72.0) <= 3.0, \
    ("CAR-07 volta a medir", leitura.estado, leitura.bpm)
ok(f"CAR-07 rosto andando {40.0 / distancia_olhos:.2f} distâncias entre os olhos por segundo (limiar "
   f"{LIMIAR_MOVIMENTO} em 0,5 s): movimento com o último bpm guardado; parado de novo, volta a {leitura.bpm:.1f} bpm")


# CAR-08 · quadro monocromático (três canais iguais): canal "ir" e ainda acha 72 bpm com SNR moderado.
final = medir(serie(72, mono=True, amp=0.002, semente=9))[1][-1]
assert final.canal == "ir" and final.estado == "pronto" and abs(final.bpm - 72.0) <= 3.0, \
    ("CAR-08", final.canal, final.estado, final.bpm, final.snr_db)
marcado = medir(serie(72, semente=9), infrared=True)[1][-1]
assert marcado.canal == "ir" and marcado.estado == "pronto" and abs(marcado.bpm - 72.0) <= 3.0, ("CAR-08 flag", marcado)
ok(f"CAR-08 monocromático: canal ir, {final.bpm:.1f} bpm com SNR {final.snr_db:.1f} dB; quadro marcado como "
   f"infravermelho também usa um canal só ({marcado.bpm:.1f} bpm)")


# CAR-09 · respiração sintética de 15 rpm somada ao sinal: respiração entre 13 e 17 rpm.
final = medir(serie(72, segundos=32.0, resp_rpm=15, resp_amp=0.01, semente=10))[1][-1]
assert final.respiracao_rpm is not None and 13.0 <= final.respiracao_rpm <= 17.0, ("CAR-09", final.respiracao_rpm)
assert final.estado == "pronto" and abs(final.bpm - 72.0) <= 3.0, ("CAR-09 bpm", final.bpm)
ok(f"CAR-09 respiração sintética de 15 rpm: {final.respiracao_rpm:.1f} rpm (bpm {final.bpm:.1f})")


# CAR-10 · sem rosto por mais de 2 s: "sem_rosto" e janelas zeradas.
monitor = CardioMonitor()
quadros = list(serie(72, segundos=21.0, semente=12))
antes = None
for t, imagem in quadros:
    sumiu = 17.0 <= t < 19.5
    leitura = monitor.update(imagem, None if sumiu else rosto(), t)
    if t < 17.0:
        antes = leitura
    elif 17.0 <= t < 17.0 + SEM_ROSTO_S - 0.1:
        assert leitura.estado != "sem_rosto", ("CAR-10 menos de 2 s ainda não é sem rosto", t)
    elif 17.0 + SEM_ROSTO_S + 0.05 <= t < 19.5:
        assert leitura.estado == "sem_rosto" and leitura.bpm is None and leitura.progresso == 0.0, \
            ("CAR-10", t, leitura)
        assert leitura.onda == [] and monitor.amostras == 0 and leitura.ultimo_bpm is None, ("CAR-10 zeradas", t)
    elif t >= 19.5:
        assert leitura.estado == "medindo" and leitura.progresso < 1.0, ("CAR-10 recomeça", t, leitura.estado)
assert antes.estado == "pronto" and CardioMonitor().update(quadros[0][1], None, 0.0).estado == "sem_rosto"
ok("CAR-10 sem rosto por mais de 2 s: sem_rosto, janelas zeradas; rosto de volta recomeça a medir")


# CAR-11 · média das ROIs com quadro e pontos reais (foto + MediaPipe): testa acima das sobrancelhas e dentro do rosto.
MODELO = Path(__file__).resolve().parents[1] / "caixa" / "vision" / "models" / "face_landmarker.task"
# Contornos do MediaPipe (FACE_LANDMARKS_FACE_OVAL, *_EYEBROW, *_EYE e LIPS em mediapipe/tasks/python/vision/
# face_landmarker.py): oval do rosto em ordem, sobrancelhas (borda de cima + borda de baixo) e olhos.
OVAL = (10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 176, 149,
        150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109)
SOBRANCELHAS = ((70, 63, 105, 66, 107, 55, 65, 52, 53, 46), (300, 293, 334, 296, 336, 285, 295, 282, 283, 276))
OLHOS = ((33, 246, 161, 160, 159, 158, 157, 173, 133, 155, 154, 153, 145, 144, 163, 7),
         (263, 466, 388, 387, 386, 385, 384, 398, 362, 382, 381, 380, 374, 373, 390, 249))
LABIOS = (61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291, 375, 321, 405, 314, 17, 84, 181, 91, 146)


def foto_de_rosto():
    try:
        import matplotlib.cbook as cbook

        caminho = cbook.get_sample_data("grace_hopper.jpg", asfileobj=False)
    except Exception as exc:  # noqa: BLE001
        return None, f"foto de exemplo do matplotlib indisponível ({exc})"
    imagem = cv2.imread(str(caminho))
    return (imagem, None) if imagem is not None else (None, f"não abriu {caminho}")


def pontos_reais(imagem):
    try:
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision as mp_vision

        opcoes = mp_vision.FaceLandmarkerOptions(base_options=mp_python.BaseOptions(model_asset_path=str(MODELO)),
                                                 running_mode=mp_vision.RunningMode.IMAGE, num_faces=1)
        with mp_vision.FaceLandmarker.create_from_options(opcoes) as detector:
            resultado = detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB,
                                                 data=cv2.cvtColor(imagem, cv2.COLOR_BGR2RGB)))
    except Exception as exc:  # noqa: BLE001
        return None, f"MediaPipe ou modelo indisponível ({exc})"
    if not resultado.face_landmarks:
        return None, "o MediaPipe não achou rosto na foto"
    altura, largura = imagem.shape[:2]
    return np.array([(p.x * largura, p.y * altura) for p in resultado.face_landmarks[0]], np.float32), None


def mascara(forma, poligono):
    m = np.zeros(forma, np.uint8)
    cv2.fillPoly(m, [np.round(np.asarray(poligono)).astype(np.int32)], 255)
    return m > 0


foto, motivo = foto_de_rosto()
reais = None
if foto is not None:
    reais, motivo = pontos_reais(foto)
if reais is None:
    pulado(f"CAR-11 {motivo}")
else:
    forma = foto.shape[:2]
    rgb, rois, pixels = media_das_rois(foto, reais)
    assert rgb is not None and pixels > 300 and set(rois) == {"testa", "bochecha_esq", "bochecha_dir"}, "CAR-11"
    assert rgb[0] > rgb[1] > rgb[2], ("CAR-11 média de pele: R > G > B", rgb)
    rosto_m = mascara(forma, reais[list(OVAL)])
    nucleo = np.ones((3, 3), np.uint8)
    sobrancelhas = np.zeros(forma, bool)
    for s in SOBRANCELHAS:  # interior da sobrancelha, sem a borda que a testa usa como limite de baixo
        sobrancelhas |= cv2.erode(mascara(forma, reais[list(s)]).astype(np.uint8), nucleo) > 0
    olhos_m = mascara(forma, reais[list(OLHOS[0])]) | mascara(forma, reais[list(OLHOS[1])])
    testa = mascara(forma, rois["testa"])
    assert (testa & sobrancelhas).sum() <= 0.01 * testa.sum(), \
        ("CAR-11 testa pega sobrancelha", (testa & sobrancelhas).sum())
    assert (testa & rosto_m).sum() >= 0.98 * testa.sum(), "CAR-11 testa fora do rosto"
    topo_sobrancelhas = min(reais[i][1] for s in SOBRANCELHAS for i in s[:5])
    ys, _ = np.nonzero(testa)
    assert ys.mean() < topo_sobrancelhas + 1.0 and ys.mean() < reais[[33, 263], 1].min(), "CAR-11 testa acima"
    for nome in ("bochecha_esq", "bochecha_dir"):
        b = mascara(forma, rois[nome])
        assert (b & rosto_m).sum() >= 0.98 * b.sum() and not (b & olhos_m).any(), ("CAR-11", nome)
        assert not (b & mascara(forma, reais[list(LABIOS)])).any(), ("CAR-11 bochecha pega boca", nome)
    # "esq"/"dir" = lado da IMAGEM sem espelho: a "bochecha_esq" (117...) fica do lado do ponto 33 (olho direito do
    # motorista no vision/face.py), à esquerda do nariz na foto.
    assert np.mean([p[0] for p in rois["bochecha_esq"]]) < reais[1][0] < np.mean([p[0] for p in rois["bochecha_dir"]])
    assert reais[33][0] < reais[1][0] < reais[263][0]
    ok(f"CAR-11 foto real: média das ROIs R {rgb[0]:.0f} G {rgb[1]:.0f} B {rgb[2]:.0f} em {pixels} px; testa sem "
       "sobrancelha, acima dos olhos e dentro do oval; bochechas dentro do rosto, fora dos olhos e da boca")


# Regras das ROIs pedidas na pesquisa rPPG de 19/10/2026 (sem ID na spec 022): pixel saturado fora da média, bochecha
# do lado virado fora, combinação das ROIs seguindo a que tem pulso.
pele = np.empty((48, 64, 3), np.uint8)
pele[:] = PELE_BGR.astype(np.uint8)
pele[:, :32] = 255  # metade da imagem estourada (reflexo)
media, rois, pixels = media_das_rois(pele, rosto())
so_pele = np.full((48, 64, 3), PELE_BGR, np.uint8)
inteira = media_das_rois(so_pele, rosto())
assert np.allclose(media, PELE_BGR[::-1]) and pixels < 0.6 * inteira[2], ("pixels >= 250 ficam fora", media, pixels)
virado = rosto()
centro = virado[list(ROI_BOCHECHA_DIR)].mean(axis=0)
virado[list(ROI_BOCHECHA_DIR)] = centro + 0.6 * (virado[list(ROI_BOCHECHA_DIR)] - centro)  # 36% da área da outra
assert set(media_das_rois(so_pele, virado)[1]) == {"testa", "bochecha_esq"}, "bochecha do lado virado sai"
assert set(CardioMonitor().update(so_pele, virado, 0.0).rois) == {"testa", "bochecha_esq"}


def so_na_regiao(linhas, semente):
    """Pulso só nas linhas dadas da imagem (o resto da pele só com ruído)."""
    sem_pulso = serie(None, semente=semente + 100)
    for (t, com), (_, sem) in zip(serie(72, semente=semente), sem_pulso):
        mistura = sem.copy()
        mistura[linhas] = com[linhas]
        yield t, mistura


testa_so = medir(so_na_regiao(slice(0, 20), 21))[1][-1]
bochechas_so = medir(so_na_regiao(slice(20, 48), 22))[1][-1]
assert testa_so.estado == "pronto" and abs(testa_so.bpm - 72.0) <= 3.0, \
    ("só a testa pulsa", testa_so.estado, testa_so.bpm)
assert bochechas_so.estado == "pronto" and abs(bochechas_so.bpm - 72.0) <= 3.0, ("só as bochechas", bochechas_so.bpm)
ok(f"ROIs: metade dos pixels estourada fica fora da média; bochecha com 36% da área da outra (rosto virado) sai; "
   f"só a testa pulsando dá {testa_so.bpm:.1f} bpm e só as bochechas, {bochechas_so.bpm:.1f} bpm (combinação por SNR)")


# CAR-12 · nenhuma chave de cardio em evento (_decorate), em nenhum modo; cardio fora do risco.
assert CARDIO_KEYS <= PRIVATE_KEYS
com_cardio = {"bpm": 72.0, "cardio": {"bpm": 72}, "frequencia_cardiaca": 72.0, "snr_db": 6.0, "respiracao_rpm": 15.0,
              "rmssd_ms": 30.0, "onda": [0.1], "historico_bpm": [72.0], "ultimo_bpm": 70.0, "perclos_60s": 0.01}
for modo in ("local", "enviar", "desligado"):
    engine = DriverStateEngine(DrowsinessMonitor(), activation_mode=modo, cardio=CardioMonitor(),
                               background_baseline=False)
    decorado = engine._decorate(com_cardio, RiskAssessment(), None)
    assert not CARDIO_KEYS & set(decorado) and decorado["perclos_60s"] == 0.01, ("CAR-12", modo, decorado)


@dataclass
class Quadro(Sample):
    landmarks: object = None
    infrared: bool = False


perfil = DriverProfile(ear_open=0.20, ear_closed=0.05, score_open=0.05, score_closed=0.9, pitch_baseline=0.0,
                       yaw_baseline=0.0)


def rodar(cardio):
    engine = DriverStateEngine(DrowsinessMonitor(profile=perfil), activation_mode="enviar", cardio=cardio,
                               background_baseline=False)
    estados = []
    for t, imagem in serie(72, segundos=18.0, semente=13):
        fechado = 16.0 <= t < 17.5  # microssono: gera evento com detalhes
        quadro = Quadro(timestamp=t, face_found=True, ear=0.05 if fechado else 0.20,
                        blink_score=0.9 if fechado else 0.05,
                        jaw_open=0.02, pitch=0.0, yaw=0.0, eye_distance_px=36.0, landmarks=rosto())
        estados.append(engine.update(quadro, imagem))
    return estados


com, sem = rodar(CardioMonitor()), rodar(None)
eventos = [e for s in com for e in s.events]
assert any(e.alert_type == "microssono" for e in eventos), [e.alert_type for e in eventos]
assert all(not CARDIO_KEYS & set(e.details) for e in eventos), "CAR-12 chave de cardio em evento"
assert isinstance(com[-1].cardio, CardioReading) and com[-1].cardio.estado == "pronto", "CAR-12 estado do cardio"
assert all(s.cardio is None for s in sem)
assert [(s.risk.level, s.risk.alarm) for s in com] == [(s.risk.level, s.risk.alarm) for s in sem], \
    "CAR-12 cardio no risco"
assert DriverStateEngine(DrowsinessMonitor(), cardio=CardioMonitor()).update(
    Quadro(timestamp=0.0, face_found=True, landmarks=rosto())).cardio is None, "sem quadro, sem cardio"
ok(f"CAR-12 nenhuma chave de cardio nos eventos (nem no modo enviar); risco igual com e sem cardio; "
   f"DriverState.cardio = {com[-1].cardio.bpm:.1f} bpm")


# CAR-13 · FaceMetrics.landmarks com 478 pontos quando há rosto (MediaPipe real; YuNet e "sem rosto" deixam None).
from vision.face import FaceMetrics  # noqa: E402

assert FaceMetrics(timestamp=0.0, face_found=False).landmarks is None
if foto is None:
    pulado(f"CAR-13 {motivo}")
else:
    try:
        from vision.face import FaceAnalyzer

        analisador = FaceAnalyzer(classifier=None)
    except RuntimeError as exc:
        analisador = None
        pulado(f"CAR-13 FaceAnalyzer não carregou ({exc})")
    if analisador is not None:
        medidas = analisador.analyze(foto, 0.0)
        vazio = analisador.analyze(np.zeros_like(foto), 0.1)
        analisador.close()
        if not medidas.face_found:
            pulado("CAR-13 o MediaPipe não achou rosto na foto de exemplo")
        else:
            pontos = medidas.landmarks
            assert isinstance(pontos, np.ndarray) and pontos.shape == (478, 2) and pontos.dtype == np.float32, "CAR-13"
            assert np.allclose(pontos[[33, 160, 158, 133, 153, 144]], medidas.eye_points[:6]), "CAR-13 mesmos pixels"
            assert 0 <= pontos[:, 0].min() and pontos[:, 0].max() < foto.shape[1], "CAR-13 em pixels"
            assert not vazio.face_found and vazio.landmarks is None, "CAR-13 sem rosto"
            ok("CAR-13 FaceMetrics.landmarks: 478×2 float32 em pixels, os mesmos dos olhos; None sem rosto")


# CAR-14 · custo médio do update < 3 ms por quadro 640×480 (20 s a 30 quadros/s, rosto de ~220 px).
caixa = (210, 110, 220, 260)
base = rosto(caixa)
ruido = np.random.default_rng(14)
quadros = []
for k in range(8):
    imagem = np.empty((480, 640, 3), np.uint8)
    imagem[:] = (ruido.normal(0, 25, (480, 640, 1)) + 90).clip(0, 255).astype(np.uint8)
    pele_rosto = PELE_BGR + ruido.normal(0, 2, (caixa[3], caixa[2], 3))
    imagem[caixa[1]:caixa[1] + caixa[3], caixa[0]:caixa[0] + caixa[2]] = pele_rosto.clip(0, 255).astype(np.uint8)
    quadros.append(imagem)
monitor = CardioMonitor()
custos = []
for i in range(600):
    pontos = base + ruido.uniform(-0.3, 0.3, base.shape).astype(np.float32)
    inicio = time.perf_counter()
    monitor.update(quadros[i % 8], pontos, i / 30.0)
    custos.append((time.perf_counter() - inicio) * 1000.0)
media, p95, pior = float(np.mean(custos)), float(np.percentile(custos, 95)), float(np.max(custos))
assert media < 3.0, ("CAR-14", media)
ok(f"CAR-14 custo do update em 640×480: média {media:.2f} ms, p95 {p95:.2f} ms, pior {pior:.2f} ms (passo de 1 s)")


# Variabilidade (RMSSD) experimental: só com >= 25 quadros/s e SNR >= 10 dB (o piso da medida cai para ~25 ms).
limpa = dict(segundos=20.0, amp=0.005, ruido_quadro=0.02, ruido_px=1.0, semente=15)
final = medir(serie(72, **limpa))[1][-1]
assert final.snr_db >= 10.0 and final.rmssd_ms is not None and 0.0 <= final.rmssd_ms < 40.0, \
    ("RMSSD com pulso regular fica no piso", final.rmssd_ms, final.snr_db)
comum = medir(serie(72, segundos=20.0, semente=15))[1][-1]
assert comum.estado == "pronto" and comum.snr_db < 10.0 and comum.rmssd_ms is None, \
    ("RMSSD com SNR comum", comum.snr_db)
lento = medir(serie(72, fps=20.0, **limpa))[1][-1]
assert lento.estado == "pronto" and lento.rmssd_ms is None, ("RMSSD a 20 quadros/s", lento.estado, lento.rmssd_ms)
devagar = medir(serie(72, segundos=20.0, fps=12.0, semente=15))[1][-1]
assert devagar.estado == "sinal_fraco" and devagar.bpm is None, \
    ("menos de 15 quadros/s não mostra número", devagar.estado)
monitor.reset()
assert monitor.amostras == 0
ok(f"RMSSD experimental: {final.rmssd_ms:.0f} ms num pulso regular com SNR {final.snr_db:.1f} dB (piso); nenhuma com "
   f"SNR {comum.snr_db:.1f} dB nem a 20 quadros/s; a 12 quadros/s não mostra bpm (mínimo 15); reset zera")

if pulados:
    print(f"\n{len(pulados)} critério(s) PULADO(S): " + "; ".join(pulados))
print(f"\nTODOS OS {checks} TESTES PASSARAM (Python {sys.version.split()[0]})")
