// Spec 025 · regras e textos do teste com a câmera do aparelho: abas do Ao vivo, caminhos do MediaPipe servidos pelo
// próprio painel, mensagens de erro da câmera e formatos dos números. Sem imports (o teste roda direto no Node).
// Texto sem travessão e sem jargão; o pulso é sempre "estimativa pela câmera, não é medida médica".

export type IdDaAba = "script" | "camera";

/** No painel instalado, o script local e a câmera; no painel web (transporte "servidor", na VPS), só a câmera. */
export function abasDoAoVivo(transporte: string | undefined): { id: IdDaAba; rotulo: string }[] {
  const camera = { id: "camera" as const, rotulo: "Câmera deste aparelho" };
  if (transporte === "servidor") return [camera];
  return [{ id: "script", rotulo: "Script neste computador" }, camera];
}

/** WASM (só o par com SIMD) e o mesmo modelo da caixa, copiados para public/mediapipe no build (scripts/copiar-mediapipe.mjs). */
export function caminhosDoMediapipe(base: string) {
  const raiz = `${base.replace(/\/+$/, "")}/mediapipe`;
  return {
    wasmLoaderPath: `${raiz}/wasm/vision_wasm_internal.js`,
    wasmBinaryPath: `${raiz}/wasm/vision_wasm_internal.wasm`,
    modelo: `${raiz}/modelos/face_landmarker.task`,
  };
}

export type ErroDaCamera = { titulo: string; texto: string; comoLiberar: string[]; tentarDeNovo: boolean };

/** Mensagem para cada erro do getUserMedia (nome do DOMException) e para os nossos ("inseguro", "navegador", "modelo"). */
export function erroDaCamera(nome: string, { instalado }: { instalado: boolean }): ErroDaCamera {
  switch (nome) {
    case "NotAllowedError":
    case "PermissionDeniedError":
    case "SecurityError":
      return {
        titulo: "A câmera foi bloqueada",
        texto: instalado
          ? "O RotaGuard Painel não recebeu permissão para usar a câmera deste computador."
          : "O navegador não deixou o painel usar a câmera deste aparelho.",
        comoLiberar: instalado
          ? [
              "No Windows, abra Configurações, Privacidade e segurança, Câmera, e deixe ligado o acesso para aplicativos da área de trabalho.",
              "Se o RotaGuard Painel não perguntar de novo, feche e abra o painel.",
              "Depois, toque em Tentar de novo.",
            ]
          : [
              "No computador, clique no cadeado ao lado do endereço, procure Câmera e escolha Permitir.",
              "No celular, abra as configurações do navegador, entre nas permissões deste site e libere a câmera.",
              "Depois, toque em Tentar de novo.",
            ],
        tentarDeNovo: true,
      };
    case "NotFoundError":
    case "DevicesNotFoundError":
      return {
        titulo: "Nenhuma câmera encontrada",
        texto: "Ligue uma webcam ou abra o painel num notebook ou celular com câmera.",
        comoLiberar: [],
        tentarDeNovo: true,
      };
    case "OverconstrainedError":
      return {
        titulo: "A câmera não aceitou o formato pedido",
        texto: "Tente outra câmera ou outro navegador.",
        comoLiberar: [],
        tentarDeNovo: true,
      };
    case "NotReadableError":
    case "TrackStartError":
    case "AbortError":
      return {
        titulo: "A câmera está ocupada",
        texto: "Outro programa está usando a câmera, por exemplo o RotaGuard Teste ou uma chamada de vídeo. Feche esse programa e tente de novo.",
        comoLiberar: [],
        tentarDeNovo: true,
      };
    case "inseguro":
      return {
        titulo: "Endereço sem proteção",
        texto: "A câmera só funciona em endereço seguro (https). Abra o painel pelo endereço com https.",
        comoLiberar: [],
        tentarDeNovo: false,
      };
    case "navegador":
      return {
        titulo: "Este navegador não roda o teste",
        texto: "Abra o painel no Chrome, no Edge, no Firefox ou no Safari atualizados.",
        comoLiberar: [],
        tentarDeNovo: false,
      };
    case "motor_bloqueado":
      return {
        titulo: "O painel bloqueou o motor do teste",
        texto: "A proteção desta página não deixa o navegador rodar o motor que acha os pontos do rosto. É preciso atualizar o painel; avise a RotaGuard.",
        comoLiberar: [],
        tentarDeNovo: false,
      };
    case "modelo":
      return {
        titulo: "Não foi possível carregar o modelo do rosto",
        texto: "Os arquivos do teste não chegaram inteiros. Confira a conexão com o painel e tente de novo.",
        comoLiberar: [],
        tentarDeNovo: true,
      };
    default:
      return {
        titulo: "Não foi possível abrir a câmera",
        texto: "Algo deu errado ao abrir a câmera neste aparelho.",
        comoLiberar: [],
        tentarDeNovo: true,
      };
  }
}

export type ModoDaMalha = "completa" | "pontos" | "essencial" | "desligada";

export const MODOS_DA_MALHA: { id: ModoDaMalha; rotulo: string }[] = [
  { id: "completa", rotulo: "Completa" },
  { id: "pontos", rotulo: "Pontos" },
  { id: "essencial", rotulo: "Essencial" },
  { id: "desligada", rotulo: "Desligada" },
];

const ROTULOS_DE_EVENTO: Record<string, string> = {
  microssono: "Olhos fechados por 1 s ou mais (microssono)",
  sono: "Olhos fechados por 3 s ou mais (sono)",
  sem_resposta: "Olhos fechados por 6 s ou mais (sem resposta)",
  bocejo: "Bocejo",
  cabeceio: "Cabeceio: a cabeça caiu e voltou",
  sem_rosto: "Rosto fora da câmera",
  perclos_alto: "Olhos fechados em 12% ou mais do último minuto",
};

export function rotuloDoEvento(tipo: string): string {
  return ROTULOS_DE_EVENTO[tipo] ?? tipo.replaceAll("_", " ");
}

/** Eventos que pedem atenção (texto em destaque na linha do tempo). */
export function eventoGrave(tipo: string): boolean {
  return tipo === "sono" || tipo === "sem_resposta" || tipo === "cabeceio" || tipo === "perclos_alto";
}

const decimal = (valor: number, casas = 1) =>
  valor.toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });

/** "1,2 s", "1 min 05 s"; null = o evento ainda está acontecendo. */
export function formatarDuracao(segundos: number | null): string {
  if (segundos === null) return "acontecendo";
  if (segundos < 60) return `${decimal(segundos)} s`;
  const inteiro = Math.round(segundos);
  return `${Math.floor(inteiro / 60)} min ${String(inteiro % 60).padStart(2, "0")} s`;
}

/** Relógio da sessão: "0:42", "12:05", "1:02:05". */
export function formatarRelogio(segundos: number): string {
  const total = Math.max(0, Math.floor(segundos));
  const horas = Math.floor(total / 3600);
  const minutos = Math.floor((total % 3600) / 60);
  const resto = String(total % 60).padStart(2, "0");
  return horas > 0 ? `${horas}:${String(minutos).padStart(2, "0")}:${resto}` : `${minutos}:${resto}`;
}

/** Pitch positivo = cabeça baixa (convenção do Python e da matriz do MediaPipe). */
export function descreverInclinacao(pitch: number): string {
  const graus = Math.round(Math.abs(pitch));
  if (graus < 1) return "reta";
  return `${graus}° ${pitch > 0 ? "para baixo" : "para cima"}`;
}

export function formatarPorcentagem(valor: number): string {
  return `${Math.round(valor * 100)}%`;
}

export function formatarSegundos(segundos: number): string {
  return `${decimal(segundos)} s`;
}
