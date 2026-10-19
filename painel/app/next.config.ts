import type { NextConfig } from "next";

// Prévia do painel da empresa (spec 012). Exportação estática: a mesma pasta out/ vira a interface do app Tauri
// (spec 007), sem servidor Node dentro do app.
//
// Spec 024 (painel na VPS): o build web passa PAINEL_BASE_PATH=/painel e NEXT_PUBLIC_PAINEL_TRANSPORTE=servidor. Ele
// sai em out-web/ (PAINEL_DIST_DIR troca), para nunca mexer no out/ do app instalado. Sem essas variáveis, o app
// instalado sai como antes; a única diferença é NEXT_PUBLIC_PAINEL_TRANSPORTE e NEXT_PUBLIC_PAINEL_BASE_PATH fixados
// como "" no build, para o código do transporte servidor nem entrar no pacote do app (variável indefinida não é
// embutida e o código morto ficaria lá).
function basePathDoBuild(): string | undefined {
  const bruto = process.env.PAINEL_BASE_PATH?.trim();
  if (!bruto) return undefined;
  const base = bruto.replace(/\/+$/, "");
  if (!/^(\/[A-Za-z0-9._-]+)+$/.test(base)) throw new Error(`PAINEL_BASE_PATH inválido: "${bruto}" (use algo como /painel)`);
  return base;
}

const basePath = basePathDoBuild();
const transporte = process.env.NEXT_PUBLIC_PAINEL_TRANSPORTE?.trim() ?? "";
const buildWeb = basePath !== undefined || transporte === "servidor";

const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
  devIndicators: false,
  poweredByHeader: false,
  env: { NEXT_PUBLIC_PAINEL_TRANSPORTE: transporte, NEXT_PUBLIC_PAINEL_BASE_PATH: basePath ?? "" },
  ...(buildWeb ? { distDir: process.env.PAINEL_DIST_DIR?.trim() || "out-web" } : {}),
  ...(basePath ? { basePath, assetPrefix: basePath } : {}),
};

export default nextConfig;
