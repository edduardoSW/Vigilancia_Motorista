// Spec 025 · as "bolinhas": 478 pontos, malha fina, olhos, íris e boca em destaque e as áreas do pulso, num canvas
// por cima do vídeo. Uma passada por cor (um beginPath, muitos subcaminhos, um fill ou stroke): poucas chamadas de
// desenho por quadro. As ligações vêm do próprio MediaPipe (carregado só ao ligar a câmera), por isso entram pelo
// construtor em vez de import.
import type { NormalizedLandmark } from "@mediapipe/tasks-vision";
import { rgba, type CoresDoTema } from "./camera-cores";
import type { ModoDaMalha } from "./camera-regras";
import { ROIS } from "./camera-rppg";

type Conexao = { start: number; end: number };

export type ConexoesDoRosto = {
  tesselacao: Conexao[];
  contornos: Conexao[];
  olhos: Conexao[];
  iris: Conexao[];
  boca: Conexao[];
};

export type OpcoesDoDesenho = {
  modo: ModoDaMalha;
  /** 0 a 1, acompanhando a onda do pulso; null enquanto mede. */
  pulso: number | null;
  olhosFechados: boolean;
  areas: boolean[];
  cores: CoresDoTema;
};

const IRIS_DIREITA = { centro: 468, anel: [469, 470, 471, 472] };
const IRIS_ESQUERDA = { centro: 473, anel: [474, 475, 476, 477] };

const indicesDe = (...listas: Conexao[][]) => new Set(listas.flat().flatMap((conexao) => [conexao.start, conexao.end]));

export class DesenhoDaMalha {
  private readonly ctx: CanvasRenderingContext2D;
  private readonly conexoes: ConexoesDoRosto;
  private readonly olhos: Set<number>;
  private readonly boca: Set<number>;
  private readonly comuns: number[];

  constructor(canvas: HTMLCanvasElement, conexoes: ConexoesDoRosto) {
    const ctx = canvas.getContext("2d", { alpha: true });
    if (!ctx) throw new Error("canvas 2D indisponível");
    this.ctx = ctx;
    this.conexoes = conexoes;
    this.olhos = indicesDe(conexoes.olhos);
    this.boca = indicesDe(conexoes.boca);
    const destaque = new Set([...this.olhos, ...this.boca, ...indicesDe(conexoes.iris)]);
    this.comuns = Array.from({ length: 478 }, (_, indice) => indice).filter((indice) => !destaque.has(indice));
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

  desenhar(pontos: NormalizedLandmark[], { modo, pulso, olhosFechados, areas, cores }: OpcoesDoDesenho): void {
    const ctx = this.ctx;
    const w = ctx.canvas.width;
    const h = ctx.canvas.height;
    ctx.clearRect(0, 0, w, h);
    if (modo === "desligada" || pontos.length < 478) return;
    const r = Math.max(1, w / 460); // tamanho do ponto acompanha o vídeo na tela
    const x = (indice: number) => pontos[indice].x * w;
    const y = (indice: number) => pontos[indice].y * h;
    ctx.lineJoin = "round";
    ctx.lineCap = "round";

    // 1. Áreas do pulso: o contorno lima acende e apaga com a onda medida.
    ctx.beginPath();
    ROIS.forEach((area, k) => {
      if (!areas[k]) return;
      area.forEach((indice, i) => (i ? ctx.lineTo(x(indice), y(indice)) : ctx.moveTo(x(indice), y(indice))));
      ctx.closePath();
    });
    const batida = pulso ?? 0.5;
    ctx.fillStyle = rgba(cores.lima, pulso === null ? 0.1 : 0.08 + 0.2 * batida);
    ctx.fill();
    ctx.setLineDash(pulso === null ? [r * 3, r * 2] : []);
    ctx.lineWidth = r * (pulso === null ? 1 : 1 + 0.8 * batida);
    ctx.strokeStyle = rgba(cores.lima, pulso === null ? 0.8 : 0.55 + 0.45 * batida);
    ctx.stroke();
    ctx.setLineDash([]);

    // 2. Linhas: a malha inteira, ou só os contornos no modo essencial (celular).
    const linhas = modo === "completa" ? this.conexoes.tesselacao : modo === "essencial" ? this.conexoes.contornos : null;
    if (linhas) {
      ctx.beginPath();
      for (const { start, end } of linhas) {
        ctx.moveTo(x(start), y(start));
        ctx.lineTo(x(end), y(end));
      }
      ctx.lineWidth = Math.max(0.5, r * (modo === "completa" ? 0.35 : 0.55));
      ctx.strokeStyle = rgba(cores.sobreVideo, modo === "completa" ? 0.2 : 0.5);
      ctx.stroke();
    }

    // 3. Os 478 pontos (quadradinhos custam menos que arc e parecem bolinhas nesse tamanho).
    if (modo !== "essencial") {
      ctx.beginPath();
      const lado = r * 1.9;
      for (const indice of this.comuns) ctx.rect(x(indice) - lado / 2, y(indice) - lado / 2, lado, lado);
      ctx.fillStyle = rgba(cores.sobreVideo, 0.72);
      ctx.fill();
    }

    // 4. Boca e olhos em destaque; olhos fechados ficam na cor de alarme.
    this.circulos(this.boca, r * 1.05, rgba(cores.sobreVideo, 0.95), x, y);
    this.circulos(this.olhos, r * 1.25, olhosFechados ? rgba(cores.alarme, 1) : rgba(cores.lima, 1), x, y);

    // 5. Íris: anel e centro (some com o olho fechado, quando o modelo só adivinha a posição).
    if (!olhosFechados) {
      ctx.beginPath();
      for (const { centro, anel } of [IRIS_DIREITA, IRIS_ESQUERDA]) {
        const raio = anel.reduce((soma, indice) => soma + Math.hypot(x(indice) - x(centro), y(indice) - y(centro)), 0) / anel.length;
        ctx.moveTo(x(centro) + raio, y(centro));
        ctx.arc(x(centro), y(centro), raio, 0, Math.PI * 2);
      }
      ctx.lineWidth = r * 0.9;
      ctx.strokeStyle = rgba(cores.lima, 0.95);
      ctx.stroke();
      ctx.beginPath();
      for (const { centro } of [IRIS_DIREITA, IRIS_ESQUERDA]) {
        ctx.moveTo(x(centro) + r * 1.2, y(centro));
        ctx.arc(x(centro), y(centro), r * 1.2, 0, Math.PI * 2);
      }
      ctx.fillStyle = rgba(cores.lima, 1);
      ctx.fill();
    }
  }

  private circulos(indices: Set<number>, raio: number, cor: string, x: (i: number) => number, y: (i: number) => number): void {
    const ctx = this.ctx;
    ctx.beginPath();
    for (const indice of indices) {
      ctx.moveTo(x(indice) + raio, y(indice));
      ctx.arc(x(indice), y(indice), raio, 0, Math.PI * 2);
    }
    ctx.fillStyle = cor;
    ctx.fill();
  }
}
