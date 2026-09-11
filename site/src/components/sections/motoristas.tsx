import { getLocale, getTranslations } from "next-intl/server";
import { Photo } from "@/components/photo";
import { site } from "@/content/site";

const itens = ["filmagem", "alarme", "dados", "revisao", "oculos"] as const;

export async function Motoristas() {
  const t = await getTranslations("motoristas");
  const locale = await getLocale();
  const url = `${site.dominio}/${locale}#motoristas`;
  const compartilhar = `https://wa.me/?text=${encodeURIComponent(t("mensagemCompartilhar", { url }))}`;

  return (
    <section id="motoristas" aria-labelledby="titulo-motoristas" className="com-trilho border-t border-fio">
      <div className="shell grid gap-12 py-20 lg:grid-cols-12 lg:py-28">
        <Photo
          codigo="s13"
          cena={t("titulo")}
          sizes="(min-width: 1024px) 38vw, 100vw"
          className="aspect-[4/5] w-full lg:col-span-5"
        />
        <div className="flex flex-col lg:col-span-6 lg:col-start-7">
          <h2 id="titulo-motoristas" className="text-[clamp(2.6rem,5vw,4.8rem)]">
            {t("titulo")}
          </h2>
          <ol className="mt-10 grid border-t border-asfalto">
            {itens.map((chave, i) => (
              <li key={chave} className="grid grid-cols-[3rem_1fr] gap-4 border-b border-fio py-5">
                <span className="numero text-grafite">0{i + 1}</span>
                <span className="text-[1.2rem] leading-snug">{t(`itens.${chave}`)}</span>
              </li>
            ))}
          </ol>
          <a
            href={compartilhar}
            target="_blank"
            rel="noopener"
            data-evento="motoristas_compartilhar"
            className="btn btn-secundario mt-8 self-start"
          >
            {t("compartilhar")}
          </a>
        </div>
      </div>
    </section>
  );
}
