export type Segmento = "carga" | "fretamento" | "urbano" | "geral";

export interface SiteConfig {
  /** Domínio público do site (canonical, Open Graph). Trocar quando o domínio for definido. */
  dominio: string;
  /** false enquanto o site for prévia: as páginas saem com noindex. */
  indexar: boolean;
  /**
   * WhatsApp e telefone só com dígitos, com DDI e DDD (ex.: 5511999990000).
   * Vazio = os botões aparecem desativados com o aviso "número ainda não configurado".
   * Pode vir do ambiente: NEXT_PUBLIC_ROTAGUARD_WHATSAPP e NEXT_PUBLIC_ROTAGUARD_TELEFONE.
   */
  whatsapp: string;
  telefone: string;
}

export const site: SiteConfig = {
  dominio: process.env.NEXT_PUBLIC_ROTAGUARD_DOMINIO || "https://rotaguard.example",
  indexar: process.env.NEXT_PUBLIC_ROTAGUARD_INDEXAR === "1",
  whatsapp: (process.env.NEXT_PUBLIC_ROTAGUARD_WHATSAPP || "").replace(/\D/g, ""),
  telefone: (process.env.NEXT_PUBLIC_ROTAGUARD_TELEFONE || "").replace(/\D/g, ""),
};

export function linkWhatsApp(mensagem: string): string | null {
  if (!site.whatsapp) return null;
  return `https://wa.me/${site.whatsapp}?text=${encodeURIComponent(mensagem)}`;
}

export function linkTelefone(): string | null {
  if (!site.telefone) return null;
  return `tel:+${site.telefone}`;
}
