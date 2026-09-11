import type { Metadata } from "next";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { getLocale, getTranslations } from "next-intl/server";
import { downloads } from "@/content/downloads";
import { COOKIE_SESSAO, sessaoValida } from "@/lib/sessao";
import { sair } from "../entrar/actions";

export const metadata: Metadata = { robots: { index: false, follow: false } };

export default async function AppPage() {
  const locale = await getLocale();
  const sessao = (await cookies()).get(COOKIE_SESSAO)?.value;
  if (!sessaoValida(sessao)) redirect(`/${locale}/entrar`);

  const t = await getTranslations("app");

  return (
    <section className="com-trilho">
      <div className="shell py-20 lg:py-28">
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div>
            <h1 className="text-[clamp(2.8rem,6vw,5rem)]">{t("titulo")}</h1>
            <p className="texto-longo mt-6 text-grafite">{t("texto")}</p>
          </div>
          <form action={sair}>
            <input type="hidden" name="locale" value={locale} />
            <button type="submit" className="btn btn-secundario">
              {t("sair")}
            </button>
          </form>
        </div>

        <ul className="mt-14 grid border-t border-asfalto">
          {downloads.map((d) => (
            <li key={d.plataforma} className="grid gap-3 border-b border-fio py-6 sm:grid-cols-[1fr_auto] sm:items-center">
              <div>
                <p className="font-titulo text-[2.2rem] leading-none font-bold">{t(`plataformas.${d.plataforma}.nome`)}</p>
                <p className="mt-2 text-grafite">{t(`plataformas.${d.plataforma}.formato`)}</p>
              </div>
              {d.url ? (
                <a href={d.url} className="btn btn-primario" data-evento="download_app" data-plataforma={d.plataforma}>
                  {t("baixar")}
                </a>
              ) : (
                <span className="etiqueta text-grafite">{t("emPreparacao")}</span>
              )}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
