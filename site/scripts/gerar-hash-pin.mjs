#!/usr/bin/env node
// Gera as variáveis de ambiente do acesso por PIN sem gravar o PIN em lugar nenhum.
// Uso: node scripts/gerar-hash-pin.mjs   (o PIN é digitado no terminal, não fica no histórico)
// Copie as duas linhas para site/.env.local (fora do git) ou para as variáveis do servidor.
import { randomBytes, scryptSync } from "node:crypto";
import { createInterface } from "node:readline";

const rl = createInterface({ input: process.stdin, output: process.stdout, terminal: true });
rl.stdoutMuted = true;
rl._writeToOutput = (texto) => {
  if (!rl.stdoutMuted || texto.includes("PIN")) rl.output.write(texto);
};

rl.question("PIN (só números, não aparece na tela): ", (pin) => {
  rl.close();
  process.stdout.write("\n");
  const limpo = pin.trim().normalize("NFKC");
  if (!/^\d{4,12}$/.test(limpo)) {
    console.error("O PIN precisa ter de 4 a 12 dígitos.");
    process.exit(1);
  }
  const sal = randomBytes(16);
  const hash = scryptSync(limpo, sal, 32);
  console.log(`ROTAGUARD_PIN_HASH=scrypt$${sal.toString("base64")}$${hash.toString("base64")}`);
  console.log(`ROTAGUARD_SESSAO_SEGREDO=${randomBytes(32).toString("base64url")}`);
});
