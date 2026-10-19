// Spec 025 · cor média de cada região do pulso (testa, bochecha esq e bochecha dir, lado da imagem), como o
// cardio.py _medias_rois: só os pixels dentro do polígono e com os três canais entre 16 e 249, e no mínimo 100 pixels.
// Cada região é copiada pelo próprio drawImage para um canvas pequeno (no máximo 96 px no lado maior, quase sempre o
// tamanho real) e só esses pixels voltam da placa de vídeo.
import { PIXEL_ESCURO, PIXEL_SATURADO, PIXELS_MIN_ROI, ROIS, type Ponto, type Rgb } from "./camera-rppg";

const LADO_MAXIMO = 96;

/** Trechos [x inicial, x final) de cada linha y que ficam dentro do polígono (varredura por linha). */
function dentroNaLinha(poligono: readonly Ponto[], y: number): number[] {
  const cruzamentos: number[] = [];
  for (let i = 0; i < poligono.length; i++) {
    const a = poligono[i];
    const b = poligono[(i + 1) % poligono.length];
    if ((a.y <= y && b.y > y) || (b.y <= y && a.y > y)) cruzamentos.push(a.x + ((y - a.y) / (b.y - a.y)) * (b.x - a.x));
  }
  return cruzamentos.sort((p, q) => p - q);
}

export class LeitorDeRoi {
  private readonly ctx: CanvasRenderingContext2D;

  constructor() {
    const canvas = document.createElement("canvas");
    canvas.width = LADO_MAXIMO * ROIS.length;
    canvas.height = LADO_MAXIMO;
    const ctx = canvas.getContext("2d", { willReadFrequently: true, alpha: false });
    if (!ctx) throw new Error("canvas 2D indisponível");
    this.ctx = ctx;
  }

  /** Polígonos em pixels do vídeo (vértices já suavizados e arredondados); `usar` tira a bochecha do rosto virado. */
  ler(video: HTMLVideoElement, poligonos: readonly (readonly Ponto[])[], usar: readonly boolean[]): (Rgb | null)[] {
    const largura = video.videoWidth;
    const altura = video.videoHeight;
    if (!largura || !altura) return poligonos.map(() => null);
    const recortes = poligonos.map((poligono, k) => {
      if (!usar[k]) return null;
      const x0 = Math.max(Math.floor(Math.min(...poligono.map((p) => p.x))), 0);
      const y0 = Math.max(Math.floor(Math.min(...poligono.map((p) => p.y))), 0);
      const x1 = Math.min(Math.floor(Math.max(...poligono.map((p) => p.x))) + 1, largura);
      const y1 = Math.min(Math.floor(Math.max(...poligono.map((p) => p.y))) + 1, altura);
      if (x1 - x0 < 2 || y1 - y0 < 2) return null;
      const escala = Math.min(1, LADO_MAXIMO / Math.max(x1 - x0, y1 - y0));
      const w = Math.max(1, Math.round((x1 - x0) * escala));
      const h = Math.max(1, Math.round((y1 - y0) * escala));
      this.ctx.drawImage(video, x0, y0, x1 - x0, y1 - y0, k * LADO_MAXIMO, 0, w, h);
      return { x0, y0, w, h, escalaX: w / (x1 - x0), escalaY: h / (y1 - y0) };
    });
    if (recortes.every((recorte) => recorte === null)) return poligonos.map(() => null);
    const dados = this.ctx.getImageData(0, 0, LADO_MAXIMO * ROIS.length, LADO_MAXIMO).data;
    const larguraDaFaixa = LADO_MAXIMO * ROIS.length;
    return recortes.map((recorte, k) => {
      if (!recorte) return null;
      let r = 0;
      let g = 0;
      let b = 0;
      let n = 0;
      for (let py = 0; py < recorte.h; py++) {
        const y = recorte.y0 + (py + 0.5) / recorte.escalaY;
        const cruzamentos = dentroNaLinha(poligonos[k], y);
        for (let c = 0; c + 1 < cruzamentos.length; c += 2) {
          const inicio = Math.max(0, Math.ceil((cruzamentos[c] - recorte.x0) * recorte.escalaX - 0.5));
          const fim = Math.min(recorte.w - 1, Math.floor((cruzamentos[c + 1] - recorte.x0) * recorte.escalaX - 0.5));
          for (let px = inicio; px <= fim; px++) {
            const o = (py * larguraDaFaixa + k * LADO_MAXIMO + px) * 4;
            const R = dados[o];
            const G = dados[o + 1];
            const B = dados[o + 2];
            // cardio.py: canal <= 15 (escuro) ou >= 250 (reflexo) sai da média.
            if (R <= PIXEL_ESCURO || G <= PIXEL_ESCURO || B <= PIXEL_ESCURO || R >= PIXEL_SATURADO || G >= PIXEL_SATURADO || B >= PIXEL_SATURADO) continue;
            r += R;
            g += G;
            b += B;
            n++;
          }
        }
      }
      // O mínimo de 100 pixels vale no tamanho real do vídeo: o recorte reduzido conta em proporção.
      if (n === 0 || n / (recorte.escalaX * recorte.escalaY) < PIXELS_MIN_ROI) return null;
      return [r / n, g / n, b / n] as Rgb;
    });
  }
}
