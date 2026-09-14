import type { Caixa, Veiculo } from "@/lib/bridge";

// Nomes em pt-BR dos valores do cadastro de veículos e caixas (spec 015, decisões 4 e 5).

export const TIPO_VEICULO: Record<Veiculo["tipo"], string> = {
  onibus: "Ônibus",
  micro_onibus: "Micro-ônibus",
  caminhao: "Caminhão",
  van: "Van",
};

export const TRANSPORTA: Record<Veiculo["transporta"], { rotulo: string; regra: string }> = {
  passageiros: { rotulo: "Passageiros", regra: "Pausa de 30 min a cada 4 h dirigindo" },
  carga: { rotulo: "Carga", regra: "Pausa de 30 min a cada 6 h dirigindo" },
};

export const SITUACAO_VEICULO: Record<Veiculo["situacao"], string> = {
  em_uso: "Em uso",
  oficina: "Na oficina",
  fora_de_uso: "Fora de uso",
};

export const SITUACAO_CAIXA: Record<Caixa["situacao"], string> = {
  ok: "Funcionando",
  atencao: "Precisa de atenção",
  bloqueada: "Bloqueada pela RotaGuard",
};

/** "Ônibus 2240": o número do veículo é o nome usado em todo o painel. */
export const nomeDoVeiculo = (veiculo: Pick<Veiculo, "tipo" | "numero">) => `${TIPO_VEICULO[veiculo.tipo]} ${veiculo.numero}`;

/** "14/09/2026 às 05:48"; data sem hora fica só com a data. */
export function quando(iso: string | null) {
  if (!iso) return null;
  if (iso.length <= 10) return `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`;
  const data = new Date(iso);
  if (Number.isNaN(data.getTime())) return iso;
  return `${data.toLocaleDateString("pt-BR")} às ${data.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}`;
}
