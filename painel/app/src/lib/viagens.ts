import type { Viagem } from "@/content";

// Viagens lidas das caixas neste computador (spec 030, decisão 7). A leitura da caixa (spec 004) ainda não existe, então
// não há viagem nenhuma: Viagens, o relatório, a busca rápida e o menu mostram o estado vazio. Quando a leitura chegar,
// só este arquivo passa a buscar na ponte; as telas e as regras (src/content) continuam iguais.
const NENHUMA: readonly Viagem[] = [];

/** As viagens lidas, da que chegou por último para a mais antiga. */
export function useViagens(): readonly Viagem[] {
  return NENHUMA;
}

export const viagemPorId = (viagens: readonly Viagem[], id: string | null) => (id ? viagens.find((viagem) => viagem.id === id) : undefined);
