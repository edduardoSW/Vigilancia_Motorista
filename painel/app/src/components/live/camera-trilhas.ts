// Spec 025 · abrir e desligar a câmera do aparelho, e barrar envio para fora enquanto o teste roda.
// Sem imports e sem tocar no window por conta própria (o ambiente vem por parâmetro): o teste roda no Node com objetos falsos.

type AmbienteDaCamera = { isSecureContext: boolean; mediaDevices?: { getUserMedia(restricoes: MediaStreamConstraints): Promise<MediaStream> } };

type VideoDaCamera = {
  muted: boolean;
  playsInline: boolean;
  srcObject: MediaProvider | null;
  setAttribute(nome: string, valor: string): void;
  play(): Promise<void>;
};

function erroNomeado(nome: string, mensagem: string): Error {
  const erro = new Error(mensagem);
  erro.name = nome;
  return erro;
}

function ambienteDoNavegador(): AmbienteDaCamera {
  return { isSecureContext: window.isSecureContext, mediaDevices: navigator.mediaDevices };
}

/** Pede só vídeo, a câmera da frente como preferência (nunca exact: o iPhone recusa) e 640 × 480 a 30 quadros. */
export async function abrirCamera(video: VideoDaCamera, ambiente: AmbienteDaCamera = ambienteDoNavegador()): Promise<MediaStream> {
  if (!ambiente.isSecureContext) throw erroNomeado("inseguro", "a câmera só abre em endereço seguro (https)");
  if (!ambiente.mediaDevices?.getUserMedia) throw erroNomeado("navegador", "navegador sem getUserMedia");
  const stream = await ambiente.mediaDevices.getUserMedia({
    audio: false,
    video: { facingMode: { ideal: "user" }, width: { ideal: 640 }, height: { ideal: 480 }, frameRate: { ideal: 30 } },
  });
  // iPhone: o vídeo só toca sozinho mudo e dentro da página (sem playsinline ele abre em tela cheia ou fica preto).
  video.muted = true;
  video.playsInline = true;
  video.setAttribute("playsinline", "");
  video.srcObject = stream;
  await video.play();
  return stream;
}

/** CAM-09: desliga todas as trilhas (a luz da câmera apaga) e solta o vídeo. */
export function pararCamera(stream: { getTracks(): { stop(): void }[] } | null, video: { pause(): void; srcObject: unknown } | null): void {
  stream?.getTracks().forEach((trilha) => trilha.stop());
  if (video) {
    video.pause();
    video.srcObject = null;
  }
}

type JanelaComFetch = { fetch: typeof fetch; location: { href: string; origin: string } };

/**
 * Enquanto a câmera está ligada, todo fetch para fora do painel recebe "bloqueado" sem sair do aparelho. O MediaPipe
 * 1.1.x manda métricas de uso para o Google a cada 60 s e ao fechar: com a falha, ele para sozinho. A CSP da página
 * (connect-src 'self') continua sendo a trava principal; esta é a segunda. Devolve a função que desfaz.
 */
export function bloquearEnviosParaFora(janela: JanelaComFetch = window): () => void {
  const original = janela.fetch;
  const guardado: typeof fetch = (entrada, opcoes) => {
    const endereco = typeof entrada === "string" ? entrada : entrada instanceof URL ? entrada.href : entrada.url;
    if (new URL(endereco, janela.location.href).origin !== janela.location.origin) {
      return Promise.resolve(new Response(null, { status: 403, statusText: "Envio bloqueado neste aparelho" }));
    }
    return original.call(janela, entrada, opcoes);
  };
  janela.fetch = guardado;
  return () => {
    if (janela.fetch === guardado) janela.fetch = original;
  };
}
