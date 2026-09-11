import { geoConicEqualArea } from "d3-geo";
import type { Feature, Point } from "geojson";
import { RouteDraw } from "@/components/maps/route-draw";
import { lerGeoJson, lerTopoObjetos } from "@/lib/geo";
import { caminhoLeve } from "@/lib/svg-path";

const LARGURA = 640;
const ALTURA = 760;

interface PontoRota {
  nome: string;
  km: number;
  x: number;
  y: number;
}

/** A BR-116 de São Paulo a Curitiba com a geometria real, as divisas e as rodovias próximas e as cidades de referência. */
export async function routeStrip({ rotulo }: { rotulo: string }): Promise<{ svg: React.ReactNode; kmTotal: number | null }> {
  const [rota, ufsObjetos, rodoviasObjetos] = await Promise.all([
    lerGeoJson("rota-br116-sp-curitiba.json"),
    lerTopoObjetos("brasil-ufs.topo.json"),
    lerTopoObjetos("rodovias-federais.topo.json"),
  ]);

  const linhas = rota?.features.filter((f) => f.geometry?.type === "LineString" || f.geometry?.type === "MultiLineString") ?? [];
  if (!rota || linhas.length === 0) return { svg: null, kmTotal: null };

  // clipExtent: só o que aparece no quadro entra no caminho (a malha do Brasil inteiro não vai para o HTML).
  const projecao = geoConicEqualArea()
    .rotate([54, 0])
    .parallels([-2, -22])
    .fitExtent(
      [
        [90, 60],
        [LARGURA - 90, ALTURA - 60],
      ],
      { type: "FeatureCollection", features: linhas }
    )
    .clipExtent([
      [-10, -10],
      [LARGURA + 10, ALTURA + 10],
    ]);

  const pontos: PontoRota[] = rota.features
    .filter((f): f is Feature<Point> => f.geometry?.type === "Point")
    .map((f) => {
      const p = (f.properties ?? {}) as Record<string, unknown>;
      const [x, y] = projecao(f.geometry.coordinates as [number, number]) ?? [0, 0];
      return { nome: String(p.nome ?? ""), km: Number(p.km_desde_inicio ?? 0), x, y };
    });

  const propsLinha = (linhas[0].properties ?? {}) as Record<string, unknown>;
  const kmTotal = Number(propsLinha.comprimento_km ?? 0) || null;

  const ufs = ufsObjetos ? Object.values(ufsObjetos).find((c) => c.features.length > 1) ?? Object.values(ufsObjetos)[0] : undefined;
  const rodovias = Object.values(rodoviasObjetos ?? {}).flatMap((c) => c.features);
  const dRota = caminhoLeve(projecao, linhas, 0.35);

  const svg = (
    <svg viewBox={`0 0 ${LARGURA} ${ALTURA}`} role="img" aria-label={rotulo} className="block h-auto w-full">
      {ufs ? <path d={caminhoLeve(projecao, ufs.features, 0.6)} fill="var(--c-papel)" stroke="var(--c-fio)" strokeWidth="1" /> : null}
      <path d={caminhoLeve(projecao, rodovias, 0.6)} fill="none" stroke="var(--c-fio-forte)" strokeWidth="1" opacity="0.6" />
      <path d={dRota} fill="none" stroke="var(--c-fio-forte)" strokeWidth="6" strokeLinecap="round" opacity="0.35" />
      <RouteDraw d={dRota} />
      {pontos.map((p) => (
        <g key={p.nome} transform={`translate(${p.x.toFixed(1)} ${p.y.toFixed(1)})`}>
          <circle r="6" fill="var(--c-concreto)" stroke="var(--c-asfalto)" strokeWidth="2.5" />
          <text x="14" y="-4" fontFamily="var(--font-titulo)" fontSize="26" fontWeight="700" fill="var(--c-asfalto)">
            {p.nome}
          </text>
          <text x="14" y="18" fontFamily="var(--font-instrumento)" fontSize="15" fill="var(--c-grafite)">
            km {Math.round(p.km)}
          </text>
        </g>
      ))}
    </svg>
  );

  return { svg, kmTotal };
}
