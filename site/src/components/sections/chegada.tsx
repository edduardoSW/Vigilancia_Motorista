import { getTranslations } from "next-intl/server";
import { Photo } from "@/components/photo";
import { escala } from "@/content/escalas";

const passos = ["recolher", "conectar", "conferir", "relatorio"] as const;

export async function Chegada() {
  const t = await getTranslations("garagem");
  const te = await getTranslations("escalas");

  return (
    <section id="chegada" data-escala="garagem" aria-labelledby="titulo-chegada" className="com-trilho border-t border-fio">
      <div className="shell grid gap-12 py-20 lg:grid-cols-12 lg:py-28">
        <div className="lg:col-span-5">
          <p className="etiqueta flex flex-wrap gap-x-3 text-grafite">
            <span>{t("ato")}</span>
            <span className="numero text-asfalto">{escala("garagem").valor}</span>
            <span>{te("garagem")}</span>
          </p>
          <h2 id="titulo-chegada" className="mt-4 text-[clamp(2.6rem,5vw,4.8rem)]">
            {t("titulo")}
          </h2>
          <Photo
            codigo="f03"
            cena={t("passos.recolher.titulo")}
            sizes="(min-width: 1024px) 38vw, 100vw"
            className="mt-10 aspect-[4/5] w-full"
          />
        </div>

        <div className="flex flex-col justify-end lg:col-span-6 lg:col-start-7">
          <ol className="grid border-t border-asfalto">
            {passos.map((chave, i) => (
              <li key={chave} className="grid grid-cols-[4rem_1fr] gap-4 border-b border-fio py-7">
                <span className="font-titulo text-[3rem] leading-none font-extrabold">{i + 1}</span>
                <span>
                  <span className="block font-titulo text-[2.1rem] leading-none font-bold">{t(`passos.${chave}.titulo`)}</span>
                  <span className="mt-3 block text-[1.1rem] text-grafite">{t(`passos.${chave}.texto`)}</span>
                </span>
              </li>
            ))}
          </ol>
          <p className="etiqueta mt-6 text-grafite">{t("nota")}</p>
        </div>
      </div>
    </section>
  );
}
