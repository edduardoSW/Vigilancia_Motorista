// Momentos para verificar (prévia 2 aprovada em 14/09/2026): eventos de um episódio repetido viram um momento só, e
// cada evento que o servidor manda revisar e não está em episódio vira um momento. Textos em linguagem de garagem.
import {
  type Categoria,
  categoriaDe,
  duracao,
  type Evento,
  hora,
  minutosEntre,
  precisaRevisao,
  rotuloCurto,
  segundos,
  type VideoBruto,
  type Viagem,
} from "@/content";
import { duracaoDoTrecho, motivoSemVideo } from "@/components/trip/video-rules";

export type TipoMomento = "sono" | "celular" | "jornada" | "outro";
export type ResultadoMomento = "confirmado" | "alarme_falso";

export interface Decisao {
  resultado: ResultadoMomento;
  orientado: boolean;
  por: string;
  em: string;
}

/** Trecho gravado no momento, com a duração já calculada (spec 019, VID-01). */
export interface VideoMomento {
  id: string;
  inicio: string;
  fim: string;
  duracaoS: number;
  camera: string;
}

export interface Momento {
  id: string;
  numero: number;
  inicio: string;
  fim: string;
  tipo: TipoMomento;
  titulo: string;
  detalhe: string;
  /** Soma dos trechos gravados; null sem vídeo. */
  videoS: number | null;
  videos: VideoMomento[];
  /** Por que o momento não tem vídeo; null quando tem. */
  semVideo: string | null;
  decisaoInicial: Decisao | null;
}

const paraVideos = (lista: VideoBruto[] | undefined): VideoMomento[] =>
  (lista ?? []).map((video) => ({ ...video, duracaoS: duracaoDoTrecho(video.inicio, video.fim) }));

const somaDosTrechos = (videos: VideoMomento[]) => (videos.length ? videos.reduce((soma, video) => soma + video.duracaoS, 0) : null);

const tipoDaCategoria = (categoria: Categoria): TipoMomento =>
  categoria === "sonolencia" ? "sono" : categoria === "celular" ? "celular" : categoria === "jornada" ? "jornada" : "outro";

const OLHOS_FECHADOS = new Set(["microssono", "sono", "nao_responsivo"]);

function duranteQue(viagem: Viagem, iso: string) {
  const parte = viagem.jornada.find((item) => iso >= item.inicio && iso < item.fim);
  return parte?.tipo === "pausa" ? "Durante a pausa" : "Durante a direção";
}

function tituloDoEvento(evento: Evento) {
  const tempo = evento.duracaoS ? segundos(evento.duracaoS) : "";
  switch (evento.tipo) {
    case "olhando_celular":
      return `Olhando o celular por ${tempo}`;
    case "celular_no_ouvido":
      return `Celular no ouvido por ${tempo}`;
    case "celular_na_mao":
      return `Celular na mão por ${tempo}`;
    case "atencao":
      return "Primeiros sinais de sono";
    case "sonolencia":
      return "Sinais de sono";
    case "microssono":
    case "sono":
      return `Olhos fechados por ${tempo}`;
    case "nao_responsivo":
      return `Olhos fechados por ${tempo}, sem reação`;
    case "direcao_continua":
      return "Dirigiu mais de 5 h 30 sem parar";
    case "ativacao_atipica":
      return "Sinais fora do padrão do motorista";
    default:
      return rotuloCurto(evento.tipo);
  }
}

function detalheDoEvento(viagem: Viagem, evento: Evento) {
  if (evento.tipo === "atencao") return "Cansaço leve, comparado ao começo da viagem";
  if (evento.tipo === "direcao_continua") return "Limite do CTB para motorista profissional";
  if (evento.tipo === "ativacao_atipica") return "Indício para avaliar, não é diagnóstico";
  return duranteQue(viagem, evento.hora);
}

function decisaoDe(eventos: Evento[]): Decisao | null {
  const revisaveis = eventos.filter(precisaRevisao);
  if (!revisaveis.length || revisaveis.some((evento) => !evento.revisao)) return null;
  const revisoes = revisaveis.map((evento) => evento.revisao!);
  const falso = revisoes.every((revisao) => revisao.resultado === "alarme_falso");
  const ultima = revisoes.at(-1)!;
  return {
    resultado: falso ? "alarme_falso" : "confirmado",
    orientado: revisoes.some((revisao) => revisao.resultado === "orientado"),
    por: ultima.por,
    em: ultima.em,
  };
}

export function momentosDaViagem(viagem: Viagem): Momento[] {
  const momentos: Omit<Momento, "numero">[] = [];

  for (const episodio of viagem.episodios) {
    const eventos = viagem.eventos.filter((evento) => evento.episodio === episodio.id);
    if (!eventos.some(precisaRevisao)) continue;
    const fechados = eventos.filter((evento) => OLHOS_FECHADOS.has(evento.tipo)).length;
    const principal = eventos.find(precisaRevisao)!;
    momentos.push({
      id: `${viagem.id}-${episodio.id}`,
      inicio: episodio.inicio,
      fim: episodio.fim,
      tipo: tipoDaCategoria(categoriaDe(principal.tipo)),
      titulo: fechados >= 2 ? `Sono repetido: olhos fechados ${fechados} vezes` : episodio.titulo,
      detalhe: `Em ${duracao(minutosEntre(episodio.inicio, episodio.fim))}, entre ${hora(episodio.inicio)} e ${hora(episodio.fim)}`,
      videoS: somaDosTrechos(paraVideos(episodio.videos)),
      videos: paraVideos(episodio.videos),
      semVideo: episodio.videos?.length ? null : motivoSemVideo(principal.tipo),
      decisaoInicial: decisaoDe(eventos),
    });
  }

  for (const evento of viagem.eventos) {
    if (evento.episodio || !precisaRevisao(evento)) continue;
    momentos.push({
      id: `${viagem.id}-${evento.id}`,
      inicio: evento.hora,
      fim: evento.hora,
      tipo: tipoDaCategoria(categoriaDe(evento.tipo)),
      titulo: tituloDoEvento(evento),
      detalhe: detalheDoEvento(viagem, evento),
      videoS: somaDosTrechos(paraVideos(evento.videos)),
      videos: paraVideos(evento.videos),
      semVideo: evento.videos?.length ? null : motivoSemVideo(evento.tipo),
      decisaoInicial: decisaoDe([evento]),
    });
  }

  return momentos
    .sort((a, b) => Date.parse(a.inicio) - Date.parse(b.inicio))
    .map((momento, indice) => ({ ...momento, numero: indice + 1 }));
}

/** Madrugada: 00:00 a 06:59 (PRD, RF-03). */
export const naMadrugada = (iso: string) => Number(iso.slice(11, 13)) < 7;

export function contarPorTipo(momentos: Momento[]) {
  const contagem: Record<TipoMomento, number> = { sono: 0, celular: 0, jornada: 0, outro: 0 };
  for (const momento of momentos) contagem[momento.tipo] += 1;
  return contagem;
}
