"use client";

import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";
import { Camada } from "@/components/ui/layer";
import { cn } from "@/lib/utils";
import { AlertaSonoro } from "./camera-alerta";
import { AntesDeLigar, BarraDaCamera, CartaoOlhos, CartaoPulso, Controles, LinhaDoTempo, Medidas } from "./camera-medidas";
import type { Carga, Instantaneo, SessaoDaCamera } from "./camera-motor";
import { Palco, type Fase, type ResumoDaSessao } from "./camera-palco";
import type { ModoDaMalha } from "./camera-regras";
import type { EventoDaSessao, Estagio } from "./camera-sono";
import { abrirCamera, pararCamera } from "./camera-trilhas";

// Spec 025 · teste com a câmera deste aparelho, dentro da tela Ao vivo. O MediaPipe (bundle, WASM e modelo) só baixa
// quando a pessoa liga a câmera. No celular (ou em tela cheia) a experiência ocupa a janela inteira, numa camada fora
// da animação da tela; a sessão continua a mesma quando o vídeo troca de lugar.

const ESTREITO = "(max-width: 760px)";
const ATUALIZA_TELA_MS = 200;

function useEstreito(): boolean {
  return useSyncExternalStore(
    (avisar) => {
      const consulta = window.matchMedia(ESTREITO);
      consulta.addEventListener("change", avisar);
      return () => consulta.removeEventListener("change", avisar);
    },
    () => window.matchMedia(ESTREITO).matches,
    () => false,
  );
}

type Tentativa = { controle: AbortController; stream: MediaStream | null };

const naJanelaDoApp = () => typeof window !== "undefined" && "pywebview" in window;

export function CameraDoAparelho() {
  const estreito = useEstreito();
  const [fase, setFase] = useState<Fase>("aviso");
  const [carga, setCarga] = useState<Carga | null>(null);
  const [erro, setErro] = useState<{ nome: string; detalhe: string; instalado: boolean } | null>(null);
  const [leitura, setLeitura] = useState<Instantaneo | null>(null);
  const [eventos, setEventos] = useState<EventoDaSessao[]>([]);
  const [escolhaDeModo, setEscolhaDeModo] = useState<ModoDaMalha | null>(null);
  const [som, setSom] = useState(false);
  const [telaCheia, setTelaCheia] = useState(false);
  const [sessao, setSessao] = useState<SessaoDaCamera | null>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [resumo, setResumo] = useState<ResumoDaSessao | null>(null);
  const video = useRef<HTMLVideoElement | null>(null);
  const tentativa = useRef<Tentativa | null>(null);
  const sessaoAtual = useRef<SessaoDaCamera | null>(null);
  const alerta = useRef<AlertaSonoro | null>(null);
  const ultimaTela = useRef(0);
  const ultimoEstagio = useRef<Estagio>("normal");
  const versaoVista = useRef(-1);
  const ultimaLeitura = useRef<Instantaneo | null>(null);

  // Spec 029: a malha abre na Discreta (no computador e no celular) até a pessoa escolher outra.
  const modo = escolhaDeModo ?? "discreta";
  useEffect(() => {
    sessao?.definirModo(modo);
  }, [sessao, modo]);

  const aoQuadro = useCallback((instantaneo: Instantaneo) => {
    const agora = performance.now();
    alerta.current?.atualizar(instantaneo.sono.estagio, agora);
    ultimaLeitura.current = instantaneo;
    const mudouEstagio = instantaneo.sono.estagio !== ultimoEstagio.current;
    if (!mudouEstagio && agora - ultimaTela.current < ATUALIZA_TELA_MS) return; // a tela muda 5 vezes por segundo; o canvas, a cada quadro
    ultimaTela.current = agora;
    ultimoEstagio.current = instantaneo.sono.estagio;
    setLeitura(instantaneo);
    const atual = sessaoAtual.current;
    if (atual && atual.versaoDosEventos !== versaoVista.current) {
      versaoVista.current = atual.versaoDosEventos;
      setEventos(atual.eventos.map((evento) => ({ ...evento })));
    }
  }, []);

  const encerrar = useCallback((mostrarResumo: boolean) => {
    tentativa.current?.controle.abort();
    const atual = sessaoAtual.current;
    if (atual) atual.encerrar(video.current);
    else pararCamera(tentativa.current?.stream ?? null, video.current);
    tentativa.current = null;
    sessaoAtual.current = null;
    alerta.current?.atualizar("normal", 0);
    if (!mostrarResumo) return;
    const final = ultimaLeitura.current;
    setResumo(
      final && atual
        ? { duracao: final.t, eventos: atual.eventos.length, piscadas: final.sono.piscadas, bocejos: final.sono.bocejos, cabeceios: final.sono.cabeceios }
        : null,
    );
    if (atual) setEventos(atual.eventos.map((evento) => ({ ...evento })));
    setSessao(null);
    setStream(null);
    setTelaCheia(false);
    setFase("parado");
  }, []);

  const aoFalhar = useCallback(
    (falha: unknown) => {
      encerrar(false);
      setSessao(null);
      setStream(null);
      setTelaCheia(false);
      setErro({ nome: "modelo", detalhe: falha instanceof Error ? `${falha.name}: ${falha.message}` : String(falha), instalado: naJanelaDoApp() });
      setFase("erro");
    },
    [encerrar],
  );

  async function ligar() {
    if (tentativa.current || sessaoAtual.current) return;
    const atual: Tentativa = { controle: new AbortController(), stream: null };
    tentativa.current = atual;
    ultimaLeitura.current = null;
    versaoVista.current = -1;
    setErro(null);
    setResumo(null);
    setLeitura(null);
    setEventos([]);
    setCarga(null);
    setFase("pedindo");
    // Modelo e câmera ao mesmo tempo: enquanto a pessoa responde à permissão, o modelo já vai baixando.
    const motorPronto = import("./camera-motor").then(async (modulo) => ({
      modulo,
      motor: await modulo.prepararMotor((novaCarga) => {
        if (tentativa.current === atual) setCarga(novaCarga);
      }, atual.controle.signal),
    }));
    motorPronto.catch(() => {}); // tratado abaixo; evita aviso de promessa sem tratamento se a câmera falhar antes
    try {
      const elemento = video.current;
      if (!elemento) throw new Error("vídeo da tela não encontrado");
      const aberto = await abrirCamera(elemento);
      atual.stream = aberto;
      if (tentativa.current !== atual) return pararCamera(aberto, null);
      setStream(aberto);
      setFase("carregando");
      const { modulo, motor } = await motorPronto;
      if (tentativa.current !== atual) {
        motor.fechar();
        return pararCamera(aberto, null);
      }
      const nova = new modulo.SessaoDaCamera(motor, aberto);
      nova.definirModo(modo);
      // Se a câmera cair (cabo, outro programa, iPhone interrompendo), a tela volta ao estado de parada.
      aberto.getVideoTracks().forEach((trilha) => trilha.addEventListener("ended", () => sessaoAtual.current === nova && encerrar(true)));
      tentativa.current = null;
      sessaoAtual.current = nova;
      setSessao(nova);
      setFase("rodando");
    } catch (falha) {
      if (tentativa.current !== atual) return; // a pessoa parou no meio
      atual.controle.abort();
      pararCamera(atual.stream, video.current);
      void motorPronto.then(({ motor }) => motor.fechar(), () => {});
      tentativa.current = null;
      setStream(null);
      setErro({
        nome: falha instanceof Error ? falha.name : "erro",
        detalhe: falha instanceof Error ? `${falha.name}: ${falha.message}` : String(falha),
        instalado: naJanelaDoApp(),
      });
      setFase("erro");
    }
  }

  // Sair da tela, trocar de aba ou esconder a janela (celular indo para outro app) desliga a câmera.
  useEffect(() => {
    const aoEsconder = () => {
      if (document.hidden && (tentativa.current || sessaoAtual.current)) encerrar(true);
    };
    document.addEventListener("visibilitychange", aoEsconder);
    return () => {
      document.removeEventListener("visibilitychange", aoEsconder);
      encerrar(false);
      alerta.current?.fechar();
    };
  }, [encerrar]);

  // Esc sai da tela cheia.
  useEffect(() => {
    if (!telaCheia) return;
    const aoTeclar = (evento: KeyboardEvent) => {
      if (evento.key === "Escape") setTelaCheia(false);
    };
    window.addEventListener("keydown", aoTeclar);
    return () => window.removeEventListener("keydown", aoTeclar);
  }, [telaCheia]);

  async function alternarSom() {
    if (som) {
      alerta.current?.desligar();
      setSom(false);
      return;
    }
    alerta.current ??= new AlertaSonoro();
    try {
      await alerta.current.ligar();
      setSom(true);
    } catch {
      setSom(false);
    }
  }

  const ligada = fase === "pedindo" || fase === "carregando" || fase === "rodando";
  const comDados = fase === "rodando" || (fase === "parado" && resumo !== null);
  const aoVivo = fase === "rodando";
  const foco = estreito || (telaCheia && fase === "rodando");
  const numerosAoLado = foco && !estreito && aoVivo;

  const experiencia = (
    <div className={cn("@container", foco ? "mx-auto min-h-full max-w-[1500px] px-4 pb-10 sm:px-8" : "mt-6")}>
      {ligada && (
        <BarraDaCamera
          rodando={fase === "rodando"}
          tempo={fase === "rodando" ? leitura?.t ?? 0 : null}
          foco={foco}
          estreito={estreito}
          aoParar={() => encerrar(true)}
          aoTelaCheia={() => setTelaCheia((atual) => !atual)}
        />
      )}
      {foco && !ligada && (
        <div className="flex items-center justify-between gap-4 border-b border-fio py-3">
          <p className="font-titulo text-[17px] font-semibold">Teste com a câmera</p>
          <p className="text-[12.5px] text-grafite">Calculado neste aparelho</p>
        </div>
      )}
      <div className={cn("grid gap-5", ligada || foco ? "mt-4" : "", "@min-[860px]:grid-cols-[minmax(0,1fr)_300px] @min-[1120px]:grid-cols-[minmax(0,1fr)_340px]")}>
        <div className="min-w-0">
          <Palco
            fase={fase}
            videoRef={video}
            stream={stream}
            sessao={sessao}
            leitura={leitura}
            carga={carga}
            erro={erro}
            instalado={erro?.instalado ?? naJanelaDoApp()}
            resumo={resumo}
            foco={foco}
            aoLigar={ligar}
            aoQuadro={aoQuadro}
            aoFalhar={aoFalhar}
          />
          {fase === "rodando" && (
            <Controles modo={modo} som={som} leitura={leitura} aoModo={setEscolhaDeModo} aoSom={alternarSom} />
          )}
        </div>
        <aside className="grid content-start gap-4">
          {aoVivo ? (
            <>
              <CartaoOlhos leitura={leitura} />
              <CartaoPulso leitura={leitura} sessao={sessao} />
              {numerosAoLado && <Medidas leitura={leitura} aoLado />}
            </>
          ) : (
            <AntesDeLigar />
          )}
        </aside>
      </div>
      {comDados && (
        <>
          {!numerosAoLado && <Medidas leitura={leitura} aoVivo={aoVivo} />}
          <LinhaDoTempo eventos={eventos} duracao={leitura?.t ?? resumo?.duracao ?? 0} />
        </>
      )}
    </div>
  );

  if (!foco) return experiencia;
  return (
    <Camada>
      <div role="dialog" aria-modal="true" aria-label="Teste com a câmera deste aparelho" className="fixed inset-0 z-40 overflow-y-auto bg-papel">
        {experiencia}
      </div>
    </Camada>
  );
}
