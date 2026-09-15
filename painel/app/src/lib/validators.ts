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

/** CPF que já veio mascarado da ponte (o Python nunca devolve o CPF inteiro na lista). */
export const cpfMascarado = (valor: string | null | undefined) => (valor ?? "").includes("•");

/** Na lista o CPF aparece só com o miolo: •••.•••.247-••. O que já veio mascarado passa como está. */
export function mascararCpf(valor: string | null | undefined) {
  if (cpfMascarado(valor)) return valor ?? "";
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

// Spec 019 · termo assinado importado como comprovante (decisão 5). A tela confere nome, tamanho e data antes de ler o
// arquivo; o Python confere de novo pelos primeiros bytes e grava o SHA-256 (TER-01 e TER-02).

/** Maior arquivo de termo aceito (TER-01). */
export const TERMO_MAX_BYTES = 10 * 1024 * 1024;

/** O que o seletor de arquivo mostra; quem decide é o Python, pelos primeiros bytes. */
export const TERMO_ACEITA = ".pdf,.png,.jpg,.jpeg";

const EXTENSOES_TERMO = new Set(["pdf", "png", "jpg", "jpeg"]);

export function validarArquivoTermo(arquivo: { nome: string; bytes: number } | null | undefined): string | null {
  if (!arquivo) return "Escolha o arquivo do termo assinado.";
  const extensao = /\.([a-z0-9]+)$/i.exec(arquivo.nome.trim())?.[1]?.toLowerCase();
  if (!extensao || !EXTENSOES_TERMO.has(extensao)) return "Use um PDF ou uma foto (PNG ou JPEG) do termo assinado.";
  if (arquivo.bytes <= 0) return "O arquivo está vazio. Escolha o arquivo do termo assinado.";
  if (arquivo.bytes > TERMO_MAX_BYTES) return "O arquivo pode ter até 10 MB.";
  return null;
}

/** Data da assinatura: obrigatória e nunca depois de hoje (TER-01). */
export function validarDataTermo(data: string | null | undefined, hoje: string): string | null {
  if (!data || !/^\d{4}-\d{2}-\d{2}$/.test(data)) return "Informe a data em que o termo foi assinado.";
  if (data > hoje) return "A data não pode ser depois de hoje.";
  return null;
}

/** "data:application/pdf;base64,JVBER..." (FileReader.readAsDataURL) → "JVBER...", que é o que a ponte recebe. */
export function conteudoBase64(dataUrl: string | null | undefined) {
  const texto = dataUrl ?? "";
  const marca = texto.indexOf(";base64,");
  return texto.startsWith("data:") && marca !== -1 ? texto.slice(marca + ";base64,".length) : "";
}

/** "212 KB", "1,4 MB". Nunca "0 KB". */
export function tamanhoArquivo(bytes: number) {
  const kb = Math.max(1, Math.round(bytes / 1024));
  if (kb < 1024) return `${kb} KB`;
  const mb = Math.round((bytes / (1024 * 1024)) * 10) / 10;
  return `${String(mb).replace(".", ",")} MB`;
}

const doisDigitos = (numero: number) => String(numero).padStart(2, "0");
const soData = (texto: string) => /^\d{4}-\d{2}-\d{2}$/.test(texto);

function instante(iso: string) {
  const data = new Date(iso);
  return Number.isNaN(data.getTime()) ? null : data;
}

/** "2026-09-15T15:00:00Z" → "15/09/2026", no dia deste computador. Data sem hora fica como está. */
export function dataLocal(iso: string) {
  if (soData(iso)) return formatarData(iso);
  const data = instante(iso);
  return data ? formatarData(hojeIso(data)) : iso;
}

/** "15/09/2026 às 10:07", no relógio deste computador. Data sem hora fica só com a data. */
export function dataHoraLocal(iso: string) {
  if (soData(iso)) return formatarData(iso);
  const data = instante(iso);
  if (!data) return iso;
  return `${formatarData(hojeIso(data))} às ${doisDigitos(data.getHours())}:${doisDigitos(data.getMinutes())}`;
}

export interface TermoParaFrase {
  assinado: boolean;
  data: string | null;
  versao: string | null;
  arquivo: { nome: string; bytes: number; importado_em: string; importado_por: string } | null;
}

/**
 * Situação do termo em frase, na janela do motorista:
 * "Assinado em 02/09/2026 · versão 1 · termo-carlos.pdf (212 KB), importado por Marina Lopes em 15/09/2026";
 * "Assinado em 02/09/2026 · sem o arquivo do termo"; "Falta registrar. Os vídeos ficam trancados." (em alarme).
 */
export function fraseDoTermo(termo: TermoParaFrase): { texto: string; alarme: boolean } {
  if (!termo.assinado) return { texto: "Falta registrar. Os vídeos ficam trancados.", alarme: true };
  const assinado = termo.data ? `Assinado em ${formatarData(termo.data)}` : "Assinado";
  if (!termo.arquivo) return { texto: `${assinado} · sem o arquivo do termo`, alarme: false };
  const { nome, bytes, importado_por, importado_em } = termo.arquivo;
  const versao = termo.versao ? ` · versão ${termo.versao}` : "";
  return { texto: `${assinado}${versao} · ${nome} (${tamanhoArquivo(bytes)}), importado por ${importado_por} em ${dataLocal(importado_em)}`, alarme: false };
}

export interface RegistroParaHistorico {
  assinado: boolean;
  data: string | null;
  versao: string | null;
  registrado_por: string | null;
  registrado_em: string;
  arquivo: { nome: string; bytes: number } | null;
}

/** Uma linha do "Histórico do termo" (TER-03): nada é apagado, revogar também é registro. */
export function registroDoTermo(registro: RegistroParaHistorico) {
  const assinado = registro.data ? `Assinado em ${formatarData(registro.data)}` : "Assinado";
  const titulo = registro.assinado ? `${assinado}${registro.versao ? ` · versão ${registro.versao}` : ""}` : "Termo revogado";
  const arquivo = registro.arquivo ? `${registro.arquivo.nome} (${tamanhoArquivo(registro.arquivo.bytes)})` : "Sem arquivo";
  const quando = dataHoraLocal(registro.registrado_em);
  const quem = registro.registrado_por ? `Registrado por ${registro.registrado_por} em ${quando}` : `Registrado em ${quando}`;
  return { titulo, arquivo, quem };
}
