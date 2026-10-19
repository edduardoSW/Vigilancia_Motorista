// Spec 025 · pulso estimado pela cor da pele (rPPG) no navegador: porte do caixa/vision/cardio.py (spec 022), com os
// mesmos parâmetros e as mesmas regras para mostrar número, para o navegador e a caixa darem a mesma leitura.
// Fica de fora do porte: infravermelho, respiração e variabilidade (experimentais na caixa).
// Função pura, sem imports: o teste roda direto no Node e confere número a número com o Python (camera-rppg.test.mjs).
// Estimativa pela câmera, não é medida médica.

// --- Parâmetros do sinal (cardio.py) ----------------------------------------------------------------------------------
export const FS = 30;
export const BANDA_HZ: [number, number] = [0.7, 3.0]; // 42 a 180 bpm
export const POS_JANELA_S = 1.6;
export const JANELA_S = 10;
export const MINIMO_S = 6;
export const PASSO_S = 1;
export const NFFT_MIN = 2048;
export const MEIA_BANDA_SNR_HZ = 0.2; // gabarito em volta do pico e do 2º harmônico
export const BANDA_SNR_HZ: [number, number] = [BANDA_HZ[0], 2 * BANDA_HZ[1] + MEIA_BANDA_SNR_HZ];
export const LAMBDA_TENDENCIA = 300; // Tarvainen, a 30 Hz
export const LIMIAR_SNR_DB = 0;
export const FAIXA_CONFIANCA_DB = 10;
// --- Regras para mostrar número -----------------------------------------------------------------------------------
export const AQUECIMENTO_S = 15; // dados bons antes do primeiro número; o progresso vai de 0 a 1 aqui
export const FPS_MINIMO = 15;
export const MEDIANA_N = 5;
export const CONSISTENTES_N = 3;
export const RECENTES_N = 2;
export const CONSISTENCIA_BPM = 6;
export const METADE_RAZAO = 0.5;
export const METADE_PROCURA_HZ = 0.1;
// --- Regiões da pele ----------------------------------------------------------------------------------------------
// Testa: testa medial baixa e glabela alta, abaixo da linha do cabelo.
export const ROI_TESTA = [69, 108, 151, 337, 299, 296, 336, 9, 107, 66];
// "esq" e "dir" = lado da IMAGEM sem espelho, como no cardio.py: a "esq" (117...) é a bochecha DIREITA do motorista,
// do lado do ponto 33 (olho direito no face.py).
export const ROI_BOCHECHA_ESQ = [117, 118, 101, 36, 205, 187, 123];
export const ROI_BOCHECHA_DIR = [346, 347, 330, 266, 425, 411, 352];
export const NOMES_DAS_ROIS = ["testa", "bochecha_esq", "bochecha_dir"] as const;
export const ROIS = [ROI_TESTA, ROI_BOCHECHA_ESQ, ROI_BOCHECHA_DIR];
export const CANTOS_OLHOS = [33, 263];
export const PONTE_NARIZ = [6, 168];
// Pixel com algum canal <= 15 (escuro) ou >= 250 (reflexo) sai da média: vale o canal entre 16 e 249.
export const PIXEL_ESCURO = 15;
export const PIXEL_SATURADO = 250;
export const PIXELS_MIN_ROI = 100;
export const RAZAO_BOCHECHAS_MIN = 0.5; // bochecha com menos da metade da área da outra (rosto virado) sai
export const SUAVIZACAO_PONTOS_S = 0.1;
// --- Movimento e falta de rosto -----------------------------------------------------------------------------------
export const LIMIAR_MOVIMENTO = 0.1;
export const JANELA_MOVIMENTO_S = 0.5;
export const SEGURA_MOVIMENTO_S = 0.5;
export const SEM_ROSTO_S = 2;
export const BURACO_MAX_S = 0.5;
export const IDADE_MAX_S = 2 * JANELA_S;
// --- Saída ----------------------------------------------------------------------------------------------------------
export const ONDA_S = 6;
export const ONDA_PASSO_S = 0.1;

const INDICES_ROI = [...new Set([...ROI_TESTA, ...ROI_BOCHECHA_ESQ, ...ROI_BOCHECHA_DIR])].sort((a, b) => a - b);
const INDICES_MOVIMENTO = [...new Set([...INDICES_ROI, ...CANTOS_OLHOS, ...PONTE_NARIZ, 1])].sort((a, b) => a - b);

export type Rgb = [number, number, number];
export type Ponto = { x: number; y: number };

/** round() do Python (metade para o par), para os números baterem com a caixa. */
export function arredondarPython(valor: number, casas = 0): number {
  const fator = 10 ** casas;
  const escalado = valor * fator;
  const piso = Math.floor(escalado);
  const resto = escalado - piso;
  const inteiro = Math.abs(resto - 0.5) < 1e-9 ? (piso % 2 === 0 ? piso : piso + 1) : Math.round(escalado);
  return inteiro / fator;
}

function mediana(valores: readonly number[]): number {
  const ordenados = [...valores].sort((a, b) => a - b);
  const meio = ordenados.length >> 1;
  return ordenados.length % 2 ? ordenados[meio] : (ordenados[meio - 1] + ordenados[meio]) / 2;
}

/** Interpolação linear numa grade uniforme de `fs` Hz, de ts[0] até no máximo ts[fim] (cardio.py reamostrar). */
export function reamostrar(ts: readonly number[], linhas: readonly (readonly number[])[], fs = FS): { grade: number[]; colunas: Float64Array[] } {
  const n = ts.length;
  const canais = linhas[0]?.length ?? 0;
  if (n < 2) return { grade: [...ts], colunas: Array.from({ length: canais }, (_, c) => Float64Array.from(linhas, (linha) => linha[c])) };
  const total = Math.floor((ts[n - 1] - ts[0]) * fs + 1e-9) + 1;
  const grade = new Array<number>(total);
  const colunas = Array.from({ length: canais }, () => new Float64Array(total));
  let j = 0;
  for (let i = 0; i < total; i++) {
    const x = ts[0] + i / fs;
    grade[i] = x;
    while (j < n - 2 && ts[j + 1] <= x) j++;
    for (let c = 0; c < canais; c++) {
      if (x >= ts[n - 1]) colunas[c][i] = linhas[n - 1][c];
      else {
        const inclinacao = (linhas[j + 1][c] - linhas[j][c]) / (ts[j + 1] - ts[j]);
        colunas[c][i] = inclinacao * (x - ts[j]) + linhas[j][c];
      }
    }
  }
  return { grade, colunas };
}

/**
 * POS (Wang et al. 2017, Algoritmo 1): janela de 1,6 s, projeção [[0, 1, -1], [-2, 1, 1]], h = S1 + (σS1/σS2)·S2,
 * soma com sobreposição. Mesma conta do cardio.py (lá em O(N) com somas acumuladas). Desce quando o sangue chega.
 */
export function pos(r: Float64Array, g: Float64Array, b: Float64Array, fs = FS, janelaS = POS_JANELA_S): Float64Array {
  const n = r.length;
  const l = Math.ceil(janelaS * fs);
  const h = new Float64Array(n);
  if (l < 2 || n < l) return h;
  const s1 = new Float64Array(l);
  const s2 = new Float64Array(l);
  for (let fim = l - 1; fim < n; fim++) {
    const inicio = fim - l + 1;
    let mr = 0;
    let mg = 0;
    let mb = 0;
    for (let k = inicio; k <= fim; k++) {
      mr += r[k];
      mg += g[k];
      mb += b[k];
    }
    mr /= l;
    mg /= l;
    mb /= l;
    if (mr <= 0 || mg <= 0 || mb <= 0) continue;
    let q1 = 0;
    let q2 = 0;
    for (let k = 0; k < l; k++) {
      const cr = r[inicio + k] / mr;
      const cg = g[inicio + k] / mg;
      const cb = b[inicio + k] / mb;
      s1[k] = cg - cb;
      s2[k] = -2 * cr + cg + cb;
      q1 += s1[k] * s1[k];
      q2 += s2[k] * s2[k];
    }
    // S1 e S2 têm média zero na janela: o desvio é a raiz da média dos quadrados, e h já sai com média zero.
    const alfa = q2 > 1e-300 ? Math.sqrt(q1 / q2) : 0;
    for (let k = 0; k < l; k++) h[inicio + k] += s1[k] + alfa * s2[k];
  }
  return h;
}

const fatores = new Map<string, [Float64Array, Float64Array, Float64Array]>();

/** Cholesky em banda (diagonal e duas subdiagonais) de I + λ²·D2'D2, guardado por tamanho. */
function fatorDeTendencia(n: number, lam2: number): [Float64Array, Float64Array, Float64Array] {
  const chave = `${n}:${lam2}`;
  const guardado = fatores.get(chave);
  if (guardado) return guardado;
  const diagonal = new Float64Array(n).fill(1);
  const sub1 = new Float64Array(n);
  const sub2 = new Float64Array(n);
  for (let i = 0; i < n - 2; i++) {
    diagonal[i] += lam2;
    diagonal[i + 1] += 4 * lam2;
    diagonal[i + 2] += lam2;
    sub1[i + 1] -= 2 * lam2;
    sub1[i + 2] -= 2 * lam2;
    sub2[i + 2] += lam2;
  }
  const l0 = new Float64Array(n);
  const l1 = new Float64Array(n);
  const l2 = new Float64Array(n);
  for (let i = 0; i < n; i++) {
    const a2 = i >= 2 ? sub2[i] / l0[i - 2] : 0;
    const a1 = i >= 1 ? (sub1[i] - a2 * l1[i - 1]) / l0[i - 1] : 0;
    l0[i] = Math.sqrt(diagonal[i] - a1 * a1 - a2 * a2);
    l1[i] = a1;
    l2[i] = a2;
  }
  if (fatores.size > 64) fatores.delete(fatores.keys().next().value as string);
  const fator: [Float64Array, Float64Array, Float64Array] = [l0, l1, l2];
  fatores.set(chave, fator);
  return fator;
}

/** Tarvainen et al. 2002: x - (I + λ²·D2'D2)⁻¹·x, com λ = 300 a 30 Hz (corte em ~0,34 Hz). */
export function removerTendencia(x: ArrayLike<number>, fs = FS, lam = LAMBDA_TENDENCIA): Float64Array {
  const n = x.length;
  const saida = Float64Array.from(x);
  if (n < 4) {
    const media = n ? saida.reduce((a, b) => a + b, 0) / n : 0;
    return saida.map((v) => v - media);
  }
  const lamFs = lam * (fs / FS) ** 2;
  const [l0, l1, l2] = fatorDeTendencia(n, arredondarPython(lamFs * lamFs, 6));
  const y = new Float64Array(n);
  for (let i = 0; i < n; i++) {
    let s = saida[i];
    if (i >= 1) {
      s -= l1[i] * y[i - 1];
      if (i >= 2) s -= l2[i] * y[i - 2];
    }
    y[i] = s / l0[i];
  }
  const tendencia = new Float64Array(n);
  for (let i = n - 1; i >= 0; i--) {
    let s = y[i];
    if (i + 1 < n) {
      s -= l1[i + 1] * tendencia[i + 1];
      if (i + 2 < n) s -= l2[i + 2] * tendencia[i + 2];
    }
    tendencia[i] = s / l0[i];
  }
  for (let i = 0; i < n; i++) saida[i] -= tendencia[i];
  return saida;
}

function semReta(x: ArrayLike<number>): Float64Array {
  const n = x.length;
  let media = 0;
  for (let i = 0; i < n; i++) media += x[i];
  media /= n;
  let num = 0;
  let den = 0;
  for (let i = 0; i < n; i++) {
    const eixo = i - (n - 1) / 2;
    num += eixo * x[i];
    den += eixo * eixo;
  }
  const inclinacao = den ? num / den : 0;
  return Float64Array.from(x, (valor, i) => valor - media - inclinacao * (i - (n - 1) / 2));
}

/** Passa-faixa ideal por transformada de Fourier do tamanho do sinal (zera fora da banda), sem a reta antes. */
export function passaFaixa(x: ArrayLike<number>, fs = FS, banda: [number, number] = BANDA_HZ): Float64Array {
  const n = x.length;
  const saida = new Float64Array(n);
  if (n < 4) return saida;
  const limpo = semReta(x);
  for (let k = 1; k <= n >> 1; k++) {
    const f = (k * fs) / n;
    if (f < banda[0] || f > banda[1]) continue;
    let re = 0;
    let im = 0;
    for (let j = 0; j < n; j++) {
      const angulo = (-2 * Math.PI * k * j) / n;
      re += limpo[j] * Math.cos(angulo);
      im += limpo[j] * Math.sin(angulo);
    }
    const peso = k * 2 === n ? 1 : 2; // o bin de Nyquist aparece uma vez só
    for (let j = 0; j < n; j++) {
      const angulo = (2 * Math.PI * k * j) / n;
      saida[j] += (peso * (re * Math.cos(angulo) - (k * 2 === n ? 0 : im * Math.sin(angulo)))) / n;
    }
  }
  return saida;
}

/** FFT radix-2 iterativa, no próprio vetor (re.length tem que ser potência de 2). */
export function fft(re: Float64Array, im: Float64Array): void {
  const n = re.length;
  for (let i = 1, j = 0; i < n; i++) {
    let bit = n >> 1;
    for (; j & bit; bit >>= 1) j ^= bit;
    j ^= bit;
    if (i < j) {
      [re[i], re[j]] = [re[j], re[i]];
      [im[i], im[j]] = [im[j], im[i]];
    }
  }
  for (let tamanho = 2; tamanho <= n; tamanho <<= 1) {
    const angulo = (-2 * Math.PI) / tamanho;
    const metade = tamanho / 2;
    for (let i = 0; i < n; i += tamanho) {
      for (let k = 0; k < metade; k++) {
        const cr = Math.cos(angulo * k);
        const ci = Math.sin(angulo * k);
        const ar = re[i + k + metade] * cr - im[i + k + metade] * ci;
        const ai = re[i + k + metade] * ci + im[i + k + metade] * cr;
        re[i + k + metade] = re[i + k] - ar;
        im[i + k + metade] = im[i + k] - ai;
        re[i + k] += ar;
        im[i + k] += ai;
      }
    }
  }
}

/** Periodograma com Hann e zero-padding (no mínimo 2048 pontos), como o cardio.py espectro. */
export function espectro(x: ArrayLike<number>, fs = FS, nfftMin = NFFT_MIN): { freqs: Float64Array; potencia: Float64Array } {
  const n = x.length;
  let media = 0;
  for (let i = 0; i < n; i++) media += x[i];
  media /= Math.max(1, n);
  let nfft = 2;
  while (nfft < n) nfft <<= 1;
  nfft = Math.max(nfftMin, nfft);
  const re = new Float64Array(nfft);
  const im = new Float64Array(nfft);
  for (let i = 0; i < n; i++) re[i] = (x[i] - media) * (n > 1 ? 0.5 - 0.5 * Math.cos((2 * Math.PI * i) / (n - 1)) : 1);
  fft(re, im);
  const potencia = new Float64Array(nfft / 2 + 1);
  const freqs = new Float64Array(nfft / 2 + 1);
  for (let k = 0; k < potencia.length; k++) {
    potencia[k] = re[k] * re[k] + im[k] * im[k];
    freqs[k] = (k * fs) / nfft;
  }
  return { freqs, potencia };
}

function parabolico(f: Float64Array, p: Float64Array, i: number): number {
  if (i > 0 && i < p.length - 1) {
    const a = p[i - 1];
    const b = p[i];
    const c = p[i + 1];
    const denominador = a - 2 * b + c;
    if (denominador < 0) return f[i] + Math.min(0.5, Math.max(-0.5, (0.5 * (a - c)) / denominador)) * (f[1] - f[0]);
  }
  return f[i];
}

function snrDb(f: Float64Array, p: Float64Array, f0: number, meia: number, faixa: [number, number]): number {
  let sinal = 0;
  let ruido = 0;
  for (let k = 0; k < f.length; k++) {
    if (f[k] < faixa[0] || f[k] > faixa[1]) continue;
    if (Math.abs(f[k] - f0) <= meia || Math.abs(f[k] - 2 * f0) <= meia) sinal += p[k];
    else ruido += p[k];
  }
  if (sinal <= 0) return -60;
  if (ruido <= 0) return 60;
  return Math.min(60, Math.max(-60, 10 * Math.log10(sinal / ruido)));
}

/** Pico em 0,7 a 3 Hz (parábola) e SNR; se houver pico em f/2 com 50% da potência ou mais, fica f/2. */
export function picoESnr(f: Float64Array, p: Float64Array): { hz: number; snrDb: number } | null {
  let i = -1;
  for (let k = 0; k < f.length; k++) if (f[k] >= BANDA_HZ[0] && f[k] <= BANDA_HZ[1] && (i < 0 || p[k] > p[i])) i = k;
  if (i < 0 || p[i] <= 0) return null;
  const metade = f[i] / 2;
  if (metade >= BANDA_HZ[0]) {
    let j = -1;
    for (let k = 0; k < f.length; k++) {
      if (f[k] < BANDA_HZ[0] || f[k] > BANDA_HZ[1] || Math.abs(f[k] - metade) > METADE_PROCURA_HZ) continue;
      if (j < 0 || p[k] > p[j]) j = k;
    }
    if (j >= 0 && p[j] >= METADE_RAZAO * p[i] && j > 0 && j < p.length - 1 && p[j] >= p[j - 1] && p[j] >= p[j + 1]) i = j;
  }
  const hz = parabolico(f, p, i);
  return { hz, snrDb: snrDb(f, p, hz, MEIA_BANDA_SNR_HZ, BANDA_SNR_HZ) };
}

/** (bpm, SNR) de um sinal de pulso uniforme: tira a tendência, espectro com Hann e pico em 42 a 180 bpm. */
export function estimarBpm(sinal: ArrayLike<number>, fs = FS): { bpm: number; snrDb: number } | null {
  const { freqs, potencia } = espectro(removerTendencia(sinal, fs), fs);
  const pico = picoESnr(freqs, potencia);
  return pico ? { bpm: 60 * pico.hz, snrDb: pico.snrDb } : null;
}

/** Área do polígono (fórmula do laço), em pixels, como o cv2.contourArea. */
export function areaDoPoligono(pontos: readonly Ponto[]): number {
  let soma = 0;
  for (let i = 0; i < pontos.length; i++) {
    const a = pontos[i];
    const b = pontos[(i + 1) % pontos.length];
    soma += a.x * b.y - b.x * a.y;
  }
  return Math.abs(soma) / 2;
}

/** Quais regiões entram: bochecha com menos da metade da área da outra (rosto virado) sai. */
export function regioesUsaveis(poligonos: readonly (readonly Ponto[])[]): boolean[] {
  const esquerda = areaDoPoligono(poligonos[1]);
  const direita = areaDoPoligono(poligonos[2]);
  const maior = Math.max(esquerda, direita);
  return [true, maior > 0 && esquerda >= RAZAO_BOCHECHAS_MIN * maior, maior > 0 && direita >= RAZAO_BOCHECHAS_MIN * maior];
}

export type EstadoDoPulso = "sem_rosto" | "medindo" | "pronto" | "sinal_fraco" | "movimento";

export type LeituraDoPulso = {
  estado: EstadoDoPulso;
  bpm: number | null;
  /** 0 a 1. */
  confianca: number;
  snrDb: number | null;
  /** 0 a 1 até o primeiro número (aquecimento de 15 s). */
  progresso: number;
  /** Últimos ~6 s normalizados entre -1 e 1, a 30 Hz; sobe na sístole. */
  onda: readonly number[];
  /** Último número bom, para mostrar apagado com movimento ou sinal fraco. */
  ultimoBpm: number | null;
};

type Linha = { t: number; segmento: number; medias: (Rgb | null)[] };

function trechos(ts: readonly number[], segmentos: readonly number[]): [number, number][] {
  if (!ts.length) return [];
  const limites = [0];
  for (let i = 1; i < ts.length; i++) if (segmentos[i] !== segmentos[i - 1] || ts[i] - ts[i - 1] > BURACO_MAX_S) limites.push(i);
  limites.push(ts.length);
  return limites.slice(0, -1).map((inicio, k) => [inicio, limites[k + 1]]);
}

/** Pulso dos trechos mais recentes até somar `duracao`, cada trecho com o seu POS (cardio.py _pulso_emendado). */
function pulsoEmendado(ts: number[], cores: Rgb[], segmentos: number[], duracao: number) {
  const partes: Float64Array[] = [];
  let total = 0;
  let ultimo: Float64Array | null = null;
  const minimo = Math.ceil(POS_JANELA_S * FS) + 1;
  for (const [inicio, fim] of trechos(ts, segmentos).reverse()) {
    if (total >= duracao - 0.5 / FS) break;
    if (fim - inicio < 3) continue;
    const { colunas } = reamostrar(ts.slice(inicio, fim), cores.slice(inicio, fim), FS);
    if (colunas[0].length < minimo) continue;
    const h = pos(colunas[0], colunas[1], colunas[2], FS);
    ultimo ??= h;
    const manter = Math.min(h.length, arredondarPython((duracao - total) * FS));
    partes.push(h.subarray(h.length - manter));
    total += manter / FS;
  }
  if (!partes.length) return null;
  const pulso = new Float64Array(partes.reduce((soma, parte) => soma + parte.length, 0));
  let posicao = 0;
  for (const parte of partes.reverse()) {
    pulso.set(parte, posicao);
    posicao += parte.length;
  }
  return { pulso, total, ultimo };
}

/**
 * O CardioMonitor do Python sem infravermelho, respiração e variabilidade: uma chamada por quadro (médias das regiões
 * já medidas na tela), estimativa 1 vez por segundo depois de 6 s e número só depois de 15 s de dados bons, com 15
 * quadros por segundo ou mais e 3 das últimas 5 estimativas perto da mediana.
 */
export class MonitorDoPulso {
  private linhas: Linha[] = [];
  private segmento = 0;
  private quebrar = true;
  private duracao = 0;
  private movimentos: { t: number; pontos: Ponto[] }[] = [];
  private movendoAte = -Infinity;
  private suaves: Ponto[] | null = null;
  private tSuave: number | null = null;
  private estimativas: (number | null)[] = [];
  private proximo = -Infinity;
  private estado: EstadoDoPulso = "medindo";
  private bpm: number | null = null;
  private snr: number | null = null;
  private confianca = 0;
  private onda: readonly number[] = [];
  private proximaOnda = -Infinity;
  private melhor = 0;
  private ultimoBpm: number | null = null;
  private visto: number | null = null;

  private limpar(): void {
    this.linhas = [];
    this.segmento = 0;
    this.quebrar = true;
    this.duracao = 0;
    this.movimentos = [];
    this.movendoAte = -Infinity;
    this.suaves = null;
    this.tSuave = null;
    this.estimativas = [];
    this.proximo = -Infinity;
    this.estado = "medindo";
    this.bpm = null;
    this.snr = null;
    this.confianca = 0;
    this.onda = [];
    this.proximaOnda = -Infinity;
    this.melhor = 0;
  }

  /** Média exponencial dos vértices das regiões (redetectar a cada quadro piora o sinal). Chamar antes de medir. */
  suavizar(t: number, pontos: readonly Ponto[]): Ponto[] {
    const atuais = INDICES_ROI.map((indice) => ({ x: pontos[indice].x, y: pontos[indice].y }));
    if (!this.suaves || this.tSuave === null || !(t - this.tSuave > 0 && t - this.tSuave <= BURACO_MAX_S)) this.suaves = atuais;
    else {
      const alfa = 1 - Math.exp(-(t - this.tSuave) / SUAVIZACAO_PONTOS_S);
      this.suaves = this.suaves.map((ponto, k) => ({ x: ponto.x + alfa * (atuais[k].x - ponto.x), y: ponto.y + alfa * (atuais[k].y - ponto.y) }));
    }
    this.tSuave = t;
    const saida = [...pontos];
    INDICES_ROI.forEach((indice, k) => (saida[indice] = this.suaves![k]));
    return saida;
  }

  /** `quadro` null = sem rosto. `medias`: R, G, B da testa, bochecha esq e bochecha dir (lado da imagem), ou null. */
  atualizar(t: number, quadro: { pontos: readonly Ponto[]; medias: (Rgb | null)[] } | null): LeituraDoPulso {
    if (!quadro) return this.semRosto(t);
    if (this.visto !== null && t - this.visto > BURACO_MAX_S) this.quebrar = true;
    this.visto = t;
    if (this.movimento(t, quadro.pontos)) {
      this.quebrar = true;
      return this.leitura("movimento");
    }
    if (quadro.medias.every((media) => media === null) || !this.acrescentar(t, quadro.medias)) {
      this.quebrar = true;
      return this.leitura(this.estadoAtual());
    }
    if (t >= this.proximo && this.duracao >= MINIMO_S - 1e-6) {
      this.proximo = t + PASSO_S - 1e-6;
      this.estimar(t);
    }
    this.atualizarOnda(t);
    return this.leitura(this.estadoAtual());
  }

  private semRosto(t: number): LeituraDoPulso {
    if (this.visto === null || t - this.visto >= SEM_ROSTO_S) {
      if (this.linhas.length || this.duracao || this.ultimoBpm !== null) {
        this.limpar();
        this.ultimoBpm = null;
      }
      this.visto = null;
      return { estado: "sem_rosto", bpm: null, confianca: 0, snrDb: null, progresso: 0, onda: [], ultimoBpm: null };
    }
    this.quebrar = true; // o rosto sumiu por pouco: mantém a última leitura, sem medir
    return this.leitura(this.estadoAtual());
  }

  private movimento(t: number, pontos: readonly Ponto[]): boolean {
    const [a, b] = CANTOS_OLHOS.map((indice) => pontos[indice]);
    const olhos = Math.hypot(a.x - b.x, a.y - b.y);
    const atuais = INDICES_MOVIMENTO.map((indice) => pontos[indice]);
    while (this.movimentos.length && t - this.movimentos[0].t > JANELA_MOVIMENTO_S) this.movimentos.shift();
    if (this.movimentos.length && olhos > 1) {
      const antes = this.movimentos[0].pontos;
      const deslocamento = atuais.reduce((soma, ponto, k) => soma + Math.hypot(ponto.x - antes[k].x, ponto.y - antes[k].y), 0) / atuais.length / olhos;
      if (deslocamento > LIMIAR_MOVIMENTO) this.movendoAte = t + SEGURA_MOVIMENTO_S;
    }
    this.movimentos.push({ t, pontos: atuais });
    return t < this.movendoAte;
  }

  private acrescentar(t: number, medias: (Rgb | null)[]): boolean {
    const anterior = this.linhas.at(-1)?.t ?? null;
    if (anterior !== null && t <= anterior) return false; // horário repetido ou voltando
    if (this.quebrar || anterior === null || t - anterior > BURACO_MAX_S) {
      this.segmento++;
      this.quebrar = false;
    } else {
      this.duracao += t - anterior;
    }
    this.linhas.push({ t, segmento: this.segmento, medias: [...medias] });
    while (this.linhas.length && this.linhas[0].t < t - IDADE_MAX_S) this.linhas.shift();
    return true;
  }

  private colunasDaRegiao(k: number, desde: number) {
    const ts: number[] = [];
    const cores: Rgb[] = [];
    const segmentos: number[] = [];
    for (const linha of this.linhas) {
      const cor = linha.medias[k];
      if (linha.t < desde || !cor) continue;
      ts.push(linha.t);
      cores.push(cor);
      segmentos.push(linha.segmento);
    }
    return { ts, cores, segmentos };
  }

  private quadrosPorSegundo(desde: number): number {
    const linhas = this.linhas.filter((linha) => linha.t >= desde);
    const intervalos: number[] = [];
    for (let i = 1; i < linhas.length; i++) {
      const dt = linhas[i].t - linhas[i - 1].t;
      if (linhas[i].segmento === linhas[i - 1].segmento && dt <= BURACO_MAX_S) intervalos.push(dt);
    }
    return intervalos.length ? 1 / mediana(intervalos) : 0;
  }

  private estimar(t: number): void {
    const desde = t - IDADE_MAX_S;
    const porRegiao: { k: number; hz: number; snr: number; potencia: Float64Array }[] = [];
    let freqs: Float64Array | null = null;
    for (let k = 0; k < ROIS.length; k++) {
      const { ts, cores, segmentos } = this.colunasDaRegiao(k, desde);
      if (ts.length < 3) continue;
      const emendado = pulsoEmendado(ts, cores, segmentos, JANELA_S);
      if (!emendado || emendado.total < 0.8 * MINIMO_S) continue;
      const { freqs: f, potencia } = espectro(removerTendencia(emendado.pulso), FS);
      const pico = picoESnr(f, potencia);
      if (pico) {
        freqs = f;
        porRegiao.push({ k, hz: pico.hz, snr: pico.snrDb, potencia });
      }
    }
    if (!porRegiao.length || !freqs) {
      this.registrar(null, null, null, 0);
      return;
    }
    // Combinação ponderada pelo SNR: soma dos espectros normalizados com peso 10^(SNR/10).
    const combinado = new Float64Array(freqs.length);
    for (const regiao of porRegiao) {
      let soma = 0;
      for (let i = 0; i < freqs.length; i++) if (freqs[i] >= BANDA_SNR_HZ[0] && freqs[i] <= BANDA_SNR_HZ[1]) soma += regiao.potencia[i];
      const peso = 10 ** (regiao.snr / 10) / Math.max(soma, 1e-300);
      for (let i = 0; i < freqs.length; i++) combinado[i] += peso * regiao.potencia[i];
    }
    const pico = picoESnr(freqs, combinado);
    this.melhor = porRegiao.reduce((melhor, regiao) => (regiao.snr > melhor.snr ? regiao : melhor)).k;
    const fps = this.quadrosPorSegundo(desde);
    const bom = pico !== null && pico.snrDb >= LIMIAR_SNR_DB && fps >= FPS_MINIMO;
    const concordam = bom ? porRegiao.filter((regiao) => regiao.snr >= LIMIAR_SNR_DB && Math.abs(regiao.hz - pico!.hz) * 60 <= 5).length : 0;
    this.registrar(bom ? 60 * pico!.hz : null, pico?.snrDb ?? null, fps, concordam);
  }

  private registrar(bpm: number | null, snr: number | null, fps: number | null, concordam: number): void {
    this.estimativas.push(bpm);
    if (this.estimativas.length > MEDIANA_N) this.estimativas.shift();
    this.snr = snr;
    const aceitas = this.estimativas.filter((valor): valor is number => valor !== null);
    let perto: number[] = [];
    if (this.estimativas.slice(-RECENTES_N).some((valor) => valor !== null)) {
      const centro = mediana(aceitas);
      perto = aceitas.filter((valor) => Math.abs(valor - centro) <= CONSISTENCIA_BPM);
    }
    if (perto.length < CONSISTENTES_N) {
      this.estado = "sinal_fraco";
      this.bpm = null;
      this.confianca = 0;
      return;
    }
    this.estado = "pronto";
    this.bpm = arredondarPython(mediana(perto), 1);
    const peloSnr = snr !== null ? Math.min(1, Math.max(0, (snr - LIMIAR_SNR_DB) / FAIXA_CONFIANCA_DB)) : 0;
    const peloFps = fps ? Math.min(1, fps / 25) : 1;
    this.confianca = arredondarPython((0.25 + 0.75 * peloSnr) * (concordam >= 2 ? 1 : 0.8) * peloFps, 3);
  }

  private atualizarOnda(t: number): void {
    if (this.duracao < 2 || t < this.proximaOnda) return;
    this.proximaOnda = t + ONDA_PASSO_S - 1e-6;
    const { ts, cores, segmentos } = this.colunasDaRegiao(this.melhor, t - ONDA_S - POS_JANELA_S - 1);
    if (ts.length < 3) return;
    const emendado = pulsoEmendado(ts, cores, segmentos, ONDA_S);
    if (!emendado || emendado.pulso.length < 8) return;
    const onda = passaFaixa(emendado.pulso, FS).map((valor) => -valor); // sístole para cima
    let maximo = 0;
    for (const valor of onda) maximo = Math.max(maximo, Math.abs(valor));
    this.onda = Array.from(onda, (valor) => arredondarPython(maximo > 0 ? valor / maximo : valor, 4));
  }

  private estadoAtual(): EstadoDoPulso {
    return this.duracao < AQUECIMENTO_S ? "medindo" : this.estado;
  }

  private leitura(estado: EstadoDoPulso): LeituraDoPulso {
    const pronto = estado === "pronto";
    if (pronto) this.ultimoBpm = this.bpm;
    return {
      estado,
      bpm: pronto ? this.bpm : null,
      confianca: pronto ? this.confianca : 0,
      snrDb: this.snr === null ? null : arredondarPython(this.snr, 2),
      progresso: this.duracao >= AQUECIMENTO_S ? 1 : arredondarPython(this.duracao / AQUECIMENTO_S, 4),
      onda: this.onda, // a mesma lista até a próxima onda (10 vezes por segundo): a tela só redesenha quando muda
      ultimoBpm: this.ultimoBpm,
    };
  }
}
