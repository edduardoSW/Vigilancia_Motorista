// Casca do painel (specs 014, 017 e 019): menu por função, busca rápida, o que a Consulta vê num momento, nada guardado no
// navegador, os Primeiros passos do Início, janelas no centro, lista e cards, modo escuro e vídeos do momento.
// Roda sem build: o Node lê os .ts direto (apaga os tipos sozinho).
import assert from "node:assert/strict";
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";
import { buscarNaPaleta } from "../../src/components/command-search.ts";
import { mostrarPrimeirosPassos, primeirosPassos } from "../../src/components/home/first-steps.ts";
import { ITENS_MENU, itemAtivo, itensDoMenu } from "../../src/components/menu.ts";
import { acoesDoMomento } from "../../src/components/moment-actions.ts";
import * as regrasDoVideo from "../../src/components/trip/video-rules.ts";
import { podeFazer, PREFERENCIAS_PADRAO, TELAS_COM_VISAO } from "../../src/lib/bridge.ts";

const raiz = path.join(import.meta.dirname, "..", "..");
const ler = (...partes) => readFileSync(path.join(raiz, ...partes), "utf8");
const pode = (funcao) => (acao) => podeFazer(funcao, acao);
const FUNCOES = ["administrador", "supervisor", "consulta"];

// Mapa do painel depois de entrar (spec 014): 7 itens nesta ordem.
const MAPA = ["Início", "Viagens", "Motoristas", "Veículos e caixas", "Equipe", "Configurações", "Guia de uso"];
const rotulosDoMapa = (funcao) => itensDoMenu(pode(funcao)).map((item) => item.rotulo).filter((rotulo) => MAPA.includes(rotulo));

test("MEN-01 menu com os 7 itens na ordem do mapa; itens sem permissão não aparecem", () => {
  assert.deepEqual(rotulosDoMapa("administrador"), MAPA);
  const semAdministracao = MAPA.filter((rotulo) => rotulo !== "Equipe" && rotulo !== "Configurações");
  assert.deepEqual(rotulosDoMapa("supervisor"), semAdministracao);
  assert.deepEqual(rotulosDoMapa("consulta"), semAdministracao, "Consulta vê motoristas e veículos só para leitura");
  for (const funcao of FUNCOES) {
    const rotulos = itensDoMenu(pode(funcao)).map((item) => item.rotulo);
    assert.ok(rotulos.includes("Guia de uso"), `GUI-08: ${funcao} sem o Guia de uso`);
    assert.ok(rotulos.includes("Teste neste computador"), `spec 018: ${funcao} sem a tela do teste local`);
  }
  assert.equal(itensDoMenu(() => false).length, 0, "sem nenhuma permissão, nenhum item");
});

test("MEN-01 cada item do menu leva a uma tela que existe na exportação", () => {
  for (const item of ITENS_MENU) {
    assert.match(item.href, /^\/([\w-]+\/)?$/, `${item.rotulo}: endereço fora do padrão com barra no fim`);
    const pagina = item.href === "/" ? path.join(raiz, "src", "app", "page.tsx") : path.join(raiz, "src", "app", item.href.replaceAll("/", ""), "page.tsx");
    assert.ok(existsSync(pagina), `${item.rotulo}: falta ${path.relative(raiz, pagina)}`);
  }
});

test("MEN-01 o item da tela aberta fica marcado, inclusive dentro do relatório de uma viagem", () => {
  assert.equal(itemAtivo("/"), "/");
  assert.equal(itemAtivo(""), "/");
  assert.equal(itemAtivo("/viagens/"), "/viagens/");
  assert.equal(itemAtivo("/viagens"), "/viagens/");
  assert.equal(itemAtivo("/viagens/v-2240/"), "/viagens/");
  assert.equal(itemAtivo("/veiculos/"), "/veiculos/");
  assert.equal(itemAtivo("/guia/"), "/guia/");
  assert.equal(itemAtivo("/ao-vivo/"), "/ao-vivo/");
  assert.equal(itemAtivo("/motoristas-antigos/"), null, "prefixo sem ser o mesmo trecho não marca");
  assert.equal(itemAtivo("/nao-existe/"), null);
  const menu = ler("src", "components", "sidebar.tsx");
  assert.match(menu, /itensDoMenu\(/, "o menu usa a mesma lista testada aqui");
  assert.match(menu, /aria-current/);
});

test("MEN-02 busca rápida: sem acento e sem maiúscula, todas as palavras, telas do menu da própria função", () => {
  const itens = [
    { id: "t-veiculos", grupo: "Telas", titulo: "Veículos e caixas", href: "/veiculos/" },
    { id: "t-motoristas", grupo: "Telas", titulo: "Motoristas", href: "/motoristas/" },
    { id: "m-1", grupo: "Motoristas", titulo: "Carlos Menezes", detalhe: "Matrícula 0412", href: "/motoristas/?abrir=1" },
    { id: "m-2", grupo: "Motoristas", titulo: "Rogério Lima", detalhe: "Matrícula 0291", href: "/motoristas/?abrir=3" },
    { id: "v-1", grupo: "Veículos", titulo: "Ônibus 2240", detalhe: "BRA1C84", palavras: "onibus rodoviario", href: "/veiculos/?abrir=3" },
  ];
  assert.deepEqual(buscarNaPaleta("VEICULOS", itens).map((item) => item.id), ["t-veiculos"]);
  assert.deepEqual(buscarNaPaleta("rogerio", itens).map((item) => item.id), ["m-2"]);
  assert.deepEqual(buscarNaPaleta("0412", itens).map((item) => item.id), ["m-1"], "acha pelo detalhe");
  assert.deepEqual(buscarNaPaleta("onibus 2240", itens).map((item) => item.id), ["v-1"], "todas as palavras");
  assert.deepEqual(buscarNaPaleta("onibus 9999", itens), []);
  assert.deepEqual(buscarNaPaleta("   ", itens), []);
  assert.deepEqual(buscarNaPaleta("motoristas", itens).map((item) => item.id), ["t-motoristas"], "título que começa com a palavra vem primeiro");
  const muitos = Array.from({ length: 9 }, (_, indice) => ({ id: `x${indice}`, grupo: "Motoristas", titulo: `Motorista ${indice}`, href: "/" }));
  assert.equal(buscarNaPaleta("motorista", muitos).length, 5, "no máximo 5 por grupo");
  const telasConsulta = itensDoMenu(pode("consulta")).map((item) => item.rotulo);
  assert.ok(!telasConsulta.includes("Equipe") && !telasConsulta.includes("Configurações"), "a busca usa o menu da função");
  assert.match(ler("src", "components", "command-palette.tsx"), /itensDoMenu\(/);
  assert.match(ler("src", "components", "auth-gate.tsx"), /<CommandPalette/, "Ctrl+K montado depois de entrar");
});

test("EQP-02 Consulta não recebe vídeo nem botões de decisão na tela do momento", () => {
  assert.deepEqual(acoesDoMomento(pode("consulta")), { video: false, decidir: false });
  assert.deepEqual(acoesDoMomento(pode("supervisor")), { video: true, decidir: true });
  assert.deepEqual(acoesDoMomento(pode("administrador")), { video: true, decidir: true });
  for (const partes of [["moment-list.tsx"], ["trip", "moment-dialog.tsx"]]) {
    assert.match(ler("src", "components", ...partes), /acoesDoMomento\(/, `${partes.at(-1)}: usa a regra testada aqui`);
  }
  assert.match(ler("src", "components", "trip", "moment-dialog.tsx"), /bridge\.video_abrir\(/, "vídeo passa pela ponte (o Python confere de novo)");
  assert.match(ler("src", "components", "decisions-provider.tsx"), /bridge\.decisao_registrar\(/, "decisão passa pela ponte");
});

function arquivosFonte(pasta = path.join(raiz, "src")) {
  return readdirSync(pasta).flatMap((nome) => {
    const caminho = path.join(pasta, nome);
    if (statSync(caminho).isDirectory()) return arquivosFonte(caminho);
    return /\.tsx?$/.test(nome) ? [caminho] : [];
  });
}

test("ENT-07 nada de sessão, senha ou código guardado no navegador (sem localStorage, cookie ou IndexedDB)", () => {
  for (const caminho of arquivosFonte()) {
    assert.doesNotMatch(readFileSync(caminho, "utf8"), /localStorage|sessionStorage|document\.cookie|indexedDB/, path.relative(raiz, caminho));
  }
});

const VAZIA = { veiculos: 0, caixasVinculadas: 0, motoristasAtivos: 0, motoristasSemTermo: 0, pessoas: 1, ultimaCopiaEm: null };

test("GUI-07 Primeiros passos marcam cada item pelo estado real e o próximo passo leva ao cadastro", () => {
  const passos = primeirosPassos(VAZIA);
  assert.deepEqual(passos.map((passo) => passo.id), ["veiculos", "caixas", "motoristas", "termos", "equipe", "copia"]);
  assert.ok(passos.every((passo) => !passo.feito), "instalação nova: nada feito");
  assert.equal(passos[0].titulo, "Cadastre os veículos da empresa");
  assert.equal(passos[0].href, "/veiculos/");
  const marcado = (estado, id) => primeirosPassos({ ...VAZIA, ...estado }).find((passo) => passo.id === id).feito;
  assert.equal(marcado({ veiculos: 7 }, "veiculos"), true);
  assert.equal(marcado({ caixasVinculadas: 1 }, "caixas"), true);
  assert.equal(marcado({ motoristasAtivos: 5 }, "motoristas"), true);
  assert.equal(marcado({ motoristasAtivos: 0, motoristasSemTermo: 0 }, "termos"), false, "sem motorista não há termo registrado");
  assert.equal(marcado({ motoristasAtivos: 5, motoristasSemTermo: 1 }, "termos"), false);
  assert.equal(marcado({ motoristasAtivos: 5, motoristasSemTermo: 0 }, "termos"), true);
  assert.equal(marcado({ pessoas: 1 }, "equipe"), false, "só quem administra ainda");
  assert.equal(marcado({ pessoas: 3 }, "equipe"), true);
  assert.equal(marcado({ ultimaCopiaEm: "2026-09-15T12:00:00Z" }, "copia"), true);
  for (const passo of passos) assert.ok(existsSync(path.join(raiz, "src", "app", passo.href.split("?")[0].replaceAll("/", ""), "page.tsx")), passo.href);
});

test("GUI-07 Primeiros passos somem quando tudo está feito ou quando o administrador esconde", () => {
  const completo = primeirosPassos({ veiculos: 7, caixasVinculadas: 7, motoristasAtivos: 5, motoristasSemTermo: 0, pessoas: 3, ultimaCopiaEm: "2026-09-15T12:00:00Z" });
  assert.equal(mostrarPrimeirosPassos(completo, false), false);
  assert.equal(mostrarPrimeirosPassos(primeirosPassos(VAZIA), false), true);
  assert.equal(mostrarPrimeirosPassos(primeirosPassos(VAZIA), true), false);
});

// Spec 019: janelas no centro, lista e cards, modo escuro e vídeos do momento.

test("MOD-01 nenhum painel lateral: cadastrar, ver, editar e buscar abrem no centro, com o resto da janela desfocado", () => {
  const css = ler("src", "app", "globals.css");
  assert.match(css, /\.veu\s*\{[^}]*backdrop-filter:\s*blur\(\d+px\)/, "o véu desfoca o fundo");
  assert.doesNotMatch(css, /anim-drawer/, "sobrou a animação do painel lateral");
  const janela = ler("src", "components", "ui", "dialog.tsx");
  assert.match(janela, /place-items-center/, "a janela fica no centro");
  assert.match(janela, /"veu /, "a janela tem o véu");
  assert.match(ler("src", "components", "ui", "drawer.tsx"), /<Dialog\b/, "quem ainda chama Drawer abre a janela no centro");
  const busca = ler("src", "components", "command-palette.tsx");
  assert.match(busca, /place-items-center/);
  assert.match(busca, /\bveu\b/);
  for (const caminho of arquivosFonte()) {
    assert.doesNotMatch(readFileSync(caminho, "utf8"), /anim-drawer|<dialog\b|\.showModal\(/, `${path.relative(raiz, caminho)}: janela fora do padrão`);
  }
});

test("VIS-01 Viagens, Momentos, Motoristas, Veículos, Caixas e Equipe têm Lista e Cards", () => {
  assert.deepEqual([...TELAS_COM_VISAO].sort(), Object.keys(PREFERENCIAS_PADRAO.visao).sort(), "cada tela tem a visão padrão");
  const fontes = arquivosFonte().map((caminho) => ({ nome: path.relative(raiz, caminho), texto: readFileSync(caminho, "utf8") }));
  for (const tela of TELAS_COM_VISAO) {
    const usam = fontes.filter(({ texto }) => texto.includes(`useVisao("${tela}")`));
    assert.ok(usam.length > 0, `${tela}: nenhuma tela usa useVisao("${tela}")`);
    for (const { nome, texto } of usam) {
      assert.match(texto, /<ViewToggle\b/, `${nome}: sem o botão Lista | Cards`);
      assert.match(texto, /<CardGrid\b/, `${nome}: sem os cards`);
    }
  }
});

test("ESC-01 tema Claro, Escuro ou Igual ao Windows, escolhido pela pessoa e guardado pela ponte", async () => {
  const { OPCOES_TEMA } = await import("../../src/components/theme-options.ts");
  assert.deepEqual(
    OPCOES_TEMA.map((opcao) => [opcao.valor, opcao.rotulo]),
    [
      ["claro", "Claro"],
      ["escuro", "Escuro"],
      ["sistema", "Igual ao Windows"],
    ],
  );
  assert.equal(PREFERENCIAS_PADRAO.tema, "claro");
  const portao = ler("src", "components", "auth-gate.tsx");
  assert.match(portao, /prefers-color-scheme: dark/, "Igual ao Windows segue o tema do Windows");
  assert.match(portao, /dataset\.tema/);
  for (const partes of [["sidebar.tsx"], ["settings", "appearance-section.tsx"]]) {
    const texto = ler("src", "components", ...partes);
    assert.match(texto, /OPCOES_TEMA/, `${partes.at(-1)}: sem a escolha de tema`);
    assert.match(texto, /salvarPreferencias\(/, `${partes.at(-1)}: o tema passa pela ponte`);
  }
});

test("ESC-02 nenhuma cor fixa nas telas: só os tokens do globals.css; texto sobre o lima usa text-sobre-lima", () => {
  const corFixa = /#[0-9a-f]{3,8}\b|\b(bg|text|border|fill|stroke)-(white|black)\b/i;
  for (const caminho of arquivosFonte()) {
    readFileSync(caminho, "utf8")
      .split("\n")
      .forEach((linha, indice) => {
        const onde = `${path.relative(raiz, caminho)}:${indice + 1}`;
        assert.doesNotMatch(linha, corFixa, onde);
        if (linha.includes("bg-lima")) assert.match(linha, /text-sobre-lima/, `${onde}: texto sobre o lima`);
      });
  }
});

function tokensDoBloco(css, seletor) {
  const bloco = css.slice(css.indexOf(seletor));
  const corpo = bloco.slice(bloco.indexOf("{") + 1, bloco.indexOf("}"));
  return Object.fromEntries([...corpo.matchAll(/--color-([\w-]+):\s*(#[0-9a-f]{6})\b/gi)].map(([, nome, valor]) => [nome, valor]));
}

function luminancia(hex) {
  const [r, g, b] = [1, 3, 5].map((inicio) => {
    const canal = parseInt(hex.slice(inicio, inicio + 2), 16) / 255;
    return canal <= 0.04045 ? canal / 12.92 : ((canal + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

const contraste = (a, b) => {
  const [maior, menor] = [luminancia(a), luminancia(b)].sort((x, y) => y - x);
  return (maior + 0.05) / (menor + 0.05);
};

// Texto sobre cada fundo em que ele aparece nas telas.
const PARES = [
  ...["papel", "lateral", "superficie", "elevada", "selecao", "escolha"].flatMap((fundo) => [
    ["tinta", fundo],
    ["grafite", fundo],
    ["verde", fundo],
    ["alarme", fundo],
  ]),
  ["sobre-verde", "verde-cheio"],
  ["sobre-lima", "lima"],
  ["sobre-video", "video"],
  ["sobre-aviso", "aviso"],
];

test("ESC-02 texto e texto secundário com contraste de 4,5:1 ou mais sobre o fundo e a superfície, nos dois temas", () => {
  const css = ler("src", "app", "globals.css");
  const claro = tokensDoBloco(css, "@theme {");
  const soEscuro = tokensDoBloco(css, 'html[data-tema="escuro"] {');
  assert.deepEqual(Object.keys(soEscuro).sort(), Object.keys(claro).sort(), "o escuro troca todas as cores do claro, e só elas");
  for (const [nome, tema] of [
    ["claro", claro],
    ["escuro", soEscuro],
  ]) {
    for (const [texto, fundo] of PARES) {
      const razao = contraste(tema[texto], tema[fundo]);
      assert.ok(razao >= 4.5, `${nome}: ${texto} sobre ${fundo} = ${razao.toFixed(2)}:1`);
    }
  }
});

const demo = JSON.parse(ler("src", "content", "demo.json"));
const CAMPOS_DO_VIDEO = ["Início", "Fim", "Duração", "Câmera", "Caixa", "Coletado em", "Fica guardado até", "Situação"];

test("VID-01 todo momento tem o campo Vídeo; com vídeo, a janela mostra os 8 campos; sem vídeo, diz o motivo", () => {
  const trechos = demo.viagens.flatMap((viagem) => [...viagem.eventos, ...viagem.episodios].flatMap((item) => item.videos ?? []));
  assert.ok(trechos.length >= 5, "a demonstração tem vídeos para mostrar");
  for (const trecho of trechos) {
    assert.ok(trecho.camera, `${trecho.id}: sem câmera`);
    assert.ok(regrasDoVideo.duracaoDoTrecho(trecho.inicio, trecho.fim) > 0, `${trecho.id}: fim antes do início`);
  }
  assert.ok(!demo.viagens.some((viagem) => [...viagem.eventos, ...viagem.episodios].some((item) => "trecho" in item)), "sobrou o campo trecho antigo");
  const janela = ler("src", "components", "trip", "moment-dialog.tsx");
  for (const campo of CAMPOS_DO_VIDEO) assert.match(janela, new RegExp(`rotulo="${campo}"`), `janela do momento sem ${campo}`);
  const lista = ler("src", "components", "moment-list.tsx");
  assert.ok((lista.match(/resumoDoVideo\(momento\)/g) ?? []).length >= 2, "o campo Vídeo aparece na lista e nos cards");
  assert.match(ler("src", "content", "moments.ts"), /motivoSemVideo\(/);
  assert.equal(typeof regrasDoVideo.motivoSemVideo, "function", "motivoSemVideo mora em video-rules.ts, testável");
  assert.match(regrasDoVideo.motivoSemVideo("direcao_continua"), /tempo de direção/);
  assert.match(regrasDoVideo.motivoSemVideo("atencao"), /primeiros sinais de sono/);
  assert.match(regrasDoVideo.motivoSemVideo("olhando_celular"), /não gravou vídeo/);
});

test("VID-02 Fica guardado até = coleta + prazo das configurações; sem termo, o vídeo aparece trancado", () => {
  const { guardadoAte, situacaoDoVideo, duracaoDoTrecho } = regrasDoVideo;
  assert.equal(guardadoAte("2026-09-14T06:12:00-03:00", 30), "2026-10-14");
  assert.equal(guardadoAte("2026-12-20T23:50:00", 15), "2027-01-04", "vira o ano");
  assert.equal(guardadoAte("2028-02-20T10:00:00", 10), "2028-03-01", "ano bissexto");
  assert.equal(duracaoDoTrecho("2026-09-14T04:02:52", "2026-09-14T04:03:12"), 20);
  assert.equal(duracaoDoTrecho("2026-09-14T04:03:12", "2026-09-14T04:02:52"), 0);
  const base = { coletadoEm: "2026-09-14T06:12:00", dias: 30, termoAssinado: true };
  assert.deepEqual(situacaoDoVideo({ ...base, hoje: "2026-09-15" }), { tipo: "disponivel", texto: "Disponível" });
  assert.equal(situacaoDoVideo({ ...base, hoje: "2026-10-14" }).tipo, "disponivel", "o último dia ainda tem o vídeo");
  assert.deepEqual(situacaoDoVideo({ ...base, hoje: "2026-10-15" }), { tipo: "apagado", texto: "Apagado pelo prazo de 30 dias" });
  assert.deepEqual(situacaoDoVideo({ ...base, hoje: "2026-09-15", termoAssinado: false }), {
    tipo: "trancado",
    texto: "Trancado: falta o termo de ciência do motorista",
  });
  assert.equal(situacaoDoVideo({ ...base, hoje: "2026-10-15", termoAssinado: false }).tipo, "apagado", "depois do prazo não há vídeo para trancar");
  const janela = ler("src", "components", "trip", "moment-dialog.tsx");
  assert.match(janela, /guardadoAte\(viagem\.chegada, dias\)/);
  assert.match(janela, /videos_dias/, "o prazo vem das configurações, pela ponte");
});
