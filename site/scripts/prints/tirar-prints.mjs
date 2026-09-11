#!/usr/bin/env node
/**
 * Prints de página inteira do site com o Edge ou Chrome sem janela, pelo protocolo DevTools (sem Playwright).
 * A viewport fica em tamanho de tela real (1440×900 e 400×850), então 100svh continua valendo uma tela,
 * e a captura vai além da viewport.
 *
 * Uso: node scripts/prints/tirar-prints.mjs http://localhost:3100/pt-BR ../docs/site/prints/2026-09-11
 * Variável opcional: NAVEGADOR=<caminho do msedge.exe ou chrome.exe>
 */
import { spawn } from "node:child_process";
import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";

const url = process.argv[2] ?? "http://localhost:3100/pt-BR";
const saida = path.resolve(process.argv[3] ?? "prints");
const telas = [
  { nome: "computador", largura: 1440, altura: 900, escala: 1, movel: false },
  { nome: "celular", largura: 400, altura: 850, escala: 2, movel: true },
];

const candidatos = [
  process.env.NAVEGADOR,
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
  "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
].filter(Boolean);
const navegador = candidatos.find((c) => existsSync(c));
if (!navegador) {
  console.error("Nenhum Edge ou Chrome encontrado. Defina NAVEGADOR.");
  process.exit(1);
}

const porta = 9300 + Math.floor(Math.random() * 500);
const perfil = path.join(tmpdir(), `rotaguard-prints-${porta}`);
const processo = spawn(
  navegador,
  [`--headless=new`, `--remote-debugging-port=${porta}`, `--user-data-dir=${perfil}`, "--hide-scrollbars", "--no-first-run", "about:blank"],
  { stdio: "ignore" }
);

const esperar = (ms) => new Promise((r) => setTimeout(r, ms));

async function wsDaAba() {
  for (let i = 0; i < 50; i++) {
    try {
      const abas = await (await fetch(`http://127.0.0.1:${porta}/json/list`)).json();
      const aba = abas.find((a) => a.type === "page");
      if (aba) return aba.webSocketDebuggerUrl;
    } catch {
      /* navegador ainda subindo */
    }
    await esperar(200);
  }
  throw new Error("DevTools não respondeu");
}

function conectar(wsUrl) {
  const ws = new WebSocket(wsUrl);
  let id = 0;
  const pendentes = new Map();
  const ouvintes = new Map();
  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.id && pendentes.has(msg.id)) {
      const { resolver, rejeitar } = pendentes.get(msg.id);
      pendentes.delete(msg.id);
      if (msg.error) rejeitar(new Error(msg.error.message));
      else resolver(msg.result);
    } else if (msg.method && ouvintes.has(msg.method)) {
      ouvintes.get(msg.method)(msg.params);
      ouvintes.delete(msg.method);
    }
  };
  const aberto = new Promise((r) => (ws.onopen = r));
  return {
    aberto,
    enviar: (method, params = {}) =>
      new Promise((resolver, rejeitar) => {
        const n = ++id;
        pendentes.set(n, { resolver, rejeitar });
        ws.send(JSON.stringify({ id: n, method, params }));
      }),
    uma: (method) => new Promise((r) => ouvintes.set(method, r)),
    fechar: () => ws.close(),
  };
}

try {
  mkdirSync(saida, { recursive: true });
  const cdp = conectar(await wsDaAba());
  await cdp.aberto;
  await cdp.enviar("Page.enable");
  await cdp.enviar("Runtime.enable");

  for (const tela of telas) {
    await cdp.enviar("Emulation.setDeviceMetricsOverride", {
      width: tela.largura,
      height: tela.altura,
      deviceScaleFactor: tela.escala,
      mobile: tela.movel,
    });
    const carregou = cdp.uma("Page.loadEventFired");
    await cdp.enviar("Page.navigate", { url });
    await carregou;
    await esperar(1200);

    // Rola a página inteira devagar para disparar imagens preguiçosas, IntersectionObserver e ScrollTrigger.
    const { result } = await cdp.enviar("Runtime.evaluate", { expression: "document.documentElement.scrollHeight", returnByValue: true });
    for (let y = 0; y < result.value; y += Math.round(tela.altura * 0.8)) {
      await cdp.enviar("Runtime.evaluate", { expression: `window.scrollTo(0, ${y})` });
      await esperar(120);
    }
    await cdp.enviar("Runtime.evaluate", { expression: "window.scrollTo(0, 0)" });
    await esperar(1500);

    const { result: altura } = await cdp.enviar("Runtime.evaluate", { expression: "document.documentElement.scrollHeight", returnByValue: true });
    const { data } = await cdp.enviar("Page.captureScreenshot", {
      format: "png",
      captureBeyondViewport: true,
      clip: { x: 0, y: 0, width: tela.largura, height: altura.value, scale: 1 },
    });
    const arquivo = path.join(saida, `${tela.nome}.png`);
    writeFileSync(arquivo, Buffer.from(data, "base64"));

    const { data: topo } = await cdp.enviar("Page.captureScreenshot", { format: "png" });
    writeFileSync(path.join(saida, `${tela.nome}-primeira-tela.png`), Buffer.from(topo, "base64"));
    console.log(`${tela.nome}: ${tela.largura}×${altura.value} → ${arquivo}`);
  }
  cdp.fechar();
} finally {
  processo.kill();
}
