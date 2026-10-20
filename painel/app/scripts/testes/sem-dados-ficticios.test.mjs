// Spec 030 · painel sem dados fictícios (SDF-01 a SDF-06, lado da tela). Roda sem build; as conferências do pacote
// (out/) rodam depois de `npm run build` e pulam sem ele. O lado do Python está em tests/test_painel_sem_demonstracao.py.
import assert from "node:assert/strict";
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";
import { numerosDoInicio, resumoDoInicio, tarefasDoInicio } from "../../src/components/home/inicio-numeros.ts";
import { FORA_DO_APP, transporteVazio } from "../../src/lib/bridge.ts";
import { VAZIO } from "../../src/content/estados-vazios.ts";

const raiz = path.join(import.meta.dirname, "..", "..");
const src = path.join(raiz, "src");
const saida = path.join(raiz, "out");
const ler = (...partes) => readFileSync(path.join(raiz, ...partes), "utf8");

// Inventário do que era fictício (19/10/2026), de onde vinha, e o que tem que sumir do pacote do app.
export const TERMOS_FICTICIOS = [
  // empresa e aviso (src/content/demo.json, demo-backend.ts, cadastros.py)
  "Viação Demonstração",
  "Garagem central",
  "pessoas, veículos e viagens fictícios",
  // motoristas (demo.json, demo-backend.ts motoristasDemo, cadastros.py DEMO_MOTORISTAS)
  "Carlos Menezes",
  "Juliana Prado",
  "Rogério Lima",
  "Aline Costa",
  "Marcos Teixeira",
  "Carlos M.",
  "Juliana P.",
  "Rogério L.",
  "Aline C.",
  "Marcos T.",
  // equipe das capturas (?sessao=) e quem decidiu os momentos (demo.json, demo-backend.ts, cadastros.py)
  "Marina (gestora)",
  "Marina Lopes",
  "marina.lopes",
  "Paulo Reis",
  "Ana Souza",
  // veículos, placas e caixas (demo.json, demo-backend.ts PLACAS, cadastros.py DEMO_VEICULOS)
  "Caminhão 3302",
  "Ônibus 2258",
  "Ônibus 2240",
  "Caminhão 3310",
  "Ônibus 2251",
  "Ônibus 2263",
  "Ônibus 1187",
  "BRA2E19",
  "BRA3F27",
  "BRA1C84",
  "BRA5H02",
  "BRA4D66",
  "BRA7B31",
  "BRA8A12",
  "RG-0129",
  "RG-0139",
  "RG-0142",
  "RG-0133",
  "RG-0150",
  "RG-0147",
  "RG-0118",
  "RG-0155",
  // viagens, linhas e revisões (demo.json)
  "v-2240",
  "v-3310",
  "v-1187",
  "Campinas → Uberlândia",
  "Rio de Janeiro → Belo Horizonte",
  "São Paulo → Curitiba",
  "Mão na orelha, sem celular.",
  "Pausa extra combinada",
  // caixa "conectada" e contadores fixos (demo.json coletas, home-screen.tsx, sidebar.tsx)
  "Caixa do Ônibus",
  "Lendo a viagem de ontem",
  "64% lido",
  "(64%)",
  // central de mentira (demo-backend.ts criarRemotosDemo)
  "Notebook da Ana",
  "Desktop da garagem",
  "ANA-NOTE",
  "GARAGEM-01",
  "Webcam HD integrada",
  "RotaGuard Script 0.4",
  // faixa e textos da prévia (auth-gate.tsx, layout.tsx, moment-dialog.tsx, about-section.tsx, guide.ts)
  "dados fictícios",
  "Prévia com dados",
  "vídeo fictício",
  "demonstração",
  "Demonstração",
];

function arquivos(pasta, filtro) {
  if (!existsSync(pasta)) return [];
  return readdirSync(pasta).flatMap((nome) => {
    const caminho = path.join(pasta, nome);
    if (statSync(caminho).isDirectory()) return arquivos(caminho, filtro);
    return filtro(nome) ? [caminho] : [];
  });
}

const exportado = existsSync(path.join(saida, "index.html"));
const textoDoPacote = () => arquivos(saida, (nome) => /\.(html|txt|js|css|json)$/.test(nome)).map((caminho) => ({ caminho, texto: readFileSync(caminho, "utf8") }));
const fontes = () => arquivos(src, (nome) => /\.(tsx?|css|json)$/.test(nome)).map((caminho) => ({ caminho, texto: readFileSync(caminho, "utf8") }));

test("SDF-01 o pacote do app (out/) não tem nenhum nome, placa, caixa, viagem ou empresa da demonstração", { skip: !exportado && "rode npm run build antes" }, () => {
  const pacote = textoDoPacote();
  assert.ok(pacote.length > 20, "o pacote tem arquivos de texto");
  for (const termo of TERMOS_FICTICIOS) {
    const achados = pacote.filter(({ texto }) => texto.includes(termo)).map(({ caminho }) => path.relative(saida, caminho));
    assert.deepEqual(achados, [], `"${termo}" no pacote: ${achados.slice(0, 3).join(", ")}`);
  }
  const viagens = existsSync(path.join(saida, "viagens")) ? readdirSync(path.join(saida, "viagens")) : [];
  assert.deepEqual(viagens.filter((nome) => /^v-/.test(nome)), [], "nenhuma página de viagem fictícia exportada");
});

test("SDF-01 o código das telas não tem dado fictício; a demonstração em memória e o demo.json só existem nos testes", () => {
  assert.ok(!existsSync(path.join(src, "content", "demo.json")) && !existsSync(path.join(src, "lib", "demo-backend.ts")), "saíram de src/");
  assert.ok(existsSync(path.join(raiz, "scripts", "testes", "fixtures", "demo.json")), "o demo.json virou fixture");
  assert.ok(existsSync(path.join(raiz, "scripts", "testes", "fixtures", "demo-backend.ts")), "a demonstração em memória virou fixture");
  for (const { caminho, texto } of fontes()) {
    assert.doesNotMatch(texto, /demo-backend|demo\.json/, `${path.relative(raiz, caminho)}: importa a demonstração`);
    for (const termo of TERMOS_FICTICIOS) assert.ok(!texto.includes(termo), `${path.relative(raiz, caminho)}: "${termo}"`);
  }
});

test("SDF-02 a faixa 'Prévia com dados fictícios' não existe mais", () => {
  const portao = ler("src", "components", "auth-gate.tsx");
  assert.doesNotMatch(portao, /AVISO_PREVIA|function Faixa|<Faixa/);
  assert.doesNotMatch(ler("src", "app", "layout.tsx"), /fictíci/i);
  const verificar = readFileSync(path.join(raiz, "..", "desktop", "rotaguard_painel.py"), "utf8");
  assert.match(verificar, /TEXTO_PROIBIDO = "dados fictícios"/, "o --verificar recusa a faixa de volta");
});

test("SDF-02 e SDF-03 nas páginas exportadas: sem a faixa e o menu com a situação real", { skip: !exportado && "rode npm run build antes" }, () => {
  for (const pagina of ["index.html", "viagens/index.html", "motoristas/index.html", "veiculos/index.html", "remotos/index.html", "ao-vivo/index.html"]) {
    const html = readFileSync(path.join(saida, pagina), "utf8");
    assert.doesNotMatch(html, /fictíci/i, pagina);
    assert.match(html, /<html[^>]*lang="pt-BR"/, pagina);
    assert.match(html, /Nenhuma caixa conectada/, `${pagina}: o menu diz que não há caixa conectada`);
  }
});

test("SDF-03 menu sem 'Caixa conectada 64%': mostra a situação real (caixa e central)", () => {
  const menu = ler("src", "components", "sidebar.tsx");
  assert.doesNotMatch(menu, /coletas|progresso|@\/content"/, "o menu não lê dado de exemplo");
  assert.match(menu, /Nenhuma caixa conectada/);
  assert.match(menu, /bridge\.central_estado\(\)/, "a linha da central vem da ponte");
  assert.match(menu, /Central: conectado como/);
  assert.match(menu, /clearInterval/, "para de consultar ao sair");
});

test("SDF-04 estados vazios com o próximo passo, sem travessão, e as telas usam eles", () => {
  assert.equal(VAZIO.viagens.texto.split(".")[0], "As viagens aparecem quando uma caixa for conectada a este computador");
  assert.equal(VAZIO.viagens.titulo, "Nenhuma viagem ainda.");
  for (const [tela, estado] of Object.entries(VAZIO)) {
    assert.ok(estado.titulo.trim() && estado.texto.trim(), `${tela}: título e texto`);
    assert.doesNotMatch(`${estado.titulo} ${estado.texto} ${estado.acao?.rotulo ?? ""}`, /—|–/, `${tela}: sem travessão`);
    assert.match(estado.titulo, /\.$/, `${tela}: título é frase`);
  }
  for (const tela of ["motoristas", "veiculos", "caixas", "viagens"]) assert.ok(VAZIO[tela].acao || tela === "caixas", `${tela}: tem próximo passo`);
  assert.equal(VAZIO.motoristas.acao.precisa, "cadastrar");
  assert.equal(VAZIO.veiculos.acao.precisa, "cadastrar");
  assert.match(VAZIO.caixas.texto, /arquivo da empresa/);
  const usos = {
    viagens: ler("src", "components", "trips", "trips-screen.tsx"),
    motoristas: ler("src", "components", "drivers", "drivers-screen.tsx"),
    veiculos: ler("src", "components", "vehicles", "vehicles-screen.tsx"),
    caixas: ler("src", "components", "vehicles", "vehicles-screen.tsx"),
    relatorio: ler("src", "components", "trip", "trip-report.tsx"),
  };
  for (const [tela, texto] of Object.entries(usos)) {
    assert.match(texto, new RegExp(`VAZIO\\.${tela}\\b`), `${tela}: usa o estado vazio`);
    assert.match(texto, /<EmptyState\b/, `${tela}: mostra o estado vazio`);
  }
  assert.match(ler("src", "components", "trips", "trips-screen.tsx"), /useViagens\(\)/, "Viagens só com viagem lida");
});

test("SDF-04 a página de Viagens exportada já sai com o estado vazio", { skip: !exportado && "rode npm run build antes" }, () => {
  const html = readFileSync(path.join(saida, "viagens", "index.html"), "utf8");
  assert.match(html, /Nenhuma viagem ainda\./);
  assert.ok(existsSync(path.join(saida, "viagens", "relatorio", "index.html")), "o relatório abre por ?id= (sem página por viagem)");
});

const HOJE_ZERO = {
  testes: 0,
  testes_central: 0,
  testes_locais: 0,
  eventos: 0,
  alertas: 0,
  alertas_por_tipo: {},
  testando_agora: 0,
  computadores: 0,
  script_aberto: false,
  central_conectada: false,
};

test("SDF-05 Início: números reais e zero quando não há; nada vem de constante", () => {
  const zerado = numerosDoInicio({ hoje: HOJE_ZERO, motoristasAtivos: 0, veiculosEmUso: 0, cnhPedemAtencao: 0 });
  assert.deepEqual(
    zerado.map((numero) => [numero.id, numero.valor]),
    [
      ["testes", 0],
      ["alertas", 0],
      ["testando", 0],
      ["motoristas", 0],
      ["veiculos", 0],
      ["cnh", 0],
    ],
  );
  assert.ok(zerado.every((numero) => !numero.alarme), "zero não pede atenção");
  assert.equal(resumoDoInicio(HOJE_ZERO), "Nenhum teste hoje");
  const carregando = numerosDoInicio({ hoje: null, motoristasAtivos: null, veiculosEmUso: null, cnhPedemAtencao: null });
  assert.ok(carregando.every((numero) => numero.valor === null), "carregando não inventa zero");
  const hoje = { ...HOJE_ZERO, testes: 3, testes_central: 2, testes_locais: 1, eventos: 6, alertas: 3, testando_agora: 2, computadores: 2, script_aberto: true, central_conectada: true };
  const numeros = Object.fromEntries(numerosDoInicio({ hoje, motoristasAtivos: 4, veiculosEmUso: 2, cnhPedemAtencao: 1, detalheDosAlertas: "2 de sono e 1 de celular" }).map((numero) => [numero.id, numero]));
  assert.equal(numeros.testes.valor, 3);
  assert.equal(numeros.testes.detalhe, "2 à distância e 1 neste computador");
  assert.equal(numeros.alertas.valor, 3);
  assert.equal(numeros.alertas.detalhe, "2 de sono e 1 de celular");
  assert.ok(numeros.alertas.alarme && numeros.cnh.alarme, "alerta e CNH vencendo pedem atenção");
  assert.equal(numeros.testando.valor, 2);
  assert.match(numeros.testando.detalhe, /este computador/);
  assert.equal(numeros.motoristas.valor, 4);
  assert.equal(numeros.veiculos.valor, 2);
  assert.equal(resumoDoInicio(hoje), "3 testes hoje · 3 alertas · 2 computadores testando agora");
  assert.equal(resumoDoInicio({ ...HOJE_ZERO, testes: 1, alertas: 1, testando_agora: 1 }), "1 teste hoje · 1 alerta · 1 computador testando agora");
  for (const numero of Object.values(numeros)) assert.match(numero.href, /^\/([\w-]+\/)?(\?[\w=&-]+)?$/, `${numero.id}: leva a uma tela`);
});

test("SDF-05 O que fazer agora: só tarefa que existe de verdade, com um próximo passo quando não há nada", () => {
  const nada = tarefasDoInicio({ hoje: HOJE_ZERO, administra: true, empresaSemNome: false });
  assert.deepEqual(
    nada.map((tarefa) => tarefa.href),
    ["/ao-vivo/", "/configuracoes/?secao=central"],
    "sem teste: testar aqui e ligar a central",
  );
  assert.match(nada[0].titulo, /Nenhum teste hoje/);
  assert.match(nada[0].detalhe, /RotaGuard Script/, "nome novo do app de teste (spec 031)");
  const consulta = tarefasDoInicio({ hoje: HOJE_ZERO, administra: false, empresaSemNome: true });
  assert.deepEqual(consulta.map((tarefa) => tarefa.href), ["/ao-vivo/"], "sem administrar: não oferece Configurações");
  const testando = tarefasDoInicio({ hoje: { ...HOJE_ZERO, testes: 1, testes_central: 1, testando_agora: 1, alertas: 2, central_conectada: true }, administra: true, empresaSemNome: true });
  assert.deepEqual(
    testando.map((tarefa) => [tarefa.id, tarefa.href]),
    [
      ["testando", "/remotos/"],
      ["alertas", "/remotos/"],
      ["empresa", "/configuracoes/?secao=empresa"],
    ],
  );
  assert.ok(testando[1].alarme, "alertas em alarme");
  const local = tarefasDoInicio({ hoje: { ...HOJE_ZERO, testes: 1, testes_locais: 1, testando_agora: 1, script_aberto: true, alertas: 1 }, administra: false, empresaSemNome: false });
  assert.deepEqual(local.map((tarefa) => tarefa.href), ["/ao-vivo/", "/ao-vivo/"], "só o script daqui: tudo leva ao teste neste computador");
  const inicio = ler("src", "components", "home", "home-screen.tsx");
  assert.doesNotMatch(inicio, /@\/content"|\bdados\.(viagens|coletas|motoristas|veiculos)|COLETA|caixa-conectada/, "o Início não lê dado de exemplo");
  assert.match(inicio, /bridge\.inicio_resumo\(\)/);
  assert.match(inicio, /numerosDoInicio\(/);
  assert.match(inicio, /tarefasDoInicio\(/);
});

test("SDF-06 a ativação não oferece demonstração: nome da empresa e administrador, ou o arquivo da empresa", () => {
  const portao = ler("src", "components", "auth-gate.tsx");
  assert.doesNotMatch(portao, /demonstra/i);
  assert.match(portao, /bridge\.ativar_local\(/);
  assert.match(portao, /bridge\.ativar_com_arquivo\(/);
  assert.match(portao, /Nome da empresa/);
  assert.match(portao, /campo === "empresa"/, "o erro do nome marca o campo");
  const ponte = ler("src", "lib", "bridge.ts");
  assert.doesNotMatch(ponte, /ativar_demonstracao|demo-backend/);
  assert.match(ponte, /ativar_local: 2, ativar_com_arquivo: 2/, "o código de ativação da web continua fora dos argumentos");
});

test("fora da janela do app o transporte é vazio: toda chamada diz para abrir pelo app, sem dado nenhum", async () => {
  const vazio = transporteVazio();
  for (const nome of ["estado", "motoristas_listar", "remotos_listar", "inicio_resumo", "ativar_local"]) {
    assert.deepEqual(await vazio[nome](), { ok: false, erro: FORA_DO_APP }, nome);
  }
  assert.match(FORA_DO_APP, /RotaGuard Painel/);
});
