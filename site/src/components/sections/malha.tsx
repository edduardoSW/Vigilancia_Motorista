import { getFormatter, getTranslations } from "next-intl/server";
import { brazilNetworkMap } from "@/components/maps/brazil-network-map";
import { escala } from "@/content/escalas";

export async function Malha() {
  const t = await getTranslations("brasil");
  const te = await getTranslations("escalas");
  const formato = await getFormatter();
  const { svg, kmRodovias } = await brazilNetworkMap({ rotulo: t("legendaMalha") });

  return (
    <section id="malha" data-escala="brasil" aria-labelledby="titulo-malha" className="com-trilho border-t border-fio">
      <div className="shell grid gap-10 py-20 lg:grid-cols-12 lg:py-28">
        <div className="self-start lg:sticky lg:top-[calc(var(--header-h)+3rem)] lg:col-span-4">
          <p className="etiqueta flex gap-3 text-grafite">
            <span className="numero text-asfalto">{escala("brasil").valor}</span>
            <span>{te("brasil")}</span>
          </p>
          <h2 id="titulo-malha" className="mt-4 text-[clamp(2.4rem,4.4vw,4.2rem)]">
            {t("titulo")}
          </h2>
          <p className="texto-longo mt-6 text-grafite">{t("texto")}</p>
          {kmRodovias ? (
            <p className="mt-10 border-t border-asfalto pt-4">
              <span className="numero block text-[clamp(2.2rem,3.4vw,3.2rem)] leading-none">
                {formato.number(kmRodovias)}
              </span>
              <span className="mt-2 block text-grafite">{t("numeroRotulo")}</span>
            </p>
          ) : null}
        </div>

        <figure className="lg:col-span-8">
          {svg ?? <div className="aspect-square bg-terra" aria-hidden="true" />}
          <figcaption className="mt-4 grid gap-2 border-t border-fio pt-4 text-[0.95rem] text-grafite sm:grid-cols-2">
            <span className="flex items-center gap-3">
              <span aria-hidden="true" className="block h-px w-8 bg-asfalto" />
              {t("legendaMalha")}
            </span>
            <span className="flex items-center gap-3">
              <span aria-hidden="true" className="block h-1 w-8 bg-asfalto" />
              {t("legendaRota")}
            </span>
            <span className="etiqueta text-[0.65rem] sm:col-span-2">{t("fonte")}</span>
          </figcaption>
        </figure>
      </div>
    </section>
  );
}
