/* Onde o app busca os dados.
   "local"    → fase de testes: tudo no próprio navegador, sem servidor e sem banco; entrada por PIN.
   "servidor" → API do servidor DriveSafe: login de verdade e dispositivos instalados nos veículos.
   Para trocar sem editar este arquivo, abra o app uma vez com ?modo=servidor ou ?modo=local (a escolha fica salva). */

const DEFAULT_MODE = "local";

function pickMode() {
  try {
    const fromUrl = new URLSearchParams(location.search).get("modo");
    if (fromUrl === "local" || fromUrl === "servidor") localStorage.setItem("drivesafe-modo", fromUrl);
    const stored = localStorage.getItem("drivesafe-modo");
    if (stored === "local" || stored === "servidor") return stored;
  } catch {
    // navegador sem armazenamento local: fica no padrão
  }
  return DEFAULT_MODE;
}

export const DATA_MODE = pickMode();
export const IS_LOCAL = DATA_MODE === "local";
