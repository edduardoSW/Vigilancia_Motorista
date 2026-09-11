import { getFormatter, getTranslations } from "next-intl/server";
import { escala } from "@/content/escalas";

// Viagem de exemplo de 8 h (22:40 → 06:40) com dois trechos de 20 s: 40 s de 28 800 s = 0,14 %.
const INICIO_MIN = 22 * 60 + 40;
const DURACAO_MIN = 8 * 60;
const TRECHOS = [
  { inicioMin: 3 * 60 + 10 + 24 * 60, segundos: 20 },
  { inicioMin: 5 * 60 + 2 + 24 * 60, segundos: 20 },
];
const LARGURA = 1000;

function xDoMinuto(minuto: number) {
  return ((minuto - INICIO_MIN) / DURACAO_MIN) * LARGURA;
}

/** Os 6 pontos por olho que medem a abertura (caixa/vision/face.py), desenhados sem mira e sem vermelho. */
function OlhoPontos({ rotulo }: { rotulo: string }) {
  const pontos: [number, number, string][] = [
    [70, 150, "1"],
    [208, 70, "2"],
    [392, 70, "3"],
    [530, 150, "4"],
    [392, 230, "5"],
    [208, 230, "6"],
  ];
  return (
    <svg viewBox="0 0 600 300" role="img" aria-label={rotulo} className="block h-auto w-full">
      <path d="M70 150 Q300 -40 530 150 Q300 340 70 150Z" fill="var(--c-papel)" stroke="var(--c-asfalto)" strokeWidth="2" />
      <circle cx="300" cy="150" r="74" fill="none" stroke="var(--c-asfalto)" strokeWidth="1.5" />
      <circle cx="300" cy="150" r="30" fill="var(--c-asfalto)" opacity="0.85" />
      <g stroke="var(--c-grafite)" strokeWidth="1.2" strokeDasharray="5 6">
        <line x1="208" y1="70" x2="208" y2="230" />
        <line x1="392" y1="70" x2="392" y2="230" />
        <line x1="70" y1="150" x2="530" y2="150" />
      </g>
      {pontos.map(([x, y, n]) => (
        <g key={n}>
          <circle cx={x} cy={y} r="9" fill="var(--c-concreto)" stroke="var(--c-asfalto)" strokeWidth="2.5" />
          <text
            x={x}
            y={n === "1" || n === "4" ? y - 18 : n === "2" || n === "3" ? y - 18 : y + 34}
            textAnchor="middle"
            fontFamily="var(--font-instrumento)"
            fontSize="18"
            fill="var(--c-asfalto)"
          >
            {n}
          </text>
        </g>
      ))}
    </svg>
  );
}

export async function Registro() {
  const t = await getTranslations("olho");
  const te = await getTranslations("escalas");
  const tc = await getTranslations("comum");
  const formato = await getFormatter();
  const porcentagem = formato.number(40 / (DURACAO_MIN * 60), { style: "percent", maximumFractionDigits: 2 });
  const horas = Array.from({ length: 9 }, (_, i) => INICIO_MIN + 20 + i * 60).filter((m) => m <= INICIO_MIN + DURACAO_MIN);

  return (
    <section id="registro" data-escala="olho" aria-labelledby="titulo-registro" className="com-trilho border-t border-fio bg-papel">
      <div className="shell py-20 lg:py-28">
        <div className="grid items-center gap-12 lg:grid-cols-12">
          <div className="lg:col-span-6">
            <p className="etiqueta flex gap-3 text-grafite">
              <span className="numero text-asfalto">{escala("olho").valor}</span>
              <span>{te("olho")}</span>
            </p>
            <h2 id="titulo-registro" className="mt-4 text-[clamp(2.6rem,5vw,4.8rem)]">
              {t("titulo")}
            </h2>
            <p className="texto-longo mt-6 text-grafite">{t("texto")}</p>
          </div>
          <figure className="lg:col-span-6">
            <OlhoPontos rotulo={t("pontos")} />
            <figcaption className="etiqueta mt-2 text-grafite">{t("pontos")}</figcaption>
          </figure>
        </div>

        <figure className="mt-20 border-t border-asfalto pt-6">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <span className="font-titulo text-[1.9rem] font-bold">{t("faixaTitulo")}</span>
            <span className="etiqueta text-grafite">{tc("exemplo")}</span>
          </div>
          <svg viewBox={`0 0 ${LARGURA} 120`} className="mt-6 block h-auto w-full overflow-visible" aria-hidden="true">
            <line x1="0" y1="40" x2={LARGURA} y2="40" stroke="var(--c-asfalto)" strokeWidth="6" />
            {TRECHOS.map((tr) => (
              <rect key={tr.inicioMin} x={xDoMinuto(tr.inicioMin)} y="14" width="4" height="52" fill="var(--c-alarme)" />
            ))}
            {horas.map((m) => (
              <g key={m} transform={`translate(${xDoMinuto(m)} 0)`}>
                <line y1="62" y2="74" stroke="var(--c-grafite)" strokeWidth="1.5" />
                <text y="100" textAnchor="middle" fontFamily="var(--font-instrumento)" fontSize="15" fill="var(--c-grafite)">
                  {String(Math.floor(m / 60) % 24).padStart(2, "0")}h
                </text>
              </g>
            ))}
          </svg>
          <figcaption className="mt-6 grid gap-4 sm:grid-cols-3">
            <span className="flex items-center gap-3">
              <span aria-hidden="true" className="block h-1.5 w-8 bg-asfalto" />
              {t("faixaRegistro")}
            </span>
            <span className="flex items-center gap-3">
              <span aria-hidden="true" className="block h-5 w-1 bg-alarme" />
              {t("faixaTrechos")}
            </span>
            <span className="font-semibold">{t("faixaResumo", { porcentagem })}</span>
          </figcaption>
        </figure>

        <div className="mt-16 grid gap-8 lg:grid-cols-2">
          <p className="border-l-2 border-asfalto pl-4 text-[1.1rem]">{t("cifrado")}</p>
          <p className="border-l-2 border-fio-forte pl-4 text-[1.1rem] text-grafite">{t("ativacao")}</p>
        </div>
      </div>
    </section>
  );
}
