import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

const nextConfig: NextConfig = {
  // Spec 021: na VPS o site roda com o servidor mínimo do Next (.next/standalone), sem node_modules inteiro na imagem.
  output: "standalone",
  devIndicators: false,
  images: {
    formats: ["image/avif", "image/webp"],
    qualities: [70, 80],
  },
  poweredByHeader: false,
};

export default withNextIntl(nextConfig);
