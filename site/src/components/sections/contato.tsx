import { getTranslations } from "next-intl/server";
import { Photo } from "@/components/photo";
import { WhatsAppButton } from "@/components/whatsapp-button";
import { linkTelefone, site } from "@/content/site";

const segmentos = ["carga", "fretamento", "urbano"] as const;

export async function Contato() {
  const t = await getTranslations("contato");
  const telefone = linkTelefone();

  return (
    <section id="contato" aria-labelledby="titulo-contato" className="relative ml-(--rail) overflow-hidden bg-noite text-noite-texto">
      <Photo codigo="s08" cena={t("titulo")} sizes="100vw" className="absolute inset-0 h-full w-full opacity-60" tom="escuro" />
      <div aria-hidden="true" className="absolute inset-0 bg-linear-to-r from-noite via-noite/80 to-noite/30" />
      <div className="shell relative py-24 lg:py-36">
        <h2 id="titulo-contato" className="max-w-3xl text-[clamp(2.8rem,6vw,5.6rem)]">
          {t("titulo")}
        </h2>
        <p className="texto-longo mt-6 text-noite-muted">{t("texto")}</p>
        <div className="mt-10 flex max-w-4xl flex-wrap gap-3">
          {segmentos.map((s) => (
            <WhatsAppButton key={s} mensagem={t(`mensagens.${s}`)} rotulo={t(s)} secao={`contato-${s}`} className="btn btn-claro" />
          ))}
          {telefone ? (
            <a href={telefone} data-evento="ligar_clique" className="btn btn-contorno-claro">
              {t("ligar")}
            </a>
          ) : null}
        </div>
        {!site.whatsapp ? <p className="etiqueta mt-6 text-noite-muted">{t("semNumero")}</p> : null}
      </div>
    </section>
  );
}
