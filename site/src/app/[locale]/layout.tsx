import type { Metadata } from "next";
import { Manrope, Space_Grotesk } from "next/font/google";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getTranslations } from "next-intl/server";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { idiomaDe, idiomas } from "@/content/idiomas";
import { site } from "@/content/site";
import { routing } from "@/i18n/routing";
import "../globals.css";

// Technical display typography paired with a quieter face for short reading.
const bodyFont = Manrope({ subsets: ["latin"], variable: "--font-body", display: "swap" });
const displayFont = Space_Grotesk({ subsets: ["latin"], variable: "--font-display", display: "swap" });

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
      images: [{url: "/midia/rotaguard/onibus-rodoviario.webp", width: 1536, height: 1024}],
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
      className={`${bodyFont.variable} ${displayFont.variable}`}
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
