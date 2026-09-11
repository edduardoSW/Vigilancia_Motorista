// SITE-05 · acesso por PIN: hash scrypt, sessão assinada com validade, bloqueio por tentativas.
import assert from "node:assert/strict";
import { randomBytes, scryptSync } from "node:crypto";
import { test } from "node:test";

const pinTeste = "4829" + "1736"; // PIN só de teste
const sal = randomBytes(16);
process.env.ROTAGUARD_PIN_HASH = `scrypt$${sal.toString("base64")}$${scryptSync(pinTeste, sal, 32).toString("base64")}`;
process.env.ROTAGUARD_SESSAO_SEGREDO = randomBytes(32).toString("base64url");

const s = await import("../../src/lib/sessao.ts");

test("SITE-05 PIN certo passa e errado não", () => {
  assert.equal(s.verificarPin(pinTeste), "ok");
  assert.equal(s.verificarPin("00000000"), "incorreto");
});

test("SITE-05 sem hash configurado não libera nada", () => {
  const guardado = process.env.ROTAGUARD_PIN_HASH;
  process.env.ROTAGUARD_PIN_HASH = "";
  assert.equal(s.verificarPin(pinTeste), "sem-configuracao");
  process.env.ROTAGUARD_PIN_HASH = guardado;
});

test("SITE-05 sessão válida, expirada e adulterada", () => {
  const agora = Date.now();
  const sessao = s.criarSessao(agora);
  assert.ok(sessao);
  assert.equal(s.sessaoValida(sessao, agora), true);
  assert.equal(s.sessaoValida(sessao, agora + (s.VALIDADE_SESSAO_S + 1) * 1000), false);
  const [v, expira, assinatura] = sessao.split(".");
  assert.equal(s.sessaoValida(`${v}.${Number(expira) + 3600}.${assinatura}`, agora), false);
  assert.equal(s.sessaoValida(undefined, agora), false);
});

test("SITE-05 bloqueia depois de 5 erros e libera depois de 15 min", () => {
  const ip = "203.0.113.9";
  const t0 = Date.now();
  for (let i = 0; i < 5; i++) s.registrarErro(ip, t0);
  assert.equal(s.bloqueado(ip, t0), true);
  assert.equal(s.bloqueado(ip, t0 + 15 * 60 * 1000 + 1), false);
});
