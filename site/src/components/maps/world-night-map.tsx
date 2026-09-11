import { geoEqualEarth, geoPath } from "d3-geo";
import type { Feature, Geometry } from "geojson";
import { NightShade } from "@/components/maps/night-shade";
import { lerTopo } from "@/lib/geo";
import { caminhoLeve } from "@/lib/svg-path";

const LARGURA = 960;
const ALTURA = 468;

function ehBrasil(f: Feature<Geometry>): boolean {
  const p = (f.properties ?? {}) as Record<string, unknown>;
  return p.codigo === "BRA" || f.id === "076" || f.id === 76 || p.name === "Brazil" || p.ISO_A3 === "BRA";
}

export async function WorldNightMap({ rotulo }: { rotulo: string }) {
  const mundo = await lerTopo("mundo.topo.json");
  const projecao = geoEqualEarth().fitSize([LARGURA, ALTURA], { type: "Sphere" });
  const [tx, ty] = projecao.translate();
  const paises = mundo?.features ?? [];
  const brasil = paises.filter(ehBrasil);
  const outros = paises.filter((f) => !ehBrasil(f));

  return (
    <svg viewBox={`0 0 ${LARGURA} ${ALTURA}`} role="img" aria-label={rotulo} className="block h-auto w-full">
      <path d={geoPath(projecao)({ type: "Sphere" }) ?? undefined} fill="var(--c-papel)" stroke="var(--c-fio)" strokeWidth="1" />
      <path d={caminhoLeve(projecao, outros, 0.6)} fill="var(--c-terra)" stroke="var(--c-papel)" strokeWidth="0.5" />
      <path d={caminhoLeve(projecao, brasil, 0.4)} fill="var(--c-asfalto)" />
      <NightShade escala={projecao.scale()} translacao={[tx, ty]} />
    </svg>
  );
}
