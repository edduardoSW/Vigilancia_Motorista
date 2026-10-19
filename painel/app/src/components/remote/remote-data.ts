// Spec 026 · textos da tela "Testes à distância" e da seção Central. Funções puras, sem imports, para o teste rodar
// direto no Node (scripts/testes/remotos.test.mjs).

export type TiposDeEvento = Record<string, { rotulo: string; categoria: string }>;

const dois = (numero: number) => String(numero).padStart(2, "0");
const plural = (n: number, um: string, varios: string) => `${n} ${n === 1 ? um : varios}`;

export function nomeDoTipo(tipo: string | null | undefined, tipos: TiposDeEvento): string {
  if (!tipo) return "Evento";
  return tipos[tipo]?.rotulo ?? tipo.replaceAll("_", " ");
}

/** Nível de risco do script (0 a 3); cor de alarme só a partir do médio. */
export function textoRisco(nivel: number | null | undefined): { texto: string; alarme: boolean } {
  if (nivel === 3) return { texto: "risco alto", alarme: true };
  if (nivel === 2) return { texto: "risco médio", alarme: true };
  if (nivel === 1) return { texto: "risco baixo", alarme: false };
  return { texto: "sem alerta", alarme: false };
}

export function duracaoTexto(segundos: number | null | undefined): string {
  if (segundos === null || segundos === undefined || !Number.isFinite(segundos) || segundos < 0) return "sem duração";
  if (segundos < 60) return `${Math.round(segundos)} s`;
  const minutos = Math.round(segundos / 60);
  if (minutos < 60) return `${minutos} min`;
  return `${Math.floor(minutos / 60)} h ${dois(minutos % 60)}`;
}

/** Data e hora locais curtas: "19/10 às 14:02". */
export function dataHora(iso: string | null | undefined): string {
  const instante = iso ? Date.parse(iso) : Number.NaN;
  if (Number.isNaN(instante)) return "sem data";
  const data = new Date(instante);
  return `${dois(data.getDate())}/${dois(data.getMonth() + 1)} às ${dois(data.getHours())}:${dois(data.getMinutes())}`;
}

export function hora(iso: string | null | undefined): string {
  const instante = iso ? Date.parse(iso) : Number.NaN;
  if (Number.isNaN(instante)) return "";
  const data = new Date(instante);
  return `${dois(data.getHours())}:${dois(data.getMinutes())}`;
}

/** "há 12 s", "há 3 min", "há 2 h"; depois de um dia, a data ("em 18/10 às 11:58"). */
export function haQuanto(iso: string | null | undefined, agoraMs: number): string {
  const instante = iso ? Date.parse(iso) : Number.NaN;
  if (Number.isNaN(instante)) return "nunca";
  const segundos = Math.max(0, Math.round((agoraMs - instante) / 1000));
  if (segundos < 60) return `há ${segundos} s`;
  if (segundos < 3600) return `há ${Math.floor(segundos / 60)} min`;
  if (segundos < 86_400) return `há ${Math.floor(segundos / 3600)} h`;
  return `em ${dataHora(iso)}`;
}

/** Quanto tempo depois do início da sessão: "+09:40" ou "+1:02:03". */
export function deslocamento(ocorrido: string | null | undefined, inicio: string | null | undefined): string {
  const fim = ocorrido ? Date.parse(ocorrido) : Number.NaN;
  const comeco = inicio ? Date.parse(inicio) : Number.NaN;
  if (Number.isNaN(fim) || Number.isNaN(comeco)) return "";
  const total = Math.max(0, Math.round((fim - comeco) / 1000));
  const horas = Math.floor(total / 3600);
  const resto = `${dois(Math.floor((total % 3600) / 60))}:${dois(total % 60)}`;
  return horas ? `+${horas}:${resto}` : `+${resto}`;
}

export function percentual(valor: number | null | undefined): string {
  return valor === null || valor === undefined || !Number.isFinite(valor) ? "sem medida" : `${Math.round(valor * 100)}%`;
}

type SessaoParaResumo = {
  eventos?: number;
  trechos?: number;
  resumo: { perclos_medio?: number | null; piscadas_por_minuto?: number | null };
};

/** "3 eventos · 2 trechos · PERCLOS 7% · 15 piscadas/min": só o que foi medido. */
export function resumoDaSessao(sessao: SessaoParaResumo): string {
  const partes = [plural(sessao.eventos ?? 0, "evento", "eventos"), sessao.trechos ? plural(sessao.trechos, "trecho", "trechos") : "sem trechos"];
  const perclos = sessao.resumo.perclos_medio;
  if (typeof perclos === "number" && Number.isFinite(perclos)) partes.push(`PERCLOS ${percentual(perclos)}`);
  const piscadas = sessao.resumo.piscadas_por_minuto;
  if (typeof piscadas === "number" && Number.isFinite(piscadas)) partes.push(`${Math.round(piscadas)} piscadas/min`);
  return partes.join(" · ");
}

/** Subtítulo com número real: "2 computadores · 1 testando agora · 3 sessões". */
export function resumoDaTela(lista: { aparelhos: { testando_agora: boolean }[]; sessoes: unknown[] }): string {
  if (!lista.aparelhos.length && !lista.sessoes.length) return "Nenhum computador conectado ainda";
  const testando = lista.aparelhos.filter((item) => item.testando_agora).length;
  const partes = [plural(lista.aparelhos.length, "computador", "computadores")];
  if (testando) partes.push(`${testando} testando agora`);
  partes.push(plural(lista.sessoes.length, "sessão", "sessões"));
  return partes.join(" · ");
}

type CentralParaStatus = {
  conectado: boolean;
  usuario: { nome: string } | null;
  empresa: { nome: string } | null;
  ultima_busca: string | null;
  sem_conexao: boolean;
};

/** Uma frase sobre a central, com a cor de alarme só quando não alcança a central (PCE-05). */
export function statusDaCentral(estado: CentralParaStatus, agoraMs: number): { texto: string; alarme: boolean } {
  const busca = estado.ultima_busca ? `última busca ${haQuanto(estado.ultima_busca, agoraMs)}` : "buscando pela primeira vez";
  if (!estado.conectado) {
    return { texto: `Não conectado à central${estado.ultima_busca ? `. Mostrando o que já foi baixado (${busca})` : ""}.`, alarme: false };
  }
  if (estado.sem_conexao) {
    return { texto: `Sem conexão com a central. Mostrando o que já foi baixado (${busca}).`, alarme: true };
  }
  const quem = [estado.usuario ? `Conectado como ${estado.usuario.nome}` : "Conectado", estado.empresa?.nome].filter(Boolean).join(" · ");
  return { texto: `${quem} · ${busca}`, alarme: false };
}

/** Índice do quadro a mostrar no instante `t` (o último com tempo <= t). Quadros em ordem de tempo. */
export function quadroNoTempo(quadros: readonly { t: number }[], t: number): number {
  if (!quadros.length) return -1;
  let baixo = 0;
  let alto = quadros.length - 1;
  while (baixo < alto) {
    const meio = Math.ceil((baixo + alto) / 2);
    if (quadros[meio].t <= t) baixo = meio;
    else alto = meio - 1;
  }
  return baixo;
}
