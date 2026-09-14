// Funções da equipe (spec 014, decisão 3) e formatos usados nas telas de Equipe.
import type { Funcao, Usuario } from "@/lib/bridge";

export { NOME_FUNCAO } from "@/lib/bridge";

export const FUNCOES: Funcao[] = ["administrador", "supervisor", "consulta"];

export const FRASE_FUNCAO: Record<Funcao, string> = {
  administrador: "Faz tudo: viagens, vídeos, cadastros, equipe, configurações e cópia de segurança.",
  supervisor: "Lê a caixa, vê os vídeos, verifica os momentos e cadastra motoristas e veículos.",
  consulta: "Só vê as viagens e imprime os relatórios. Não vê vídeo.",
};

/** Tabela "O que cada função pode fazer" (mesma regra de PERMISSOES em @/lib/bridge, em frases). */
export const TABELA_PERMISSOES: { texto: string; funcoes: Funcao[] }[] = [
  { texto: "Ver viagens e imprimir relatórios", funcoes: ["administrador", "supervisor", "consulta"] },
  { texto: "Ver os vídeos curtos", funcoes: ["administrador", "supervisor"] },
  { texto: "Ler a caixa e verificar os momentos", funcoes: ["administrador", "supervisor"] },
  { texto: "Cadastrar motoristas e veículos", funcoes: ["administrador", "supervisor"] },
  { texto: "Equipe, configurações e registro de atividades", funcoes: ["administrador"] },
];

/** "Marina Lopes da Silva" → "marina.silva" (sem acento, só letras, números e ponto). */
export function sugerirUsuario(nome: string) {
  const partes = nome
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, " ")
    .split(/\s+/)
    .filter((parte) => parte && !["da", "de", "do", "das", "dos", "e"].includes(parte));
  if (partes.length === 0) return "";
  return partes.length === 1 ? partes[0] : `${partes[0]}.${partes[partes.length - 1]}`;
}

const doisDigitos = (numero: number) => String(numero).padStart(2, "0");

/** "Hoje às 06:58", "Ontem às 18:20", "10/09 às 09:12". */
export function quando(iso: string | null, agora = new Date()) {
  if (!iso) return "Nunca entrou";
  const data = new Date(iso);
  if (Number.isNaN(data.getTime())) return iso;
  const horario = `${doisDigitos(data.getHours())}:${doisDigitos(data.getMinutes())}`;
  const inicioDoDia = (valor: Date) => new Date(valor.getFullYear(), valor.getMonth(), valor.getDate()).getTime();
  const dias = Math.round((inicioDoDia(agora) - inicioDoDia(data)) / 86_400_000);
  if (dias === 0) return `Hoje às ${horario}`;
  if (dias === 1) return `Ontem às ${horario}`;
  const ano = data.getFullYear() === agora.getFullYear() ? "" : `/${data.getFullYear()}`;
  return `${doisDigitos(data.getDate())}/${doisDigitos(data.getMonth() + 1)}${ano} às ${horario}`;
}

export function situacaoDe(pessoa: Usuario) {
  if (!pessoa.ativo) return "Desativado";
  if (pessoa.trocar_senha) return "Ainda não trocou a senha";
  return "Ativo";
}
