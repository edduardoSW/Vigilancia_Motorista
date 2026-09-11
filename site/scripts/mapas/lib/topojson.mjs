// Decodificador mínimo de TopoJSON para a conferência (o site usa topojson-client; aqui evitamos dependência).

export function arcosDecodificados(topo) {
  const t = topo.transform;
  return topo.arcs.map((arco) => {
    let x = 0, y = 0;
    return arco.map((p) => {
      if (!t) return [p[0], p[1]];
      x += p[0];
      y += p[1];
      return [x * t.scale[0] + t.translate[0], y * t.scale[1] + t.translate[1]];
    });
  });
}

function montarLinha(arcos, indices) {
  const coords = [];
  for (const idx of indices) {
    const arco = idx < 0 ? arcos[~idx].slice().reverse() : arcos[idx];
    arco.forEach((p, k) => { if (k > 0 || coords.length === 0) coords.push(p); });
  }
  return coords;
}

function geometria(arcos, g, transform) {
  const ponto = (p) => (transform ? [p[0] * transform.scale[0] + transform.translate[0], p[1] * transform.scale[1] + transform.translate[1]] : p);
  switch (g.type) {
    case 'Point': return { type: 'Point', coordinates: ponto(g.coordinates) };
    case 'MultiPoint': return { type: 'MultiPoint', coordinates: g.coordinates.map(ponto) };
    case 'LineString': return { type: 'LineString', coordinates: montarLinha(arcos, g.arcs) };
    case 'MultiLineString': return { type: 'MultiLineString', coordinates: g.arcs.map((l) => montarLinha(arcos, l)) };
    case 'Polygon': return { type: 'Polygon', coordinates: g.arcs.map((r) => montarLinha(arcos, r)) };
    case 'MultiPolygon': return { type: 'MultiPolygon', coordinates: g.arcs.map((p) => p.map((r) => montarLinha(arcos, r))) };
    case null: case undefined: return null;
    default: throw new Error(`Tipo TopoJSON não suportado: ${g.type}`);
  }
}

/** Converte um objeto da topologia em array de feições GeoJSON. */
export function feicoes(topo, nomeObjeto) {
  const arcos = arcosDecodificados(topo);
  const obj = topo.objects[nomeObjeto];
  if (!obj) throw new Error(`Objeto "${nomeObjeto}" não existe (há: ${Object.keys(topo.objects).join(', ')})`);
  const geoms = obj.type === 'GeometryCollection' ? obj.geometries : [obj];
  return geoms.map((g) => ({ type: 'Feature', properties: g.properties || {}, geometry: geometria(arcos, g, topo.transform) }));
}

/** Índices de arcos únicos usados por um objeto (equivale ao que topojson.mesh desenha). */
export function arcosDoObjeto(topo, nomeObjeto) {
  const usados = new Set();
  const visitar = (a) => (Array.isArray(a) ? a.forEach(visitar) : usados.add(a < 0 ? ~a : a));
  const obj = topo.objects[nomeObjeto];
  const geoms = obj.type === 'GeometryCollection' ? obj.geometries : [obj];
  for (const g of geoms) if (g.arcs) visitar(g.arcs);
  return usados;
}
