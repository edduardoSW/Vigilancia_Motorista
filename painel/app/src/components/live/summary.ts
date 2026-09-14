// Spec 018 · frase-resumo dos eventos do script local ("3 de sono e 1 de celular"). Função pura, sem imports, para o
// teste rodar direto no Node (node --test com remoção de tipos).

export type TiposDeEvento = Record<string, { rotulo: string; categoria: string }>;

const CATEGORIAS: { id: string; texto: string }[] = [
  { id: "sonolencia", texto: "de sono" },
  { id: "celular", texto: "de celular" },
  { id: "jornada", texto: "de direção contínua" },
  { id: "ativacao", texto: "de ativação atípica" },
  { id: "sistema", texto: "da câmera ou calibração" },
  { id: "outro", texto: "de outro tipo" },
];

export function categoriaDe(tipo: string, tipos: TiposDeEvento): string {
  const categoria = tipos[tipo]?.categoria;
  return categoria && CATEGORIAS.some((item) => item.id === categoria) ? categoria : "outro";
}

export function nomeDoTipo(tipo: string, tipos: TiposDeEvento): string {
  return tipos[tipo]?.rotulo ?? tipo.replaceAll("_", " ");
}

function juntar(partes: string[]): string {
  if (partes.length <= 1) return partes.join("");
  return `${partes.slice(0, -1).join(", ")} e ${partes[partes.length - 1]}`;
}

export function resumoDosEventos(eventos: { tipo: string }[], tipos: TiposDeEvento): string {
  if (eventos.length === 0) return "Nenhum evento";
  const contagem = new Map<string, number>();
  for (const evento of eventos) {
    const categoria = categoriaDe(evento.tipo, tipos);
    contagem.set(categoria, (contagem.get(categoria) ?? 0) + 1);
  }
  const partes = CATEGORIAS.filter((item) => contagem.has(item.id)).map((item) => `${contagem.get(item.id)} ${item.texto}`);
  return juntar(partes);
}
