"use client";

import type { Capitulo } from "@/content/guide";

// Um capítulo do guia: passos numerados, lista de alertas (capítulo 4) e "Se der errado" no fim.
export function GuideArticle({ capitulo }: { capitulo: Capitulo }) {
  return (
    <article className="anim-enter max-w-[680px]">
      <p className="text-[13px] text-grafite">Capítulo {capitulo.numero}</p>
      <h2 className="mt-1 font-titulo text-[26px] font-semibold leading-tight">{capitulo.titulo}</h2>
      <p className="mt-2 text-[15px] text-grafite">{capitulo.resumo}</p>

      {capitulo.topicos.map((topico) => (
        <section key={topico.id} id={topico.id} className="mt-9 scroll-mt-6">
          <h3 className="text-[17px] font-semibold">{topico.titulo}</h3>
          <ol className="mt-3.5 grid gap-3">
            {topico.passos.map((passo, indice) => (
              <li key={passo} className="grid grid-cols-[26px_minmax(0,1fr)] items-start gap-3 text-[15px] leading-[1.5]">
                <span aria-hidden="true" className="mt-px grid size-[22px] place-items-center rounded-full bg-verde text-[12px] font-semibold text-white">
                  {indice + 1}
                </span>
                <span>{passo}</span>
              </li>
            ))}
          </ol>
        </section>
      ))}

      {capitulo.alertas && (
        <section id="lista-de-alertas" className="mt-9 scroll-mt-6">
          <h3 className="text-[17px] font-semibold">Cada alerta</h3>
          <dl className="mt-3 border-t border-fio">
            {capitulo.alertas.map((alerta) => (
              <div key={alerta.tipo} id={`alerta-${alerta.tipo}`} className="grid scroll-mt-6 grid-cols-[230px_minmax(0,1fr)] gap-6 border-b border-fio py-3.5">
                <dt className="text-[14.5px] font-semibold">{alerta.rotulo}</dt>
                <dd className="text-[14.5px] text-grafite">{alerta.explicacao}</dd>
              </div>
            ))}
          </dl>
        </section>
      )}

      <section id="se-der-errado" className="mt-10 scroll-mt-6 rounded-[12px] bg-lateral px-5 py-4">
        <h3 className="text-[15px] font-semibold">Se der errado</h3>
        <p className="mt-1 text-[14.5px] leading-[1.55]">
          {capitulo.seDerErrado.problema} {capitulo.seDerErrado.solucao}
        </p>
      </section>

      <button type="button" className="no-print btn btn-small mt-8" onClick={() => window.print()}>
        Imprimir este capítulo
      </button>
    </article>
  );
}
