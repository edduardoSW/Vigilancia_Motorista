// Demonstration gate only. The browser is not a trusted security boundary.
// Never use this local session to authorize APIs or access real driver data.
export const ACCESS_KEY = "rotaguard.acesso";
export const ATTEMPT_KEY = "rotaguard.tentativas";
export const ACCESS_TTL = 12 * 60 * 60 * 1000;
export const ATTEMPT_TTL = 15 * 60 * 1000;
export const PIN_CONFIG = {
  salt: "63e65e474dae045e08d218c22e473376",
  hash: "a88211eec137b5f21a62748d5c3e9626ca8e6ebcf886331dbe425ce0f31225aa",
};
type StorageLike = Pick<Storage, "getItem" | "setItem" | "removeItem">;
type PinConfig = {salt: string; hash: string};
export async function hashPin(pin: string, salt: string) {
  const bytes = new TextEncoder().encode(salt + ":" + pin.normalize("NFKC"));
  return Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)), b => b.toString(16).padStart(2,"0")).join("");
}
function parse(value: string | null) {
  try { return value ? JSON.parse(value) : null; } catch { return null; }
}
export function hasAccess(storage: StorageLike, now = Date.now(), config = PIN_CONFIG): boolean {
  try {
    const session = parse(storage.getItem(ACCESS_KEY));
    return session?.version === 1 && session?.credential === config.hash &&
      Number.isFinite(session.createdAt) && Number.isFinite(session.expiresAt) &&
      session.createdAt <= now && session.expiresAt > now &&
      session.expiresAt - session.createdAt === ACCESS_TTL;
  } catch { return false; }
}
export async function signIn(pin: string, storage: StorageLike, config: PinConfig = PIN_CONFIG, now = Date.now()): Promise<"ok"|"pin"|"blocked"|"storage"> {
  try {
    const raw = parse(storage.getItem(ATTEMPT_KEY));
    const recent = Number.isFinite(raw?.startedAt) && raw.startedAt <= now && now - raw.startedAt < ATTEMPT_TTL;
    const attempts = recent && Number.isInteger(raw?.count) && raw.count > 0 ? raw : {count:0, startedAt:now};
    if (attempts.count >= 5) return "blocked";
    if (!/^\d{4,12}$/.test(pin) || await hashPin(pin, config.salt) !== config.hash) {
      storage.setItem(ATTEMPT_KEY, JSON.stringify({...attempts, count:attempts.count+1}));
      return attempts.count + 1 >= 5 ? "blocked" : "pin";
    }
    storage.setItem(ACCESS_KEY, JSON.stringify({version:1, credential:config.hash, createdAt:now, expiresAt:now+ACCESS_TTL}));
    storage.removeItem(ATTEMPT_KEY);
    return "ok";
  } catch { return "storage"; }
}
export function signOut(storage: StorageLike) { storage.removeItem(ACCESS_KEY); }
