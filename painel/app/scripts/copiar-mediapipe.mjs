// Spec 025 · copia o que o teste com a câmera precisa para public/mediapipe/ (fora do git), antes do dev e do build:
// - o WASM do @mediapipe/tasks-vision, só o par com SIMD (o nosimd e o "module" não são usados);
// - o modelo do rosto da caixa (caixa/vision/models/face_landmarker.task, o mesmo float16 do Google).
// O export estático copia public/ para out/, então o painel instalado e o da VPS servem os arquivos sem CDN.
// COPIAR_MEDIAPIPE_DESTINO troca a pasta de destino (usado no teste CAM-10).
import { copyFileSync, existsSync, mkdirSync, statSync } from "node:fs";
import path from "node:path";

const raiz = path.join(import.meta.dirname, "..");
const destino = path.resolve(process.env.COPIAR_MEDIAPIPE_DESTINO || path.join(raiz, "public", "mediapipe"));
const wasm = path.join(raiz, "node_modules", "@mediapipe", "tasks-vision", "wasm");
const modelo = path.join(raiz, "..", "..", "caixa", "vision", "models", "face_landmarker.task");

const ARQUIVOS = [
  { de: path.join(wasm, "vision_wasm_internal.js"), para: path.join(destino, "wasm", "vision_wasm_internal.js") },
  { de: path.join(wasm, "vision_wasm_internal.wasm"), para: path.join(destino, "wasm", "vision_wasm_internal.wasm") },
  { de: modelo, para: path.join(destino, "modelos", "face_landmarker.task") },
];

const faltando = ARQUIVOS.filter(({ de }) => !existsSync(de));
if (faltando.length) {
  console.error("Teste com a câmera (spec 025): faltam arquivos para copiar para public/mediapipe:");
  for (const { de } of faltando) console.error(`  ${path.relative(path.join(raiz, "..", ".."), de)}`);
  console.error(
    "Rode npm install em painel/app (WASM) e confira caixa/vision/models (modelo). " +
      "No Docker, o estágio da interface precisa copiar caixa/vision/models/face_landmarker.task.",
  );
  process.exit(1);
}

let copiados = 0;
for (const { de, para } of ARQUIVOS) {
  const origem = statSync(de);
  // Pula o que já está igual: o predev roda a cada npm run dev.
  if (existsSync(para)) {
    const atual = statSync(para);
    if (atual.size === origem.size && atual.mtimeMs >= origem.mtimeMs) continue;
  }
  mkdirSync(path.dirname(para), { recursive: true });
  copyFileSync(de, para);
  copiados++;
}
const megas = ARQUIVOS.reduce((soma, { de }) => soma + statSync(de).size, 0) / 1e6;
console.log(`MediaPipe em ${path.relative(raiz, destino) || destino}: ${copiados} copiado(s), ${megas.toFixed(1)} MB no total.`);
