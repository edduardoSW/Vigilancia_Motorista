export type Plataforma = "windows" | "macos" | "linux" | "android" | "ios";

export interface Download {
  plataforma: Plataforma;
  /**
   * Link do arquivo publicado (por exemplo, o asset da release do GitHub gerada pelo workflow do app, spec 007).
   * Vazio = "em preparação". No iPhone não há arquivo: a instalação é pelo Safari (PWA).
   */
  url: string;
}

const base = process.env.NEXT_PUBLIC_ROTAGUARD_DOWNLOADS_BASE ?? "";

export const downloads: Download[] = [
  { plataforma: "windows", url: base ? `${base}/RotaGuard-windows-x64-setup.exe` : "" },
  { plataforma: "macos", url: base ? `${base}/RotaGuard-macos-universal.dmg` : "" },
  { plataforma: "linux", url: base ? `${base}/RotaGuard-linux-x86_64.AppImage` : "" },
  { plataforma: "android", url: base ? `${base}/RotaGuard-android.apk` : "" },
  { plataforma: "ios", url: process.env.NEXT_PUBLIC_ROTAGUARD_PWA_URL ?? "" },
];
