import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

export default defineConfig([
  ...nextVitals,
  ...nextTs,
  // out-web: saída do build da web (spec 024, distDir). public/mediapipe: WASM do MediaPipe copiado no build (spec 025).
  globalIgnores([".next/**", "out/**", "out-web/**", "next-env.d.ts", "public/mediapipe/**"]),
]);
