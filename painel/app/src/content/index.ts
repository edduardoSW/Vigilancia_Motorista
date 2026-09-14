// Dados fictícios da prévia (spec 012) e as regras que o servidor já usa (servidor/backend/alert_types.py).
import bruto from "./demo.json";
import tiposBrutos from "./tipos-de-evento.json";

export type Categoria = "sonolencia" | "celular" | "ativacao" | "jornada" | "distracao" | "sistema";
export type ResultadoRevisao = "confirmado" | "alarme_falso" | "orientado";

export interface Revisao {
  resultado: ResultadoRevisao;
  por: string;
  em: string;
  nota?: string;
}

export interface Evento {
  id: string;
  hora: string;
  tipo: string;
  risco: number;
  duracaoS: number;
  episodio?: string;
  revisao?: Revisao;
}

export interface ParteJornada {
  inicio: string;
  fim: string;
  tipo: "direcao" | "pausa";
}

export interface Episodio {
  id: string;
  titulo: string;
  inicio: string;
  fim: string;
  resumo: string;
  trecho: { duracaoS: number; situacao: string } | null;
}

export interface Viagem {
  id: string;
  veiculo: string;
  tipo: "onibus" | "caminhao";
  motorista: string;
  linha: string;
  saida: string;
  chegada: string;
  caixa: string;
  revisao: "pendente" | "concluida";
  integridade: { situacao: "conferida" | "importando" | "falhou"; blocos: number; detalhe: string };
  saudeCaixa: { temperaturaMaxC: number; quedasEnergia: number; semVisaoRostoMin: number; relogio: string };
  jornada: ParteJornada[];
  eventos: Evento[];
  episodios: Episodio[];
}

export type SituacaoVeiculo = "coletada" | "importando" | "revisada" | "em_viagem" | "pronta" | "atencao";

export interface Veiculo {
  prefixo: string;
  tipo: "onibus" | "caminhao";
  descricao: string;
  caixa: string;
  situacao: SituacaoVeiculo;
  detalhe: string;
  viagem: string | null;
}

export interface Motorista {
  id: string;
  nome: string;
  iniciais: string;
  consentimento: "registrado" | "pendente";
}

export interface Coleta {
  caixa: string;
  veiculo: string;
  motorista: string;
  saida: string;
  chegada: string;
  conectadaEm: string;
  progresso: number;
  etapas: { nome: string; detalhe: string; feita: boolean }[];
}

export interface Demo {
  aviso: string;
  empresa: { nome: string; garagem: string };
  agora: string;
  motoristas: Motorista[];
  veiculos: Veiculo[];
  coletas: Coleta[];
  viagens: Viagem[];
}

export const dados = bruto as unknown as Demo;
export const tipos = tiposBrutos as Record<string, { rotulo: string; categoria: Categoria }>;

// Igual ao servidor: aviso de sistema e evento de risco 1 não pedem revisão humana.
const REVISAVEIS = new Set<Categoria>(["sonolencia", "celular", "ativacao", "jornada", "distracao"]);
const RISCO_MINIMO = 2;
// Direção contínua: CTB, art. 67-C (5 h 30 min). Madrugada: 00:00 a 06:59 (PRD, RF-03).
export const LIMITE_DIRECAO_MIN = 330;

export const rotuloDe = (tipo: string) => tipos[tipo]?.rotulo ?? tipo;
/** Nome sem a explicação entre parênteses, para listas densas. */
export const rotuloCurto = (tipo: string) => rotuloDe(tipo).replace(/\s*\(.*\)$/, "");
export const categoriaDe = (tipo: string): Categoria => tipos[tipo]?.categoria ?? "sistema";
export const precisaRevisao = (evento: Evento) => REVISAVEIS.has(categoriaDe(evento.tipo)) && evento.risco >= RISCO_MINIMO;

export const viagemDe = (id: string) => dados.viagens.find((viagem) => viagem.id === id);
export const motoristaDe = (id: string) => dados.motoristas.find((motorista) => motorista.id === id);
export const veiculoDe = (prefixo: string) => dados.veiculos.find((veiculo) => veiculo.prefixo === prefixo);
export const nomeDoVeiculo = (tipo: "onibus" | "caminhao", prefixo: string) => `${tipo === "onibus" ? "Ônibus" : "Caminhão"} ${prefixo}`;

const minutos = (iso: string) => Date.parse(iso) / 60000;
export const minutosEntre = (inicio: string, fim: string) => Math.round(minutos(fim) - minutos(inicio));
export const hora = (iso: string) => iso.slice(11, 16);
export const dia = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}`;
export const dataLonga = (iso: string) => new Date(iso).toLocaleDateString("pt-BR", { weekday: "long", day: "numeric", month: "long" });

const dois = (numero: number) => String(numero).padStart(2, "0");
export const isoLocal = (data: Date) =>
  `${data.getFullYear()}-${dois(data.getMonth() + 1)}-${dois(data.getDate())}T${dois(data.getHours())}:${dois(data.getMinutes())}`;
export const somarMinutos = (iso: string, total: number) => isoLocal(new Date(Date.parse(iso) + total * 60000));

export function duracao(totalMinutos: number) {
  const h = Math.floor(totalMinutos / 60);
  const m = totalMinutos % 60;
  if (!h) return `${m} min`;
  return m ? `${h} h ${dois(m)} min` : `${h} h`;
}

export function segundos(valor: number) {
  if (valor >= 60) return duracao(Math.round(valor / 60));
  return `${valor.toLocaleString("pt-BR", { maximumFractionDigits: 1 })} s`;
}

/** Posição de 0 a 1 de um instante na linha do tempo da viagem. */
export function posicao(viagem: Viagem, iso: string) {
  const total = minutosEntre(viagem.saida, viagem.chegada);
  return Math.min(1, Math.max(0, minutosEntre(viagem.saida, iso) / total));
}

function diasDaViagem(viagem: Viagem) {
  const dias: string[] = [];
  for (let d = new Date(`${viagem.saida.slice(0, 10)}T00:00`); d.getTime() <= Date.parse(viagem.chegada); d.setDate(d.getDate() + 1)) {
    dias.push(isoLocal(d).slice(0, 10));
  }
  return dias;
}

/** Faixas da madrugada (00:00 a 06:59) dentro da viagem, em posições de 0 a 1. */
export function faixasMadrugada(viagem: Viagem): [number, number][] {
  return diasDaViagem(viagem)
    .map((data): [number, number] => [posicao(viagem, `${data}T00:00`), posicao(viagem, `${data}T07:00`)])
    .filter(([a, b]) => b > a);
}

export function minutosNaMadrugada(viagem: Viagem) {
  const total = minutosEntre(viagem.saida, viagem.chegada);
  return Math.round(faixasMadrugada(viagem).reduce((soma, [a, b]) => soma + (b - a) * total, 0));
}

export function maiorDirecaoContinua(viagem: Viagem) {
  return Math.max(0, ...viagem.jornada.filter((parte) => parte.tipo === "direcao").map((parte) => minutosEntre(parte.inicio, parte.fim)));
}

export function contagemPorCategoria(viagem: Viagem) {
  const contagem: Partial<Record<Categoria, number>> = {};
  for (const evento of viagem.eventos) {
    const categoria = categoriaDe(evento.tipo);
    if (categoria !== "sistema") contagem[categoria] = (contagem[categoria] ?? 0) + 1;
  }
  return contagem;
}

export function resumoDaViagem(viagem: Viagem) {
  const pausas = viagem.jornada.filter((parte) => parte.tipo === "pausa");
  const paraRevisar = viagem.eventos.filter(precisaRevisao);
  return {
    duracaoMin: minutosEntre(viagem.saida, viagem.chegada),
    maiorDirecaoMin: maiorDirecaoContinua(viagem),
    pausaMin: pausas.reduce((total, parte) => total + minutosEntre(parte.inicio, parte.fim), 0),
    pausas: pausas.length,
    madrugadaMin: minutosNaMadrugada(viagem),
    detectados: viagem.eventos.filter((evento) => categoriaDe(evento.tipo) !== "sistema").length,
    paraRevisar: paraRevisar.length,
    pendentes: paraRevisar.filter((evento) => !evento.revisao).length,
    confirmados: paraRevisar.filter((evento) => evento.revisao?.resultado === "confirmado").length,
  };
}

export interface ItemRevisao {
  evento: Evento;
  viagem: Viagem;
}

export function filaDeRevisao(): ItemRevisao[] {
  return dados.viagens.flatMap((viagem) => viagem.eventos.filter(precisaRevisao).map((evento) => ({ evento, viagem })));
}

export const NOME_CATEGORIA: Record<Categoria, string> = {
  sonolencia: "Sono",
  celular: "Celular",
  ativacao: "Ativação atípica",
  jornada: "Jornada",
  distracao: "Distração",
  sistema: "Avisos da caixa",
};

export const NOME_RESULTADO: Record<ResultadoRevisao, string> = {
  confirmado: "Confirmado",
  alarme_falso: "Alarme falso",
  orientado: "Motorista orientado",
};
