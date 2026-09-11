import { readFile } from "node:fs/promises";
import path from "node:path";
import type { Feature, FeatureCollection, Geometry } from "geojson";
import { feature } from "topojson-client";
import type { Topology } from "topojson-specification";

const PASTA_MAPAS = path.join(process.cwd(), "src", "data", "mapas");

/** Lê um arquivo de mapa gerado por scripts/mapas. Devolve null se ainda não existir (o site continua buildando). */
async function lerJson<T>(nome: string): Promise<T | null> {
  try {
    return JSON.parse(await readFile(path.join(PASTA_MAPAS, nome), "utf8")) as T;
  } catch {
    return null;
  }
}

/** TopoJSON → FeatureCollection. Usa o primeiro objeto, ou o nome pedido. */
export async function lerTopo(nome: string, objeto?: string): Promise<FeatureCollection<Geometry> | null> {
  const topo = await lerJson<Topology>(nome);
  if (!topo) return null;
  const chave = objeto ?? Object.keys(topo.objects)[0];
  const geo = feature(topo, topo.objects[chave]) as FeatureCollection<Geometry> | Feature<Geometry>;
  return geo.type === "FeatureCollection" ? geo : { type: "FeatureCollection", features: [geo] };
}

/** Todos os objetos de um TopoJSON, por nome. */
export async function lerTopoObjetos(nome: string): Promise<Record<string, FeatureCollection<Geometry>> | null> {
  const topo = await lerJson<Topology>(nome);
  if (!topo) return null;
  return Object.fromEntries(
    Object.keys(topo.objects).map((chave) => {
      const geo = feature(topo, topo.objects[chave]) as FeatureCollection<Geometry> | Feature<Geometry>;
      return [chave, geo.type === "FeatureCollection" ? geo : { type: "FeatureCollection", features: [geo] }];
    })
  );
}

/** Metadados gravados pelo gerador de mapas (fonte, versão, extensões calculadas). */
export async function lerMetadados<T = Record<string, unknown>>(nome: string): Promise<T | null> {
  const bruto = await lerJson<{ metadados?: T }>(nome);
  return bruto?.metadados ?? null;
}

export async function lerGeoJson(nome: string): Promise<FeatureCollection<Geometry> | null> {
  return lerJson<FeatureCollection<Geometry>>(nome);
}
