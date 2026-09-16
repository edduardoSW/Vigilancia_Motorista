export type Plataforma = "windows" | "linux";
export type App = "painel" | "teste";

export interface Download {
  app: App;
  plataforma: Plataforma;
  /** Nome do arquivo gerado por implantacao/painel/build.py (spec 013) ou implantacao/app-teste/build.py (spec 010). */
  arquivo: string;
  url: string;
}

/**
 * Os arquivos ficam no próprio site, em public/downloads, fora do git: o GitHub não aceita arquivo acima de 100 MB.
 * Copie para lá o que os builds geraram em build/painel/pacotes e build/app-teste/pacotes. Para servir de outro lugar
 * (release do GitHub, armazenamento de arquivos), use NEXT_PUBLIC_ROTAGUARD_DOWNLOADS_BASE.
 */
export const BASE_PADRAO = "/downloads";

const base = (process.env.NEXT_PUBLIC_ROTAGUARD_DOWNLOADS_BASE || BASE_PADRAO).replace(/\/+$/, "");

// Só Windows e Linux: não haverá versão para Mac (decisão de 14/09/2026).
// Windows: a versão portátil (.zip) sai do build em qualquer computador; o instalador .exe só com o Inno Setup.
// Painel primeiro (spec 020) e só Windows: o Linux do painel está fora do escopo da spec 013.
const arquivos: [App, Plataforma, string][] = [
  ["painel", "windows", "RotaGuard-Painel-windows-x64.zip"],
  ["teste", "windows", "RotaGuard-Teste-windows-x64.zip"],
  ["teste", "linux", "RotaGuard-Teste-linux-x86_64.tar.gz"],
];

export const downloads: Download[] = arquivos.map(([app, plataforma, arquivo]) => ({
  app,
  plataforma,
  arquivo,
  url: `${base}/${arquivo}`,
}));
