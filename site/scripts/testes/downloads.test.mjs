// APT-11 e APT-23 (spec 010) · os arquivos oferecidos no site são exatamente os que o build do app de teste gera,
// servidos pelo próprio site em /downloads (public/downloads, fora do git). Só Windows e Linux: sem Mac.
// DPA-01 a DPA-04 (spec 020) · o painel entra na mesma área, só com o .zip do Windows que o build do painel gera.
import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";
import { pathToFileURL } from "node:url";

const raiz = path.join(import.meta.dirname, "..", "..", "..");
const ler = (...partes) => readFileSync(path.join(raiz, ...partes), "utf8");
const mensagens = (locale) => JSON.parse(ler("site", "messages", `${locale}.json`));
const locales = ["pt-BR", "en", "es", "fr", "zh-CN"];

// O Node 22.18+ lê TypeScript sem compilar; downloads.ts só usa tipos que podem ser apagados.
delete process.env.NEXT_PUBLIC_ROTAGUARD_DOWNLOADS_BASE;
const { downloads } = await import(pathToFileURL(path.join(raiz, "site", "src", "content", "downloads.ts")).href);
const doApp = (app) => downloads.filter((d) => d.app === app);

const esperados = ["RotaGuard-Script-windows-x64.zip", "RotaGuard-Script-linux-x86_64.tar.gz"];
const painelWindows = "RotaGuard-Painel-windows-x64-setup.exe";
const painelPortatil = "RotaGuard-Painel-windows-x64.zip";
const scriptWindows = "RotaGuard-Script-windows-x64-setup.exe";

test("DPA-01 site oferece o instalador do painel em /downloads, com o .zip portátil ao lado", () => {
  const painel = doApp("painel");
  assert.deepEqual(painel.map((d) => [d.plataforma, d.arquivo, d.url]), [["windows", painelWindows, `/downloads/${painelWindows}`]]);
  assert.deepEqual(painel[0].portatil, {arquivo: painelPortatil, url: `/downloads/${painelPortatil}`});
});

test("DPA-01 build.py do painel gera o mesmo nome", () => {
  const build = ler("implantacao", "painel", "build.py");
  assert.match(build, /^NOME = "RotaGuard-Painel"$/m);
  assert.match(build, /return f"\{NOME\}-\{alvo\(\)\}\.zip"/);
  assert.match(build, /return f"\{NOME\}-\{alvo\(\)\}-setup\.exe"/);
  assert.match(ler("implantacao", "painel", "rotaguard-painel.iss"), /^OutputBaseFilename=RotaGuard-Painel-windows-x64-setup$/m);
  assert.match(ler("implantacao", "app-teste", "build.py"), /return "windows-x64" if maquina in \("amd64", "x86_64"\)/);
});

test("DPA-02 painel só Windows; app de teste continua com Windows e Linux", () => {
  assert.deepEqual(doApp("painel").map((d) => d.plataforma), ["windows"]);
  assert.deepEqual(doApp("teste").map((d) => [d.plataforma, d.arquivo, d.portatil?.arquivo]),
    [["windows", scriptWindows, esperados[0]], ["linux", esperados[1], undefined]]);
});

test("DPA-03 painel antes do teste e um endereço por arquivo", () => {
  assert.deepEqual([...new Set(downloads.map((d) => d.app))], ["painel", "teste"]);
  const urls = downloads.flatMap((d) => d.portatil ? [d.url, d.portatil.url] : [d.url]);
  assert.equal(new Set(urls).size, urls.length, "dois itens com o mesmo endereço");
  const area = ler("site", "src", "components", "download-area.tsx");
  assert.match(area, /situacao\[d\.url\]/, "a situação do arquivo precisa ser guardada pelo endereço");
  assert.doesNotMatch(area, /situacao\[d\.plataforma\]/, "situação por plataforma mistura o Windows dos dois apps");
});

test("DPA-04 bloco do painel nos 5 idiomas, com o primeiro uso", () => {
  for (const locale of locales) {
    const app = mensagens(locale).app;
    for (const chave of ["painelTitulo", "painelTexto", "painelWindows", "painelInstrucoes", "testeTitulo", "portatil"]) {
      assert.ok(typeof app[chave] === "string" && app[chave].trim(), `${locale}: app.${chave} vazio`);
    }
    assert.match(app.painelWindows, /RotaGuardPainel\.exe/, `${locale}: Windows do painel sem o nome do .exe`);
    assert.match(app.painelInstrucoes, /Ver demonstração/, `${locale}: primeiro uso sem o botão da tela do painel`);
    assert.match(app.painelInstrucoes, /WebView2/, `${locale}: primeiro uso sem o aviso do WebView2`);
  }
});

test("DPA-04 português não diz mais que o painel está em preparação e o FAQ cita o painel", () => {
  const pt = mensagens("pt-BR");
  assert.doesNotMatch(JSON.stringify(pt.app), /Painel da empresa e app para celular: em preparação/);
  assert.match(pt.app.depois, /Linux/);
  assert.match(pt.home.answer4, /painel da empresa para Windows/i);
  assert.doesNotMatch(pt.home.answer4, /painel da empresa e a versão para celular estão em preparação/i);
});

test("APT-11 site oferece Windows e Linux", () => {
  const downloads = ler("site", "src", "content", "downloads.ts");
  for (const nome of esperados) assert.ok(downloads.includes(nome), `site sem ${nome}`);
});

test("APT-11 build.py gera os mesmos nomes", () => {
  const build = ler("implantacao", "app-teste", "build.py");
  for (const nome of [...esperados, "RotaGuard-Script-windows-x64-setup.exe"]) {
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
  assert.ok(downloads.every((d) => d.url.startsWith("/downloads/") && (!d.portatil || d.portatil.url.startsWith("/downloads/"))));
  assert.match(ler("site", "src", "content", "downloads.ts"), /BASE_PADRAO = "\/downloads"/);
  assert.match(ler("site", ".gitignore"), /^public\/downloads\/$/m);
});

test("APT-23 sem Mac: nada de macOS no site, no build, no workflow nem nas mensagens", () => {
  assert.doesNotMatch(ler("site", "src", "content", "downloads.ts"), /macos/i);
  assert.doesNotMatch(ler("site", "src", "components", "download-area.tsx"), /macos/i);
  assert.doesNotMatch(ler("implantacao", "app-teste", "build.py"), /macos-|ditto|\.app"/);
  assert.doesNotMatch(ler("implantacao", "app-teste", "rotaguard-script.spec"), /BUNDLE|Info\.plist|darwin/);
  assert.doesNotMatch(ler(".github", "workflows", "app-teste.yml"), /macos/i);
  const pasta = path.join(raiz, "site", "messages");
  for (const arquivo of readdirSync(pasta).filter((nome) => nome.endsWith(".json"))) {
    const mensagens = JSON.parse(readFileSync(path.join(pasta, arquivo), "utf8"));
    assert.ok(!("macos" in mensagens.app), `${arquivo}: app.macos ainda existe`);
    assert.doesNotMatch(JSON.stringify(mensagens.app) + mensagens.home.answer4, /macOS/, `${arquivo} ainda cita macOS`);
  }
});

// NOM-01 (spec 031): o app de teste se chama RotaGuard Script; o nome antigo não aparece em nenhum idioma.
test("NOM-01 nenhum texto do site diz RotaGuard Teste", () => {
  for (const idioma of ["pt-BR", "en", "es", "fr", "zh-CN"]) {
    const texto = readFileSync(new URL(`../../messages/${idioma}.json`, import.meta.url), "utf8");
    assert.doesNotMatch(texto, /RotaGuard Teste|RotaGuardTeste|RotaGuard-Teste/, idioma);
    assert.match(texto, /RotaGuard Script/, idioma);
  }
});
