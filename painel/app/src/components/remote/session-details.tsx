"use client";

import { useEffect, useState } from "react";
import tiposDeEvento from "@/content/tipos-de-evento.json";
import { Glyph } from "@/components/ui/glyph";
import { bridge, type SessaoRemotaDetalhe, type TrechoParaTocar, type TrechoRemoto } from "@/lib/bridge";
import { cn } from "@/lib/utils";
import { ClipPlayer } from "./clip-player";
import { dataHora, deslocamento, duracaoTexto, hora, nomeDoTipo, percentual, textoRisco, type TiposDeEvento } from "./remote-data";

const tipos = tiposDeEvento as TiposDeEvento;

function Dado({ rotulo, children }: { rotulo: string; children: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="text-[12.5px] text-grafite">{rotulo}</dt>
      <dd className="mt-0.5 truncate text-[14.5px] font-semibold tabular-nums">{children}</dd>
    </div>
  );
}

// Uma sessão de teste de outro computador (spec 026, decisão 8): resumo, linha do tempo e os trechos com player.
// Os trechos só aparecem para quem tem `ver_video` (a Ponte já devolve a lista vazia para a Consulta, PCE-07).
export function SessionDetails({ sessaoUid }: { sessaoUid: string }) {
  const [detalhe, setDetalhe] = useState<SessaoRemotaDetalhe | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [escolhido, setEscolhido] = useState<string | null>(null);
  const [tocar, setTocar] = useState<TrechoParaTocar | null>(null);
  const [abrindo, setAbrindo] = useState(false);

  useEffect(() => {
    let vivo = true;
    bridge.remotos_sessao(sessaoUid).then((resposta) => {
      if (!vivo) return;
      if (resposta.ok) setDetalhe(resposta.dados);
      else setErro(resposta.erro);
    });
    return () => {
      vivo = false;
    };
  }, [sessaoUid]);

  async function abrirTrecho(uid: string) {
    setEscolhido(uid);
    setAbrindo(true);
    const resposta = await bridge.remotos_trecho(uid);
    setAbrindo(false);
    setTocar(resposta.ok ? resposta.dados : { uid, disponivel: false, motivo: resposta.erro } as TrechoParaTocar);
  }

  if (erro) return <p role="alert" className="text-[14px] text-alarme">{erro}</p>;
  if (!detalhe) return <p className="text-[14px] text-grafite">Carregando a sessão…</p>;

  const { sessao, eventos, trechos, pode_ver_trechos: podeVer } = detalhe;
  const resumo = sessao.resumo;
  const porTipo = Object.entries(resumo.eventos_por_tipo ?? {}).sort((a, b) => b[1] - a[1]);
  const trechoDoEvento = new Map(trechos.map((trecho) => [trecho.uid, trecho]));

  return (
    <div className="grid gap-6">
      <dl className="grid grid-cols-3 gap-x-6 gap-y-4 rounded-[12px] border border-fio bg-superficie p-4">
        <Dado rotulo="Computador">{sessao.aparelho_nome}</Dado>
        <Dado rotulo="Começou">{dataHora(sessao.iniciada_em)}</Dado>
        <Dado rotulo={sessao.em_andamento ? "Até agora" : "Duração"}>{duracaoTexto(resumo.duracao_s)}</Dado>
        <Dado rotulo="PERCLOS médio">{percentual(resumo.perclos_medio)}</Dado>
        <Dado rotulo="Piscadas por minuto">{typeof resumo.piscadas_por_minuto === "number" ? Math.round(resumo.piscadas_por_minuto) : "sem medida"}</Dado>
        <Dado rotulo="Câmera">{sessao.camera ?? "não informada"}</Dado>
      </dl>

      {porTipo.length > 0 && (
        <section aria-labelledby="sessao-tipos">
          <h3 id="sessao-tipos" className="font-titulo text-[16px] font-semibold">
            Eventos por tipo
          </h3>
          <ul className="mt-2 grid gap-1.5 text-[14px]">
            {porTipo.map(([tipo, total]) => (
              <li key={tipo} className="flex items-baseline justify-between gap-4 border-b border-fio pb-1.5">
                <span>{nomeDoTipo(tipo, tipos)}</span>
                <span className="tabular-nums text-grafite">{total}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section aria-labelledby="sessao-linha">
        <h3 id="sessao-linha" className="font-titulo text-[16px] font-semibold">
          Linha do tempo
        </h3>
        {eventos.length === 0 ? (
          <p className="mt-2 text-[14px] text-grafite">Nenhum evento nesta sessão.</p>
        ) : (
          <ol className="mt-2 grid">
            {eventos.map((evento) => {
              const risco = textoRisco(evento.nivel_risco);
              const trecho = evento.trecho_uid ? trechoDoEvento.get(evento.trecho_uid) : undefined;
              return (
                <li key={evento.uid} className="grid grid-cols-[72px_minmax(0,1fr)_auto] items-center gap-3 border-b border-fio py-2 text-[14px]">
                  <span className="tabular-nums text-grafite">{deslocamento(evento.ocorrido_em, sessao.iniciada_em) || hora(evento.ocorrido_em)}</span>
                  <span className="min-w-0">
                    <span className="block truncate">{nomeDoTipo(evento.tipo, tipos)}</span>
                    <span className={cn("block text-[12.5px]", risco.alarme ? "font-semibold text-alarme" : "text-grafite")}>
                      {risco.texto}
                      {evento.duracao_s ? ` · ${duracaoTexto(evento.duracao_s)}` : ""}
                    </span>
                  </span>
                  {podeVer && trecho ? (
                    <button type="button" className="btn btn-small" onClick={() => void abrirTrecho(trecho.uid)}>
                      <Glyph name="video" size={14} />
                      Ver trecho
                    </button>
                  ) : (
                    <span />
                  )}
                </li>
              );
            })}
          </ol>
        )}
      </section>

      <section aria-labelledby="sessao-trechos">
        <h3 id="sessao-trechos" className="font-titulo text-[16px] font-semibold">
          Trechos de vídeo
        </h3>
        {!podeVer ? (
          <p className="mt-2 text-[14px] text-grafite">Os trechos de vídeo ficam com administradores e supervisores.</p>
        ) : trechos.length === 0 ? (
          <p className="mt-2 text-[14px] text-grafite">Nenhum trecho gravado nesta sessão.</p>
        ) : (
          <div className="mt-2 grid gap-3">
            <ul className="flex flex-wrap gap-2">
              {trechos.map((trecho) => (
                <li key={trecho.uid}>
                  <BotaoTrecho trecho={trecho} ativo={escolhido === trecho.uid} onClick={() => void abrirTrecho(trecho.uid)} />
                </li>
              ))}
            </ul>
            {abrindo && <p className="text-[13.5px] text-grafite">Abrindo o trecho…</p>}
            {!abrindo && tocar && <ClipPlayer trecho={tocar} />}
            {!abrindo && !tocar && <p className="text-[13.5px] text-grafite">Escolha um trecho para ver os 8 s antes e os 8 s depois do momento.</p>}
          </div>
        )}
      </section>
    </div>
  );
}

function BotaoTrecho({ trecho, ativo, onClick }: { trecho: TrechoRemoto; ativo: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      aria-pressed={ativo}
      onClick={onClick}
      className={cn(
        "flex min-w-[172px] flex-col items-start rounded-[10px] border px-3 py-2 text-left transition-colors",
        ativo ? "border-verde bg-selecao" : "border-fio bg-superficie hover:border-tinta/30",
      )}
    >
      <span className="text-[13.5px] font-semibold">{nomeDoTipo(trecho.tipo, tipos)}</span>
      <span className={cn("text-[12.5px] tabular-nums", trecho.baixado ? "text-grafite" : "text-alarme")}>
        {hora(trecho.inicio)} · {trecho.baixado ? duracaoTexto(trecho.duracao_s) : trecho.erro ? "não baixou" : "baixando"}
      </span>
    </button>
  );
}
