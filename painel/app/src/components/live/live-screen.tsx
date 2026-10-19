"use client";

import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { PageHeader } from "@/components/ui/page-header";
import { Tabs } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import { abasDoAoVivo, type IdDaAba } from "./camera-regras";
import { CameraDoAparelho } from "./camera-tela";
import { StatusLine, TIPOS, quando } from "./live-status";
import { nomeDoTipo, resumoDosEventos } from "./summary";
import { eventosVisiveis, useScriptLocal, type ScriptLocalAoVivo } from "./use-script-local";

const MOSTRAR = 100;
// Painel instalado: script local e câmera. Painel web (transporte "servidor", na VPS): não há script local, só a câmera.
const ABAS = abasDoAoVivo(process.env.NEXT_PUBLIC_PAINEL_TRANSPORTE);
const RESUMO_DA_CAMERA = "Malha do rosto, sinais de sono e pulso estimado, tudo calculado neste aparelho";

function duracao(segundos: number | null): string {
  if (segundos === null || segundos <= 0) return "";
  if (segundos < 60) return `${segundos.toLocaleString("pt-BR", { maximumFractionDigits: 1 })} s`;
  return `${Math.round(segundos / 60)} min`;
}

// Tela Ao vivo: "Teste neste computador" (spec 018, o script da caixa rodando aqui) e o teste com a câmera do
// aparelho (spec 025). Na web, só a câmera.
export function LiveScreen() {
  return ABAS.length === 1 ? <SoCamera /> : <ComAbas />;
}

function SoCamera() {
  return (
    <section className="anim-enter max-w-[1240px] px-14 pb-16 pt-[34px]">
      <PageHeader title="Teste com a câmera" summary={RESUMO_DA_CAMERA} />
      <CameraDoAparelho />
    </section>
  );
}

function ComAbas() {
  const script = useScriptLocal();
  const params = useSearchParams();
  const [escolhida, setEscolhida] = useState<IdDaAba | null>(null);
  const aba: IdDaAba = escolhida ?? (params.get("aba") === "camera" ? "camera" : "script");
  const rotulo = ABAS.find((item) => item.id === aba)?.rotulo;

  function escolher(id: string) {
    const nova = id === "camera" ? "camera" : "script";
    setEscolhida(nova);
    // A aba fica no endereço: recarregar ou mandar o link abre na mesma aba.
    window.history.replaceState(null, "", nova === "camera" ? "?aba=camera" : window.location.pathname);
  }

  return (
    <section className={cn("anim-enter px-14 pb-16 pt-[34px]", aba === "script" ? "max-w-[980px]" : "max-w-[1240px]")}>
      <PageHeader title="Teste neste computador" summary={aba === "script" ? resumoDoScript(script) : RESUMO_DA_CAMERA} />
      <Tabs items={ABAS.map((item) => ({ id: item.id, label: item.rotulo }))} value={aba} onChange={escolher} label="O que testar" />
      <div role="tabpanel" aria-label={rotulo}>
        {aba === "script" ? <ScriptNesteComputador {...script} /> : <CameraDoAparelho />}
      </div>
    </section>
  );
}

function resumoDoScript({ estado, eventos }: ScriptLocalAoVivo): string {
  const aberto = Boolean(estado?.aberto);
  const visiveis = eventosVisiveis(estado, eventos);
  const contagem = visiveis.length === 1 ? "1 evento" : `${visiveis.length} eventos`;
  if (visiveis.length === 0) return aberto ? "Nenhum evento nesta sessão ainda" : "Nenhum evento capturado ainda";
  return `${contagem} ${aberto ? "nesta sessão" : "capturados"} · ${resumoDosEventos(visiveis, TIPOS)}`;
}

// Spec 018: o script da caixa rodando aqui, reconhecido sozinho, e os eventos dele.
function ScriptNesteComputador({ estado, erro, eventos, novos }: ScriptLocalAoVivo) {
  const aberto = Boolean(estado?.aberto);
  const linhas = eventosVisiveis(estado, eventos).slice(0, MOSTRAR);

  return (
    <>
      <StatusLine estado={estado} erro={erro} className="border-b border-fio py-4 text-[16px]" />

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
    </>
  );
}
