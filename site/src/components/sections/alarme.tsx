import { getTranslations } from "next-intl/server";

const degraus = [
  { segundos: 1, chave: "um" },
  { segundos: 3, chave: "tres" },
  { segundos: 6, chave: "seis" },
] as const;

export async function Alarme() {
  const t = await getTranslations("alarme");

  return (
    <section data-escala="cabine" aria-labelledby="titulo-alarme" className="com-trilho">
      <div className="shell py-20 lg:py-28">
        <h2 id="titulo-alarme" className="max-w-4xl text-[clamp(2.4rem,4.4vw,4.2rem)]">
          {t("titulo")}
        </h2>

        <div className="mt-14 grid gap-12 border-t border-asfalto pt-10 lg:grid-cols-12 lg:gap-0">
          <div className="lg:col-span-6 lg:pr-10">
            <h3 className="text-[2rem]">{t("sono.titulo")}</h3>
            <ol className="mt-6 grid">
              {degraus.map((d) => (
                <li key={d.chave} className="grid grid-cols-[7.5rem_1fr] items-baseline gap-4 border-t border-fio py-4">
                  <span className="font-titulo text-[clamp(3.4rem,5vw,4.6rem)] leading-none font-extrabold">
                    {d.segundos}
                    <span className="text-[0.45em] font-bold"> s</span>
                  </span>
                  <span className="text-[1.15rem]">{t(`sono.${d.chave}`)}</span>
                </li>
              ))}
            </ol>
            <p className="mt-4 text-grafite">{t("sono.extra")}</p>
          </div>

          <div className="lg:col-span-3 lg:border-l lg:border-fio lg:px-8">
            <h3 className="text-[2rem]">{t("celular.titulo")}</h3>
            <p className="mt-6 text-[1.15rem]">{t("celular.texto")}</p>
          </div>

          <div className="lg:col-span-3 lg:border-l lg:border-fio lg:pl-8">
            <h3 className="text-[2rem]">{t("contexto.titulo")}</h3>
            <p className="mt-6 text-[1.15rem]">{t("contexto.texto")}</p>
          </div>
        </div>

        <p className="etiqueta mt-12 max-w-3xl text-grafite">{t("nota")}</p>
      </div>
    </section>
  );
}
