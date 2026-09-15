// Spec 012 · painel da empresa (prévia 2 aprovada em 14/09/2026): dados coerentes com o servidor, momentos agrupados,
// sem localização, sem diagnóstico, sem os vícios visuais rejeitados e com as telas exportadas.
// Rodar depois de `npm run build` para as verificações que leem a pasta out/.
import assert from "node:assert/strict";
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";

const raiz = path.join(import.meta.dirname, "..", "..");
const repositorio = path.join(raiz, "..", "..");
const demo = JSON.parse(readFileSync(path.join(raiz, "src", "content", "demo.json"), "utf8"));
const saida = path.join(raiz, "out");

function arquivosFonte(pasta = path.join(raiz, "src")) {
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
  assert.ok(pendentes.length >= 3, "a prévia precisa de momentos para verificar");
  assert.ok(demo.viagens.flatMap((v) => v.eventos).some((e) => !precisaRevisao(e)), "precisa de evento que não entra na verificação");
});

test("PRV-08 tipos de evento do painel com o mesmo nome e categoria do servidor", () => {
  const tipos = JSON.parse(readFileSync(path.join(raiz, "src", "content", "tipos-de-evento.json"), "utf8"));
  for (const [tipo, { rotulo, categoria }] of Object.entries(tipos)) {
    const noServidor = tiposPy.match(new RegExp(`^\\s+"${tipo}": "([^"]+)"`, "m"));
    assert.ok(noServidor, `${tipo} não existe no servidor`);
    assert.equal(rotulo, noServidor[1], `${tipo}: nome diferente do servidor`);
    assert.equal(categoria, categoriaDe[tipo], `${tipo}: categoria diferente do servidor`);
  }
  for (const viagem of demo.viagens) for (const evento of viagem.eventos) assert.ok(tipos[evento.tipo], `${evento.tipo} sem nome no painel`);
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

const exportado = existsSync(path.join(saida, "index.html"));
const relatorios = demo.viagens.map((v) => `viagens/${v.id}/index.html`);
const telas = ["viagens", "motoristas", "veiculos", "equipe", "configuracoes", "guia", "ao-vivo"].map((tela) => `${tela}/index.html`);
const paginas = ["index.html", ...telas, ...relatorios];
// Texto visível da página exportada, sem tags nem scripts (um aviso só em comentário do código não conta).
const textoVisivel = (pagina) =>
  readFileSync(path.join(saida, pagina), "utf8")
    .replace(/<script[\s\S]*?<\/script>/g, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/<!-- -->/g, "")
    .replace(/\s+/g, " ");

test("PRV-01 exportação estática com o Início, as telas do menu, o teste local e o relatório de cada viagem", { skip: !exportado && "sem build" }, () => {
  for (const pagina of paginas) assert.ok(existsSync(path.join(saida, pagina)), `falta out/${pagina}`);
  assert.ok(!existsSync(path.join(saida, "revisao")) && !existsSync(path.join(saida, "frota")), "telas da prévia rejeitada ainda exportadas");
});

test("PRV-02 cada tela exportada avisa que os dados são fictícios e está em pt-BR", { skip: !exportado && "sem build" }, () => {
  for (const pagina of paginas) {
    const html = readFileSync(path.join(saida, pagina), "utf8");
    assert.match(textoVisivel(pagina), /dados fictícios/i, pagina);
    assert.match(html, /<html[^>]*lang="pt-BR"/, pagina);
  }
});

test("PRV-04 relatório diz na tela que os alertas não são diagnóstico e ajudam a avaliação de quem verifica", { skip: !exportado && "sem build" }, () => {
  for (const pagina of relatorios) {
    const texto = textoVisivel(pagina);
    assert.match(texto, /não (é|são) diagnóstico/i, pagina);
    assert.match(texto, /sua avaliação/i, pagina);
  }
});

test("PRV-09 momentos agrupados e contagens da tela Viagens", { skip: !exportado && "sem build" }, () => {
  assert.match(textoVisivel("viagens/v-2240/index.html"), /4 momentos para você verificar/);
  assert.match(textoVisivel("viagens/v-2240/index.html"), /Sono repetido: olhos fechados 2 vezes/);
  assert.match(textoVisivel("viagens/v-3310/index.html"), /2 momentos para você verificar/);
  assert.match(textoVisivel("index.html"), /Caixa do Ônibus 2258 conectada/);
  const viagens = textoVisivel("viagens/index.html");
  assert.match(viagens, /4 para ver/);
  assert.match(viagens, /2 para ver/);
  assert.match(viagens, /Para verificar 2/, "aba com as 2 viagens que faltam verificar");
  assert.match(viagens, /Revisadas 1/, "a viagem v-1187 já foi verificada");
  assert.match(viagens, /Todas 3/);
});
