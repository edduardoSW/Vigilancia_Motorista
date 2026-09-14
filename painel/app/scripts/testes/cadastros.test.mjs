// Spec 015 · cadastro de motoristas, veículos e caixas: regras puras da tela (src/lib/validators.ts).
// O Node 26 remove os tipos do TypeScript sozinho, então o teste importa o .ts direto, sem dependência nova.
// Rodar: node --test scripts/testes/cadastros.test.mjs
import assert from "node:assert/strict";
import { test } from "node:test";
import {
  diasAte,
  formatarData,
  mascararCpf,
  mesAno,
  nomeCurto,
  normalizarPlaca,
  situacaoCnh,
  validarCnh,
  validarCpf,
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
