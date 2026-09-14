// Spec 015 · regras puras do cadastro (motoristas e veículos), sem React e sem importação, para o Node testar direto
// (scripts/testes/cadastros.test.mjs). Cada validar* devolve a frase do erro em pt-BR ou null quando está certo.
// O Python (painel/desktop/cadastros.py) confere de novo ao salvar; a tela só avisa antes.

export type SituacaoCnh = "ok" | "vence_em_breve" | "vencida";

/** Dias de antecedência do aviso de CNH (spec 015, decisão 3). */
export const AVISO_CNH_DIAS = 30;

export const soDigitos = (valor: string | null | undefined) => (valor ?? "").replace(/\D/g, "");

function contagem(nome: string, digitos: string, total: number) {
  const diferenca = total - digitos.length;
  if (diferenca > 0) return `${nome} tem ${total} números. ${diferenca === 1 ? "Faltou 1" : `Faltaram ${diferenca}`}.`;
  return `${nome} tem ${total} números. ${diferenca === -1 ? "Sobrou 1" : `Sobraram ${-diferenca}`}.`;
}

const repetido = (digitos: string) => /^(\d)\1+$/.test(digitos);

/**
 * CNH: 11 números, os 2 últimos são dígitos verificadores (módulo 11), na mesma variante do demo-backend.ts.
 * 1º: pesos 9..1; resto ≥ 10 vira 0 e dá desconto 2 no 2º. 2º: pesos 1..9; resto ≥ 10 vira 0, senão resto − desconto
 * (negativo: aquela base não tem CNH válida).
 */
export function validarCnh(valor: string | null | undefined): string | null {
  const digitos = soDigitos(valor);
  if (!digitos) return "Informe o número da CNH.";
  if (digitos.length !== 11) return contagem("A CNH", digitos, 11);
  const numeros = [...digitos].map(Number);
  let soma = 0;
  for (let i = 0; i < 9; i++) soma += numeros[i] * (9 - i);
  let primeiro = soma % 11;
  let desconto = 0;
  if (primeiro >= 10) {
    primeiro = 0;
    desconto = 2;
  }
  soma = 0;
  for (let i = 0; i < 9; i++) soma += numeros[i] * (i + 1);
  const resto = soma % 11;
  const segundo = resto >= 10 ? 0 : resto - desconto;
  if (repetido(digitos) || numeros[9] !== primeiro || numeros[10] !== segundo) {
    return "Número da CNH inválido. Confira os dois últimos números.";
  }
  return null;
}

/** CPF opcional (spec 015, pergunta 1): vazio passa; informado confere os 2 dígitos verificadores. */
export function validarCpf(valor: string | null | undefined): string | null {
  const digitos = soDigitos(valor);
  if (!digitos) return null;
  if (digitos.length !== 11) return contagem("O CPF", digitos, 11);
  const numeros = [...digitos].map(Number);
  const digito = (quantos: number) => {
    let soma = 0;
    for (let i = 0; i < quantos; i++) soma += numeros[i] * (quantos + 1 - i);
    const resto = (soma * 10) % 11;
    return resto === 10 ? 0 : resto;
  };
  if (repetido(digitos) || digito(9) !== numeros[9] || digito(10) !== numeros[10]) return "CPF inválido. Confira os números.";
  return null;
}

/** Na lista o CPF aparece só com o miolo: •••.•••.247-••. */
export function mascararCpf(valor: string | null | undefined) {
  const digitos = soDigitos(valor);
  return digitos.length === 11 ? `•••.•••.${digitos.slice(6, 9)}-••` : "";
}

const MERCOSUL = /^[A-Z]{3}\d[A-Z]\d{2}$/;
const ANTIGA = /^[A-Z]{3}-?\d{4}$/;

export function validarPlaca(valor: string | null | undefined): string | null {
  const placa = (valor ?? "").trim().toUpperCase();
  if (!placa) return "Informe a placa.";
  if (MERCOSUL.test(placa) || ANTIGA.test(placa)) return null;
  return "Placa inválida. Use o formato ABC1D23 (nova) ou ABC-1234 (antiga).";
}

/** Placa em maiúsculas; a antiga sempre com hífen (ABC-1234). */
export function normalizarPlaca(valor: string) {
  const placa = valor.trim().toUpperCase();
  return /^[A-Z]{3}\d{4}$/.test(placa) ? `${placa.slice(0, 3)}-${placa.slice(3)}` : placa;
}

const PARTICULAS = new Set(["de", "da", "das", "do", "dos", "e"]);
const capitalizar = (palavra: string) => palavra.charAt(0).toLocaleUpperCase("pt-BR") + palavra.slice(1).toLocaleLowerCase("pt-BR");

/** Nome nos relatórios sugerido (MOT-03): "Carlos Menezes" → "Carlos M.". */
export function nomeCurto(nomeCompleto: string) {
  const partes = nomeCompleto.trim().split(/\s+/).filter(Boolean);
  if (!partes.length) return "";
  const primeiro = capitalizar(partes[0]);
  const sobrenome = partes.slice(1).filter((parte) => !PARTICULAS.has(parte.toLocaleLowerCase("pt-BR"))).at(-1);
  return sobrenome ? `${primeiro} ${sobrenome.charAt(0).toLocaleUpperCase("pt-BR")}.` : primeiro;
}

const dataDoDia = (data: string | Date) => {
  if (typeof data === "string") {
    const [ano, mes, dia] = data.slice(0, 10).split("-").map(Number);
    return Date.UTC(ano, mes - 1, dia);
  }
  return Date.UTC(data.getFullYear(), data.getMonth(), data.getDate());
};

/** Dias inteiros de hoje até a data (negativo = já passou). Conta só o dia, sem fuso nem horário de verão. */
export function diasAte(data: string, hoje: string | Date) {
  return Math.round((dataDoDia(data) - dataDoDia(hoje)) / 86_400_000);
}

/** MOT-06: aviso a partir de 30 dias antes; a CNH vale até o fim do dia da validade. */
export function situacaoCnh(validade: string, hoje: string | Date): SituacaoCnh {
  const dias = diasAte(validade, hoje);
  if (dias < 0) return "vencida";
  return dias <= AVISO_CNH_DIAS ? "vence_em_breve" : "ok";
}

/** "2026-09-26" → "26/09/2026". */
export const formatarData = (data: string) => `${data.slice(8, 10)}/${data.slice(5, 7)}/${data.slice(0, 4)}`;

/** "2028-03-31" → "03/2028". */
export const mesAno = (data: string) => `${data.slice(5, 7)}/${data.slice(0, 4)}`;

/** Hoje no formato AAAA-MM-DD, no relógio deste computador. */
export function hojeIso(agora = new Date()) {
  const dois = (numero: number) => String(numero).padStart(2, "0");
  return `${agora.getFullYear()}-${dois(agora.getMonth() + 1)}-${dois(agora.getDate())}`;
}
