"use client";

import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";
import { coresDoTema } from "./camera-cores";
import type { Instantaneo, SessaoDaCamera } from "./camera-motor";
import { desenharOnda } from "./camera-onda";
import {
  MODOS_DA_MALHA,
  descreverInclinacao,
  eventoGrave,
  formatarDuracao,
  formatarPorcentagem,
  formatarRelogio,
  formatarSegundos,
  rotuloDoEvento,
  situacaoDoPulso,
  type ModoDaMalha,
} from "./camera-regras";
import { ALERT_PERCLOS, MIN_FPS_FOR_DURATION, P80_OPENNESS, type EventoDaSessao } from "./camera-sono";

const CARTAO = "rounded-[12px] border border-fio bg-superficie";

/** Antes de ligar: o que o teste faz, o que acontece com a imagem e como ter uma boa leitura. */
export function AntesDeLigar() {
  return (
    <div className={cn(CARTAO, "p-5")}>
      <h3 className="font-titulo text-[16px] font-semibold">O que acontece com a imagem</h3>
      <p className="mt-2 text-[14px] leading-relaxed">
        Tudo é calculado neste aparelho. Nenhuma imagem, ponto ou número é gravado ou enviado. Ao parar ou sair da tela, a câmera desliga.
      </p>
      <p className="mt-2 text-[13.5px] leading-relaxed text-grafite">
        Rosto e frequência cardíaca são dados pessoais sensíveis. Use o teste só com quem concordou em aparecer.
      </p>
      <h3 className="mt-5 font-titulo text-[16px] font-semibold">Para uma boa leitura</h3>
      <ul className="mt-2 grid gap-1.5 text-[13.5px] leading-relaxed text-grafite">
        <li>Rosto de frente e inteiro na imagem.</li>
        <li>Luz de frente, sem janela clara atrás.</li>
        <li>Para o pulso, fique parado por uns 10 segundos.</li>
      </ul>
      <p className="mt-5 border-t border-fio pt-4 text-[13px] leading-relaxed text-grafite">
        É um teste no navegador, com as mesmas regras da caixa. O pulso é uma estimativa pela câmera, não é medida médica. A caixa RotaGuard continua
        sendo a referência.
      </p>
    </div>
  );
}

/** Barra fixa no alto enquanto a câmera está ligada: o botão de parar nunca sai da tela (CAM-09). */
export function BarraDaCamera({
  rodando,
  tempo,
  foco,
  estreito,
  aoParar,
  aoTelaCheia,
}: {
  rodando: boolean;
  tempo: number | null;
  foco: boolean;
  estreito: boolean;
  aoParar: () => void;
  aoTelaCheia: () => void;
}) {
  return (
    <div className={cn("sticky top-0 z-20 flex flex-wrap items-center justify-between gap-x-4 gap-y-2 border-b border-fio bg-papel py-3", foco && "px-1")}>
      <p role="status" className="flex min-w-0 items-center gap-2.5 text-[14px]">
        <span aria-hidden="true" className="pulse-dot" />
        <span className="font-semibold">Câmera ligada</span>
        <span className="truncate text-grafite">
          {tempo !== null ? `${formatarRelogio(tempo)} · ` : ""}nada sai deste aparelho
        </span>
      </p>
      <div className="flex items-center gap-2">
        {rodando && !estreito && (
          <button type="button" className="btn btn-small btn-quiet" onClick={aoTelaCheia}>
            {foco ? "Sair da tela cheia" : "Tela cheia"}
          </button>
        )}
        <button type="button" className="btn btn-small btn-primary" onClick={aoParar}>
          <span aria-hidden="true" className="size-2.5 rounded-[2px] bg-sobre-verde" />
          Parar câmera
        </button>
      </div>
    </div>
  );
}

function Rotulo({ children, extra }: { children: React.ReactNode; extra?: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <h3 className="text-[13px] font-semibold text-grafite">{children}</h3>
      {extra}
    </div>
  );
}

export function CartaoOlhos({ leitura }: { leitura: Instantaneo | null }) {
  const abertura = leitura?.rosto ? leitura.abertura : null;
  const fechados = leitura ? leitura.sono.estagio !== "normal" || (abertura !== null && abertura <= P80_OPENNESS) : false;
  const situacao = !leitura?.rosto ? "Sem rosto" : abertura === null ? "Aprendendo" : fechados ? "Fechados" : "Abertos";
  const largura = abertura === null ? 0 : Math.min(100, abertura * 100);
  return (
    <section className={cn(CARTAO, "p-5")} aria-label="Olhos">
      <Rotulo extra={<span className={cn("text-[13px] font-semibold", fechados ? "text-alarme" : "text-tinta")}>{situacao}</span>}>Abertura dos olhos</Rotulo>
      <p className={cn("mt-1 font-titulo text-[40px] font-semibold leading-none tabular-nums", fechados && "text-alarme")}>
        {abertura === null ? "–" : formatarPorcentagem(Math.min(abertura, 1))}
      </p>
      <div
        role="progressbar"
        aria-label="Abertura dos olhos"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(largura)}
        className="relative mt-4 h-2 rounded-[3px] bg-trilho"
      >
        <div className={cn("h-full rounded-[3px] transition-[width] duration-150", fechados ? "bg-alarme" : "bg-verde")} style={{ width: `${largura}%` }} />
        <span aria-hidden="true" className="absolute -top-1 h-4 w-px bg-grafite" style={{ left: `${P80_OPENNESS * 100}%` }} />
      </div>
      <p className="mt-2 text-[12.5px] text-grafite">Abaixo de 20% do seu olho aberto conta como fechado.</p>
    </section>
  );
}

export function CartaoPulso({ leitura, sessao }: { leitura: Instantaneo | null; sessao: SessaoDaCamera | null }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const cardio = leitura?.cardio ?? null;

  // A onda é refeita 10 vezes por segundo pelo monitor (como na caixa); aqui só é desenhada.
  useEffect(() => {
    const tela = canvas.current;
    if (!tela) return;
    let id = 0;
    let cores = coresDoTema();
    let proximasCores = 0;
    let desenhada: readonly number[] | null | undefined;
    let largura = 0;
    const desenhar = (agora: number) => {
      const onda = sessao?.ondaAtual() ?? null;
      // A onda muda 10 vezes por segundo: só redesenha quando ela, o tema ou o tamanho mudam.
      if (agora >= proximasCores || onda?.trecho !== desenhada || tela.clientWidth !== largura) {
        if (agora >= proximasCores) {
          cores = coresDoTema();
          proximasCores = agora + 1000;
        }
        desenhada = onda?.trecho;
        largura = tela.clientWidth;
        desenharOnda(tela, onda?.trecho ?? null, onda?.confiavel ?? false, cores);
      }
      id = requestAnimationFrame(desenhar);
    };
    id = requestAnimationFrame(desenhar);
    return () => cancelAnimationFrame(id);
  }, [sessao]);

  // Spec 029: com o sinal ruim o cartão nunca para; o último valor fica esmaecido e o andamento continua visível.
  const situacao = situacaoDoPulso(cardio);
  const { numero, esmaecido, andamento } = situacao;
  return (
    <section className={cn(CARTAO, "p-5")} aria-label="Pulso estimado">
      <Rotulo extra={<span className={cn("text-[13px] font-semibold", situacao.alarme ? "text-alarme" : "text-tinta")}>{situacao.rotulo}</span>}>
        Pulso estimado
      </Rotulo>
      <p className="mt-1 flex items-baseline gap-2">
        <span className={cn("font-titulo text-[40px] font-semibold leading-none tabular-nums transition-opacity duration-200", esmaecido && "text-apagado opacity-60")}>
          {numero === null ? "–" : numero}
        </span>
        <span className="text-[14px] font-semibold text-grafite">bpm</span>
        {esmaecido && <span className="text-[12.5px] text-grafite">última leitura</span>}
      </p>
      <canvas ref={canvas} className="mt-3 block h-14 w-full" aria-hidden="true" />
      {andamento && (
        <div className="mt-2" role="status">
          <p className="flex items-center gap-2 text-[12.5px] font-semibold tabular-nums text-tinta">
            {andamento.progresso === null && <span aria-hidden="true" className="pulse-dot" />}
            {andamento.texto}
          </p>
          {andamento.progresso !== null && (
            <div
              role="progressbar"
              aria-label="Medindo o pulso"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={Math.round(andamento.progresso * 100)}
              className="mt-1.5 h-1.5 overflow-hidden rounded-[3px] bg-trilho"
            >
              <div className="h-full rounded-[3px] bg-verde transition-[width] duration-200" style={{ width: `${andamento.progresso * 100}%` }} />
            </div>
          )}
        </div>
      )}
      <p className="mt-2 text-[12.5px] text-grafite">{situacao.aviso}</p>
      <p className="mt-3 border-t border-fio pt-3 text-[12.5px] font-semibold">Estimativa pela câmera, não é medida médica.</p>
    </section>
  );
}

export function Controles({
  modo,
  som,
  leitura,
  aoModo,
  aoSom,
}: {
  modo: ModoDaMalha;
  som: boolean;
  leitura: Instantaneo | null;
  aoModo: (modo: ModoDaMalha) => void;
  aoSom: () => void;
}) {
  const lento = leitura !== null && leitura.t > 3 && leitura.quadrosPorSegundo < MIN_FPS_FOR_DURATION;
  return (
    <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-3">
      <div className="flex items-center gap-2.5">
        <span id="rotulo-malha" className="text-[13px] font-semibold text-grafite">
          Malha
        </span>
        <div role="group" aria-labelledby="rotulo-malha" className="inline-flex h-9 items-center gap-0.5 rounded-[9px] border border-fio bg-superficie p-0.5">
          {MODOS_DA_MALHA.map((opcao) => (
            <button
              key={opcao.id}
              type="button"
              aria-pressed={modo === opcao.id}
              onClick={() => aoModo(opcao.id)}
              className={cn("h-full rounded-[7px] px-2.5 text-[13px] font-semibold transition-colors", modo === opcao.id ? "bg-selecao text-tinta" : "text-grafite hover:text-tinta")}
            >
              {opcao.rotulo}
            </button>
          ))}
        </div>
      </div>
      <button type="button" aria-pressed={som} onClick={aoSom} className="inline-flex h-9 items-center gap-2 text-[13px] font-semibold text-grafite hover:text-tinta">
        <span aria-hidden="true" className={cn("relative h-5 w-9 rounded-[10px] border transition-colors", som ? "border-verde-cheio bg-verde-cheio" : "border-fio-campo bg-desligado")}>
          <span className={cn("absolute top-[2px] size-3.5 rounded-[7px] bg-superficie transition-transform", som ? "translate-x-[17px]" : "translate-x-[2px]")} />
        </span>
        Som do alerta
      </button>
      {leitura && (
        <p className="text-[12.5px] tabular-nums text-grafite @min-[700px]:ml-auto @min-[700px]:text-right">
          <span className={cn(lento && "font-semibold text-tinta")}>{Math.round(leitura.quadrosPorSegundo)} quadros/s</span> · {Math.round(leitura.msPorQuadro)} ms por
          quadro · {leitura.processador}
          {lento && <span className="block">Abaixo de 24 quadros por segundo, a duração das piscadas fica imprecisa.</span>}
        </p>
      )}
    </div>
  );
}

function Medida({ rotulo, valor, detalhe, alerta, compacta }: { rotulo: string; valor: React.ReactNode; detalhe: React.ReactNode; alerta?: boolean; compacta?: boolean }) {
  return (
    <div className={cn(CARTAO, "min-w-0", compacta ? "px-3.5 py-2.5" : "px-4 py-3.5")}>
      <p className={cn("font-semibold text-grafite", compacta ? "truncate text-[12px]" : "text-[12.5px]")}>{rotulo}</p>
      <p className={cn("mt-1 font-titulo font-semibold leading-tight tabular-nums", compacta ? "text-[19px]" : "text-[24px]", alerta && "text-alarme")}>{valor}</p>
      {!compacta && <p className="mt-0.5 text-[12px] leading-snug text-grafite">{detalhe}</p>}
    </div>
  );
}

/** `aoLado`: na tela cheia os números vão para a coluna da direita, em duas colunas, e tudo cabe numa tela só. */
/** Com a câmera parada, o que é do instante (olho fechado agora, inclinação agora) some; contagens e taxas ficam. */
export function Medidas({ leitura, aoLado = false, aoVivo = true }: { leitura: Instantaneo | null; aoLado?: boolean; aoVivo?: boolean }) {
  const sono = leitura?.sono;
  const fechadoHa = aoVivo ? (sono?.fechadoHa ?? 0) : 0;
  const perclos = sono?.perclos60s ?? null;
  const pose = aoVivo && leitura?.rosto ? leitura.pose : null;
  return (
    <section aria-label="Sinais desta sessão" className={cn("grid grid-cols-2 gap-3", !aoLado && "mt-6 @min-[620px]:grid-cols-3 @min-[1080px]:grid-cols-6")}>
      <Medida compacta={aoLado} rotulo="Olhos fechados há" valor={fechadoHa > 0 ? formatarSegundos(fechadoHa) : "–"} detalhe="Alerta em 1 s e em 3 s" alerta={fechadoHa >= 1} />
      <Medida
        compacta={aoLado}
        rotulo={aoLado ? "PERCLOS 60 s" : "Olhos fechados no último minuto"}
        valor={perclos === null ? "–" : formatarPorcentagem(perclos)}
        detalhe={perclos === null ? "Juntando 30 s de dados" : "PERCLOS, alerta a partir de 12%"}
        alerta={perclos !== null && perclos >= ALERT_PERCLOS}
      />
      <Medida
        compacta={aoLado}
        rotulo="Piscadas por minuto"
        valor={sono?.piscadasPorMinuto ?? "–"}
        detalhe={sono ? `${sono.piscadas} ${sono.piscadas === 1 ? "piscada" : "piscadas"} nesta sessão` : "Contando"}
      />
      <Medida compacta={aoLado} rotulo="Bocejos" valor={sono?.bocejos ?? 0} detalhe="Boca bem aberta por 2 s ou mais" />
      <Medida
        compacta={aoLado}
        rotulo="Inclinação da cabeça"
        valor={pose ? descreverInclinacao(pose.pitch) : "–"}
        detalhe={pose ? `Virada ${Math.round(Math.abs(pose.yaw))}° · de lado ${Math.round(Math.abs(pose.roll))}°` : "Em relação à câmera"}
      />
      <Medida compacta={aoLado} rotulo="Cabeceios" valor={sono?.cabeceios ?? 0} detalhe="A cabeça cai rápido e volta" />
    </section>
  );
}

export function LinhaDoTempo({ eventos, duracao }: { eventos: EventoDaSessao[]; duracao: number }) {
  const ordenados = [...eventos].reverse();
  const total = Math.max(duracao, 1);
  return (
    <section aria-labelledby="linha-do-tempo" className="mt-8">
      <div className="flex items-baseline justify-between gap-4">
        <h2 id="linha-do-tempo" className="font-titulo text-[18px] font-semibold">
          Linha do tempo desta sessão
        </h2>
        <span className="text-[13px] tabular-nums text-grafite">{eventos.length === 1 ? "1 evento" : `${eventos.length} eventos`}</span>
      </div>
      <div aria-hidden="true" className="relative mt-3 h-2 rounded-[3px] bg-trilho">
        {eventos.map((evento) => (
          <span
            key={evento.id}
            className={cn("absolute top-0 h-full min-w-[3px] rounded-[2px]", eventoGrave(evento.tipo) || evento.tipo === "microssono" ? "bg-alarme" : "bg-verde")}
            style={{
              left: `${Math.min(99.5, (evento.inicio / total) * 100)}%`,
              width: `${Math.min(100 - (evento.inicio / total) * 100, ((evento.duracao ?? duracao - evento.inicio) / total) * 100)}%`,
            }}
          />
        ))}
      </div>
      <div className="mt-1 flex justify-between text-[12px] tabular-nums text-grafite">
        <span>0:00</span>
        <span>{formatarRelogio(duracao)}</span>
      </div>
      {ordenados.length === 0 ? (
        <p className="mt-3 text-[14px] text-grafite">
          Nada até agora. Feche os olhos por 1 segundo, boceje ou deixe a cabeça cair e voltar para ver aparecer aqui.
        </p>
      ) : (
        <div role="table" aria-label="Eventos desta sessão" className="mt-3 max-h-[46vh] overflow-y-auto border-b border-fio">
          <div
            role="row"
            className="sticky top-0 grid h-9 grid-cols-[64px_minmax(0,1fr)_96px] items-center gap-4 border-b border-fio bg-papel text-[12.5px] font-semibold text-grafite"
          >
            <span role="columnheader">Quando</span>
            <span role="columnheader">O que aconteceu</span>
            <span role="columnheader" className="text-right">
              Duração
            </span>
          </div>
          {ordenados.map((evento) => (
            <div role="row" key={evento.id} className="anim-row grid min-h-12 grid-cols-[64px_minmax(0,1fr)_96px] items-center gap-4 border-b border-fio py-2 text-[14px] last:border-b-0">
              <span role="cell" className="tabular-nums text-grafite">
                {formatarRelogio(evento.inicio)}
              </span>
              <span role="cell" className={cn(eventoGrave(evento.tipo) && "font-semibold text-alarme")}>
                {rotuloDoEvento(evento.tipo)}
              </span>
              <span role="cell" className={cn("text-right tabular-nums", evento.duracao === null ? "font-semibold" : "text-grafite")}>
                {formatarDuracao(evento.duracao)}
              </span>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
