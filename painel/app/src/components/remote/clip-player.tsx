"use client";

import { useEffect, useRef, useState } from "react";
import { EVENTO_BLOQUEIO } from "@/components/auth-gate";
import { Glyph } from "@/components/ui/glyph";
import type { TrechoParaTocar } from "@/lib/bridge";
import { quadroNoTempo } from "./remote-data";

const minutoSegundo = (segundos: number) => `${Math.floor(segundos / 60)}:${String(Math.floor(segundos % 60)).padStart(2, "0")}`;

// Player do trecho (spec 026, decisão 5): MP4/WebM num <video>; .rgclip (quadros JPEG) desenhado num canvas.
// O vídeo já vem com a malha e a marca d'água de hora e tipo, gravadas no computador de quem testou.
export function ClipPlayer({ trecho }: { trecho: TrechoParaTocar }) {
  if (!trecho.disponivel) {
    return <p className="rounded-[10px] border border-dashed border-fio px-4 py-6 text-[13.5px] text-grafite">{trecho.motivo ?? "Trecho ainda não disponível."}</p>;
  }
  if (trecho.url) {
    return (
      <video key={trecho.url} src={trecho.url} controls preload="metadata" className="aspect-video w-full rounded-[10px] bg-video">
        Este computador não conseguiu tocar o vídeo.
      </video>
    );
  }
  return <QuadrosPlayer key={trecho.uid} quadros={trecho.quadros ?? []} fps={trecho.fps ?? 15} largura={trecho.largura ?? 640} altura={trecho.altura ?? 360} />;
}

function QuadrosPlayer({ quadros, fps, largura, altura }: { quadros: { t: number; url: string }[]; fps: number; largura: number; altura: number }) {
  const tela = useRef<HTMLCanvasElement>(null);
  const imagens = useRef<HTMLImageElement[]>([]);
  const [tempo, setTempo] = useState(0);
  const tempoAtual = useRef(0);
  const [tocando, setTocando] = useState(false);
  const [carregados, setCarregados] = useState(0);
  const duracao = quadros.length ? quadros[quadros.length - 1].t + 1 / fps : 0;

  // Carrega os quadros uma vez; o primeiro aparece assim que chega.
  useEffect(() => {
    let vivo = true;
    imagens.current = quadros.map((quadro) => {
      const imagem = new Image();
      imagem.decoding = "async";
      imagem.onload = () => {
        if (vivo) setCarregados((total) => total + 1);
      };
      imagem.src = quadro.url;
      return imagem;
    });
    return () => {
      vivo = false;
    };
  }, [quadros]);

  // Desenha o quadro do instante atual.
  useEffect(() => {
    const contexto = tela.current?.getContext("2d");
    const imagem = imagens.current[quadroNoTempo(quadros, tempo)];
    if (contexto && imagem?.complete && imagem.naturalWidth) contexto.drawImage(imagem, 0, 0, largura, altura);
  }, [tempo, carregados, quadros, largura, altura]);

  function irPara(segundos: number) {
    tempoAtual.current = segundos;
    setTempo(segundos);
  }

  // Relógio do player: avança pelo tempo real decorrido; para no fim.
  useEffect(() => {
    if (!tocando) return;
    let quadroAnimacao = 0;
    let anterior = performance.now();
    const passo = (agora: number) => {
      const proximo = Math.min(duracao, tempoAtual.current + (agora - anterior) / 1000);
      anterior = agora;
      tempoAtual.current = proximo;
      setTempo(proximo);
      if (proximo >= duracao) {
        setTocando(false);
        return;
      }
      quadroAnimacao = requestAnimationFrame(passo);
    };
    quadroAnimacao = requestAnimationFrame(passo);
    return () => cancelAnimationFrame(quadroAnimacao);
  }, [tocando, duracao]);

  // Tela bloqueada (spec 014): o trecho para, como os vídeos.
  useEffect(() => {
    const parar = () => setTocando(false);
    window.addEventListener(EVENTO_BLOQUEIO, parar);
    return () => window.removeEventListener(EVENTO_BLOQUEIO, parar);
  }, []);

  function alternar() {
    if (!tocando && tempo >= duracao) irPara(0);
    setTocando((atual) => !atual);
  }

  return (
    <div>
      <canvas
        ref={tela}
        width={largura}
        height={altura}
        role="img"
        aria-label={`Trecho em quadros, ${quadros.length} imagens`}
        onClick={alternar}
        className="block aspect-video w-full cursor-pointer rounded-[10px] bg-video"
      />
      <div className="mt-2.5 flex items-center gap-3">
        <button type="button" className="btn btn-small min-w-[92px] justify-center" onClick={alternar} aria-pressed={tocando}>
          <Glyph name="play" size={14} />
          {tocando ? "Pausar" : tempo > 0 && tempo < duracao ? "Continuar" : "Tocar"}
        </button>
        <input
          type="range"
          min={0}
          max={duracao}
          step={1 / fps}
          value={Math.min(tempo, duracao)}
          onChange={(evento) => irPara(Number(evento.target.value))}
          aria-label="Posição no trecho"
          className="h-1.5 min-w-0 flex-1 accent-[var(--color-verde)]"
        />
        <span className="shrink-0 text-[13px] tabular-nums text-grafite">
          {minutoSegundo(tempo)} / {minutoSegundo(duracao)}
        </span>
      </div>
      {carregados < quadros.length && (
        <p className="mt-1.5 text-[12.5px] text-grafite">
          Carregando quadros: {carregados} de {quadros.length}
        </p>
      )}
    </div>
  );
}
