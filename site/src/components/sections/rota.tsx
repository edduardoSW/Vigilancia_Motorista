import { getFormatter, getTranslations } from "next-intl/server";
import { routeStrip } from "@/components/maps/route-strip";
import { escala } from "@/content/escalas";

const paradas = [
  { chave: "saida", marca: "normal" },
  { chave: "madrugada", marca: "normal" },
  { chave: "alarme", marca: "alarme" },
  { chave: "semSinal", marca: "vazada" },
  { chave: "trecho", marca: "trecho" },
  { chave: "jornada", marca: "normal" },
  { chave: "chegada", marca: "normal" },
  { chave: "relatorio", marca: "cheia" },
] as const;

function Marca({ tipo }: { tipo: (typeof paradas)[number]["marca"] }) {
  const base = "mt-2 block size-3.5 shrink-0";
  if (tipo === "alarme") return <span aria-hidden="true" className={`${base} rounded-full bg-alarme`} />;
  if (tipo === "trecho") return <span aria-hidden="true" className={`${base} bg-alarme`} />;
  if (tipo === "vazada") return <span aria-hidden="true" className={`${base} rounded-full border border-dashed border-asfalto`} />;
  if (tipo === "cheia") return <span aria-hidden="true" className={`${base} bg-asfalto`} />;
  return <span aria-hidden="true" className={`${base} rounded-full border-2 border-asfalto bg-concreto`} />;
}

export async function Rota() {
  const t = await getTranslations("rota");
  const te = await getTranslations("escalas");
  const formato = await getFormatter();
  const { svg, kmTotal } = await routeStrip({ rotulo: t("titulo") });

  return (
    <section id="rota" data-escala="rota" aria-labelledby="titulo-rota" className="com-trilho border-t border-fio bg-papel">
      <div className="shell grid gap-12 py-20 lg:grid-cols-12 lg:py-28">
        <div className="lg:col-span-5">
          <p className="etiqueta flex gap-3 text-grafite">
            <span className="numero text-asfalto">{escala("rota").valor}</span>
            <span>{te("rota")}</span>
          </p>
          <h2 id="titulo-rota" className="mt-4 text-[clamp(2.4rem,4.4vw,4.2rem)]">
            {t("titulo")}
          </h2>
          <p className="mt-6 border-l-2 border-asfalto pl-4 text-grafite">{t("aviso")}</p>

          <ol className="mt-12 grid">
            {paradas.map((p) => (
              <li key={p.chave} className="grid grid-cols-[4.5rem_1rem_1fr] gap-x-4 border-t border-fio py-5">
                <span className="numero text-[1.05rem] leading-7">{t(`paradas.${p.chave}.hora`)}</span>
                <Marca tipo={p.marca} />
                <span>
                  <span className="block font-titulo text-[1.7rem] leading-7 font-bold">{t(`paradas.${p.chave}.titulo`)}</span>
                  <span className="mt-2 block text-grafite">{t(`paradas.${p.chave}.texto`)}</span>
                </span>
              </li>
            ))}
          </ol>
        </div>

        <figure className="self-start lg:sticky lg:top-[calc(var(--header-h)+2rem)] lg:col-span-6 lg:col-start-7">
          {svg ?? <div className="aspect-[640/760] bg-terra" aria-hidden="true" />}
          <figcaption className="mt-3 flex flex-wrap items-baseline justify-between gap-2 border-t border-fio pt-3 text-grafite">
            <span className="etiqueta text-[0.65rem]">{t("fonte")}</span>
            {kmTotal ? <span className="numero text-asfalto">{t("distancia", { km: formato.number(Math.round(kmTotal)) })}</span> : null}
          </figcaption>
        </figure>
      </div>
    </section>
  );
}
