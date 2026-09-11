import { getTranslations } from "next-intl/server";
import { escala } from "@/content/escalas";

// Linha do tempo do relatório de exemplo (22:40 → 06:50), em minutos desde o início, coerente com a viagem da
// seção Rota: microssono às 02:14; mais três entre 02:46 e 03:10 (3 em 30 min → trecho às 03:10);
// celular às 03:45; 5 h 30 ao volante às 04:10.
const TOTAL_MIN = 8 * 60 + 10;
const eventos = [
  { minuto: 214, tipo: "microssono" },
  { minuto: 246, tipo: "microssono" },
  { minuto: 258, tipo: "microssono" },
  { minuto: 270, tipo: "microssono" },
  { minuto: 270, tipo: "trecho" },
  { minuto: 305, tipo: "celular" },
  { minuto: 330, tipo: "jornada" },
] as const;

export async function Relatorio() {
  const t = await getTranslations("relatorio");
  const te = await getTranslations("escalas");
  const tc = await getTranslations("comum");
  const f = (chave: string) => t(`ficha.${chave}`);

  const linhas: [string, string][] = [
    [f("veiculo"), f("veiculoValor")],
    [f("periodo"), f("periodoValor")],
    [f("direcao"), f("direcaoValor")],
    [f("madrugada"), f("madrugadaValor")],
    [f("trechos"), f("trechosValor")],
    [f("integridade"), f("integridadeValor")],
  ];

  return (
    <section id="relatorio" data-escala="relatorio" aria-labelledby="titulo-relatorio" className="com-trilho border-t border-fio bg-terra/60">
      <div className="shell grid gap-12 py-20 lg:grid-cols-12 lg:py-28">
        <div className="lg:col-span-5">
          <p className="etiqueta flex gap-3 text-grafite">
            <span className="numero text-asfalto">{escala("relatorio").valor}</span>
            <span>{te("relatorio")}</span>
          </p>
          <h2 id="titulo-relatorio" className="mt-4 text-[clamp(2.6rem,5vw,4.8rem)]">
            {t("titulo")}
          </h2>
          <p className="texto-longo mt-6 text-grafite">{t("texto")}</p>
        </div>

        <article
          aria-label={f("cabecalho")}
          className="bg-papel p-6 shadow-[0_1px_0_var(--c-fio),0_24px_48px_rgb(27_27_25/0.10)] sm:p-9 lg:col-span-7"
        >
          <header className="flex flex-wrap items-baseline justify-between gap-3 border-b-2 border-asfalto pb-3">
            <span className="font-titulo text-[2rem] leading-none font-bold">{f("cabecalho")}</span>
            <span className="etiqueta text-grafite">{tc("exemplo")}</span>
          </header>

          <dl className="grid sm:grid-cols-2">
            {linhas.map(([rotulo, valor]) => (
              <div key={rotulo} className="border-b border-fio py-3 sm:odd:pr-6 sm:even:pl-6">
                <dt className="etiqueta text-[0.66rem] text-grafite">{rotulo}</dt>
                <dd className="numero mt-1 text-[1.05rem]">{valor}</dd>
              </div>
            ))}
          </dl>

          <div className="mt-6">
            <p className="etiqueta text-[0.66rem] text-grafite">{f("eventos")}</p>
            <svg viewBox="0 0 600 64" className="mt-3 block h-auto w-full" aria-hidden="true">
              <line x1="0" y1="32" x2="600" y2="32" stroke="var(--c-asfalto)" strokeWidth="2" />
              {eventos.map((e) => {
                const x = (e.minuto / TOTAL_MIN) * 600;
                const chave = `${e.tipo}-${e.minuto}`;
                if (e.tipo === "trecho") return <rect key={chave} x={x - 2} y="6" width="4" height="52" fill="var(--c-alarme)" />;
                if (e.tipo === "microssono") return <circle key={chave} cx={x} cy="32" r="6" fill="var(--c-alarme)" />;
                if (e.tipo === "celular") return <circle key={chave} cx={x} cy="32" r="6" fill="var(--c-papel)" stroke="var(--c-asfalto)" strokeWidth="2.5" />;
                return <rect key={chave} x={x - 6} y="26" width="12" height="12" fill="var(--c-asfalto)" />;
              })}
              <text x="0" y="62" fontFamily="var(--font-instrumento)" fontSize="12" fill="var(--c-grafite)">22:40</text>
              <text x="600" y="62" textAnchor="end" fontFamily="var(--font-instrumento)" fontSize="12" fill="var(--c-grafite)">06:50</text>
            </svg>
            <ul className="mt-3 flex flex-wrap gap-x-6 gap-y-2 text-[0.95rem]">
              <li className="flex items-center gap-2"><span aria-hidden="true" className="size-3 rounded-full bg-alarme" />{f("microssono")} · 4</li>
              <li className="flex items-center gap-2"><span aria-hidden="true" className="size-3 rounded-full border-2 border-asfalto" />{f("celular")} · 1</li>
              <li className="flex items-center gap-2"><span aria-hidden="true" className="size-3 bg-asfalto" />{f("jornada")} · 1</li>
            </ul>
          </div>

          <div className="mt-6 border-t border-fio pt-4">
            <p className="etiqueta text-[0.66rem] text-grafite">{f("revisao")}</p>
            <ul className="mt-3 flex flex-wrap gap-2">
              {["confirmado", "falso", "orientado"].map((k) => (
                <li key={k} className="border border-asfalto px-3 py-1.5 text-[0.95rem]">{f(k)}</li>
              ))}
            </ul>
          </div>
        </article>
      </div>
    </section>
  );
}
