"use client";

import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";
import type { Carga, Instantaneo, SessaoDaCamera } from "./camera-motor";
import { erroDaCamera, formatarRelogio, formatarSegundos } from "./camera-regras";

export type Fase = "aviso" | "pedindo" | "carregando" | "rodando" | "parado" | "erro";

export type ResumoDaSessao = { duracao: number; eventos: number; piscadas: number; bocejos: number; cabeceios: number };

const megas = (bytes: number) => (bytes / 1e6).toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });

// Vídeo espelhado só na tela (o MediaPipe recebe o original, então "olho esquerdo" continua sendo o da pessoa), com a
// malha num canvas por cima e os avisos de cada fase. O vídeo existe desde o início: é nele que a câmera abre.
export function Palco({
  fase,
  videoRef,
  stream,
  sessao,
  leitura,
  carga,
  erro,
  instalado,
  resumo,
  foco,
  aoLigar,
  aoQuadro,
  aoFalhar,
}: {
  fase: Fase;
  videoRef: React.RefObject<HTMLVideoElement | null>;
  stream: MediaStream | null;
  sessao: SessaoDaCamera | null;
  leitura: Instantaneo | null;
  carga: Carga | null;
  erro: { nome: string; detalhe: string } | null;
  instalado: boolean;
  resumo: ResumoDaSessao | null;
  foco: boolean;
  aoLigar: () => void;
  aoQuadro: (instantaneo: Instantaneo) => void;
  aoFalhar: (erro: unknown) => void;
}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const [proporcao, setProporcao] = useState(4 / 3);

  // Tela cheia e celular montam outro vídeo: ele recebe a mesma câmera, sem pedir de novo.
  useEffect(() => {
    const elemento = videoRef.current;
    if (!elemento || !stream || elemento.srcObject === stream) return;
    elemento.srcObject = stream;
    void elemento.play().catch(() => {});
  }, [videoRef, stream]);

  useEffect(() => {
    const elemento = videoRef.current;
    if (!elemento) return;
    const medir = () => {
      if (elemento.videoWidth && elemento.videoHeight) setProporcao(elemento.videoWidth / elemento.videoHeight);
    };
    elemento.addEventListener("loadedmetadata", medir);
    elemento.addEventListener("resize", medir);
    return () => {
      elemento.removeEventListener("loadedmetadata", medir);
      elemento.removeEventListener("resize", medir);
    };
  }, [videoRef]);

  useEffect(() => {
    const elemento = videoRef.current;
    const tela = canvas.current;
    if (!sessao || !elemento || !tela) return;
    return sessao.ligar(elemento, tela, aoQuadro, aoFalhar);
  }, [sessao, videoRef, aoQuadro, aoFalhar]);

  const comVideo = fase === "carregando" || fase === "rodando";
  const estagio = fase === "rodando" ? leitura?.sono.estagio ?? "normal" : "normal";
  const nivel = estagio === "normal" ? 0 : estagio === "microssono" ? 1 : 2;
  const semRosto = fase === "rodando" && leitura !== null && !leitura.rosto && leitura.sono.semRostoHa > 0.5;
  const alturaMaxima = foco ? "100dvh - 132px" : "74vh";

  return (
    <div
      className={cn(
        "relative mx-auto overflow-hidden rounded-[12px] bg-video text-sobre-video transition-shadow duration-200",
        nivel === 1 && "ring-[3px] ring-alarme",
        nivel === 2 && "ring-[6px] ring-alarme",
      )}
      style={{ aspectRatio: proporcao, width: `min(100%, calc((${alturaMaxima}) * ${proporcao}))` }}
    >
      <div className="absolute inset-0 -scale-x-100">
        <video ref={videoRef} className={cn("absolute inset-0 size-full object-fill", !comVideo && "invisible")} muted playsInline autoPlay />
        <canvas ref={canvas} className="absolute inset-0 size-full" aria-hidden="true" />
      </div>

      {fase === "aviso" && (
        <Centro>
          <p className="font-titulo text-[clamp(20px,3.2cqi,28px)] font-semibold leading-tight">Veja o que a caixa enxerga</p>
          <p className="mt-2 max-w-[440px] text-[14px] leading-relaxed text-sobre-video/80">
            478 pontos no rosto, abertura dos olhos, boca, posição da cabeça e uma estimativa do pulso, calculados neste aparelho.
          </p>
          <button type="button" onClick={aoLigar} className="mt-5 inline-flex h-11 items-center rounded-[9px] bg-lima px-5 text-[15px] font-semibold text-sobre-lima transition-transform hover:-translate-y-px">
            Ligar a câmera
          </button>
        </Centro>
      )}

      {fase === "pedindo" && (
        <Centro>
          <p className="font-titulo text-[22px] font-semibold">Permita o uso da câmera</p>
          <p className="mt-2 max-w-[400px] text-[14px] text-sobre-video/80">
            {instalado ? "O RotaGuard Painel vai perguntar se pode usar a câmera deste computador." : "O navegador vai perguntar se este endereço pode usar a câmera."}
          </p>
        </Centro>
      )}

      {fase === "carregando" && (
        <div className="absolute inset-x-0 bottom-0 bg-video/85 px-5 py-4">
          <div className="flex items-baseline justify-between gap-4 text-[13.5px]">
            <span className="font-semibold">{carga?.etapa === "preparando" ? "Preparando a detecção do rosto" : "Carregando o modelo do rosto"}</span>
            {carga?.etapa === "baixando" && (
              <span className="tabular-nums text-sobre-video/75">
                {megas(carga.baixado)} de {megas(carga.total)} MB
              </span>
            )}
          </div>
          <div
            role="progressbar"
            aria-label="Carregando o modelo do rosto"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={carga ? Math.round((carga.baixado / carga.total) * 100) : 0}
            className="mt-2 h-1.5 overflow-hidden rounded-[3px] bg-sobre-video/20"
          >
            <div className="h-full rounded-[3px] bg-lima text-sobre-lima transition-[width] duration-200" style={{ width: `${carga ? Math.min(100, (carga.baixado / carga.total) * 100) : 4}%` }} />
          </div>
          <p className="mt-2 text-[12.5px] text-sobre-video/70">Só na primeira vez demora: depois o navegador guarda os arquivos.</p>
        </div>
      )}

      {fase === "rodando" && leitura?.aprendendo && leitura.rosto && (
        <p className="absolute left-3 top-3 rounded-[8px] bg-video/80 px-3 py-1.5 text-[13px]">Aprendendo como é o seu olho aberto</p>
      )}

      {semRosto && (
        <Centro fundo>
          <p className="font-titulo text-[20px] font-semibold">Procurando o rosto</p>
          <p className="mt-1.5 max-w-[360px] text-[14px] text-sobre-video/80">Fique de frente para a câmera, com o rosto inteiro na imagem e luz de frente.</p>
        </Centro>
      )}

      {fase === "rodando" && nivel > 0 && leitura && (
        <div role="alert" className="absolute inset-x-3 bottom-3 flex items-center justify-between gap-4 rounded-[10px] bg-papel px-4 py-3 text-alarme">
          <span className="font-titulo text-[clamp(17px,2.6cqi,24px)] font-semibold tabular-nums">Olhos fechados há {formatarSegundos(leitura.sono.fechadoHa)}</span>
          <span className="text-[14px] font-semibold">{estagio === "microssono" ? "Microssono" : estagio === "sono" ? "Sono" : "Sem resposta"}</span>
        </div>
      )}

      {fase === "rodando" && nivel === 0 && !semRosto && <Legenda />}

      {fase === "erro" && erro && <PainelDeErro erro={erro} instalado={instalado} aoLigar={aoLigar} />}

      {fase === "parado" && (
        <Centro>
          <p className="font-titulo text-[22px] font-semibold">Câmera desligada</p>
          {resumo && (
            <p className="mt-2 max-w-[440px] text-[14px] tabular-nums text-sobre-video/80">
              A sessão durou {formatarRelogio(resumo.duracao)}: {resumo.piscadas} {resumo.piscadas === 1 ? "piscada" : "piscadas"}, {resumo.bocejos}{" "}
              {resumo.bocejos === 1 ? "bocejo" : "bocejos"}, {resumo.cabeceios} {resumo.cabeceios === 1 ? "cabeceio" : "cabeceios"} e{" "}
              {resumo.eventos === 1 ? "1 evento" : `${resumo.eventos} eventos`} na linha do tempo.
            </p>
          )}
          <button type="button" onClick={aoLigar} className="mt-5 inline-flex h-11 items-center rounded-[9px] bg-lima px-5 text-[15px] font-semibold text-sobre-lima transition-transform hover:-translate-y-px">
            Ligar de novo
          </button>
        </Centro>
      )}

      {!comVideo && (
        <p className="absolute left-4 top-3.5 flex items-center gap-2 text-[12.5px] text-sobre-video/70">
          <span aria-hidden="true" className="size-2 rounded-full bg-sobre-video/40" />
          Câmera desligada
        </p>
      )}
    </div>
  );
}

function Centro({ children, fundo }: { children: React.ReactNode; fundo?: boolean }) {
  return <div className={cn("absolute inset-0 grid place-content-center justify-items-center px-6 text-center", fundo && "bg-video/70")}>{children}</div>;
}

// Legenda das cores da malha, para quem está assistindo saber o que é cada coisa.
function Legenda() {
  return (
    <ul className="absolute bottom-3 left-3 hidden flex-wrap gap-x-4 gap-y-1 rounded-[8px] bg-video/75 px-3 py-1.5 text-[12px] text-sobre-video/85 @min-[560px]:flex">
      <li className="flex items-center gap-1.5">
        <span aria-hidden="true" className="h-2.5 w-1.5 border-y border-l border-lima" />
        Olhos, marcados por fora
      </li>
      <li className="flex items-center gap-1.5">
        <span aria-hidden="true" className="size-2 rounded-full bg-sobre-video" />
        Boca e pontos do rosto
      </li>
      <li className="flex items-center gap-1.5">
        <span aria-hidden="true" className="size-2.5 border-l border-t border-lima" />
        Cantos das áreas do pulso
      </li>
    </ul>
  );
}

function PainelDeErro({ erro, instalado, aoLigar }: { erro: { nome: string; detalhe: string }; instalado: boolean; aoLigar: () => void }) {
  const mensagem = erroDaCamera(erro.nome, { instalado });
  return (
    <div role="alert" className="absolute inset-0 overflow-y-auto px-6 py-8">
      <div className="mx-auto grid min-h-full max-w-[460px] content-center">
        <p className="font-titulo text-[22px] font-semibold">{mensagem.titulo}</p>
        <p className="mt-2 text-[14px] leading-relaxed text-sobre-video/85">{mensagem.texto}</p>
        {mensagem.comoLiberar.length > 0 && (
          <ol className="mt-3 grid list-decimal gap-1.5 pl-5 text-[14px] leading-relaxed text-sobre-video/85">
            {mensagem.comoLiberar.map((passo) => (
              <li key={passo}>{passo}</li>
            ))}
          </ol>
        )}
        {mensagem.tentarDeNovo && (
          <button type="button" onClick={aoLigar} className="mt-5 inline-flex h-11 w-fit items-center rounded-[9px] bg-lima px-5 text-[15px] font-semibold text-sobre-lima transition-transform hover:-translate-y-px">
            Tentar de novo
          </button>
        )}
        <p className="mt-4 break-words text-[12px] text-sobre-video/55">Detalhe técnico: {erro.detalhe}</p>
      </div>
    </div>
  );
}
