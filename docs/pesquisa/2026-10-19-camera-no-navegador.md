# Demonstração ao vivo no navegador: malha facial, sinais de sono e rPPG (pesquisa de 19/10/2026)

**Destino (mudado no meio da pesquisa):** a demo sai do site e vai para o **painel da empresa**:
`painel/app` (Next.js 16.3.5, `output: "export"`), tela `src/app/ao-vivo/page.tsx` e `src/components/live/*`,
servida na VPS em `https://rotaguard.acexpartners.com.br/painel/` (specs 021, 024 e 025) e também no painel instalado
(pywebview/WebView2). As seções 6 e 8 já estão escritas para o painel.

**O que eu fiz de verdade (não só li):**
- conferi versões no npm (`npm view ... version` e `dist-tags`) e baixei os pacotes com `npm pack`, para ler o código;
- baixei e li os três model cards (Face Mesh V2, Blendshape V2 e BlazeFace) e o modelo canônico da malha, para conferir os índices das ROIs;
- escrevi um protótipo em TypeScript e rodei **23 testes `node --test`, todos passando** (Node 26.2.0, sem compilar);
- conferi os tipos com o `tsc` 6.0.3 do próprio painel contra o `vision.d.ts` 1.1.1 e o React 19 (`tsc` saiu com 0).

Protótipo (scratchpad, fora do repositório):
`C:\Users\MATHEU~1\AppData\Local\Temp\claude\c--Users-Matheus-Corte-Downloads-Vigilancia-Motorista-main-Vigilancia-Motorista-main\b92b8a20-6be0-44e6-8616-27345e1b8984\scratchpad\demo-proto\`
(`src/rppg.ts`, `src/sono.ts`, `src/malha.ts`, `src/roi.ts`, `src/motor.ts`, `src/camera-demo.tsx`, `testes/*.test.ts`).

> [!warning] Três achados que mudam o plano
> 1. **O `@mediapipe/tasks-vision` 1.1.x manda métricas de uso para o Google** (`https://odml.pa.googleapis.com/v1/log`, a cada 60 s e no `close()`). Imagens não saem, mas a frase "nada sai do aparelho" deixa de ser verdade sem bloqueio. Correção: CSP `connect-src 'self'` (seção 5).
> 2. **A spec 025 manda criar a pasta `components/live/camera/`, mas isso quebra o teste SCR-13**: ele faz `readdirSync` de `components/live/` e `readFileSync` de cada item, e uma subpasta dá `EISDIR` (reproduzi). Saídas possíveis: arquivos soltos em `live/` (`camera-*.ts`) ou ajustar o SCR-13 para ler só arquivos.
> 3. **O painel web usa `basePath: "/painel"`** (spec 024, decisão 6), então caminhos fixos como `/mediapipe/...` dão 404 na VPS. O caminho tem que vir de uma variável de build (seção 6).

---

## 1. Biblioteca da malha facial: `@mediapipe/tasks-vision`

### Versão e licença (conferidas no npm em 19/10/2026)

| Pacote | `latest` | Outras tags | Licença | Última publicação |
|---|---|---|---|---|
| `@mediapipe/tasks-vision` | **1.1.1** (14/10/2026) | `nightly: 1.2.0-rc.20261018` (não usar) | Apache-2.0 | 14/10/2026 |
| `@vladmandic/human` | 3.3.6 | — | MIT | 26/08/2025 |
| `@vladmandic/face-api` | 1.7.15 | — | MIT | 05/02/2025 |
| `face-api.js` | 0.22.2 | — | MIT | 02/05/2022 (parado) |

Histórico estável do tasks-vision: 0.10.35 (27/04/2026), 1.0.0 (28/07), 1.0.1 (31/07), 1.1.0 (06/10), 1.1.1 (14/10).
Notas das versões ([releases](https://github.com/google-ai-edge/mediapipe/releases)): **1.1.0 "Add stats logging to
Web Tasks"**; 1.0.0 "Add dummy logging framework" e "Add MediaPipe Tasks Privacy Notice".

> [!note] Conflito com decisão antiga
> `PENDENCIAS.md:178` e o `webapp` legado (`painel/webapp/assets/js/views/testmode.js:21`) fixam a **1.0.1**. A regra
> é usar a estável mais nova (1.1.1). A diferença que importa é a telemetria: no 1.0.1 a classe que envia existe no
> bundle, mas não achei onde ela é criada. No 1.1.1 ela nasce junto com cada tarefa (`t.o=new $h(...)` em
> `vision_bundle.mjs`). Recomendo a **1.1.1 com CSP** (protege em qualquer versão). Se o Matheus preferir a 1.0.1,
> a justificativa ("sem telemetria") fica escrita na spec.

### O que vem no pacote 1.1.1 (lido do tarball)

- `vision_bundle.mjs` (156 KB), `vision.d.ts`, e `wasm/` com três pares `.js`/`.wasm`: `vision_wasm_internal`
  (SIMD, 13,5 MB), `vision_wasm_nosimd_internal` (12,6 MB) e `vision_wasm_module_internal` (só para `useModule = true`).
- `FilesetResolver.forVisionTasks(basePath, useModule = false)` monta `${basePath}/vision_wasm[_nosimd]_internal.{js,wasm}`
  e escolhe a versão sem SIMD sozinho (`isSimdSupported()`). O carregador entra por `<script>` injetado na thread
  principal ou por `importScripts` num worker. **Sem `eval` e sem `new Function`** (procurei nos dois arquivos), mas
  com `WebAssembly.instantiateStreaming`. Por isso a CSP precisa de `'wasm-unsafe-eval'`, e o `.wasm` tem que ir
  como `application/wasm`.
- **Sem `SharedArrayBuffer`** nos três carregadores (contagem 0). Por isso **COOP/COEP não são necessários**.
- `BaseOptions.delegate?: "CPU" | "GPU"`; `FaceLandmarker.detectForVideo(videoFrame, timestamp, imageProcessingOptions?)`;
  `FaceLandmarkerResult` traz `faceLandmarks`, `faceBlendshapes` e `facialTransformationMatrixes` (`Matrix {rows, columns, data}`).
- Constantes de conexão: `FACE_LANDMARKS_TESSELATION`, `_CONTOURS`, `_FACE_OVAL`, `_LIPS`, `_LEFT_EYE`/`_RIGHT_EYE`,
  `_LEFT_IRIS`/`_RIGHT_IRIS` e `_LEFT_EYEBROW`/`_RIGHT_EYEBROW`. Mais `DrawingUtils` (`drawLandmarks`, `drawConnectors`).

### Modelo `.task`

- Bundle `face_landmarker.task` float16: BlazeFace short-range (192×192), FaceMesh-V2 (256×256), 478 pontos, e Blendshape
  com 52 saídas ([guia oficial](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker)).
- **O arquivo que já está no repositório (`caixa/vision/models/face_landmarker.task`, 3.758.596 bytes, versionado no
  git) é idêntico ao `float16/latest` do Google:** o SHA-256 começa por `64184e229b263107bc2b` nos dois. O
  Last-Modified do Google é 03/05/2023. Dá para copiar daí na hora do build, sem baixar nada.
- Bom para a demo: a caixa e o navegador usam o mesmo modelo.

### Hospedar local (sem CDN de terceiros)

```ts
const fileset = await FilesetResolver.forVisionTasks(`${BASE}/mediapipe/wasm`); // pasta própria, não jsDelivr
const lm = await FaceLandmarker.createFromOptions(fileset, {
  baseOptions: { modelAssetPath: `${BASE}/mediapipe/modelos/face_landmarker.task`, delegate: "GPU" },
  runningMode: "VIDEO", numFaces: 1, outputFaceBlendshapes: true, outputFacialTransformationMatrixes: true,
});
```
Na doc oficial o exemplo de JS usa `cdn.jsdelivr.net/.../@latest/wasm` ([web_js](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker/web_js)). Não usar: é terceiro e a versão flutua.

### GPU delegate

- `delegate: "GPU"` usa WebGL2. Se `createFromOptions` falhar (sem WebGL2, driver bloqueado), cair para `"CPU"`. O
  protótipo faz isso com try/catch (`motor.ts`) e mostra o delegate usado na tela.
- A `DrawingUtils` aceita contexto WebGL2 para desenhar dados da GPU. Para pontos (que já vêm como números), o canvas 2D próprio basta e é mais simples.

### Desempenho em celular médio e notebook

- **Não achei benchmark oficial do Google para o FaceLandmarker web.** A página do modelo não traz latências.
- Único número público, de um concorrente (não verificado): ~9 ms por inferência do MediaPipe num iPhone 16 Pro no
  Safari ([micro-facemesh README](https://cdn.jsdelivr.net/npm/@svenflow/micro-facemesh@0.1.2/README.md)).
- > [!note] Hipótese, confirmar nos aparelhos da equipe
  > Notebook com GPU integrada: de 30 fps cravados. Celular Android médio: de 15 a 30 fps com GPU. Por isso a demo
  > **mostra fps, ms por inferência e o delegate** (DEMO-12) e avisa quando ficar abaixo de 24 fps. É o
  > `MIN_FPS_FOR_DURATION` do Python: abaixo disso, a duração da piscada não é confiável.
- Pedir câmera de 640×480 a 30 fps (`ideal`). Mais resolução não melhora a malha (a entrada é 256×256) e só custa tempo
  de cópia.

### `detectForVideo` com `requestVideoFrameCallback`

- `requestVideoFrameCallback` é **Baseline 2024** (out/2024) ([MDN](https://developer.mozilla.org/en-US/docs/Web/API/HTMLVideoElement/requestVideoFrameCallback)).
  Ele chama uma vez por quadro novo da câmera, sem processar o mesmo quadro duas vezes. Se a inferência demora, os
  quadros seguintes são pulados sozinhos.
- O `timestamp` tem que **crescer sempre** (em ms). O protótipo usa `Math.max(ultimo + 1, Math.round(agora))`.
- Para navegador sem rVFC, a reserva é `requestAnimationFrame` comparando `video.currentTime`.
- O código está em `motor.ts` (`rodar()`). O React só atualiza o texto 4 vezes por segundo; o canvas atualiza a cada quadro.

### Alternativas (resumo)

- **Human 3.3.6** (MIT): rosto, íris, emoção, corpo e mão em TF.js 4.10 (WebGL/WebGPU/WASM)
  ([GitHub](https://github.com/vladmandic/human)). A malha padrão tem 468 pontos e não há blendshapes do MediaPipe. A
  última publicação é de ago/2025. Pesa mais e não reaproveita o modelo da caixa.
- **face-api.js 0.22.2**: parado desde 2022, com 68 pontos. Não serve. O fork `@vladmandic/face-api` 1.7.15 é de fev/2025.
- **Conclusão:** MediaPipe Tasks Vision, porque usa o mesmo modelo e as mesmas regras do Python, tem blendshapes e matriz de pose, e é Apache-2.0.

---

## 2. Desenho das "bolinhas"

### Como montar

- Use um contêiner com `aspect-ratio` igual ao do vídeo. Dentro dele, o `<video>` em `object-fit: fill` e o
  `<canvas>` com `position: absolute; inset: 0`. Assim, `x * canvas.width` cai exatamente no pixel do vídeo, sem
  conta de recorte do `cover`.
- **Espelhe só a exibição** (`transform: scaleX(-1)` no contêiner, que vira os dois juntos). O MediaPipe recebe o vídeo
  original. O guia avisa que `*Left`/`*Right` dos blendshapes são do rosto da pessoa, e que imagem espelhada inverte
  esses valores ([guia](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker)).
- O tamanho interno do canvas é `clientWidth × devicePixelRatio`, limitado a 2. Ajustar no `resize`, nunca a cada quadro.

### Estilo (sugestão, trocar pelos tokens do painel)

| Camada | O que | Estilo |
|---|---|---|
| 1 | ROIs do pulso (testa e duas bochechas) | preenchimento vermelho a 16% e borda a 65%: mostra de onde vem o bpm |
| 2 | Tesselação (`FACE_LANDMARKS_TESSELATION`) | linha de 0,5 px, branco a 10%; no modo "leve", só `FACE_LANDMARKS_CONTOURS` |
| 3 | 478 pontos | quadrados de ~2 px, branco a 55% (parecem círculos nesse tamanho e custam menos que `arc`) |
| 4 | Olhos, íris e boca | círculos um pouco maiores, em verde-água (olhos e íris) e âmbar (boca) |

Índices das ROIs, **conferidos no modelo canônico**
([canonical_face_model.obj](https://raw.githubusercontent.com/google-ai-edge/mediapipe/master/mediapipe/modules/face_geometry/data/canonical_face_model.obj),
coordenadas x e y no espaço do modelo):

| ROI | Índices | Onde caem |
|---|---|---|
| Testa | `69, 108, 151, 337, 299, 296, 336, 9, 107, 66` | y de 4,9 a 6,6, acima das sobrancelhas (o topo da sobrancelha fica em ~5,1) e abaixo do cabelo (10, 109 e 338 ficam em 8,2 a 8,3, perto demais) |
| Bochecha direita (da pessoa) | `117, 118, 101, 36, 205, 187, 123` | x de −6,3 a −2,8; y de −2,2 a 0,9 (olho em ~2,5, nariz em x 0) |
| Bochecha esquerda | `346, 347, 330, 266, 425, 411, 352` | espelho exato da direita |

Os centros 151, 50 e 280 do [R2I-rPPG](https://arxiv.org/html/2410.15851v2) ficam dentro desses polígonos. O "cheat
sheet" que dá 234 e 454 como bochechas está errado para rPPG: esses pontos ficam no contorno do rosto (x ±7,7).

### Desempenho

- **Cerca de 10 chamadas de desenho por quadro:** um `beginPath`, muitos subcaminhos e um único `fill`/`stroke` por
  cor (ROIs, malha e quatro grupos de pontos). Nada de `stroke()` por linha nem `fillText`.
- A tesselação tem ~2,5 mil segmentos num único `stroke()`. Em celular fraco, trocar para `modo = "leve"` (só contornos).
- > [!note] Hipótese, medir
  > Calculei de 1 a 4 ms por quadro no canvas 2D. Se passar disso no celular da demo, usar o modo leve. WebGL não
  > compensa a complexidade para 478 pontos.

Código completo em `demo-proto/src/malha.ts` (tipos conferidos). O núcleo, condensado (no arquivo, os grupos de cor
são montados dentro de `desenhar`):

```ts
desenhar(lm: NormalizedLandmark[], roiAtiva = true): void {
  const ctx = this.ctx, w = ctx.canvas.width, h = ctx.canvas.height;
  const r = Math.max(1, w / 520);
  ctx.clearRect(0, 0, w, h);
  if (roiAtiva) {                                   // 1. ROIs do pulso
    ctx.beginPath();
    for (const roi of ROIS) {
      roi.forEach((i, k) => (k ? ctx.lineTo(lm[i].x * w, lm[i].y * h) : ctx.moveTo(lm[i].x * w, lm[i].y * h)));
      ctx.closePath();
    }
    ctx.fillStyle = this.tema.roi; ctx.fill();
    ctx.lineWidth = r * 0.8; ctx.strokeStyle = this.tema.roiBorda; ctx.stroke();
  }
  const conexoes = this.modo === "completa" ? this.tess : FaceLandmarker.FACE_LANDMARKS_CONTOURS;
  ctx.beginPath();                                  // 2. malha numa passada só
  for (const { start, end } of conexoes) { ctx.moveTo(lm[start].x * w, lm[start].y * h); ctx.lineTo(lm[end].x * w, lm[end].y * h); }
  ctx.lineWidth = Math.max(0.5, r * 0.45); ctx.strokeStyle = this.tema.malha; ctx.stroke();
  for (const [cor, pertence, raio] of this.grupos(r)) { // 3. pontos: uma passada por cor
    ctx.beginPath();
    for (let i = 0; i < lm.length; i++) {
      if (!pertence(i)) continue;
      const x = lm[i].x * w, y = lm[i].y * h;
      if (raio <= r) ctx.rect(x - raio, y - raio, raio * 2, raio * 2);
      else { ctx.moveTo(x + raio, y); ctx.arc(x, y, raio, 0, Math.PI * 2); }
    }
    ctx.fillStyle = cor; ctx.fill();
  }
}
```
(Os conjuntos de índices de olhos, íris e boca saem das constantes `FACE_LANDMARKS_*` no construtor.)

---

## 3. rPPG no navegador

### Extrair a média RGB barata (`demo-proto/src/roi.ts`)

1. Para cada ROI, pegar o retângulo que envolve o polígono e usar só o **miolo de 70%** (fica longe de sobrancelha,
   nariz e borda).
2. `drawImage(video, sx, sy, sw, sh, k*24, 0, 24, 24)` num canvas pequeno, criado com `willReadFrequently: true`. O
   próprio `drawImage` reduz a ROI a 24×24 (a média se preserva).
3. Um único `getImageData` de 72×24 px (~7 KB) por quadro. Filtro simples de pele: descartar pixels com luminância
   abaixo de 25 ou acima de 245 (sombra e reflexo) e pixels com `R < G` (não é pele).
4. Com `|yaw| > 20°`, descartar a bochecha do fundo, como faz o [R2I-rPPG](https://arxiv.org/html/2410.15851v2).
   > [!note] Hipótese
   > Não testei o sinal do yaw por lado. Na tela, conferir qual bochecha some ao virar o rosto.
- **Worker e OffscreenCanvas:** não são necessários com recorte desse tamanho. O `estimarBpm` mediu **0,45 ms por
  chamada** neste notebook (média de 200 chamadas, janela de 10 s a 30 Hz, nfft de 2048) e roda uma vez por segundo.
  Se for preciso tirar trabalho da thread principal, a saída é `createImageBitmap(video, sx, sy, sw, sh, {resizeWidth: 24, resizeHeight: 24})`
  transferido para um worker. > [!note] Hipótese: confirmar o suporte às opções de resize no Safari antes de usar.
- **Luz e câmera:** o autoajuste de exposição e de balanço de branco da webcam atrapalha o rPPG. Opcional:
  `track.applyConstraints({ advanced: [{ exposureMode: "manual", whiteBalanceMode: "manual" }] })` dentro de try/catch.
  > [!note] Hipótese: depende da câmera e do navegador. Para o pitch, o que mais ajuda é luz frontal estável e a pessoa parada.

### Algoritmo (mesmos parâmetros da spec 022, para o navegador e a caixa darem o mesmo número)

1. Reamostrar para 30 Hz pelo timestamp (a câmera oscila).
2. **POS** ([Wang et al., 2017](https://arxiv.org/pdf/1901.04366), descrito no toolbox iPhys): janela L = ⌈1,6 s × fs⌉;
   em cada janela, normalizar pela média temporal, projetar com `P = [[0,1,−1],[−2,1,1]]` (S1 = G−B, S2 = −2R+G+B),
   h = S1 + (σS1/σS2)·S2, tirar a média e somar com sobreposição.
3. Remover a tendência linear.
4. Espectro: Hann com zero-padding até 2048. Com janela de 10 s e segmento único, o Welch vira um periodograma.
   Procurar o pico em **0,7 a 3,0 Hz (42 a 180 bpm)** e refinar com interpolação parabólica.
5. SNR (de Haan e Jeanne, 2013): energia perto do pico e do 2º harmônico contra o resto da banda.
6. Primeiro número só com **6 s**. Janela de **10 s**, atualizada **1 vez por segundo**. Sem rosto, zera tudo.

> [!warning] Achado para as specs 022 e 025: ±0,1 Hz no SNR é estreito demais para janela de 10 s
> Com janela de Hann de 10 s, o lóbulo principal ocupa ±2/T = ±0,2 Hz. Medi com uma senoide **limpa** de 72 bpm: o
> SNR dá **9,3 dB com ±0,1 Hz** e **29,1 dB com ±0,2 Hz**. Com ruído realista, dá 0,8 dB contra 2,7 dB, e só ruído dá
> −8,1 dB contra −6,9 dB. Com ±0,1 Hz, metade do próprio pico conta como ruído, e o limiar de "sinal fraco" fica
> dependente do tamanho da janela. O protótipo usa **±0,2 Hz** (`MEIA_BANDA_HZ`) e limiar de **0 dB** (`SNR_MIN_DB`).
> Os dois são **hipóteses a validar com pessoas reais e oxímetro**. O Python (`cardio.py`) precisa usar o mesmo valor.

### Código funcional (o mesmo testado; arquivo `demo-proto/src/rppg.ts`)

```ts
export type RgbSample = { t: number; r: number; g: number; b: number }; // t em segundos
export type HeartEstimate = { bpm: number; snrDb: number; confiavel: boolean; progresso: number; onda: Float64Array; fs: number };

export const FAIXA_HZ = { min: 0.7, max: 3.0 }; // 42 a 180 bpm (spec 022)
export const JANELA_S = 10;
export const JANELA_MIN_S = 6;
export const SNR_MIN_DB = 0;      // hipótese
export const MEIA_BANDA_HZ = 0.2; // ver o aviso acima

export function reamostrar(amostras: RgbSample[], fs: number) {
  const n = amostras.length;
  if (n < 2) return { r: new Float64Array(0), g: new Float64Array(0), b: new Float64Array(0) };
  const t0 = amostras[0].t, total = Math.floor((amostras[n - 1].t - t0) * fs) + 1;
  const r = new Float64Array(total), g = new Float64Array(total), b = new Float64Array(total);
  let j = 0;
  for (let i = 0; i < total; i++) {
    const t = t0 + i / fs;
    while (j < n - 2 && amostras[j + 1].t < t) j++;
    const a = amostras[j], c = amostras[j + 1], span = c.t - a.t;
    const w = span > 0 ? Math.min(1, Math.max(0, (t - a.t) / span)) : 0;
    r[i] = a.r + w * (c.r - a.r); g[i] = a.g + w * (c.g - a.g); b[i] = a.b + w * (c.b - a.b);
  }
  return { r, g, b };
}

/** POS: projeção no plano ortogonal ao tom de pele, janela de 1,6 s, soma com sobreposição. */
export function pos(r: Float64Array, g: Float64Array, b: Float64Array, fs: number): Float64Array {
  const n = r.length, l = Math.ceil(1.6 * fs), h = new Float64Array(n);
  if (n < l) return h;
  const s1 = new Float64Array(l), s2 = new Float64Array(l);
  for (let fim = l - 1; fim < n; fim++) {
    const ini = fim - l + 1;
    let mr = 0, mg = 0, mb = 0;
    for (let k = ini; k <= fim; k++) { mr += r[k]; mg += g[k]; mb += b[k]; }
    mr /= l; mg /= l; mb /= l;
    if (mr <= 0 || mg <= 0 || mb <= 0) continue;
    for (let k = 0; k < l; k++) {
      const cr = r[ini + k] / mr, cg = g[ini + k] / mg, cb = b[ini + k] / mb;
      s1[k] = cg - cb;           // P = [[0, 1, -1],
      s2[k] = -2 * cr + cg + cb; //      [-2, 1, 1]]
    }
    const alfa = desvio(s1) / (desvio(s2) || 1e-12);
    let media = 0;
    for (let k = 0; k < l; k++) media += s1[k] + alfa * s2[k];
    media /= l;
    for (let k = 0; k < l; k++) h[ini + k] += s1[k] + alfa * s2[k] - media;
  }
  return h;
}

function desvio(x: Float64Array): number {
  let m = 0; for (let i = 0; i < x.length; i++) m += x[i]; m /= x.length;
  let v = 0; for (let i = 0; i < x.length; i++) v += (x[i] - m) ** 2;
  return Math.sqrt(v / x.length);
}

export function tirarTendencia(x: Float64Array): Float64Array {
  const n = x.length;
  let st = 0, sx = 0, stt = 0, stx = 0;
  for (let i = 0; i < n; i++) { st += i; sx += x[i]; stt += i * i; stx += i * x[i]; }
  const den = n * stt - st * st || 1, a = (n * stx - st * sx) / den, c = (sx - a * st) / n;
  const y = new Float64Array(n);
  for (let i = 0; i < n; i++) y[i] = x[i] - (a * i + c);
  return y;
}

/** FFT radix-2 iterativa, in-place (re.length = potência de 2). */
export function fft(re: Float64Array, im: Float64Array): void {
  const n = re.length;
  for (let i = 1, j = 0; i < n; i++) {
    let bit = n >> 1;
    for (; j & bit; bit >>= 1) j ^= bit;
    j ^= bit;
    if (i < j) { [re[i], re[j]] = [re[j], re[i]]; [im[i], im[j]] = [im[j], im[i]]; }
  }
  for (let len = 2; len <= n; len <<= 1) {
    const ang = (-2 * Math.PI) / len, wr = Math.cos(ang), wi = Math.sin(ang);
    for (let i = 0; i < n; i += len) {
      let cr = 1, ci = 0;
      for (let k = 0; k < len / 2; k++) {
        const ar = re[i + k + len / 2] * cr - im[i + k + len / 2] * ci;
        const ai = re[i + k + len / 2] * ci + im[i + k + len / 2] * cr;
        re[i + k + len / 2] = re[i + k] - ar; im[i + k + len / 2] = im[i + k] - ai;
        re[i + k] += ar; im[i + k] += ai;
        const t = cr * wr - ci * wi; ci = cr * wi + ci * wr; cr = t;
      }
    }
  }
}

/** Welch (Hann, 50% de sobreposição, zero-padding). Com segmento = sinal inteiro, vira periodograma. */
export function welch(x: Float64Array, fs: number, segmento = x.length, nfft = 2048) {
  const seg = Math.min(segmento, x.length), passo = Math.max(1, Math.floor(seg / 2));
  const psd = new Float64Array(nfft / 2 + 1), hann = new Float64Array(seg);
  for (let i = 0; i < seg; i++) hann[i] = 0.5 - 0.5 * Math.cos((2 * Math.PI * i) / Math.max(1, seg - 1));
  let segmentos = 0;
  for (let ini = 0; ini + seg <= x.length; ini += passo) {
    const re = new Float64Array(nfft), im = new Float64Array(nfft);
    for (let i = 0; i < seg; i++) re[i] = x[ini + i] * hann[i];
    fft(re, im);
    for (let k = 0; k < psd.length; k++) psd[k] += re[k] * re[k] + im[k] * im[k];
    segmentos++;
  }
  for (let k = 0; k < psd.length; k++) psd[k] /= Math.max(1, segmentos);
  const freqs = new Float64Array(psd.length);
  for (let k = 0; k < freqs.length; k++) freqs[k] = (k * fs) / nfft;
  return { freqs, psd };
}

export function picoESnr(freqs: Float64Array, psd: Float64Array) {
  let melhor = -1;
  for (let k = 1; k < psd.length - 1; k++) {
    if (freqs[k] < FAIXA_HZ.min || freqs[k] > FAIXA_HZ.max) continue;
    if (melhor < 0 || psd[k] > psd[melhor]) melhor = k;
  }
  if (melhor < 0) return { hz: NaN, snrDb: -Infinity };
  const a = psd[melhor - 1], b = psd[melhor], c = psd[melhor + 1], den = a - 2 * b + c;
  const hz = freqs[melhor] + (den !== 0 ? (0.5 * (a - c)) / den : 0) * (freqs[1] - freqs[0]); // parábola
  let sinal = 0, ruido = 0;
  for (let k = 0; k < psd.length; k++) {
    const f = freqs[k];
    if (f < FAIXA_HZ.min || f > 2 * FAIXA_HZ.max + MEIA_BANDA_HZ) continue;
    if (Math.abs(f - hz) <= MEIA_BANDA_HZ || Math.abs(f - 2 * hz) <= MEIA_BANDA_HZ) sinal += psd[k];
    else ruido += psd[k];
  }
  return { hz, snrDb: 10 * Math.log10((sinal || 1e-12) / (ruido || 1e-12)) };
}

export function estimarBpm(amostras: RgbSample[], fs = 30): HeartEstimate | null {
  if (amostras.length < 2) return null;
  const fim = amostras[amostras.length - 1].t;
  const janela = amostras.filter((a) => a.t >= fim - JANELA_S);
  const duracao = fim - janela[0].t;
  if (duracao < JANELA_MIN_S) return null;
  const { r, g, b } = reamostrar(janela, fs);
  const onda = tirarTendencia(pos(r, g, b, fs));
  const { freqs, psd } = welch(onda, fs);
  const { hz, snrDb } = picoESnr(freqs, psd);
  const max = onda.reduce((m, v) => Math.max(m, Math.abs(v)), 1e-12);
  for (let i = 0; i < onda.length; i++) onda[i] /= max;
  return { bpm: hz * 60, snrDb, confiavel: snrDb >= SNR_MIN_DB, progresso: Math.min(1, duracao / JANELA_S), onda, fs };
}
```

### Exibição ao vivo

- Até `progresso` 0,9: "medindo… fique parado". Depois, `confiavel ? "72 bpm" : "sinal fraco"`. Nunca mostrar número
  com SNR abaixo do limiar.
- Onda: os últimos 6 s de `onda`, desenhados num canvas de 720×80 a cada quadro. Linha vermelha quando o sinal é
  confiável e cinza quando não é (`desenharOnda` em `camera-demo.tsx`).
- A spec 022 também pede suavização por mediana das últimas leituras e pausa quando a cabeça mexe. Ficaram fora do
  protótipo: entram com os critérios de movimento (CAR-07) quando forem portados.

---

## 4. Regras de sono portadas do Python (`demo-proto/src/sono.ts`)

Mesmos limiares, copiados de `caixa/vision/eyes.py`, `calibration.py` e `drowsiness.py`:

| Regra | Python (fonte) | Navegador |
|---|---|---|
| EAR de 6 pontos | `face.py:36-37` (`RIGHT_EYE = 33,160,158,133,153,144`; `LEFT_EYE = 362,385,387,263,373,380`), `face.py:120-126` | `ear()` **em pixels** (`x*videoWidth`, `y*videoHeight`); em coordenadas normalizadas o EAR distorce com a proporção do vídeo |
| Abertura relativa sem calibração | `eyes.py:198-204`: EAR aberto = mediana dos últimos 600 EAR com `blink_score < 0,3`; fechado = 0,3 × aberto | `AberturaAuto` (precisa de ~30 quadros, cerca de 1 s) |
| Piscada | `BLINK_START 0,50`, `BLINK_END 0,60` (histerese), `P80 0,20`, cruzamento por interpolação (`eyes.py:289-346`) | `RastreadorDeOlho` (sem as velocidades da pálpebra/AVR) |
| Olhos fechados | `MICROSLEEP_S 1,0`, `SLEEP_S 3,0`, `UNRESPONSIVE_S 6,0` (`drowsiness.py:28-30`) | `estagio` em `MonitorDeSono` |
| PERCLOS P80 | baldes de 1 s; o fechamento só conta depois de 250 ms (`SHORT_CLOSURE_S`); só vale com 50% da janela (`drowsiness.py:104-145, 290-296`) | `Perclos` com janelas de **60 s** (para o pitch) e 3 min; alerta a partir de 12% |
| Bocejo | `jawOpen ≥ max(0,45; base + 0,30)` por **2,0 s**, solta abaixo do limiar − 0,1 (`drowsiness.py:50-52, 385-397`) | igual (`jawBase = 0` sem calibração) |
| Cabeceio | pitch sobe ≥ 15° em até 1 s, a partir de ≤ 5° da referência (mediana móvel de 10 s); fica baixo de 0,3 a 3 s; volta a ≤ 7° (`drowsiness.py:54-64, 151-206`) | `Cabeceio` (porte linha a linha) |
| Pose | `rotation_to_euler`: pitch = atan2(r21, r22), yaw = atan2(−r20, √(r21²+r22²)), roll = atan2(r10, r00) (`face.py:128-135`) | `eulerDaMatriz(data, colunaMaior = true)` |

> [!note] Hipótese: ordem da matriz no JS
> O `vision.d.ts` só diz "flattened one-dimensional array", sem a ordem. Assumi coluna-maior (o padrão do `MatrixData`
> do MediaPipe), e a função aceita as duas. **Conferir na tela:** ao baixar a cabeça, o pitch tem que ficar positivo
> (convenção do Python e da nota 7 de "Erros e aprendizados" da vault). Se ficar negativo ou se mexer quando a cabeça
> gira de lado, trocar para `colunaMaior = false`.

**Blendshapes que ajudam** (52 no total; o model card diz que os valores vão de 0 a 1):

| Blendshape | Uso | Status |
|---|---|---|
| `eyeBlinkLeft`/`eyeBlinkRight` | fechamento do olho; o Python usa como `blink_score` e para escolher quadros de olho aberto na referência do EAR | usado em `face.py:260-262` |
| `jawOpen` | bocejo | usado em `face.py:293` e `drowsiness.py:385` |
| `eyeLookDownLeft`/`eyeLookDownRight` | separar "olhando para baixo" (celular, painel) de "olho fechado", porque olhar para baixo também derruba o EAR | hipótese, testar |
| `eyeSquintLeft`/`eyeSquintRight` | apertar o olho (sol, sorriso) baixa o EAR sem sono; serve para não dar alarme falso | hipótese |
| `eyeWideLeft`/`eyeWideRight` | olho arregalado depois de cochilo (reação de susto) | hipótese, só exibição |
| `mouthClose`, `mouthStretchLeft`/`mouthStretchRight`, `mouthFunnel` | separar bocejo (boca muito aberta e esticada) de fala ou canto, junto com `jawOpen` | hipótese |
| `eyeLookIn`/`Out`/`Up` | direção aproximada do olhar | só exibição |

Em vez de escolher entre EAR e blendshape, a recomendação é combinar os dois, como o Python faz.

Fora do porte (a caixa continua sendo a referência): calibração individual de 60 s, duração da piscada em relação à
linha de base, AVR (velocidade da pálpebra), níveis de atenção e de alerta por janela de 10 min, celular e mão no
rosto. Para o celular, o mesmo pacote tem `ObjectDetector` e `HandLandmarker`, e os modelos já estão em
`caixa/vision/models`: o `efficientdet_lite0_*.tflite` (7,3 MB e 4,6 MB) e o `hand_landmarker.task` (7,8 MB). Ficam para
uma segunda etapa, porque somam ~12 MB e outra inferência por quadro.

---

## 5. Privacidade e permissões

- **`getUserMedia` só funciona em contexto seguro** (HTTPS, `localhost` ou `file://`); fora dele,
  `navigator.mediaDevices` é `undefined` ([MDN](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia)).
  A VPS tem HTTPS pelo Caddy, e o painel instalado abre em `localhost`.
- Erros que a tela precisa tratar (CAM-08): `NotAllowedError` (negado ou bloqueado por política),
  `NotFoundError` (sem câmera), `NotReadableError` (câmera ocupada, por exemplo pelo script da caixa aberto no mesmo
  PC) e `OverconstrainedError`. As mensagens em pt-BR estão em `camera-demo.tsx`.
- Cabeçalho `Permissions-Policy: camera=(self), microphone=(), geolocation=()`.
- **O que "nada sai do aparelho" exige, na prática:**
  1. Nenhum `fetch` ou envio de quadro, ponto ou número nosso para o servidor (CAM-07).
  2. **Bloquear a telemetria do MediaPipe 1.1.x.** O aviso de privacidade do pacote (README, "Last modified: June 5,
     2026") diz que o processamento é no aparelho, mas que *"MediaPipe Tasks APIs send metrics about the performance
     and utilization of the APIs in your app to Google"*. Diz também que *"You are responsible for obtaining informed
     consent from your app users about Google's processing of MediaPipe metrics data"*
     ([ToS do MediaPipe](https://developers.google.com/edge/mediapipe/legal/tos)). No código, o envio é um POST para
     `https://odml.pa.googleapis.com/v1/log` a cada 60 s (`setInterval(...flush, 6e4)`) e no `close()`. Se o envio
     falhar, ele para sozinho (`clearInterval`) e não quebra a tarefa.
     **Correção:** CSP com `connect-src 'self'`. Na web, como cabeçalho do Caddy; no painel instalado, como
     `<meta http-equiv="Content-Security-Policy">` no `layout.tsx`. Nos dois lugares, porque o static export não
     emite cabeçalho. Assim o aviso de privacidade continua verdadeiro.
     > [!note] Hipótese, testar
     > Que a CSP em `<meta>` vale para os `fetch` do WASM no WebView2. Precisa de DEMO-15 com a aba de rede aberta
     > por **mais de 60 s** e com a câmera parada no final (o `close()` também dispara o envio).
- **Botão "Parar câmera" sempre visível** enquanto roda. Parar chama `track.stop()` em todas as trilhas, `video.srcObject = null`
  e `landmarker.close()`. Sair da tela ou esconder a aba (`visibilitychange`) também para.
- **iOS Safari:** `<video muted playsinline autoplay>` (sem `playsinline` o vídeo fica preto ou abre em tela cheia)
  ([Apple Forums](https://developer.apple.com/forums/thread/92713), [Valley of Code](https://thevalleyofcode.com/lesson/media-webrtc/webrtc-ios-black-box/)).
  Um segundo `getUserMedia` silencia a trilha anterior ([WebKit 179363](https://bugs.webkit.org/show_bug.cgi?id=179363)),
  então só uma câmera aberta por vez. Interrupções (print com marcação, ligação) silenciam a trilha
  ([WebKit 230698](https://bugs.webkit.org/show_bug.cgi?id=230698)): ouvir `track.onmute`/`onended` e oferecer "Tentar de novo".
  Usar `facingMode: "user"` como preferência, nunca `exact`.
  > [!note] Hipótese: os relatos são do iOS 11 a 15; confirmar no iPhone da equipe.
- **Android Chrome:** em geral funciona direto. Alguns aparelhos ignoram o pedido de 640×480 e entregam 1280×720, o que
  não é problema, porque o canvas segue o tamanho do vídeo. A permissão fica salva por site.
- **Painel instalado (pywebview 6.2.1 com WebView2):** o `edgechromium.py` dessa versão **não trata
  `PermissionRequested`** (procurei; só o `qt.py` trata), então vale o comportamento padrão do WebView2: perguntar.
  > [!note] Hipótese
  > Com `private_mode: True` (`rotaguard_painel.py:253`), a permissão não fica salva e o WebView2 pergunta a cada
  > abertura. A spec 025, decisão 6, diz "WebView2 permite câmera". Isso precisa ser testado na janela de verdade.
  > Se o script da caixa estiver aberto, o Windows costuma devolver `NotReadableError`.

**Texto curto de aviso** (antes de ligar). Sem "conforme a LGPD": o teste SITE-04 do site proíbe a frase enquanto não
houver parecer, e vale a mesma regra no painel.

> O teste usa a câmera para medir olhos, boca, posição da cabeça e uma estimativa da frequência cardíaca pela cor da
> pele. Rosto e frequência cardíaca são dados pessoais sensíveis. Tudo é calculado neste aparelho: nenhuma imagem,
> ponto ou número é gravado ou enviado. Ao parar ou sair da tela, a câmera desliga.
> Estimativa pela câmera, não é medida médica. A caixa RotaGuard continua sendo a referência.
> **[Ligar a câmera]**

Base legal: o PRD já registra que vídeo do rosto e frequência cardíaca são dado sensível (LGPD, art. 5º, II, e art. 11;
`docs/produto/PRD.md:171,194`). Não consegui abrir o texto da lei no Planalto (conexão recusada), então não citei os
artigos de novo. > [!note] Hipótese: o clique em "Ligar a câmera", depois do aviso, funciona como consentimento
específico e destacado para a demo. Isso **não substitui** o parecer jurídico e o RIPD já pendentes para o produto.

---

## 6. Integração com o painel (Next.js 16.3.5, static export)

### Onde fica cada coisa

| O quê | Onde | Por quê |
|---|---|---|
| Lógica pura testável (`rppg.ts`, `sono.ts`) | `painel/app/src/components/live/camera-rppg.ts` e `camera-sono.ts`, ou na pasta `camera/` **se o SCR-13 for ajustado** | sem imports de valor, igual ao `summary.ts`: o teste `.mjs` importa o `.ts` direto e o Node 26 tira os tipos (padrão de `ao-vivo.test.mjs:6`) |
| Navegador (`malha.ts`, `roi.ts`, `motor.ts`) | mesma pasta, com imports **sem** extensão `.ts` (o `tsconfig` do painel não tem `allowImportingTsExtensions`) | só o bundler lê esses arquivos |
| Componente | `camera-demo.tsx` (client), renderizado dentro de `LiveScreen` | a página `ao-vivo/page.tsx` continua server component só com `metadata` |
| WASM e modelo | `painel/app/public/mediapipe/wasm/` e `public/mediapipe/modelos/` → `out/mediapipe/...` | o static export copia `public/` como está |

> [!warning] SCR-13 x pasta `camera/`
> `scripts/testes/ao-vivo.test.mjs` lê **todo item** de `src/components/live/` com `readFileSync`, e uma subpasta dá
> `EISDIR` (reproduzi com `node`). A spec 025 pede `components/live/camera/*`. Uma das duas tem que mudar. Também:
> nenhum arquivo em `live/` pode ter `uppercase`, `font-mono` ou `rounded-full ... px-` (mesmo teste). O esboço
> `camera-demo.tsx` já respeita isso.

### Arquivos estáticos

- Não versionar o WASM (~14 MB). Fazer `scripts/copiar-mediapipe.mjs` rodar no `predev` e no `prebuild`:
  - de `node_modules/@mediapipe/tasks-vision/wasm/`, copiar **só** `vision_wasm_internal.js` e `vision_wasm_internal.wasm`
    (SIMD) e, se quiser cobrir aparelho muito antigo, o par `_nosimd_`. Não copiar o `_module_`;
  - copiar `caixa/vision/models/face_landmarker.task` (já está no git e é igual ao do Google);
  - adicionar `painel/app/public/mediapipe/` ao `.gitignore`.
- Tamanho: o `out/` de hoje tem 1,8 MB. Só com o SIMD e o modelo, sobe **~17,6 MB** (13,5 + 0,33 + 3,76). Com o par
  nosimd, ~30 MB. Pela rede (gzip -9, medido), o `.wasm` cai para **3,9 MB** e o `.task` para 3,3 MB (o modelo quase
  não comprime). O instalador do painel cresce o mesmo tanto.
  > [!note] Hipótese
  > Pular o nosimd só derruba navegador sem WebAssembly SIMD (estimei antes do Chrome 91 e do Safari 16.4).
  > Conferir no caniuse antes de decidir.

### `basePath` (spec 024, decisão 6)

- Na web, o build roda com `basePath: "/painel"`. O Next **não** reescreve URLs montadas à mão, então
  `"/mediapipe/wasm"` daria 404. Solução: em `next.config.ts`, a mesma variável que liga o `basePath` também entra em
  `env: { NEXT_PUBLIC_BASE_PATH: base }`. No código:
  `const BASE = process.env.NEXT_PUBLIC_BASE_PATH ?? ""; FilesetResolver.forVisionTasks(\`${BASE}/mediapipe/wasm\`)`.
  O painel instalado fica com `BASE = ""`.

### Sem SSR, sem rota de API e sem COOP/COEP

- No static export, `headers`, `rewrites`, `redirects`, proxy e Route Handlers que leem `Request` **não funcionam**
  (`node_modules/next/dist/docs/01-app/02-guides/static-exports.md:278-298`). Cabeçalho é com o servidor (Caddy).
- **COOP/COEP:** não precisa, porque o pacote não usa `SharedArrayBuffer` (conferido). E não convém: COEP `require-corp`
  quebraria recursos de outra origem se algum dia entrarem.
- **Não quebrar o build:** o componente é `"use client"` e a página só renderiza o aviso e o botão. O MediaPipe entra
  por `await import("./motor")` **dentro do clique** (`ligar()`), então nada dele roda no prerender, e o bundle de 156 KB
  e o WASM não entram no carregamento inicial. `next/dynamic({ ssr: false })` também serve
  (`node_modules/next/dist/docs/01-app/02-guides/lazy-loading.md:66`: só em client component), mas o `import()` no clique
  é mais simples e ainda adia o download até alguém pedir a câmera.
- O Turbopack não precisa saber do WASM: ele não é importado pelo bundler, é buscado em `public/` pela URL.
- Sem rota de API: tudo roda no cliente, nada vai para `/painel/api/`. Isso é bom para a privacidade.

### Cabeçalhos no Caddy (`rotaguard.caddy`, bloco do `/painel*`)

```caddy
header /painel* {
    Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; media-src 'self' blob: mediastream:; connect-src 'self'; worker-src 'self' blob:; font-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    Permissions-Policy "camera=(self), microphone=(), geolocation=()"
}
@mpwasm path /painel/mediapipe/wasm/*.wasm
header @mpwasm Content-Type "application/wasm"
```
- O `'unsafe-inline'` do `script-src` é porque o static export injeta scripts inline e não tem nonce. O
  `'wasm-unsafe-eval'` é para compilar o WASM, sem liberar `eval` de JS (doc local
  `01-app/02-guides/content-security-policy.md:721`). As fontes são servidas localmente pelo `next/font`.
- O servidor Python do painel (`painel/web/`, spec 024) também tem que mandar `.wasm` como `application/wasm` e `.task`
  como `application/octet-stream`. O `servir_app_local.py` já faz esse mapeamento
  (`painel/servir_app_local.py:19-24`).
- Ligar `encode zstd gzip` no Caddy para o `.wasm`.
- Cache: `Cache-Control: public, max-age=31536000, immutable` só se o caminho tiver a versão
  (`/mediapipe/1.1.1/wasm/`). Sem a versão no caminho, usar `no-cache` com ETag.
- **Painel instalado:** o mesmo CSP em `<meta httpEquiv="Content-Security-Policy">` no `layout.tsx`, sem
  `frame-ancestors` (não vale em meta).

### Desktop x web na mesma tela

- A spec 025, decisão 7, diz que no painel instalado continua a aba do script local e na web só o teste do navegador. Para
  saber onde está: a ponte já sabe a origem (`janela`, `demonstracao` ou o futuro `servidor`, em `bridge.ts:325-345`).
  Exportar um `origemDaPonte()` e mostrar a demo na web e no instalado, com o aviso de câmera ocupada no instalado.

---

## 7. Licenças e model cards: como apresentar com honestidade

- **Licenças:** a biblioteca e os modelos são Apache-2.0. Está na `package.json` do pacote e nos três model cards:
  Face Mesh V2 e Blendshape V2 ([cards](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker))
  e BlazeFace. Uso comercial é permitido. Pede `NOTICE` e atribuição: incluir em `THIRD_PARTY_NOTICES.md` e numa linha
  "Créditos" do painel.
- **O que os model cards dizem de verdade** (li os PDFs):
  - **Face Mesh V2** (15/09/2022) e **Blendshape V2** (11/11/2022): "The primary intended application is AR
    entertainment"; fora do escopo: *"This model is not intended for human life-critical decisions"*. Também: não
    faz reconhecimento nem identificação e não guarda representação única do rosto. Limites: rosto virado mais de 80°,
    **inclinado mais de 8° da vertical**, menos de 50% visível ou longe da câmera. O erro médio é 2,62% da distância
    entre os olhos (tracking), comparável à discordância entre anotadores humanos (2,56%).
  - **BlazeFace short-range** (09/06/2021, é o detector que vem **dentro** do `face_landmarker.task`): *"Any form of
    surveillance or identity recognition is explicitly out of scope and not enabled by this technology"*. Também
    exclui pessoas a mais de 2 m.
  - Então a frase "não é para vigilância" vem do card do **BlazeFace**. Os cards da malha e dos blendshapes falam em
    "decisões críticas para a vida humana". O mapa de licenças da vault já registra isso
    (`DriveSafe AI.../05 - Privacidade, licencas e model cards.md:33-37`).
- **Como apresentar na demo** (texto para slide ou rodapé da tela):
  > Demonstração técnica. A malha e os sinais vêm do MediaPipe (Google, Apache 2.0), modelos feitos para realidade
  > aumentada. Os fabricantes dizem que não servem para decisões críticas nem para vigilância ou identificação. Por isso
  > a RotaGuard não identifica ninguém, não decide sozinha e trata tudo como "sinais compatíveis com" sono, com regras
  > próprias e validação pendente. A frequência cardíaca é uma estimativa pela câmera, não é medida médica.
- Não dizer "detecta sono com X% de precisão" nem "mede a frequência cardíaca". O teste SITE-04 já proíbe números
  sem piloto.
- Ser franco com quem perguntar: o produto usa o modelo fora do uso pretendido pelo fabricante (AR). Isso é uma
  **escolha de engenharia que pede validação própria** (gravações da frota, oxímetro), não um uso endossado pelo Google.

---

## 8. Critérios de aceite (para a spec 025; numeração própria, com a equivalência)

As IDs DEMO-xx foram testadas no protótipo. Ao levar para o painel, renomear para CAM-xx (spec 025) ou manter as duas.
Os testes ficam em `painel/app/scripts/testes/camera-*.test.mjs`, importando os `.ts` puros (mesmo glob
`*.test.mjs` de hoje; o `package.json` não muda).

### Lógica pura (rodando no `node --test`; resultado do protótipo: **23 de 23 passando**)

| ID | Critério | Spec 025 | Protótipo |
|---|---|---|---|
| DEMO-20 | FFT: seno de 8 ciclos em 64 amostras cai no bin 8 | — | ✔ |
| DEMO-21 | POS: séries sintéticas (pulso mais forte no verde, luz oscilando 3% a 0,25 Hz, ruído de sensor, fps irregular de ±15%) a 48, 55, 72, 90, 120, 140 e 170 bpm: erro **≤ 2 bpm em 72** e ≤ 3 nas outras, depois de 12 s | CAM-01 | ✔ |
| DEMO-22 | 72 bpm captado a 15 fps (celular fraco): erro < 3 | — | ✔ |
| DEMO-22b | Ruído do tamanho do pulso, 5 sementes: erro < 3 em todas | — | ✔ |
| DEMO-23 | Sem pulso (só luz e ruído): SNR pelo menos 6 dB abaixo do caso com pulso e `confiavel = false` ("sinal fraco") | CAM-02 | ✔ |
| DEMO-24 | Menos de 6 s de amostras: sem número | (CAR-05) | ✔ |
| DEMO-25 | Rampa de luz de 30% em 10 s: bpm não muda mais de 3 | (CAR-06) | ✔ |
| DEMO-30 | EAR de 6 pontos com os índices de `face.py`: abertura 9 em largura 30 → 0,30; 1,5 → 0,05 | CAM-03 | ✔ |
| DEMO-31 | Piscada de 150 ms: conta 1 piscada e não vira microssono | CAM-04 (parte) | ✔ |
| DEMO-32 | Olhos fechados 1,2 s → microssono; 3,2 s → sono; 6,2 s → sem resposta; 0,9 s → normal | CAM-04 | ✔ |
| DEMO-33 | PERCLOS 60 s: 9 fechamentos de 1 s em 60 s → entre 12% e 18% | — | ✔ |
| DEMO-33b | PERCLOS 60 s com fechamentos de 2 s a cada 10 s (20%) → 0,20 ± 0,01 | CAM-05 | ✔ |
| DEMO-34 | PERCLOS ignora fechamentos < 250 ms e fica `null` com menos de metade da janela | — | ✔ |
| DEMO-35 | Bocejo: `jawOpen` 0,6 por 2,5 s conta 1; 0,6 por 0,8 s (fala) não conta | CAM-06 | ✔ |
| DEMO-36 | Cabeceio: queda de 20° em 0,3 s, 1 s baixo e volta → 1; inclinar 20° devagar e ficar → 0 | — | ✔ |
| DEMO-37 | `eulerDaMatriz`: rotação de +20° em X dá pitch +20 nas duas ordens de matriz | — | ✔ |
| DEMO-38 | Abertura automática: aprende EAR aberto 0,30 e leva 0,09 a ~0 | — | ✔ |

> [!warning] Dois conflitos com a spec 025 (decisão é do Matheus)
> - **CAM-06 fala em bocejo acima do limiar "por mais de 1,5 s"; o Python usa 2,0 s** (`YAWN_MIN_S`). A própria
>   spec 025, decisão 2, diz "mesmas regras do Python". Sugiro 2,0 s, como no DEMO-35.
> - **CAM-05 ("20% fechado → 0,20")** só dá 0,20 se o fechado vier em fechamentos de **mais de 250 ms**. Piscadas curtas
>   não entram no PERCLOS do Python. A série do teste tem que deixar isso explícito, como no DEMO-33b.

### Navegador e painel (precisam de navegador real; não executei)

| ID | Critério | Como testar |
|---|---|---|
| DEMO-01 | Antes de ligar: aviso de privacidade, "não é medida médica" e botão "Ligar a câmera"; nenhum arquivo do MediaPipe baixado | Playwright: aba de rede sem `/mediapipe/` antes do clique |
| DEMO-02 | Sem HTTPS (`isSecureContext = false`): mensagem "A câmera só funciona em endereço seguro (https)" | unitário com `window.isSecureContext` falso, ou servir por IP em http |
| DEMO-03 | `NotAllowedError`, `NotFoundError` e `NotReadableError` mostram a mensagem certa e "Tentar de novo", sem quebrar a tela (CAM-08) | Playwright com `getUserMedia` substituído para rejeitar |
| DEMO-04 | "Parar câmera" e sair da rota: todas as trilhas ficam com `readyState === "ended"` e `landmarker.close()` é chamado (CAM-09) | Playwright com câmera falsa (`--use-fake-device-for-media-stream`) |
| DEMO-05 | Com câmera falsa ou vídeo de rosto: 478 pontos desenhados, ROIs visíveis e o vídeo espelhado só na exibição | Playwright com `--use-file-for-fake-video-capture=rosto.y4m` + captura de tela |
| DEMO-06 | Os arquivos do MediaPipe vêm de `{BASE}/mediapipe/` com `BASE` = `/painel` (web) e `""` (instalado); zero 404 | build com e sem a variável + Playwright |
| DEMO-07 | `next build` (static export) e `eslint` sem erro; o HTML de `/ao-vivo/` não contém `tasks-vision` (CAM-10) | `npm run build && npm run lint`, e procurar a string em `out/ao-vivo/index.html` |
| DEMO-08 | Nenhum endereço externo em `src/components/live/**` (CAM-07) | `node --test` com regex `https?://` |
| DEMO-09 | SCR-13 continua passando com os arquivos novos (sem subpasta ou com o teste ajustado; sem `uppercase` nem `font-mono`) | `npm test` |
| DEMO-10 | `.wasm` com `Content-Type: application/wasm` e CSP com `connect-src 'self'` e `'wasm-unsafe-eval'` em `/painel/*` | `curl -I https://rotaguard.acexpartners.com.br/painel/mediapipe/wasm/vision_wasm_internal.wasm` |
| DEMO-11 | Sem WebGL2 (ou GPU falhando): cai para CPU e mostra "CPU" | Playwright com `--disable-gpu` |
| DEMO-12 | A tela mostra fps, ms por inferência e o delegate; abaixo de 24 fps avisa que a duração da piscada fica imprecisa | manual e Playwright |
| DEMO-13 | Olhos fechados 1 s na frente da câmera: "fechados 1 s (microssono)" aparece em até 1,3 s; 3 s: "sono" | manual, com cronômetro, nos aparelhos do pitch |
| DEMO-14 | Pessoa parada sob luz estável, contra oxímetro de dedo: erro ≤ 5 bpm em 3 de 3 medidas de 30 s; com a cabeça mexendo, aparece "sinal fraco" ou "medindo" em vez de número errado | manual, com o oxímetro anotado (validação real, não sintética) |
| DEMO-15 | **Nenhuma requisição para fora da origem** durante 90 s de demo e depois de parar a câmera (o envio do MediaPipe dispara a cada 60 s e no `close()`); a CSP aparece bloqueando `odml.pa.googleapis.com` | Playwright: `page.on("request")` com host ≠ origem → falha; na web e no WebView2 |
| DEMO-16 | iPhone (Safari) e Android (Chrome): vídeo aparece sem tela cheia nem tela preta, e a malha acompanha | manual, com o modelo e a versão do iOS/Android anotados na spec |
| DEMO-17 | Painel instalado (pywebview 6.2.1): a câmera pede permissão e funciona; com o script da caixa aberto, aparece a mensagem de câmera ocupada | manual no Windows |
| DEMO-18 | Esconder a aba ou trocar de app no celular para a câmera; voltar mostra "Ligar a câmera" de novo | manual |

---

## Dependências atrasadas (só aviso; major não foi mexida)

`npm view` em 19/10/2026: `next` latest **16.4.2** (o site usa 16.3.4 e o painel 16.3.5); `react` latest **19.3.1**
(os dois usam 19.3.0). Ambas são minor ou patch, não major. O `typescript` latest é 7.0.2, mas o erro 30 da vault manda
manter o 6.0.3 (o `next build` quebra com o TS 7).

## Fontes

- npm: `npm view @mediapipe/tasks-vision version|dist-tags|time|versions`, `npm pack @mediapipe/tasks-vision@1.1.1` e `@1.0.1` (código lido: `vision.d.ts`, `vision_bundle.mjs`, `wasm/*.js`, README "Privacy Notice").
- MediaPipe: [guia do Face Landmarker](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker), [guia web](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker/web_js), [releases](https://github.com/google-ai-edge/mediapipe/releases), [ToS](https://developers.google.com/edge/mediapipe/legal/tos), [v1.0.0 (espelho)](https://newreleases.io/project/github/google-ai-edge/mediapipe/release/v1.0.0).
- Model cards (PDF): [Face Mesh V2](https://storage.googleapis.com/mediapipe-assets/Model%20Card%20MediaPipe%20Face%20Mesh%20V2.pdf), [Blendshape V2](https://storage.googleapis.com/mediapipe-assets/Model%20Card%20Blendshape%20V2.pdf), [BlazeFace short range](https://storage.googleapis.com/mediapipe-assets/MediaPipe%20BlazeFace%20Model%20Card%20(Short%20Range).pdf).
- Modelo canônico: [canonical_face_model.obj](https://raw.githubusercontent.com/google-ai-edge/mediapipe/master/mediapipe/modules/face_geometry/data/canonical_face_model.obj); modelo: [face_landmarker.task (latest)](https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task).
- rPPG: [iPhys toolbox (POS)](https://arxiv.org/pdf/1901.04366), [R2I-rPPG](https://arxiv.org/html/2410.15851v2), [Kossack et al., ICCVW 2021](https://openaccess.thecvf.com/content/ICCV2021W/V4V/papers/Kossack_Automatic_Region-Based_Heart_Rate_Measurement_Using_Remote_Photoplethysmography_ICCVW_2021_paper.pdf), [cheat sheet de índices (com erro nas bochechas)](https://hackernoon.com/mediapipe-face-mesh-landmark-indices-cheat-sheet).
- Navegador: [MDN getUserMedia](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia), [MDN requestVideoFrameCallback](https://developer.mozilla.org/en-US/docs/Web/API/HTMLVideoElement/requestVideoFrameCallback), [WebKit 179363](https://bugs.webkit.org/show_bug.cgi?id=179363), [WebKit 230698](https://bugs.webkit.org/show_bug.cgi?id=230698), [WebKit 230922](https://bugs.webkit.org/show_bug.cgi?id=230922), [Apple Forums 92713](https://developer.apple.com/forums/thread/92713), [Valley of Code](https://thevalleyofcode.com/lesson/media-webrtc/webrtc-ios-black-box/).
- Alternativas: [Human](https://github.com/vladmandic/human); benchmark de terceiro: [micro-facemesh](https://cdn.jsdelivr.net/npm/@svenflow/micro-facemesh@0.1.2/README.md).
- Next.js 16 (docs locais): `painel/app/node_modules/next/dist/docs/01-app/02-guides/static-exports.md`, `lazy-loading.md`, `content-security-policy.md`, `03-api-reference/05-config/01-next-config-js/headers.md`.
- Repositório: `caixa/vision/{face,eyes,calibration,drowsiness,phone,risk}.py`, `docs/specs/021,022,024,025`, `docs/produto/PRD.md`, `painel/app/**`, `.venv/Lib/site-packages/webview/platforms/edgechromium.py`.
