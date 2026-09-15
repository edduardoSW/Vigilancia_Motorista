"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useDecisions } from "@/components/decisions-provider";
import { acoesDoMomento } from "@/components/moment-actions";
import { useSession } from "@/components/session-provider";
import { dataCompleta, horaComSegundos, quandoDecidiu } from "@/components/trip/format";
import { guardadoAte, situacaoDoVideo } from "@/components/trip/video-rules";
import { Dialog } from "@/components/ui/dialog";
import { Glyph } from "@/components/ui/glyph";
import { useToast } from "@/components/ui/toast";
import { hora, rotuloDe, segundos, type Viagem } from "@/content";
import type { Momento } from "@/content/moments";
import { bridge, type Motorista } from "@/lib/bridge";
import { cn } from "@/lib/utils";
import { formatarData, hojeIso } from "@/lib/validators";

// Janela do momento (spec 019, VID-01): o vídeo, os campos de cada trecho gravado, o que a caixa registrou e a decisão.
// "Anterior" e "Próximo" passam de momento sem fechar. A Consulta vê o momento sem o vídeo e sem os botões (EQP-02).
function Campo({ rotulo, valor, alarme = false }: { rotulo: string; valor: string; alarme?: boolean }) {
  return (
    <div className="min-w-0">
      <dt className="text-[12.5px] text-grafite">{rotulo}</dt>
      <dd className={cn("truncate text-[13.5px] tabular-nums", alarme && "font-semibold text-alarme")}>{valor}</dd>
    </div>
  );
}

export function MomentDialog({
  open,
  viagem,
  momento,
  motorista,
  total,
  onClose,
  onMudar,
}: {
  open: boolean;
  viagem: Viagem;
  momento: Momento | null;
  /** undefined enquanto o cadastro carrega; null sem cadastro. */
  motorista: Motorista | null | undefined;
  total: number;
  onClose: () => void;
  onMudar: (passo: -1 | 1) => void;
}) {
  const { pode, estado } = useSession();
  const { toast } = useToast();
  const { decisions, pendentes, decide, undo, toggleCoached } = useDecisions();
  const acoes = acoesDoMomento(pode);
  const [trecho, setTrecho] = useState(0);
  const dias = estado?.videos_dias ?? 30;
  const situacao =
    motorista === undefined ? null : situacaoDoVideo({ coletadoEm: viagem.chegada, dias, hoje: hojeIso(), termoAssinado: Boolean(motorista?.termo.assinado) });
  const temVideo = Boolean(momento?.videos.length);
  const livre = Boolean(open && momento && temVideo && acoes.video && situacao?.tipo === "disponivel");

  // Abrir o momento com vídeo liberado conta como abrir o vídeo (registro de atividades; o Python confere de novo).
  useEffect(() => {
    if (!livre || !momento) return;
    let vivo = true;
    bridge.video_abrir(momento.id, viagem.motorista).then((resposta) => {
      if (!vivo) return;
      if (!resposta.ok) toast({ text: resposta.erro });
      else if (!resposta.dados.liberado) toast({ text: resposta.dados.motivo ?? "Vídeo trancado." });
    });
    return () => {
      vivo = false;
    };
  }, [livre, momento, viagem.motorista, toast]);

  if (!momento) return null;
  const decisao = decisions[momento.id];
  const ocupado = pendentes.has(momento.id);
  const video = momento.videos[Math.min(trecho, momento.videos.length - 1)];
  const eventos = viagem.eventos.filter((evento) => momento.id === `${viagem.id}-${evento.id}` || (evento.episodio && momento.id === `${viagem.id}-${evento.episodio}`));

  let areaDoVideo: React.ReactNode;
  if (!acoes.video) {
    areaDoVideo = (
      <>
        <Glyph name="lock" size={28} />
        <p className="text-[14.5px] font-semibold">Sua função não vê os vídeos</p>
        <p className="text-[13px]">Administrador e supervisor veem os trechos gravados deste momento.</p>
      </>
    );
  } else if (!temVideo) {
    areaDoVideo = (
      <>
        <Glyph name="video" size={28} />
        <p className="text-[14.5px] font-semibold">Sem vídeo neste momento</p>
        <p className="text-[13px]">{momento.semVideo}</p>
      </>
    );
  } else if (!situacao) {
    areaDoVideo = <p className="text-[14px]">Conferindo o termo do motorista…</p>;
  } else if (situacao.tipo !== "disponivel") {
    areaDoVideo = (
      <>
        <Glyph name="lock" size={28} />
        <p className="text-[14.5px] font-semibold">{situacao.texto}</p>
        <p className="text-[13px]">{situacao.tipo === "apagado" ? "O registro do momento continua; só o vídeo saiu." : "Registre o termo de ciência para liberar os vídeos deste motorista."}</p>
        {situacao.tipo === "trancado" && motorista && pode("cadastrar") && (
          <Link href={`/motoristas/?abrir=${motorista.id}`} className="btn btn-small mt-1">
            Abrir o cadastro do motorista
          </Link>
        )}
      </>
    );
  } else {
    areaDoVideo = (
      <>
        <Glyph name="play" size={34} />
        <p className="text-[15px] font-semibold">
          Trecho {Math.min(trecho, momento.videos.length - 1) + 1} de {momento.videos.length} · {segundos(video.duracaoS)}
        </p>
        <p className="text-[13px] opacity-75">Prévia: vídeo fictício, sem imagem. No app de verdade, aqui toca o trecho que a caixa gravou.</p>
      </>
    );
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      width={780}
      title={`Momento ${momento.numero} · ${hora(momento.inicio)}`}
      summary={`${momento.titulo} · ${momento.detalhe}`}
      footer={
        <>
          <div className="mr-auto flex gap-2">
            <button type="button" className="btn btn-quiet" disabled={momento.numero <= 1} onClick={() => onMudar(-1)}>
              Anterior
            </button>
            <button type="button" className="btn btn-quiet" disabled={momento.numero >= total} onClick={() => onMudar(1)}>
              Próximo
            </button>
          </div>
          <button type="button" className="btn" onClick={onClose}>
            Fechar
          </button>
        </>
      }
    >
      <div
        className={cn(
          "grid aspect-video max-h-[300px] w-full place-items-center rounded-[10px] px-8 text-center",
          livre ? "bg-video text-sobre-video" : "border border-fio bg-lateral text-grafite",
        )}
      >
        <div className="grid max-w-[480px] justify-items-center gap-2">{areaDoVideo}</div>
      </div>

      {temVideo && acoes.video && (
        <>
          <h3 className="mt-6 font-titulo text-[16px] font-semibold">
            {momento.videos.length === 1 ? "Trecho gravado" : `${momento.videos.length} trechos gravados`}
          </h3>
          <ol className="mt-2 grid gap-2">
            {momento.videos.map((item, indice) => {
              const escolhido = indice === Math.min(trecho, momento.videos.length - 1);
              return (
                <li key={item.id} className={cn("rounded-[10px] border p-3", escolhido ? "border-verde bg-selecao" : "border-fio bg-superficie")}>
                  <div className="flex min-h-8 items-center justify-between gap-3">
                    <b className="text-[14px] font-semibold">Trecho {indice + 1}</b>
                    {!escolhido && (
                      <button type="button" className="btn btn-small" onClick={() => setTrecho(indice)}>
                        Ver este trecho
                      </button>
                    )}
                  </div>
                  <dl className="mt-2 grid grid-cols-4 gap-x-4 gap-y-2">
                    <Campo rotulo="Início" valor={horaComSegundos(item.inicio)} />
                    <Campo rotulo="Fim" valor={horaComSegundos(item.fim)} />
                    <Campo rotulo="Duração" valor={segundos(item.duracaoS)} />
                    <Campo rotulo="Câmera" valor={item.camera} />
                    <Campo rotulo="Caixa" valor={viagem.caixa} />
                    <Campo rotulo="Coletado em" valor={`${dataCompleta(viagem.chegada)} às ${hora(viagem.chegada)}`} />
                    <Campo rotulo="Fica guardado até" valor={formatarData(guardadoAte(viagem.chegada, dias))} />
                    <Campo rotulo="Situação" valor={situacao?.texto ?? "Conferindo…"} alarme={Boolean(situacao && situacao.tipo !== "disponivel")} />
                  </dl>
                </li>
              );
            })}
          </ol>
        </>
      )}

      <h3 className="mt-6 font-titulo text-[16px] font-semibold">O que a caixa registrou</h3>
      <ul className="mt-2 divide-y divide-fio border-y border-fio text-[13.5px]">
        {eventos.map((evento) => (
          <li key={evento.id} className="flex items-center gap-4 py-2">
            <span className="w-12 tabular-nums text-grafite">{hora(evento.hora)}</span>
            <span className="min-w-0 flex-1 truncate">{rotuloDe(evento.tipo)}</span>
            <span className="tabular-nums text-grafite">{evento.duracaoS ? segundos(evento.duracaoS) : ""}</span>
          </li>
        ))}
      </ul>

      <h3 className="mt-6 font-titulo text-[16px] font-semibold">Decisão</h3>
      {decisao ? (
        <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-2 text-[14px]">
          <span className="inline-flex items-center gap-1.5 font-semibold">
            <Glyph name="check" size={16} className="text-verde" />
            {decisao.resultado === "confirmado" ? "Confirmado" : "Alarme falso"}
          </span>
          <span className="text-grafite">
            {decisao.por}, {quandoDecidiu(decisao.em)}
          </span>
          {acoes.decidir && decisao.resultado === "confirmado" && (
            <button type="button" className="btn btn-small" disabled={ocupado} onClick={() => void toggleCoached(momento.id)}>
              {decisao.orientado ? "Motorista orientado ✓" : "Marcar motorista orientado"}
            </button>
          )}
          {!acoes.decidir && decisao.orientado && <span className="text-grafite">Motorista orientado</span>}
          {acoes.decidir && (
            <button type="button" className="btn btn-small btn-quiet" disabled={ocupado} onClick={() => void undo(momento.id)}>
              Desfazer
            </button>
          )}
        </div>
      ) : acoes.decidir ? (
        <div className="mt-2 flex gap-2">
          <button type="button" className="btn btn-primary" disabled={ocupado} onClick={() => void decide(momento.id, "confirmado")}>
            Confirmar
          </button>
          <button type="button" className="btn" disabled={ocupado} onClick={() => void decide(momento.id, "alarme_falso")}>
            Alarme falso
          </button>
        </div>
      ) : (
        <p className="mt-2 text-[14px] text-grafite">Falta verificar.</p>
      )}
      <p className="mt-4 text-[12.5px] text-grafite">Os alertas ajudam a sua avaliação e não são diagnóstico.</p>
    </Dialog>
  );
}
