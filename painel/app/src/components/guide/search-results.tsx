"use client";

import type { CapituloId, Resultado } from "@/content/guide";

// Resultados da busca do guia, com o trecho onde a palavra aparece destacado.
export function SearchResults({
  consulta,
  resultados,
  onOpen,
}: {
  consulta: string;
  resultados: Resultado[];
  onOpen: (capitulo: CapituloId, topico: string | null) => void;
}) {
  if (resultados.length === 0) {
    return (
      <p className="anim-enter text-[15px] text-grafite" role="status">
        Não achamos nada com “{consulta.trim()}”. Tente outra palavra ou veja a lista de capítulos.
      </p>
    );
  }

  return (
    <div className="anim-enter">
      <p className="text-[13px] text-grafite" role="status">
        {resultados.length} {resultados.length === 1 ? "lugar" : "lugares"} com “{consulta.trim()}”
      </p>
      <ul className="mt-3 border-t border-fio">
        {resultados.map((resultado) => (
          <li key={`${resultado.capituloId}-${resultado.topicoId ?? "capitulo"}`} className="anim-row">
            <button
              type="button"
              className="block w-full border-b border-fio px-2 py-3.5 text-left transition-colors hover:bg-lateral"
              onClick={() => onOpen(resultado.capituloId, resultado.topicoId)}
            >
              <span className="block text-[12.5px] text-grafite">
                {resultado.capituloNumero}. {resultado.capituloTitulo}
              </span>
              <b className="mt-0.5 block text-[15px] font-semibold">{resultado.titulo}</b>
              <span className="mt-1 block text-[14px] text-grafite">
                {resultado.trecho.antes}
                <mark className="rounded-[3px] bg-lima px-0.5 text-tinta">{resultado.trecho.achado}</mark>
                {resultado.trecho.depois}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
