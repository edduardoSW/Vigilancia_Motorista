// DPA-05 (spec 020) · conferência da área de download com o Edge sem janela, pelo protocolo DevTools.
// Precisa do site rodando (next start) e confere contra o que existe em public/downloads: o que está lá mostra "Baixar"
// e o tamanho; o que falta mostra "Em preparação". Baixa o .zip do painel pelo botão e compara o SHA-256.
// A sessão da área do PIN é gravada direto no localStorage com o hash público do código; o PIN não é usado.
// Uso (na pasta site): SITE_URL=http://127.0.0.1:3207 node scripts/testes/area-de-download.mjs [pasta das capturas]
import { spawn } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";

const site = path.join(import.meta.dirname, "..", "..");
const base = process.env.SITE_URL ?? "http://localhost:3000";
const capturas = process.argv[2] ? path.resolve(process.argv[2]) : null;
if (process.env.NEXT_PUBLIC_ROTAGUARD_DOWNLOADS_BASE) {
  console.error("Esta conferência vale para os arquivos em public/downloads; tire NEXT_PUBLIC_ROTAGUARD_DOWNLOADS_BASE.");
  process.exit(2);
}
const importar = (...partes) => import(pathToFileURL(path.join(site, ...partes)).href);
const { downloads } = await importar("src", "content", "downloads.ts");
const { ACCESS_KEY, ACCESS_TTL, PIN_CONFIG } = await importar("src", "lib", "acesso-local.ts");

const local = (d) => path.join(site, "public", "downloads", d.arquivo);
const sha256 = (arquivo) => createHash("sha256").update(readFileSync(arquivo)).digest("hex");
const esperado = (d) => existsSync(local(d))
  ? { baixar: true, texto: `${d.arquivo} · ${Math.round(statSync(local(d)).size / 1_048_576)} MB` }
  : { baixar: false, texto: d.arquivo };
const painel = downloads.find((d) => d.app === "painel");

const edge = ["C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe", "C:/Program Files/Microsoft/Edge/Application/msedge.exe"].find(existsSync);
const porta = 9300 + Math.floor(Math.random() * 300);
const pastaDownload = mkdtempSync(path.join(tmpdir(), "rg-download-"));
const navegador = spawn(edge, ["--headless=new", "--no-first-run", `--remote-debugging-port=${porta}`, `--user-data-dir=${mkdtempSync(path.join(tmpdir(), "rg-020-"))}`, "about:blank"], { stdio: "ignore", windowsHide: true });
const espera = (ms) => new Promise((r) => setTimeout(r, ms));

let ws, seq = 0;
const pendentes = new Map(), errosJs = [], eventos = [];
const cdp = (method, params = {}) => new Promise((resolve, reject) => {
  const id = ++seq;
  const t = setTimeout(() => { pendentes.delete(id); reject(new Error("CDP timeout: " + method)); }, 30000);
  pendentes.set(id, { resolve, reject, t });
  ws.send(JSON.stringify({ id, method, params }));
});
async function js(expression) {
  const r = await cdp("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description ?? r.exceptionDetails.text);
  return r.result.value;
}
async function ate(expression, vezes = 150) {
  for (let i = 0; i < vezes; i++) { if (await js(expression)) return; await espera(100); }
  throw new Error("Não chegou: " + expression);
}
const tela = (largura, altura = 900, escala = 1) => cdp("Emulation.setDeviceMetricsOverride", { width: largura, height: altura, deviceScaleFactor: escala, mobile: largura < 640 });
const resultados = [];
function confere(nome, ok, detalhe = "") {
  resultados.push(ok);
  console.log(`${ok ? "PASS" : "FAIL"} ${nome}${ok || !detalhe ? "" : " · " + detalhe}`);
}

const sessao = `(()=>{const agora=Date.now();localStorage.setItem(${JSON.stringify(ACCESS_KEY)},JSON.stringify({version:1,credential:${JSON.stringify(PIN_CONFIG.hash)},createdAt:agora,expiresAt:agora+${ACCESS_TTL}}));return true})()`;
const lerItens = `[...document.querySelectorAll(".download-list>li")].map(li=>({app:li.closest(".download-group").getAttribute("aria-labelledby").replace("download-",""),plataforma:li.querySelector("h3").innerText.toLowerCase(),texto:li.querySelector("small").innerText,href:li.querySelector("a")?.getAttribute("href")??null,desligado:li.querySelector("span.action")?.getAttribute("aria-disabled")??null}))`;
// A página terminou de conferir os arquivos quando todo item tem tamanho ou está em preparação.
const conferido = `document.querySelectorAll(".download-list>li").length===${downloads.length} && [...document.querySelectorAll(".download-list>li")].every(li=>/MB/.test(li.querySelector("small").innerText)||li.querySelector("span.action"))`;
async function abrir(locale) {
  await cdp("Page.navigate", { url: `${base}/${locale}/app` });
  await ate(`location.pathname==="/${locale}/app" && !!document.querySelector(".download-group")`);
  await ate(conferido);
}

try {
  let alvo;
  for (let i = 0; i < 60 && !alvo; i++) {
    try { alvo = (await (await fetch(`http://127.0.0.1:${porta}/json/list`)).json()).find((t) => t.type === "page")?.webSocketDebuggerUrl; } catch {}
    if (!alvo) await espera(150);
  }
  ws = new WebSocket(alvo);
  await new Promise((r) => (ws.onopen = r));
  ws.onmessage = (e) => {
    const m = JSON.parse(e.data);
    if (m.id && pendentes.has(m.id)) { const p = pendentes.get(m.id); pendentes.delete(m.id); clearTimeout(p.t); if (m.error) p.reject(new Error(m.error.message)); else p.resolve(m.result); }
    else if (m.method === "Runtime.exceptionThrown") errosJs.push(m.params.exceptionDetails.exception?.description ?? m.params.exceptionDetails.text);
    else if (m.method) eventos.push(m);
  };
  await cdp("Page.enable"); await cdp("Runtime.enable"); await tela(1440);

  await cdp("Page.navigate", { url: `${base}/pt-BR/app` });
  await ate(`location.pathname==="/pt-BR/entrar"`);
  confere("sem sessão, /app manda para o PIN", true);
  await js(sessao);

  for (const locale of ["pt-BR", "en", "es", "fr", "zh-CN"]) {
    await tela(1440);
    await abrir(locale);
    const titulos = await js(`[...document.querySelectorAll(".download-group")].map(g=>g.getAttribute("aria-labelledby"))`);
    confere(`${locale}: blocos na ordem painel → teste`, titulos.join() === "download-painel,download-teste", titulos.join());
    const itens = await js(lerItens);
    downloads.forEach((d, i) => {
      const e = esperado(d), item = itens[i] ?? {};
      const ok = item.app === d.app && item.plataforma === d.plataforma && item.texto === e.texto &&
        (e.baixar ? item.href === d.url && item.desligado === null : item.href === null && item.desligado === "true");
      confere(`${locale}: ${d.app} ${d.plataforma} ${e.baixar ? "com Baixar e tamanho" : "em preparação"}`, ok, JSON.stringify(item));
    });
    confere(`${locale}: sem tradução ausente e sem macOS`, await js(`!document.body.innerText.includes("MISSING_MESSAGE") && !/macOS/.test(document.body.innerText)`));
    for (const largura of [320, 390, 768, 1440]) {
      await tela(largura);
      await espera(120);
      const medida = await js(`({rolagem:document.documentElement.scrollWidth,tela:window.innerWidth,fora:[...document.querySelectorAll(".download-group *")].filter(e=>e.getBoundingClientRect().right>window.innerWidth+0.5).length})`);
      confere(`${locale}: sem rolagem lateral em ${largura}px`, medida.rolagem <= medida.tela && medida.fora === 0, JSON.stringify(medida));
    }
  }

  await tela(1440);
  await cdp("Page.navigate", { url: `${base}/pt-BR` });
  await ate(`location.pathname==="/pt-BR" && document.readyState==="complete"`);
  confere("FAQ da página inicial cita o painel para Windows", await js(`document.body.textContent.includes("painel da empresa para Windows")`));

  if (existsSync(local(painel))) {
    await cdp("Browser.setDownloadBehavior", { behavior: "allow", downloadPath: pastaDownload, eventsEnabled: true });
    await abrir("pt-BR");
    await js(`document.querySelector('a[data-app="painel"]').click(),true`);
    let fim;
    for (let i = 0; i < 600 && !fim; i++) {
      fim = eventos.find((m) => m.method === "Browser.downloadProgress" && m.params.state !== "inProgress");
      if (!fim) await espera(100);
    }
    const baixado = path.join(pastaDownload, painel.arquivo);
    confere("Baixar do painel baixa o .zip com o mesmo SHA-256 de public/downloads",
      fim?.params.state === "completed" && existsSync(baixado) && sha256(baixado) === sha256(local(painel)),
      `${fim?.params.state} ${readdirSync(pastaDownload).join(",")}`);
  } else {
    confere(`${painel.arquivo} em public/downloads (copie de build/painel/pacotes)`, false);
  }

  if (capturas) {
    mkdirSync(capturas, { recursive: true });
    for (const [nome, largura, altura, escala] of [["computador", 1440, 900, 1], ["celular", 390, 844, 2]]) {
      await tela(largura, altura, escala);
      await abrir("pt-BR");
      await js(`document.fonts.ready.then(()=>true)`);
      await espera(400);
      const total = await js(`Math.ceil(document.documentElement.scrollHeight)`);
      const { data } = await cdp("Page.captureScreenshot", { format: "png", captureBeyondViewport: true, clip: { x: 0, y: 0, width: largura, height: total, scale: 1 } });
      writeFileSync(path.join(capturas, `area-de-download-${nome}.png`), Buffer.from(data, "base64"));
    }
    console.log("capturas em", capturas);
  }
  confere("sem erro de JavaScript", errosJs.length === 0, errosJs.join(" | "));
} catch (erro) {
  confere("roteiro terminou", false, erro.stack);
} finally {
  ws?.close();
  navegador.kill();
}
const falhas = resultados.filter((ok) => !ok).length;
console.log(`\n${resultados.length - falhas} de ${resultados.length} conferências passaram`);
process.exitCode = falhas ? 1 : 0;
