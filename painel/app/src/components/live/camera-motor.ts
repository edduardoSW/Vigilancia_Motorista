// Spec 025 · motor do teste com a câmera: baixa o modelo do próprio painel, cria o FaceLandmarker (placa de vídeo, e o
// processador como reserva) e roda, a cada quadro novo do vídeo, a malha, os sinais de sono e o pulso. Tudo no aparelho:
// nenhum quadro, ponto ou número sai daqui. A tela importa este arquivo só quando a pessoa liga a câmera.
import type { FaceLandmarker, FaceLandmarkerResult, NormalizedLandmark } from "@mediapipe/tasks-vision";
import { coresDoTema, type CoresDoTema } from "./camera-cores";
import { DesenhoDaMalha, type ConexoesDoRosto } from "./camera-malha";
import { caminhosDoMediapipe, type ModoDaMalha } from "./camera-regras";
import { LeitorDeRoi } from "./camera-roi";
import { MonitorDoPulso, ROIS, regioesUsaveis, type LeituraDoPulso, type Ponto as PontoDoPulso } from "./camera-rppg";
import {
  LEFT_EYE,
  ModeloDeAbertura,
  MonitorDeSono,
  P80_OPENNESS,
  RIGHT_EYE,
  combinarOlhos,
  ear,
  eulerDaMatriz,
  larguraDoOlho,
  type EventoDaSessao,
  type LeituraDeSono,
  type Ponto,
} from "./camera-sono";
import { bloquearEnviosParaFora, pararCamera } from "./camera-trilhas";

export type Processador = "placa de vídeo" | "processador";

export type Carga = { etapa: "baixando" | "preparando"; baixado: number; total: number };

export type Motor = { landmarker: FaceLandmarker; conexoes: ConexoesDoRosto; processador: Processador; fechar(): void };

/** Só para a barra de progresso quando o servidor comprime e não diz o tamanho (WASM com SIMD + modelo, versão 1.1.1). */
const TAMANHO_ESPERADO = 13_520_000 + 3_760_000;

function erroNomeado(nome: string, mensagem: string): Error {
  const erro = new Error(mensagem);
  erro.name = nome;
  return erro;
}

async function baixar(endereco: string, sinal: AbortSignal, aoAvancar: (bytes: number, total: number | null) => void): Promise<Uint8Array> {
  const resposta = await fetch(endereco, { signal: sinal });
  if (!resposta.ok || !resposta.body) throw erroNomeado("modelo", `${endereco}: HTTP ${resposta.status}`);
  const comprimido = Boolean(resposta.headers.get("content-encoding"));
  const total = comprimido ? null : Number(resposta.headers.get("content-length")) || null;
  const leitor = resposta.body.getReader();
  const pedacos: Uint8Array[] = [];
  let recebido = 0;
  for (;;) {
    const { done, value } = await leitor.read();
    if (done) break;
    pedacos.push(value);
    recebido += value.length;
    aoAvancar(recebido, total);
  }
  const bytes = new Uint8Array(recebido);
  let posicao = 0;
  for (const pedaco of pedacos) {
    bytes.set(pedaco, posicao);
    posicao += pedaco.length;
  }
  return bytes;
}

/**
 * O WASM do MediaPipe escreve no console avisos de funcionamento normal ("INFO: Created TensorFlow Lite XNNPACK
 * delegate for CPU" sai como erro). O carregador do Emscripten aceita print e printErr pelo self.Module, que o MediaPipe
 * usa e depois apaga: o normal some e só erro de verdade (E ou F do glog) continua aparecendo.
 */
function silenciarMediapipe(): void {
  Object.assign(globalThis, {
    Module: {
      print: () => {},
      printErr: (texto: string) => {
        if (/^[EF]d{4}/.test(texto)) console.warn(`MediaPipe: ${texto}`);
      },
    },
  });
}

/**
 * Baixa o modelo e o WASM com progresso (o WASM fica no cache do navegador e o MediaPipe o pega de lá) e cria o
 * detector. A trava de envio para fora entra antes do MediaPipe e só sai depois do close(), que também tenta enviar.
 */
export async function prepararMotor(aoCarregar: (carga: Carga) => void, sinal: AbortSignal): Promise<Motor> {
  const caminhos = caminhosDoMediapipe(process.env.NEXT_PUBLIC_PAINEL_BASE_PATH ?? "");
  const soltar = bloquearEnviosParaFora();
  try {
    const recebido = { modelo: 0, wasm: 0 };
    const totais: { modelo: number | null; wasm: number | null } = { modelo: null, wasm: null };
    const avisar = () => {
      const baixado = recebido.modelo + recebido.wasm;
      const total = totais.modelo !== null && totais.wasm !== null ? totais.modelo + totais.wasm : Math.max(TAMANHO_ESPERADO, baixado);
      aoCarregar({ etapa: "baixando", baixado, total });
    };
    const [modelo] = await Promise.all([
      baixar(caminhos.modelo, sinal, (bytes, total) => {
        recebido.modelo = bytes;
        totais.modelo = total;
        avisar();
      }),
      baixar(caminhos.wasmBinaryPath, sinal, (bytes, total) => {
        recebido.wasm = bytes;
        totais.wasm = total;
        avisar();
      }),
    ]);
    aoCarregar({ etapa: "preparando", baixado: 1, total: 1 });
    const { FaceLandmarker } = await import("@mediapipe/tasks-vision");
    const fileset = { wasmLoaderPath: caminhos.wasmLoaderPath, wasmBinaryPath: caminhos.wasmBinaryPath };
    const criar = (delegate: "GPU" | "CPU") => {
      silenciarMediapipe();
      return FaceLandmarker.createFromOptions(fileset, {
        baseOptions: { modelAssetBuffer: modelo, delegate },
        runningMode: "VIDEO",
        numFaces: 1,
        outputFaceBlendshapes: true,
        outputFacialTransformationMatrixes: true,
      });
    };
    let landmarker: FaceLandmarker;
    let processador: Processador = "placa de vídeo";
    try {
      landmarker = await criar("GPU");
    } catch {
      // Sem WebGL2 (ou driver bloqueado): o processador dá conta, mais devagar.
      landmarker = await criar("CPU");
      processador = "processador";
    }
    const conexoes: ConexoesDoRosto = {
      tesselacao: FaceLandmarker.FACE_LANDMARKS_TESSELATION,
      contornos: [
        ...FaceLandmarker.FACE_LANDMARKS_FACE_OVAL,
        ...FaceLandmarker.FACE_LANDMARKS_LEFT_EYEBROW,
        ...FaceLandmarker.FACE_LANDMARKS_RIGHT_EYEBROW,
        ...FaceLandmarker.FACE_LANDMARKS_LEFT_EYE,
        ...FaceLandmarker.FACE_LANDMARKS_RIGHT_EYE,
        ...FaceLandmarker.FACE_LANDMARKS_LIPS,
      ],
      olhos: [...FaceLandmarker.FACE_LANDMARKS_LEFT_EYE, ...FaceLandmarker.FACE_LANDMARKS_RIGHT_EYE],
      iris: [...FaceLandmarker.FACE_LANDMARKS_LEFT_IRIS, ...FaceLandmarker.FACE_LANDMARKS_RIGHT_IRIS],
      boca: FaceLandmarker.FACE_LANDMARKS_LIPS,
    };
    const fechar = () => {
      try {
        landmarker.close();
      } finally {
        soltar();
      }
    };
    if (sinal.aborted) {
      fechar();
      throw erroNomeado("AbortError", "cancelado");
    }
    return { landmarker, conexoes, processador, fechar };
  } catch (erro) {
    soltar();
    if (erro instanceof Error && erro.name !== "modelo" && erro.name !== "AbortError" && !sinal.aborted) {
      // A política da página (CSP sem 'wasm-unsafe-eval') impede compilar o WASM: não é arquivo faltando.
      const bloqueado = /Content Security|CompileError|wasm-unsafe-eval/i.test(erro.message);
      // Falha do próprio MediaPipe (WASM sem SIMD, memória): a tela mostra o nome e a mensagem reais.
      throw erroNomeado(bloqueado ? "motor_bloqueado" : "modelo", `${erro.name}: ${erro.message}`);
    }
    throw erro;
  }
}

export type Pose = { pitch: number; yaw: number; roll: number };

export type Instantaneo = {
  /** Segundos desde que a câmera ligou. */
  t: number;
  rosto: boolean;
  abertura: number | null;
  aprendendo: boolean;
  sono: LeituraDeSono;
  pose: Pose | null;
  /** Pulso estimado pelo mesmo monitor da caixa (cardio.py): estado, bpm, confiança, aquecimento e onda. */
  cardio: LeituraDoPulso;
  /** Regiões do pulso em uso (testa, bochecha esq e bochecha dir, lado da imagem). */
  regioes: boolean[];
  quadrosPorSegundo: number;
  msPorQuadro: number;
  processador: Processador;
};


const pontuacao = (resultado: FaceLandmarkerResult, nome: string) =>
  resultado.faceBlendshapes[0]?.categories.find((categoria) => categoria.categoryName === nome)?.score ?? null;

const dentroDaImagem = (pontos: NormalizedLandmark[], indices: readonly number[]) =>
  indices.every((indice) => pontos[indice].x >= 0 && pontos[indice].x <= 1 && pontos[indice].y >= 0 && pontos[indice].y <= 1);

/**
 * Uma sessão da câmera: guarda o motor, a câmera e tudo o que já foi medido. O vídeo e o canvas podem trocar (tela
 * cheia, celular) sem perder a sessão: `ligar` recomeça o laço nos elementos novos.
 */
export class SessaoDaCamera {
  readonly stream: MediaStream;
  readonly processador: Processador;
  private modo: ModoDaMalha = "completa";
  private readonly motor: Motor;
  private readonly sono = new MonitorDeSono();
  private readonly modeloDeAbertura = new ModeloDeAbertura();
  private readonly inicioMs = performance.now();
  private readonly monitorDoPulso = new MonitorDoPulso();
  private cardio: LeituraDoPulso = { estado: "sem_rosto", bpm: null, confianca: 0, snrDb: null, progresso: 0, onda: [], ultimoBpm: null };
  private ultimoTs = -1;
  private tempos: number[] = [];
  private msMedio = 0;
  private cores: CoresDoTema = coresDoTema();
  private proximasCores = 0;
  private desligarAtual: (() => void) | null = null;
  private encerrada = false;

  constructor(motor: Motor, stream: MediaStream) {
    this.motor = motor;
    this.stream = stream;
    this.processador = motor.processador;
  }

  get eventos(): readonly EventoDaSessao[] {
    return this.sono.eventos;
  }

  get versaoDosEventos(): number {
    return this.sono.versao;
  }

  /** Completa, pontos, essencial (celular) ou desligada: vale a partir do próximo quadro. */
  definirModo(modo: ModoDaMalha): void {
    this.modo = modo;
  }

  /** Segundos desde que a câmera ligou. */
  agora(): number {
    return (performance.now() - this.inicioMs) / 1000;
  }

  /** Onda dos últimos 6 s (refeita 10 vezes por segundo, como na caixa) e se ela já vale como leitura. */
  ondaAtual(): { trecho: readonly number[]; confiavel: boolean } | null {
    return this.cardio.onda.length ? { trecho: this.cardio.onda, confiavel: this.cardio.estado === "pronto" } : null;
  }

  /** 0 a 1 acompanhando a sístole, para o contorno das regiões pulsar; null enquanto não há número. */
  private pulso(): number | null {
    if (this.cardio.estado !== "pronto" || !this.cardio.onda.length) return null;
    return (this.cardio.onda[this.cardio.onda.length - 1] + 1) / 2;
  }

  /** Começa o laço por quadro novo do vídeo (requestVideoFrameCallback; requestAnimationFrame como reserva). */
  ligar(video: HTMLVideoElement, canvas: HTMLCanvasElement, aoQuadro: (instantaneo: Instantaneo) => void, aoFalhar: (erro: unknown) => void): () => void {
    this.desligarAtual?.();
    const desenho = new DesenhoDaMalha(canvas, this.motor.conexoes);
    const roi = new LeitorDeRoi();
    const observador = new ResizeObserver(() => desenho.ajustar());
    observador.observe(canvas);
    desenho.ajustar();
    let ativo = true;
    let id = 0;
    let ultimoTempoDoVideo = -1;

    const processar = (agoraMs: number) => {
      const ts = Math.max(this.ultimoTs + 1, Math.round(agoraMs)); // o detectForVideo exige horário sempre crescente
      this.ultimoTs = ts;
      const t0 = performance.now();
      let resultado: FaceLandmarkerResult;
      try {
        resultado = this.motor.landmarker.detectForVideo(video, ts);
      } catch (erro) {
        ativo = false;
        aoFalhar(erro);
        return;
      }
      const ms = performance.now() - t0;
      this.msMedio = this.msMedio ? this.msMedio * 0.9 + ms * 0.1 : ms;
      const t = (ts - this.inicioMs) / 1000;
      this.tempos.push(t);
      while (this.tempos.length && this.tempos[0] < t - 2) this.tempos.shift();
      if (t >= this.proximasCores) {
        this.cores = coresDoTema(); // o tema pode trocar com a câmera ligada
        this.proximasCores = t + 1;
      }

      const pontos = resultado.faceLandmarks[0];
      let leitura: LeituraDeSono;
      let abertura: number | null = null;
      let pose: Pose | null = null;
      let regioes: boolean[];
      if (!pontos) {
        desenho.limpar();
        leitura = this.sono.atualizar({ t, rosto: false, abertura: null, jawOpen: null, pitch: null });
        this.cardio = this.monitorDoPulso.atualizar(t, null);
        regioes = [false, false, false];
      } else {
        const largura = video.videoWidth;
        const altura = video.videoHeight;
        const emPixels: Ponto[] = [];
        for (const indice of [...RIGHT_EYE, ...LEFT_EYE]) emPixels[indice] = { x: pontos[indice].x * largura, y: pontos[indice].y * altura };
        // Olho com ponto fora da imagem não é medido: o modelo inventa a forma dele (face.py).
        const direitoDentro = dentroDaImagem(pontos, RIGHT_EYE);
        const esquerdoDentro = dentroDaImagem(pontos, LEFT_EYE);
        const earOlhos = combinarOlhos(
          esquerdoDentro ? ear(emPixels, LEFT_EYE) : null,
          direitoDentro ? ear(emPixels, RIGHT_EYE) : null,
          esquerdoDentro ? larguraDoOlho(emPixels, LEFT_EYE) : 0,
          direitoDentro ? larguraDoOlho(emPixels, RIGHT_EYE) : 0,
        );
        const piscadas = [pontuacao(resultado, "eyeBlinkLeft"), pontuacao(resultado, "eyeBlinkRight")].filter((valor) => valor !== null);
        const piscada = piscadas.length && (direitoDentro || esquerdoDentro) ? piscadas.reduce((a, b) => a + b, 0) / piscadas.length : null;
        const distanciaOlhosPx = Math.hypot(
          emPixels[RIGHT_EYE[0]].x - emPixels[LEFT_EYE[3]].x,
          emPixels[RIGHT_EYE[0]].y - emPixels[LEFT_EYE[3]].y,
        );
        const matriz = resultado.facialTransformationMatrixes?.[0];
        pose = matriz ? eulerDaMatriz(matriz.data) : null;
        abertura = this.modeloDeAbertura.abertura({ ear: earOlhos, piscada, distanciaOlhosPx });
        leitura = this.sono.atualizar({ t, rosto: true, abertura, jawOpen: pontuacao(resultado, "jawOpen"), pitch: pose?.pitch ?? null });

        // Pulso como no cardio.py: vértices suavizados, polígonos arredondados, bochecha do rosto virado fora.
        const todosEmPixels: PontoDoPulso[] = pontos.map((ponto) => ({ x: ponto.x * largura, y: ponto.y * altura }));
        const suaves = this.monitorDoPulso.suavizar(t, todosEmPixels);
        const poligonos = ROIS.map((regiao) => regiao.map((indice) => ({ x: Math.round(suaves[indice].x), y: Math.round(suaves[indice].y) })));
        regioes = regioesUsaveis(poligonos);
        this.cardio = this.monitorDoPulso.atualizar(t, { pontos: todosEmPixels, medias: roi.ler(video, poligonos, regioes) });
        desenho.desenhar(pontos, {
          modo: this.modo,
          pulso: this.pulso(),
          olhosFechados: leitura.estagio !== "normal" || (abertura !== null && abertura <= P80_OPENNESS),
          areas: regioes,
          cores: this.cores,
        });
      }
      aoQuadro({
        t,
        rosto: Boolean(pontos),
        abertura,
        aprendendo: this.modeloDeAbertura.aprendendo,
        sono: leitura,
        pose,
        cardio: this.cardio,
        regioes,
        quadrosPorSegundo: this.tempos.length / Math.min(2, Math.max(t, 0.5)),
        msPorQuadro: this.msMedio,
        processador: this.processador,
      });
    };

    const comRvfc = "requestVideoFrameCallback" in HTMLVideoElement.prototype;
    const porQuadro = (agora: number) => {
      if (!ativo) return;
      if (video.readyState >= 2) processar(agora);
      if (ativo) id = video.requestVideoFrameCallback(porQuadro);
    };
    const porAnimacao = (agora: number) => {
      if (!ativo) return;
      if (video.readyState >= 2 && video.currentTime !== ultimoTempoDoVideo) {
        ultimoTempoDoVideo = video.currentTime;
        processar(agora);
      }
      if (ativo) id = requestAnimationFrame(porAnimacao);
    };
    id = comRvfc ? video.requestVideoFrameCallback(porQuadro) : requestAnimationFrame(porAnimacao);

    const desligar = () => {
      ativo = false;
      if (comRvfc) video.cancelVideoFrameCallback(id);
      else cancelAnimationFrame(id);
      observador.disconnect();
      desenho.limpar();
      if (this.desligarAtual === desligar) this.desligarAtual = null;
    };
    this.desligarAtual = desligar;
    return desligar;
  }

  /** CAM-09: para o laço, desliga todas as trilhas da câmera e fecha o detector (e a trava de envio). */
  encerrar(video: HTMLVideoElement | null): void {
    if (this.encerrada) return;
    this.encerrada = true;
    this.desligarAtual?.();
    pararCamera(this.stream, video);
    this.motor.fechar();
  }
}
