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
# Estimativa entre este SNR e o LIMIAR_SNR_DB só conta se concordar (±CONSISTENCIA_BPM) com a mediana das estimativas
# acima do limiar ou com o último número mostrado há pouco (MEMORIA_S). Sem âncora acima do limiar, nunca vira número:
# só ruído continua sem número (CAR-04, CAR-20). Valor medido no sintético em 20/10/2026 (ver CAR-21).
LIMIAR_SNR_CONSISTENTE_DB = -1.5
FAIXA_CONFIANCA_DB = 10.0  # SNR acima do limiar que leva a parte do SNR na confiança a 1
# Abaixo de 60 bpm os dois limiares sobem 2 dB: ruído de luz e de movimento é 1/f (piso mais alto na ponta baixa da
# banda) e o SNR contra a banda inteira subestima isso. Medido em 20/10/2026: ruído rosa + deriva de cor SEM pulso deu
# picos de 46-55 bpm com SNR de +0,4 a +1,5 dB (viravam número); com pulso de 72, nenhum pico abaixo de 60 bpm passou de
# -0,8 dB (CAR-22). Pulso real de 50-60 bpm precisa de sinal um pouco melhor para aparecer.
BAIXA_FREQ_BPM = 60.0
EXTRA_BAIXA_DB = 2.0
# POS é o padrão; CHROM ou GREEN só ganham a janela com SNR pelo menos esta margem acima (pesquisa rPPG §1.1: no
# sintético o GREEN ganha por construção, no mundo real o POS ganha; a margem evita trocar por acaso).
MARGEM_METODO_DB = 1.0

# --- Regras para mostrar número (pesquisa rPPG de 19/10/2026, §3.5 e §3.7) -------------------------------------------
AQUECIMENTO_S = 15.0  # dados bons antes do primeiro número (~3 janelas seguidas); o progresso vai de 0 a 1 aqui
# Taxa de quadros: abaixo de FPS_MINIMO, "camera_lenta" e nenhum número; entre FPS_MINIMO e FPS_BOM mede com a janela
# de JANELA_LENTA_S e confiança menor (notebook comum com MediaPipe roda a 10-15 quadros/s; o portão antigo de 15
# barrava esses notebooks: pedido de 20/10/2026). A 10 fps com janela de 10 s o protótipo errou 5,4 bpm em média; com
# 12 s e a regra de consistência, o sintético fica em <= 3 bpm (CAR-18). Hipótese até medir com webcam e oxímetro.
FPS_MINIMO = 10.0
FPS_BOM = 15.0
JANELA_LENTA_S = 12.0
MEDIANA_N = 5  # mediana das últimas 5 estimativas
CONSISTENTES_N = 3  # pelo menos 3 das últimas 5 estimativas boas e perto da mediana...
RECENTES_N = 2  # ...e pelo menos 1 das 2 últimas boa (uma janela ruim isolada não apaga o número; duas apagam)
CONSISTENCIA_BPM = 6.0  # = resolução nativa de uma janela de 10 s (Nowara 2018, §4.1.1)
# O último número mostrado vale como um voto por até MEMORIA_S: depois de perder o sinal, 2 janelas boas que concordam
# com ele trazem o número de volta (em vez de 3 e de outro aquecimento). Pedido de 20/10/2026: "nunca parar".
MEMORIA_S = 30.0
FRESCO_S = 1.0  # a estimativa só sai se o trecho bom mais novo terminou há no máximo isso (senão é dado velho)
METADE_RAZAO = 0.5  # pico em f/2 com >= 50% da potência do principal: fica f/2 (evita pegar o 2º harmônico)
BORDA_HZ = 0.05  # pico a menos disso das bordas da banda não vale (borda = vazamento da tendência; CAR-22)
# Abaixo desta confiança o número não é publicado (fica "sinal_fraco" com ultimo_bpm e progresso). Pedido da
# coordenação em 20/10/2026 depois do "42 bpm, confiança 25%" na tela. A confiança junta SNR e concordância entre
# janelas (votos), para o piso não apagar pulso fraco mas consistente (CAR-21) nem câmera de 10-12 quadros/s (CAR-18).
# 0,40 = onde a tela (tela_teste/estado.py) já chama a leitura de "Sinal fraco". Com 0,35, ruído rosa + deriva de cor
# SEM pulso deu 49-53 bpm por 6 s com confiança 0,373 (o código antigo deu 54 bpm por 2 s no mesmo caso; CAR-22).
CONFIANCA_MINIMA = 0.40
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
# Pixel com algum canal <= 7 (preto do sensor) ou >= 252 (estourado) sai da média (pesquisa rPPG §2.2). Antes era
# 15 e 250: com pele clara e luz forte o vermelho fica perto de 245-250 e a faixa velha jogava fora até metade da ROI
# (CAR-19, 20/10/2026). Só o pixel estourado sai; a ROI fica enquanto tiver PIXELS_MIN_ROI pixels bons.
PIXEL_ESCURO = 7
PIXEL_SATURADO = 252
PIXELS_MIN_ROI = 30  # ROI com menos pixels úteis é descartada (era 100). Hipótese: rosto pequeno na imagem; a calibrar.
# Motivo medido (pedido de 20/10/2026: a tela falava em luz sem medir). Luminância Y (0,299 R + 0,587 G + 0,114 B)
# média de todos os pixels das ROIs e fração de pixels com algum canal >= PIXEL_SATURADO, em média exponencial de
# LUZ_SUAVIZACAO_S. Hipóteses a calibrar com o ferramentas/diagnosticar_cardio.py em webcam: abaixo de Y = 50 (~20%
# da escala) o pulso de ~0,3% fica abaixo de 0,15 nível e o ganho alto da câmera domina; acima de 25% de pixels
# estourados sobra pouca pele útil e o que sobra fica na borda do reflexo.
LUZ_MINIMA = 50.0
FRACAO_ESTOURADA_MAX = 0.25
LUZ_SUAVIZACAO_S = 1.0
LUZ_A_CADA = 3  # a luz é medida 1 quadro em 3 (média exponencial de 1 s: não precisa de todos; CAR-14)
# Quadro com salto de intensidade numa ROI (em relação ao quadro anterior) maior que SALTO_K vezes a mediana dos
# saltos dos últimos SALTO_N quadros (e maior que SALTO_MIN) sai da janela e quebra o trecho: piscada de luz, ajuste
# automático de exposição, mão passando. A mediana inclui os quadros jogados fora: se o ruído continuar por mais de
# ~5 s ele vira o normal e volta a entrar (aí o SNR decide), para a medida nunca travar (CAR-15).
SALTO_K = 6.0
SALTO_MIN = 0.004
SALTO_N = 300
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


MOTIVOS = ("pouca_luz", "luz_estourada", "mexendo", "camera_lenta", "sinal_fraco")


@dataclass
class CardioReading:
    estado: str  # "sem_rosto" | "medindo" | "pronto" | "sinal_fraco" | "movimento"
    bpm: float | None = None
    confianca: float = 0.0  # 0..1
    snr_db: float | None = None
    respiracao_rpm: float | None = None
    rmssd_ms: float | None = None  # experimental
    # 0..1: no aquecimento, dados bons / AQUECIMENTO_S; depois de perder o número, quanto falta para ele voltar
    # (trecho bom novo + janelas que concordam); 1 em "pronto".
    progresso: float = 0.0
    onda: list[float] = field(default_factory=list)  # últimos ~6 s normalizados -1..1, ~30 Hz; sobe na sístole
    historico_bpm: list[float] = field(default_factory=list)  # últimos 120 valores "pronto"
    canal: str = "rgb"  # "rgb" | "ir"
    rois: dict[str, list[tuple[int, int]]] = field(default_factory=dict)  # "testa", "bochecha_esq", "bochecha_dir"
    ultimo_bpm: float | None = None  # último bpm bom, para mostrar esmaecido em movimento/sinal fraco
    # --- 20/10/2026 (só acréscimos; os campos acima não mudam) ---
    # Por que não há número, MEDIDO: "pouca_luz" (luminância < LUZ_MINIMA), "luz_estourada" (fração estourada >
    # FRACAO_ESTOURADA_MAX), "mexendo" (movimento agora ou há pouco), "camera_lenta" (fps < FPS_MINIMO), "sinal_fraco"
    # (nada disso, só o SNR baixo) ou None (tudo bem: "pronto", "sem_rosto", ou "medindo" sem problema medido).
    motivo: str | None = None
    fps: float | None = None  # quadros por segundo com rosto, medidos nos últimos ~2 s
    # Estimativa de quanto falta para o número (s): 0 em "pronto"; None em "movimento", "sem_rosto" e com
    # motivo "camera_lenta" (não dá para estimar).
    segundos_para_medida: float | None = None
    luminancia: float | None = None  # Y médio dos pixels das ROIs (0-255)
    fracao_saturada: float | None = None  # 0..1 dos pixels das ROIs com algum canal >= PIXEL_SATURADO
    metodo: str | None = None  # "pos" | "chrom" | "green" | "ir": o que ganhou a última janela


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


def chrom(rgb, fs: float) -> np.ndarray:
    """CHROM (de Haan & Jeanne, IEEE TBME 60(10), 2013) na forma da pesquisa rPPG §1.3: canais divididos pela média,
    X = 3R - 2G e Y = 1,5R + G - 1,5B filtrados na banda no trecho inteiro (filtrar dentro de 1,6 s não funciona: a
    resolução de 0,625 Hz joga 55 bpm fora da banda) e S = Xf - alfa·Yf com alfa = sigma(Xf)/sigma(Yf).
    A banda vai até a borda de cima da banda do SNR (BANDA_SNR_HZ, 6,2 Hz) e não até 3 Hz: cortando em 3 Hz o ruído
    entre 3 e 6,2 Hz sumia do denominador do SNR e o ruído puro chegava a +3,4 dB (medido em 20/10/2026), o que
    tornava a comparação com o POS e o GREEN injusta e furava a proteção do CAR-04.
    Implementação própria; sobe quando o sangue chega (sinal oposto ao do POS, o que não muda a frequência)."""
    rgb = np.asarray(rgb, dtype=float)
    n = len(rgb)
    media = rgb.mean(axis=0) if n else np.zeros(3)
    if n < 4 or np.any(media <= 0):
        return np.zeros(n)
    c = rgb / media
    banda = (BANDA_HZ[0], BANDA_SNR_HZ[1])
    xf = passa_faixa(3.0 * c[:, 0] - 2.0 * c[:, 1], fs, banda)
    yf = passa_faixa(1.5 * c[:, 0] + c[:, 1] - 1.5 * c[:, 2], fs, banda)
    desvio_y = float(yf.std())
    return xf - (float(xf.std()) / desvio_y if desvio_y > 0 else 0.0) * yf


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
    """(frequência do pulso em Hz, SNR em dB) a partir do espectro, ou (None, None) se não houver pico na banda.
    Pico = o maior MÁXIMO LOCAL do espectro inteiro (não só da banda) entre banda[0] + BORDA_HZ e banda[1] - BORDA_HZ,
    com interpolação parabólica; se houver pico em f/2 com >= 50% da potência, fica f/2.
    Antes era o maior valor dentro da banda: com tendência ou ruído de baixa frequência vazando, o maior valor era a
    própria borda (0,70 Hz = 42 bpm, visto na tela em 20/10/2026), que não é pico nenhum (CAR-22)."""
    dentro = np.flatnonzero((f >= banda[0] + BORDA_HZ) & (f <= banda[1] - BORDA_HZ))
    dentro = dentro[(dentro > 0) & (dentro < len(p) - 1)]
    indices = dentro[(p[dentro] >= p[dentro - 1]) & (p[dentro] >= p[dentro + 1])] if len(dentro) else dentro
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


def _media_roi(quadro: np.ndarray, poligono: np.ndarray, medir_luz: bool = True):
    """(R, G, B) médios dentro do polígono, sem pixels escuros nem estourados (ou None), pixels usados e, com
    medir_luz, a luz no polígono inteiro: (pixels do polígono, pixels estourados, soma da luminância Y); sem medir_luz,
    None."""
    altura, largura = quadro.shape[:2]
    x0 = max(int(poligono[:, 0].min()), 0)
    y0 = max(int(poligono[:, 1].min()), 0)
    x1 = min(int(poligono[:, 0].max()) + 1, largura)
    y1 = min(int(poligono[:, 1].max()) + 1, altura)
    if x1 - x0 < 2 or y1 - y0 < 2:
        return None, 0, None
    recorte = quadro[y0:y1, x0:x1]
    poligono_m = np.zeros((y1 - y0, x1 - x0), np.uint8)
    cv2.fillPoly(poligono_m, [poligono - np.array([x0, y0], np.int32)], 255)
    luz = None
    if medir_luz:
        total = cv2.countNonZero(poligono_m)
        if total:
            b, g, r = cv2.mean(recorte, mask=poligono_m)[:3]
            estourados = total - cv2.countNonZero(
                cv2.bitwise_and(poligono_m, cv2.inRange(recorte, (0, 0, 0), (PIXEL_SATURADO - 1,) * 3)))
            luz = (total, estourados, (0.299 * r + 0.587 * g + 0.114 * b) * total)
    mascara = cv2.bitwise_and(poligono_m, cv2.inRange(recorte, (PIXEL_ESCURO + 1,) * 3, (PIXEL_SATURADO - 1,) * 3))
    pixels = cv2.countNonZero(mascara)
    if pixels < PIXELS_MIN_ROI:
        return None, pixels, luz
    b, g, r = cv2.mean(recorte, mask=mascara)[:3]
    return (r, g, b), pixels, luz


def _medias_rois(quadro: np.ndarray, pontos: np.ndarray, medir_luz: bool = True):
    """Médias R, G, B por ROI (ou None), pixels usados, polígonos usados e a luz medida (luminância média e fração
    estourada nos polígonos, ou None). Bochecha com menos da metade da área da outra (rosto virado) sai."""
    if quadro.ndim == 2:
        quadro = cv2.cvtColor(quadro, cv2.COLOR_GRAY2BGR)
    poligonos = {nome: np.rint(pontos[list(indices)]).astype(np.int32) for nome, indices in ROIS.items()}
    areas = {nome: abs(cv2.contourArea(poligonos[nome])) for nome in ("bochecha_esq", "bochecha_dir")}
    maior = max(areas.values())
    medias, pixels = {}, {}
    total = estourados = soma_y = 0.0
    for nome, poligono in poligonos.items():
        if nome in areas and (maior <= 0 or areas[nome] < RAZAO_BOCHECHAS_MIN * maior):
            medias[nome], pixels[nome] = None, 0
            continue
        medias[nome], pixels[nome], luz = _media_roi(quadro, poligono, medir_luz)
        if luz is not None:
            total, estourados, soma_y = total + luz[0], estourados + luz[1], soma_y + luz[2]
    usados = {nome: [(int(x), int(y)) for x, y in poligonos[nome]] for nome in ROIS if medias[nome] is not None}
    luz = (soma_y / total, estourados / total) if total else None
    return medias, pixels, usados, luz


def media_das_rois(frame_bgr: np.ndarray, landmarks):
    """Média R, G, B (ponderada pelos pixels) da testa e das bochechas, polígonos usados e total de pixels.
    Devolve (np.array([R, G, B]) ou None, {nome: [(x, y), ...]}, pixels)."""
    pontos = _pontos(landmarks)
    if pontos is None or frame_bgr is None:
        return None, {}, 0
    medias, pixels, usados, _ = _medias_rois(frame_bgr, pontos)
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


_METODOS = {
    "pos": lambda u: pos(u, FS),
    "chrom": lambda u: chrom(u, FS),
    "green": lambda u: canal_unico(u[:, 1], FS),
    "ir": lambda u: canal_unico(u.mean(axis=1), FS),
}
_TRECHO_MIN = int(math.ceil(POS_JANELA_S * FS)) + 1  # amostras (na grade de FS) para um trecho entrar
TRECHO_MIN_S = _TRECHO_MIN / FS


def _trechos_uniformes(ts, valores, segmentos, duracao: float):
    """Trechos contínuos mais recentes (do mais novo para o mais velho) reamostrados a FS Hz até somar `duracao` s.
    Devolve ([(uniforme, amostras a manter do fim), ...], duração em s, horário do fim do trecho mais novo usado)."""
    saida, total, fim_novo = [], 0.0, None
    for inicio, fim in reversed(_trechos(ts, segmentos)):
        if total >= duracao - 0.5 / FS:
            break
        if fim - inicio < 3:
            continue
        _, uniforme = reamostrar(ts[inicio:fim], valores[inicio:fim], FS)
        if len(uniforme) < _TRECHO_MIN:
            continue
        if fim_novo is None:
            fim_novo = float(ts[fim - 1])
        manter = min(len(uniforme), int(round((duracao - total) * FS)))
        saida.append((uniforme, manter))
        total += manter / FS
    return saida, total, fim_novo


def _aplicar(trechos, metodo: str):
    """Pulso emendado: cada trecho com seu método (emendar depois do POS evita o degrau de cor entre trechos, pele um
    pouco diferente depois de mexer). Devolve (pulso, pulso do trecho mais novo) ou (None, None)."""
    partes, ultimo = [], None
    for uniforme, manter in trechos:
        h = _METODOS[metodo](uniforme)
        if ultimo is None:
            ultimo = h
        partes.append(h[len(h) - manter:])
    return (np.concatenate(partes[::-1]), ultimo) if partes else (None, None)


def _pulso_emendado(ts, valores, segmentos, duracao: float, mono: bool):
    """Pulso POS (ou canal único) dos trechos mais recentes até somar `duracao` segundos, na grade de FS Hz.
    Devolve (pulso, duração em s, pulso do trecho mais recente) ou (None, 0.0, None)."""
    trechos, total, _ = _trechos_uniformes(ts, valores, segmentos, duracao)
    pulso, ultimo = _aplicar(trechos, "ir" if mono else "pos")
    return (None, 0.0, None) if pulso is None else (pulso, total, ultimo)


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

def _extra_db(bpm: float) -> float:
    return EXTRA_BAIXA_DB if bpm < BAIXA_FREQ_BPM else 0.0


class CardioMonitor:
    """Uma chamada de update por quadro (barata: médias das ROIs e a onda); a estimativa roda uma vez por segundo.

    Nunca para (pedido de 20/10/2026): quando o sinal piora, as janelas continuam deslizando, o último número bom fica
    em `ultimo_bpm` e vale como voto por MEMORIA_S, então o número volta com 2 janelas boas, sem outro aquecimento.
    Só zera tudo com SEM_ROSTO_S sem rosto (CAR-10)."""

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
        self._t_ultimo_bom = -math.inf
        self._visto = None

    def update(self, frame_bgr, landmarks, timestamp: float, infrared: bool = False) -> CardioReading:
        t = float(timestamp)
        self._t = t
        pontos = _pontos(landmarks)
        if pontos is None or frame_bgr is None:
            return self._sem_rosto(t)
        if self._visto is not None and t - self._visto > BURACO_MAX_S:
            self._quebrar = True
        self._visto = t
        self._marcar_taxa(t)
        movendo = self._movimento(t, pontos)
        self._quadros += 1
        medir_luz = self._luz is None or self._quadros % LUZ_A_CADA == 0
        medias, _, poligonos, luz = _medias_rois(frame_bgr, self._suavizar(t, pontos), medir_luz)
        if medir_luz:
            self._medir_luz(t, luz)
        canal = "ir" if infrared or _monocromatico(medias) else "rgb"
        if canal != self._canal:
            self._limpar_janelas()  # trocar de câmera/canal no meio da janela misturaria sinais diferentes
            self._canal = canal
        if movendo:
            self._quebrar = True
            self._intensidades = None
            return self._leitura("movimento", poligonos)
        aceito = any(m is not None for m in medias.values()) and self._acrescentar(t, medias, pontos)
        if not aceito:
            self._quebrar = True
        # O relógio da estimativa anda mesmo com o quadro jogado fora: sem dado novo, a janela registra "nada" e o
        # número sai depois de 2 s (antes ficava "pronto" parado no último valor).
        if t >= self._proximo and self._duracao >= self.minimo_s - 1e-6:
            self._proximo = t + self.passo_s - 1e-6
            self._estimar(t)
        if aceito:
            self._atualizar_onda(t)
        return self._leitura(self._estado_atual(), poligonos)

    # --- estado interno ----------------------------------------------------------------------------------------
    def _limpar_janelas(self) -> None:
        self._buffer = _Buffer(3 * len(ROIS) + 2)  # R, G, B por ROI + intensidade da testa + altura do nariz
        self._segmento = 0
        self._inicio_segmento = None
        self._quebrar = True
        self._duracao = 0.0  # tempo bom acumulado desde o último zerar (aquecimento)
        self._mov: deque = deque()
        self._mov_ate = -math.inf
        self._ultimo_mov = -math.inf
        self._suaves = None
        self._t_suave = None
        self._estimativas: deque = deque(maxlen=MEDIANA_N)  # (bpm, snr) ou None
        self._votos = 0
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
        self._metodo = None
        self._registrado = True
        self._intensidades = None
        self._saltos: deque = deque(maxlen=SALTO_N)
        self._luz = None
        self._estourado = None
        self._t_luz = None
        self._tempos: deque = deque()
        self._fps_cache = (-math.inf, None)
        self._escala_salto = None
        self._quadros = 0
        self._t = 0.0
        self.diagnostico: dict = {}  # bpm e SNR de cada método na última janela (ferramentas e testes)

    def _sem_rosto(self, t: float) -> CardioReading:
        if self._visto is None or t - self._visto >= SEM_ROSTO_S:
            if self._buffer.n or self._duracao or self._ultimo_bpm is not None:
                self._limpar_janelas()
                self._ultimo_bpm = None
                self._t_ultimo_bom = -math.inf
            self._visto = None
            return CardioReading("sem_rosto", historico_bpm=list(self._historico), canal=self._canal)
        self._quebrar = True  # rosto sumiu por pouco: mantém a última leitura, sem medir
        self._intensidades = None
        return self._leitura(self._estado_atual(), {})

    def _marcar_taxa(self, t: float) -> None:
        self._tempos.append(t)
        while len(self._tempos) > 2 and t - self._tempos[0] > 2.0:
            self._tempos.popleft()

    def _fps_camera(self) -> float | None:
        """Quadros com rosto por segundo nos últimos ~2 s (mediana dos intervalos, sem os buracos)."""
        if len(self._tempos) < 3 or self._tempos[-1] - self._tempos[0] < 0.9:
            return None
        if self._tempos[-1] - self._fps_cache[0] < 0.5:
            return self._fps_cache[1]
        dt = np.diff(np.asarray(self._tempos))
        dt = dt[(dt > 0) & (dt <= BURACO_MAX_S)]
        fps = float(1.0 / np.median(dt)) if len(dt) else None
        self._fps_cache = (self._tempos[-1], fps)
        return fps

    def _medir_luz(self, t: float, luz) -> None:
        if luz is None:
            return
        if self._luz is None or self._t_luz is None or not 0 < t - self._t_luz <= BURACO_MAX_S:
            self._luz, self._estourado = luz
        else:
            alfa = 1.0 - math.exp(-(t - self._t_luz) / LUZ_SUAVIZACAO_S)
            self._luz += alfa * (luz[0] - self._luz)
            self._estourado += alfa * (luz[1] - self._estourado)
        self._t_luz = t

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
        if t < self._mov_ate:
            self._ultimo_mov = t
            return True
        return False

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

    def _salto(self, medias: dict) -> bool:
        """True se a intensidade de alguma ROI pulou demais desde o quadro anterior (ver SALTO_K)."""
        atuais = {nome: (m[0] + m[1] + m[2]) / 3.0 for nome, m in medias.items() if m is not None}
        anteriores, self._intensidades = self._intensidades, atuais
        if not anteriores:
            return False
        comuns = [nome for nome in atuais if nome in anteriores and anteriores[nome] > 0]
        if not comuns:
            return False
        salto = max(abs(atuais[nome] / anteriores[nome] - 1.0) for nome in comuns)
        if len(self._saltos) >= 30 and (self._escala_salto is None or self._quadros % 10 == 0):
            self._escala_salto = float(np.median(self._saltos))  # a cada 10 quadros basta (CAR-14)
        self._saltos.append(salto)
        escala = self._escala_salto
        return escala is not None and salto > max(SALTO_K * escala, SALTO_MIN)

    def _acrescentar(self, t: float, medias: dict, pontos: np.ndarray) -> bool:
        anterior = self._buffer.ultimo_t
        if anterior is not None and t <= anterior:
            return False  # horário repetido ou voltando: ignora o quadro
        if self._salto(medias):
            return False
        if self._quebrar or anterior is None or t - anterior > BURACO_MAX_S:
            self._segmento += 1
            self._inicio_segmento = t
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
        fps = self._fps(ts, segs) if len(ts) > 1 else 0.0
        janela = self.janela_s if fps >= FPS_BOM else max(self.janela_s, JANELA_LENTA_S)
        mono = self._canal == "ir"
        metodos = ("ir",) if mono else ("pos", "chrom", "green")
        por_roi: dict[str, tuple] = {}
        trechos_roi: dict[str, list] = {}
        f = None
        for k, nome in enumerate(_NOMES):
            cor = valores[:, 3 * k:3 * k + 3]
            ok = np.isfinite(cor[:, 0])
            if ok.sum() < 3:
                continue
            trechos, duracao, fim_novo = _trechos_uniformes(ts[ok], cor[ok], segs[ok], janela)
            if not trechos or duracao < 0.8 * self.minimo_s or t - fim_novo > FRESCO_S:
                continue  # pouco dado, ou só dado velho (o trecho bom mais novo acabou há mais de FRESCO_S)
            pulso, ultimo = _aplicar(trechos, metodos[0])
            f, p = espectro(remover_tendencia(pulso), FS)
            f0, snr = pico_e_snr(f, p)
            if f0 is not None:
                por_roi[nome] = (f0, snr, p, ultimo)
                trechos_roi[nome] = trechos
        resultados = {}
        if por_roi:
            # Combinação das ROIs ponderada pelo SNR: soma dos espectros normalizados com peso 10^(SNR/10) (pesquisa
            # rPPG, §2.3).
            faixa = (f >= BANDA_SNR_HZ[0]) & (f <= BANDA_SNR_HZ[1])
            combinado = sum(10.0 ** (snr / 10.0) * p / max(p[faixa].sum(), 1e-300) for _, snr, p, _ in por_roi.values())
            f0, snr = pico_e_snr(f, combinado)
            if f0 is not None:
                resultados[metodos[0]] = (f0, snr, por_roi)
        # CHROM e GREEN rodam só na ROI em que o POS foi melhor (custo: CAR-14) e só quando o POS não está folgado
        # (abaixo de LIMIAR + FAIXA_CONFIANCA_DB, onde a confiança já seria 1). Uma ROI só contra o POS combinado das
        # três deixa a troca de método conservadora.
        if not mono and metodos[0] in resultados and resultados[metodos[0]][1] < LIMIAR_SNR_DB + FAIXA_CONFIANCA_DB:
            melhor = max(por_roi, key=lambda nome: por_roi[nome][1])
            for metodo in metodos[1:]:
                pulso, ultimo = _aplicar(trechos_roi[melhor], metodo)
                # O CHROM já sai filtrado na banda (sem tendência); o GREEN passa pelo Tarvainen.
                f, p = espectro(pulso if metodo == "chrom" else remover_tendencia(pulso), FS)
                f0, snr = pico_e_snr(f, p)
                if f0 is not None:
                    # Escolher o melhor de 3 sobe o SNR do ruído puro (máximo de -1,1 dB contra -2,8 dB do POS, 408
                    # janelas, 20/10/2026): o SNR do método alternativo entra descontado da margem, o que deixa o
                    # ruído abaixo do LIMIAR_SNR_CONSISTENTE_DB e a troca só acontece com folga real.
                    snr -= MARGEM_METODO_DB
                    resultados[metodo] = (f0, snr, {melhor: (f0, snr, p, ultimo)})
        self.diagnostico = {m: (round(60.0 * r[0], 1), round(r[1], 2)) for m, r in resultados.items()}
        if not resultados:
            self._registrar(None, None, None)
            return
        # POS (ou o canal único) é o padrão. CHROM ou GREEN só ganham com SNR MARGEM_METODO_DB acima E com o pico
        # concordando com o do POS ou com a referência das últimas janelas: luz piscando na banda (tela, lâmpada)
        # dá pico forte no GREEN numa frequência errada, e o POS cancela essa variação (Wang 2017). CAR-20.
        padrao = resultados.get(metodos[0])
        if padrao is None:
            self._registrar(None, None, None)
            return
        referencia = self._referencia()
        escolhido = metodos[0]
        for metodo, (g, snr, _) in resultados.items():
            concorda = abs(g - padrao[0]) * 60 <= CONSISTENCIA_BPM or (
                referencia is not None and abs(60.0 * g - referencia) <= CONSISTENCIA_BPM)
            if metodo != metodos[0] and concorda and snr > resultados[escolhido][1]:
                escolhido = metodo  # (o SNR do alternativo já veio descontado de MARGEM_METODO_DB)
        f0, snr, por_roi = resultados[escolhido]
        self._metodo = escolhido
        self._melhor = max(por_roi, key=lambda nome: por_roi[nome][1])
        candidata = snr >= LIMIAR_SNR_CONSISTENTE_DB + _extra_db(60.0 * f0) and fps >= FPS_MINIMO
        concordam = sum(1 for g, s, _, _ in por_roi.values() if candidata and s >= LIMIAR_SNR_CONSISTENTE_DB
                        and abs(g - f0) * 60 <= 5)
        self._registrar(60.0 * f0 if candidata else None, snr, fps, concordam)
        resp_t, _, resp = self._buffer.desde(t - RESP_JANELA_S)
        self._respiracao = _respiracao_rpm(resp_t, resp[:, _COL_INTENSIDADE], resp[:, _COL_NARIZ])
        self._rmssd = None
        base = resultados.get(metodos[0])  # a variabilidade foi calibrada com o POS (ou o canal único)
        if (self._estado == "pronto" and base is not None and fps >= RMSSD_FPS_MIN and base[1] >= RMSSD_SNR_MIN_DB
                and abs(base[0] - f0) * 60 <= CONSISTENCIA_BPM):
            melhor = max(base[2], key=lambda nome: base[2][nome][1])
            self._rmssd = _rmssd_ms(base[2][melhor][3], base[0])

    def _referencia(self) -> float | None:
        """Mediana das últimas janelas acima de LIMIAR_SNR_DB ou, sem nenhuma, o último número mostrado há pouco."""
        fortes = [e[0] for e in self._estimativas if e is not None and e[1] >= LIMIAR_SNR_DB + _extra_db(e[0])]
        return float(np.median(fortes)) if fortes else self._memoria()

    def _memoria(self) -> float | None:
        if self._ultimo_bpm is not None and self._t - self._t_ultimo_bom <= MEMORIA_S:
            return self._ultimo_bpm
        return None

    def _registrar(self, bpm, snr, fps, concordam: int = 0) -> None:
        """Regra para mostrar número: 3 votos perto da referência entre as últimas 5 janelas e 1 das 2 últimas boa.
        Referência = mediana das janelas acima de LIMIAR_SNR_DB (ou, sem nenhuma, o último número mostrado há menos de
        MEMORIA_S). Janela entre LIMIAR_SNR_CONSISTENTE_DB e LIMIAR_SNR_DB só vota se concordar com a referência; o
        último número mostrado também vota se concordar."""
        self._estimativas.append(None if bpm is None else (bpm, snr))
        self._snr = snr
        self._registrado = False
        validas = [e for e in self._estimativas if e is not None]
        fortes = [b for b, s in validas if s >= LIMIAR_SNR_DB + _extra_db(b)]
        memoria = self._memoria()
        referencia = float(np.median(fortes)) if fortes else memoria
        perto, recente = [], False
        if referencia is not None:
            perto = [b for b, _ in validas if abs(b - referencia) <= CONSISTENCIA_BPM]
            recente = any(e is not None and abs(e[0] - referencia) <= CONSISTENCIA_BPM
                          for e in list(self._estimativas)[-RECENTES_N:])
        memoria_vota = memoria is not None and referencia is not None and abs(memoria - referencia) <= CONSISTENCIA_BPM
        votos = len(perto) + (1 if memoria_vota else 0)
        self._votos = votos
        if votos < CONSISTENTES_N or not recente or not perto:
            self._estado, self._bpm, self._confianca = "sinal_fraco", None, 0.0
            return
        # O último número mostrado entra na mediana quando vota: logo depois de perder o sinal, a janela emenda o
        # trecho novo com o de antes (fase quebrada) e o pico escorrega ~3 bpm por alguns segundos (CAR-15).
        bpm_mostrado = round(float(np.median(perto + ([memoria] if memoria_vota else []))), 1)
        # Confiança: SNR (de LIMIAR_SNR_CONSISTENTE_DB a LIMIAR + FAIXA_CONFIANCA_DB) e votos de janelas que concordam
        # (até MEDIANA_N + o último número), vezes a taxa de quadros (0,7 a 10 quadros/s até 1 a 20) e 0,8 se só uma
        # ROI apoia o pico. Abaixo de CONFIANCA_MINIMA, nada de número.
        faixa_snr = LIMIAR_SNR_DB + FAIXA_CONFIANCA_DB - LIMIAR_SNR_CONSISTENTE_DB
        pelo_snr = min(1.0, max(0.0, (snr - LIMIAR_SNR_CONSISTENTE_DB) / faixa_snr)) if snr is not None else 0.0
        pelos_votos = min(1.0, votos / (MEDIANA_N + 1.0))
        pelo_fps = 0.7 + 0.3 * min(1.0, max(0.0, (fps - FPS_MINIMO) / 10.0)) if fps else 1.0
        confianca = round((0.2 + 0.4 * pelo_snr + 0.4 * pelos_votos) * (1.0 if concordam >= 2 else 0.8) * pelo_fps, 3)
        if confianca < CONFIANCA_MINIMA:
            self._estado, self._bpm, self._confianca = "sinal_fraco", None, 0.0
            return
        self._estado, self._bpm, self._confianca = "pronto", bpm_mostrado, confianca

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

    def _andamento(self, estado: str):
        """(progresso 0..1, segundos que faltam). No aquecimento, pelo tempo de dado bom. Depois de perder o número,
        pelo que falta: o trecho bom novo chegar a TRECHO_MIN_S (o POS precisa de 1,6 s) e os votos que faltam (uma
        janela por PASSO_S)."""
        if estado == "pronto":
            return 1.0, 0.0
        if self._duracao < self.aquecimento_s:
            return round(self._duracao / self.aquecimento_s, 4), round(self.aquecimento_s - self._duracao, 1)
        ultimo = self._buffer.ultimo_t
        trecho = 0.0
        if ultimo is not None and self._inicio_segmento is not None and self._t - ultimo <= FRESCO_S:
            trecho = ultimo - self._inicio_segmento
        falta = max(0.0, TRECHO_MIN_S - trecho) + max(0, CONSISTENTES_N - self._votos) * self.passo_s
        falta = max(falta, self.passo_s)  # sem número ainda: pelo menos mais uma janela (ex.: confiança abaixo do piso)
        total = TRECHO_MIN_S + CONSISTENTES_N * self.passo_s
        return round(min(0.99, max(0.0, 1.0 - falta / total)), 4), round(falta, 1)

    def _motivo(self, estado: str, fps: float | None) -> str | None:
        """Por que não há número, só pelo que foi medido (ordem: o que a pessoa pode resolver primeiro)."""
        if estado in ("pronto", "sem_rosto"):
            return None
        if estado == "movimento":
            return "mexendo"
        if self._luz is not None and self._luz < LUZ_MINIMA:
            return "pouca_luz"
        if self._estourado is not None and self._estourado > FRACAO_ESTOURADA_MAX:
            return "luz_estourada"
        if fps is not None and fps < FPS_MINIMO:
            return "camera_lenta"
        if estado == "sinal_fraco":
            return "mexendo" if self._t - self._ultimo_mov <= self.janela_s / 2.0 else "sinal_fraco"
        return None

    def _leitura(self, estado: str, poligonos: dict) -> CardioReading:
        pronto = estado == "pronto"
        if pronto:
            self._ultimo_bpm = self._bpm
            self._t_ultimo_bom = self._t
            if not self._registrado:
                self._historico.append(self._bpm)
                self._registrado = True
        mostra_extra = estado in ("pronto", "sinal_fraco", "medindo")
        fps = self._fps_camera()
        progresso, faltam = self._andamento(estado)
        motivo = self._motivo(estado, fps)
        if estado == "movimento" or motivo == "camera_lenta":
            faltam = None  # parado esperando a pessoa ficar quieta ou a câmera acelerar: não dá para estimar
        return CardioReading(
            estado=estado,
            bpm=self._bpm if pronto else None,
            confianca=self._confianca if pronto else 0.0,
            snr_db=None if self._snr is None else round(self._snr, 2),
            respiracao_rpm=None if self._respiracao is None or not mostra_extra else round(self._respiracao, 1),
            rmssd_ms=None if self._rmssd is None or not pronto else round(self._rmssd, 1),
            progresso=progresso,
            onda=list(self._onda),
            historico_bpm=list(self._historico),
            canal=self._canal,
            rois=poligonos,
            ultimo_bpm=self._ultimo_bpm,
            motivo=motivo,
            fps=None if fps is None else round(fps, 1),
            segundos_para_medida=faltam,
            luminancia=None if self._luz is None else round(self._luz, 1),
            fracao_saturada=None if self._estourado is None else round(self._estourado, 3),
            metodo=self._metodo,
        )
