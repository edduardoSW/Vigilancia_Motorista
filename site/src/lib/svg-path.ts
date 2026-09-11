import { geoPath, type GeoPermissibleObjects, type GeoProjection } from "d3-geo";

/**
 * Caminho SVG leve para mapas renderizados no servidor.
 * O d3-geo projeta e recorta; aqui cada linha é simplificada no espaço da tela (Douglas-Peucker com tolerância em
 * pixels do viewBox), as coordenadas saem com uma casa decimal e uma camada inteira vira um único `d`.
 * Sem isso, a malha federal e as divisas deixavam o HTML com vários megabytes.
 */
type Ponto = [number, number];
interface Parte {
  pontos: Ponto[];
  fechada: boolean;
}

class Gravador {
  partes: Parte[] = [];
  private atual: Parte | null = null;
  moveTo(x: number, y: number) {
    this.atual = { pontos: [[x, y]], fechada: false };
    this.partes.push(this.atual);
  }
  lineTo(x: number, y: number) {
    this.atual?.pontos.push([x, y]);
  }
  closePath() {
    if (this.atual) this.atual.fechada = true;
  }
  arc() {
    /* pontos (geoPath.pointRadius) não são usados nestes mapas */
  }
}

function distanciaAoSegmento2([px, py]: Ponto, [ax, ay]: Ponto, [bx, by]: Ponto): number {
  const dx = bx - ax;
  const dy = by - ay;
  const comprimento2 = dx * dx + dy * dy;
  const t = comprimento2 === 0 ? 0 : Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / comprimento2));
  const x = ax + t * dx - px;
  const y = ay + t * dy - py;
  return x * x + y * y;
}

export function simplificar(pontos: Ponto[], tolerancia: number): Ponto[] {
  if (pontos.length <= 2) return pontos;
  const tol2 = tolerancia * tolerancia;
  const manter = new Uint8Array(pontos.length);
  manter[0] = 1;
  manter[pontos.length - 1] = 1;
  const pilha: [number, number][] = [[0, pontos.length - 1]];
  while (pilha.length) {
    const [inicio, fim] = pilha.pop()!;
    let maior = 0;
    let indice = -1;
    for (let i = inicio + 1; i < fim; i++) {
      const d = distanciaAoSegmento2(pontos[i], pontos[inicio], pontos[fim]);
      if (d > maior) {
        maior = d;
        indice = i;
      }
    }
    if (indice !== -1 && maior > tol2) {
      manter[indice] = 1;
      pilha.push([inicio, indice], [indice, fim]);
    }
  }
  return pontos.filter((_, i) => manter[i] === 1);
}

const n = (v: number) => (Math.round(v * 10) / 10).toString();

export function caminhoLeve(projecao: GeoProjection, objetos: GeoPermissibleObjects[], tolerancia = 0.75): string {
  const gravador = new Gravador();
  const gerador = geoPath(projecao, gravador as unknown as CanvasRenderingContext2D);
  for (const objeto of objetos) gerador(objeto);

  let d = "";
  for (const parte of gravador.partes) {
    const simples = simplificar(parte.pontos, tolerancia);
    if (simples.length < 2 || (parte.fechada && simples.length < 3)) continue;
    d += `M${n(simples[0][0])} ${n(simples[0][1])}`;
    for (let i = 1; i < simples.length; i++) d += `L${n(simples[i][0])} ${n(simples[i][1])}`;
    if (parte.fechada) d += "Z";
  }
  return d;
}
