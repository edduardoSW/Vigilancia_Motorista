import { createHmac, scryptSync, timingSafeEqual } from "node:crypto";

/**
 * Acesso à área de download com o PIN combinado com a equipe.
 * - O PIN nunca fica no código: só o hash scrypt em ROTAGUARD_PIN_HASH ("scrypt$<sal base64>$<hash base64>"),
 *   gerado com `node scripts/gerar-hash-pin.mjs`.
 * - A sessão é um cookie httpOnly com validade e assinatura HMAC (ROTAGUARD_SESSAO_SEGREDO).
 * - O PIN libera só o download do app; não protege dado de motorista.
 */
export const COOKIE_SESSAO = "rg_sessao";
export const VALIDADE_SESSAO_S = 12 * 60 * 60;

export type ResultadoPin = "ok" | "incorreto" | "sem-configuracao";

export function verificarPin(pin: string): ResultadoPin {
  const configurado = process.env.ROTAGUARD_PIN_HASH ?? "";
  const [algoritmo, salB64, hashB64] = configurado.split("$");
  if (algoritmo !== "scrypt" || !salB64 || !hashB64) return "sem-configuracao";
  const esperado = Buffer.from(hashB64, "base64");
  const obtido = scryptSync(pin.normalize("NFKC"), Buffer.from(salB64, "base64"), esperado.length);
  return timingSafeEqual(obtido, esperado) ? "ok" : "incorreto";
}

function segredo(): string | null {
  const s = process.env.ROTAGUARD_SESSAO_SEGREDO ?? "";
  return s.length >= 32 ? s : null;
}

export function criarSessao(agoraMs = Date.now()): string | null {
  const chave = segredo();
  if (!chave) return null;
  const expira = Math.floor(agoraMs / 1000) + VALIDADE_SESSAO_S;
  const assinatura = createHmac("sha256", chave).update(`v1.${expira}`).digest("base64url");
  return `v1.${expira}.${assinatura}`;
}

export function sessaoValida(valor: string | undefined, agoraMs = Date.now()): boolean {
  const chave = segredo();
  if (!chave || !valor) return false;
  const [versao, expiraTexto, assinatura] = valor.split(".");
  const expira = Number(expiraTexto);
  if (versao !== "v1" || !Number.isFinite(expira) || !assinatura) return false;
  if (expira < Math.floor(agoraMs / 1000)) return false;
  const esperada = createHmac("sha256", chave).update(`v1.${expira}`).digest();
  const recebida = Buffer.from(assinatura, "base64url");
  return recebida.length === esperada.length && timingSafeEqual(recebida, esperada);
}

// Limite simples em memória: 5 tentativas erradas a cada 15 min por IP (um único servidor Node).
const JANELA_MS = 15 * 60 * 1000;
const MAX_TENTATIVAS = 5;
const tentativas = new Map<string, { erros: number; inicio: number }>();

export function bloqueado(ip: string, agoraMs = Date.now()): boolean {
  const registro = tentativas.get(ip);
  if (!registro) return false;
  if (agoraMs - registro.inicio > JANELA_MS) {
    tentativas.delete(ip);
    return false;
  }
  return registro.erros >= MAX_TENTATIVAS;
}

export function registrarErro(ip: string, agoraMs = Date.now()): void {
  const registro = tentativas.get(ip);
  if (!registro || agoraMs - registro.inicio > JANELA_MS) {
    tentativas.set(ip, { erros: 1, inicio: agoraMs });
  } else {
    registro.erros += 1;
  }
}

export function limparErros(ip: string): void {
  tentativas.delete(ip);
}
