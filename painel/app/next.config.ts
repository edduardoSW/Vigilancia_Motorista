import type { NextConfig } from "next";

// Prévia do painel da empresa (spec 012). Exportação estática: a mesma pasta out/ vira a interface do app Tauri
// (spec 007), sem servidor Node dentro do app.
const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
  devIndicators: false,
  poweredByHeader: false,
};

export default nextConfig;
