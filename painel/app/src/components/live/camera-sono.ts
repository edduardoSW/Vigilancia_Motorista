// Spec 025 · sinais de sono do teste no navegador, com os mesmos limiares do Python (caixa/vision/face.py, eyes.py,
// calibration.py e drowsiness.py). A caixa continua sendo a referência. Sem imports e só com sintaxe que o Node apaga
// sozinho: o teste roda direto (node --test).

// eyes.py
export const P80_OPENNESS = 0.2;
export const BLINK_START_OPENNESS = 0.5;
export const BLINK_END_OPENNESS = 0.6;
export const MAX_FRAME_GAP_S = 0.5;
export const MIN_EYE_DISTANCE_PX = 30;
export const MIN_SIGNAL_SPAN = 0.15;
// calibration.py
export const SHORT_CLOSURE_S = 0.25;
export const MAX_BLINK_S = 1.0;
export const COMPLETE_BLINK_OPENNESS = 0.4;
// drowsiness.py
export const MICROSLEEP_S = 1.0;
export const SLEEP_S = 3.0;
export const UNRESPONSIVE_S = 6.0;
export const PERCLOS_MIN_VALID_FRACTION = 0.5;
export const ALERT_PERCLOS = 0.12;
export const MIN_FPS_FOR_DURATION = 24;
export const YAWN_MIN_S = 2.0;
export const YAWN_JAW_MIN = 0.45;
export const YAWN_JAW_ABOVE_BASELINE = 0.3;
export const NOD_MIN_DEG = 15;
export const NOD_NEAR_REFERENCE_DEG = 5;
export const NOD_RECOVERED_DEG = 7;
export const NOD_MAX_FALL_S = 1.0;
export const NOD_MIN_DOWN_S = 0.3;
export const NOD_MAX_DOWN_S = 3.0;
export const NOD_REFERENCE_S = 10;
export const NOD_REFERENCE_STEP_S = 0.2;
export const NOD_RECENT_S = 1.5;
// face.py
export const EYE_WIDTH_RATIO_FOR_SINGLE_EYE = 0.7;
// Só do teste no navegador: linha do tempo da sessão.
export const SEM_ROSTO_EVENTO_S = 2;
export const PERCLOS_REARMA = 0.1;
export const JANELA_PISCADAS_S = 60;
export const PISCADAS_MIN_S = 10;

// face.py: 6 pontos por olho (Soukupová e Čech, 2016), na ordem p1..p6.
export const RIGHT_EYE = [33, 160, 158, 133, 153, 144];
export const LEFT_EYE = [362, 385, 387, 263, 373, 380];

export type Ponto = { x: number; y: number };

const distancia = (a: Ponto, b: Ponto) => Math.hypot(a.x - b.x, a.y - b.y);

/** Largura do olho (canto a canto), em pixels. */
export function larguraDoOlho(pontos: readonly Ponto[], indices: readonly number[]): number {
  return distancia(pontos[indices[0]], pontos[indices[3]]);
}

/** EAR em PIXELS (x × largura, y × altura do vídeo): em coordenadas normalizadas ele distorce com a proporção. */
export function ear(pontos: readonly Ponto[], indices: readonly number[]): number | null {
  const p = indices.map((indice) => pontos[indice]);
  const largura = distancia(p[0], p[3]);
  if (largura < 1e-6) return null;
  return (distancia(p[1], p[5]) + distancia(p[2], p[4])) / (2 * largura);
}

/** face.py combine_eyes: média dos dois olhos, ou só o mais visível quando a cabeça está virada. */
export function combinarOlhos(esquerdo: number | null, direito: number | null, larguraEsquerdo: number, larguraDireito: number): number | null {
  if (esquerdo === null || direito === null) return direito === null ? esquerdo : direito;
  const maior = Math.max(larguraEsquerdo, larguraDireito);
  const menor = Math.min(larguraEsquerdo, larguraDireito);
  if (maior > 0 && menor / maior < EYE_WIDTH_RATIO_FOR_SINGLE_EYE) return larguraEsquerdo >= larguraDireito ? esquerdo : direito;
  return (esquerdo + direito) / 2;
}

/** Pitch, yaw e roll em graus (face.py rotation_to_euler). O MediaPipe entrega a matriz 4×4 em coluna. */
export function eulerDaMatriz(dados: ArrayLike<number>, colunaMaior = true): { pitch: number; yaw: number; roll: number } {
  const m = (linha: number, coluna: number) => (colunaMaior ? dados[coluna * 4 + linha] : dados[linha * 4 + coluna]);
  const grau = 180 / Math.PI;
  return {
    pitch: Math.atan2(m(2, 1), m(2, 2)) * grau,
    yaw: Math.atan2(-m(2, 0), Math.hypot(m(2, 1), m(2, 2))) * grau,
    roll: Math.atan2(m(1, 0), m(0, 0)) * grau,
  };
}

function mediana(valores: readonly number[]): number {
  const ordenados = [...valores].sort((a, b) => a - b);
  const meio = ordenados.length >> 1;
  return ordenados.length % 2 ? ordenados[meio] : (ordenados[meio - 1] + ordenados[meio]) / 2;
}

function escalado(valor: number, aberto: number | null, fechado: number | null): number | null {
  if (aberto === null || fechado === null || Math.abs(aberto - fechado) < MIN_SIGNAL_SPAN) return null;
  return (valor - fechado) / (aberto - fechado);
}

export type SinaisDoOlho = { ear: number | null; piscada: number | null; distanciaOlhosPx: number | null };

/**
 * Abertura relativa (1 = aberto habitual da pessoa, 0 = fechado) sem calibração, como o OpennessModel do Python sem
 * perfil: EAR aberto = mediana dos últimos 600 EAR com a piscada abaixo de 0,3, fechado = 30% disso; a pontuação de
 * piscada do MediaPipe vira o segundo sinal. Com os dois, vale o maior: os dois precisam concordar que o olho fechou.
 */
export class ModeloDeAbertura {
  private ears: number[] = [];
  private pontuacoes: number[] = [];

  get aprendendo(): boolean {
    return this.ears.length < 30 && this.pontuacoes.length < 30;
  }

  abertura({ ear: earAtual, piscada, distanciaOlhosPx }: SinaisDoOlho): number | null {
    if (distanciaOlhosPx !== null && distanciaOlhosPx < MIN_EYE_DISTANCE_PX) return null;
    if (earAtual !== null && (piscada === null || piscada < 0.3)) {
      this.ears.push(earAtual);
      if (this.ears.length > 600) this.ears.shift();
    }
    if (piscada !== null) {
      this.pontuacoes.push(piscada);
      if (this.pontuacoes.length > 600) this.pontuacoes.shift();
    }
    const sinais: number[] = [];
    if (earAtual !== null && this.ears.length >= 30) {
      const aberto = mediana(this.ears);
      const fechado = 0.3 * aberto;
      sinais.push((earAtual - fechado) / Math.max(aberto - fechado, 1e-6));
    }
    if (piscada !== null && this.pontuacoes.length >= 30) {
      const aberto = mediana(this.pontuacoes);
      const valor = escalado(piscada, aberto, Math.min(1, aberto + 0.5));
      if (valor !== null) sinais.push(valor);
    }
    if (sinais.length === 0) return null;
    return Math.max(0, Math.min(Math.max(...sinais), 1.5));
  }
}

function cruzamento(t0: number | null, o0: number | null, t1: number, o1: number, nivel: number): number {
  if (t0 === null || o0 === null || o0 === o1) return t1;
  const fracao = (nivel - o0) / (o1 - o0);
  return fracao >= 0 && fracao <= 1 ? t0 + fracao * (t1 - t0) : t1;
}

export type Piscada = { inicio: number; fim: number; duracao: number; fechadoPor: number; minimo: number };

/** Piscadas e fechamentos (eyes.py EyeStateTracker), sem as velocidades da pálpebra. */
export class EstadoDoOlho {
  private ultimoT: number | null = null;
  private ultimaAbertura: number | null = null;
  private inicioPiscada: number | null = null;
  private inicioFechado: number | null = null;
  private fechadoTotal = 0;
  private minimo = 1;

  /** Há quanto tempo o olho está continuamente pelo menos 80% fechado. */
  get fechadoHa(): number {
    if (this.inicioFechado === null || this.ultimoT === null) return 0;
    return Math.max(0, this.ultimoT - this.inicioFechado);
  }

  private zerar(): void {
    this.ultimoT = this.ultimaAbertura = this.inicioPiscada = this.inicioFechado = null;
    this.fechadoTotal = 0;
    this.minimo = 1;
  }

  atualizar(t: number, abertura: number | null): Piscada | null {
    if (abertura === null) {
      if (this.ultimoT !== null && t - this.ultimoT > MAX_FRAME_GAP_S) this.zerar();
      return null;
    }
    let tAnterior = this.ultimoT;
    let aberturaAnterior = this.ultimaAbertura;
    if (tAnterior !== null && t - tAnterior > MAX_FRAME_GAP_S) {
      this.zerar();
      tAnterior = aberturaAnterior = null;
    }
    let terminou: Piscada | null = null;
    if (this.inicioPiscada === null && abertura < BLINK_START_OPENNESS) {
      this.inicioPiscada = cruzamento(tAnterior, aberturaAnterior, t, abertura, BLINK_START_OPENNESS);
      this.minimo = abertura;
    }
    if (this.inicioPiscada !== null) {
      this.minimo = Math.min(this.minimo, abertura);
      if (abertura <= P80_OPENNESS && this.inicioFechado === null) {
        this.inicioFechado = cruzamento(tAnterior, aberturaAnterior, t, abertura, P80_OPENNESS);
      } else if (abertura > P80_OPENNESS && this.inicioFechado !== null) {
        this.fechadoTotal += cruzamento(tAnterior, aberturaAnterior, t, abertura, P80_OPENNESS) - this.inicioFechado;
        this.inicioFechado = null;
      }
      if (abertura > BLINK_END_OPENNESS) {
        const fim = cruzamento(tAnterior, aberturaAnterior, t, abertura, BLINK_END_OPENNESS);
        terminou = {
          inicio: this.inicioPiscada,
          fim,
          duracao: Math.max(0, fim - this.inicioPiscada),
          fechadoPor: Math.max(0, this.fechadoTotal),
          minimo: this.minimo,
        };
        this.inicioPiscada = null;
        this.fechadoTotal = 0;
        this.minimo = 1;
      }
    }
    this.ultimoT = t;
    this.ultimaAbertura = abertura;
    return terminou;
  }
}

/** PERCLOS P80 ponderado por tempo, em baldes de 1 s (drowsiness.py PerclosWindow). */
export class Perclos {
  private baldes: [number, number, number][] = []; // [segundo, válido, fechado]

  private balde(t: number): [number, number, number] {
    const segundo = Math.floor(t);
    const ultimo = this.baldes[this.baldes.length - 1];
    if (!ultimo || ultimo[0] !== segundo) {
      this.baldes.push([segundo, 0, 0]);
      while (this.baldes.length && this.baldes[0][0] < segundo - 900) this.baldes.shift();
    }
    return this.baldes[this.baldes.length - 1];
  }

  valido(t: number, dt: number): void {
    if (dt > 0) this.balde(t)[1] += dt;
  }

  fechado(t: number, dt: number): void {
    if (dt > 0) this.balde(t)[2] += dt;
  }

  valor(agora: number, janela: number): number | null {
    let valido = 0;
    let fechado = 0;
    for (let i = this.baldes.length - 1; i >= 0; i--) {
      const [segundo, v, f] = this.baldes[i];
      if (segundo < agora - janela) break;
      valido += v;
      fechado += f;
    }
    if (valido < janela * PERCLOS_MIN_VALID_FRACTION) return null;
    return Math.min(1, fechado / valido);
  }
}

/** Cabeceio pelo pitch (positivo = cabeça baixa), referência móvel de 10 s (drowsiness.py NodTracker). */
export class Cabeceio {
  private recentes: [number, number][] = [];
  private referencia: [number, number][] = [];
  private proximaReferencia = -Infinity;
  private baixoDesde: number | null = null;
  private caiuRapido = false;
  private esperandoVolta = false;

  /** Devolve o cabeceio que acabou de terminar (início e tempo com a cabeça baixa), ou null. */
  atualizar(t: number, pitch: number | null): { inicio: number; duracao: number } | null {
    if (pitch === null) {
      this.recentes = [];
      this.baixoDesde = null;
      this.esperandoVolta = false;
      return null;
    }
    if (!this.referencia.length) {
      this.guardarReferencia(t, pitch);
      this.lembrar(t, pitch);
      return null;
    }
    const referencia = mediana(this.referencia.map(([, valor]) => valor));
    const desvio = pitch - referencia;
    let cabeceio: { inicio: number; duracao: number } | null = null;
    if (this.esperandoVolta) {
      this.esperandoVolta = desvio > NOD_RECOVERED_DEG;
    } else if (this.baixoDesde === null) {
      if (desvio >= NOD_MIN_DEG) {
        const perto = this.recentes.filter(([, valor]) => valor - referencia <= NOD_NEAR_REFERENCE_DEG);
        this.baixoDesde = t;
        this.caiuRapido = perto.length > 0 && t - perto[perto.length - 1][0] <= NOD_MAX_FALL_S;
      } else {
        this.guardarReferencia(t, pitch);
      }
    } else if (desvio <= NOD_RECOVERED_DEG) {
      const baixo = t - this.baixoDesde;
      if (this.caiuRapido && baixo >= NOD_MIN_DOWN_S && baixo <= NOD_MAX_DOWN_S) cabeceio = { inicio: this.baixoDesde, duracao: baixo };
      this.baixoDesde = null;
    } else if (t - this.baixoDesde > NOD_MAX_DOWN_S) {
      this.baixoDesde = null;
      this.esperandoVolta = true;
    }
    this.lembrar(t, pitch);
    return cabeceio;
  }

  private lembrar(t: number, pitch: number): void {
    this.recentes.push([t, pitch]);
    while (this.recentes.length && this.recentes[0][0] < t - NOD_RECENT_S) this.recentes.shift();
  }

  private guardarReferencia(t: number, pitch: number): void {
    if (t < this.proximaReferencia) return;
    this.proximaReferencia = t + NOD_REFERENCE_STEP_S;
    this.referencia.push([t, pitch]);
    while (this.referencia.length && this.referencia[0][0] < t - NOD_REFERENCE_S) this.referencia.shift();
  }
}

export type Estagio = "normal" | "microssono" | "sono" | "sem_resposta";
export type TipoDeEvento = "microssono" | "sono" | "sem_resposta" | "bocejo" | "cabeceio" | "sem_rosto" | "perclos_alto";

/** Um item da linha do tempo da sessão. `duracao` fica null enquanto o evento está acontecendo. */
export type EventoDaSessao = { id: number; tipo: TipoDeEvento; inicio: number; duracao: number | null };

export type QuadroDeSono = { t: number; rosto: boolean; abertura: number | null; jawOpen: number | null; pitch: number | null };

export type LeituraDeSono = {
  estagio: Estagio;
  fechadoHa: number;
  perclos60s: number | null;
  piscadas: number;
  piscadasPorMinuto: number | null;
  bocejos: number;
  cabeceios: number;
  semRostoHa: number;
};

const ESTAGIOS: Estagio[] = ["normal", "microssono", "sono", "sem_resposta"];
const MAXIMO_DE_EVENTOS = 200;

function estagioDe(fechadoHa: number): Estagio {
  if (fechadoHa >= UNRESPONSIVE_S) return "sem_resposta";
  if (fechadoHa >= SLEEP_S) return "sono";
  if (fechadoHa >= MICROSLEEP_S) return "microssono";
  return "normal";
}

/** Junta tudo por quadro, como DrowsinessMonitor.update sem linha de base individual: só os gatilhos críticos. */
export class MonitorDeSono {
  private olho = new EstadoDoOlho();
  private perclos = new Perclos();
  private cabeceio = new Cabeceio();
  private primeiroT: number | null = null;
  private ultimoT: number | null = null;
  private pendente = 0;
  private inicioBocejo: number | null = null;
  private bocejoAtual: EventoDaSessao | null = null;
  private fechamentoAtual: EventoDaSessao | null = null;
  private ultimoFechadoHa = 0;
  private semRostoDesde: number | null = null;
  private semRostoAtual: EventoDaSessao | null = null;
  private perclosAtual: EventoDaSessao | null = null;
  private perclosArmado = true;
  private fimDasPiscadas: number[] = [];
  private proximoId = 1;
  private readonly jawBase: number;
  piscadas = 0;
  bocejos = 0;
  cabeceios = 0;
  /** Mais antigos primeiro; muda no lugar (duração de quem está acontecendo). */
  readonly eventos: EventoDaSessao[] = [];
  /** Sobe a cada evento novo ou atualizado: a tela só copia a lista quando muda. */
  versao = 0;

  constructor(jawBase = 0) {
    this.jawBase = jawBase; // sem "parameter property": o Node não apaga essa sintaxe
  }

  private novoEvento(tipo: TipoDeEvento, inicio: number): EventoDaSessao {
    const evento: EventoDaSessao = { id: this.proximoId++, tipo, inicio, duracao: null };
    this.eventos.push(evento);
    if (this.eventos.length > MAXIMO_DE_EVENTOS) this.eventos.shift();
    this.versao++;
    return evento;
  }

  private fechar(evento: EventoDaSessao | null, duracao: number): null {
    if (evento) {
      evento.duracao = Math.max(0, duracao);
      this.versao++;
    }
    return null;
  }

  atualizar(q: QuadroDeSono): LeituraDeSono {
    if (this.primeiroT === null) this.primeiroT = q.t;
    let dt = 0;
    if (this.ultimoT !== null && q.t - this.ultimoT > 0 && q.t - this.ultimoT <= MAX_FRAME_GAP_S) dt = q.t - this.ultimoT;
    this.ultimoT = q.t;

    // Rosto fora da câmera: vira evento depois de 2 s.
    if (!q.rosto) {
      if (this.semRostoDesde === null) this.semRostoDesde = q.t;
      if (!this.semRostoAtual && q.t - this.semRostoDesde >= SEM_ROSTO_EVENTO_S) this.semRostoAtual = this.novoEvento("sem_rosto", this.semRostoDesde);
    } else if (this.semRostoDesde !== null) {
      this.semRostoAtual = this.fechar(this.semRostoAtual, q.t - this.semRostoDesde);
      this.semRostoDesde = null;
    }

    if (q.abertura !== null) this.perclos.valido(q.t, dt);
    const piscada = this.olho.atualizar(q.t, q.abertura);
    if (piscada && piscada.minimo <= COMPLETE_BLINK_OPENNESS && piscada.duracao <= MAX_BLINK_S) {
      this.piscadas++;
      this.fimDasPiscadas.push(piscada.fim);
    }
    while (this.fimDasPiscadas.length && this.fimDasPiscadas[0] < q.t - JANELA_PISCADAS_S) this.fimDasPiscadas.shift();
    const fechadoHa = this.olho.fechadoHa;

    // PERCLOS: o fechamento só conta depois de passar de 250 ms (drowsiness.py).
    if (q.abertura !== null && q.abertura <= P80_OPENNESS) {
      this.pendente += dt;
      if (fechadoHa >= SHORT_CLOSURE_S) {
        this.perclos.fechado(q.t, this.pendente);
        this.pendente = 0;
      }
    } else if (q.abertura !== null) {
      this.pendente = 0;
    }

    // Olhos fechados: um evento por fechamento, que sobe de microssono para sono e sem resposta.
    const estagio = estagioDe(fechadoHa);
    if (estagio !== "normal") {
      if (!this.fechamentoAtual) this.fechamentoAtual = this.novoEvento(estagio, q.t - fechadoHa);
      else if (ESTAGIOS.indexOf(estagio) > ESTAGIOS.indexOf(this.fechamentoAtual.tipo as Estagio)) {
        this.fechamentoAtual.tipo = estagio;
        this.versao++;
      }
    } else if (this.fechamentoAtual && fechadoHa === 0) {
      this.fechamentoAtual = this.fechar(this.fechamentoAtual, this.ultimoFechadoHa);
    }
    if (fechadoHa > 0 || !this.fechamentoAtual) this.ultimoFechadoHa = fechadoHa;

    // Bocejo: jawOpen alto por 2 s; histerese de 0,1 para soltar.
    const limiar = Math.max(YAWN_JAW_MIN, this.jawBase + YAWN_JAW_ABOVE_BASELINE);
    if (q.jawOpen !== null && q.jawOpen >= limiar) {
      if (this.inicioBocejo === null) this.inicioBocejo = q.t;
      else if (!this.bocejoAtual && q.t - this.inicioBocejo >= YAWN_MIN_S) {
        this.bocejos++;
        this.bocejoAtual = this.novoEvento("bocejo", this.inicioBocejo);
      }
    } else if (q.jawOpen === null || q.jawOpen < limiar - 0.1) {
      if (this.inicioBocejo !== null) this.bocejoAtual = this.fechar(this.bocejoAtual, q.t - this.inicioBocejo);
      this.inicioBocejo = null;
    }

    const cabeceio = this.cabeceio.atualizar(q.t, q.pitch);
    if (cabeceio) {
      this.cabeceios++;
      this.fechar(this.novoEvento("cabeceio", cabeceio.inicio), cabeceio.duracao);
    }

    // PERCLOS acima do limiar de alerta: um evento por subida; rearma abaixo de 10%.
    const perclos60s = this.perclos.valor(q.t, 60);
    if (perclos60s !== null && perclos60s >= ALERT_PERCLOS && this.perclosArmado) {
      this.perclosArmado = false;
      this.perclosAtual = this.novoEvento("perclos_alto", q.t);
    } else if (perclos60s !== null && perclos60s < ALERT_PERCLOS && this.perclosAtual) {
      this.perclosAtual = this.fechar(this.perclosAtual, q.t - this.perclosAtual.inicio);
    }
    if (perclos60s !== null && perclos60s < PERCLOS_REARMA) this.perclosArmado = true;

    const decorrido = q.t - this.primeiroT;
    return {
      estagio,
      fechadoHa,
      perclos60s,
      piscadas: this.piscadas,
      piscadasPorMinuto:
        decorrido < PISCADAS_MIN_S ? null : Math.round((this.fimDasPiscadas.length * 60) / Math.min(JANELA_PISCADAS_S, decorrido)),
      bocejos: this.bocejos,
      cabeceios: this.cabeceios,
      semRostoHa: this.semRostoDesde === null ? 0 : q.t - this.semRostoDesde,
    };
  }
}
