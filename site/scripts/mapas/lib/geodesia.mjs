// Cálculos geodésicos e geométricos usados na geração e na conferência dos mapas.

const A = 6378137.0; // semieixo maior do WGS 84 (m)
const F = 1 / 298.257223563; // achatamento do WGS 84
const B = A * (1 - F);
const RAD = Math.PI / 180;

/**
 * Distância geodésica entre dois pontos no elipsoide WGS 84, pela fórmula inversa de Vincenty (1975).
 * Precisão submilimétrica para os trechos curtos usados aqui. Devolve metros.
 */
export function distanciaVincenty(lon1, lat1, lon2, lat2) {
  if (lon1 === lon2 && lat1 === lat2) return 0;
  const L = (lon2 - lon1) * RAD;
  const U1 = Math.atan((1 - F) * Math.tan(lat1 * RAD));
  const U2 = Math.atan((1 - F) * Math.tan(lat2 * RAD));
  const sinU1 = Math.sin(U1), cosU1 = Math.cos(U1);
  const sinU2 = Math.sin(U2), cosU2 = Math.cos(U2);
  let lambda = L;
  let iter = 0;
  let sinSigma, cosSigma, sigma, cos2Alpha, cos2SigmaM;
  for (;;) {
    const sinLambda = Math.sin(lambda), cosLambda = Math.cos(lambda);
    sinSigma = Math.sqrt((cosU2 * sinLambda) ** 2 + (cosU1 * sinU2 - sinU1 * cosU2 * cosLambda) ** 2);
    if (sinSigma === 0) return 0;
    cosSigma = sinU1 * sinU2 + cosU1 * cosU2 * cosLambda;
    sigma = Math.atan2(sinSigma, cosSigma);
    const sinAlpha = (cosU1 * cosU2 * sinLambda) / sinSigma;
    cos2Alpha = 1 - sinAlpha * sinAlpha;
    cos2SigmaM = cos2Alpha !== 0 ? cosSigma - (2 * sinU1 * sinU2) / cos2Alpha : 0;
    const C = (F / 16) * cos2Alpha * (4 + F * (4 - 3 * cos2Alpha));
    const lambdaAnt = lambda;
    lambda = L + (1 - C) * F * sinAlpha * (sigma + C * sinSigma * (cos2SigmaM + C * cosSigma * (-1 + 2 * cos2SigmaM ** 2)));
    if (Math.abs(lambda - lambdaAnt) < 1e-12) break;
    if (++iter > 200) throw new Error('Vincenty não convergiu (pontos quase antípodas)');
  }
  const u2 = (cos2Alpha * (A * A - B * B)) / (B * B);
  const Acoef = 1 + (u2 / 16384) * (4096 + u2 * (-768 + u2 * (320 - 175 * u2)));
  const Bcoef = (u2 / 1024) * (256 + u2 * (-128 + u2 * (74 - 47 * u2)));
  const deltaSigma = Bcoef * sinSigma * (cos2SigmaM + (Bcoef / 4) * (cosSigma * (-1 + 2 * cos2SigmaM ** 2) -
    (Bcoef / 6) * cos2SigmaM * (-3 + 4 * sinSigma ** 2) * (-3 + 4 * cos2SigmaM ** 2)));
  return B * Acoef * (sigma - deltaSigma);
}

/** Comprimento geodésico (m) de uma linha [[lon, lat], ...]. */
export function comprimentoLinha(coords) {
  let total = 0;
  for (let i = 1; i < coords.length; i++) {
    total += distanciaVincenty(coords[i - 1][0], coords[i - 1][1], coords[i][0], coords[i][1]);
  }
  return total;
}

/** Projeção plana local (m) em torno de uma latitude de referência; boa para trechos de até ~100 km. */
function projetorLocal(lat0) {
  const kx = A * RAD * Math.cos(lat0 * RAD);
  const ky = A * RAD;
  return ([lon, lat]) => [lon * kx, lat * ky];
}

function distPontoSegmento2(p, a, b) {
  const dx = b[0] - a[0], dy = b[1] - a[1];
  const len2 = dx * dx + dy * dy;
  let t = len2 === 0 ? 0 : ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / len2;
  t = Math.max(0, Math.min(1, t));
  const x = a[0] + t * dx - p[0], y = a[1] + t * dy - p[1];
  return x * x + y * y;
}

/**
 * Douglas-Peucker com tolerância em metros. Mantém o primeiro e o último vértice,
 * então simplificar trecho a trecho preserva os nós entre trechos.
 */
export function simplificarDP(coords, toleranciaM) {
  if (coords.length <= 2) return coords.slice();
  const latMedia = coords.reduce((s, c) => s + c[1], 0) / coords.length;
  const proj = projetorLocal(latMedia);
  const xy = coords.map(proj);
  const manter = new Uint8Array(coords.length);
  manter[0] = 1;
  manter[coords.length - 1] = 1;
  const pilha = [[0, coords.length - 1]];
  const tol2 = toleranciaM * toleranciaM;
  while (pilha.length) {
    const [i, j] = pilha.pop();
    let maxD = -1, idx = -1;
    for (let k = i + 1; k < j; k++) {
      const d = distPontoSegmento2(xy[k], xy[i], xy[j]);
      if (d > maxD) { maxD = d; idx = k; }
    }
    if (maxD > tol2) {
      manter[idx] = 1;
      pilha.push([i, idx], [idx, j]);
    }
  }
  return coords.filter((_, k) => manter[k]);
}

/** Distância (m) de um ponto ao segmento mais próximo de uma linha, em projeção local. */
export function distanciaPontoLinhaM(ponto, coords) {
  const proj = projetorLocal(ponto[1]);
  const p = proj(ponto);
  let min = Infinity;
  for (let i = 1; i < coords.length; i++) {
    min = Math.min(min, distPontoSegmento2(p, proj(coords[i - 1]), proj(coords[i])));
  }
  return Math.sqrt(min);
}

/** Ponto dentro de polígono (anel externo + buracos), por paridade de cruzamentos. */
function dentroDoAnel(pt, anel) {
  let dentro = false;
  for (let i = 0, j = anel.length - 1; i < anel.length; j = i++) {
    const [xi, yi] = anel[i], [xj, yj] = anel[j];
    if ((yi > pt[1]) !== (yj > pt[1]) && pt[0] < ((xj - xi) * (pt[1] - yi)) / (yj - yi) + xi) dentro = !dentro;
  }
  return dentro;
}

export function pontoNaGeometria(pt, geom) {
  const polis = geom.type === 'Polygon' ? [geom.coordinates] : geom.type === 'MultiPolygon' ? geom.coordinates : [];
  return polis.some((p) => dentroDoAnel(pt, p[0]) && !p.slice(1).some((b) => dentroDoAnel(pt, b)));
}

/** Distância (m) de um ponto à borda de um polígono ou multipolígono. */
export function distanciaPontoBordaM(pt, geom) {
  const polis = geom.type === 'Polygon' ? [geom.coordinates] : geom.coordinates;
  let min = Infinity;
  for (const p of polis) for (const anel of p) min = Math.min(min, distanciaPontoLinhaM(pt, anel));
  return min;
}

/** Conta autointerseções entre segmentos não adjacentes de uma linha (checagem de "voltas"). */
export function autointersecoes(coords) {
  const lat0 = coords.reduce((s, c) => s + c[1], 0) / coords.length;
  const xy = coords.map(projetorLocal(lat0));
  const segs = [];
  for (let i = 1; i < xy.length; i++) {
    const a = xy[i - 1], b = xy[i];
    segs.push({ i, a, b, minx: Math.min(a[0], b[0]), maxx: Math.max(a[0], b[0]), miny: Math.min(a[1], b[1]), maxy: Math.max(a[1], b[1]) });
  }
  segs.sort((s, t) => s.minx - t.minx);
  const orient = (p, q, r) => Math.sign((q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0]));
  const achados = [];
  for (let m = 0; m < segs.length; m++) {
    const s = segs[m];
    for (let n = m + 1; n < segs.length && segs[n].minx <= s.maxx; n++) {
      const t = segs[n];
      if (Math.abs(s.i - t.i) <= 1) continue;
      if (t.miny > s.maxy || t.maxy < s.miny) continue;
      const o1 = orient(s.a, s.b, t.a), o2 = orient(s.a, s.b, t.b);
      const o3 = orient(t.a, t.b, s.a), o4 = orient(t.a, t.b, s.b);
      if (o1 * o2 < 0 && o3 * o4 < 0) achados.push([Math.min(s.i, t.i), Math.max(s.i, t.i)]);
    }
  }
  return achados;
}
