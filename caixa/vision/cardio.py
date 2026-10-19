"""Frequência cardíaca estimada pela face (rPPG), com respiração e variabilidade experimentais. Spec 022.

A cada batimento a pele muda de cor de forma mínima. Este módulo mede a cor média da testa e das bochechas (polígonos
de pontos do Face Landmarker), extrai o pulso e acha a frequência no espectro. É uma ESTIMATIVA pela câmera, não é
medida médica, e fica fora do nível de risco até ser validada com gravações e oxímetro (spec 022, decisão 4).
Privacidade: nada daqui vai para evento, fila, servidor ou registro (LGPD art. 11; vision/engine.py, CARDIO_KEYS).

Referências (implementação própria em numpy, sem código de pyVHR (GPL) nem do rPPG-Toolbox (licença RAIL)):
- POS: Wang, den Brinker, Stuijk & de Haan, "Algorithmic Principles of Remote PPG", IEEE TBME 64(7), 2017,
  Algoritmo 1: janela de 1,6 s, projeção [[0, 1, -1], [-2, 1, 1]], h = S1 + (sigma(S1)/sigma(S2))·S2, soma com
  sobreposição deslizando 1 quadro. Aqui calculado em O(N) com somas acumuladas (mesmo resultado do laço do artigo,
  conferido em tests/test_cardio.py). Assinatura do pulso em R, G, B = 0,33 / 0,77 / 0,53 (nota 6).
- SNR: de Haan & Jeanne, "Robust Pulse Rate From Chrominance-Based rPPG", IEEE TBME 60(10), 2013: energia em volta da
  fundamental e do 2º harmônico contra o resto da banda. Meia largura de 0,2 Hz em vez de 0,1 Hz porque, com Hann em
  10 s, o lóbulo principal ocupa ±2/T = ±0,2 Hz (senoide limpa: 9,3 dB com ±0,1 Hz e 29,1 dB com ±0,2 Hz, medido na
  pesquisa da demo web de 19/10/2026); mesma regra da versão TypeScript do painel.
- Remoção de tendência: Tarvainen, Ranta-Aho & Karjalainen, IEEE TBME 49(2), 2002: z - (I + lambda² D2'D2)^-1 z.
  Com lambda = 300 a 30 Hz o corte (-3 dB) fica em ~0,34 Hz; com 100 ficaria em 0,60 Hz e comeria pulso de 42-50 bpm
  (pesquisa rPPG de 19/10/2026). O sistema é resolvido por Cholesky em banda (O(N)); o fator fica guardado por
  tamanho. A inversa densa 300×300 custou 416 ms nesta máquina e travaria o loop a cada tamanho novo.
- Infravermelho: Nowara et al., SparsePPG, CVPRW 2018 (pulso em 940 nm ~10x mais fraco; um canal só). Também de lá:
  redetectar os pontos a cada quadro piora o sinal, por isso os vértices das ROIs são suavizados.
- ROIs e combinação por SNR: Kim, Lee & Sohn, Sensors 2021 (malar, glabela e testa medial são as melhores regiões).

Passa-faixa sem scipy: o pico só é procurado em 0,7-3,0 Hz (equivale a um passa-faixa ideal para a estimativa); para a
onda desenhada e para a variabilidade, a banda é aplicada zerando a FFT fora de 0,7-3,0 Hz (filtro ideal, sem fase).
"""
from __future__ import annotations

import functools
import math
from collections import deque
from dataclasses import dataclass, field

import cv2
import numpy as np

# --- Parâmetros do sinal (iguais aos da versão TypeScript do painel, spec 025) ----------------------------------
FS = 30.0  # Hz: taxa da grade uniforme depois da reamostragem pelo horário de cada quadro
BANDA_HZ = (0.7, 3.0)  # 42 a 180 bpm (spec 022)
POS_JANELA_S = 1.6  # Wang et al. 2017
JANELA_S = 10.0  # janela do espectro
MINIMO_S = 6.0  # dados mínimos para a primeira estimativa
PASSO_S = 1.0  # uma estimativa por segundo
NFFT_MIN = 2048  # zero-padding do espectro (Hann, segmento único)
MEIA_BANDA_SNR_HZ = 0.2  # em volta do pico e do 2º harmônico (ver docstring)
BANDA_SNR_HZ = (BANDA_HZ[0], 2 * BANDA_HZ[1] + MEIA_BANDA_SNR_HZ)  # inclui o 2º harmônico de 180 bpm
LAMBDA_TENDENCIA = 300.0  # Tarvainen, a 30 Hz (corte ~0,34 Hz)
# Abaixo deste SNR a janela não vale ("sinal fraco"). Mesmo valor da versão TypeScript. Medido no sintético (3 ROIs com
# ruído branco, combinação por SNR, 19/10/2026): só ruído deu no máximo -1,8 dB em 3.000 janelas (p99 -3,5 dB); pulso
# de 0,3% no verde com ruído de 0,14% por quadro ficou com p5 de +1,4 dB; de 0,2%, mediana de -0,3 dB (erro p95 de
# 0,8 bpm: parte boa fica de fora). Hipótese: confirmar com gravações reais e oxímetro (mirar <= 5% de número em trecho
# sem pulso; luz que pisca e movimento não são ruído branco e devem subir o SNR do "nada").
LIMIAR_SNR_DB = 0.0
FAIXA_CONFIANCA_DB = 10.0  # SNR acima do limiar que leva a parte do SNR na confiança a 1

# --- Regras para mostrar número (pesquisa rPPG de 19/10/2026, §3.5 e §3.7) -------------------------------------------
AQUECIMENTO_S = 15.0  # dados bons antes do primeiro número (~3 janelas seguidas); o progresso vai de 0 a 1 aqui
FPS_MINIMO = 15.0  # abaixo disso o erro piora muito (10 fps: erro médio 5,4 bpm e máximo 36 no sintético)
MEDIANA_N = 5  # mediana das últimas 5 estimativas
CONSISTENTES_N = 3  # pelo menos 3 das últimas 5 estimativas boas e perto da mediana...
RECENTES_N = 2  # ...e pelo menos 1 das 2 últimas boa (uma janela ruim isolada não apaga o número; duas apagam)
CONSISTENCIA_BPM = 6.0  # = resolução nativa de uma janela de 10 s (Nowara 2018, §4.1.1)
METADE_RAZAO = 0.5  # pico em f/2 com >= 50% da potência do principal: fica f/2 (evita pegar o 2º harmônico)
METADE_PROCURA_HZ = 0.1

# --- Regiões da pele (ROIs) ---------------------------------------------------------------------------------------
# Índices do Face Landmarker (478 pontos), em ordem de contorno, conferidos no canonical_face_model.obj do MediaPipe
# (pesquisas de 19/10/2026) e numa foto real (tests/test_cardio.py, CAR-11). Os mesmos da versão TypeScript.
# Testa: testa medial baixa e glabela alta; a borda de baixo segue o topo das sobrancelhas (66-107 e 336-296) e a de
# cima fica abaixo da linha do cabelo (10, 109 e 338 ficam de fora).
ROI_TESTA = (69, 108, 151, 337, 299, 296, 336, 9, 107, 66)
# Bochechas (malar): uma fileira abaixo da pálpebra de baixo, acima do sulco da boca e longe da asa do nariz.
# "esq" e "dir" = lado da IMAGEM sem espelho: a "esq" (117...) é a bochecha DIREITA do motorista, do lado do ponto 33
# (olho direito no vision/face.py).
ROI_BOCHECHA_ESQ = (117, 118, 101, 36, 205, 187, 123)
ROI_BOCHECHA_DIR = (346, 347, 330, 266, 425, 411, 352)
ROIS = {"testa": ROI_TESTA, "bochecha_esq": ROI_BOCHECHA_ESQ, "bochecha_dir": ROI_BOCHECHA_DIR}
CANTOS_OLHOS = (33, 263)  # cantos externos: escala do rosto
PONTE_NARIZ = (6, 168)  # pontos estáveis para o movimento da respiração
# Pixel com algum canal <= 15 (escuro: o pulso de ~0,3% some no degrau de 1 nível) ou >= 250 (reflexo; o
# vision/face.py usa 250 como reflexo) sai da média (pesquisa rPPG §2.2).
PIXEL_ESCURO = 15
PIXEL_SATURADO = 250
PIXELS_MIN_ROI = 100  # ROI com menos pixels úteis é descartada. Hipótese: rosto pequeno na imagem; a calibrar.
RAZAO_BOCHECHAS_MIN = 0.5  # bochecha com menos da metade da área da outra = rosto virado (~25° de yaw): sai
SUAVIZACAO_PONTOS_S = 0.1  # constante de tempo da média exponencial dos vértices das ROIs
MONO_TOLERANCIA = 1.0  # canais com médias a até 1 nível um do outro = quadro sem cor (infravermelho)

# --- Movimento e falta de rosto -----------------------------------------------------------------------------------
# Deslocamento médio dos pontos em 0,5 s, em distâncias entre os cantos externos dos olhos. 0,10 ≈ 9 mm em 0,5 s.
# Hipótese a calibrar com gravações: o tremor do MediaPipe fica perto de 0,01 e olhar o retrovisor passa de 0,3.
LIMIAR_MOVIMENTO = 0.10
JANELA_MOVIMENTO_S = 0.5
SEGURA_MOVIMENTO_S = 0.5  # depois que para de mexer, espera mais 0,5 s antes de voltar a medir
SEM_ROSTO_S = 2.0  # sem rosto por mais que isso: "sem_rosto" e janelas zeradas (CAR-10)
BURACO_MAX_S = 0.5  # buraco maior entre quadros: não interpola por cima; emenda os trechos (POS por trecho)
IDADE_MAX_S = 2 * JANELA_S  # amostra de pulso mais velha que isso não entra, mesmo com pouca coisa boa depois

# --- Saída ----------------------------------------------------------------------------------------------------------
ONDA_S = 6.0
ONDA_PASSO_S = 0.1  # a onda é refeita 10 vezes por segundo (a tela não precisa de mais; cada vez custa um POS de 8 s)
HISTORICO_N = 120

# --- Respiração (experimental) ------------------------------------------------------------------------------------
RESP_BANDA_HZ = (0.1, 0.5)  # 6 a 30 rpm
RESP_JANELA_S = 30.0
RESP_MINIMO_S = 20.0
RESP_FS = 10.0
# Medido no sintético (ruído branco, 30 s, 500 janelas): só ruído deu p99 de 9,9 dB e máximo de 11,5 dB; respiração de
# 0,2% na intensidade deu mediana de 14,5 dB, e de 0,5%, mínimo de 16 dB. Hipótese: no carro a vibração e a direção
# mexem a cabeça nessa mesma faixa (pesquisa rPPG §5.2); por isso fica "experimental".
LIMIAR_SNR_RESP_DB = 12.0

# --- Variabilidade (RMSSD), experimental --------------------------------------------------------------------------
# Piso medido no sintético (pulso perfeitamente regular, RMSSD verdadeira 0): com a banda inteira 0,7-3 Hz, 60 a 155 ms
# (inútil); com f0 ± 0,5 Hz, 24 ms com SNR de 12 dB, 39 ms com 7 dB e 64 ms com 4 dB. Com variação respiratória real
# de 33 ms, saiu 40 ms (12 dB) e 54 ms (7 dB). Por isso: banda f0 ± 0,5 Hz (guarda as modulações de até 0,5 Hz, que
# cobrem a faixa HF de 0,15-0,4 Hz) e só com SNR >= 10 dB. Mesmo assim fica "experimental" (PURE: r = 0,53, pesquisa
# rPPG §5.1) e nunca vai para relatório.
RMSSD_FPS_MIN = 25.0
RMSSD_SNR_MIN_DB = 10.0
RMSSD_MEIA_BANDA_HZ = 0.5
RMSSD_MIN_DIFERENCAS = 8

_NOMES = tuple(ROIS)
_INDICES_ROI = sorted(set(ROI_TESTA + ROI_BOCHECHA_ESQ + ROI_BOCHECHA_DIR))
_INDICES_MOVIMENTO = sorted(set(_INDICES_ROI) | set(CANTOS_OLHOS + PONTE_NARIZ + (1,)))
_COL_INTENSIDADE, _COL_NARIZ = 3 * len(ROIS), 3 * len(ROIS) + 1  # colunas do buffer depois das R, G, B por ROI


@dataclass
class CardioReading:
    estado: str  # "sem_rosto" | "medindo" | "pronto" | "sinal_fraco" | "movimento"
    bpm: float | None = None
    confianca: float = 0.0  # 0..1
    snr_db: float | None = None
    respiracao_rpm: float | None = None
    rmssd_ms: float | None = None  # experimental
    progresso: float = 0.0  # 0..1 até a primeira leitura (aquecimento)
    onda: list[float] = field(default_factory=list)  # últimos ~6 s normalizados -1..1, ~30 Hz; sobe na sístole
    historico_bpm: list[float] = field(default_factory=list)  # últimos 120 valores "pronto"
    canal: str = "rgb"  # "rgb" | "ir"
    rois: dict[str, list[tuple[int, int]]] = field(default_factory=dict)  # "testa", "bochecha_esq", "bochecha_dir"
    ultimo_bpm: float | None = None  # último bpm bom, para mostrar esmaecido em movimento/sinal fraco


# ===================================================================================================================
# Funções puras
# ===================================================================================================================

def reamostrar(ts, valores, fs: float):
    """Interpolação linear numa grade uniforme de `fs` Hz, de ts[0] até no máximo ts[-1] (a câmera oscila).
    valores: (N,) ou (N, C). Devolve (grade, valores_na_grade)."""
    ts = np.asarray(ts, dtype=float)
    valores = np.asarray(valores, dtype=float)
    if len(ts) < 2:
        return ts.copy(), valores.copy()
    n = int(math.floor((ts[-1] - ts[0]) * fs + 1e-9)) + 1
    grade = ts[0] + np.arange(n) / fs
    if valores.ndim == 1:
        return grade, np.interp(grade, ts, valores)
    return grade, np.column_stack([np.interp(grade, ts, valores[:, c]) for c in range(valores.shape[1])])


def _soma_movel(x: np.ndarray, comprimento: int) -> np.ndarray:
    acumulado = np.concatenate(([0.0], np.cumsum(x)))
    return acumulado[comprimento:] - acumulado[:-comprimento]


def _somar_janelas(coeficientes: np.ndarray, n: int, comprimento: int) -> np.ndarray:
    """Para cada amostra i, soma os coeficientes das janelas que a cobrem (k de i-l+1 a i): o overlap-add."""
    acumulado = np.concatenate(([0.0], np.cumsum(coeficientes)))
    i = np.arange(n)
    return acumulado[np.minimum(i, len(coeficientes) - 1) + 1] - acumulado[np.maximum(0, i - comprimento + 1)]


def pos(rgb, fs: float, janela_s: float = POS_JANELA_S) -> np.ndarray:
    """POS (Wang et al. 2017, Algoritmo 1). rgb: (N, 3) na ordem R, G, B, amostrado uniformemente a `fs`.
    Devolve o sinal H do artigo (acompanha o pulso com o sinal trocado: a pele escurece quando o sangue chega).

    Mesma conta do laço do artigo, em O(N): na janela k, Cn = C/média_k; S1 = Gn - Bn e S2 = -2Rn + Gn + Bn têm média
    zero, então sigma² = média dos quadrados (somas móveis de R², G², B², RG, RB, GB), e o overlap-add de
    h = S1 + alfa·S2 vira G·soma((1+alfa)/mG) + B·soma((alfa-1)/mB) + R·soma(-2·alfa/mR) nas janelas que cobrem cada
    amostra."""
    rgb = np.asarray(rgb, dtype=float)
    n = len(rgb)
    comprimento = int(math.ceil(janela_s * fs))
    if comprimento < 2 or n < comprimento:
        return np.zeros(n)
    escala = rgb.mean(axis=0)
    if np.any(escala <= 0):
        return np.zeros(n)
    c = rgb / escala  # a escala global some na normalização por janela; só melhora a precisão das somas
    r, g, b = c[:, 0], c[:, 1], c[:, 2]
    mr, mg, mb = (_soma_movel(x, comprimento) / comprimento for x in (r, g, b))
    validas = (mr > 0) & (mg > 0) & (mb > 0)
    mr, mg, mb = (np.where(validas, m, 1.0) for m in (mr, mg, mb))
    rr, gg, bb = (_soma_movel(x * x, comprimento) / comprimento / (m * m) for x, m in ((r, mr), (g, mg), (b, mb)))
    rg = _soma_movel(r * g, comprimento) / comprimento / (mr * mg)
    rb = _soma_movel(r * b, comprimento) / comprimento / (mr * mb)
    gb = _soma_movel(g * b, comprimento) / comprimento / (mg * mb)
    var1 = np.maximum(gg - 2.0 * gb + bb, 0.0)
    var2 = np.maximum(4.0 * rr + gg + bb - 4.0 * rg - 4.0 * rb + 2.0 * gb, 0.0)
    alfa = np.sqrt(np.divide(var1, var2, out=np.zeros_like(var1), where=var2 > 1e-300))
    alfa = np.where(validas, alfa, 0.0)
    ativa = validas.astype(float)
    return (g * _somar_janelas(ativa * (1.0 + alfa) / mg, n, comprimento)
            + b * _somar_janelas(ativa * (alfa - 1.0) / mb, n, comprimento)
            + r * _somar_janelas(ativa * -2.0 * alfa / mr, n, comprimento))


def canal_unico(x, fs: float, janela_s: float = POS_JANELA_S) -> np.ndarray:
    """Um canal só (infravermelho ou quadro sem cor): x/média - 1 em janelas de 1,6 s somadas com sobreposição, a
    mesma normalização temporal do POS. Mesmo sinal do POS (desce quando o sangue chega)."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    comprimento = int(math.ceil(janela_s * fs))
    if comprimento < 2 or n < comprimento or x.mean() <= 0:
        return np.zeros(n)
    x = x / x.mean()
    medias = _soma_movel(x, comprimento) / comprimento
    validas = (medias > 0).astype(float)
    inversos = validas / np.where(medias > 0, medias, 1.0)
    return x * _somar_janelas(inversos, n, comprimento) - _somar_janelas(validas, n, comprimento)


@functools.lru_cache(maxsize=64)
def _fator_tendencia(n: int, lam2: float):
    """Cholesky em banda (L com diagonal e duas subdiagonais) de A = I + lam²·D2'D2."""
    diagonal, sub1, sub2 = [1.0] * n, [0.0] * n, [0.0] * n  # A[i, i], A[i, i-1], A[i, i-2]
    for i in range(n - 2):  # cada linha (1, -2, 1) de D2 nas colunas i, i+1, i+2
        diagonal[i] += lam2
        diagonal[i + 1] += 4.0 * lam2
        diagonal[i + 2] += lam2
        sub1[i + 1] -= 2.0 * lam2
        sub1[i + 2] -= 2.0 * lam2
        sub2[i + 2] += lam2
    l0, l1, l2 = [0.0] * n, [0.0] * n, [0.0] * n
    for i in range(n):
        a2 = sub2[i] / l0[i - 2] if i >= 2 else 0.0
        a1 = (sub1[i] - a2 * l1[i - 1]) / l0[i - 1] if i >= 1 else 0.0
        l0[i], l1[i], l2[i] = math.sqrt(diagonal[i] - a1 * a1 - a2 * a2), a1, a2
    return tuple(l0), tuple(l1), tuple(l2)


def remover_tendencia(x, fs: float = FS, lam: float = LAMBDA_TENDENCIA) -> np.ndarray:
    """Tarvainen et al. 2002: x - (I + lambda²·D2'D2)^-1·x. lambda vale para 30 Hz; em outra taxa é escalado por
    (fs/30)² para manter o corte."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n < 4:
        return x - x.mean() if n else x
    lam_fs = lam * (fs / FS) ** 2
    l0, l1, l2 = _fator_tendencia(n, round(lam_fs * lam_fs, 6))
    z = x.tolist()
    y = [0.0] * n
    for i in range(n):
        s = z[i]
        if i >= 1:
            s -= l1[i] * y[i - 1]
            if i >= 2:
                s -= l2[i] * y[i - 2]
        y[i] = s / l0[i]
    tendencia = [0.0] * n
    for i in range(n - 1, -1, -1):
        s = y[i]
        if i + 1 < n:
            s -= l1[i + 1] * tendencia[i + 1]
            if i + 2 < n:
                s -= l2[i + 2] * tendencia[i + 2]
        tendencia[i] = s / l0[i]
    return x - np.asarray(tendencia)


def _sem_reta(x: np.ndarray) -> np.ndarray:
    eixo = np.arange(len(x)) - (len(x) - 1) / 2.0
    return x - x.mean() - (eixo @ x) / (eixo @ eixo) * eixo


def passa_faixa(x, fs: float, banda=BANDA_HZ) -> np.ndarray:
    """Passa-faixa ideal por FFT (zera fora da banda). Tira antes a reta, para a borda circular não vazar."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n < 4:
        return np.zeros(n)
    espectro_ = np.fft.rfft(_sem_reta(x))
    f = np.fft.rfftfreq(n, 1.0 / fs)
    espectro_[(f < banda[0]) | (f > banda[1])] = 0.0
    return np.fft.irfft(espectro_, n)


def espectro(x, fs: float, nfft_min: int = NFFT_MIN):
    """Periodograma com Hann e zero-padding (o Welch de segmento único da versão TypeScript)."""
    x = np.asarray(x, dtype=float)
    x = x - x.mean()
    nfft = max(nfft_min, 1 << max(1, (len(x) - 1).bit_length()))
    potencia = np.abs(np.fft.rfft(x * np.hanning(len(x)), nfft)) ** 2
    return np.fft.rfftfreq(nfft, 1.0 / fs), potencia


def _parabolico(f, p, i: int) -> float:
    """Pico refinado pela parábola dos 3 pontos; deslocamento limitado a meio bin (denominador quase zero)."""
    if 0 < i < len(p) - 1:
        a, b, c = p[i - 1], p[i], p[i + 1]
        denominador = a - 2.0 * b + c
        if denominador < 0:
            desvio = min(0.5, max(-0.5, 0.5 * (a - c) / denominador))
            return float(f[i] + desvio * (f[1] - f[0]))
    return float(f[i])


def _snr_db(f, p, f0: float, meia: float, faixa) -> float:
    dentro = (f >= faixa[0]) & (f <= faixa[1])
    alvo = (np.abs(f - f0) <= meia) | (np.abs(f - 2.0 * f0) <= meia)
    sinal = float(p[dentro & alvo].sum())
    ruido = float(p[dentro & ~alvo].sum())
    if sinal <= 0.0:
        return -60.0
    if ruido <= 0.0:
        return 60.0
    return float(np.clip(10.0 * math.log10(sinal / ruido), -60.0, 60.0))


def pico_e_snr(f, p, banda=BANDA_HZ):
    """(frequência do pulso em Hz, SNR em dB) a partir do espectro, ou (None, None) se não houver energia na banda.
    Pico na banda com interpolação parabólica; se houver pico em f/2 com >= 50% da potência, fica f/2."""
    indices = np.flatnonzero((f >= banda[0]) & (f <= banda[1]))
    if len(indices) == 0:
        return None, None
    i = int(indices[np.argmax(p[indices])])
    if p[i] <= 0.0:
        return None, None
    metade = f[i] / 2.0
    if metade >= banda[0]:
        perto = indices[np.abs(f[indices] - metade) <= METADE_PROCURA_HZ]
        if len(perto):
            j = int(perto[np.argmax(p[perto])])
            if p[j] >= METADE_RAZAO * p[i] and 0 < j < len(p) - 1 and p[j] >= p[j - 1] and p[j] >= p[j + 1]:
                i = j
    f0 = _parabolico(f, p, i)
    return f0, _snr_db(f, p, f0, MEIA_BANDA_SNR_HZ, BANDA_SNR_HZ)


def estimar_bpm(sinal, fs: float):
    """(bpm, snr_db) de um sinal de pulso uniforme: tira a tendência, espectro com Hann, pico em 42-180 bpm."""
    f, p = espectro(remover_tendencia(sinal, fs), fs)
    f0, snr = pico_e_snr(f, p)
    return (None, None) if f0 is None else (60.0 * f0, snr)


# ===================================================================================================================
# Média das ROIs
# ===================================================================================================================

def _pontos(landmarks) -> np.ndarray | None:
    if landmarks is None:
        return None
    pontos = np.asarray(landmarks, dtype=np.float32)
    if pontos.ndim != 2 or pontos.shape[0] < 478 or pontos.shape[1] < 2:
        return None
    return pontos[:, :2]


def _media_roi(quadro: np.ndarray, poligono: np.ndarray):
    """(R, G, B) médios dentro do polígono, sem pixels escuros nem saturados, e o número de pixels usados."""
    altura, largura = quadro.shape[:2]
    x0 = max(int(poligono[:, 0].min()), 0)
    y0 = max(int(poligono[:, 1].min()), 0)
    x1 = min(int(poligono[:, 0].max()) + 1, largura)
    y1 = min(int(poligono[:, 1].max()) + 1, altura)
    if x1 - x0 < 2 or y1 - y0 < 2:
        return None, 0
    recorte = quadro[y0:y1, x0:x1]
    mascara = np.zeros((y1 - y0, x1 - x0), np.uint8)
    cv2.fillPoly(mascara, [poligono - np.array([x0, y0], np.int32)], 255)
    mascara = cv2.bitwise_and(mascara, cv2.inRange(recorte, (PIXEL_ESCURO + 1,) * 3, (PIXEL_SATURADO - 1,) * 3))
    pixels = cv2.countNonZero(mascara)
    if pixels < PIXELS_MIN_ROI:
        return None, pixels
    b, g, r = cv2.mean(recorte, mask=mascara)[:3]
    return (r, g, b), pixels


def _medias_rois(quadro: np.ndarray, pontos: np.ndarray):
    """Médias R, G, B por ROI (ou None), pixels usados e polígonos usados. Bochecha com menos da metade da área da
    outra (rosto virado) sai."""
    if quadro.ndim == 2:
        quadro = cv2.cvtColor(quadro, cv2.COLOR_GRAY2BGR)
    poligonos = {nome: np.rint(pontos[list(indices)]).astype(np.int32) for nome, indices in ROIS.items()}
    areas = {nome: abs(cv2.contourArea(poligonos[nome])) for nome in ("bochecha_esq", "bochecha_dir")}
    maior = max(areas.values())
    medias, pixels = {}, {}
    for nome, poligono in poligonos.items():
        if nome in areas and (maior <= 0 or areas[nome] < RAZAO_BOCHECHAS_MIN * maior):
            medias[nome], pixels[nome] = None, 0
            continue
        medias[nome], pixels[nome] = _media_roi(quadro, poligono)
    usados = {nome: [(int(x), int(y)) for x, y in poligonos[nome]] for nome in ROIS if medias[nome] is not None}
    return medias, pixels, usados


def media_das_rois(frame_bgr: np.ndarray, landmarks):
    """Média R, G, B (ponderada pelos pixels) da testa e das bochechas, polígonos usados e total de pixels.
    Devolve (np.array([R, G, B]) ou None, {nome: [(x, y), ...]}, pixels)."""
    pontos = _pontos(landmarks)
    if pontos is None or frame_bgr is None:
        return None, {}, 0
    medias, pixels, usados = _medias_rois(frame_bgr, pontos)
    total = sum(pixels[nome] for nome in usados)
    if total == 0:
        return None, usados, 0
    soma = sum(np.asarray(medias[nome]) * pixels[nome] for nome in usados)
    return soma / total, usados, int(total)


def _monocromatico(medias: dict) -> bool:
    validas = [m for m in medias.values() if m is not None]
    return bool(validas) and all(max(abs(r - g), abs(g - b), abs(r - b)) <= MONO_TOLERANCIA for r, g, b in validas)


# ===================================================================================================================
# Pulso emendado por trechos, variabilidade e respiração
# ===================================================================================================================

def _trechos(ts: np.ndarray, segmentos: np.ndarray):
    """Índices (início, fim) dos trechos contínuos: mesmo segmento e sem buraco maior que BURACO_MAX_S."""
    if len(ts) == 0:
        return []
    corte = np.flatnonzero((np.diff(segmentos) != 0) | (np.diff(ts) > BURACO_MAX_S)) + 1
    limites = np.concatenate(([0], corte, [len(ts)]))
    return list(zip(limites[:-1].tolist(), limites[1:].tolist()))


def _pulso_emendado(ts, valores, segmentos, duracao: float, mono: bool):
    """Pulso dos trechos mais recentes até somar `duracao` segundos, cada trecho com seu POS (ou canal único), na grade
    de FS Hz. Emendar depois do POS evita o degrau de cor entre trechos (pele um pouco diferente depois de mexer).
    Devolve (pulso, duração em s, pulso do trecho mais recente) ou (None, 0.0, None)."""
    partes, total, ultimo = [], 0.0, None
    minimo = int(math.ceil(POS_JANELA_S * FS)) + 1
    for inicio, fim in reversed(_trechos(ts, segmentos)):
        if total >= duracao - 0.5 / FS:
            break
        if fim - inicio < 3:
            continue
        _, uniforme = reamostrar(ts[inicio:fim], valores[inicio:fim], FS)
        if len(uniforme) < minimo:
            continue
        h = canal_unico(uniforme.mean(axis=1), FS) if mono else pos(uniforme, FS)
        if ultimo is None:
            ultimo = h
        manter = min(len(h), int(round((duracao - total) * FS)))
        partes.append(h[len(h) - manter:])
        total += manter / FS
    if not partes:
        return None, 0.0, None
    return np.concatenate(partes[::-1]), total, ultimo


def _rmssd_ms(pulso: np.ndarray, f0: float) -> float | None:
    """Variabilidade experimental: picos da onda filtrada em f0 ± 0,5 Hz (sístole para cima), tempo com interpolação
    parabólica, intervalos dentro de ±30% do período e RMSSD das diferenças entre intervalos vizinhos."""
    if f0 <= 0 or len(pulso) < 3:
        return None
    banda = (max(BANDA_HZ[0], f0 - RMSSD_MEIA_BANDA_HZ), min(BANDA_HZ[1], f0 + RMSSD_MEIA_BANDA_HZ))
    y = -passa_faixa(pulso, FS, banda)
    periodo = 1.0 / f0
    candidatos = np.flatnonzero((y[1:-1] > y[:-2]) & (y[1:-1] >= y[2:]) & (y[1:-1] > 0)) + 1
    distancia = 0.6 * periodo * FS
    escolhidos: list[int] = []
    for i in candidatos[np.argsort(-y[candidatos])]:
        if all(abs(i - j) >= distancia for j in escolhidos):
            escolhidos.append(int(i))
    escolhidos.sort()
    tempos = []
    for i in escolhidos:
        a, b, c = y[i - 1], y[i], y[i + 1]
        denominador = a - 2.0 * b + c
        desvio = min(0.5, max(-0.5, 0.5 * (a - c) / denominador)) if denominador < 0 else 0.0
        tempos.append((i + desvio) / FS)
    intervalos = np.diff(tempos)
    bons = (intervalos >= 0.7 * periodo) & (intervalos <= 1.3 * periodo)
    diferencas = [intervalos[k + 1] - intervalos[k] for k in range(len(intervalos) - 1) if bons[k] and bons[k + 1]]
    if len(diferencas) < RMSSD_MIN_DIFERENCAS:
        return None
    return float(math.sqrt(np.mean(np.square(diferencas))) * 1000.0)


def _respiracao(ts, intensidade, nariz):
    """Experimental: soma dos espectros normalizados (0,1-0,5 Hz) da intensidade lenta da testa e do movimento vertical
    da ponte do nariz, janela de 30 s. Meia largura do pico = 2/T (lóbulo de Hann), como no pulso.
    Devolve (rpm, snr_db) ou (None, None) sem dados."""
    ts = np.asarray(ts, dtype=float)
    if len(ts) < 10 or ts[-1] - ts[0] < RESP_MINIMO_S:
        return None, None
    soma, f = None, None
    for serie in (np.asarray(intensidade, dtype=float), np.asarray(nariz, dtype=float)):
        ok = np.isfinite(serie)
        if ok.sum() < 10:
            continue
        _, u = reamostrar(ts[ok], serie[ok], RESP_FS)
        u = _sem_reta(u)
        if u.std() <= 1e-9 * (abs(serie[ok].mean()) + 1.0):
            continue  # parado de verdade (ex.: pontos fixos): não entra
        f, p = espectro(u, RESP_FS, 4096)
        banda = (f >= RESP_BANDA_HZ[0]) & (f <= RESP_BANDA_HZ[1])
        total = p[banda].sum()
        if total > 0:
            soma = p / total if soma is None else soma + p / total
    if soma is None:
        return None, None
    indices = np.flatnonzero((f >= RESP_BANDA_HZ[0]) & (f <= RESP_BANDA_HZ[1]))
    i = int(indices[np.argmax(soma[indices])])
    f0 = _parabolico(f, soma, i)
    duracao = min(ts[-1] - ts[0], RESP_JANELA_S)
    return 60.0 * f0, _snr_db(f, soma, f0, 2.0 / duracao, RESP_BANDA_HZ)


def _respiracao_rpm(ts, intensidade, nariz) -> float | None:
    rpm, snr = _respiracao(ts, intensidade, nariz)
    return rpm if snr is not None and snr >= LIMIAR_SNR_RESP_DB else None


class _Buffer:
    """Amostras por quadro em arrays numpy (tempo, trecho e colunas), sem converter listas a cada quadro."""

    def __init__(self, colunas: int, capacidade: int = 4096):
        self.t = np.empty(capacidade)
        self.seg = np.empty(capacidade, np.int64)
        self.v = np.empty((capacidade, colunas))
        self.inicio = 0
        self.n = 0

    def acrescentar(self, t: float, segmento: int, valores) -> None:
        fim = self.inicio + self.n
        if fim == len(self.t):
            if self.inicio == 0:  # cheio de verdade (taxa muito alta): dobra
                self.t = np.concatenate((self.t, np.empty_like(self.t)))
                self.seg = np.concatenate((self.seg, np.empty_like(self.seg)))
                self.v = np.concatenate((self.v, np.empty_like(self.v)))
            else:  # traz o que vale para o começo
                for nome in ("t", "seg", "v"):
                    array = getattr(self, nome)
                    array[:self.n] = array[self.inicio:fim]
                self.inicio, fim = 0, self.n
        self.t[fim], self.seg[fim], self.v[fim] = t, segmento, valores
        self.n += 1

    def cortar_antes(self, limite: float) -> None:
        k = int(np.searchsorted(self.t[self.inicio:self.inicio + self.n], limite))
        self.inicio += k
        self.n -= k

    def desde(self, limite: float):
        """Visões (t, seg, v) das amostras com t >= limite."""
        t = self.t[self.inicio:self.inicio + self.n]
        k = int(np.searchsorted(t, limite))
        fim = self.inicio + self.n
        return t[k:], self.seg[self.inicio + k:fim], self.v[self.inicio + k:fim]

    @property
    def ultimo_t(self) -> float | None:
        return float(self.t[self.inicio + self.n - 1]) if self.n else None


# ===================================================================================================================
# Monitor
# ===================================================================================================================

class CardioMonitor:
    """Uma chamada de update por quadro (barata: médias das ROIs e a onda); a estimativa roda uma vez por segundo."""

    def __init__(self, janela_s: float = JANELA_S, minimo_s: float = MINIMO_S, passo_s: float = PASSO_S,
                 aquecimento_s: float = AQUECIMENTO_S):
        if not 0 < minimo_s <= janela_s:
            raise ValueError("minimo_s precisa ficar entre 0 e janela_s")
        self.janela_s = float(janela_s)
        self.minimo_s = float(minimo_s)
        self.passo_s = float(passo_s)
        self.aquecimento_s = max(float(aquecimento_s), self.minimo_s)
        self._historico: deque = deque(maxlen=HISTORICO_N)
        self._canal = "rgb"
        self.reset()

    @property
    def amostras(self) -> int:
        """Quadros guardados nas janelas (0 depois de reset ou de sem_rosto)."""
        return self._buffer.n

    def reset(self) -> None:
        self._limpar_janelas()
        self._historico.clear()
        self._ultimo_bpm = None
        self._visto = None

    def update(self, frame_bgr, landmarks, timestamp: float, infrared: bool = False) -> CardioReading:
        t = float(timestamp)
        pontos = _pontos(landmarks)
        if pontos is None or frame_bgr is None:
            return self._sem_rosto(t)
        if self._visto is not None and t - self._visto > BURACO_MAX_S:
            self._quebrar = True
        self._visto = t
        movendo = self._movimento(t, pontos)
        medias, _, poligonos = _medias_rois(frame_bgr, self._suavizar(t, pontos))
        canal = "ir" if infrared or _monocromatico(medias) else "rgb"
        if canal != self._canal:
            self._limpar_janelas()  # trocar de câmera/canal no meio da janela misturaria sinais diferentes
            self._canal = canal
        if movendo:
            self._quebrar = True
            return self._leitura("movimento", poligonos)
        if all(m is None for m in medias.values()) or not self._acrescentar(t, medias, pontos):
            self._quebrar = True
            return self._leitura(self._estado_atual(), poligonos)
        if t >= self._proximo and self._duracao >= self.minimo_s - 1e-6:
            self._proximo = t + self.passo_s - 1e-6
            self._estimar(t)
        self._atualizar_onda(t)
        return self._leitura(self._estado_atual(), poligonos)

    # --- estado interno ----------------------------------------------------------------------------------------
    def _limpar_janelas(self) -> None:
        self._buffer = _Buffer(3 * len(ROIS) + 2)  # R, G, B por ROI + intensidade da testa + altura do nariz
        self._segmento = 0
        self._quebrar = True
        self._duracao = 0.0  # tempo bom acumulado desde o último zerar (aquecimento)
        self._mov: deque = deque()
        self._mov_ate = -math.inf
        self._suaves = None
        self._t_suave = None
        self._estimativas: deque = deque(maxlen=MEDIANA_N)
        self._proximo = -math.inf
        self._estado = "medindo"
        self._bpm = None
        self._snr = None
        self._confianca = 0.0
        self._respiracao = None
        self._rmssd = None
        self._onda: list[float] = []
        self._proxima_onda = -math.inf
        self._melhor = "testa"
        self._registrado = True

    def _sem_rosto(self, t: float) -> CardioReading:
        if self._visto is None or t - self._visto >= SEM_ROSTO_S:
            if self._buffer.n or self._duracao or self._ultimo_bpm is not None:
                self._limpar_janelas()
                self._ultimo_bpm = None
            self._visto = None
            return CardioReading("sem_rosto", historico_bpm=list(self._historico), canal=self._canal)
        self._quebrar = True  # rosto sumiu por pouco: mantém a última leitura, sem medir
        return self._leitura(self._estado_atual(), {})

    def _movimento(self, t: float, pontos: np.ndarray) -> bool:
        olhos = float(np.linalg.norm(pontos[CANTOS_OLHOS[0]] - pontos[CANTOS_OLHOS[1]]))
        atuais = pontos[_INDICES_MOVIMENTO]
        while self._mov and t - self._mov[0][0] > JANELA_MOVIMENTO_S:
            self._mov.popleft()
        if self._mov and olhos > 1.0:
            deslocamento = float(np.linalg.norm(atuais - self._mov[0][1], axis=1).mean()) / olhos
            if deslocamento > LIMIAR_MOVIMENTO:
                self._mov_ate = t + SEGURA_MOVIMENTO_S
        self._mov.append((t, atuais))
        return t < self._mov_ate

    def _suavizar(self, t: float, pontos: np.ndarray) -> np.ndarray:
        """Média exponencial dos vértices das ROIs (o resto dos pontos não entra na máscara)."""
        atuais = pontos[_INDICES_ROI].astype(np.float64)
        if self._suaves is None or self._t_suave is None or not 0 < t - self._t_suave <= BURACO_MAX_S:
            self._suaves = atuais
        else:
            alfa = 1.0 - math.exp(-(t - self._t_suave) / SUAVIZACAO_PONTOS_S)
            self._suaves = self._suaves + alfa * (atuais - self._suaves)
        self._t_suave = t
        saida = pontos.copy()
        saida[_INDICES_ROI] = self._suaves
        return saida

    def _acrescentar(self, t: float, medias: dict, pontos: np.ndarray) -> bool:
        anterior = self._buffer.ultimo_t
        if anterior is not None and t <= anterior:
            return False  # horário repetido ou voltando: ignora o quadro
        if self._quebrar or anterior is None or t - anterior > BURACO_MAX_S:
            self._segmento += 1
            self._quebrar = False
        else:
            self._duracao += t - anterior
        linha = []
        for nome in _NOMES:
            linha.extend(medias[nome] if medias[nome] is not None else (math.nan,) * 3)
        testa = medias["testa"]
        olhos = float(np.linalg.norm(pontos[CANTOS_OLHOS[0]] - pontos[CANTOS_OLHOS[1]]))
        linha.append(sum(testa) / 3.0 if testa is not None else math.nan)
        linha.append(float(pontos[list(PONTE_NARIZ), 1].mean()) / olhos if olhos > 1.0 else math.nan)
        self._buffer.acrescentar(t, self._segmento, linha)
        self._buffer.cortar_antes(t - max(IDADE_MAX_S, RESP_JANELA_S))
        return True

    def _fps(self, ts: np.ndarray, segs: np.ndarray) -> float:
        dt = np.diff(ts)
        intervalos = dt[(np.diff(segs) == 0) & (dt <= BURACO_MAX_S)]
        return float(1.0 / np.median(intervalos)) if len(intervalos) else 0.0

    def _estimar(self, t: float) -> None:
        ts, segs, valores = self._buffer.desde(t - IDADE_MAX_S)
        mono = self._canal == "ir"
        por_roi = {}
        for k, nome in enumerate(_NOMES):
            cor = valores[:, 3 * k:3 * k + 3]
            ok = np.isfinite(cor[:, 0])
            if ok.sum() < 3:
                continue
            pulso, duracao, ultimo = _pulso_emendado(ts[ok], cor[ok], segs[ok], self.janela_s, mono)
            if pulso is None or duracao < 0.8 * self.minimo_s:
                continue
            f, p = espectro(remover_tendencia(pulso), FS)
            f0, snr = pico_e_snr(f, p)
            if f0 is not None:
                por_roi[nome] = (f0, snr, p, ultimo)
        if not por_roi:
            self._registrar(None, None, None)
            return
        # Combinação ponderada pelo SNR: soma dos espectros normalizados com peso 10^(SNR/10) (pesquisa rPPG, §2.3).
        faixa = (f >= BANDA_SNR_HZ[0]) & (f <= BANDA_SNR_HZ[1])
        combinado = sum(10.0 ** (snr / 10.0) * p / max(p[faixa].sum(), 1e-300) for _, snr, p, _ in por_roi.values())
        f0, snr = pico_e_snr(f, combinado)
        self._melhor = max(por_roi, key=lambda nome: por_roi[nome][1])
        fps = self._fps(ts, segs)
        bom = f0 is not None and snr >= LIMIAR_SNR_DB and fps >= FPS_MINIMO
        concordam = sum(1 for g, s, _, _ in por_roi.values() if bom and s >= LIMIAR_SNR_DB and abs(g - f0) * 60 <= 5)
        self._registrar(60.0 * f0 if bom else None, snr, fps, concordam)
        resp_t, _, resp = self._buffer.desde(t - RESP_JANELA_S)
        self._respiracao = _respiracao_rpm(resp_t, resp[:, _COL_INTENSIDADE], resp[:, _COL_NARIZ])
        self._rmssd = None
        if bom and self._estado == "pronto" and fps >= RMSSD_FPS_MIN and snr >= RMSSD_SNR_MIN_DB:
            self._rmssd = _rmssd_ms(por_roi[self._melhor][3], f0)

    def _registrar(self, bpm, snr, fps, concordam: int = 0) -> None:
        self._estimativas.append(bpm)
        self._snr = snr
        self._registrado = False
        aceitas = [b for b in self._estimativas if b is not None]
        perto = []
        if any(b is not None for b in list(self._estimativas)[-RECENTES_N:]):
            mediana = float(np.median(aceitas))
            perto = [b for b in aceitas if abs(b - mediana) <= CONSISTENCIA_BPM]
        if len(perto) < CONSISTENTES_N:
            self._estado, self._bpm, self._confianca = "sinal_fraco", None, 0.0
            return
        self._estado = "pronto"
        self._bpm = round(float(np.median(perto)), 1)
        pelo_snr = min(1.0, max(0.0, (snr - LIMIAR_SNR_DB) / FAIXA_CONFIANCA_DB)) if snr is not None else 0.0
        pelo_fps = min(1.0, fps / 25.0) if fps else 1.0
        self._confianca = round((0.25 + 0.75 * pelo_snr) * (1.0 if concordam >= 2 else 0.8) * pelo_fps, 3)

    def _atualizar_onda(self, t: float) -> None:
        if self._duracao < 2.0 or t < self._proxima_onda:
            return
        self._proxima_onda = t + ONDA_PASSO_S - 1e-6
        k = _NOMES.index(self._melhor)
        ts, segs, valores = self._buffer.desde(t - ONDA_S - POS_JANELA_S - 1.0)
        cor = valores[:, 3 * k:3 * k + 3]
        ok = np.isfinite(cor[:, 0])
        if ok.sum() < 3:
            return
        pulso, _, _ = _pulso_emendado(ts[ok], cor[ok], segs[ok], ONDA_S, self._canal == "ir")
        if pulso is None or len(pulso) < 8:
            return
        onda = -passa_faixa(pulso, FS)  # sístole para cima (hipótese pelo modelo de pele de Wang 2017)
        maximo = float(np.abs(onda).max())
        self._onda = np.round(onda / maximo if maximo > 0 else onda, 4).tolist()

    def _estado_atual(self) -> str:
        return "medindo" if self._duracao < self.aquecimento_s else self._estado

    def _leitura(self, estado: str, poligonos: dict) -> CardioReading:
        pronto = estado == "pronto"
        if pronto:
            self._ultimo_bpm = self._bpm
            if not self._registrado:
                self._historico.append(self._bpm)
                self._registrado = True
        mostra_extra = estado in ("pronto", "sinal_fraco", "medindo")
        return CardioReading(
            estado=estado,
            bpm=self._bpm if pronto else None,
            confianca=self._confianca if pronto else 0.0,
            snr_db=None if self._snr is None else round(self._snr, 2),
            respiracao_rpm=None if self._respiracao is None or not mostra_extra else round(self._respiracao, 1),
            rmssd_ms=None if self._rmssd is None or not pronto else round(self._rmssd, 1),
            progresso=1.0 if self._duracao >= self.aquecimento_s else round(self._duracao / self.aquecimento_s, 4),
            onda=list(self._onda),
            historico_bpm=list(self._historico),
            canal=self._canal,
            rois=poligonos,
            ultimo_bpm=self._ultimo_bpm,
        )
