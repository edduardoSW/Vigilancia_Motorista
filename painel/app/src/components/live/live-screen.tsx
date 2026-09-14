"use client";

import { PageHeader } from "@/components/ui/page-header";
import { cn } from "@/lib/utils";
import { StatusLine, TIPOS, quando } from "./live-status";
import { nomeDoTipo, resumoDosEventos } from "./summary";
import { eventosVisiveis, useScriptLocal } from "./use-script-local";

const MOSTRAR = 100;

function duracao(segundos: number | null): string {
  if (segundos === null || segundos <= 0) return "";
  if (segundos < 60) return `${segundos.toLocaleString("pt-BR", { maximumFractionDigits: 1 })} s`;
  return `${Math.round(segundos / 60)} min`;
}

// Tela "Teste neste computador" (spec 018): o script da caixa rodando aqui, reconhecido sozinho, e os eventos dele.
export function LiveScreen() {
  const { estado, erro, eventos, novos } = useScriptLocal();
  const aberto = Boolean(estado?.aberto);
  const visiveis = eventosVisiveis(estado, eventos);
  const linhas = visiveis.slice(0, MOSTRAR);
  const contagem = visiveis.length === 1 ? "1 evento" : `${visiveis.length} eventos`;
  const resumo =
    visiveis.length === 0
      ? aberto
        ? "Nenhum evento nesta sessão ainda"
        : "Nenhum evento capturado ainda"
      : `${contagem} ${aberto ? "nesta sessão" : "capturados"} · ${resumoDosEventos(visiveis, TIPOS)}`;

  return (
    <section className="anim-enter max-w-[980px] px-14 pb-16 pt-[34px]">
      <PageHeader title="Teste neste computador" summary={resumo} />

      <StatusLine estado={estado} erro={erro} className="mt-1 border-y border-fio py-4 text-[16px]" />

      <h2 className="mt-8 text-[14px] font-bold">{aberto ? "Eventos desta sessão" : "Últimos eventos capturados"}</h2>
      {linhas.length === 0 ? (
        <p className="mt-3 text-[14px] text-grafite">
          {aberto ? "Os eventos aparecem aqui assim que o script registrar." : "Quando o script registrar algo, aparece aqui."}
        </p>
      ) : (
        <div role="table" aria-label="Eventos do script" className="mt-3 max-h-[60vh] overflow-y-auto border-b border-fio">
          <div
            role="row"
            className="sticky top-0 grid h-9 grid-cols-[110px_minmax(0,1fr)_90px_80px] items-center gap-4 border-b border-fio bg-papel text-[12.5px] font-semibold text-grafite"
          >
            <span role="columnheader">Quando</span>
            <span role="columnheader">O que aconteceu</span>
            <span role="columnheader">Nível</span>
            <span role="columnheader" className="text-right">
              Duração
            </span>
          </div>
          {linhas.map((evento) => (
            <div
              role="row"
              key={evento.id}
              className={cn(
                "grid h-12 grid-cols-[110px_minmax(0,1fr)_90px_80px] items-center gap-4 border-b border-fio text-[14px] last:border-b-0 hover:bg-lateral",
                novos.has(evento.id) && "anim-row",
              )}
            >
              <span role="cell" className="text-grafite tabular-nums">
                {quando(evento.em)}
              </span>
              <span role="cell" className="truncate">
                {nomeDoTipo(evento.tipo, TIPOS)}
              </span>
              <span role="cell" className={evento.risco >= 3 ? "font-semibold text-alarme" : "text-grafite"}>
                Nível {evento.risco}
              </span>
              <span role="cell" className="text-right text-grafite tabular-nums">
                {duracao(evento.duracao_s)}
              </span>
            </div>
          ))}
        </div>
      )}

      {estado?.pasta && <p className="mt-6 text-[12.5px] text-grafite">Lendo os eventos de {estado.pasta}</p>}
    </section>
  );
}
