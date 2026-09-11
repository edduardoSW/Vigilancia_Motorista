// SITE-06 · a noite do mapa-múndi vem da posição real do Sol (fórmulas da NOAA), conferida em datas conhecidas.
import assert from "node:assert/strict";
import { test } from "node:test";
import { antipodaSolar, pontoSubsolar } from "../../src/lib/solar.ts";

const casos = [
  ["2026-06-21T12:00:00Z", 23.44, 0.4, "solstício de junho"],
  ["2026-12-21T12:00:00Z", -23.44, -0.6, "solstício de dezembro"],
  ["2026-03-20T12:00:00Z", 0, 1.9, "equinócio de março"],
];

for (const [iso, lat, lon, nome] of casos) {
  test(`SITE-06 ponto subsolar no ${nome}`, () => {
    const p = pontoSubsolar(new Date(iso));
    assert.ok(Math.abs(p.latitude - lat) < 0.6, `latitude ${p.latitude}`);
    assert.ok(Math.abs(p.longitude - lon) < 0.6, `longitude ${p.longitude}`);
  });
}

test("SITE-06 a noite fica do lado oposto ao Sol", () => {
  const data = new Date("2026-09-11T15:00:00Z");
  const sol = pontoSubsolar(data);
  const [lon, lat] = antipodaSolar(data);
  const diferenca = Math.abs(((lon - sol.longitude + 540) % 360) - 180);
  assert.ok(Math.abs(diferenca - 180) < 1e-9);
  assert.ok(Math.abs(lat + sol.latitude) < 1e-9);
});
