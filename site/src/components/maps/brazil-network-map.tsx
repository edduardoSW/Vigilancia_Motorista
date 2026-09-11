import { geoConicEqualArea } from "d3-geo";
import type { FeatureCollection, Geometry, MultiPoint } from "geojson";
import { lerGeoJson, lerMetadados, lerTopoObjetos } from "@/lib/geo";
import { caminhoLeve } from "@/lib/svg-path";

const LARGURA = 900;
const ALTURA = 900;

// Enquadramento pelo continente: o contorno do IBGE inclui Trindade e Fernando de Noronha,
// que puxariam o mapa para o oceano (limite leste continental ≈ -34,79°).
const CONTINENTE: MultiPoint = {
  type: "MultiPoint",
  coordinates: [
    [-74.0, 5.3],
    [-34.79, 5.3],
    [-34.79, -33.75],
    [-74.0, -33.75],
  ],
};

export interface MalhaBrasil {
  svg: React.ReactNode;
  kmRodovias: number | null;
}

function acharColecao(
  objetos: Record<string, FeatureCollection<Geometry>> | null,
  pistas: string[]
): FeatureCollection<Geometry> | undefined {
  if (!objetos) return undefined;
  const chave = Object.keys(objetos).find((k) => pistas.some((p) => k.toLowerCase().includes(p)));
  return chave ? objetos[chave] : Object.values(objetos)[0];
}

/**
 * Malha rodoviária federal (SNV/DNIT) sobre as divisas das UFs (IBGE), em projeção cônica equivalente de Albers
 * com os parâmetros usados pelo IBGE para o Brasil (meridiano central -54°, paralelos -2° e -22°).
 * A BR-116 entre São Paulo e Curitiba aparece em destaque como viagem de demonstração.
 */
export async function brazilNetworkMap({ rotulo }: { rotulo: string }): Promise<MalhaBrasil> {
  const [ufsObjetos, rodoviasObjetos, rota, metadados] = await Promise.all([
    lerTopoObjetos("brasil-ufs.topo.json"),
    lerTopoObjetos("rodovias-federais.topo.json"),
    lerGeoJson("rota-br116-sp-curitiba.json"),
    lerMetadados<{ extensao_km?: { total_snv?: number } }>("rodovias-federais.topo.json"),
  ]);

  const ufs = acharColecao(ufsObjetos, ["uf", "estado", "states"]);
  if (!ufs) return { svg: null, kmRodovias: null };

  const rodovias = Object.values(rodoviasObjetos ?? {}).flatMap((c) => c.features);
  const linhaRota = rota?.features.filter((f) => f.geometry?.type === "LineString" || f.geometry?.type === "MultiLineString") ?? [];

  const projecao = geoConicEqualArea()
    .rotate([54, 0])
    .parallels([-2, -22])
    .fitExtent(
      [
        [24, 24],
        [LARGURA - 24, ALTURA - 24],
      ],
      CONTINENTE
    );

  // Extensão oficial do SNV (cada trecho contado uma vez). Somar a geometria contaria duas vezes
  // os trechos compartilhados entre BRs (81,8 mil km em vez de 74,8 mil).
  const kmRodovias = metadados?.extensao_km?.total_snv ? Math.round(metadados.extensao_km.total_snv) : null;

  const svg = (
    <svg viewBox={`0 0 ${LARGURA} ${ALTURA}`} role="img" aria-label={rotulo} className="block h-auto w-full">
      <path d={caminhoLeve(projecao, ufs.features, 0.8)} fill="var(--c-papel)" stroke="var(--c-fio)" strokeWidth="0.8" />
      <path
        d={caminhoLeve(projecao, rodovias, 0.7)}
        fill="none"
        stroke="var(--c-asfalto)"
        strokeWidth="0.9"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity="0.72"
      />
      {linhaRota.length ? (
        <path
          d={caminhoLeve(projecao, linhaRota, 0.5)}
          fill="none"
          stroke="var(--c-asfalto)"
          strokeWidth="5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      ) : null}
    </svg>
  );

  return { svg, kmRodovias };
}
