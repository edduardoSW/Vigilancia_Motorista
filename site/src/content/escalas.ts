export type EscalaId = "mundo" | "brasil" | "rota" | "rodovia" | "cabine" | "olho" | "garagem" | "relatorio";

export interface Escala {
  id: EscalaId;
  /** id da seção na página (âncora em português). */
  secao: string;
  /** Escala cartográfica mostrada na régua. Na cabine e no olho é figurada, não medida. */
  valor: string;
  /** Escalas onde a imagem da câmera existe (dentro da caixa). */
  imagem?: boolean;
}

export const escalas: Escala[] = [
  { id: "mundo", secao: "inicio", valor: "1:40 000 000" },
  { id: "brasil", secao: "malha", valor: "1:5 000 000" },
  { id: "rota", secao: "rota", valor: "1:1 000 000" },
  { id: "rodovia", secao: "rodovia", valor: "1:50 000" },
  { id: "cabine", secao: "cabine", valor: "1:20", imagem: true },
  { id: "olho", secao: "registro", valor: "1:1", imagem: true },
  { id: "garagem", secao: "chegada", valor: "1:200" },
  { id: "relatorio", secao: "relatorio", valor: "1:1 000 000" },
];

export function escala(id: EscalaId): Escala {
  const e = escalas.find((x) => x.id === id);
  if (!e) throw new Error(`Escala desconhecida: ${id}`);
  return e;
}
