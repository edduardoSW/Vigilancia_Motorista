// Menu da coluna da esquerda (spec 014, áreas do painel). A mesma lista serve o menu e a busca rápida (Ctrl+K).
// Só importa tipos: o teste lê este arquivo direto no Node (scripts/testes/shell.test.mjs).
import type { GlyphName } from "@/components/ui/glyph";
import type { Acao } from "@/lib/bridge";

export interface ItemMenu {
  href: string;
  rotulo: string;
  icone: GlyphName;
  /** Ação exigida para o item aparecer (spec 014, decisão 3). */
  acao: Acao;
  /** "rodape": fica embaixo, junto de quem entrou. */
  grupo: "principal" | "rodape";
}

export const ITENS_MENU: readonly ItemMenu[] = [
  { href: "/", rotulo: "Início", icone: "home", acao: "ver_viagens", grupo: "principal" },
  { href: "/viagens/", rotulo: "Viagens", icone: "trips", acao: "ver_viagens", grupo: "principal" },
  { href: "/motoristas/", rotulo: "Motoristas", icone: "driver", acao: "ver_viagens", grupo: "principal" },
  { href: "/veiculos/", rotulo: "Veículos e caixas", icone: "vehicle", acao: "ver_viagens", grupo: "principal" },
  { href: "/equipe/", rotulo: "Equipe", icone: "team", acao: "equipe", grupo: "principal" },
  { href: "/configuracoes/", rotulo: "Configurações", icone: "settings", acao: "configuracoes", grupo: "principal" },
  { href: "/ao-vivo/", rotulo: "Teste neste computador", icone: "live", acao: "ver_viagens", grupo: "rodape" },
  { href: "/guia/", rotulo: "Guia de uso", icone: "book", acao: "ver_viagens", grupo: "rodape" },
];

/** Itens que a função de quem entrou pode abrir, na ordem da spec 014. */
export const itensDoMenu = (pode: (acao: Acao) => boolean) => ITENS_MENU.filter((item) => pode(item.acao));

const semBarra = (caminho: string) => caminho.replace(/\/+$/, "") || "/";

/** Endereço do item marcado para a tela aberta. O relatório de uma viagem marca Viagens. */
export function itemAtivo(rota: string, itens: readonly ItemMenu[] = ITENS_MENU): string | null {
  const atual = semBarra(rota || "/");
  const item = itens.find((candidato) => {
    const base = semBarra(candidato.href);
    return base === "/" ? atual === "/" : atual === base || atual.startsWith(`${base}/`);
  });
  return item?.href ?? null;
}
