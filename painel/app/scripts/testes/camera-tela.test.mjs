// Spec 025 · teste com a câmera do aparelho dentro do painel: nada sai do aparelho, permissão negada sem quebrar a tela,
// parar desliga a câmera, CSP na página e os arquivos do MediaPipe servidos pelo próprio painel. Roda sem build.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { existsSync, mkdtempSync, readdirSync, readFileSync, rmSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { test } from "node:test";
import {
  abasDoAoVivo,
  caminhosDoMediapipe,
  descreverInclinacao,
  erroDaCamera,
  formatarDuracao,
  formatarRelogio,
  rotuloDoEvento,
} from "../../src/components/live/camera-regras.ts";
import { abrirCamera, bloquearEnviosParaFora, pararCamera } from "../../src/components/live/camera-trilhas.ts";

const raiz = path.join(import.meta.dirname, "..", "..");
const repositorio = path.join(raiz, "..", "..");
const ler = (...partes) => readFileSync(path.join(raiz, ...partes), "utf8");
const pastaLive = path.join(raiz, "src", "components", "live");
const arquivosDaCamera = readdirSync(pastaLive)
  .filter((nome) => nome.startsWith("camera-"))
  .map((nome) => ({ nome, texto: readFileSync(path.join(pastaLive, nome), "utf8") }));

test("CAM-07 nenhum endereço externo nos arquivos do teste: o MediaPipe vem de /mediapipe/ do próprio painel", () => {
  assert.ok(arquivosDaCamera.length >= 8, "arquivos camera-* soltos em components/live (subpasta quebra o SCR-13)");
  assert.ok(readdirSync(pastaLive).every((nome) => statSync(path.join(pastaLive, nome)).isFile()), "sem subpasta em live/");
  for (const { nome, texto } of [...arquivosDaCamera, { nome: "ao-vivo/page.tsx", texto: ler("src", "app", "ao-vivo", "page.tsx") }]) {
    assert.doesNotMatch(texto, /https?:\/\/|wss?:\/\/|jsdelivr|unpkg|googleapis|gstatic/i, `${nome}: endereço externo`);
  }
  assert.deepEqual(caminhosDoMediapipe(""), {
    wasmLoaderPath: "/mediapipe/wasm/vision_wasm_internal.js",
    wasmBinaryPath: "/mediapipe/wasm/vision_wasm_internal.wasm",
    modelo: "/mediapipe/modelos/face_landmarker.task",
  });
  assert.equal(caminhosDoMediapipe("/painel").modelo, "/painel/mediapipe/modelos/face_landmarker.task", "na VPS o painel mora em /painel");
  const motor = arquivosDaCamera.find(({ nome }) => nome === "camera-motor.ts").texto;
  assert.match(motor, /caminhosDoMediapipe\(process\.env\.NEXT_PUBLIC_PAINEL_BASE_PATH \?\? ""\)/);
  assert.match(motor, /await import\("@mediapipe\/tasks-vision"\)/, "o MediaPipe só baixa quando a pessoa liga a câmera");
  assert.match(motor, /bloquearEnviosParaFora\(\)/, "a telemetria do MediaPipe nem chega à rede");
});

test("CAM-07 envio para fora barrado no próprio aparelho: só passa o que é do painel", async () => {
  const pedidos = [];
  const janela = {
    location: { href: "https://rotaguard.acexpartners.com.br/painel/ao-vivo/", origin: "https://rotaguard.acexpartners.com.br" },
    fetch: async (entrada) => {
      pedidos.push(String(entrada));
      return new Response("ok", { status: 200 });
    },
  };
  const original = janela.fetch;
  const soltar = bloquearEnviosParaFora(janela);
  const fora = await janela.fetch("https://odml.pa.googleapis.com/v1/log", { method: "POST" });
  assert.notEqual(fora.status, 200, "a telemetria recebe falha e para sozinha");
  await janela.fetch("/painel/mediapipe/modelos/face_landmarker.task");
  await janela.fetch(new URL("https://rotaguard.acexpartners.com.br/painel/api/ponte/entrar"));
  assert.deepEqual(pedidos, ["/painel/mediapipe/modelos/face_landmarker.task", "https://rotaguard.acexpartners.com.br/painel/api/ponte/entrar"]);
  soltar();
  assert.equal(janela.fetch, original, "ao parar, o fetch volta ao original");
});

test("CAM-08 sem permissão de câmera: mensagem clara, como liberar e botão para tentar de novo", () => {
  const negado = erroDaCamera("NotAllowedError", { instalado: false });
  assert.match(negado.titulo, /bloquead/i);
  assert.ok(negado.comoLiberar.length >= 2, "passos para liberar a câmera");
  assert.ok(negado.comoLiberar.some((passo) => /cadeado|câmera/i.test(passo)));
  assert.equal(negado.tentarDeNovo, true);
  assert.match(erroDaCamera("NotAllowedError", { instalado: true }).comoLiberar.join(" "), /RotaGuard/);
  assert.match(erroDaCamera("NotFoundError", { instalado: false }).titulo, /Nenhuma câmera/);
  assert.match(erroDaCamera("NotReadableError", { instalado: true }).texto, /outro programa/i);
  assert.match(erroDaCamera("inseguro", { instalado: false }).texto, /https/);
  assert.match(erroDaCamera("xyz", { instalado: false }).titulo, /Não foi possível/);
  const bloqueado = erroDaCamera("motor_bloqueado", { instalado: true });
  assert.match(bloqueado.titulo, /bloqueou/, "CSP sem 'wasm-unsafe-eval': não é falta de arquivo");
  assert.equal(bloqueado.tentarDeNovo, false);
  assert.match(arquivosDaCamera.find(({ nome }) => nome === "camera-motor.ts").texto, /"motor_bloqueado"/);
  for (const nome of ["NotAllowedError", "NotFoundError", "NotReadableError", "OverconstrainedError", "inseguro", "modelo", "motor_bloqueado", "xyz"]) {
    const erro = erroDaCamera(nome, { instalado: false });
    assert.ok(erro.titulo && erro.texto, nome);
    assert.doesNotMatch(`${erro.titulo} ${erro.texto} ${erro.comoLiberar.join(" ")}`, /—|LGPD/, `${nome}: travessão ou LGPD`);
  }
  const tela = arquivosDaCamera.filter(({ nome }) => nome.endsWith(".tsx")).map(({ texto }) => texto).join("\n");
  assert.match(tela, /erroDaCamera\(/);
  assert.match(tela, /Tentar de novo/);
  assert.match(tela, /role="alert"/);
});

test("CAM-08 endereço sem https: recusa antes de pedir a câmera, com o nome que a tela entende", async () => {
  let pediu = false;
  const ambiente = { isSecureContext: false, mediaDevices: { getUserMedia: async () => ((pediu = true), {}) } };
  await assert.rejects(abrirCamera({}, ambiente), (erro) => erro.name === "inseguro");
  assert.equal(pediu, false);
  await assert.rejects(abrirCamera({}, { isSecureContext: true, mediaDevices: undefined }), (erro) => erro.name === "navegador");
});

test("CAM-09 parar desliga todas as trilhas da câmera (track.stop) e solta o vídeo", () => {
  const trilhas = [0, 1].map(() => ({ readyState: "live", stop() { this.readyState = "ended"; } }));
  const stream = { getTracks: () => trilhas };
  const video = { srcObject: stream, pausado: false, pause() { this.pausado = true; } };
  pararCamera(stream, video);
  assert.ok(trilhas.every((trilha) => trilha.readyState === "ended"));
  assert.equal(video.srcObject, null);
  assert.equal(video.pausado, true);
  pararCamera(null, null);
});

test("CAM-09 abrir pede só vídeo, câmera da frente como preferência e 640 × 480 a 30 quadros por segundo", async () => {
  let pedido;
  const stream = { getTracks: () => [] };
  const ambiente = { isSecureContext: true, mediaDevices: { getUserMedia: async (restricoes) => ((pedido = restricoes), stream) } };
  const video = { muted: false, playsInline: false, atributos: {}, setAttribute(nome, valor) { this.atributos[nome] = valor; }, play: async () => {} };
  assert.equal(await abrirCamera(video, ambiente), stream);
  assert.equal(pedido.audio, false);
  assert.deepEqual(pedido.video.facingMode, { ideal: "user" }, "preferência, nunca exact (iPhone)");
  assert.equal(pedido.video.width.ideal, 640);
  assert.equal(video.srcObject, stream);
  assert.equal(video.muted, true);
  assert.equal(video.atributos.playsinline, "", "iPhone: sem playsinline o vídeo abre em tela cheia ou fica preto");
});

test("CAM-11 a página declara CSP com connect-src 'self', a mesma do Caddy (menos frame-ancestors, que não vale em meta)", () => {
  const layout = ler("src", "app", "layout.tsx");
  assert.match(layout, /<meta httpEquiv="Content-Security-Policy" content=\{/);
  const politica = layout.match(/POLITICA_DE_CONTEUDO =\s*"([^"]+)"/)?.[1];
  assert.ok(politica, "política em uma linha só, para conferir");
  const diretivas = (texto) => Object.fromEntries(texto.split(";").map((parte) => parte.trim().split(/\s+/)).filter((partes) => partes[0]).map(([nome, ...valores]) => [nome, valores.sort().join(" ")]));
  const meta = diretivas(politica);
  assert.equal(meta["connect-src"], "'self'");
  assert.equal(meta["default-src"], "'self'");
  assert.match(meta["script-src"], /'wasm-unsafe-eval'/);
  assert.doesNotMatch(meta["script-src"], /'unsafe-eval'/, "eval de JavaScript só no next dev");
  assert.equal(meta["frame-ancestors"], undefined);
  // Na web, quem manda a política do /painel é o servidor do painel (spec 024) ou o Caddy: a meta tem que ser a mesma.
  const naWeb = [];
  const caddy = path.join(repositorio, "implantacao", "vps", "rotaguard.caddy");
  const doCaddy = existsSync(caddy) && readFileSync(caddy, "utf8").match(/Content-Security-Policy "([^"]+)"/)?.[1];
  if (doCaddy) naWeb.push(["Caddy", doCaddy]);
  const servidor = path.join(repositorio, "painel", "web", "servidor_web.py");
  const doServidor = existsSync(servidor) && readFileSync(servidor, "utf8").match(/POLITICA_PADRAO = "; "\.join\(\(([\s\S]*?)\)\)/)?.[1];
  if (doServidor) naWeb.push(["servidor_web.py", [...doServidor.matchAll(/"([^"]+)"/g)].map(([, parte]) => parte).join("; ")]);
  for (const [origem, politicaDaWeb] of naWeb) {
    const semMoldura = diretivas(politicaDaWeb);
    delete semMoldura["frame-ancestors"];
    assert.deepEqual(meta, semMoldura, `meta e ${origem} com a mesma política`);
  }
});

test("abas do Ao vivo: instalado mostra o script e a câmera; na web (VPS), só a câmera do aparelho", () => {
  assert.deepEqual(abasDoAoVivo(undefined).map((aba) => [aba.id, aba.rotulo]), [
    ["script", "Script neste computador"],
    ["camera", "Câmera deste aparelho"],
  ]);
  assert.deepEqual(abasDoAoVivo("servidor").map((aba) => aba.id), ["camera"]);
  const tela = ler("src", "components", "live", "live-screen.tsx");
  assert.match(tela, /abasDoAoVivo\(process\.env\.NEXT_PUBLIC_PAINEL_TRANSPORTE\)/);
});

test("textos da tela: duração, relógio da sessão, inclinação e eventos em português, sem travessão", () => {
  assert.equal(formatarDuracao(1.24), "1,2 s");
  assert.equal(formatarDuracao(65), "1 min 05 s");
  assert.equal(formatarDuracao(null), "acontecendo");
  assert.equal(formatarRelogio(42.7), "0:42");
  assert.equal(formatarRelogio(3725), "1:02:05");
  assert.equal(descreverInclinacao(8.4), "8° para baixo");
  assert.equal(descreverInclinacao(-3.6), "4° para cima");
  assert.equal(descreverInclinacao(0.4), "reta");
  assert.equal(rotuloDoEvento("microssono"), "Olhos fechados por 1 s ou mais (microssono)");
  assert.equal(rotuloDoEvento("sono"), "Olhos fechados por 3 s ou mais (sono)");
  for (const { nome, texto } of arquivosDaCamera) {
    assert.doesNotMatch(texto, /—/, `${nome}: travessão`);
    assert.doesNotMatch(texto, /conforme a LGPD/i, `${nome}: frase proibida sem parecer (SITE-04)`);
  }
  const tela = arquivosDaCamera.filter(({ nome }) => nome.endsWith(".tsx")).map(({ texto }) => texto).join("\n");
  assert.match(tela, /Estimativa pela câmera, não é medida médica/);
  assert.match(tela, /Parar câmera/);
});

test("CAM-10 dependência exata e arquivos copiados no build: só o par SIMD do WASM e o modelo da caixa", () => {
  const pacote = JSON.parse(ler("package.json"));
  assert.equal(pacote.dependencies["@mediapipe/tasks-vision"], "1.1.1", "versão exata, sem ^");
  assert.match(pacote.scripts.prebuild, /copiar-mediapipe\.mjs/);
  assert.match(pacote.scripts.predev, /copiar-mediapipe\.mjs/);
  assert.match(ler(".gitignore"), /^\/?public\/mediapipe\/?$/m, "WASM e modelo fora do git");
  const destino = mkdtempSync(path.join(tmpdir(), "rg-mediapipe-"));
  try {
    const saida = spawnSync(process.execPath, [path.join(raiz, "scripts", "copiar-mediapipe.mjs")], {
      env: { ...process.env, COPIAR_MEDIAPIPE_DESTINO: destino },
      encoding: "utf8",
    });
    assert.equal(saida.status, 0, saida.stderr);
    const copiados = ["wasm", "modelos"].flatMap((pasta) => readdirSync(path.join(destino, pasta)).map((nome) => `${pasta}/${nome}`)).sort();
    assert.deepEqual(copiados, ["modelos/face_landmarker.task", "wasm/vision_wasm_internal.js", "wasm/vision_wasm_internal.wasm"]);
    const modelo = path.join(repositorio, "caixa", "vision", "models", "face_landmarker.task");
    assert.equal(statSync(path.join(destino, "modelos", "face_landmarker.task")).size, statSync(modelo).size, "o mesmo modelo da caixa");
  } finally {
    rmSync(destino, { recursive: true, force: true });
  }
});

test("alerta sonoro: 2 bipes ao passar de 1 s de olho fechado, 3 bipes a cada 1,1 s a partir de 3 s, nada com o olho aberto", async () => {
  const { AlertaSonoro } = await import("../../src/components/live/camera-alerta.ts");
  let bipes = 0;
  const parametro = () => ({ value: 0, setValueAtTime() {}, linearRampToValueAtTime() {} });
  globalThis.AudioContext = class {
    state = "suspended";
    currentTime = 0;
    destination = {};
    async resume() { this.state = "running"; }
    async suspend() { this.state = "suspended"; }
    async close() {}
    createOscillator() { bipes++; return { type: "", frequency: parametro(), connect: (no) => no, start() {}, stop() {} }; }
    createGain() { return { gain: parametro(), connect: (no) => no }; }
  };
  try {
    const alerta = new AlertaSonoro();
    alerta.atualizar("sono", 0);
    assert.equal(bipes, 0, "sem ligar o som, nada toca");
    await alerta.ligar();
    assert.equal(bipes, 1, "um bipe curto confirma que o som ligou");
    alerta.atualizar("normal", 100);
    alerta.atualizar("microssono", 200);
    assert.equal(bipes, 3);
    alerta.atualizar("microssono", 1500);
    assert.equal(bipes, 3, "microssono toca uma vez só");
    alerta.atualizar("sono", 2000);
    assert.equal(bipes, 6);
    alerta.atualizar("sono", 2500);
    assert.equal(bipes, 6);
    alerta.atualizar("sem_resposta", 3200);
    assert.equal(bipes, 9, "repete enquanto o olho continua fechado");
    alerta.atualizar("normal", 3300);
    alerta.atualizar("microssono", 3400);
    assert.equal(bipes, 11, "depois de abrir o olho, o próximo fechamento avisa de novo");
    alerta.desligar();
    alerta.atualizar("sono", 9000);
    assert.equal(bipes, 11, "som desligado");
  } finally {
    delete globalThis.AudioContext;
  }
});
