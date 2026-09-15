import type { Motorista, MotoristaDados } from "@/lib/bridge";
import { diasAte, formatarData, mesAno, situacaoCnh } from "@/lib/validators";
import { plural } from "./use-list-shortcuts";

// Textos e dados do motorista usados na lista, nos cards e na janela (specs 015 e 019).

export const SITUACAO_MOTORISTA: Record<Motorista["situacao"], string> = {
  ativo: "Ativo",
  afastado: "Afastado",
  desligado: "Desligado",
};

/**
 * Aviso da CNH (MOT-06). `texto` vai na lista e na janela ("Vence em 11 dias (26/09/2026)"); `curto` cabe no card
 * ("Vence em 11 dias"). Em alarme só quando pede ação: vencendo em até 30 dias ou vencida.
 */
export function avisoCnh(validade: string, hoje: string) {
  const situacao = situacaoCnh(validade, hoje);
  if (situacao === "vencida") {
    const texto = `Vencida em ${formatarData(validade)}`;
    return { texto, curto: texto, alarme: true };
  }
  if (situacao === "vence_em_breve") {
    const dias = diasAte(validade, hoje);
    const curto = dias === 0 ? "Vence hoje" : `Vence em ${plural(dias, "dia", "dias")}`;
    return { texto: `${curto} (${formatarData(validade)})`, curto, alarme: true };
  }
  const texto = `Vale até ${mesAno(validade)}`;
  return { texto, curto: texto, alarme: false };
}

/** "Nenhum momento confirmado", "3 momentos confirmados". */
export const textoMomentos = (total: number) =>
  total === 0 ? "Nenhum momento confirmado" : plural(total, "momento confirmado", "momentos confirmados");

/** "Assinado em 02/09/2026" na lista e no card; a frase completa fica na janela (fraseDoTermo). */
export const termoCurto = (motorista: Motorista) => (motorista.termo.data ? `Assinado em ${formatarData(motorista.termo.data)}` : "Assinado");

/** O termo como está. O arquivo só entra por termo_importar; salvar o cadastro não muda o termo. */
export const termoAtual = (motorista: Motorista): NonNullable<MotoristaDados["termo"]> => ({
  assinado: motorista.termo.assinado,
  data: motorista.termo.data,
  versao: motorista.termo.versao,
});

/**
 * O cadastro inteiro, como a ponte espera ao salvar. O Python grava todos os campos de uma vez e, sem `termo`,
 * entende que o motorista não assinou; o CPF mascarado da lista quer dizer "manter o guardado".
 */
export function dadosDoMotorista(motorista: Motorista): MotoristaDados {
  return {
    id: motorista.id,
    nome: motorista.nome,
    nome_curto: motorista.nome_curto,
    matricula: motorista.matricula,
    telefone: motorista.telefone,
    cpf: motorista.cpf,
    cnh_numero: motorista.cnh_numero,
    cnh_categoria: motorista.cnh_categoria,
    cnh_validade: motorista.cnh_validade,
    situacao: motorista.situacao,
    observacoes: motorista.observacoes,
    termo: termoAtual(motorista),
  };
}
