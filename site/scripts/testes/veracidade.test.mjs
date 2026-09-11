// SITE-04 · nenhuma afirmação falsa da prévia v2 volta; as ressalvas obrigatórias continuam no texto.
// Base: docs/site/avaliacoes/2026-09-11-previa-v2/05-tecnica-e-veracidade.md (Anexo B) e docs/produto/PRD.md.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";

const texto = readFileSync(path.join(import.meta.dirname, "..", "..", "messages", "pt-BR.json"), "utf8");

const proibidas = [
  [/em piloto com/i, "V02: não há piloto em andamento"],
  [/conforme a LGPD/i, "V33: sem parecer jurídico e RIPD"],
  [/nenhuma imagem é gravada/i, "a caixa grava trechos curtos por recorrência"],
  [/só o evento sai/i, "V29: o estado do aparelho também sai"],
  [/12 pontos por olho/i, "V35: são 6 pontos por olho"],
  [/imediatamente/i, "V19: o aviso não é imediato sem sinal"],
  [/sair da faixa/i, "V13: o produto não mede faixa"],
  [/reduz\s+\d+\s*%|até\s+\d+\s*%\s+(menos|dos acidentes)/i, "número sem piloto e sem fonte"],
  // Só a afirmação; a pergunta do FAQ ("Detecta uso de drogas?") é permitida porque a resposta nega.
  [/detecta (o )?uso de (drogas|anfetamina|estimulantes)(?!\?)/i, "não é diagnóstico"],
  [/universidades/i, "público fora do foco"],
  [/Raspberry Pi, Linux, Windows e macOS/i, "V50: testado só no Windows"],
];

for (const [padrao, motivo] of proibidas) {
  test(`SITE-04 proibido: ${padrao} (${motivo})`, () => {
    assert.equal(padrao.test(texto), false);
  });
}

test("SITE-04 ressalva: sinais de ativação não são diagnóstico", () => {
  assert.match(texto, /não (é|faz) diagnóstico/i);
});

test("SITE-04 ressalva: rota é demonstração e o produto não registra localização", () => {
  assert.match(texto, /Viagem de demonstração/);
  assert.match(texto, /não registra localização/);
});

test("SITE-04 ressalva: limites em validação com gravações reais", () => {
  assert.match(texto, /validação com gravações reais/);
});
