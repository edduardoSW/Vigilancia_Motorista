import { getLocale, getTranslations } from "next-intl/server";
import { fotosProvisorias } from "@/lib/fotos";

export default async function CreditosPage() {
  const t = await getTranslations("creditos");
  const tr = await getTranslations("rodape");
  const locale = await getLocale();
  const fotos = await fotosProvisorias();

  return (
    <section className="com-trilho">
      <div className="shell py-20 lg:py-28">
        <h1 className="text-[clamp(2.8rem,6vw,5rem)]">{t("titulo")}</h1>

        <h2 className="mt-14 text-[2.4rem]">{t("fotos")}</h2>
        <p className="texto-longo mt-4 text-grafite">{t("aviso")}</p>
        <ul className="mt-8 grid border-t border-asfalto">
          {fotos.map((f) => (
            <li key={f.arquivo} className="grid gap-1 border-b border-fio py-4 sm:grid-cols-[6rem_1fr]">
              <span className="numero text-grafite">{f.codigo.toUpperCase()}</span>
              <span>
                <span className="block">{locale === "pt-BR" ? f.altPt : f.altEn}</span>
                <span className="mt-1 block text-[0.95rem] text-grafite">
                  {t("autor")}: {f.autor} · {t("licenca")}:{" "}
                  {f.licencaUrl ? (
                    <a href={f.licencaUrl} className="link-sublinhado" rel="license noopener" target="_blank">
                      {f.licenca}
                    </a>
                  ) : (
                    f.licenca
                  )}{" "}
                  ·{" "}
                  <a href={f.fonteUrl} className="link-sublinhado" rel="noopener" target="_blank">
                    {t("fonte")}
                  </a>
                </span>
              </span>
            </li>
          ))}
        </ul>

        <h2 className="mt-14 text-[2.4rem]">{t("mapas")}</h2>
        <p className="texto-longo mt-4 text-grafite">{tr("mapas")}</p>
      </div>
    </section>
  );
}
