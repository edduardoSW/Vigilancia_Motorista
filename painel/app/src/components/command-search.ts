// Regra da busca rápida (Ctrl+K): telas, viagens, motoristas, veículos e guia, sem acento e sem maiúscula.
// Sem importação: o teste lê este arquivo direto no Node (scripts/testes/shell.test.mjs).

export interface ItemBusca {
  id: string;
  grupo: string;
  titulo: string;
  detalhe?: string;
  /** Texto que também conta na busca sem aparecer (por exemplo, "onibus" para "Ônibus 2240"). */
  palavras?: string;
  href: string;
}

export const normalizarBusca = (texto: string) => texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

/** Todas as palavras precisam aparecer. Título que começa com a primeira palavra vem antes; no máximo N por grupo. */
export function buscarNaPaleta(consulta: string, itens: ItemBusca[], limitePorGrupo = 5): ItemBusca[] {
  const palavras = normalizarBusca(consulta).split(/\s+/).filter(Boolean);
  if (!palavras.length) return [];

  const grupos = new Map<string, { item: ItemBusca; ordem: number; peso: number }[]>();
  itens.forEach((item, ordem) => {
    const titulo = normalizarBusca(item.titulo);
    const tudo = [titulo, normalizarBusca(item.detalhe ?? ""), normalizarBusca(item.palavras ?? "")].join(" ");
    if (!palavras.every((palavra) => tudo.includes(palavra))) return;
    const peso = titulo.startsWith(palavras[0]) ? 0 : titulo.includes(palavras[0]) ? 1 : 2;
    grupos.set(item.grupo, [...(grupos.get(item.grupo) ?? []), { item, ordem, peso }]);
  });

  return [...grupos.values()].flatMap((lista) =>
    lista
      .sort((a, b) => a.peso - b.peso || a.ordem - b.ordem)
      .slice(0, limitePorGrupo)
      .map((achado) => achado.item),
  );
}
