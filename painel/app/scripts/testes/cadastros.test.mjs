// Spec 015 · cadastro de motoristas, veículos e caixas: regras puras da tela (src/lib/validators.ts).
// O Node 26 remove os tipos do TypeScript sozinho, então o teste importa o .ts direto, sem dependência nova.
// Rodar: node --test scripts/testes/cadastros.test.mjs
import assert from "node:assert/strict";
import { test } from "node:test";
import {
  conteudoBase64,
  cpfMascarado,
  dataHoraLocal,
  dataLocal,
  diasAte,
  formatarData,
  fraseDoTermo,
  mascararCpf,
  mesAno,
  nomeCurto,
  normalizarPlaca,
  registroDoTermo,
  situacaoCnh,
  tamanhoArquivo,
  TERMO_MAX_BYTES,
  validarArquivoTermo,
  validarCnh,
  validarCpf,
  validarDataTermo,
  validarPlaca,
} from "../../src/lib/validators.ts";

// CNH: 9 números + 2 dígitos verificadores, na mesma variante do src/lib/demo-backend.ts (o Python deve usar a mesma).
// Calculados à mão:
// 123456789 → soma 165 (peso 9..1) resto 0 → 1º dígito 0; soma 285 (peso 1..9) resto 10 → 2º dígito 0.
// 100000001 → soma 10 resto 10 → 1º dígito 0 com desconto 2; soma 10 resto 10 (≥ 10) → 2º dígito 0.
// 000000085 → soma 21 resto 10 → 1º dígito 0 com desconto 2; soma 109 resto 10 (≥ 10) → 2º dígito 0.
// 000000093 → soma 21 resto 10 → desconto 2; soma 99 resto 0, 0 − 2 < 0 → essa base não tem CNH válida.
const CNH_OK = ["12345678900", "10000000100", "00000008500"];

test("MOT-02 CNH com 11 números e dígito verificador certo passa", () => {
  for (const numero of CNH_OK) assert.equal(validarCnh(numero), null, numero);
  assert.equal(validarCnh(" 123.456.789-00 "), null, "pontuação e espaço não contam");
});

test("MOT-02 CNH com número faltando diz quantos faltam, como na prévia", () => {
  assert.equal(validarCnh("1234567890"), "A CNH tem 11 números. Faltou 1.");
  assert.equal(validarCnh("123456789"), "A CNH tem 11 números. Faltaram 2.");
  assert.equal(validarCnh("123456789001"), "A CNH tem 11 números. Sobrou 1.");
  assert.equal(validarCnh(""), "Informe o número da CNH.");
});

test("MOT-02 CNH com dígito verificador errado ou números todos iguais é recusada", () => {
  const invalido = "Número da CNH inválido. Confira os dois últimos números.";
  assert.equal(validarCnh("12345678901"), invalido);
  assert.equal(validarCnh("10000000108"), invalido, "a variante que soma 11 no negativo não vale aqui");
  assert.equal(validarCnh("00000009309"), invalido, "resto menor que o desconto: base sem CNH válida");
  assert.equal(validarCnh("00000009300"), invalido);
  assert.equal(validarCnh("11111111111"), invalido);
});

test("MOT-02 CPF é opcional; se informado, confere o dígito verificador", () => {
  assert.equal(validarCpf(""), null, "vazio é aceito");
  assert.equal(validarCpf(null), null, "nulo é aceito");
  assert.equal(validarCpf("529.982.247-25"), null);
  assert.equal(validarCpf("52998224725"), null);
  assert.equal(validarCpf("52998224724"), "CPF inválido. Confira os números.");
  assert.equal(validarCpf("111.111.111-11"), "CPF inválido. Confira os números.");
  assert.equal(validarCpf("5299822472"), "O CPF tem 11 números. Faltou 1.");
});

test("MOT-02 CPF aparece mascarado na lista", () => {
  assert.equal(mascararCpf("52998224725"), "•••.•••.247-••");
  assert.equal(mascararCpf(null), "");
});

test("MOT-02 CPF que já chega mascarado da ponte continua mascarado (bug: sumia na tela e travava a edição)", () => {
  assert.equal(mascararCpf("•••.•••.247-••"), "•••.•••.247-••");
  assert.equal(cpfMascarado("•••.•••.247-••"), true);
  assert.equal(cpfMascarado("529.982.247-25"), false);
  assert.equal(cpfMascarado(null), false);
});

test("MOT-03 nome nos relatórios sugerido pelo nome completo", () => {
  assert.equal(nomeCurto("Carlos Menezes"), "Carlos M.");
  assert.equal(nomeCurto("  juliana   prado "), "Juliana P.");
  assert.equal(nomeCurto("Maria da Silva"), "Maria S.");
  assert.equal(nomeCurto("Ana Beatriz dos Santos e Souza"), "Ana S.");
  assert.equal(nomeCurto("Rogério"), "Rogério");
  assert.equal(nomeCurto(""), "");
});

test("MOT-06 dias até a validade contam só a data, sem fuso nem horário de verão", () => {
  assert.equal(diasAte("2026-09-26", "2026-09-14"), 12);
  assert.equal(diasAte("2026-09-14", "2026-09-14"), 0);
  assert.equal(diasAte("2026-09-10", "2026-09-14"), -4);
  assert.equal(diasAte("2027-09-14", "2026-09-14"), 365);
  assert.equal(diasAte("2026-09-26", new Date(2026, 8, 14, 23, 59)), 12, "aceita Date com horário");
});

test("MOT-06 situação da CNH: aviso 30 dias antes e vencida depois da validade", () => {
  const hoje = "2026-09-14";
  assert.equal(situacaoCnh("2028-03-31", hoje), "ok");
  assert.equal(situacaoCnh("2026-10-15", hoje), "ok", "31 dias ainda não avisa");
  assert.equal(situacaoCnh("2026-10-14", hoje), "vence_em_breve", "30 dias avisa");
  assert.equal(situacaoCnh("2026-09-26", hoje), "vence_em_breve", "Rogério Lima, 12 dias");
  assert.equal(situacaoCnh("2026-09-14", hoje), "vence_em_breve", "vale até hoje");
  assert.equal(situacaoCnh("2026-09-13", hoje), "vencida");
});

test("MOT-06 datas da carteira em pt-BR", () => {
  assert.equal(formatarData("2026-09-26"), "26/09/2026");
  assert.equal(mesAno("2028-03-31"), "03/2028");
});

test("VEI-01 placa Mercosul ou antiga, com ou sem hífen", () => {
  for (const placa of ["BRA2E19", "bra3f27", "ABC-1234", "ABC1234", " abc-1234 "]) assert.equal(validarPlaca(placa), null, placa);
  assert.equal(validarPlaca(""), "Informe a placa.");
  for (const placa of ["BR2E19", "BRA2E1", "1BC1234", "ABC-1D23", "ABCD123", "ABC12345"]) {
    assert.equal(validarPlaca(placa), "Placa inválida. Use o formato ABC1D23 (nova) ou ABC-1234 (antiga).", placa);
  }
});

test("VEI-01 placa guardada em maiúsculas, antiga com hífen", () => {
  assert.equal(normalizarPlaca(" bra2e19 "), "BRA2E19");
  assert.equal(normalizarPlaca("abc1234"), "ABC-1234");
  assert.equal(normalizarPlaca("ABC-1234"), "ABC-1234");
});

// Spec 019 · termo assinado importado como comprovante (decisão 5). A tela confere nome e tamanho antes de ler o arquivo;
// o Python confere de novo pelos primeiros bytes (um .exe renomeado para .pdf passa aqui e é recusado lá, TER-01).

test("TER-01 arquivo do termo: só PDF, PNG ou JPEG, até 10 MB, antes de mandar pela ponte", () => {
  const tipo = "Use um PDF ou uma foto (PNG ou JPEG) do termo assinado.";
  assert.equal(validarArquivoTermo(null), "Escolha o arquivo do termo assinado.");
  for (const nome of ["termo-carlos.pdf", "TERMO.PDF", "foto.png", "foto.jpg", "foto.JPEG"]) {
    assert.equal(validarArquivoTermo({ nome, bytes: 212_000 }), null, nome);
  }
  for (const nome of ["termo.docx", "termo.exe", "termo", "pdf", "termo.pdf.exe", "foto.gif"]) {
    assert.equal(validarArquivoTermo({ nome, bytes: 212_000 }), tipo, nome);
  }
  assert.equal(validarArquivoTermo({ nome: "termo.pdf", bytes: 0 }), "O arquivo está vazio. Escolha o arquivo do termo assinado.");
  assert.equal(TERMO_MAX_BYTES, 10 * 1024 * 1024);
  assert.equal(validarArquivoTermo({ nome: "termo.pdf", bytes: TERMO_MAX_BYTES }), null, "10 MB cabem");
  assert.equal(validarArquivoTermo({ nome: "termo.pdf", bytes: TERMO_MAX_BYTES + 1 }), "O arquivo pode ter até 10 MB.");
});

test("TER-01 data da assinatura obrigatória e nunca depois de hoje", () => {
  const hoje = "2026-09-15";
  assert.equal(validarDataTermo("2026-09-02", hoje), null);
  assert.equal(validarDataTermo("2026-09-15", hoje), null, "hoje vale");
  assert.equal(validarDataTermo("2026-09-16", hoje), "A data não pode ser depois de hoje.");
  assert.equal(validarDataTermo("", hoje), "Informe a data em que o termo foi assinado.");
  assert.equal(validarDataTermo("02/09/2026", hoje), "Informe a data em que o termo foi assinado.");
});

test("TER-01 conteúdo lido pelo FileReader vai para a ponte sem o prefixo data:...;base64,", () => {
  assert.equal(conteudoBase64("data:application/pdf;base64,JVBERi0xLjQ="), "JVBERi0xLjQ=");
  assert.equal(conteudoBase64("data:image/png;base64,iVBORw0KGgo="), "iVBORw0KGgo=");
  assert.equal(conteudoBase64("data:application/pdf;base64,"), "", "arquivo vazio");
  assert.equal(conteudoBase64("sem prefixo"), "");
  assert.equal(conteudoBase64(null), "");
});

test("TER-03 tamanho do arquivo em KB ou MB, sem virar 0 KB", () => {
  assert.equal(tamanhoArquivo(212 * 1024), "212 KB");
  assert.equal(tamanhoArquivo(300), "1 KB");
  assert.equal(tamanhoArquivo(1024 * 1024 - 100), "1 MB", "1023,9 KB arredonda para 1 MB, não para 1024 KB");
  assert.equal(tamanhoArquivo(Math.round(1.4 * 1024 * 1024)), "1,4 MB");
  assert.equal(tamanhoArquivo(10 * 1024 * 1024), "10 MB");
});

test("TER-03 quando: data e hora no relógio deste computador", () => {
  assert.equal(dataLocal("2026-09-15"), "15/09/2026");
  assert.equal(dataLocal("2026-09-15T15:00:00Z"), "15/09/2026", "meio-dia UTC é 15/09 em qualquer fuso do Brasil");
  assert.equal(dataLocal("não é data"), "não é data");
  assert.equal(dataHoraLocal(new Date(2026, 8, 15, 10, 7).toISOString()), "15/09/2026 às 10:07");
  assert.equal(dataHoraLocal("2026-09-15"), "15/09/2026", "sem hora fica só a data");
});

test("TER-03 frase do termo com arquivo: data, versão, arquivo, tamanho, quem importou e quando", () => {
  const arquivo = { nome: "termo-carlos.pdf", tipo: "pdf", bytes: 212 * 1024, importado_em: "2026-09-15T15:00:00Z", importado_por: "Marina Lopes" };
  assert.deepEqual(fraseDoTermo({ assinado: true, data: "2026-09-02", versao: "1", arquivo }), {
    texto: "Assinado em 02/09/2026 · versão 1 · termo-carlos.pdf (212 KB), importado por Marina Lopes em 15/09/2026",
    alarme: false,
  });
});

test("spec 019 decisão 5: termo registrado antes, sem arquivo, continua valendo e aparece como 'sem o arquivo do termo'", () => {
  assert.deepEqual(fraseDoTermo({ assinado: true, data: "2026-09-02", versao: "1", arquivo: null }), {
    texto: "Assinado em 02/09/2026 · sem o arquivo do termo",
    alarme: false,
  });
  assert.deepEqual(fraseDoTermo({ assinado: true, data: null, versao: null, arquivo: null }), { texto: "Assinado · sem o arquivo do termo", alarme: false });
});

test("MOT-04 sem termo, a frase fica em alarme e diz que os vídeos ficam trancados", () => {
  assert.deepEqual(fraseDoTermo({ assinado: false, data: null, versao: null, arquivo: null }), {
    texto: "Falta registrar. Os vídeos ficam trancados.",
    alarme: true,
  });
});

test("TER-03 histórico: cada registro com data, versão, arquivo (ou sem arquivo), quem registrou e quando", () => {
  const em = new Date(2026, 8, 15, 10, 7).toISOString();
  const importado = {
    id: 7,
    assinado: true,
    data: "2026-09-02",
    versao: "2",
    registrado_por: "Marina Lopes",
    registrado_em: em,
    arquivo: { nome: "termo-carlos.jpg", tipo: "imagem", bytes: 1024 * 1024 * 2, importado_em: em, importado_por: "Marina Lopes" },
  };
  assert.deepEqual(registroDoTermo(importado), {
    titulo: "Assinado em 02/09/2026 · versão 2",
    arquivo: "termo-carlos.jpg (2 MB)",
    quem: "Registrado por Marina Lopes em 15/09/2026 às 10:07",
  });
  assert.deepEqual(registroDoTermo({ ...importado, arquivo: null, registrado_por: null }), {
    titulo: "Assinado em 02/09/2026 · versão 2",
    arquivo: "Sem arquivo",
    quem: "Registrado em 15/09/2026 às 10:07",
  });
  assert.deepEqual(registroDoTermo({ ...importado, assinado: false, data: null, versao: null, arquivo: null }), {
    titulo: "Termo revogado",
    arquivo: "Sem arquivo",
    quem: "Registrado por Marina Lopes em 15/09/2026 às 10:07",
  });
});
