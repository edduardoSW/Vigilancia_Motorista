export type Plataforma = "windows" | "linux";

export interface Download {
  plataforma: Plataforma;
  /** Nome do arquivo gerado por implantacao/app-teste/build.py (spec 010). */
  arquivo: string;
  url: string;
}

/**
 * Os arquivos ficam no próprio site, em public/downloads, fora do git: o GitHub não aceita arquivo acima de 100 MB.
 * Copie para lá o que o build gerou em build/app-teste/pacotes. Para servir de outro lugar (release do GitHub,
 * armazenamento de arquivos), use NEXT_PUBLIC_ROTAGUARD_DOWNLOADS_BASE.
 */
export const BASE_PADRAO = "/downloads";

const base = (process.env.NEXT_PUBLIC_ROTAGUARD_DOWNLOADS_BASE || BASE_PADRAO).replace(/\/+$/, "");

// Só Windows e Linux: não haverá versão para Mac (decisão de 14/09/2026).
// Windows: a versão portátil (.zip) sai do build em qualquer computador; o instalador .exe só no CI, com o Inno Setup.
const arquivos: Record<Plataforma, string> = {
  windows: "RotaGuard-Teste-windows-x64.zip",
  linux: "RotaGuard-Teste-linux-x86_64.tar.gz",
};

export const downloads: Download[] = (Object.keys(arquivos) as Plataforma[]).map((plataforma) => ({
  plataforma,
  arquivo: arquivos[plataforma],
  url: `${base}/${arquivos[plataforma]}`,
}));
