// Spec 025 · cores dos desenhos em canvas (malha e onda do pulso) lidas dos tokens do globals.css, no tema aberto.
// O canvas não lê classe do Tailwind: a cor vem da variável --color-* do html (claro ou escuro), nunca fixa no código.

export type Rgb = [number, number, number];

export type CoresDoTema = {
  lima: Rgb;
  sobreVideo: Rgb;
  alarme: Rgb;
  verde: Rgb;
  apagado: Rgb;
  fio: Rgb;
};

const NEUTRO: Rgb = [128, 128, 128];

function lerCor(texto: string): Rgb | null {
  const valor = texto.trim();
  // O CSS gerado encurta a cor quando dá (branco de 6 dígitos vira 3): aceitar 3, 4, 6 e 8 dígitos.
  const curta = valor.match(/^#([0-9a-f])([0-9a-f])([0-9a-f])([0-9a-f])?$/i);
  if (curta) return [parseInt(curta[1] + curta[1], 16), parseInt(curta[2] + curta[2], 16), parseInt(curta[3] + curta[3], 16)];
  const longa = valor.match(/^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})?$/i);
  if (longa) return [parseInt(longa[1], 16), parseInt(longa[2], 16), parseInt(longa[3], 16)];
  const funcao = valor.match(/rgba?\(\s*([\d.]+)[\s,]+([\d.]+)[\s,]+([\d.]+)/i);
  if (funcao) return [Number(funcao[1]), Number(funcao[2]), Number(funcao[3])];
  return null;
}

export function coresDoTema(): CoresDoTema {
  const estilo = getComputedStyle(document.documentElement);
  const token = (nome: string) => lerCor(estilo.getPropertyValue(`--color-${nome}`)) ?? NEUTRO;
  return {
    lima: token("lima"),
    sobreVideo: token("sobre-video"),
    alarme: token("alarme"),
    verde: token("verde"),
    apagado: token("apagado"),
    fio: token("fio"),
  };
}

export const rgba = ([r, g, b]: Rgb, alfa: number) => `rgba(${r}, ${g}, ${b}, ${Math.max(0, Math.min(1, alfa))})`;
