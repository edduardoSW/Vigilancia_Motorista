"use client";

import { useRef, useState } from "react";
import { useDecisions } from "@/components/decisions-provider";
import { Icon } from "@/components/icons";
import { dia, hora } from "@/content";
import type { Momento } from "@/content/moments";

// Momentos para verificar (prévia 2): hora, o que aconteceu, vídeo e decisão na própria linha.
function PlayIcon({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M8 5v14l11-7L8 5Z" />
    </svg>
  );
}

export function MomentList({ moments }: { moments: Momento[] }) {
  const { decisions, decide, undo, toggleCoached } = useDecisions();
  const [video, setVideo] = useState<Momento | null>(null);
  const dialog = useRef<HTMLDialogElement>(null);

  function openVideo(moment: Momento) {
    setVideo(moment);
    dialog.current?.showModal();
  }

  if (!moments.length) {
    return <p className="border-t border-fio py-6 text-[15px] text-grafite">Nenhum momento para verificar nesta viagem.</p>;
  }

  return (
    <>
      <ol className="border-t border-fio">
        {moments.map((moment) => {
          const decision = decisions[moment.id];
          return (
            <li
              key={moment.id}
              id={`momento-${moment.numero}`}
              className="grid scroll-mt-6 grid-cols-[30px_62px_minmax(0,1fr)_128px_auto] items-center gap-4 border-b border-fio py-3.5"
            >
              <span className="grid size-[26px] place-items-center rounded-full bg-tinta text-[12.5px] font-bold text-white">{moment.numero}</span>
              <span className="text-[16px] font-bold tabular-nums">{hora(moment.inicio)}</span>
              <div className="min-w-0">
                <b className="block text-[15px]">{moment.titulo}</b>
                <span className="text-[13px] text-grafite">{moment.detalhe}</span>
              </div>
              {moment.videoS ? (
                <button
                  type="button"
                  onClick={() => openVideo(moment)}
                  className="flex h-16 items-center justify-center gap-2 rounded-[8px] bg-[#143f33] text-[12.5px] font-semibold text-white transition-colors hover:bg-verde"
                >
                  <PlayIcon size={16} />
                  Ver vídeo · {moment.videoS} s
                </button>
              ) : (
                <span className="text-center text-[13px] font-medium text-grafite">Sem vídeo</span>
              )}
              {decision ? (
                <div className="flex min-w-[196px] flex-col items-start gap-0.5 text-[13px]">
                  <span className="inline-flex items-center gap-1.5 font-semibold">
                    <Icon name="check" size={15} className="text-verde" />
                    {decision.resultado === "confirmado" ? "Confirmado" : "Alarme falso"}
                  </span>
                  <span className="text-grafite">
                    {decision.por}, {dia(decision.em)} às {hora(decision.em)}
                  </span>
                  <span className="flex gap-3">
                    {decision.resultado === "confirmado" && (
                      <button type="button" onClick={() => toggleCoached(moment.id)} className="font-semibold text-verde hover:underline">
                        {decision.orientado ? "Motorista orientado ✓" : "Marcar motorista orientado"}
                      </button>
                    )}
                    <button type="button" onClick={() => undo(moment.id)} className="text-grafite hover:text-tinta hover:underline">
                      Desfazer
                    </button>
                  </span>
                </div>
              ) : (
                <div className="flex min-w-[196px] gap-1.5">
                  <button type="button" onClick={() => decide(moment.id, "confirmado")} className="btn btn-small">
                    Confirmar
                  </button>
                  <button type="button" onClick={() => decide(moment.id, "alarme_falso")} className="btn btn-small">
                    Alarme falso
                  </button>
                </div>
              )}
            </li>
          );
        })}
      </ol>

      <dialog
        ref={dialog}
        onClose={() => setVideo(null)}
        aria-label="Vídeo curto do momento"
        className="fixed inset-0 m-auto h-fit w-[640px] rounded-[14px] border border-fio bg-white p-0 backdrop:bg-tinta/40"
      >
        {video && (
          <div>
            <div className="flex aspect-video flex-col items-center justify-center gap-3 rounded-t-[14px] bg-[#143f33] px-10 text-center text-white">
              <PlayIcon size={36} />
              <p className="text-[15px] font-semibold">Vídeo curto · {video.videoS} s</p>
              <p className="max-w-[420px] text-[13px] text-white/75">
                Na prévia não há vídeo. No app de verdade, aqui toca o vídeo que a caixa gravou quando o sinal se repetiu.
              </p>
            </div>
            <div className="flex items-center justify-between gap-4 px-5 py-4">
              <div>
                <b className="block text-[15px]">{video.titulo}</b>
                <span className="text-[13px] text-grafite">{video.detalhe}</span>
              </div>
              <form method="dialog">
                <button type="submit" className="btn">
                  Fechar
                </button>
              </form>
            </div>
          </div>
        )}
      </dialog>
    </>
  );
}
