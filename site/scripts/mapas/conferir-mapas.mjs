#!/usr/bin/env node
/**
 * Confere os arquivos de site/src/data/mapas/ (contagens, bbox, propriedades, tamanho, continuidade da rota)
 * e desenha um teste visual em .cache/teste.svg (e .cache/teste.png, se houver como converter).
 *
 * Uso, na raiz do repositório: node site/scripts/mapas/conferir-mapas.mjs
 * Usa d3-geo se estiver instalado no site (mesma biblioteca da renderização real, inclusive a checagem do
 * sentido dos anéis); sem ele, usa uma projeção equirretangular simples. Sai com código 1 se algo falhar.
 */
import { spawnSync } from 'node:child_process';
import { readFileSync, statSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { autointersecoes, comprimentoLinha, distanciaPontoLinhaM } from './lib/geodesia.mjs';
import { arcosDecodificados, arcosDoObjeto, feicoes } from './lib/topojson.mjs';

const AQUI = dirname(fileURLToPath(import.meta.url));
const DADOS = resolve(AQUI, '..', '..', 'src', 'data', 'mapas');
const CACHE = join(AQUI, '.cache');

const falhas = [];
const checar = (ok, texto) => { console.log(`  ${ok ? 'ok  ' : 'FALHA'} ${texto}`); if (!ok) falhas.push(texto); };
const ler = (nome) => JSON.parse(readFileSync(join(DADOS, nome), 'utf8'));
const tamanho = (nome) => statSync(join(DADOS, nome)).size;
const kb = (b) => `${(b / 1024).toFixed(1)} KB`;

function bboxDe(feats) {
  const b = [Infinity, Infinity, -Infinity, -Infinity];
  const visitar = (c) => {
    if (typeof c[0] === 'number') { b[0] = Math.min(b[0], c[0]); b[1] = Math.min(b[1], c[1]); b[2] = Math.max(b[2], c[0]); b[3] = Math.max(b[3], c[1]); }
    else c.forEach(visitar);
  };
  feats.forEach((f) => f.geometry && visitar(f.geometry.coordinates));
  return b.map((v) => Math.round(v * 1000) / 1000);
}
const aneisExternos = (g) => (g.type === 'Polygon' ? [g.coordinates[0]] : g.type === 'MultiPolygon' ? g.coordinates.map((p) => p[0]) : []);
const areaPlana = (anel) => anel.reduce((s, p, i) => { const q = anel[(i + 1) % anel.length]; return s + p[0] * q[1] - q[0] * p[1]; }, 0) / 2;

let d3 = null;
try { d3 = await import('d3-geo'); } catch { /* d3-geo não instalado: segue com projeção simples */ }
console.log(d3 ? 'Usando d3-geo instalado para projetar e checar anéis.' : 'd3-geo não encontrado: projeção equirretangular simples e checagem plana dos anéis.');

/** Anéis no sentido esperado pelo d3-geo: área esférica de cada feição menor que um hemisfério. */
function checarAneis(feats, rotulo) {
  if (d3) {
    const invertidas = feats.filter((f) => d3.geoArea(f) > 2 * Math.PI).map((f) => f.properties.sigla || f.properties.nome || '?');
    checar(invertidas.length === 0, `${rotulo}: nenhuma feição com anel invertido para o d3-geo${invertidas.length ? ` (${invertidas.join(', ')})` : ''}`);
  } else {
    let ruins = 0, total = 0;
    for (const f of feats) for (const anel of aneisExternos(f.geometry)) {
      const lons = anel.map((p) => p[0]);
      if (Math.max(...lons) - Math.min(...lons) > 180) continue; // anel que cruza o antimeridiano (Antártida etc.)
      total++; if (areaPlana(anel) > 0) ruins++;
    }
    checar(ruins === 0, `${rotulo}: anéis externos no sentido horário (convenção do d3-geo), ${total - ruins}/${total}`);
  }
}

// ------------------------------------------------------------------ mundo
console.log('\nmundo.topo.json');
const mundo = ler('mundo.topo.json');
const paises = feicoes(mundo, 'paises');
checar(tamanho('mundo.topo.json') <= 150 * 1024, `tamanho ${kb(tamanho('mundo.topo.json'))} (alvo até 150 KB)`);
checar(paises.length >= 170, `${paises.length} países`);
const brasilNoMundo = paises.find((f) => f.properties.codigo === 'BRA');
const idBrasil = mundo.objects.paises.geometries.find((g) => g.properties.codigo === 'BRA')?.id;
checar(brasilNoMundo && brasilNoMundo.properties.nome === 'Brasil' && idBrasil === '076', `Brasil presente: id ${idBrasil}, ${JSON.stringify(brasilNoMundo?.properties)}`);
const ids = mundo.objects.paises.geometries.map((g) => g.id).filter(Boolean);
checar(ids.length >= 170 && new Set(ids).size === ids.length && ids.every((i) => /^\d{3}$/.test(i)), `${ids.length} países com id ISO numérico único de 3 dígitos`);
checar(paises.every((f) => f.properties.nome && f.properties.nome_en && f.properties.codigo), 'todas as feições com nome, nome_en e codigo');
const bbMundo = bboxDe(paises);
checar(bbMundo[0] <= -179 && bbMundo[2] >= 179 && bbMundo[1] <= -89, `bbox ${bbMundo.join(', ')}`);
checar(!!mundo.metadados?.licenca, `metadados: ${mundo.metadados?.fonte} ${mundo.metadados?.versao_do_dado}`);
checarAneis(paises, 'mundo');

// ------------------------------------------------------------------ Brasil e UFs
console.log('\nbrasil-ufs.topo.json');
const br = ler('brasil-ufs.topo.json');
const ufs = feicoes(br, 'ufs');
const contorno = feicoes(br, 'brasil');
checar(tamanho('brasil-ufs.topo.json') <= 200 * 1024, `tamanho ${kb(tamanho('brasil-ufs.topo.json'))} (alvo até 200 KB)`);
const siglas = ufs.map((f) => f.properties.sigla).sort();
checar(ufs.length === 27 && new Set(siglas).size === 27, `27 UFs com sigla única: ${siglas.join(' ')}`);
checar(contorno.length === 1, `contorno "brasil" com ${contorno.length} feição`);
const bbBr = bboxDe(contorno);
checar(bbBr[0] > -74.5 && bbBr[0] < -73.5 && bbBr[1] > -34 && bbBr[1] < -33.5 && bbBr[3] > 5 && bbBr[3] < 5.5, `bbox com ilhas oceânicas ${bbBr.join(', ')}`);
const continental = { type: 'Feature', geometry: { type: 'MultiPolygon', coordinates: [] } };
continental.geometry.coordinates = (contorno[0].geometry.type === 'Polygon' ? [contorno[0].geometry.coordinates] : contorno[0].geometry.coordinates)
  .filter((p) => Math.max(...p[0].map((c) => c[0])) < -34.7);
const bbCont = bboxDe([continental]);
checar(bbCont[2] > -35 && bbCont[2] < -34.7, `bbox sem ilhas a leste de 34,7° O ${bbCont.join(', ')}`);
const arcosUfs = arcosDoObjeto(br, 'ufs');
const soltos = [...arcosDoObjeto(br, 'brasil')].filter((a) => !arcosUfs.has(a)).length;
checar(soltos === 0, `contorno usa só arcos das UFs (divisas coincidem): ${soltos} arcos exclusivos`);
checarAneis([...ufs, ...contorno], 'brasil');

// ------------------------------------------------------------------ rodovias
console.log('\nrodovias-federais.topo.json');
const rod = ler('rodovias-federais.topo.json');
const vias = feicoes(rod, 'rodovias');
checar(tamanho('rodovias-federais.topo.json') <= 400 * 1024, `tamanho ${kb(tamanho('rodovias-federais.topo.json'))} (alvo até 400 KB)`);
const brsDistintas = new Set(vias.map((f) => f.properties.br));
const situacoes = [...new Set(vias.map((f) => f.properties.situacao))].sort();
checar(vias.every((f) => /^\d{3}$/.test(f.properties.br)), `${vias.length} feições, ${brsDistintas.size} BRs, br com 3 dígitos`);
checar(situacoes.every((s) => ['duplicada', 'pavimentada', 'implantada', 'leito_natural'].includes(s)), `situações: ${situacoes.join(', ')} (sem planejada)`);
const bbRod = bboxDe(vias);
checar(bbRod[0] > -74.5 && bbRod[1] > -34 && bbRod[3] < 5.5 && bbRod[2] < -32, `bbox ${bbRod.join(', ')} (leste em Fernando de Noronha, BR-363)`);
const arcosRod = arcosDecodificados(rod);
const kmMesh = [...arcosDoObjeto(rod, 'rodovias')].reduce((s, i) => s + comprimentoLinha(arcosRod[i]), 0) / 1000;
const linhasDe = (g) => (g.type === 'LineString' ? [g.coordinates] : g.coordinates);
const kmFeicoes = vias.reduce((s, f) => s + linhasDe(f.geometry).reduce((t, l) => t + comprimentoLinha(l), 0), 0) / 1000;
const kmOficial = rod.metadados?.extensao_km?.total_geodesico;
console.log(`  malha desenhada (arcos únicos): ${kmMesh.toFixed(0)} km; somando feições (coincidentes repetidos): ${kmFeicoes.toFixed(0)} km; medida antes de simplificar: ${kmOficial} km`);
checar(kmOficial && Math.abs(kmMesh / kmOficial - 1) < 0.03, `arcos únicos batem com a extensão medida (diferença ${((kmMesh / kmOficial - 1) * 100).toFixed(2)}%, trechos coincidentes compartilham arcos)`);
const br116 = vias.filter((f) => f.properties.br === '116');
checar(br116.length > 0, `BR-116 presente (${br116.map((f) => f.properties.situacao).join(', ')})`);

// ------------------------------------------------------------------ rota
console.log('\nrota-br116-sp-curitiba.json');
const rota = ler('rota-br116-sp-curitiba.json');
const linhas = rota.features.filter((f) => f.geometry.type === 'LineString');
const pontos = rota.features.filter((f) => f.geometry.type === 'Point');
checar(rota.type === 'FeatureCollection' && linhas.length === 1, `FeatureCollection com 1 LineString e ${pontos.length} pontos, ${kb(tamanho('rota-br116-sp-curitiba.json'))}`);
const linha = linhas[0].geometry.coordinates;
const kmLinha = comprimentoLinha(linha) / 1000;
checar(typeof linhas[0].properties.nome === 'string' && linhas[0].properties.comprimento_km > 0, `propriedades da linha: ${JSON.stringify(linhas[0].properties)}`);
checar(Math.abs(kmLinha / linhas[0].properties.comprimento_km - 1) < 0.01, `linha entregue mede ${kmLinha.toFixed(1)} km (comprimento_km medido na geometria original)`);
checar(linha.every((c, i) => i === 0 || c[0] !== linha[i - 1][0] || c[1] !== linha[i - 1][1]), `${linha.length} vértices, sem repetidos seguidos`);
checar(autointersecoes(linha).length === 0, 'sem autointerseções (sem voltas)');
const bbRota = bboxDe(linhas);
checar(bbRota[0] > -49.5 && bbRota[2] < -46.5 && bbRota[1] > -25.7 && bbRota[3] < -23.5, `bbox ${bbRota.join(', ')}`);
let kmAnterior = -1;
for (const p of pontos) {
  const d = distanciaPontoLinhaM(p.geometry.coordinates, linha);
  checar(d < 2 && p.properties.km_desde_inicio > kmAnterior, `${p.properties.nome}: km ${p.properties.km_desde_inicio}, a ${d.toFixed(1)} m da linha`);
  kmAnterior = p.properties.km_desde_inicio;
}
const dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]);
checar(dist(linha[0], pontos[0].geometry.coordinates) < 1e-4 && pontos[0].properties.km_desde_inicio === 0, 'linha começa no primeiro ponto (km 0)');
checar(dist(linha.at(-1), pontos.at(-1).geometry.coordinates) < 1e-4 && pontos.at(-1).properties.km_desde_inicio === linhas[0].properties.comprimento_km, 'linha termina no último ponto (km = comprimento_km)');

// ------------------------------------------------------------------ teste visual
// "→" vira "->": o librsvg antigo que acompanha o ImageMagick no Windows descarta o texto inteiro.
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/→/g, '->');
function projetor(objetoFit, largura, altura, tipo, margem = [12, 28, 12, 12]) {
  const [me, mt, md, mb] = margem;
  if (d3) {
    const proj = (tipo === 'mundo' ? d3.geoEqualEarth() : d3.geoMercator()).fitExtent([[me, mt], [largura - md, altura - mb]], objetoFit);
    const caminho = d3.geoPath(proj);
    return { d: (g) => caminho(g) || '', ponto: (c) => proj(c) };
  }
  const b = objetoFit.type === 'Sphere' ? [-180, -90, 180, 90] : bboxDe(objetoFit.features || [objetoFit]);
  const k = Math.cos((((b[1] + b[3]) / 2) * Math.PI) / 180);
  const esc2 = Math.min((largura - me - md) / ((b[2] - b[0]) * k), (altura - mt - mb) / (b[3] - b[1]));
  const ponto = ([x, y]) => [me + (x - b[0]) * k * esc2, mt + (b[3] - y) * esc2];
  const anel = (r) => `M${r.map((c) => ponto(c).map((v) => v.toFixed(1)).join(',')).join('L')}`;
  const d = (g) => {
    if (!g) return '';
    switch (g.type) {
      case 'LineString': return anel(g.coordinates);
      case 'MultiLineString': return g.coordinates.map(anel).join('');
      case 'Polygon': return g.coordinates.map((r) => `${anel(r)}Z`).join('');
      case 'MultiPolygon': return g.coordinates.map((p) => p.map((r) => `${anel(r)}Z`).join('')).join('');
      case 'FeatureCollection': return g.features.map((f) => d(f.geometry)).join('');
      case 'Feature': return d(g.geometry);
      default: return '';
    }
  };
  return { d, ponto };
}
const cor = { duplicada: '#1f2937', pavimentada: '#6b7280', implantada: '#b45309', leito_natural: '#d97706' };
const fc = (feats) => ({ type: 'FeatureCollection', features: feats });

let nPainel = 0;
function painel(titulo, largura, altura, fit, tipo, camadas, margem) {
  const p = projetor(fit, largura, altura, tipo, margem);
  const id = `quadro${++nPainel}`;
  // Grupo recortado (e não <svg> aninhado) e sem path vazio: o resvg aborta com qualquer um dos dois.
  const corpo = camadas(p).replace(/<path d=""[^>]*\/>/g, '');
  // Título por último, sobre uma faixa, para as camadas não o cobrirem.
  return `<clipPath id="${id}"><rect width="${largura}" height="${altura}"/></clipPath><g clip-path="url(#${id})">
<rect width="${largura}" height="${altura}" fill="#eef2f6"/>${corpo}
<rect width="${largura}" height="26" fill="#ffffff" fill-opacity="0.85"/><text x="12" y="18" font-family="Arial, sans-serif" font-size="13" fill="#111">${esc(titulo)}</text></g>`;
}

const W = 1000;
const p1 = painel(`mundo.topo.json · ${paises.length} países · ${d3 ? 'd3.geoEqualEarth' : 'equirretangular'}`, W, 520, { type: 'Sphere' }, 'mundo', (p) =>
  (d3 ? `<path d="${p.d({ type: 'Sphere' })}" fill="#dbe7f3" stroke="#9fb3c8"/>` : '') +
  paises.map((f) => `<path d="${p.d(f.geometry)}" fill="${f.properties.codigo === 'BRA' ? '#f59e0b' : '#cbd5e1'}" stroke="#64748b" stroke-width="0.4"/>`).join(''));

const pontosSvg = (p, rotulos) => pontos.map((f) => {
  const [x, y] = p.ponto(f.geometry.coordinates);
  return `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="4" fill="#fff" stroke="#dc2626" stroke-width="2"/>` +
    (rotulos ? `<text x="${(x + 7).toFixed(1)}" y="${(y + 4).toFixed(1)}" font-family="Arial, sans-serif" font-size="12" fill="#111">${esc(`${f.properties.nome} · km ${String(f.properties.km_desde_inicio).replace('.', ',')}`)}</text>` : '');
}).join('');

const p2 = painel(`brasil-ufs.topo.json (27 UFs) + rodovias-federais.topo.json + rota · ${d3 ? 'd3.geoMercator' : 'equirretangular'}`, W, 1000, fc(contorno), 'brasil', (p) =>
  ufs.map((f) => `<path d="${p.d(f.geometry)}" fill="#f8fafc" stroke="#94a3b8" stroke-width="0.8"/>`).join('') +
  contorno.map((f) => `<path d="${p.d(f.geometry)}" fill="none" stroke="#334155" stroke-width="1.4"/>`).join('') +
  ['leito_natural', 'implantada', 'pavimentada', 'duplicada'].map((s) => vias.filter((f) => f.properties.situacao === s)
    .map((f) => `<path d="${p.d(f.geometry)}" fill="none" stroke="${cor[s]}" stroke-width="${s === 'duplicada' ? 1.2 : 0.7}"/>`).join('')).join('') +
  `<path d="${p.d(linhas[0].geometry)}" fill="none" stroke="#dc2626" stroke-width="3"/>` + pontosSvg(p, false) +
  ufs.map((f) => { const c = d3 ? d3.geoCentroid(f) : null; if (!c) return ''; const [x, y] = p.ponto(c); return `<text x="${x.toFixed(0)}" y="${y.toFixed(0)}" font-family="Arial, sans-serif" font-size="11" fill="#475569" text-anchor="middle">${f.properties.sigla}</text>`; }).join(''));

// Contornos municipais do IBGE baixados pelo gerador (se estiverem no cache), para ver início e fim da rota.
const municipios = [];
for (const [codigo, nome] of [[3550308, 'São Paulo'], [3526209, 'Juquitiba'], [3542602, 'Registro'], [4106902, 'Curitiba']]) {
  try {
    const g = JSON.parse(readFileSync(join(CACHE, `ibge-municipio-${codigo}-2022.geojson`), 'utf8'));
    municipios.push({ nome, geometry: g.features[0].geometry });
  } catch { /* sem cache: painel sai sem contornos municipais */ }
}
const corredorFit = fc([linhas[0]]);
const p3 = painel(`Corredor BR-116 SP -> PR · rota ${linhas[0].properties.comprimento_km} km (${linha.length} vértices, vermelho fino) sobre malha SNV (cinza grosso), UFs (tracejado) e municípios IBGE (verde)`, W, 820, corredorFit, 'corredor', (p) =>
  ufs.filter((f) => ['SP', 'PR', 'SC', 'MG', 'RJ'].includes(f.properties.sigla)).map((f) => `<path d="${p.d(f.geometry)}" fill="#f8fafc" stroke="#64748b" stroke-width="1.2" stroke-dasharray="6 3"/>`).join('') +
  // Só contorno: o GeoJSON bruto da API do IBGE vem com anéis anti-horários (RFC 7946) e o d3 preencheria o globo todo.
  municipios.map((m) => `<path d="${p.d(m.geometry)}" fill="none" stroke="#15803d" stroke-width="1.2"/>`).join('') +
  ['leito_natural', 'implantada', 'pavimentada', 'duplicada'].map((s) => vias.filter((f) => f.properties.situacao === s)
    .map((f) => `<path d="${p.d(f.geometry)}" fill="none" stroke="${cor[s]}" stroke-width="${s === 'duplicada' ? 6 : 4}" opacity="0.45"/>`).join('')).join('') +
  `<path d="${p.d(linhas[0].geometry)}" fill="none" stroke="#dc2626" stroke-width="1.6"/>` + pontosSvg(p, true), [40, 40, 190, 30]);

const svg = `<svg width="${W}" height="${520 + 1000 + 820}" viewBox="0 0 ${W} ${520 + 1000 + 820}" xmlns="http://www.w3.org/2000/svg">
<rect width="100%" height="100%" fill="#ffffff"/><g>${p1}</g><g transform="translate(0,520)">${p2}</g><g transform="translate(0,1520)">${p3}</g></svg>`;
const arqSvg = join(CACHE, 'teste.svg');
writeFileSync(arqSvg, svg);
console.log(`\nTeste visual: ${arqSvg}`);

// PNG: ImageMagick se estiver no PATH; senão @resvg/resvg-js, num processo separado (o resvg 2.6 pode abortar).
const arqPng = join(CACHE, 'teste.png');
let png = spawnSync('magick', [arqSvg, arqPng], { stdio: 'ignore' }).status === 0;
if (!png) {
  const codigo = `import('@resvg/resvg-js').then(({ Resvg }) => { const fs = require('node:fs');
    fs.writeFileSync(process.argv[2], new Resvg(fs.readFileSync(process.argv[1], 'utf8'), { fitTo: { mode: 'width', value: ${W} } }).render().asPng()); })`;
  png = spawnSync(process.execPath, ['-e', codigo, arqSvg, arqPng], { cwd: AQUI, stdio: 'ignore' }).status === 0;
}
console.log(png ? `PNG: ${arqPng}` : 'PNG não gerado (sem ImageMagick nem @resvg/resvg-js); abra o SVG no navegador.');

console.log(falhas.length ? `\n${falhas.length} checagem(ns) falharam.` : '\nTodas as checagens passaram.');
process.exit(falhas.length ? 1 : 0);
