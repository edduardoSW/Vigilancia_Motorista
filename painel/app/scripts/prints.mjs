// Capturas das telas da prévia (spec 012, PRV-09) com o Edge do Windows em modo headless, pelo protocolo DevTools.
// Uso: com `npm run dev` rodando, `node scripts/prints.mjs` (PAINEL_URL e PRINTS_DIR opcionais).
import { spawn } from "node:child_process";
import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";

const base = process.env.PAINEL_URL || "http://localhost:3001";
const pasta = path.resolve(process.env.PRINTS_DIR || "prints");
const rotas = (process.env.ROTAS || "/,/viagens/v-2240/,/viagens/v-3310/,/veiculos/").split(",");
const larguras = (process.env.LARGURAS || "1440,1280").split(",").map(Number);
mkdirSync(pasta, { recursive: true });

const porta = 9600 + Math.floor(Math.random() * 300);
const edge = spawn(
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
  ["--headless=new", "--no-first-run", "--hide-scrollbars", `--remote-debugging-port=${porta}`, `--user-data-dir=${mkdtempSync(path.join(tmpdir(), "rg-painel-"))}`, "about:blank"],
  { stdio: "ignore", windowsHide: true },
);
const espera = (ms) => new Promise((resolver) => setTimeout(resolver, ms));
let ws;
let sequencia = 0;
const pendentes = new Map();
const erros = [];

function comando(metodo, parametros = {}) {
  return new Promise((resolver, rejeitar) => {
    const id = ++sequencia;
    const limite = setTimeout(() => { pendentes.delete(id); rejeitar(new Error(`sem resposta: ${metodo}`)); }, 30000);
    pendentes.set(id, { resolver, rejeitar, limite });
    ws.send(JSON.stringify({ id, method: metodo, params: parametros }));
  });
}

async function avaliar(expressao) {
  const resposta = await comando("Runtime.evaluate", { expression: expressao, returnByValue: true, awaitPromise: true });
  if (resposta.exceptionDetails) throw new Error(resposta.exceptionDetails.text);
  return resposta.result.value;
}

try {
  let endereco;
  for (let i = 0; i < 60 && !endereco; i++) {
    try {
      endereco = (await (await fetch(`http://127.0.0.1:${porta}/json/list`)).json()).find((alvo) => alvo.type === "page")?.webSocketDebuggerUrl;
    } catch { /* o Edge ainda está abrindo */ }
    if (!endereco) await espera(150);
  }
  ws = new WebSocket(endereco);
  await new Promise((resolver) => { ws.onopen = resolver; });
  ws.onmessage = (mensagem) => {
    const dado = JSON.parse(mensagem.data);
    if (dado.id && pendentes.has(dado.id)) {
      const pendente = pendentes.get(dado.id);
      pendentes.delete(dado.id);
      clearTimeout(pendente.limite);
      if (dado.error) pendente.rejeitar(new Error(dado.error.message));
      else pendente.resolver(dado.result);
    } else if (dado.method === "Runtime.exceptionThrown") {
      erros.push(dado.params.exceptionDetails.exception?.description || dado.params.exceptionDetails.text);
    } else if (dado.method === "Runtime.consoleAPICalled" && dado.params.type === "error") {
      erros.push(dado.params.args.map((arg) => arg.value ?? arg.description).join(" "));
    }
  };
  await comando("Page.enable");
  await comando("Runtime.enable");

  for (const largura of larguras) {
    for (const rota of rotas) {
      await comando("Emulation.setDeviceMetricsOverride", { width: largura, height: 900, deviceScaleFactor: 1, mobile: false });
      await comando("Page.navigate", { url: base + rota });
      for (let i = 0; i < 150; i++) {
        if (await avaliar("document.readyState === 'complete'")) break;
        await espera(100);
      }
      await avaliar("document.fonts.ready.then(() => true)");
      await espera(600);
      const transborda = await avaliar("document.documentElement.scrollWidth > window.innerWidth");
      const { contentSize } = await comando("Page.getLayoutMetrics");
      const altura = Math.min(Math.ceil(contentSize.height), 6000);
      const captura = await comando("Page.captureScreenshot", {
        format: "png",
        captureBeyondViewport: true,
        clip: { x: 0, y: 0, width: largura, height: altura, scale: 1 },
      });
      const nome = `${largura}-${rota.replace(/\//g, "_").replace(/^_|_$/g, "") || "chegadas"}.png`;
      writeFileSync(path.join(pasta, nome), Buffer.from(captura.data, "base64"));
      console.log(`${nome} · ${largura}x${altura}${transborda ? " · TRANSBORDA NA HORIZONTAL" : ""}`);
    }
  }
  console.log(erros.length ? `Erros no navegador:\n${erros.join("\n")}` : "Nenhum erro de JavaScript no navegador.");
  process.exitCode = erros.length ? 1 : 0;
} finally {
  ws?.close();
  edge.kill();
}
