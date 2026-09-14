"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { CAPITULOS, buscarNoGuia, capituloDe, type CapituloId } from "@/content/guide";
import { PageHeader } from "@/components/ui/page-header";
import { SideList } from "@/components/settings/side-list";
import { GuideArticle } from "./guide-article";
import { SearchResults } from "./search-results";

const ITENS = CAPITULOS.map((capitulo) => ({ id: capitulo.id, label: capitulo.titulo, prefix: String(capitulo.numero) }));

// Guia de uso (spec 017; prévia 9): capítulos à esquerda, busca no topo, artigo à direita. Todas as funções abrem.
export function GuideScreen() {
  const router = useRouter();
  const params = useSearchParams();
  const capitulo = capituloDe(params.get("capitulo")) ?? CAPITULOS[0];
  const [busca, setBusca] = useState("");
  const campo = useRef<HTMLInputElement>(null);
  const alvo = useRef<string | null>(null);
  const resultados = useMemo(() => (busca.trim() ? buscarNoGuia(busca) : null), [busca]);

  function abrir(id: CapituloId, topicoId: string | null = null) {
    alvo.current = topicoId;
    setBusca("");
    router.replace(`/guia/?capitulo=${id}`, { scroll: false });
  }

  // Vai até o tópico escolhido na busca ou pedido por ?passo= (link "Guia" do cabeçalho de cada tela).
  const passo = params.get("passo");
  useEffect(() => {
    const topico = alvo.current ?? passo;
    alvo.current = null;
    const elemento = topico ? document.getElementById(topico) : null;
    if (elemento) elemento.scrollIntoView({ block: "start" });
    else document.getElementById("conteudo")?.scrollTo({ top: 0 });
  }, [capitulo.id, passo]);

  useEffect(() => {
    const aoTeclar = (evento: KeyboardEvent) => {
      const digitando = evento.target instanceof HTMLElement && evento.target.closest("input, textarea, select");
      if (evento.key === "/" && !digitando) {
        evento.preventDefault();
        campo.current?.focus();
      }
    };
    window.addEventListener("keydown", aoTeclar);
    return () => window.removeEventListener("keydown", aoTeclar);
  }, []);

  return (
    <section className="anim-enter max-w-[1100px] px-14 pb-16 pt-[34px]">
      <PageHeader
        title="Guia de uso"
        summary={`${CAPITULOS.length} capítulos, passo a passo`}
        actions={
          <input
            ref={campo}
            type="search"
            className="input w-[320px]"
            placeholder="O que você quer fazer?"
            aria-label="Buscar no guia"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Escape") setBusca("");
              if (e.key === "Enter" && resultados?.[0]) abrir(resultados[0].capituloId, resultados[0].topicoId);
            }}
          />
        }
      />

      <div className="mt-8 grid grid-cols-[260px_minmax(0,1fr)] gap-12">
        <div className="no-print">
          <SideList label="Capítulos do guia" items={ITENS} value={capitulo.id} onChange={(id) => abrir(id)} />
        </div>
        <div className="min-w-0">
          {resultados ? (
            <SearchResults consulta={busca} resultados={resultados} onOpen={abrir} />
          ) : (
            <GuideArticle key={capitulo.id} capitulo={capitulo} />
          )}
        </div>
      </div>
    </section>
  );
}
