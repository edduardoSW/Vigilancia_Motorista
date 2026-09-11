// SITE-07 · no HTML gerado pelo build: nenhum link morto (href="#"), idioma certo no <html>, hreflang dos 5 idiomas
// e a página sai com noindex enquanto for prévia. Rodar depois de `npm run build`.
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";

const app = path.join(import.meta.dirname, "..", "..", ".next", "server", "app");
const paginas = { "pt-BR": "pt-BR.html", en: "en.html", es: "es.html", fr: "fr.html", "zh-CN": "zh-CN.html" };

for (const [locale, arquivo] of Object.entries(paginas)) {
  const caminho = path.join(app, arquivo);
  test(`SITE-07 ${locale}: HTML existe no build`, { skip: !existsSync(path.join(app)) && "sem build" }, () => {
    assert.ok(existsSync(caminho), `falta ${caminho}`);
  });

  test(`SITE-07 ${locale}: sem href="#" e com lang e hreflang`, { skip: !existsSync(caminho) && "sem build" }, () => {
    const html = readFileSync(caminho, "utf8");
    assert.equal(/href="#"/.test(html), false, 'link morto href="#"');
    assert.match(html, new RegExp(`<html[^>]*lang="${locale}"`));
    for (const lang of ["pt-BR", "en", "es", "fr", "zh-CN", "x-default"]) {
      assert.match(html, new RegExp(`hreflang="${lang}"`, "i"), `sem hreflang ${lang}`);
    }
    assert.match(html, /name="robots" content="noindex/);
  });

  // SITE-08 · peso: o HTML inicial (com o payload do React) fica abaixo de 700 KB, mesmo com os mapas desenhados.
  test(`SITE-08 ${locale}: HTML abaixo de 700 KB`, { skip: !existsSync(caminho) && "sem build" }, () => {
    const kb = readFileSync(caminho).length / 1024;
    assert.ok(kb < 700, `HTML com ${Math.round(kb)} KB`);
  });
}
