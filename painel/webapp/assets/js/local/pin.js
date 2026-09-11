/* Entrada do modo de testes local: um PIN único para todas as contas de teste.
   Guarda só o hash (SHA-256 com prefixo fixo). Não é segurança de verdade — o modo local roda inteiro no navegador;
   serve para ninguém entrar sem querer. Login de verdade é o do modo servidor. */

const PIN_HASH = "2bf661facb0aed4ec749e2da115d114001c8e4692a4c1e9520e7acaf85647dd7";

export async function checkPin(pin) {
  if (!/^\d{4,8}$/.test(pin)) return false;
  const bytes = new TextEncoder().encode(`drivesafe-local:${pin}`);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  const hex = [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
  return hex === PIN_HASH;
}
