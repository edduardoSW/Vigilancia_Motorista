import { getTranslations } from "next-intl/server";

const passos = ["conversa", "instalacao", "viagens", "resultado"] as const;

export async function Piloto() {
  const t = await getTranslations("piloto");

  return (
    <section id="piloto" aria-labelledby="titulo-piloto" className="com-trilho border-t border-fio bg-papel">
      <div className="shell py-20 lg:py-28">
        <h2 id="titulo-piloto" className="max-w-4xl text-[clamp(2.6rem,5vw,4.8rem)]">
          {t("titulo")}
        </h2>
        <ol className="mt-14 grid border-t border-asfalto sm:grid-cols-2 lg:grid-cols-4">
          {passos.map((chave, i) => (
            <li key={chave} className="border-b border-fio py-6 sm:pr-6 lg:border-b-0 lg:border-r lg:px-6 lg:first:pl-0 lg:last:border-r-0">
              <span className="font-titulo text-[3.4rem] leading-none font-extrabold">{i + 1}</span>
              <p className="mt-4 text-[1.2rem] leading-snug">{t(`passos.${chave}`)}</p>
            </li>
          ))}
        </ol>
        <p className="etiqueta mt-8 text-grafite">{t("nota")}</p>
      </div>
    </section>
  );
}
