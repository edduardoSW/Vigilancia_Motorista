// Campos do vídeo do momento (spec 019, VID-01 e VID-02): até quando fica guardado e a situação.
// Sem importação: o teste lê este arquivo direto no Node (scripts/testes/shell.test.mjs).

export type SituacaoVideo = "disponivel" | "trancado" | "apagado";

const dois = (numero: number) => String(numero).padStart(2, "0");

/** "Fica guardado até": o dia da coleta mais o prazo de Configurações, contado só em dias (sem fuso). */
export function guardadoAte(coletadoEm: string, dias: number): string {
  const [ano, mes, dia] = coletadoEm.slice(0, 10).split("-").map(Number);
  const data = new Date(Date.UTC(ano, mes - 1, dia + dias));
  return `${data.getUTCFullYear()}-${dois(data.getUTCMonth() + 1)}-${dois(data.getUTCDate())}`;
}

/** Segundos entre o início e o fim do trecho gravado. */
export const duracaoDoTrecho = (inicio: string, fim: string) => Math.max(0, Math.round((Date.parse(fim) - Date.parse(inicio)) / 1000));

/** Apagado pelo prazo vem antes de trancado: depois do prazo o vídeo não existe mais, com ou sem termo. */
export function situacaoDoVideo({
  coletadoEm,
  dias,
  hoje,
  termoAssinado,
}: {
  coletadoEm: string;
  dias: number;
  /** AAAA-MM-DD */
  hoje: string;
  termoAssinado: boolean;
}): { tipo: SituacaoVideo; texto: string } {
  if (hoje > guardadoAte(coletadoEm, dias)) return { tipo: "apagado", texto: `Apagado pelo prazo de ${dias} dias` };
  if (!termoAssinado) return { tipo: "trancado", texto: "Trancado: falta o termo de ciência do motorista" };
  return { tipo: "disponivel", texto: "Disponível" };
}

/** Por que o momento não tem vídeo: a caixa grava trecho curto só quando o sinal pede (definição de 11/09/2026). */
export function motivoSemVideo(tipo: string) {
  if (tipo === "direcao_continua") return "Aviso de tempo de direção: não tem vídeo.";
  if (tipo === "atencao") return "A caixa não grava os primeiros sinais de sono, só quando o sinal se repete.";
  return "A caixa não gravou vídeo neste momento.";
}
