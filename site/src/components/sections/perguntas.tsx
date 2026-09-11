import { getTranslations } from "next-intl/server";

const itens = ["filma", "drogas", "oculos", "internet", "gps", "custo", "acidentes", "lgpd"] as const;

export async function Perguntas() {
  const t = await getTranslations("perguntas");

  return (
    <section id="perguntas" aria-labelledby="titulo-perguntas" className="com-trilho border-t border-fio">
      <div className="shell grid gap-12 py-20 lg:grid-cols-12 lg:py-28">
        <h2 id="titulo-perguntas" className="text-[clamp(2.6rem,5vw,4.8rem)] lg:col-span-4">
          {t("titulo")}
        </h2>
        <div className="border-t border-asfalto lg:col-span-8">
          {itens.map((chave) => (
            <details key={chave} className="group border-b border-fio" data-evento="faq_abrir">
              <summary className="flex min-h-16 cursor-pointer list-none items-center justify-between gap-6 py-4 font-titulo text-[1.8rem] leading-tight font-bold [&::-webkit-details-marker]:hidden">
                {t(`itens.${chave}.pergunta`)}
                <span aria-hidden="true" className="numero text-xl transition-transform group-open:rotate-45">
                  +
                </span>
              </summary>
              <p className="texto-longo pb-6 text-grafite">{t(`itens.${chave}.resposta`)}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}
