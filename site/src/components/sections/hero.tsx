import { getTranslations } from "next-intl/server";
import { LiveClock } from "@/components/maps/live-clock";
import { WorldNightMap } from "@/components/maps/world-night-map";
import { Photo } from "@/components/photo";
import { WhatsAppButton } from "@/components/whatsapp-button";
import { escala } from "@/content/escalas";

const portas = [
  { chave: "carga", codigo: "s07", frota: "caminhao" },
  { chave: "fretamento", codigo: "s08", frota: "onibus" },
  { chave: "urbano", codigo: "s10", frota: "onibus" },
] as const;

export async function Hero() {
  const t = await getTranslations("hero");
  const tc = await getTranslations("contato.mensagens");
  const te = await getTranslations("escalas");
  const tg = await getTranslations("comum");

  return (
    <section id="inicio" data-escala="mundo" aria-labelledby="titulo-inicio" className="com-trilho">
      <div className="shell grid gap-x-12 gap-y-10 pt-8 pb-8 lg:min-h-[calc(100svh-var(--header-h)-clamp(12rem,33svh,20rem))] lg:grid-cols-12 lg:pt-10">
        <div className="flex flex-col justify-center lg:col-span-7">
          <p className="etiqueta flex flex-wrap gap-x-3 text-grafite">
            <span>{t("ato")}</span>
            <span className="numero text-asfalto">{escala("mundo").valor}</span>
          </p>
          <h1 id="titulo-inicio" className="mt-4 max-w-[24ch] text-[clamp(2.8rem,4.9vw,4.4rem)]">
            {t("titulo")}
          </h1>
          <p className="mt-5 max-w-[58ch] text-[1.15rem] leading-relaxed text-grafite">{t("texto")}</p>
          <div className="mt-7 flex flex-wrap items-center gap-3">
            <WhatsAppButton mensagem={tc("geral")} rotulo={t("ctaPrincipal")} secao="inicio" className="btn btn-primario" />
            <a href="#rota" className="btn btn-secundario">
              {t("ctaSecundario")}
            </a>
          </div>
          <p className="etiqueta mt-6 text-grafite">{tg("estagio")}</p>
        </div>

        <figure className="self-center lg:col-span-5">
          <div className="flex items-baseline justify-between gap-4 border-b border-asfalto pb-2">
            <span className="etiqueta">
              {t("mapaTitulo")} · {te("mundo")}
            </span>
            <span className="etiqueta text-grafite">
              {t("agora")} <LiveClock />
            </span>
          </div>
          <div className="mt-3">
            <WorldNightMap rotulo={t("mapaLegenda")} />
          </div>
          <figcaption className="mt-3 grid gap-1 text-[0.95rem] text-grafite sm:grid-cols-2 sm:gap-6">
            <span>{t("mapaLegenda")}</span>
            <span className="text-asfalto">{t("mapaRegra")}</span>
          </figcaption>
        </figure>
      </div>

      <nav aria-label={t("portasTitulo")} className="border-t border-asfalto">
        <ul className="grid md:grid-cols-3">
          {portas.map((porta, i) => (
            <li key={porta.chave} className="relative md:border-l md:border-concreto md:first:border-l-0">
              <a href={`?frota=${porta.frota}#cabine`} className="group relative block h-[clamp(12rem,33svh,20rem)] overflow-hidden bg-noite text-noite-texto">
                <Photo
                  codigo={porta.codigo}
                  cena={t(`portas.${porta.chave}.titulo`)}
                  sizes="(min-width: 768px) 33vw, 100vw"
                  className="absolute inset-0 h-full w-full transition-transform duration-700 group-hover:scale-[1.03]"
                  credito="nenhum"
                  tom="escuro"
                  prioridade={i === 0}
                />
                <span aria-hidden="true" className="absolute inset-0 bg-linear-to-t from-noite via-noite/40 to-transparent" />
                <span className="absolute inset-x-0 bottom-0 flex items-end justify-between gap-4 p-5 lg:p-6">
                  <span>
                    <span className="numero block text-[0.8rem] text-noite-muted">0{i + 1}</span>
                    <span className="mt-1 block font-titulo text-[clamp(1.9rem,2.6vw,2.6rem)] leading-none font-bold">
                      {t(`portas.${porta.chave}.titulo`)}
                    </span>
                    <span className="mt-2 block text-noite-muted">{t(`portas.${porta.chave}.texto`)}</span>
                  </span>
                  <span aria-hidden="true" className="text-2xl transition-transform group-hover:translate-x-1">
                    →
                  </span>
                </span>
              </a>
            </li>
          ))}
        </ul>
      </nav>
    </section>
  );
}
