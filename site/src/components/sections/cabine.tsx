import { getTranslations } from "next-intl/server";
import { Photo } from "@/components/photo";
import { VehicleToggle } from "@/components/sections/vehicle-toggle";
import { escala } from "@/content/escalas";

const itens = ["camera", "processa", "semTela", "liga"] as const;

export async function Cabine() {
  const t = await getTranslations("cabine");
  const te = await getTranslations("escalas");

  return (
    <section id="cabine" data-escala="cabine" aria-labelledby="titulo-cabine" className="cena-noite ml-(--rail)">
      <div className="shell grid gap-12 py-20 lg:grid-cols-12 lg:py-28">
        <div className="lg:col-span-7">
          <p className="etiqueta flex flex-wrap gap-x-3 text-noite-muted">
            <span>{t("ato")}</span>
            <span className="numero text-noite-texto">{escala("cabine").valor}</span>
            <span>{te("cabine")}</span>
          </p>
          <h2 id="titulo-cabine" className="mt-4 text-[clamp(2.6rem,5vw,4.8rem)]">
            {t("titulo")}
          </h2>
          <div className="mt-10">
            <VehicleToggle
              rotulo={t("seletor")}
              rotuloCaminhao={t("caminhao")}
              rotuloOnibus={t("onibus")}
              caminhao={
                <Photo codigo="s01" cena={t("caminhao")} sizes="(min-width: 1024px) 55vw, 100vw" className="aspect-[3/2] w-full" tom="escuro" />
              }
              onibus={
                <Photo codigo="s02" cena={t("onibus")} sizes="(min-width: 1024px) 55vw, 100vw" className="aspect-[3/2] w-full" tom="escuro" />
              }
            />
          </div>
        </div>

        <div className="flex flex-col justify-end lg:col-span-5">
          <ol className="grid border-t border-noite-fio">
            {itens.map((chave, i) => (
              <li key={chave} className="grid grid-cols-[3rem_1fr] gap-4 border-b border-noite-fio py-5">
                <span className="numero text-noite-muted">0{i + 1}</span>
                <span className="font-titulo text-[1.9rem] leading-8 font-bold">{t(`itens.${chave}`)}</span>
              </li>
            ))}
          </ol>
          <div className="mt-10 grid grid-cols-[7rem_1fr] items-end gap-5">
            <Photo codigo="s15" cena={t("prototipo")} sizes="7rem" className="aspect-square w-full" credito="nenhum" tom="escuro" />
            <p className="text-[0.95rem] text-noite-muted">{t("prototipo")}</p>
          </div>
        </div>
      </div>
    </section>
  );
}
