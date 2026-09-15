"use client";

import { useEffect, useMemo, useState } from "react";
import { EVENTO_BLOQUEIO } from "@/components/auth-gate";
import { useDecisions } from "@/components/decisions-provider";
import { acoesDoMomento } from "@/components/moment-actions";
import { useSession, useVisao } from "@/components/session-provider";
import { quandoDecidiu } from "@/components/trip/format";
import { MomentDialog } from "@/components/trip/moment-dialog";
import { situacaoDoVideo } from "@/components/trip/video-rules";
import { CardGrid, CardInfo, CardTitulo } from "@/components/ui/card-grid";
import { Glyph } from "@/components/ui/glyph";
import { ViewToggle } from "@/components/ui/view-toggle";
import { hora, segundos, viagemDe } from "@/content";
import { momentosDaViagem, type Momento } from "@/content/moments";
import { bridge, type Motorista } from "@/lib/bridge";
import { cn } from "@/lib/utils";
import { hojeIso } from "@/lib/validators";

// Momentos para verificar (prévia 2 e spec 019): em lista ou cards. Todo momento mostra o campo Vídeo e abre a janela do
// momento (vídeo, trechos, o que a caixa registrou e decisão). A Consulta vê sem vídeo e sem botões (spec 014, EQP-02).
const trechos = (total: number) => (total === 1 ? "1 trecho" : `${total} trechos`);

export function MomentList({ viagemId }: { viagemId: string }) {
  const viagem = viagemDe(viagemId)!;
  const moments = useMemo(() => momentosDaViagem(viagem), [viagem]);
  const { pode, usuario, estado } = useSession();
  const { decisions, pendentes, decide, undo, toggleCoached } = useDecisions();
  const [visao, setVisao] = useVisao("momentos");
  const acoes = acoesDoMomento(pode);
  const [motorista, setMotorista] = useState<Motorista | null | undefined>(undefined);
  const [aberto, setAberto] = useState(false);
  const [momentoId, setMomentoId] = useState<string | null>(null);
  const usuarioId = usuario?.id ?? null;

  // O termo do motorista decide se o vídeo está liberado (spec 015, decisão 2).
  useEffect(() => {
    if (usuarioId === null) return;
    let vivo = true;
    bridge.motoristas_listar().then((resposta) => {
      if (vivo) setMotorista(resposta.ok ? (resposta.dados.find((item) => item.ref === viagem.motorista) ?? null) : null);
    });
    return () => {
      vivo = false;
    };
  }, [usuarioId, viagem.motorista]);

  // O número na barra da viagem (#momento-3) abre a janela do momento; a tela bloqueada fecha.
  useEffect(() => {
    const peloEndereco = () => {
      const achado = /^#momento-(\d+)$/.exec(window.location.hash);
      const escolhido = achado ? moments[Number(achado[1]) - 1] : undefined;
      if (!escolhido) return;
      setMomentoId(escolhido.id);
      setAberto(true);
    };
    const fechar = () => setAberto(false);
    window.addEventListener("hashchange", peloEndereco);
    window.addEventListener(EVENTO_BLOQUEIO, fechar);
    return () => {
      window.removeEventListener("hashchange", peloEndereco);
      window.removeEventListener(EVENTO_BLOQUEIO, fechar);
    };
  }, [moments]);

  const dias = estado?.videos_dias ?? 30;
  const situacao =
    motorista === undefined ? null : situacaoDoVideo({ coletadoEm: viagem.chegada, dias, hoje: hojeIso(), termoAssinado: Boolean(motorista?.termo.assinado) });

  function abrir(momento: Momento) {
    setMomentoId(momento.id);
    setAberto(true);
  }

  function fechar() {
    setAberto(false);
    if (window.location.hash) window.history.replaceState(null, "", window.location.pathname + window.location.search);
  }

  function mudar(passo: -1 | 1) {
    const proximo = moments[moments.findIndex((item) => item.id === momentoId) + passo];
    if (proximo) setMomentoId(proximo.id);
  }

  /** Texto do campo Vídeo, igual na lista e no card. */
  function resumoDoVideo(momento: Momento) {
    if (!momento.videos.length) return { livre: false, texto: "Sem vídeo" };
    if (!situacao) return { livre: false, texto: "Conferindo o vídeo…" };
    if (situacao.tipo === "apagado") return { livre: false, texto: "Vídeo apagado pelo prazo" };
    if (situacao.tipo === "trancado") return { livre: false, texto: "Vídeo trancado: falta o termo" };
    return { livre: true, texto: `${trechos(momento.videos.length)} · ${segundos(momento.videoS ?? 0)}` };
  }

  const decisaoEmTexto = (momento: Momento) => {
    const decisao = decisions[momento.id];
    if (!decisao) return "Falta verificar";
    return `${decisao.resultado === "confirmado" ? "Confirmado" : "Alarme falso"}${decisao.orientado ? ", orientado" : ""} · ${decisao.por}`;
  };

  return (
    <section aria-labelledby="momentos" className="mt-[30px]">
      <div className="mb-3 flex items-end justify-between gap-4">
        <h2 id="momentos" className="font-titulo text-[20px] font-semibold">
          Momentos para verificar
        </h2>
        {moments.length > 0 && <ViewToggle value={visao} onChange={setVisao} className="no-print" />}
      </div>

      {!moments.length ? (
        <p className="border-t border-fio py-6 text-[15px] text-grafite">Nenhum momento para verificar nesta viagem.</p>
      ) : visao === "lista" ? (
        <ol className="border-t border-fio">
          {moments.map((momento) => {
            const decisao = decisions[momento.id];
            const ocupado = pendentes.has(momento.id);
            const video = resumoDoVideo(momento);
            return (
              <li
                key={momento.id}
                id={`momento-${momento.numero}`}
                className="grid scroll-mt-6 grid-cols-[30px_62px_minmax(0,1fr)_170px_236px] items-center gap-4 border-b border-fio py-3.5"
              >
                <span className="grid size-[26px] place-items-center rounded-full bg-tinta text-[12.5px] font-bold text-papel">{momento.numero}</span>
                <span className="text-[16px] font-bold tabular-nums">{hora(momento.inicio)}</span>
                <button type="button" onClick={() => abrir(momento)} className="min-w-0 text-left">
                  <b className="block text-[15px] hover:underline">{momento.titulo}</b>
                  <span className="text-[13px] text-grafite">{momento.detalhe}</span>
                </button>
                {!acoes.video ? (
                  <span aria-hidden="true" />
                ) : momento.videos.length ? (
                  <button
                    type="button"
                    onClick={() => abrir(momento)}
                    className={cn(
                      "flex h-14 items-center justify-center gap-2 rounded-[8px] px-2 text-center text-[12.5px] font-semibold leading-tight transition-opacity",
                      video.livre ? "bg-video text-sobre-video ring-1 ring-inset ring-sobre-video/15 hover:opacity-90" : "border border-fio bg-lateral text-grafite",
                    )}
                  >
                    <Glyph name={video.livre ? "play" : "lock"} size={16} />
                    {video.texto}
                  </button>
                ) : (
                  <button type="button" onClick={() => abrir(momento)} title={momento.semVideo ?? undefined} className="text-center text-[13px] font-medium text-grafite hover:text-tinta">
                    Sem vídeo
                  </button>
                )}
                {decisao ? (
                  <div className="flex min-w-0 flex-col items-start gap-0.5 text-[13px]">
                    <span className="inline-flex items-center gap-1.5 font-semibold">
                      <Glyph name="check" size={15} className="text-verde" />
                      {decisao.resultado === "confirmado" ? "Confirmado" : "Alarme falso"}
                    </span>
                    <span className="text-grafite">
                      {decisao.por}, {quandoDecidiu(decisao.em)}
                    </span>
                    {acoes.decidir ? (
                      <span className={cn("flex gap-3", ocupado && "opacity-60")}>
                        {decisao.resultado === "confirmado" && (
                          <button type="button" disabled={ocupado} onClick={() => void toggleCoached(momento.id)} className="font-semibold text-verde hover:underline">
                            {decisao.orientado ? "Motorista orientado ✓" : "Marcar motorista orientado"}
                          </button>
                        )}
                        <button type="button" disabled={ocupado} onClick={() => void undo(momento.id)} className="text-grafite hover:text-tinta hover:underline">
                          Desfazer
                        </button>
                      </span>
                    ) : (
                      decisao.orientado && <span className="text-grafite">Motorista orientado</span>
                    )}
                  </div>
                ) : acoes.decidir ? (
                  <div className="flex gap-1.5">
                    <button type="button" disabled={ocupado} onClick={() => void decide(momento.id, "confirmado")} className="btn btn-small">
                      Confirmar
                    </button>
                    <button type="button" disabled={ocupado} onClick={() => void decide(momento.id, "alarme_falso")} className="btn btn-small">
                      Alarme falso
                    </button>
                  </div>
                ) : (
                  <span className="text-[13px] text-grafite">Falta verificar</span>
                )}
              </li>
            );
          })}
        </ol>
      ) : (
        <CardGrid
          label="Momentos para verificar"
          items={moments}
          getId={(momento: Momento) => momento.id}
          selectedId={aberto ? momentoId : null}
          onOpen={abrir}
          minWidth={280}
          renderCard={(momento: Momento) => {
            const video = resumoDoVideo(momento);
            const mostrarVideo = acoes.video && momento.videos.length > 0;
            return (
              <>
                <span
                  className={cn(
                    "grid aspect-video w-full place-items-center rounded-[8px] px-4 text-center text-[13px]",
                    mostrarVideo && video.livre ? "bg-video text-sobre-video" : "bg-lateral text-grafite",
                  )}
                >
                  <span className="grid justify-items-center gap-1.5">
                    <Glyph name={!acoes.video || (momento.videos.length && !video.livre) ? "lock" : momento.videos.length ? "play" : "video"} size={22} />
                    <span className="font-semibold">{!acoes.video ? "Vídeo só para supervisor e administrador" : video.texto}</span>
                    {acoes.video && !momento.videos.length && <span className="text-[12px]">{momento.semVideo}</span>}
                  </span>
                </span>
                <CardTitulo titulo={momento.titulo} detalhe={`Momento ${momento.numero} · ${hora(momento.inicio)} · ${momento.detalhe}`} />
                <CardInfo rotulo="Decisão">{decisaoEmTexto(momento)}</CardInfo>
              </>
            );
          }}
        />
      )}

      <MomentDialog
        key={momentoId ?? "nenhum"}
        open={aberto}
        viagem={viagem}
        momento={moments.find((item) => item.id === momentoId) ?? null}
        motorista={motorista}
        total={moments.length}
        onClose={fechar}
        onMudar={mudar}
      />
    </section>
  );
}
