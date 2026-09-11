import { getTranslations } from "next-intl/server";
import { Photo } from "@/components/photo";
import { escala } from "@/content/escalas";

export async function Rodovia() {
  const t = await getTranslations("rodovia");
  const te = await getTranslations("escalas");

  return (
    <section
      id="rodovia"
      data-escala="rodovia"
      aria-labelledby="titulo-rodovia"
      className="relative ml-(--rail) min-h-[88svh] overflow-hidden bg-noite text-noite-texto"
    >
      <Photo
        codigo="s07"
        cena={t("titulo")}
        sizes="100vw"
        className="absolute inset-0 h-full w-full"
        tom="escuro"
      />
      <div aria-hidden="true" className="absolute inset-0 bg-linear-to-t from-noite via-noite/55 to-noite/10" />
      <div className="shell relative flex min-h-[88svh] flex-col justify-between py-10">
        <p className="etiqueta flex gap-3 text-noite-muted">
          <span className="numero text-noite-texto">{escala("rodovia").valor}</span>
          <span>{te("rodovia")}</span>
        </p>
        <div className="max-w-3xl pb-8">
          <h2 id="titulo-rodovia" className="text-[clamp(2.6rem,6vw,5.6rem)]">
            {t("titulo")}
          </h2>
          <p className="texto-longo mt-6 text-noite-muted">{t("texto")}</p>
        </div>
      </div>
    </section>
  );
}
