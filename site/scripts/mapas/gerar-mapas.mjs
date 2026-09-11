#!/usr/bin/env node
/**
 * Gera os mapas do site em site/src/data/mapas/ a partir de dados públicos (nada é desenhado à mão nem por IA).
 *
 * Uso, na raiz do repositório:
 *   node site/scripts/mapas/gerar-mapas.mjs                 refaz tudo, reaproveitando downloads em .cache/
 *   node site/scripts/mapas/gerar-mapas.mjs --atualizar     baixa tudo de novo
 *   node site/scripts/mapas/gerar-mapas.mjs --so=rota       só um passo (mundo, brasil, rodovias, rota; aceita lista)
 * Depois: node site/scripts/mapas/conferir-mapas.mjs
 *
 * Requisitos: Node 18+ e internet na primeira execução. O mapshaper roda por npx, em versão fixa (lib/util.mjs).
 * Fontes, licenças e decisões: docs/site/dados-mapas.md.
 */
import { mkdirSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { extrairDoZip, lerDbf, lerShpLinhas, listarZip } from './lib/arquivos.mjs';
import {
  autointersecoes, comprimentoLinha, distanciaPontoBordaM, distanciaVincenty, pontoNaGeometria, simplificarDP,
} from './lib/geodesia.mjs';
import { MAPSHAPER, baixar, kb, mapshaper, parseJson } from './lib/util.mjs';

const AQUI = dirname(fileURLToPath(import.meta.url));
const CACHE = join(AQUI, '.cache');
const SAIDA = resolve(AQUI, '..', '..', 'src', 'data', 'mapas');

const args = process.argv.slice(2);
const ATUALIZAR = args.includes('--atualizar');
const SO = (args.find((a) => a.startsWith('--so=')) || '--so=mundo,brasil,rodovias,rota').slice(5).split(',');

// ---------------------------------------------------------------- parâmetros
const SNV_VERSAO = '202607A';
const TOL_UFS_M = 500; // Douglas-Peucker das divisas estaduais
const TOL_RODOVIAS_M = 200; // Douglas-Peucker da malha federal
const TOL_ROTA_M = 20; // Douglas-Peucker da rota (escala "rodovia")
const QUANT_MUNDO = 100000;
const QUANT_BRASIL = 50000;
const QUANT_RODOVIAS = 50000;

const FONTES = {
  naturalEarth: {
    url: 'https://naciscdn.org/naturalearth/110m/cultural/ne_110m_admin_0_countries.zip',
    pagina: 'https://www.naturalearthdata.com/downloads/110m-cultural-vectors/110m-admin-0-countries/',
    arquivo: 'ne_110m_admin_0_countries.zip',
  },
  ibgeUfs: {
    // A API devolve a malha mais recente por padrão; em 11/09/2026 era a de 2022 (periodo=2023 em diante: erro 500).
    url: 'https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR?formato=application/vnd.geo%2Bjson&qualidade=maxima&intrarregiao=UF&periodo=2022',
    arquivo: 'ibge-malha-ufs-2022-maxima.geojson',
  },
  ibgeEstados: {
    url: 'https://servicodados.ibge.gov.br/api/v1/localidades/estados',
    arquivo: 'ibge-localidades-estados.json',
  },
  snv: {
    url: `https://servicos.dnit.gov.br/dnitcloud/index.php/s/oTpPRmYs5AAdiNr/download?path=%2FSNV%20Bases%20Geom%C3%A9tricas%20(2013-Atual)%20(SHP)&files=${SNV_VERSAO}.zip`,
    pagina: 'https://www.gov.br/dnit/pt-br/assuntos/atlas-e-mapas/pnv-e-snv',
    arquivo: `snv-${SNV_VERSAO}.zip`,
  },
  ibgeMunicipio: (codigo) => ({
    url: `https://servicodados.ibge.gov.br/api/v3/malhas/municipios/${codigo}?formato=application/vnd.geo%2Bjson&qualidade=maxima&periodo=2022`,
    arquivo: `ibge-municipio-${codigo}-2022.geojson`,
  }),
};

const ATRIBUICAO = {
  naturalEarth: 'Natural Earth (domínio público)',
  ibge: 'IBGE, malha territorial de 2022 (API de malhas v3)',
  dnit: `DNIT, Sistema Nacional de Viação (SNV), versão ${SNV_VERSAO}`,
};

// ---------------------------------------------------------------- utilidades locais
const dataLocal = (ms) => new Intl.DateTimeFormat('sv-SE', { timeZone: 'America/Sao_Paulo' }).format(new Date(ms));
const acessadoEm = (caminho) => dataLocal(statSync(caminho).mtimeMs);
const arred = (n, casas) => Math.round(n * 10 ** casas) / 10 ** casas;

async function obter(fonte) {
  const r = await baixar(fonte.url, join(CACHE, fonte.arquivo), { atualizar: ATUALIZAR });
  console.log(`  ${r.baixadoAgora ? 'baixado' : 'cache'}: ${fonte.arquivo} (${kb(r.bytes)})`);
  return r.caminho;
}

function extrairZipPara(caminhoZip, pasta) {
  const buf = readFileSync(caminhoZip);
  mkdirSync(pasta, { recursive: true });
  const entradas = listarZip(buf);
  for (const e of entradas) {
    if (e.nome.endsWith('/')) continue;
    writeFileSync(join(pasta, e.nome.split('/').pop()), extrairDoZip(buf, e));
  }
  return entradas.map((e) => e.nome);
}

/** Regrava o JSON de saída com um membro "metadados" logo após "type" (membro estrangeiro, ignorado por d3 e topojson). */
function gravarComMetadados(caminho, metadados, dados = parseJson(readFileSync(caminho, 'utf8'))) {
  const { type, ...resto } = dados;
  writeFileSync(caminho, JSON.stringify({ type, metadados, ...resto }));
  return statSync(caminho).size;
}

// ---------------------------------------------------------------- 1. mundo
async function gerarMundo(rel) {
  console.log('\n[mundo] Natural Earth 1:110m, países');
  const zip = await obter(FONTES.naturalEarth);
  const pasta = join(CACHE, 'ne_110m_admin_0_countries');
  extrairZipPara(zip, pasta);
  const versao = readFileSync(join(pasta, 'ne_110m_admin_0_countries.VERSION.txt'), 'utf8').trim();
  const destino = join(SAIDA, 'mundo.topo.json');
  mapshaper([
    join(pasta, 'ne_110m_admin_0_countries.shp'),
    '-each', "nome = NAME_PT, nome_en = NAME, codigo = ADM0_A3, iso_n3 = ISO_N3_EH != '-99' ? ISO_N3_EH : null",
    '-filter-fields', 'nome,nome_en,codigo,iso_n3',
    '-rename-layers', 'paises',
    '-o', destino, 'format=topojson', `quantization=${QUANT_MUNDO}`,
  ]);
  // id da geometria = ISO 3166-1 numérico ("076"), a mesma convenção do pacote world-atlas.
  const topo = parseJson(readFileSync(destino, 'utf8'));
  for (const g of topo.objects.paises.geometries) {
    const { iso_n3: iso, ...props } = g.properties;
    g.properties = props;
    if (iso) g.id = iso;
  }
  const bytes = gravarComMetadados(destino, {
    conteudo: 'Países do mundo (Natural Earth 1:110m, Admin 0 – Countries, visão de fato)',
    fonte: 'Natural Earth',
    pagina: FONTES.naturalEarth.pagina,
    download: FONTES.naturalEarth.url,
    versao_do_dado: versao,
    acessado_em: acessadoEm(zip),
    licenca: 'Domínio público (https://www.naturalearthdata.com/about/terms-of-use/)',
    atribuicao: ATRIBUICAO.naturalEarth,
    processamento: `${MAPSHAPER}: sem simplificação além da escala 1:110m; campos NAME_PT→nome, NAME→nome_en, ADM0_A3→codigo, ISO_N3_EH→id; TopoJSON com quantização ${QUANT_MUNDO}`,
    coordenadas: 'WGS 84, [longitude, latitude]',
    objetos: { paises: 'um país por feição; id = ISO 3166-1 numérico ("076" = Brasil), ausente em Kosovo, Chipre do Norte e Somalilândia; propriedades nome, nome_en, codigo' },
  }, topo);
  rel.mundo = { arquivo: 'mundo.topo.json', bytes, versao_do_dado: versao, acessado_em: acessadoEm(zip) };
  console.log(`  -> mundo.topo.json ${kb(bytes)}`);
}

// ---------------------------------------------------------------- 2. Brasil e UFs
/** Malha de UFs da API do IBGE com sigla, nome e região (a API de malhas só traz o código). */
async function carregarUfs() {
  const arqUfs = await obter(FONTES.ibgeUfs);
  const arqEstados = await obter(FONTES.ibgeEstados);
  const ufs = parseJson(readFileSync(arqUfs, 'utf8'));
  const estados = new Map(parseJson(readFileSync(arqEstados, 'utf8')).map((e) => [String(e.id), e]));
  if (ufs.features.length !== 27) throw new Error(`Esperadas 27 UFs, vieram ${ufs.features.length}`);
  for (const f of ufs.features) {
    const e = estados.get(String(f.properties.codarea));
    if (!e) throw new Error(`Código de UF sem correspondência na API de localidades: ${f.properties.codarea}`);
    f.properties = { sigla: e.sigla, nome: e.nome, codigo_ibge: e.id, regiao: e.regiao.nome };
  }
  return { ufs, arqUfs };
}

async function gerarBrasil(rel) {
  console.log('\n[brasil] IBGE, malha de UFs');
  const { ufs, arqUfs } = await carregarUfs();
  const intermediario = join(CACHE, 'ibge-ufs-com-sigla.geojson');
  writeFileSync(intermediario, JSON.stringify(ufs));
  const destino = join(SAIDA, 'brasil-ufs.topo.json');
  mapshaper([
    intermediario,
    '-rename-layers', 'ufs',
    '-simplify', 'dp', `interval=${TOL_UFS_M}m`, 'keep-shapes',
    '-dissolve', '+', 'name=brasil',
    '-o', destino, 'format=topojson', `quantization=${QUANT_BRASIL}`, 'target=ufs,brasil',
  ]);
  const bytes = gravarComMetadados(destino, {
    conteudo: 'Contorno do Brasil (objeto "brasil") e as 27 UFs (objeto "ufs"), com divisas compartilhadas',
    fonte: 'IBGE – Instituto Brasileiro de Geografia e Estatística',
    download: FONTES.ibgeUfs.url,
    siglas: FONTES.ibgeEstados.url,
    versao_do_dado: 'Malha territorial 2022 (qualidade "máxima" da API de malhas v3)',
    acessado_em: acessadoEm(arqUfs),
    licenca: 'Dado aberto federal (Decreto 8.777/2016, art. 2º, III): livre utilização, creditando a fonte',
    atribuicao: ATRIBUICAO.ibge,
    processamento: `${MAPSHAPER}: Douglas-Peucker ${TOL_UFS_M} m (keep-shapes), contorno por dissolve das UFs; TopoJSON com quantização ${QUANT_BRASIL}`,
    coordenadas: 'SIRGAS 2000, considerado idêntico ao WGS 84 para fins práticos (IBGE, nota técnica de 2015); [longitude, latitude]',
    objetos: { ufs: 'propriedades sigla, nome, codigo_ibge, regiao', brasil: 'contorno nacional, sem propriedades' },
  });
  rel.brasil = { arquivo: 'brasil-ufs.topo.json', bytes, acessado_em: acessadoEm(arqUfs), tolerancia_m: TOL_UFS_M };
  console.log(`  -> brasil-ufs.topo.json ${kb(bytes)}`);
  return ufs;
}

// ---------------------------------------------------------------- SNV (compartilhado por rodovias e rota)
let snvCache = null;
async function carregarSnv() {
  if (snvCache) return snvCache;
  const zip = await obter(FONTES.snv);
  const pasta = join(CACHE, `snv-${SNV_VERSAO}`);
  const nomes = extrairZipPara(zip, pasta);
  const base = nomes.find((n) => n.toLowerCase().endsWith('.shp')).split('/').pop().replace(/\.shp$/i, '');
  const cpg = nomes.some((n) => n.toLowerCase().endsWith('.cpg')) ? readFileSync(join(pasta, `${base}.cpg`), 'utf8').trim() : 'latin1';
  const geoms = lerShpLinhas(readFileSync(join(pasta, `${base}.shp`)));
  const attrs = lerDbf(readFileSync(join(pasta, `${base}.dbf`)), /utf-?8/i.test(cpg) ? 'utf8' : 'latin1');
  if (geoms.length !== attrs.length) throw new Error('SNV: .shp e .dbf com contagens diferentes');
  const versoes = new Set(attrs.map((a) => a.versao_snv));
  if (versoes.size !== 1 || !versoes.has(SNV_VERSAO)) throw new Error(`SNV: versão inesperada nos atributos (${[...versoes]})`);
  snvCache = { zip, shp: join(pasta, `${base}.shp`), registros: attrs.map((a, i) => ({ ...a, partes: geoms[i] })) };
  return snvCache;
}

const SITUACAO = { DUP: 'duplicada', PAV: 'pavimentada', IMP: 'implantada', LEN: 'leito_natural' };

// ---------------------------------------------------------------- 3. rodovias federais
async function gerarRodovias(rel) {
  console.log(`\n[rodovias] DNIT, SNV ${SNV_VERSAO}`);
  const snv = await carregarSnv();
  const destino = join(SAIDA, 'rodovias-federais.topo.json');
  mapshaper([
    snv.shp,
    '-filter', "ds_sup_fed != 'PLA' && ds_sup_fed != 'TRV'",
    // Só aspas simples na expressão: no Windows o npx repassa os argumentos por cmd.exe.
    '-each', `br = vl_br, situacao = ${Object.entries(SITUACAO).map(([k, v]) => `ds_sup_fed == '${k}' ? '${v}' : `).join('')}null`,
    '-filter-fields', 'br,situacao',
    '-simplify', 'dp', `interval=${TOL_RODOVIAS_M}m`,
    '-dissolve', 'br,situacao',
    '-rename-layers', 'rodovias',
    '-o', destino, 'format=topojson', `quantization=${QUANT_RODOVIAS}`,
  ]);

  // Extensões medidas na geometria original (sem simplificação). Trecho coincidente (desc_coinc = "Coinc")
  // repete a geometria de outra BR: entra no desenho de cada BR, mas é contado uma vez só.
  const soma = () => ({ registros: 0, km_snv: 0, km_geodesico: 0 });
  const acc = { incluida: soma(), coincidentes_repetidos: soma(), planejada: soma(), travessia: soma(), por_situacao: {} };
  const planejadaComViaExistente = soma();
  const brs = new Set();
  let desconhecidas = 0;
  for (const r of snv.registros) {
    const km = r.partes.reduce((s, p) => s + comprimentoLinha(p), 0) / 1000;
    const somar = (alvo) => { alvo.registros++; alvo.km_snv += r.vl_extensa || 0; alvo.km_geodesico += km; };
    if (r.ds_sup_fed === 'PLA') {
      somar(acc.planejada);
      if (['PAV', 'DUP'].includes(r.sup_est_co)) somar(planejadaComViaExistente);
      continue;
    }
    if (r.ds_sup_fed === 'TRV') { somar(acc.travessia); continue; }
    if (!SITUACAO[r.ds_sup_fed]) { desconhecidas++; continue; }
    brs.add(r.vl_br);
    if (r.desc_coinc === 'Coinc') { somar(acc.coincidentes_repetidos); continue; }
    somar(acc.incluida);
    somar((acc.por_situacao[SITUACAO[r.ds_sup_fed]] ||= soma()));
  }
  if (desconhecidas) throw new Error(`SNV: ${desconhecidas} registros com ds_sup_fed desconhecido`);
  const fechar = (o) => ({ registros: o.registros, km_snv: arred(o.km_snv, 1), km_geodesico: arred(o.km_geodesico, 1) });
  const extensao = {
    malha_incluida: fechar(acc.incluida),
    por_situacao: Object.fromEntries(Object.entries(acc.por_situacao).map(([k, v]) => [k, fechar(v)])),
    coincidentes_desenhados_sem_somar: fechar(acc.coincidentes_repetidos),
    excluida_planejada: fechar(acc.planejada),
    excluida_planejada_mas_com_via_estadual_ou_municipal_pavimentada: fechar(planejadaComViaExistente),
    excluida_travessia: fechar(acc.travessia),
    brs_distintas: brs.size,
  };
  const bytes = gravarComMetadados(destino, {
    conteudo: 'Malha rodoviária federal existente (sem trechos planejados nem travessias), agrupada por BR e situação física',
    fonte: 'DNIT – Departamento Nacional de Infraestrutura de Transportes, Sistema Nacional de Viação (SNV)',
    pagina: FONTES.snv.pagina,
    download: FONTES.snv.url,
    versao_do_dado: `SNV ${SNV_VERSAO} (base geométrica publicada em 27/07/2026)`,
    acessado_em: acessadoEm(snv.zip),
    licenca: 'Dado público federal (Lei 12.527/2011; Decreto 8.777/2016): uso livre creditando a fonte. Ver docs/site/dados-mapas.md',
    atribuicao: ATRIBUICAO.dnit,
    processamento: `${MAPSHAPER}: filtro ds_sup_fed ≠ PLA e ≠ TRV; Douglas-Peucker ${TOL_RODOVIAS_M} m; dissolve por br e situacao; TopoJSON com quantização ${QUANT_RODOVIAS}`,
    coordenadas: 'SIRGAS 2000, considerado idêntico ao WGS 84 para fins práticos (IBGE, nota técnica de 2015); [longitude, latitude]',
    objetos: { rodovias: 'propriedades br ("116") e situacao (duplicada, pavimentada, implantada, leito_natural)' },
    trechos_coincidentes: 'aparecem em cada BR que os compartilha e usam os mesmos arcos; para desenhar a malha sem sobreposição use topojson.mesh',
    extensao_km: {
      total_snv: extensao.malha_incluida.km_snv,
      total_geodesico: extensao.malha_incluida.km_geodesico,
      por_situacao_snv: Object.fromEntries(Object.entries(extensao.por_situacao).map(([k, v]) => [k, v.km_snv])),
      observacao: 'medida antes da simplificação, contando uma vez os trechos coincidentes',
    },
  });
  rel.rodovias = { arquivo: 'rodovias-federais.topo.json', bytes, acessado_em: acessadoEm(snv.zip), tolerancia_m: TOL_RODOVIAS_M, extensao };
  console.log(`  -> rodovias-federais.topo.json ${kb(bytes)}`);
  console.log(`  extensão incluída: ${extensao.malha_incluida.km_snv} km (SNV) / ${extensao.malha_incluida.km_geodesico} km (geodésica)`);
}

// ---------------------------------------------------------------- 4. rota BR-116 São Paulo → Curitiba
const ROTA = {
  rodovia: '116',
  // Início: divisa municipal São Paulo/Taboão da Serra, onde a Rodovia Régis Bittencourt começa ao sair da capital.
  inicio: { uf: 'SP', km: 263.9, rotulo: 'DIV MUNICIPAL SÃO PAULO/TABOÃO DA SERRA' },
  // Fim: primeiro nó do SNV dentro do município de Curitiba (conferido com a malha municipal do IBGE abaixo).
  fim: { uf: 'PR', km: 119.2, rotulo: 'ENTR BR-116/277/376/476' },
  referencias: [
    { nome: 'São Paulo', rotulo: 'DIV MUNICIPAL SÃO PAULO/TABOÃO DA SERRA', municipio: 3550308, teste: 'borda' },
    { nome: 'Juquitiba', rotulo: 'INÍCIO DA SERRA DO CAFEZAL (JUQUITIBA)', municipio: 3526209, teste: 'dentro' },
    { nome: 'Registro', rotulo: 'ENTR SP-139 (REGISTRO)', municipio: 3542602, teste: 'dentro' },
    { nome: 'Divisa SP/PR', rotulo: 'DIV SP/PR (INÍCIO PONTE S/RIO PARDINHO)', uf: 'PR', teste: 'borda' },
    { nome: 'Curitiba', rotulo: 'ENTR BR-116/277/376/476', municipio: 4106902, teste: 'dentro' },
  ],
};

async function gerarRota(rel, ufsGeo) {
  console.log('\n[rota] BR-116 São Paulo → Curitiba (SNV)');
  const snv = await carregarSnv();
  const ordemUf = { SP: 0, PR: 1 };
  const trechos = snv.registros
    .filter((r) => r.vl_br === ROTA.rodovia && r.sg_tipo_tr === 'B')
    .filter((r) => (r.sg_uf === 'SP' && r.vl_km_inic >= ROTA.inicio.km - 1e-6) || (r.sg_uf === 'PR' && r.vl_km_fina <= ROTA.fim.km + 1e-6))
    .sort((a, b) => ordemUf[a.sg_uf] - ordemUf[b.sg_uf] || a.vl_km_inic - b.vl_km_inic);

  if (trechos[0].ds_local_i !== ROTA.inicio.rotulo) throw new Error(`Rota: início inesperado "${trechos[0].ds_local_i}"`);
  if (trechos.at(-1).ds_local_f !== ROTA.fim.rotulo) throw new Error(`Rota: fim inesperado "${trechos.at(-1).ds_local_f}"`);

  // Encadeia os trechos conferindo rótulos, quilometragem e continuidade geométrica (sem buracos).
  const completa = [];
  const simplificada = [];
  const nos = new Map(); // rótulo SNV do nó -> índice do vértice na linha completa
  let extensaoSnv = 0;
  trechos.forEach((t, i) => {
    if (t.partes.length !== 1) throw new Error(`Rota: trecho ${t.vl_codigo} com ${t.partes.length} partes`);
    let coords = t.partes[0];
    if (i > 0) {
      const ant = trechos[i - 1];
      if (ant.ds_local_f !== t.ds_local_i) throw new Error(`Rota: ${ant.vl_codigo} termina em "${ant.ds_local_f}", ${t.vl_codigo} começa em "${t.ds_local_i}"`);
      if (ant.sg_uf === t.sg_uf && Math.abs(ant.vl_km_fina - t.vl_km_inic) > 1e-6) throw new Error(`Rota: salto de km entre ${ant.vl_codigo} e ${t.vl_codigo}`);
      const ultimo = completa.at(-1);
      const dIni = distanciaVincenty(...ultimo, ...coords[0]);
      const dFim = distanciaVincenty(...ultimo, ...coords.at(-1));
      if (dIni > 1 && dFim <= 1) coords = coords.slice().reverse();
      else if (dIni > 1) throw new Error(`Rota: buraco de ${dIni.toFixed(0)} m antes de ${t.vl_codigo}`);
    }
    nos.set(t.ds_local_i, completa.length === 0 ? 0 : completa.length - 1);
    const s = simplificarDP(coords, TOL_ROTA_M);
    for (const [destino, lista] of [[completa, coords], [simplificada, s]]) {
      lista.forEach((c, k) => { if (!(k === 0 && destino.length > 0)) destino.push(c); });
    }
    nos.set(t.ds_local_f, completa.length - 1);
    extensaoSnv += t.vl_extensa;
  });

  // Distância acumulada (geodésica, WGS 84) na geometria original.
  const acumulada = new Float64Array(completa.length);
  for (let i = 1; i < completa.length; i++) acumulada[i] = acumulada[i - 1] + distanciaVincenty(...completa[i - 1], ...completa[i]);
  const comprimentoKm = acumulada.at(-1) / 1000;
  const comprimentoSimplKm = comprimentoLinha(simplificada) / 1000;

  const voltasCompleta = autointersecoes(completa).length;
  const voltasSimpl = autointersecoes(simplificada).length;
  if (voltasCompleta || voltasSimpl) throw new Error(`Rota: autointerseções (completa ${voltasCompleta}, simplificada ${voltasSimpl})`);

  // Confere cada referência contra a malha municipal (ou estadual) do IBGE.
  const pontos = [];
  for (const ref of ROTA.referencias) {
    const idx = nos.get(ref.rotulo);
    if (idx === undefined) throw new Error(`Rota: nó "${ref.rotulo}" não encontrado`);
    const coord = completa[idx];
    let conferencia;
    if (ref.municipio) {
      const arq = await obter(FONTES.ibgeMunicipio(ref.municipio));
      const geo = parseJson(readFileSync(arq, 'utf8')).features[0].geometry;
      const dentro = pontoNaGeometria(coord, geo);
      const borda = distanciaPontoBordaM(coord, geo);
      if (ref.teste === 'dentro' && !dentro) throw new Error(`Rota: "${ref.nome}" fora do município IBGE ${ref.municipio}`);
      if (ref.teste === 'borda' && borda > 500) throw new Error(`Rota: "${ref.nome}" a ${borda.toFixed(0)} m da borda do município ${ref.municipio}`);
      conferencia = `IBGE município ${ref.municipio}: ${dentro ? 'dentro' : 'fora'}, a ${borda.toFixed(0)} m da divisa municipal (malha 2022, qualidade máxima da API)`;
    } else {
      const uf = ufsGeo.features.find((f) => f.properties.sigla === ref.uf).geometry;
      const borda = distanciaPontoBordaM(coord, uf);
      if (borda > 500) throw new Error(`Rota: "${ref.nome}" a ${borda.toFixed(0)} m da divisa de ${ref.uf}`);
      conferencia = `IBGE: a ${borda.toFixed(0)} m da divisa de ${ref.uf} (malha 2022, qualidade máxima da API)`;
    }
    const trecho = trechos.find((t) => t.ds_local_i === ref.rotulo) || trechos.find((t) => t.ds_local_f === ref.rotulo);
    const kmMarco = trecho.ds_local_i === ref.rotulo ? trecho.vl_km_inic : trecho.vl_km_fina;
    pontos.push({
      nome: ref.nome,
      km_desde_inicio: arred(acumulada[idx] / 1000, 1),
      referencia_snv: `${ref.rotulo} · BR-116/${trecho.sg_uf} km ${String(kmMarco).replace('.', ',')}`,
      coord: [arred(coord[0], 5), arred(coord[1], 5)],
      conferencia,
    });
  }

  const colecao = {
    type: 'FeatureCollection',
    features: [
      {
        type: 'Feature',
        properties: {
          nome: 'BR-116, Rodovia Régis Bittencourt: São Paulo → Curitiba',
          comprimento_km: arred(comprimentoKm, 1),
        },
        geometry: { type: 'LineString', coordinates: simplificada.map(([x, y]) => [arred(x, 5), arred(y, 5)]) },
      },
      ...pontos.map((p) => ({
        type: 'Feature',
        properties: { nome: p.nome, km_desde_inicio: p.km_desde_inicio, referencia_snv: p.referencia_snv },
        geometry: { type: 'Point', coordinates: p.coord },
      })),
    ],
  };
  const destino = join(SAIDA, 'rota-br116-sp-curitiba.json');
  const bytes = gravarComMetadados(destino, {
    conteudo: 'Viagem de demonstração pela BR-116 (Rodovia Régis Bittencourt), de São Paulo a Curitiba. O RotaGuard não registra localização: exibir sempre como rota ilustrativa.',
    fonte: 'DNIT – Sistema Nacional de Viação (SNV), eixo principal da BR-116; posições conferidas com a malha municipal do IBGE',
    download: FONTES.snv.url,
    versao_do_dado: `SNV ${SNV_VERSAO}`,
    acessado_em: acessadoEm(snv.zip),
    licenca: 'Dado público federal (Lei 12.527/2011; Decreto 8.777/2016): uso livre creditando a fonte. Ver docs/site/dados-mapas.md',
    atribuicao: ATRIBUICAO.dnit,
    trechos_snv: trechos.map((t) => t.vl_codigo),
    inicio: `${ROTA.inicio.rotulo} (BR-116/SP km 263,9)`,
    fim: `${ROTA.fim.rotulo} (BR-116/PR km 119,2), primeiro nó do SNV dentro do município de Curitiba`,
    processamento: `Encadeamento dos ${trechos.length} trechos do SNV em ordem de km; Douglas-Peucker ${TOL_ROTA_M} m trecho a trecho (nós preservados); coordenadas com 5 casas decimais`,
    comprimento: {
      comprimento_km: 'geodésico (Vincenty, elipsoide WGS 84) na geometria original do SNV, antes da simplificação',
      linha_simplificada_km: arred(comprimentoSimplKm, 1),
      extensao_snv_km: arred(extensaoSnv, 1),
    },
    km_desde_inicio: 'geodésico ao longo da geometria original, até o nó do SNV citado em referencia_snv',
    coordenadas: 'SIRGAS 2000, considerado idêntico ao WGS 84 para fins práticos (IBGE, nota técnica de 2015); [longitude, latitude]',
  }, colecao);
  rel.rota = {
    arquivo: 'rota-br116-sp-curitiba.json', bytes, acessado_em: acessadoEm(snv.zip), tolerancia_m: TOL_ROTA_M,
    trechos: trechos.length, vertices_originais: completa.length, vertices_saida: simplificada.length,
    comprimento_km: arred(comprimentoKm, 2), linha_simplificada_km: arred(comprimentoSimplKm, 2), extensao_snv_km: arred(extensaoSnv, 1),
    pontos: pontos.map(({ nome, km_desde_inicio, referencia_snv, coord, conferencia }) => ({ nome, km_desde_inicio, referencia_snv, coord, conferencia })),
  };
  console.log(`  -> rota-br116-sp-curitiba.json ${kb(bytes)}; ${arred(comprimentoKm, 1)} km (SNV: ${arred(extensaoSnv, 1)} km)`);
  for (const p of pontos) console.log(`     ${p.nome}: km ${p.km_desde_inicio} | ${p.conferencia}`);
}

// ---------------------------------------------------------------- execução
mkdirSync(SAIDA, { recursive: true });
mkdirSync(CACHE, { recursive: true });
const caminhoRelatorio = join(CACHE, 'relatorio.json');
let rel = {};
try { rel = parseJson(readFileSync(caminhoRelatorio, 'utf8')); } catch { /* primeira execução */ }

if (SO.includes('mundo')) await gerarMundo(rel);
let ufsGeo = null;
if (SO.includes('brasil')) ufsGeo = await gerarBrasil(rel);
if (SO.includes('rodovias')) await gerarRodovias(rel);
if (SO.includes('rota')) await gerarRota(rel, ufsGeo || (await carregarUfs()).ufs);
writeFileSync(caminhoRelatorio, JSON.stringify(rel, null, 2));
console.log(`\nRelatório: ${caminhoRelatorio}`);
