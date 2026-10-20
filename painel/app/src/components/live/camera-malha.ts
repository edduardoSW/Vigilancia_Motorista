// Spec 025, refeita pela spec 029 (MAL-07): a malha do rosto num canvas por cima do vídeo, no mesmo estilo do script
// Python (caixa/vision/driver_monitor.py, draw_face_mesh). Regras da 029: nada preenchido sobre a pele; nada dentro do
// olho (as marcas dos olhos ficam do lado de fora, como colchetes); lima só no que está medindo, o resto em branco
// translúcido.
// - discreta (padrão): pontos do contorno do rosto, contorno tracejado, colchetes dos olhos, contorno de fora da boca
//   tracejado e só os cantos das regiões do pulso;
// - completa: o mesmo e os 478 pontos, menos os do olho, os de perto dele e os de dentro das regiões do pulso;
// - desligada ("Só o rosto"): nada.
// Tudo é traço (stroke), nunca preenchimento: colchetes e cantos são barras retas de pixel inteiro (nítidas) e cada
// ponto é um círculo de meio raio traçado com a largura do raio. Uma passada por cor, opacidade e espessura (um
// beginPath, muitos subcaminhos, um stroke): poucas chamadas por quadro.
import type { NormalizedLandmark } from "@mediapipe/tasks-vision";
import { rgba, type CoresDoTema } from "./camera-cores";
import type { ModoDaMalha } from "./camera-regras";
import { ROIS } from "./camera-rppg";

// Caminhos do Face Mesh em ordem de traço (os mesmos do driver_monitor.py, FaceLandmarksConnections do MediaPipe).
export const CONTORNO_DO_ROSTO = [
  10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136,
  172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109,
];
export const OLHO_DIREITO = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246];
export const OLHO_ESQUERDO = [263, 249, 390, 373, 374, 380, 381, 382, 362, 398, 384, 385, 386, 387, 388, 466];
export const BOCA_DE_FORA = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 409, 270, 269, 267, 0, 37, 39, 40, 185];
export const BOCA_DE_DENTRO = [78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308, 415, 310, 311, 312, 13, 82, 81, 80, 191];
export const IRIS = [
  { centro: 468, anel: [469, 470, 471, 472] },
  { centro: 473, anel: [474, 475, 476, 477] },
];

// Opacidades (spec 029, decisão 2), as mesmas do Python: pontos do contorno a 25%, os da completa a 40%, contorno
// tracejado a 30%, boca a 40%, colchetes dos olhos a 90% (100% com o olho fechado) e cantos do pulso de 35% a 70% no
// ritmo da onda (menores e mais apagados que os colchetes: o olho é o que mais importa ver).
const ALFA_PONTO_DO_CONTORNO = 0.25;
const ALFA_PONTO_DA_COMPLETA = 0.4;
const ALFA_CONTORNO = 0.3;
const ALFA_BOCA = 0.4;
const ALFA_COLCHETE = 0.9;
const ALFA_PULSO_MEDINDO = 0.35;
const TRACO_DO_CONTORNO: [number, number] = [0.38, 0.62]; // traço curto no meio de um segmento sim e outro não
const TRACEJADO_DA_BOCA: [number, number] = [2, 4]; // px, no quadro de 640
const LONGE_DO_OLHO_PX = 3; // nenhum ponto a menos disso do olho
const QUADRO_DE_REFERENCIA = 640; // as medidas do Python valem num quadro de 640 px de largura
const PONTOS_MINIMOS = 468;

const PROIBIDOS = new Set([...OLHO_DIREITO, ...OLHO_ESQUERDO, ...IRIS.flatMap(({ centro, anel }) => [centro, ...anel])]);

type Caixa = { x0: number; y0: number; x1: number; y1: number };

export type OpcoesDoDesenho = {
  modo: ModoDaMalha;
  /** 0 a 1 acompanhando a onda do pulso; null enquanto ainda mede. */
  pulso: number | null;
  olhosFechados: boolean;
  /** Testa, bochecha esq e bochecha dir: só as que entram na conta. */
  areas: boolean[];
  cores: CoresDoTema;
};

function caixaDe(xs: number[], ys: number[]): Caixa {
  return { x0: Math.min(...xs), y0: Math.min(...ys), x1: Math.max(...xs), y1: Math.max(...ys) };
}

/**
 * Barras retas de pixel inteiro (colchetes e cantos), agrupadas por espessura. Cada barra (x, y, largura, altura) vira
 * um traço reto no meio dela, com a espessura dela e ponta reta: cobre exatamente os mesmos pixels, sem preencher nada.
 */
class Barras {
  private readonly porEspessura = new Map<number, [number, number, number, number][]>();

  barra(x: number, y: number, largura: number, altura: number): void {
    if (largura <= 0 || altura <= 0) return;
    const deitada = largura >= altura;
    const espessura = deitada ? altura : largura;
    const linha: [number, number, number, number] = deitada
      ? [x, y + altura / 2, x + largura, y + altura / 2]
      : [x + largura / 2, y, x + largura / 2, y + altura];
    const lista = this.porEspessura.get(espessura) ?? [];
    lista.push(linha);
    this.porEspessura.set(espessura, lista);
  }

  tracar(ctx: CanvasRenderingContext2D, cor: string): void {
    ctx.lineCap = "butt";
    ctx.strokeStyle = cor;
    for (const [espessura, linhas] of this.porEspessura) {
      ctx.beginPath();
      for (const [xa, ya, xb, yb] of linhas) {
        ctx.moveTo(xa, ya);
        ctx.lineTo(xb, yb);
      }
      ctx.lineWidth = espessura;
      ctx.stroke();
    }
  }
}

/** Desenha a malha de um quadro no contexto (tudo em pixels do canvas). Exportada para o teste com canvas falso. */
export function desenharMalha(ctx: CanvasRenderingContext2D, pontos: NormalizedLandmark[], { modo, pulso, olhosFechados, areas, cores }: OpcoesDoDesenho): void {
  const w = ctx.canvas.width;
  const h = ctx.canvas.height;
  ctx.clearRect(0, 0, w, h);
  if (modo === "desligada" || pontos.length < PONTOS_MINIMOS) return;
  const escala = Math.max(1, w / QUADRO_DE_REFERENCIA); // o canvas é o quadro de 640 ampliado
  const x = (indice: number) => pontos[indice].x * w;
  const y = (indice: number) => pontos[indice].y * h;
  const caixaDosIndices = (indices: readonly number[]) => caixaDe(indices.map(x), indices.map(y));
  const olhos = [caixaDosIndices(OLHO_DIREITO), caixaDosIndices(OLHO_ESQUERDO)];
  const branco = (alfa: number) => rgba(cores.sobreVideo, alfa);

  ctx.save();
  // Garantia do MAL-01 (como o _eye_guard do Python): o retângulo de cada olho, com 1 px de folga, fica fora do recorte.
  // Nada do desenho chega lá, nem um ponto que o modelo ponha em cima do olho.
  ctx.beginPath();
  ctx.rect(0, 0, w, h);
  for (const olho of olhos) {
    const x0 = Math.floor(olho.x0) - 1;
    const y0 = Math.floor(olho.y0) - 1;
    ctx.rect(x0, y0, Math.ceil(olho.x1) + 2 - x0, Math.ceil(olho.y1) + 2 - y0);
  }
  ctx.clip("evenodd");
  ctx.lineJoin = "round";
  ctx.lineWidth = escala;

  // 1. Contorno do rosto: traço curto no meio de um segmento sim e outro não.
  ctx.beginPath();
  CONTORNO_DO_ROSTO.forEach((indice, k) => {
    if (k % 2) return;
    const seguinte = CONTORNO_DO_ROSTO[(k + 1) % CONTORNO_DO_ROSTO.length];
    const [a, b] = TRACO_DO_CONTORNO;
    ctx.moveTo(x(indice) + (x(seguinte) - x(indice)) * a, y(indice) + (y(seguinte) - y(indice)) * a);
    ctx.lineTo(x(indice) + (x(seguinte) - x(indice)) * b, y(indice) + (y(seguinte) - y(indice)) * b);
  });
  ctx.lineCap = "butt"; // ponta reta: o traço não engorda nas pontas (menos pixel mexido, MAL-03)
  ctx.strokeStyle = branco(ALFA_CONTORNO);
  ctx.stroke();

  // 2. Boca: só o contorno de fora, tracejado e fino (sem a linha do meio).
  ctx.beginPath();
  BOCA_DE_FORA.forEach((indice, k) => (k ? ctx.lineTo(x(indice), y(indice)) : ctx.moveTo(x(indice), y(indice))));
  ctx.closePath();
  ctx.setLineDash(TRACEJADO_DA_BOCA.map((tamanho) => tamanho * escala));
  ctx.strokeStyle = branco(ALFA_BOCA);
  ctx.stroke();
  ctx.setLineDash([]);

  // 3. Olhos: colchetes por fora dos cantos, em lima (é o que está medindo); mais fortes com o olho fechado.
  const colchetesDosOlhos = new Barras();
  for (const olho of olhos) colchetes(colchetesDosOlhos, olho, escala, olhosFechados);
  colchetesDosOlhos.tracar(ctx, rgba(cores.lima, olhosFechados ? 1 : ALFA_COLCHETE));

  // 4. Regiões do pulso: só os cantos, por fora; lima no ritmo da onda com leitura pronta, branco enquanto mede.
  const regioes: Caixa[] = [];
  ROIS.forEach((regiao, k) => {
    if (areas[k]) regioes.push(caixaDosIndices(regiao));
  });
  const cantosDoPulso = new Barras();
  for (const regiao of regioes) cantos(cantosDoPulso, regiao, escala);
  cantosDoPulso.tracar(ctx, pulso === null ? branco(ALFA_PULSO_MEDINDO) : rgba(cores.lima, 0.35 + 0.35 * Math.max(0, Math.min(1, pulso))));

  // 5. Pontos: na discreta, só os do contorno; na completa, todos menos os do olho, os de perto dele e os de dentro das
  // regiões do pulso (que ficam limpas para a pele aparecer). Cada ponto: círculo de meio raio com traço da largura do
  // raio (dá um ponto cheio do tamanho do raio, sem fill), com o centro no canto de pixel mais perto: 2 × 2 pixels
  // nítidos em vez de uma mancha de 3 × 3 (como a tabela de subpixel do Python, que não toca o que pesa menos de 4%).
  const raio = Math.max(1, Math.sqrt(escala));
  let indices: number[];
  if (modo === "discreta") {
    indices = CONTORNO_DO_ROSTO;
  } else {
    const alcance = LONGE_DO_OLHO_PX * escala + raio;
    const fora = (px: number, py: number, caixa: Caixa, folga: number) =>
      px <= caixa.x0 - folga || px >= caixa.x1 + folga || py <= caixa.y0 - folga || py >= caixa.y1 + folga;
    indices = [];
    for (let indice = 0; indice < pontos.length; indice++) {
      if (PROIBIDOS.has(indice)) continue;
      const px = x(indice);
      const py = y(indice);
      if (olhos.every((olho) => fora(px, py, olho, alcance)) && regioes.every((regiao) => fora(px, py, regiao, raio))) indices.push(indice);
    }
  }
  ctx.beginPath();
  for (const indice of indices) {
    const px = Math.round(x(indice));
    const py = Math.round(y(indice));
    ctx.moveTo(px + raio / 2, py);
    ctx.arc(px, py, raio / 2, 0, Math.PI * 2);
  }
  ctx.lineWidth = raio;
  ctx.strokeStyle = branco(modo === "discreta" ? ALFA_PONTO_DO_CONTORNO : ALFA_PONTO_DA_COMPLETA);
  ctx.stroke();
  ctx.restore();
}

/** Dois colchetes finos nos cantos do olho, do lado de fora: "[" antes de um canto e "]" depois do outro. A altura vem da
 * largura do olho (não pisca junto com a pálpebra); os ganchos não chegam ao olho (MAL-01). Pixels inteiros: nítidos. */
function colchetes(barras: Barras, { x0, y0, x1, y1 }: Caixa, escala: number, fechado: boolean): void {
  const largura = Math.max(x1 - x0, 4);
  const margem = Math.max(3 * escala, 0.2 * largura);
  const gancho = Math.min(Math.max(2 * escala, 0.1 * largura), margem - 1);
  const meia = Math.max(0.2 * largura, 2 * escala);
  const meio = (y0 + y1) / 2;
  const topo = Math.round(meio - meia);
  const base = Math.round(meio + meia);
  const fino = Math.max(1, Math.round(escala));
  const espessura = fino + (fechado ? 1 : 0);
  for (const [borda, direcao] of [
    [x0 - margem, 1],
    [x1 + margem, -1],
  ] as const) {
    const coluna = Math.round(borda);
    const ponta = Math.round(borda + direcao * gancho);
    // Haste vertical, engrossando para fora do olho.
    barras.barra(direcao > 0 ? coluna - espessura + 1 : coluna, topo, espessura, base - topo + 1);
    // Ganchos de cima e de baixo, apontando para o olho, sem chegar nele (começam depois da haste).
    const inicio = direcao > 0 ? coluna + 1 : ponta;
    const comprimento = Math.abs(ponta - coluna);
    barras.barra(inicio, topo, comprimento, fino);
    barras.barra(inicio, base + 1 - fino, comprimento, fino);
  }
}

/** Só os cantos da região do pulso, por fora da caixa dela: sem preenchimento e sem contorno inteiro (MAL-02). */
function cantos(barras: Barras, { x0, y0, x1, y1 }: Caixa, escala: number): void {
  const fora = 2 * escala;
  const braco = Math.round(Math.max(2 * escala, 0.1 * Math.min(x1 - x0, y1 - y0)));
  const fino = Math.max(1, Math.round(escala));
  for (const [cx, cy, dx, dy] of [
    [x0 - fora, y0 - fora, 1, 1],
    [x1 + fora, y0 - fora, -1, 1],
    [x0 - fora, y1 + fora, 1, -1],
    [x1 + fora, y1 + fora, -1, -1],
  ] as const) {
    const px = Math.round(cx);
    const py = Math.round(cy);
    // Braço deitado (com o pixel do canto) e braço em pé (sem ele, para não passar duas vezes no mesmo pixel).
    barras.barra(dx > 0 ? px : px - braco, dy > 0 ? py : py - fino + 1, braco + 1, fino);
    barras.barra(dx > 0 ? px : px - fino + 1, dy > 0 ? py + fino : py - braco, fino, braco + 1 - fino);
  }
}

export class DesenhoDaMalha {
  private readonly ctx: CanvasRenderingContext2D;

  constructor(canvas: HTMLCanvasElement) {
    const ctx = canvas.getContext("2d", { alpha: true });
    if (!ctx) throw new Error("canvas 2D indisponível");
    this.ctx = ctx;
  }

  /** Tamanho interno = tamanho na tela × densidade (no máximo 2). Chamar quando o tamanho muda, não a cada quadro. */
  ajustar(): void {
    const canvas = this.ctx.canvas;
    const densidade = Math.min(2, window.devicePixelRatio || 1);
    const largura = Math.round(canvas.clientWidth * densidade);
    const altura = Math.round(canvas.clientHeight * densidade);
    if (largura > 0 && altura > 0 && (canvas.width !== largura || canvas.height !== altura)) {
      canvas.width = largura;
      canvas.height = altura;
    }
  }

  limpar(): void {
    this.ctx.clearRect(0, 0, this.ctx.canvas.width, this.ctx.canvas.height);
  }

  desenhar(pontos: NormalizedLandmark[], opcoes: OpcoesDoDesenho): void {
    desenharMalha(this.ctx, pontos, opcoes);
  }
}
