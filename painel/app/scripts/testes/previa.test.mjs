// Spec 012 · painel da empresa (prévia 2 aprovada em 14/09/2026): dados coerentes com o servidor, momentos agrupados,
// sem localização, sem diagnóstico, sem os vícios visuais rejeitados e com as telas exportadas.
// Spec 030: a viagem de exemplo da prévia mora só nos testes (fixtures/demo.json); as regras continuam conferidas nela.
// Rodar depois de `npm run build` para as verificações que leem a pasta out/.
import assert from "node:assert/strict";
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { registerHooks } from "node:module";
import path from "node:path";
import { test } from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";

const raiz = path.join(import.meta.dirname, "..", "..");
const src = path.join(raiz, "src");
const repositorio = path.join(raiz, "..", "..");
const demo = JSON.parse(readFileSync(path.join(raiz, "scripts", "testes", "fixtures", "demo.json"), "utf8"));
const saida = path.join(raiz, "out");

// Os momentos (src/content/moments.ts) importam "@/..." do Next: ganchos do Node resolvem o alias e os .json.
registerHooks({
  resolve(especificador, contexto, proximo) {
    const alvo = especificador.startsWith("@/") ? pathToFileURL(path.join(src, especificador.slice(2))).href : especificador;
    try {
      return proximo(alvo, contexto);
    } catch (erro) {
      for (const fim of [".ts", "/index.ts"]) {
        try {
          return proximo(alvo + fim, contexto);
        } catch {
          /* tenta o próximo */
        }
      }
      throw erro;
    }
  },
  load(url, contexto, proximo) {
    if (url.endsWith(".json")) return { format: "module", source: `export default ${readFileSync(fileURLToPath(url), "utf8")};`, shortCircuit: true };
    return proximo(url, contexto);
  },
});
const { momentosDaViagem } = await import("../../src/content/moments.ts");

function arquivosFonte(pasta = src) {
  return readdirSync(pasta).flatMap((nome) => {
    const caminho = path.join(pasta, nome);
    if (statSync(caminho).isDirectory()) return arquivosFonte(caminho);
    return /\.(tsx?|css|json)$/.test(nome) ? [caminho] : [];
  });
}
const fontes = arquivosFonte().map((caminho) => ({ caminho, texto: readFileSync(caminho, "utf8") }));

// Tipos, categorias e regra de revisão lidos do próprio servidor (servidor/backend/alert_types.py).
const tiposPy = readFileSync(path.join(repositorio, "servidor", "backend", "alert_types.py"), "utf8");
const rotulos = new Set([...tiposPy.matchAll(/^\s+"(\w+)": "/gm)].map((m) => m[1]));
const blocoCategorias = tiposPy.slice(tiposPy.indexOf("CATEGORIES = {"), tiposPy.indexOf("_CATEGORY_BY_TYPE"));
const categoriaDe = {};
for (const [, categoria, tipos] of blocoCategorias.matchAll(/"(\w+)": \{([^}]*)\}/g)) {
  for (const [, tipo] of tipos.matchAll(/"(\w+)"/g)) categoriaDe[tipo] = categoria;
}
const revisaveis = new Set([...tiposPy.match(/REVIEWABLE_CATEGORIES = \{([^}]*)\}/)[1].matchAll(/"(\w+)"/g)].map((m) => m[1]));
const riscoMinimo = Number(tiposPy.match(/MIN_RISK_TO_REVIEW = (\d+)/)[1]);
const precisaRevisao = (evento) => revisaveis.has(categoriaDe[evento.tipo]) && evento.risco >= riscoMinimo;

test("PRV-06 dados: cada evento usa um tipo do servidor e fica dentro da viagem, em ordem", () => {
  for (const viagem of demo.viagens) {
    const saidaEm = Date.parse(viagem.saida);
    const chegadaEm = Date.parse(viagem.chegada);
    assert.ok(chegadaEm > saidaEm, `${viagem.id}: chegada antes da saída`);
    let anterior = saidaEm;
    for (const evento of viagem.eventos) {
      assert.ok(rotulos.has(evento.tipo), `${viagem.id}: tipo ${evento.tipo} não existe no servidor`);
      const quando = Date.parse(evento.hora);
      assert.ok(quando >= anterior && quando <= chegadaEm, `${viagem.id}: ${evento.id} fora da viagem ou fora de ordem`);
      anterior = quando;
    }
    const trechos = viagem.jornada.map((parte) => [Date.parse(parte.inicio), Date.parse(parte.fim)]);
    assert.equal(trechos[0][0], saidaEm, `${viagem.id}: jornada não começa na saída`);
    assert.equal(trechos.at(-1)[1], chegadaEm, `${viagem.id}: jornada não termina na chegada`);
    for (const episodio of viagem.episodios) {
      const eventos = viagem.eventos.filter((evento) => evento.episodio === episodio.id);
      assert.ok(eventos.length >= 2, `${viagem.id}: episódio ${episodio.id} precisa de recorrência`);
    }
  }
});

test("PRV-07 dados: revisão só para eventos que o servidor manda revisar (categoria revisável e risco mínimo)", () => {
  const revisados = demo.viagens.flatMap((viagem) => viagem.eventos.filter((evento) => evento.revisao));
  for (const evento of revisados) assert.ok(precisaRevisao(evento), `${evento.id} revisado sem precisar de revisão`);
  const pendentes = demo.viagens.flatMap((v) => v.eventos.filter((e) => precisaRevisao(e) && !e.revisao));
  assert.ok(pendentes.length >= 3, "o exemplo precisa de momentos para verificar");
  assert.ok(demo.viagens.flatMap((v) => v.eventos).some((e) => !precisaRevisao(e)), "precisa de evento que não entra na verificação");
});

test("PRV-08 tipos de evento do painel com o mesmo nome e categoria do servidor", () => {
  const tipos = JSON.parse(readFileSync(path.join(src, "content", "tipos-de-evento.json"), "utf8"));
  for (const [tipo, { rotulo, categoria }] of Object.entries(tipos)) {
    const noServidor = tiposPy.match(new RegExp(`^\\s+"${tipo}": "([^"]+)"`, "m"));
    assert.ok(noServidor, `${tipo} não existe no servidor`);
    assert.equal(rotulo, noServidor[1], `${tipo}: nome diferente do servidor`);
    assert.equal(categoria, categoriaDe[tipo], `${tipo}: categoria diferente do servidor`);
  }
  for (const viagem of demo.viagens) for (const evento of viagem.eventos) assert.ok(tipos[evento.tipo], `${evento.tipo} sem nome no painel`);
});

test("PRV-09 momentos agrupados: episódio repetido vira um momento só; decisões que vieram com a viagem", () => {
  const momentos = Object.fromEntries(demo.viagens.map((viagem) => [viagem.id, momentosDaViagem(viagem)]));
  assert.equal(momentos["v-2240"].length, 4, "4 momentos para verificar");
  assert.ok(momentos["v-2240"].some((momento) => momento.titulo === "Sono repetido: olhos fechados 2 vezes"));
  assert.equal(momentos["v-3310"].length, 2);
  assert.deepEqual(
    momentos["v-1187"].map((momento) => [momento.decisaoInicial?.resultado, momento.decisaoInicial?.orientado]),
    [
      ["alarme_falso", false],
      ["confirmado", true],
    ],
    "orientado vira confirmado com orientação",
  );
  assert.deepEqual(
    momentos["v-2240"].map((momento) => momento.numero),
    [1, 2, 3, 4],
    "numerados na ordem da viagem",
  );
});

test("PRV-03 sem mapa, GPS nem rastreamento: o produto não registra localização", () => {
  for (const { caminho, texto } of fontes) {
    assert.doesNotMatch(texto, /\bGPS\b|rastre(?:a|io|ame)|\bmapas?\b|geolocaliza|latitude|longitude/i, caminho);
  }
});

test("PRV-05 nome visível RotaGuard, sem DriveSafe", () => {
  for (const { caminho, texto } of fontes) assert.doesNotMatch(texto, /drive\s?safe/i, caminho);
});

test("PRV-10 sem os vícios da prévia rejeitada: rótulo em maiúsculas, legenda de gravidade e fonte mono", () => {
  for (const { caminho, texto } of fontes.filter((fonte) => /\.(tsx|css)$/.test(fonte.caminho))) {
    assert.doesNotMatch(texto, /\buppercase\b|text-transform:\s*uppercase/, `${caminho}: rótulo em maiúsculas`);
    assert.doesNotMatch(texto, /Gravidade (alta|média|leve)/i, `${caminho}: legenda de gravidade`);
    assert.doesNotMatch(texto, /font-mono|JetBrains/, `${caminho}: fonte mono`);
  }
});

test("PRV-04 relatório diz na tela que os alertas não são diagnóstico e ajudam a avaliação de quem verifica", () => {
  const relatorio = readFileSync(path.join(src, "components", "trip", "trip-report.tsx"), "utf8");
  assert.match(relatorio, /não (é|são) diagnóstico/i);
  assert.match(relatorio, /sua avaliação/i);
});

const exportado = existsSync(path.join(saida, "index.html"));
const telas = ["viagens", "viagens/relatorio", "motoristas", "veiculos", "remotos", "equipe", "configuracoes", "guia", "ao-vivo"].map((tela) => `${tela}/index.html`);
const paginas = ["index.html", ...telas];

test("PRV-01 exportação estática com o Início, as telas do menu, o teste local e o relatório da viagem", { skip: !exportado && "sem build" }, () => {
  for (const pagina of paginas) assert.ok(existsSync(path.join(saida, pagina)), `falta out/${pagina}`);
  assert.ok(!existsSync(path.join(saida, "revisao")) && !existsSync(path.join(saida, "frota")), "telas da prévia rejeitada ainda exportadas");
});

test("PRV-02 e SDF-02 cada tela exportada está em pt-BR e sem aviso de dados fictícios", { skip: !exportado && "sem build" }, () => {
  for (const pagina of paginas) {
    const html = readFileSync(path.join(saida, pagina), "utf8");
    assert.match(html, /<html[^>]*lang="pt-BR"/, pagina);
    assert.doesNotMatch(html, /fictíci/i, pagina);
  }
});
