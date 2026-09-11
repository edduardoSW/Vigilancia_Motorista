// SITE-03 · os 5 idiomas têm exatamente as mesmas chaves do português e nenhum texto ficou sem tradução.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";

const pasta = path.join(import.meta.dirname, "..", "..", "messages");
const ler = (locale) => JSON.parse(readFileSync(path.join(pasta, `${locale}.json`), "utf8"));

function achatar(obj, prefixo = "") {
  return Object.entries(obj).flatMap(([k, v]) =>
    v && typeof v === "object" ? achatar(v, `${prefixo}${k}.`) : [[`${prefixo}${k}`, String(v)]]
  );
}

const base = new Map(achatar(ler("pt-BR")));
// Textos que são iguais em qualquer idioma (nomes próprios, horas, códigos).
const iguaisPermitidos = /^(RotaGuard|\d{2}:\d{2}|[\d\s:→.,h]+|BR-116.*|Carreta 12|PERCLOS|CTB.*|© 2026 RotaGuard|Windows|macOS|Linux|Android|PIN)$/;

for (const locale of ["en", "es", "fr", "zh-CN"]) {
  test(`SITE-03 ${locale}: mesmas chaves que pt-BR`, () => {
    const outro = new Map(achatar(ler(locale)));
    const faltando = [...base.keys()].filter((k) => !outro.has(k));
    const sobrando = [...outro.keys()].filter((k) => !base.has(k));
    assert.deepEqual(faltando, [], `faltam chaves em ${locale}`);
    assert.deepEqual(sobrando, [], `chaves a mais em ${locale}`);
  });

  test(`SITE-03 ${locale}: nada copiado do português sem traduzir`, () => {
    const outro = new Map(achatar(ler(locale)));
    const copiados = [...base.entries()]
      .filter(([k, v]) => outro.get(k) === v && !iguaisPermitidos.test(v.trim()))
      .map(([k]) => k);
    assert.deepEqual(copiados, [], `textos iguais ao pt-BR em ${locale}`);
  });

  test(`SITE-03 ${locale}: placeholders ICU preservados`, () => {
    const outro = new Map(achatar(ler(locale)));
    const errados = [...base.entries()]
      .filter(([k, v]) => {
        const esperados = (v.match(/\{\w+\}/g) ?? []).sort().join();
        const obtidos = ((outro.get(k) ?? "").match(/\{\w+\}/g) ?? []).sort().join();
        return esperados !== obtidos;
      })
      .map(([k]) => k);
    assert.deepEqual(errados, [], `placeholders diferentes em ${locale}`);
  });
}
