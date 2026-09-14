// APT-11 e APT-23 (spec 010) · os arquivos oferecidos no site são exatamente os que o build do app de teste gera,
// servidos pelo próprio site em /downloads (public/downloads, fora do git). Só Windows e Linux: sem Mac.
import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";

const raiz = path.join(import.meta.dirname, "..", "..", "..");
const ler = (...partes) => readFileSync(path.join(raiz, ...partes), "utf8");

const esperados = ["RotaGuard-Teste-windows-x64.zip", "RotaGuard-Teste-linux-x86_64.tar.gz"];

test("APT-11 site oferece Windows e Linux", () => {
  const downloads = ler("site", "src", "content", "downloads.ts");
  for (const nome of esperados) assert.ok(downloads.includes(nome), `site sem ${nome}`);
});

test("APT-11 build.py gera os mesmos nomes", () => {
  const build = ler("implantacao", "app-teste", "build.py");
  for (const nome of [...esperados, "RotaGuard-Teste-windows-x64-setup.exe"]) {
    assert.ok(build.includes(nome), `build.py sem ${nome}`);
  }
});

test("APT-11 workflow publica a pasta de pacotes na release das tags teste-v*", () => {
  const workflow = ler(".github", "workflows", "app-teste.yml");
  assert.match(workflow, /teste-v\*/);
  assert.match(workflow, /build\/app-teste\/pacotes/);
  assert.match(workflow, /SHA256SUMS/);
});

test("APT-11 base padrão é o próprio site, com a pasta de downloads fora do git", () => {
  const downloads = ler("site", "src", "content", "downloads.ts");
  assert.match(downloads, /BASE_PADRAO = "\/downloads"/);
  assert.match(ler("site", ".gitignore"), /^public\/downloads\/$/m);
});

test("APT-23 sem Mac: nada de macOS no site, no build, no workflow nem nas mensagens", () => {
  assert.doesNotMatch(ler("site", "src", "content", "downloads.ts"), /macos/i);
  assert.doesNotMatch(ler("site", "src", "components", "download-area.tsx"), /macos/i);
  assert.doesNotMatch(ler("implantacao", "app-teste", "build.py"), /macos-|ditto|\.app"/);
  assert.doesNotMatch(ler("implantacao", "app-teste", "rotaguard-teste.spec"), /BUNDLE|Info\.plist|darwin/);
  assert.doesNotMatch(ler(".github", "workflows", "app-teste.yml"), /macos/i);
  const pasta = path.join(raiz, "site", "messages");
  for (const arquivo of readdirSync(pasta).filter((nome) => nome.endsWith(".json"))) {
    const mensagens = JSON.parse(readFileSync(path.join(pasta, arquivo), "utf8"));
    assert.ok(!("macos" in mensagens.app), `${arquivo}: app.macos ainda existe`);
    assert.doesNotMatch(JSON.stringify(mensagens.app) + mensagens.home.answer4, /macOS/, `${arquivo} ainda cita macOS`);
  }
});
