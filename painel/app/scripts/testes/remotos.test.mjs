// Spec 026 · Testes à distância e Configurações › Central no painel executável (PCE-05 a PCE-10, lado da tela).
// A demonstração em memória (fixture desde a spec 030, fora do app) é importada de verdade: ganchos do Node resolvem o
// "@/" do Next e os .json. As funções da tela (remote-data.ts) não importam nada e rodam direto.
import assert from "node:assert/strict";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { registerHooks } from "node:module";
import path from "node:path";
import { test } from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";

const raiz = path.join(import.meta.dirname, "..", "..");
const src = path.join(raiz, "src");
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

const { criarDemonstracao } = await import("./fixtures/demo-backend.ts");
const remoto = await import("../../src/components/remote/remote-data.ts");
const tipos = JSON.parse(readFileSync(path.join(src, "content", "tipos-de-evento.json"), "utf8"));
const ler = (...partes) => readFileSync(path.join(raiz, ...partes), "utf8");
const pastaRemoto = path.join(src, "components", "remote");
const fontesRemoto = () => readdirSync(pastaRemoto).map((nome) => ler("src", "components", "remote", nome)).join("\n");
const ADMIN = { nome: "Marina Lopes", usuario: "marina.lopes", senha: "frase comprida de teste um" };
const dados = (resposta) => {
  assert.equal(resposta.ok, true, JSON.stringify(resposta));
  return resposta.dados;
};

async function demoComPessoas() {
  const api = criarDemonstracao();
  dados(await api.ativar_local("Viação Demonstração", ADMIN));
  const supervisor = dados(await api.equipe_adicionar({ nome: "Paulo Reis", usuario: "paulo.reis", funcao: "supervisor" }));
  const consulta = dados(await api.equipe_adicionar({ nome: "Ana Souza", usuario: "ana.souza", funcao: "consulta" }));
  async function entrar(usuario, temporaria, nova) {
    await api.sair();
    dados(await api.entrar(usuario, temporaria));
    dados(await api.trocar_senha(temporaria, nova));
  }
  return {
    api,
    comoSupervisor: () => entrar("paulo.reis", supervisor.senha_temporaria, "frase comprida de teste dois"),
    comoConsulta: () => entrar("ana.souza", consulta.senha_temporaria, "frase comprida de teste tres"),
  };
}

test("PCE-08 demonstração: central e testes à distância com 2 computadores, um testando agora, sessões e trechos", async () => {
  const { api } = await demoComPessoas();
  const estado = dados(await api.central_estado());
  assert.equal(estado.conectado, true);
  assert.equal(estado.endereco_padrao, "https://rotaguard.acexpartners.com.br");
  const lista = dados(await api.remotos_listar());
  assert.equal(lista.aparelhos.length, 2);
  assert.deepEqual(lista.aparelhos.map((item) => item.testando_agora), [true, false], "quem testa vem primeiro");
  assert.equal(lista.aparelhos[0].risco_atual, 2);
  assert.ok(lista.sessoes.length >= 2 && lista.sessoes.some((sessao) => sessao.em_andamento));
  const datas = lista.sessoes.map((sessao) => sessao.iniciada_em);
  assert.deepEqual(datas, [...datas].sort().reverse(), "sessão mais nova primeiro");
  const atual = lista.sessoes.find((sessao) => sessao.em_andamento);
  const detalhe = dados(await api.remotos_sessao(atual.uid));
  assert.ok(detalhe.eventos.length >= 2 && detalhe.trechos.length >= 2 && detalhe.pode_ver_trechos);
  const tocavel = dados(await api.remotos_trecho(detalhe.trechos.find((trecho) => trecho.formato === "rgclip").uid));
  assert.equal(tocavel.disponivel, true);
  assert.ok(tocavel.quadros.length >= 10 && tocavel.quadros.every((quadro) => quadro.url.startsWith("data:image/svg+xml")));
  const video = dados(await api.remotos_trecho(detalhe.trechos.find((trecho) => trecho.formato === "mp4").uid));
  assert.equal(video.disponivel, false);
  assert.match(video.motivo, /demonstração indisponível/);
  assert.equal((await api.remotos_sessao("nao-existe")).codigo, "nao_encontrado");
});

test("PCE-06 e PCE-09 na demonstração: código ABCD-2345 por 30 min; desconectar mantém o que já foi baixado", async () => {
  const { api } = await demoComPessoas();
  const codigo = dados(await api.central_gerar_codigo("Notebook da Ana"));
  assert.match(codigo.codigo, /^[A-HJ-NP-Z2-9]{4}-[A-HJ-NP-Z2-9]{4}$/, "sem letras ambíguas");
  assert.equal(codigo.validade_min, 30);
  assert.ok(Math.abs(Date.parse(codigo.expira_em) - Date.now() - 30 * 60_000) < 5_000);
  const recusa = await api.central_conectar("http://rotaguard.acexpartners.com.br", "gestor@viacao.test", "senha-de-teste");
  assert.equal(recusa.ok, false);
  assert.equal(recusa.campo, "endereco");
  const depois = dados(await api.central_desconectar());
  assert.equal(depois.conectado, false);
  const lista = dados(await api.remotos_listar());
  assert.ok(lista.sessoes.length >= 2, "PCE-09 mantém as sessões");
  assert.equal(lista.aparelhos.some((item) => item.testando_agora), false, "desconectado, ninguém aparece testando");
  assert.equal((await api.central_gerar_codigo(null)).ok, false, "sem conexão não gera código");
  dados(await api.central_conectar("https://rotaguard.acexpartners.com.br", "gestor@viacao.test", "senha-de-teste"));
  const acoes = dados(await api.atividades_listar({})).itens.map((item) => item.acao);
  for (const acao of ["gerou código para outro computador", "desconectou da central", "conectou à central"]) assert.ok(acoes.includes(acao), acao);
  assert.ok(!JSON.stringify(dados(await api.atividades_listar({}))).includes(codigo.codigo), "o código não vai para o registro");
});

test("PCE-07 Consulta não vê trechos; supervisor vê; só o administrador conecta e gera código", async () => {
  const pessoas = await demoComPessoas();
  const lista = dados(await pessoas.api.remotos_listar());
  const sessao = lista.sessoes.find((item) => item.em_andamento);
  await pessoas.comoSupervisor();
  const vista = dados(await pessoas.api.remotos_sessao(sessao.uid));
  assert.ok(vista.trechos.length > 0);
  assert.equal((await pessoas.api.central_gerar_codigo("x")).codigo, "sem_permissao");
  await pessoas.comoConsulta();
  const detalhe = dados(await pessoas.api.remotos_sessao(sessao.uid));
  assert.equal(detalhe.pode_ver_trechos, false);
  assert.deepEqual(detalhe.trechos, []);
  assert.ok(detalhe.eventos.length > 0 && detalhe.eventos.every((evento) => evento.trecho_uid === null));
  assert.equal((await pessoas.api.remotos_trecho(vista.trechos[0].uid)).codigo, "sem_permissao");
  assert.equal((await pessoas.api.central_conectar("https://x.com.br", "a@b.c", "senha-de-teste")).codigo, "sem_permissao");
  assert.equal(dados(await pessoas.api.central_estado()).conectado, true, "Consulta vê o estado da central");
});

test("textos da tela: risco, duração, há quanto tempo, deslocamento na linha do tempo e resumos com número real", () => {
  assert.deepEqual(remoto.textoRisco(3), { texto: "risco alto", alarme: true });
  assert.deepEqual(remoto.textoRisco(2), { texto: "risco médio", alarme: true });
  assert.deepEqual(remoto.textoRisco(1), { texto: "risco baixo", alarme: false });
  assert.deepEqual(remoto.textoRisco(null), { texto: "sem alerta", alarme: false });
  assert.equal(remoto.duracaoTexto(42), "42 s");
  assert.equal(remoto.duracaoTexto(18 * 60), "18 min");
  assert.equal(remoto.duracaoTexto(65 * 60), "1 h 05");
  assert.equal(remoto.duracaoTexto(null), "sem duração");
  const agora = Date.parse("2026-10-19T14:00:00Z");
  assert.equal(remoto.haQuanto("2026-10-19T13:59:48Z", agora), "há 12 s");
  assert.equal(remoto.haQuanto("2026-10-19T13:57:00Z", agora), "há 3 min");
  assert.equal(remoto.haQuanto("2026-10-19T12:00:00Z", agora), "há 2 h");
  assert.equal(remoto.haQuanto(null, agora), "nunca");
  const ontem = new Date(agora - 26 * 3_600_000);
  assert.equal(remoto.haQuanto(ontem.toISOString(), agora), `em ${String(ontem.getDate()).padStart(2, "0")}/${String(ontem.getMonth() + 1).padStart(2, "0")} às ${String(ontem.getHours()).padStart(2, "0")}:${String(ontem.getMinutes()).padStart(2, "0")}`);
  assert.equal(remoto.deslocamento("2026-10-19T13:51:40Z", "2026-10-19T13:42:00Z"), "+09:40");
  assert.equal(remoto.deslocamento("2026-10-19T15:02:03Z", "2026-10-19T14:00:00Z"), "+1:02:03");
  assert.equal(remoto.deslocamento(null, "2026-10-19T14:00:00Z"), "");
  assert.equal(remoto.nomeDoTipo("microssono", tipos), "Microssono (olhos fechados 1 s)");
  assert.equal(remoto.nomeDoTipo("tipo_novo", tipos), "tipo novo");
  const sessao = { eventos: 3, trechos: 2, resumo: { perclos_medio: 0.07, piscadas_por_minuto: 15.2 } };
  assert.equal(remoto.resumoDaSessao(sessao), "3 eventos · 2 trechos · PERCLOS 7% · 15 piscadas/min");
  assert.equal(remoto.resumoDaSessao({ eventos: 1, trechos: 0, resumo: {} }), "1 evento · sem trechos");
  const aparelhos = [{ testando_agora: true }, { testando_agora: false }];
  assert.equal(remoto.resumoDaTela({ aparelhos, sessoes: [{}, {}, {}] }), "2 computadores · 1 testando agora · 3 sessões");
  assert.equal(remoto.resumoDaTela({ aparelhos: [], sessoes: [] }), "Nenhum computador conectado ainda");
});

test("PCE-05 frase da central: conectado, sem conexão (mostra o que já baixou) e desconectado", () => {
  const agora = Date.parse("2026-10-19T14:00:00Z");
  const base = { conectado: true, usuario: { nome: "Marina", funcao: "gestor" }, empresa: { nome: "Viação X" }, ultima_busca: "2026-10-19T13:59:48Z", sem_conexao: false };
  assert.deepEqual(remoto.statusDaCentral(base, agora), { texto: "Conectado como Marina · Viação X · última busca há 12 s", alarme: false });
  const fora = remoto.statusDaCentral({ ...base, sem_conexao: true }, agora);
  assert.equal(fora.alarme, true);
  assert.match(fora.texto, /^Sem conexão com a central\. Mostrando o que já foi baixado \(última busca há 12 s\)\.$/);
  assert.match(remoto.statusDaCentral({ ...base, conectado: false }, agora).texto, /^Não conectado à central/);
  assert.equal(remoto.statusDaCentral({ ...base, ultima_busca: null }, agora).texto, "Conectado como Marina · Viação X · buscando pela primeira vez");
});

test("player do .rgclip: quadro certo para cada instante (sem pular para trás)", () => {
  const quadros = [0, 0.5, 1, 1.5].map((t) => ({ t }));
  assert.equal(remoto.quadroNoTempo(quadros, 0), 0);
  assert.equal(remoto.quadroNoTempo(quadros, 0.49), 0);
  assert.equal(remoto.quadroNoTempo(quadros, 0.5), 1);
  assert.equal(remoto.quadroNoTempo(quadros, 1.2), 2);
  assert.equal(remoto.quadroNoTempo(quadros, 99), 3);
  assert.equal(remoto.quadroNoTempo([], 1), -1);
});

test("telas: menu, Configurações › Central, player e privacidade", () => {
  const menu = ler("src", "components", "menu.ts");
  assert.match(menu, /href: "\/remotos\/", rotulo: "Testes à distância", icone: "monitor", acao: "ver_viagens"/);
  assert.ok(existsSync(path.join(src, "app", "remotos", "page.tsx")), "tela /remotos/");
  const fontes = fontesRemoto();
  assert.match(fontes, /<video/, "MP4/WebM num <video>");
  assert.match(fontes, /<canvas/, ".rgclip num canvas");
  assert.match(fontes, /Sem conexão com a central|statusDaCentral/, "PCE-05 a tela avisa sem conexão");
  assert.match(fontes, /pode\("ver_video"\)|pode_ver_trechos/, "PCE-07 player só com ver_video");
  assert.match(fontes, /clearInterval/, "para de atualizar ao sair da tela");
  const ajustes = ler("src", "components", "settings", "settings-screen.tsx");
  assert.match(ajustes, /id: "central"/);
  const central = ler("src", "components", "settings", "central-section.tsx");
  assert.match(central, /type="password"/);
  assert.match(central, /Gerar código para outro computador/);
  assert.match(central, /abra o RotaGuard Script › Conectar à empresa e digite este código/);
  assert.match(central, /Desconectar/);
  assert.match(central, /setSenha\(""\)/, "a senha sai da tela depois de conectar");
  for (const texto of [fontes, central]) assert.doesNotMatch(texto, /localStorage|sessionStorage|document\.cookie/, "nada no navegador");
});

test("PCE-10 build: a tela Testes à distância sai na exportação do app", (t) => {
  const saida = path.join(raiz, "out");
  if (!existsSync(path.join(saida, "index.html"))) {
    t.skip("rode npm run build antes");
    return;
  }
  assert.ok(existsSync(path.join(saida, "remotos", "index.html")));
});
