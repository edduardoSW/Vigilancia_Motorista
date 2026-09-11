import type { Metadata } from "next";
import { B612, Sofia_Sans, Sofia_Sans_Extra_Condensed } from "next/font/google";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getTranslations } from "next-intl/server";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { idiomaDe, idiomas } from "@/content/idiomas";
import { site } from "@/content/site";
import { routing } from "@/i18n/routing";
import "../globals.css";

// Sofia Sans: sistema tipográfico de uma cidade, com larguras para título enorme e texto corrido.
// B612: desenhada pela Airbus com a ENAC para telas de cabine; aqui é a "voz do instrumento" (escalas, dados).
const sofia = Sofia_Sans({ subsets: ["latin"], variable: "--font-sofia", display: "swap" });
const sofiaCondensada = Sofia_Sans_Extra_Condensed({
  subsets: ["latin"],
  variable: "--font-sofia-condensada",
  display: "swap",
});
const b612 = B612({ subsets: ["latin"], weight: ["400", "700"], variable: "--font-b612", display: "swap" });

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export async function generateMetadata(): Promise<Metadata> {
  const locale = await getLocale();
  const t = await getTranslations("meta");
  const languages = Object.fromEntries(idiomas.map((i) => [i.htmlLang, `/${i.locale}`]));

  return {
    metadataBase: new URL(site.dominio),
    title: t("titulo"),
    description: t("descricao"),
    applicationName: t("tituloCurto"),
    alternates: {
      canonical: `/${locale}`,
      languages: { ...languages, "x-default": `/${routing.defaultLocale}` },
    },
    openGraph: {
      type: "website",
      siteName: t("tituloCurto"),
      title: t("titulo"),
      description: t("descricao"),
      locale: idiomaDe(locale).htmlLang.replace("-", "_"),
    },
    robots: site.indexar ? undefined : { index: false, follow: false },
  };
}

export default async function LocaleLayout({ children }: { children: React.ReactNode }) {
  const locale = await getLocale();
  const t = await getTranslations("comum");

  return (
    <html
      lang={idiomaDe(locale).htmlLang}
      className={`${sofia.variable} ${sofiaCondensada.variable} ${b612.variable}`}
    >
      <body>
        <NextIntlClientProvider>
          <a href="#conteudo" className="pular-conteudo">
            {t("pularConteudo")}
          </a>
          <SiteHeader />
          <main id="conteudo">{children}</main>
          <SiteFooter />
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
