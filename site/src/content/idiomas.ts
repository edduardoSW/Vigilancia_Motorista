import type { Locale } from "@/i18n/routing";

export type FlagCode = "br" | "us" | "es" | "fr" | "cn";

export interface Idioma {
  locale: Locale;
  /** Nome do idioma escrito no próprio idioma. */
  idioma: string;
  /** País da bandeira, escrito no próprio idioma. */
  pais: string;
  bandeira: FlagCode;
  /** Valor para hreflang e <html lang>. */
  htmlLang: string;
}

/** Ordem do seletor no cabeçalho. Para trocar o país de um idioma, mude `pais` e `bandeira`. */
export const idiomas: Idioma[] = [
  { locale: "pt-BR", idioma: "Português", pais: "Brasil", bandeira: "br", htmlLang: "pt-BR" },
  { locale: "en", idioma: "English", pais: "United States", bandeira: "us", htmlLang: "en" },
  { locale: "es", idioma: "Español", pais: "España", bandeira: "es", htmlLang: "es" },
  { locale: "fr", idioma: "Français", pais: "France", bandeira: "fr", htmlLang: "fr" },
  { locale: "zh-CN", idioma: "中文", pais: "中国", bandeira: "cn", htmlLang: "zh-CN" },
];

export function idiomaDe(locale: string): Idioma {
  return idiomas.find((i) => i.locale === locale) ?? idiomas[0];
}
