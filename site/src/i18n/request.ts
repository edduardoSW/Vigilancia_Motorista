import * as rootParams from "next/root-params";
import { hasLocale } from "next-intl";
import { getRequestConfig } from "next-intl/server";
import { notFound } from "next/navigation";
import { routing } from "./routing";

// next-intl 4 com Next 16: o idioma vem do segmento raiz [locale] via next/root-params,
// sem setRequestLocale (depreciado). Em Server Actions o root-params não funciona:
// lá o idioma é passado por parâmetro.
export default getRequestConfig(async ({ locale: explicito }) => {
  const valor = explicito ?? (await rootParams.locale());
  if (!hasLocale(routing.locales, valor)) notFound();

  return {
    locale: valor,
    timeZone: "America/Sao_Paulo",
    messages: (await import(`../../messages/${valor}.json`)).default,
  };
});
