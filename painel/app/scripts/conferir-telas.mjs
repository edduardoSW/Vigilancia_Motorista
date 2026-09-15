// Conferência das telas do painel do jeito que uma pessoa usa (erros 93 e 96 da vault): entra pela demonstração, navega
// clicando no menu, abre a busca rápida com Ctrl+K digitando no ritmo de gente e, depois de cada ação, confere o endereço e
// o que está na tela. Também confere o que a Consulta e o Supervisor veem (MEN-01, EQP-02, GUI-07), o texto maior em
// 1200 × 760 (CFG-09), a spec 019 (Lista e Cards, janelas no centro, motorista e vídeos no relatório, modo escuro) e salva
// as capturas. Nada aparece na tela: Edge do Windows em modo headless, pelo protocolo DevTools.
// Uso: com a pasta out/ servida em PAINEL_URL (padrão http://127.0.0.1:3107), `node scripts/conferir-telas.mjs`.
import { spawn } from "node:child_process";
import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { crc32, deflateSync } from "node:zlib";

const base = (process.env.PAINEL_URL || "http://127.0.0.1:3107").replace(/\/+$/, "");
const pasta = path.resolve(process.env.PRINTS_DIR || "prints");
mkdirSync(pasta, { recursive: true });
// Termo assinado fictício para a importação (TER-01): folha branca com título, linhas de texto e assinatura, em PNG.
function pngDoTermo(largura = 620, altura = 800) {
  const linhas = [];
  for (let y = 0; y < altura; y++) {
    const linha = Buffer.alloc(1 + largura * 3, 255);
    linha[0] = 0; // sem filtro
    const pintar = (de, ate, cinza) => linha.fill(cinza, 1 + de * 3, 1 + ate * 3);
    if (y >= 60 && y < 76) pintar(60, 380, 60);
    for (let bloco = 0; bloco < 14; bloco++) {
      const topo = 120 + bloco * 34;
      if (y >= topo && y < topo + 9) pintar(60, bloco % 4 === 3 ? 380 : 560, 175);
    }
    for (let x = 80; x < 300; x++) if (Math.abs(y - (662 + 14 * Math.sin(x / 9))) < 1.6) pintar(x, x + 1, 40);
    if (y >= 690 && y < 692) pintar(60, 320, 110);
    linhas.push(linha);
  }
  const bloco = (tipo, dados) => {
    const corpo = Buffer.concat([Buffer.from(tipo, "ascii"), dados]);
    const tamanho = Buffer.alloc(4);
    tamanho.writeUInt32BE(dados.length);
    const soma = Buffer.alloc(4);
    soma.writeUInt32BE(crc32(corpo));
    return Buffer.concat([tamanho, corpo, soma]);
  };
  const cabecalho = Buffer.alloc(13);
  cabecalho.writeUInt32BE(largura, 0);
  cabecalho.writeUInt32BE(altura, 4);
  cabecalho[8] = 8; // 8 bits por cor
  cabecalho[9] = 2; // RGB
  return Buffer.concat([Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]), bloco("IHDR", cabecalho), bloco("IDAT", deflateSync(Buffer.concat(linhas))), bloco("IEND", Buffer.alloc(0))]);
}
const termoPng = path.join(mkdtempSync(path.join(tmpdir(), "rg-termo-")), "termo-assinado-marcos.png");
writeFileSync(termoPng, pngDoTermo());

const espera = (ms) => new Promise((resolver) => setTimeout(resolver, ms));
const falhas = [];
function conferir(ok, mensagem) {
  console.log(`${ok ? "ok    " : "FALHOU"} ${mensagem}`);
  if (!ok) falhas.push(mensagem);
  return Boolean(ok);
}

const porta = 9600 + Math.floor(Math.random() * 300);
const edge = spawn(
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
  ["--headless=new", "--no-first-run", "--hide-scrollbars", `--remote-debugging-port=${porta}`, `--user-data-dir=${mkdtempSync(path.join(tmpdir(), "rg-conferir-"))}`, "about:blank"],
  { stdio: "ignore", windowsHide: true },
);
let ws;
let sequencia = 0;
const pendentes = new Map();
const erros = [];

function comando(metodo, parametros = {}) {
  return new Promise((resolver, rejeitar) => {
    const id = ++sequencia;
    const limite = setTimeout(() => {
      pendentes.delete(id);
      rejeitar(new Error(`sem resposta: ${metodo}`));
    }, 30000);
    pendentes.set(id, { resolver, rejeitar, limite });
    ws.send(JSON.stringify({ id, method: metodo, params: parametros }));
  });
}

async function avaliar(expressao) {
  const resposta = await comando("Runtime.evaluate", { expression: expressao, returnByValue: true, awaitPromise: true });
  if (resposta.exceptionDetails) throw new Error(resposta.exceptionDetails.exception?.description || resposta.exceptionDetails.text);
  return resposta.result.value;
}

async function esperarAte(expressao, descricao, limiteMs = 8000) {
  const fim = Date.now() + limiteMs;
  while (Date.now() < fim) {
    try {
      if (await avaliar(expressao)) return true;
    } catch {
      // a página está trocando
    }
    await espera(120);
  }
  return conferir(false, `tempo esgotado esperando: ${descricao}`);
}

const tamanho = (largura, altura) => comando("Emulation.setDeviceMetricsOverride", { width: largura, height: altura, deviceScaleFactor: 1, mobile: false });

async function abrir(rota) {
  await comando("Page.navigate", { url: base + rota });
  await esperarAte("document.readyState === 'complete'", `carregar ${rota}`, 15000);
  await avaliar("document.fonts.ready.then(() => true)");
}

// Clica como uma pessoa: acha o elemento visível pelo seletor e pelo texto e aperta o mouse no meio dele.
async function clicar(seletor, texto = "") {
  const ponto = await avaliar(`(() => {
    const alvo = [...document.querySelectorAll(${JSON.stringify(seletor)})].find((el) => {
      const caixa = el.getBoundingClientRect();
      return caixa.width > 0 && caixa.height > 0 && el.textContent.replace(/\\s+/g, " ").trim().includes(${JSON.stringify(texto)});
    });
    if (!alvo) return null;
    alvo.scrollIntoView({ block: "nearest" });
    const caixa = alvo.getBoundingClientRect();
    const x = caixa.left + caixa.width / 2;
    const y = caixa.top + caixa.height / 2;
    const noPonto = document.elementFromPoint(x, y);
    if (!noPonto || !(alvo === noPonto || alvo.contains(noPonto))) {
      alvo.click();
      return { js: true };
    }
    return { x, y };
  })()`);
  if (!conferir(Boolean(ponto), `achar para clicar: ${seletor} "${texto}"`)) return false;
  if (!ponto.js) {
    for (const type of ["mouseMoved", "mousePressed", "mouseReleased"]) {
      await comando("Input.dispatchMouseEvent", { type, x: ponto.x, y: ponto.y, button: "left", clickCount: type === "mouseMoved" ? 0 : 1 });
      await espera(40);
    }
  }
  await espera(300);
  return true;
}

const TECLAS = {
  Enter: { code: "Enter", windowsVirtualKeyCode: 13, text: "\r" },
  Escape: { code: "Escape", windowsVirtualKeyCode: 27 },
  k: { code: "KeyK", windowsVirtualKeyCode: 75 },
};

async function teclar(tecla, { ctrl = false } = {}) {
  const { text, ...info } = TECLAS[tecla];
  const modifiers = ctrl ? 2 : 0;
  await comando("Input.dispatchKeyEvent", { type: "keyDown", key: tecla, modifiers, ...info, ...(ctrl || !text ? {} : { text }) });
  await comando("Input.dispatchKeyEvent", { type: "keyUp", key: tecla, modifiers, ...info });
  await espera(250);
}

async function digitar(texto) {
  for (const letra of texto) {
    await comando("Input.insertText", { text: letra });
    await espera(70);
  }
  await espera(300);
}

async function capturar(nome) {
  await espera(500);
  const { data } = await comando("Page.captureScreenshot", { format: "png" });
  writeFileSync(path.join(pasta, `${nome}.png`), Buffer.from(data, "base64"));
  console.log(`       captura ${nome}.png`);
}

const textoDaTela = () => avaliar("document.querySelector('main')?.innerText ?? ''");
const rotulosDoMenu = () => avaliar("[...document.querySelectorAll('[data-menu]')].map((el) => el.textContent.replace(/\\d+ para ver/, '').trim())");
const marcado = () => avaliar("document.querySelector('[data-menu][aria-current=\"page\"]')?.textContent.replace(/\\d+ para ver/, '').trim() ?? null");
const buscaAberta = "Boolean(document.querySelector('[role=dialog][aria-label=\"Busca rápida\"]'))";
const MENU_ADMINISTRADOR = ["Início", "Viagens", "Motoristas", "Veículos e caixas", "Equipe", "Configurações", "Teste neste computador", "Guia de uso"];

try {
  let endereco;
  for (let i = 0; i < 80 && !endereco; i++) {
    try {
      endereco = (await (await fetch(`http://127.0.0.1:${porta}/json/list`)).json()).find((alvo) => alvo.type === "page")?.webSocketDebuggerUrl;
    } catch {
      // o Edge ainda está abrindo
    }
    if (!endereco) await espera(150);
  }
  ws = new WebSocket(endereco);
  await new Promise((resolver) => {
    ws.onopen = resolver;
  });
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
  await tamanho(1440, 900);

  // 0 · Primeiro uso: sem ?sessao, a demonstração começa sem ativação (aqui não há a janela do app).
  await abrir("/");
  if (await esperarAte("document.body.innerText.includes('Ativar o painel')", "tela Ativar o painel", 12000)) await capturar("00-ativar");

  // 1 · Administrador dentro da demonstração: Início.
  await abrir("/?sessao=administrador");
  await esperarAte("document.querySelectorAll('[data-menu]').length >= 8", "menu do administrador");
  await avaliar("window.__semRecarregar = true");
  conferir(JSON.stringify(await rotulosDoMenu()) === JSON.stringify(MENU_ADMINISTRADOR), "MEN-01 administrador vê os itens na ordem da spec");
  conferir((await marcado()) === "Início", "MEN-01 Início marcado ao abrir");
  await esperarAte("document.querySelector('main')?.innerText.includes('Primeiros passos')", "Primeiros passos no Início do administrador");
  await esperarAte("document.querySelector('main')?.innerText.includes('Avisos')", "avisos no Início");
  const inicio = await textoDaTela();
  conferir(inicio.includes("Caixa do Ônibus 2258 conectada"), "Início mostra a caixa conectada");
  conferir(inicio.includes("6 momentos para verificar"), "Início resume os 6 momentos para verificar");
  conferir(/CNH de Rogério Lima vence/.test(inicio), "Início avisa a CNH do Rogério Lima (spec 015, decisão 3)");
  conferir(inicio.includes("Caixa RG-0129 precisa de atenção"), "Início avisa a caixa RG-0129");
  conferir(inicio.includes("Teste neste computador"), "Início mostra o teste neste computador (spec 018)");
  conferir(inicio.indexOf("O que fazer agora") >= 0 && inicio.indexOf("O que fazer agora") < inicio.indexOf("Primeiros passos"), "INT-02 Início começa por O que fazer agora");
  conferir(
    await avaliar("(() => { const cards = [...document.querySelectorAll('main [data-tarefa]')]; return cards.length >= 3 && cards.every((card) => card.querySelector('a.btn, button')); })()"),
    "INT-02 cada card de O que fazer agora tem o seu botão",
  );
  conferir(await avaliar("(document.querySelector('aside [data-caixa-conectada]')?.getBoundingClientRect().height ?? 99) <= 40"), "INT-02 a caixa conectada ocupa uma linha só no menu");
  await capturar("01-inicio");

  // 2 · Viagens pelo menu, sem recarregar a janela. Começa em cards e troca para lista (spec 019, VIS-01).
  await clicar("[data-menu]", "Viagens");
  await esperarAte("location.pathname === '/viagens/' && document.querySelector('h1')?.textContent === 'Viagens'", "abrir Viagens pelo menu");
  await espera(400);
  conferir(await avaliar("window.__semRecarregar === true"), "trocar de tela pelo menu não recarrega a janela");
  conferir((await marcado()) === "Viagens", "MEN-01 Viagens marcado");
  conferir(
    await avaliar(
      "(() => { const barra = document.querySelector('.menu-bar'); const link = document.querySelector('[data-menu][aria-current=\"page\"]'); return Boolean(barra && link) && Math.abs(new DOMMatrix(getComputedStyle(barra).transform).m42 - link.offsetTop) < 1; })()",
    ),
    "a barrinha do menu desliza até Viagens",
  );
  const viagens = await textoDaTela();
  conferir(/Para verificar\s*2/.test(viagens) && /Revisadas\s*1/.test(viagens) && /Todas\s*3/.test(viagens), "Viagens com as abas e as contagens");
  const nomesDosCards = "[...document.querySelectorAll('main [data-card]')].map((card) => card.querySelector('b').textContent.trim())";
  if (await esperarAte("document.querySelectorAll('main [data-card]').length === 2", "VIS-01 Viagens começa em cards")) {
    const emCards = await avaliar(nomesDosCards);
    conferir(await avaliar("[...document.querySelectorAll('main [data-card]')].every((card) => /Motorista\\s+\\S/.test(card.innerText))"), "VIA-01 cada card de viagem mostra o motorista");
    await capturar("02-viagens-cards");
    await clicar("main [data-visao]", "Lista");
    await esperarAte("document.querySelectorAll('main tbody tr').length === 2", "VIS-01 a Lista mostra as viagens");
    const emLista = await avaliar("[...document.querySelectorAll('main tbody tr')].map((linha) => linha.querySelector('b').textContent.trim())");
    conferir(JSON.stringify(emCards) === JSON.stringify(emLista), `VIS-01 Lista e Cards com as mesmas viagens, na mesma ordem (${emLista.join(", ")})`);
    conferir(await avaliar("document.querySelector('main [data-visao=lista]').getAttribute('aria-pressed') === 'true'"), "VIS-01 o botão Lista fica marcado");
    await capturar("02-viagens-lista");
  }

  // 3 · Abrir a viagem clicando na linha: veículo e motorista em destaque (VIA-01) e momentos em cards e em lista (VID-01).
  await clicar("tbody tr", "Caminhão 3310");
  await esperarAte("location.pathname === '/viagens/v-3310/'", "abrir o relatório do Caminhão 3310 pela linha");
  conferir((await marcado()) === "Viagens", "MEN-01 o relatório mantém Viagens marcado");
  const blocoDasPessoas = "document.querySelector('main [aria-label=\"Veículo e motorista\"]')";
  if (await esperarAte(`${blocoDasPessoas}?.innerText.includes('Matrícula')`, "VIA-01 bloco do motorista carregado")) {
    const bloco = await avaliar(`${blocoDasPessoas}.innerText`);
    const faltamNoBloco = ["Veículo", "Motorista", "Matrícula", "CNH", "Termo", "Caixa"].filter((parte) => !bloco.includes(parte));
    conferir(faltamNoBloco.length === 0, `VIA-01 relatório com Veículo e Motorista em destaque${faltamNoBloco.length ? ` (faltam ${faltamNoBloco.join(", ")})` : ""}`);
    conferir(
      await avaliar(`[...${blocoDasPessoas}.querySelectorAll('a')].some((link) => link.textContent.includes('Ver cadastro') && link.getAttribute('href').startsWith('/motoristas/?abrir='))`),
      "VIA-01 Ver cadastro leva ao motorista",
    );
  }
  const campoVideo = "/trecho|Sem vídeo|trancado|apagado/i";
  if (await esperarAte("document.querySelectorAll('main [data-card]').length > 0", "VIS-01 momentos em cards")) {
    const cardsDeMomento = await avaliar("document.querySelectorAll('main [data-card]').length");
    conferir(await avaliar(`[...document.querySelectorAll('main [data-card]')].every((card) => ${campoVideo}.test(card.innerText))`), "VID-01 todo card de momento tem o campo Vídeo");
    await capturar("03-relatorio");
    await clicar("main [data-visao]", "Lista");
    await esperarAte(`document.querySelectorAll('main li[id^=momento-]').length === ${cardsDeMomento}`, "VIS-01 a Lista mostra os mesmos momentos");
    conferir(await avaliar(`[...document.querySelectorAll('main li[id^=momento-]')].every((linha) => ${campoVideo}.test(linha.innerText))`), "VID-01 toda linha de momento tem o campo Vídeo");
    await capturar("03-relatorio-lista");
  }

  // 4 · Janela do momento no centro (MOD-01, MOD-02) com os campos do vídeo (VID-01); confirmar e desfazer pelo aviso.
  const janela = "document.querySelector('[role=dialog]')";
  const comVideo = await avaliar("[...document.querySelectorAll('main li[id^=momento-]')].find((linha) => /trecho|trancado/.test(linha.innerText))?.id ?? null");
  if (conferir(Boolean(comVideo), "VID-01 o relatório tem um momento com vídeo")) {
    await clicar(`#${comVideo} button`);
    if (await esperarAte(`Boolean(${janela})`, "abrir a janela do momento")) {
      await espera(300);
      const textoDaJanela = await avaliar(`${janela}.innerText`);
      const faltamCampos = ["Início", "Fim", "Duração", "Câmera", "Caixa", "Coletado em", "Fica guardado até", "Situação"].filter((campo) => !textoDaJanela.includes(campo));
      conferir(faltamCampos.length === 0, `VID-01 a janela do momento mostra os campos do vídeo${faltamCampos.length ? ` (faltam ${faltamCampos.join(", ")})` : ""}`);
      conferir(
        await avaliar(`(() => { const caixa = ${janela}.getBoundingClientRect(); return Math.abs((caixa.top + caixa.bottom) / 2 - window.innerHeight / 2) < 40 && Math.abs((caixa.left + caixa.right) / 2 - window.innerWidth / 2) < 40; })()`),
        "MOD-01 a janela do momento abre no centro",
      );
      conferir(await avaliar("getComputedStyle(document.querySelector('.veu')).backdropFilter.includes('blur')"), "MOD-01 o resto da janela fica desfocado");
      conferir(
        await avaliar(`(() => { const pe = ${janela}.querySelector('footer').getBoundingClientRect(); return pe.bottom <= window.innerHeight && ${janela}.getBoundingClientRect().top >= 0; })()`),
        "MOD-02 a janela cabe na tela, com o rodapé visível",
      );
      conferir(await avaliar(`${janela}.querySelector('.overflow-y-auto').scrollTop === 0`), "MOD-02 a janela abre do começo, com o vídeo inteiro à vista");
      await capturar("04-momento-video");
      await clicar("[role=dialog] button", "Confirmar");
      await esperarAte("document.body.innerText.includes('Momento confirmado')", "aviso de momento confirmado");
      await esperarAte("[...document.querySelectorAll('[data-menu]')].some((el) => el.textContent.includes('5 para ver'))", "contador de Viagens cai para 5");
      conferir((await avaliar(`${janela}.innerText`)).includes("Marina Lopes"), "EQP-04 a decisão mostra o nome de quem entrou");
      await capturar("05-momento-confirmado");
      await clicar("[role=status] button", "Desfazer");
      await esperarAte("[...document.querySelectorAll('[data-menu]')].some((el) => el.textContent.includes('6 para ver'))", "Desfazer volta o contador para 6");
      await teclar("Escape");
      await esperarAte(`!${janela}`, "Esc fecha a janela do momento");
    }
  }

  // 5 · Busca rápida: Ctrl+K, digitar sem acento, Enter abre o motorista numa janela no centro (MOD-01).
  await teclar("k", { ctrl: true });
  if (await esperarAte(buscaAberta, "Ctrl+K abre a busca rápida")) {
    await capturar("06-busca-vazia");
    await digitar("rogerio lima");
    await esperarAte("[...document.querySelectorAll('[role=option]')].some((el) => el.textContent.includes('Rogério Lima'))", "a busca acha Rogério Lima sem acento");
    await capturar("06-busca-motorista");
    await teclar("Enter");
    await esperarAte("location.pathname === '/motoristas/' && location.search.includes('abrir=')", "Enter leva para Motoristas");
    await esperarAte("Boolean(document.querySelector('[role=dialog][aria-label=\"Rogério Lima\"]'))", "janela do Rogério Lima aberta");
    conferir((await marcado()) === "Motoristas", "MEN-01 Motoristas marcado");
    await espera(300);
    conferir(
      await avaliar(
        "(() => { const caixa = document.querySelector('[role=dialog][aria-label=\"Rogério Lima\"]').getBoundingClientRect(); return Math.abs((caixa.top + caixa.bottom) / 2 - window.innerHeight / 2) < 40 && Math.abs((caixa.left + caixa.right) / 2 - window.innerWidth / 2) < 40; })()",
      ),
      "MOD-01 o motorista abre numa janela no centro, não num painel lateral",
    );
    await capturar("07-motorista-aberto");
    await teclar("Escape");
    await esperarAte("!document.querySelector('[role=dialog][aria-label=\"Rogério Lima\"]')", "Esc fecha a janela do motorista");
  }

  // 5b · Motoristas em cards e lista (VIS-01), ver antes de editar (INT-01) e importar o termo assinado (TER-01 a TER-03).
  if (await esperarAte("location.pathname === '/motoristas/' && document.querySelectorAll('main [data-card]').length > 0", "VIS-01 Motoristas começa em cards")) {
    const motoristasEmCards = await avaliar(nomesDosCards);
    await capturar("07a-motoristas-cards");
    await clicar("main [data-visao]", "Lista");
    await esperarAte(`document.querySelectorAll('main tbody tr').length === ${motoristasEmCards.length}`, "VIS-01 a Lista mostra os motoristas");
    conferir(
      await avaliar(
        `(() => { const nomes = ${JSON.stringify(motoristasEmCards)}; const linhas = [...document.querySelectorAll('main tbody tr')]; return linhas.length === nomes.length && linhas.every((linha, i) => linha.innerText.includes(nomes[i])); })()`,
      ),
      `VIS-01 Lista e Cards com os mesmos motoristas, na mesma ordem (${motoristasEmCards.length})`,
    );
    await clicar("main [data-visao]", "Cards");
    await esperarAte("document.querySelectorAll('main [data-card]').length > 0", "voltar para os cards de Motoristas");
  }
  const janelaMarcos = "document.querySelector('[role=dialog][aria-label=\"Marcos Teixeira\"]')";
  await clicar("main [data-card]", "Marcos Teixeira");
  if (await esperarAte(`Boolean(${janelaMarcos})`, "abrir Marcos Teixeira pelo card")) {
    await espera(300);
    conferir(
      await avaliar(`(() => { const caixa = ${janelaMarcos}; return caixa.innerText.includes('Termo de ciência') && caixa.innerText.includes('Carteira de motorista') && caixa.querySelectorAll('input').length === 0; })()`),
      "INT-01 o motorista abre mostrando os dados, sem formulário",
    );
    await capturar("07b-motorista-dados");
    await clicar("[role=dialog] footer button", "Editar");
    conferir(await esperarAte(`(${janelaMarcos}?.querySelectorAll('input').length ?? 0) >= 3`, "formulário do motorista"), "INT-01 Editar troca para o formulário na mesma janela");
    await capturar("07c-motorista-editar");
    await clicar("[role=dialog] footer button", "Cancelar");
    conferir(
      await esperarAte(`Boolean(${janelaMarcos}?.innerText.includes('Carteira de motorista')) && ${janelaMarcos}.querySelectorAll('input').length === 0`, "voltar aos dados do motorista"),
      "INT-01 Cancelar volta aos dados",
    );
    await clicar("[role=dialog] button", "Importar termo assinado");
    if (await esperarAte("Boolean(document.querySelector('[role=dialog] form[aria-label=\"Importar termo assinado\"] input[type=file]'))", "TER-01 trecho Importar termo assinado")) {
      const { root } = await comando("DOM.getDocument", { depth: -1 });
      const { nodeId } = await comando("DOM.querySelector", { nodeId: root.nodeId, selector: "[role=dialog] input[type=file]" });
      await comando("DOM.setFileInputFiles", { nodeId, files: [termoPng] });
      await esperarAte("document.querySelector('[role=dialog]').innerText.includes('termo-assinado-marcos.png')", "o arquivo escolhido aparece na janela");
      await avaliar(
        "(() => { const campo = document.querySelector('[role=dialog] input[type=date]'); Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(campo, '2026-09-10'); campo.dispatchEvent(new Event('input', { bubbles: true })); return true; })()",
      );
      await capturar("07d-termo-importar");
      await clicar("[role=dialog] form[aria-label='Importar termo assinado'] button[type=submit]", "Importar");
      if (await esperarAte("/Termo de .+ importado/.test(document.body.innerText)", "TER-01 aviso de termo importado")) {
        conferir(await avaliar(`${janelaMarcos}.innerText.includes('termo-assinado-marcos.png')`), "TER-01 a janela do motorista mostra o arquivo do termo");
        await clicar("[role=dialog] button", "Ver termo");
        conferir(await esperarAte("Boolean(document.querySelector('[role=dialog] img[alt^=\"Termo assinado\"]'))", "foto do termo na janela"), "TER-02 Ver termo mostra a foto na janela");
        await capturar("07e-termo-importado");
        await clicar("[role=dialog] button", "Histórico do termo");
        conferir(
          await esperarAte("Boolean(document.querySelector('[role=dialog] ol[aria-label=\"Histórico do termo\"]')?.innerText.includes('termo-assinado-marcos.png'))", "histórico com o arquivo"),
          "TER-03 Histórico do termo mostra o registro com o arquivo",
        );
      }
    }
    await teclar("Escape");
    await esperarAte(`!${janelaMarcos}`, "Esc fecha a janela do Marcos");
  }

  // 6 · Guia pela busca rápida.
  await teclar("k", { ctrl: true });
  if (await esperarAte(buscaAberta, "Ctrl+K abre a busca rápida de novo")) {
    await digitar("esqueci a senha");
    await esperarAte("[...document.querySelectorAll('[role=option]')].some((el) => el.textContent.includes('Esqueci a senha'))", "a busca acha o capítulo do guia");
    await teclar("Enter");
    await esperarAte("location.pathname === '/guia/' && location.search.includes('capitulo=problemas')", "Enter leva para o capítulo 9 do guia");
    conferir((await marcado()) === "Guia de uso", "MEN-01 Guia de uso marcado");
    await capturar("08-guia");
  }

  // 7 · Veículos, Equipe e Configurações pelo menu.
  for (const [rotulo, caminho, captura] of [
    ["Veículos e caixas", "/veiculos/", "09-veiculos"],
    ["Equipe", "/equipe/", "10-equipe"],
    ["Configurações", "/configuracoes/", "11-configuracoes"],
  ]) {
    await clicar("[data-menu]", rotulo);
    await esperarAte(`location.pathname === '${caminho}' && document.querySelector('h1')?.textContent === '${rotulo}'`, `abrir ${rotulo} pelo menu`);
    await capturar(captura);
    if (rotulo === "Veículos e caixas") {
      const dialogo = "document.querySelector('[role=dialog][aria-label=\"Cadastrar veículo\"]')";
      await clicar("main button", "Cadastrar veículo");
      if (await esperarAte(`Boolean(${dialogo})`, "diálogo Cadastrar veículo")) {
        await espera(300);
        conferir(
          await avaliar(`(() => { const caixa = ${dialogo}.getBoundingClientRect(); return Math.abs((caixa.top + caixa.bottom) / 2 - window.innerHeight / 2) < 40; })()`),
          "o diálogo abre no meio da janela (não fica preso na tela aberta)",
        );
        await capturar("09-veiculos-cadastrar");
        await teclar("Escape");
        await esperarAte(`!${dialogo}`, "Esc fecha o diálogo");
      }
    }
  }
  conferir(await avaliar("window.__semRecarregar === true"), "a janela não recarregou em nenhuma troca de tela");

  // 8 · Texto maior (CFG-09): liga em Configurações › Aparência e percorre as telas em 1200 × 760.
  await clicar("nav[aria-label='Seções das configurações'] button", "Aparência");
  await esperarAte("document.body.innerText.includes('Aumenta as letras do painel')", "seção Aparência");
  await clicar("label", "Texto maior");
  await clicar("main button[type=submit]", "Salvar");
  if (await esperarAte("document.documentElement.hasAttribute('data-texto-maior')", "texto maior ligado")) {
    await tamanho(1200, 760);
    for (const [rotulo, caminho, captura] of [
      ["Início", "/", "12-texto-maior-inicio"],
      ["Viagens", "/viagens/", "13-texto-maior-viagens"],
      ["Motoristas", "/motoristas/", "14-texto-maior-motoristas"],
    ]) {
      await clicar("[data-menu]", rotulo);
      await esperarAte(`location.pathname === '${caminho}'`, `abrir ${rotulo} com texto maior`);
      await espera(500);
      const medida = await avaliar(
        "({ largura: document.documentElement.scrollWidth, altura: document.documentElement.scrollHeight, janela: [window.innerWidth, window.innerHeight] })",
      );
      conferir(
        medida.largura <= medida.janela[0] + 1 && medida.altura <= medida.janela[1] + 1,
        `CFG-09 ${rotulo} com texto maior em 1200 × 760, sem rolagem da janela (página ${medida.largura} × ${medida.altura}, janela ${medida.janela.join(" × ")})`,
      );
      conferir(
        await avaliar(
          "(() => { const menu = document.querySelector('aside'); const links = menu.querySelectorAll('[data-menu]'); const ultimo = links[links.length - 1].getBoundingClientRect(); const pessoa = menu.lastElementChild.getBoundingClientRect(); return menu.scrollHeight <= menu.clientHeight + 1 && ultimo.bottom <= pessoa.top + 1; })()",
        ),
        `CFG-09 menu inteiro visível com texto maior, sem o rodapé por cima de quem entrou (${rotulo})`,
      );
      conferir(await avaliar("(() => { const main = document.querySelector('main'); return main.scrollWidth <= main.clientWidth + 1; })()"), `CFG-09 ${rotulo} sem rolagem na horizontal`);
      await capturar(captura);
    }
    await tamanho(1440, 900);
    await clicar("[data-menu]", "Configurações");
    await esperarAte("location.pathname === '/configuracoes/'", "voltar para Configurações");
    await clicar("nav[aria-label='Seções das configurações'] button", "Aparência");
    await clicar("label", "Texto maior");
    await clicar("main button[type=submit]", "Salvar");
    await esperarAte("!document.documentElement.hasAttribute('data-texto-maior')", "texto maior desligado");
  }

  // 8b · Modo escuro (ESC-01, ESC-03): Escuro no pé do menu, as telas principais no escuro e Igual ao Windows.
  await clicar("aside [data-tema-opcao=escuro]");
  if (await esperarAte("document.documentElement.dataset.tema === 'escuro'", "ESC-01 Escuro no pé do menu troca o tema")) {
    conferir(await avaliar("getComputedStyle(document.documentElement).backgroundColor === 'rgb(14, 19, 17)'"), "ESC-01 fundo escuro aplicado na janela");
    for (const [rotulo, caminho, captura] of [
      ["Início", "/", "17-escuro-inicio"],
      ["Motoristas", "/motoristas/", "18-escuro-motoristas"],
      ["Viagens", "/viagens/", "19-escuro-viagens"],
    ]) {
      await clicar("[data-menu]", rotulo);
      await esperarAte(`location.pathname === '${caminho}'`, `ESC-03 abrir ${rotulo} no escuro`);
      await espera(500);
      await capturar(captura);
    }
    await clicar("main button", "Todas");
    await clicar("tbody tr", "2240");
    if (await esperarAte("location.pathname === '/viagens/v-2240/'", "ESC-03 abrir o relatório do Ônibus 2240 no escuro")) {
      await esperarAte(`${blocoDasPessoas}?.innerText.includes('Matrícula')`, "motorista do Ônibus 2240");
      await capturar("20-escuro-relatorio");
      const momentoComVideo = await avaliar("[...document.querySelectorAll('main li[id^=momento-]')].find((linha) => /trecho|trancado/.test(linha.innerText))?.id ?? null");
      if (momentoComVideo) {
        await clicar(`#${momentoComVideo} button`);
        if (await esperarAte(`Boolean(${janela})`, "ESC-03 janela do momento no escuro")) {
          await capturar("21-escuro-momento");
          await teclar("Escape");
          await esperarAte(`!${janela}`, "Esc fecha a janela do momento no escuro");
        }
      }
    }
    await clicar("[data-menu]", "Configurações");
    await esperarAte("location.pathname === '/configuracoes/'", "voltar para Configurações no escuro");
    await clicar("nav[aria-label='Seções das configurações'] button", "Aparência");
    if (await esperarAte("Boolean(document.querySelector('input[name=tema][value=escuro]')?.checked)", "ESC-01 Aparência mostra Escuro marcado")) {
      await capturar("22-escuro-aparencia");
      await clicar("label", "Igual ao Windows");
      await comando("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: "dark" }] });
      conferir(await esperarAte("document.documentElement.dataset.tema === 'escuro'", "Windows escuro"), "ESC-01 Igual ao Windows fica escuro com o Windows escuro");
      await comando("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: "light" }] });
      conferir(await esperarAte("document.documentElement.dataset.tema !== 'escuro'", "Windows claro"), "ESC-01 Igual ao Windows fica claro com o Windows claro");
      await comando("Emulation.setEmulatedMedia", { features: [] });
      await clicar("label", "Claro");
      conferir(await esperarAte("document.documentElement.dataset.tema !== 'escuro' && document.querySelector('input[name=tema][value=claro]').checked", "tema Claro"), "ESC-01 volta para o Claro");
    }
  }

  // 9 · Consulta: relatório sem vídeo e sem decisão (EQP-02); menu sem Equipe e Configurações.
  await abrir("/viagens/v-2240/?sessao=consulta");
  await esperarAte("document.querySelectorAll('[data-menu]').length >= 6", "menu da Consulta");
  const menuConsulta = await rotulosDoMenu();
  conferir(!menuConsulta.includes("Equipe") && !menuConsulta.includes("Configurações"), "MEN-01 Consulta sem Equipe e Configurações no menu");
  await esperarAte("document.querySelector('main')?.innerText.includes('Falta verificar')", "momentos da Consulta");
  conferir(
    await avaliar("![...document.querySelectorAll('main button:not([data-card])')].some((b) => /Confirmar|Alarme falso|Ver vídeo|Vídeo trancado|Desfazer|orientado/.test(b.textContent))"),
    "EQP-02 Consulta sem botão de vídeo nem de decisão",
  );
  await capturar("15-consulta-relatorio");
  await clicar("main [data-card]");
  if (await esperarAte(`Boolean(${janela})`, "janela do momento da Consulta")) {
    conferir(
      await avaliar(`(() => { const caixa = ${janela}; return caixa.innerText.includes('Sua função não vê os vídeos') && ![...caixa.querySelectorAll('button')].some((b) => /Confirmar|Alarme falso|Desfazer|orientado/.test(b.textContent)); })()`),
      "EQP-02 a janela do momento da Consulta sem vídeo e sem decisão",
    );
    await capturar("15-consulta-momento");
    await teclar("Escape");
  }

  // 10 · Supervisor: sem Equipe, Configurações e Primeiros passos.
  await abrir("/?sessao=supervisor");
  await esperarAte("document.querySelectorAll('[data-menu]').length >= 6", "menu do Supervisor");
  const menuSupervisor = await rotulosDoMenu();
  conferir(!menuSupervisor.includes("Equipe") && !menuSupervisor.includes("Configurações"), "MEN-01 Supervisor sem Equipe e Configurações no menu");
  await esperarAte("document.querySelector('main')?.innerText.includes('Avisos')", "Início do Supervisor carregado");
  conferir(!(await textoDaTela()).includes("Primeiros passos"), "GUI-07 Primeiros passos só aparecem para quem administra");
  await capturar("16-supervisor-inicio");

  conferir(erros.length === 0, erros.length ? `erros de JavaScript na janela: ${erros.join(" | ")}` : "nenhum erro de JavaScript na janela");
} finally {
  ws?.close();
  edge.kill();
}

console.log(falhas.length ? `\n${falhas.length} conferência(s) falharam.` : "\nTodas as conferências passaram.");
process.exitCode = falhas.length ? 1 : 0;
