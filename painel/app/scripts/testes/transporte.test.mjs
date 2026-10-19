// Spec 024 · painel no navegador: terceiro transporte da ponte ("servidor"), escolhido só no build web.
// O Node lê o bridge.ts direto (apaga os tipos sozinho). Os casos que dependem da variável do build rodam num processo
// filho, com e sem NEXT_PUBLIC_PAINEL_TRANSPORTE. Depois de `npm run build` (out/) e do build web (out-web/), confere
// também o que foi para cada pasta.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";
import { pathToFileURL } from "node:url";
import { CONTRATO_COMPLETO, transporteDoServidor } from "../../src/lib/bridge.ts";

const raiz = path.join(import.meta.dirname, "..", "..");
const bridgeUrl = pathToFileURL(path.join(raiz, "src", "lib", "bridge.ts")).href;

// Spec 030: fora da janela não existe mais demonstração; o gancho só avisa se alguém tentar carregar um módulo dela.
const GANCHO = `import { registerHooks } from "node:module";
registerHooks({ resolve: (especificador, contexto, proximo) => {
  if (/demo/.test(especificador)) globalThis.demoCarregada = true;
  return proximo(especificador, contexto);
} });
`;

function rodarFilho(codigo, env) {
  const limpo = { ...process.env };
  delete limpo.NEXT_PUBLIC_PAINEL_TRANSPORTE;
  delete limpo.NEXT_PUBLIC_PAINEL_BASE_PATH;
  const feito = spawnSync(process.execPath, ["--input-type=module", "-e", GANCHO + codigo], { env: { ...limpo, ...env }, encoding: "utf8" });
  assert.equal(feito.status, 0, feito.stderr);
  return JSON.parse(feito.stdout.trim().split("\n").at(-1));
}

/** fetch falso: guarda os pedidos e devolve a resposta escolhida. */
function servidorFalso(responder) {
  const pedidos = [];
  const buscar = async (url, init) => {
    pedidos.push({ url, init, corpo: JSON.parse(init.body) });
    return responder(url, init);
  };
  return { pedidos, buscar };
}

const json = (corpo, status = 200) => new Response(JSON.stringify(corpo), { status, headers: { "Content-Type": "application/json" } });

test("WEB-13 e SDF-01 sem a variável, o app instalado não escolhe o servidor; fora da janela o transporte é vazio", () => {
  const saida = rodarFilho(
    `const b = await import(${JSON.stringify(bridgeUrl)});
     globalThis.fetch = () => { throw new Error("não devia chamar a rede"); };
     const resposta = await b.bridge.estado();
     const lista = await b.bridge.motoristas_listar();
     console.log(JSON.stringify({ web: b.PAINEL_NA_WEB, origem: await b.origemDaPonte(), resposta, lista, demo: globalThis.demoCarregada === true }));`,
    {},
  );
  const fora = { ok: false, erro: "O painel abre pelo app RotaGuard Painel instalado neste computador." };
  assert.deepEqual(saida, { web: false, origem: "vazio", resposta: fora, lista: fora, demo: false });
});

test("WEB-13 com NEXT_PUBLIC_PAINEL_TRANSPORTE=servidor, a ponte é o servidor em {basePath}/api/ponte/{metodo}", () => {
  const saida = rodarFilho(
    `const pedidos = [];
     globalThis.fetch = async (url, init) => {
       pedidos.push({ url, credentials: init.credentials, cabecalho: init.headers["X-RotaGuard"], corpo: JSON.parse(init.body) });
       return new Response(JSON.stringify({ ok: true, dados: { ativado: true } }), { headers: { "Content-Type": "application/json" } });
     };
     const b = await import(${JSON.stringify(bridgeUrl)});
     const resposta = await b.bridge.estado();
     console.log(JSON.stringify({ web: b.PAINEL_NA_WEB, origem: await b.origemDaPonte(), resposta, pedidos, demo: globalThis.demoCarregada === true }));`,
    { NEXT_PUBLIC_PAINEL_TRANSPORTE: "servidor", NEXT_PUBLIC_PAINEL_BASE_PATH: "/painel" },
  );
  assert.equal(saida.web, true);
  assert.equal(saida.demo, false, "no build web a demonstração nunca carrega");
  assert.equal(saida.origem, "servidor");
  assert.deepEqual(saida.resposta, { ok: true, dados: { ativado: true } });
  assert.deepEqual(saida.pedidos, [{ url: "/painel/api/ponte/estado", credentials: "same-origin", cabecalho: "1", corpo: { args: [] } }]);
});

test("WEB-01 servidor: POST com JSON {args}, mesmo origem, cabeçalho X-RotaGuard e a resposta da ponte sem mudar", async () => {
  const { pedidos, buscar } = servidorFalso(() => json({ ok: true, dados: { id: 3, funcao: "supervisor" } }));
  const api = transporteDoServidor({ base: "/painel", buscar });
  const resposta = await api.entrar("paulo.souza", "frase de teste qualquer");
  assert.deepEqual(resposta, { ok: true, dados: { id: 3, funcao: "supervisor" } });
  const [pedido] = pedidos;
  assert.equal(pedido.url, "/painel/api/ponte/entrar");
  assert.equal(pedido.init.method, "POST");
  assert.equal(pedido.init.credentials, "same-origin");
  assert.equal(pedido.init.headers["X-RotaGuard"], "1");
  assert.equal(pedido.init.headers["Content-Type"], "application/json");
  assert.deepEqual(pedido.corpo, { args: ["paulo.souza", "frase de teste qualquer"] });
  assert.equal(transporteDoServidor({ base: "", buscar }).estado.length, 0, "um método para cada nome do contrato");
  await transporteDoServidor({ base: "", buscar }).estado();
  assert.equal(pedidos.at(-1).url, "/api/ponte/estado", "sem basePath, a API fica na raiz");
});

test("WEB-06 o código de ativação vai no corpo (campo ativacao), fora dos argumentos da ponte", async () => {
  const { pedidos, buscar } = servidorFalso(() => json({ ok: true, dados: { codigo_recuperacao: "AAAAA-BBBBB" } }));
  const api = transporteDoServidor({ base: "/painel", buscar });
  const admin = { nome: "Maria Santos", usuario: "maria.santos", senha: "frase de teste qualquer" };
  await api.ativar_local("Transportes Lima", admin, { codigo_ativacao: "  codigo-de-teste  " });
  await api.ativar_com_arquivo("{}", admin, { codigo_ativacao: "outro-codigo" });
  await api.ativar_local("Transportes Lima", admin);
  assert.deepEqual(pedidos[0].corpo, { args: ["Transportes Lima", admin], ativacao: "codigo-de-teste" });
  assert.deepEqual(pedidos[1].corpo, { args: ["{}", admin], ativacao: "outro-codigo" });
  assert.deepEqual(pedidos[2].corpo, { args: ["Transportes Lima", admin] });
  for (const pedido of pedidos) assert.ok(!Object.keys(pedido.init.headers).some((nome) => /ativa/i.test(nome)), "código fora dos cabeçalhos");
});

test("WEB-08 arquivo devolvido pelo servidor vira download no navegador; a tela recebe a resposta de sempre", async () => {
  const conteudo = JSON.stringify({ formato: "rotaguard-dados-motorista/1" });
  const arquivo = { nome: "rotaguard-motorista-carlos-m.json", tipo: "application/json", base64: Buffer.from(conteudo).toString("base64") };
  const { buscar } = servidorFalso(() => json({ ok: true, dados: { caminho: arquivo.nome }, arquivo }));
  const baixados = [];
  const api = transporteDoServidor({ base: "/painel", buscar, baixar: (a) => baixados.push(a), abrir: () => assert.fail("não abre aba") });
  const resposta = await api.motorista_exportar(1);
  assert.deepEqual(baixados, [arquivo]);
  assert.equal(resposta.ok, true);
  assert.equal("arquivo" in resposta, false, "o arquivo não chega às telas");
  assert.match(resposta.dados.caminho, /^rotaguard-motorista-carlos-m\.json \(pasta de downloads do navegador\)$/);
  const copia = await transporteDoServidor({
    base: "/painel",
    buscar: async () => json({ ok: true, dados: { caminho: "c.rotaguard-copia", bytes: 10 }, arquivo: { ...arquivo, nome: "c.rotaguard-copia" } }),
    baixar: () => {},
  }).copia_fazer("frase de teste qualquer");
  assert.equal(copia.dados.bytes, 10);
});

test("WEB-09 PDF do termo abre em outra aba; foto continua vindo na resposta", async () => {
  const pdf = { nome: "termo-carlos.pdf", tipo: "application/pdf", base64: Buffer.from("%PDF-1.4").toString("base64") };
  const abertos = [];
  const api = transporteDoServidor({
    base: "/painel",
    buscar: async () => json({ ok: true, dados: { tipo: "pdf", nome: pdf.nome, aberto: true }, arquivo: pdf }),
    abrir: (a) => abertos.push(a),
    baixar: () => assert.fail("PDF do termo abre, não baixa"),
  });
  assert.deepEqual(await api.termo_ver(1), { ok: true, dados: { tipo: "pdf", nome: pdf.nome, aberto: true } });
  assert.deepEqual(abertos, [pdf]);
  const foto = { ok: true, dados: { tipo: "imagem", nome: "t.png", conteudo: "data:image/png;base64,AAAA" } };
  assert.deepEqual(await transporteDoServidor({ base: "", buscar: async () => json(foto) }).termo_ver(2), foto);
});

test("WEB-12 respostas de erro do servidor (429, 403, 404) chegam como Resposta; o resto vira frase simples", async () => {
  const espera = { ok: false, erro: "Muitas tentativas. Espere 60 segundos e tente de novo.", codigo: "espera", esperar_s: 60 };
  assert.deepEqual(await transporteDoServidor({ base: "", buscar: async () => json(espera, 429) }).entrar("a", "b"), espera);
  const recusa = { ok: false, erro: "Pedido recusado.", codigo: "sem_permissao" };
  assert.deepEqual(await transporteDoServidor({ base: "", buscar: async () => json(recusa, 403) }).estado(), recusa);
  const html = await transporteDoServidor({ base: "", buscar: async () => new Response("<html>502</html>", { status: 502 }) }).estado();
  assert.equal(html.ok, false);
  assert.match(html.erro, /servidor do painel/);
  const semRede = await transporteDoServidor({
    base: "",
    buscar: async () => {
      throw new TypeError("Failed to fetch");
    },
  }).estado();
  assert.equal(semRede.ok, false);
  assert.match(semRede.erro, /conexão/);
  const grande = await transporteDoServidor({ base: "", buscar: async () => new Response("", { status: 413 }) }).termo_importar(1, { nome: "a.pdf", conteudo_base64: "" }, { data: "2026-10-01" });
  assert.match(grande.erro, /16 MB/);
});

test("contrato completo e a tela de ativação pede o código só no painel pela web", () => {
  assert.equal(CONTRATO_COMPLETO, true);
  const portao = readFileSync(path.join(raiz, "src", "components", "auth-gate.tsx"), "utf8");
  assert.match(portao, /PAINEL_NA_WEB &&/, "campo do código só aparece no build web");
  assert.match(portao, /codigo_ativacao/);
  assert.match(portao, /Código de ativação/);
  const bridge = readFileSync(path.join(raiz, "src", "lib", "bridge.ts"), "utf8");
  assert.doesNotMatch(bridge, /localStorage|sessionStorage|document\.cookie/, "ENT-07: nada da sessão no navegador");
});

function arquivosJs(pasta) {
  return readdirSync(pasta).flatMap((nome) => {
    const caminho = path.join(pasta, nome);
    if (statSync(caminho).isDirectory()) return arquivosJs(caminho);
    return nome.endsWith(".js") ? [caminho] : [];
  });
}
const contem = (pasta, texto) => arquivosJs(path.join(pasta, "_next")).some((arquivo) => readFileSync(arquivo, "utf8").includes(texto));

test("WEB-13 build: out/ (app instalado) sem o transporte servidor; out-web/ com ele e com /painel nos endereços", (t) => {
  const normal = path.join(raiz, "out");
  const web = path.join(raiz, "out-web");
  if (!existsSync(normal) && !existsSync(web)) {
    t.skip("rode npm run build e o build web antes");
    return;
  }
  if (existsSync(normal)) {
    assert.equal(contem(normal, "X-RotaGuard"), false, "o app instalado não leva o transporte servidor");
    assert.doesNotMatch(readFileSync(path.join(normal, "index.html"), "utf8"), /\/painel\/_next\//, "app instalado carrega da raiz");
  }
  if (existsSync(web)) {
    assert.equal(contem(web, "X-RotaGuard"), true, "o build web fala com o servidor");
    assert.match(readFileSync(path.join(web, "index.html"), "utf8"), /\/painel\/_next\//, "build web carrega de /painel/");
  }
});
