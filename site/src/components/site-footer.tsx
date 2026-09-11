import { getTranslations } from "next-intl/server";
import { Flag } from "@/components/flag";
import { navegacao } from "@/components/site-header";
import { Wordmark } from "@/components/wordmark";
import { idiomas } from "@/content/idiomas";
import { Link } from "@/i18n/navigation";

export async function SiteFooter() {
  const t = await getTranslations("rodape");
  const tn = await getTranslations("nav");

  return (
    <footer className="com-trilho border-t border-asfalto bg-concreto">
      <div className="shell grid gap-10 py-14 md:grid-cols-12">
        <div className="md:col-span-4">
          <Wordmark className="text-[1.1rem]" />
          <p className="etiqueta mt-4 text-grafite">{t("marca")}</p>
        </div>
        <nav aria-label={tn("rotulo")} className="md:col-span-3">
          <ul className="grid gap-2">
            {navegacao.map((item) => (
              <li key={item.chave}>
                <Link href={item.href} className="hover:underline">
                  {tn(item.chave)}
                </Link>
              </li>
            ))}
            <li>
              <Link href="/entrar" className="link-sublinhado">
                {tn("entrar")}
              </Link>
            </li>
          </ul>
        </nav>
        <ul className="grid content-start gap-2 md:col-span-2" aria-label={tn("idioma")}>
          {idiomas.map((i) => (
            <li key={i.locale}>
              <Link href="/" locale={i.locale} hrefLang={i.htmlLang} lang={i.htmlLang} className="flex items-center gap-2 hover:underline">
                <Flag code={i.bandeira} className="h-3 w-4.5 shrink-0" />
                {i.idioma}
              </Link>
            </li>
          ))}
        </ul>
        <div className="grid content-start gap-3 text-[0.9rem] text-grafite md:col-span-3">
          <p>{t("mapas")}</p>
          <Link href="/creditos" className="link-sublinhado text-asfalto">
            {t("fotos")}
          </Link>
          <p className="etiqueta">{t("direitos")}</p>
        </div>
      </div>
    </footer>
  );
}
