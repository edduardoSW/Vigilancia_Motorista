// Spec 025 · onda do pulso ao vivo num canvas pequeno: os últimos segundos medidos, na cor de ação do tema quando o
// sinal é bom e apagada quando é fraco. Estimativa pela câmera, não é medida médica.
import { rgba, type CoresDoTema } from "./camera-cores";

export function desenharOnda(canvas: HTMLCanvasElement, trecho: ArrayLike<number> | null, confiavel: boolean, cores: CoresDoTema): void {
  const densidade = Math.min(2, window.devicePixelRatio || 1);
  const largura = Math.round(canvas.clientWidth * densidade);
  const altura = Math.round(canvas.clientHeight * densidade);
  if (!largura || !altura) return;
  if (canvas.width !== largura || canvas.height !== altura) {
    canvas.width = largura;
    canvas.height = altura;
  }
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  ctx.clearRect(0, 0, largura, altura);
  const meio = altura / 2;
  ctx.beginPath();
  ctx.moveTo(0, meio);
  ctx.lineTo(largura, meio);
  ctx.lineWidth = densidade;
  ctx.strokeStyle = rgba(cores.fio, 1);
  ctx.stroke();
  if (!trecho || trecho.length < 2) return;
  const margem = 4 * densidade;
  const ponto = (i: number): [number, number] => [(i / (trecho.length - 1)) * (largura - margem * 2) + margem, meio - trecho[i] * (meio - margem)];
  ctx.beginPath();
  for (let i = 0; i < trecho.length; i++) {
    const [x, y] = ponto(i);
    if (i) ctx.lineTo(x, y);
    else ctx.moveTo(x, y);
  }
  const cor = confiavel ? cores.verde : cores.apagado;
  ctx.lineWidth = 2 * densidade;
  ctx.lineJoin = "round";
  ctx.strokeStyle = rgba(cor, 1);
  ctx.stroke();
  const [x, y] = ponto(trecho.length - 1);
  ctx.beginPath();
  ctx.arc(x, y, 3 * densidade, 0, Math.PI * 2);
  ctx.fillStyle = rgba(cor, 1);
  ctx.fill();
}
