import { readFile } from "node:fs/promises";
import path from "node:path";

export interface FotoProvisoria {
  codigo: string;
  arquivo: string;
  largura: number;
  altura: number;
  autor: string;
  licenca: string;
  licencaUrl?: string;
  fonteUrl: string;
  altPt: string;
  altEn: string;
  observacoes?: string;
}

let cache: FotoProvisoria[] | null = null;

/** Manifesto escrito junto com as fotos provisórias. Sem manifesto, as cenas aparecem como blocos nomeados. */
export async function fotosProvisorias(): Promise<FotoProvisoria[]> {
  if (cache) return cache;
  try {
    const bruto = await readFile(path.join(process.cwd(), "src", "data", "fotos-provisorias.json"), "utf8");
    cache = JSON.parse(bruto) as FotoProvisoria[];
  } catch {
    cache = [];
  }
  return cache;
}

export async function fotoPorCodigo(codigo: string): Promise<FotoProvisoria | null> {
  const lista = await fotosProvisorias();
  const alvo = codigo.toLowerCase();
  return lista.find((f) => f.codigo.toLowerCase() === alvo) ?? null;
}
