// Spec 017 · guia de uso do painel. Roda sem build: o Node 22.18+ lê o guide.ts direto (apaga os tipos sozinho).
import assert from "node:assert/strict";
import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";
import { AVISO_ALERTAS, CAPITULOS, EXPLICACAO_ALERTA, buscarNoGuia, normalizar } from "../../src/content/guide.ts";

const raiz = path.join(import.meta.dirname, "..", "..");
const tipos = JSON.parse(readFileSync(path.join(raiz, "src", "content", "tipos-de-evento.json"), "utf8"));

const ORDEM = [
  ["primeiros-passos", "Primeiros passos"],
  ["veiculo-chega", "Quando o veículo chega"],
  ["verificar-momentos", "Verificar os momentos"],
  ["alertas", "O que cada alerta quer dizer"],
  ["motoristas", "Motoristas e termo de ciência"],
  ["veiculos", "Veículos e caixas"],
  ["equipe", "Equipe e acessos"],
  ["copia", "Cópia de segurança"],
  ["problemas", "Quando algo dá errado"],
  ["privacidade", "Privacidade e LGPD"],
];

test("GUI-01 os 10 capítulos existem, em ordem, com passos numerados curtos e 'Se der errado'", () => {
  assert.deepEqual(
    CAPITULOS.map((capitulo) => [capitulo.id, capitulo.titulo]),
    ORDEM,
  );
  CAPITULOS.forEach((capitulo, indice) => {
    assert.equal(capitulo.numero, indice + 1, `${capitulo.id}: número fora de ordem`);
    assert.ok(capitulo.topicos.length > 0, `${capitulo.id}: sem passos`);
    for (const topico of capitulo.topicos) {
      assert.ok(topico.passos.length > 0, `${capitulo.id}/${topico.id}: tópico sem passos`);
      for (const passo of topico.passos) {
        assert.ok(passo.trim().length > 0, `${capitulo.id}/${topico.id}: passo vazio`);
        assert.ok(passo.length <= 120, `${capitulo.id}/${topico.id}: passo longo demais (${passo.length}): ${passo}`);
      }
    }
    const ids = capitulo.topicos.map((topico) => topico.id);
    assert.equal(new Set(ids).size, ids.length, `${capitulo.id}: tópico repetido`);
    assert.ok(capitulo.seDerErrado.problema.trim() && capitulo.seDerErrado.solucao.trim(), `${capitulo.id}: sem 'Se der errado'`);
  });
});

test("GUI-03 todo tipo de alerta de tipos-de-evento.json tem explicação no capítulo 4, com o mesmo nome", () => {
  const capitulo = CAPITULOS.find((item) => item.id === "alertas");
  assert.ok(capitulo?.alertas, "capítulo 4 sem a lista de alertas");
  assert.match(capitulo.resumo, /ajuda a avaliação e não é diagnóstico/);
  assert.equal(capitulo.resumo, AVISO_ALERTAS);
  for (const [tipo, { rotulo }] of Object.entries(tipos)) {
    const alerta = capitulo.alertas.find((item) => item.tipo === tipo);
    assert.ok(alerta, `${tipo} sem explicação no guia`);
    assert.equal(alerta.rotulo, rotulo, `${tipo}: nome diferente do tipos-de-evento.json`);
    assert.ok(EXPLICACAO_ALERTA[tipo]?.trim(), `${tipo}: frase simples faltando`);
    assert.equal(alerta.explicacao, EXPLICACAO_ALERTA[tipo]);
  }
  for (const tipo of Object.keys(EXPLICACAO_ALERTA)) assert.ok(tipos[tipo], `explicação de ${tipo}, que não existe no JSON`);
});

test("GUI-04 busca sem acento e sem maiúscula acha 'Esqueci a senha' com 'SENHA' e 'senha'", () => {
  for (const consulta of ["SENHA", "senha", "  Senha "]) {
    const resultados = buscarNoGuia(consulta);
    const esqueci = resultados.find((item) => item.titulo === "Esqueci a senha");
    assert.ok(esqueci, `"${consulta}" não achou Esqueci a senha`);
    assert.equal(esqueci.capituloNumero, 9);
    assert.equal(normalizar(esqueci.trecho.achado), "senha", `"${consulta}": trecho destacado errado`);
    const adicionar = resultados.find((item) => item.titulo === "Adicionar pessoa");
    assert.ok(adicionar, `"${consulta}" não achou Adicionar pessoa`);
    assert.equal(adicionar.capituloNumero, 7);
    assert.equal(normalizar(adicionar.trecho.achado), "senha");
  }
  const semAcento = buscarNoGuia("copia de seguranca");
  assert.ok(semAcento.some((item) => item.capituloId === "copia"), "sem acento não achou Cópia de segurança");
  const comAcento = buscarNoGuia("CÓPIA");
  assert.equal(comAcento[0].trecho.achado.toLowerCase(), "cópia", "o trecho destacado mantém o acento do texto");
  assert.deepEqual(buscarNoGuia("xyzabc"), [], "busca sem resultado devolve lista vazia");
  assert.deepEqual(buscarNoGuia("   "), []);
});

test("GUI-05 nenhuma palavra técnica da decisão 9 no texto do guia", () => {
  const proibidas = /\b(hash|blocos?|perclos|tokens?|sessao|sessoes|api|banco de dados|criptograf\w*)\b/g;
  const textos = CAPITULOS.flatMap((capitulo) => [
    capitulo.titulo,
    capitulo.resumo,
    capitulo.seDerErrado.problema,
    capitulo.seDerErrado.solucao,
    ...capitulo.topicos.flatMap((topico) => [topico.titulo, ...topico.passos]),
    ...(capitulo.alertas ?? []).flatMap((alerta) => [alerta.rotulo, alerta.explicacao]),
  ]);
  for (const texto of textos) {
    const achadas = normalizar(texto).match(proibidas);
    assert.equal(achadas, null, `palavra técnica "${achadas}" em: ${texto}`);
  }
});

function arquivosFonte(pasta = path.join(raiz, "src")) {
  return readdirSync(pasta).flatMap((nome) => {
    const caminho = path.join(pasta, nome);
    if (statSync(caminho).isDirectory()) return arquivosFonte(caminho);
    return /\.tsx?$/.test(nome) ? [caminho] : [];
  });
}

test("GUI-02 (parte da tela) todo link para o guia aponta para um capítulo que existe", () => {
  const ids = new Set(CAPITULOS.map((capitulo) => capitulo.id));
  let links = 0;
  for (const caminho of arquivosFonte()) {
    const texto = readFileSync(caminho, "utf8");
    for (const [, id] of texto.matchAll(/capitulo:\s*"([\w-]+)"|capitulo=([\w-]+)/g).map((m) => [m[0], m[1] ?? m[2]])) {
      links += 1;
      assert.ok(ids.has(id), `${path.relative(raiz, caminho)}: capítulo "${id}" não existe no guia`);
    }
  }
  assert.ok(links > 0, "nenhuma tela aponta para o guia");
});
