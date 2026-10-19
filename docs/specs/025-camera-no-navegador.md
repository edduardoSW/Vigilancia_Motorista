# Spec 025 · Teste com a câmera do aparelho dentro do painel

| Campo | Valor |
|---|---|
| Status | implementada em 19/10/2026 (106 testes do painel, lint e builds; Edge sem janela com câmera falsa: 72 bpm medido, zero pedidos para fora); não testada com pessoa real, celular de verdade nem oxímetro |
| PRD | RF-62, RF-16, RF-17, RNF-15 |
| Pedido | "quero que na face tenha bolinhas para captação de tudo"; "algo muito completo para eu e os integrantes da minha equipe usarem na entrega de pitch" (19/10/2026) |
| Specs irmãs | 022 (cardio e pontos no Python), 024 (painel na web), 018 (Ao vivo com o script local) |
| Código | `painel/app/src/components/live/camera-*.ts(x)` (soltos em `live/`: subpasta quebra o teste SCR-13), `painel/app/src/app/ao-vivo/page.tsx`, `painel/app/src/app/layout.tsx` (CSP), `painel/app/public/mediapipe/` (copiado no build, fora do git) |
| Testes | `painel/app/scripts/testes/camera-*.test.mjs` (CAM-01 a CAM-11), `tests/test_painel_desktop.py` (CAM-12) |
| Pesquisa | relatório do agente de 19/10/2026 (`@mediapipe/tasks-vision` no navegador) |

## Contexto

Na VPS não há script local para o painel reconhecer. Para a equipe mostrar a detecção ao vivo em qualquer notebook ou
celular, a tela **Ao vivo** ganha um teste que roda no próprio navegador.

## Decisões

1. **`@mediapipe/tasks-vision` 1.1.1** (Apache 2.0, última estável no npm em 19/10/2026; a `nightly` 1.2.0-rc fica de
   fora). WASM com SIMD e o mesmo `face_landmarker.task` da caixa (SHA-256 igual ao `float16/latest` do Google) ficam
   em `painel/app/public/mediapipe/`, copiados no build e servidos pelo próprio painel: sem CDN, funciona no painel
   instalado sem internet. O caminho vem do `basePath` (na VPS, `/painel/mediapipe/`).
   - **Telemetria bloqueada:** o pacote 1.1.x envia métricas de uso para `odml.pa.googleapis.com` (sem imagens). Para
     "nada sai do aparelho" ser verdade, a CSP tem `connect-src 'self'`: no Caddy para `/painel` e numa `<meta>` do
     `layout.tsx` para o painel instalado. Também `'wasm-unsafe-eval'` e `Permissions-Policy camera=(self)`.
2. **Mesmas regras do Python, com o nome dizendo que é o teste no navegador:** abertura do olho (EAR e `eyeBlink`), olhos
   fechados por 1 s e 3 s, PERCLOS de 60 s, piscadas por minuto, bocejo (`jawOpen`), inclinação da cabeça pela matriz
   facial e cabeceio. O nome na tela é "teste no navegador", e a caixa continua sendo a referência.
3. **Malha** em canvas por cima do vídeo espelhado: 478 pontos, olhos, íris, boca e ROIs do pulso em destaque.
4. **Cardio** com POS em TypeScript (mesmos parâmetros da spec 022), onda ao vivo, bpm, confiança e "sinal fraco".
5. **Nada sai do aparelho:** nenhum quadro, ponto ou número vai para o servidor. Botão de parar câmera sempre visível.
   Aviso: "estimativa pela câmera, não é medida médica".
6. **Funciona nos dois lugares:** painel web (HTTPS) e painel instalado (WebView2 permite câmera).
7. A aba do script local (spec 018) continua no painel instalado; na web aparece só o teste do navegador.

## Critérios de aceite

| ID | Critério |
|---|---|
| CAM-01 | POS em TS com série sintética de 72 bpm: erro ≤ 2 bpm depois de 10 s |
| CAM-02 | Só ruído: `sinal_fraco` sem número |
| CAM-03 | EAR de seis pontos igual ao do Python (`caixa/vision/face.py`) em três casos |
| CAM-04 | Série de abertura com olho fechado por 1,2 s gera um evento de microssono; 0,3 s conta como piscada |
| CAM-05 | PERCLOS de 60 s certo numa série sintética com fechamentos de 300 ms ou mais (20% fechado → 0,20 ± 0,01); fechamento abaixo de 250 ms não entra, como no Python |
| CAM-06 | Bocejo: boca aberta acima do limiar por mais de 2,0 s conta um bocejo (mesmo valor do Python) |
| CAM-07 | Nenhum endereço externo nos arquivos do teste (os modelos vêm de `/mediapipe/` do próprio painel) |
| CAM-08 | Sem permissão de câmera: mensagem clara e botão para tentar de novo, sem quebrar a tela |
| CAM-09 | Parar desliga todas as trilhas da câmera (`track.stop()`) |
| CAM-10 | Build, lint e testes do painel sem erro |
| CAM-11 | A página do painel declara CSP com `connect-src 'self'` (nenhum envio para fora, nem a telemetria do MediaPipe) |
| CAM-12 | Painel instalado: `.wasm` servido como `application/wasm` e CSP da janela com `'wasm-unsafe-eval'`, `media-src` e `worker-src` em `blob:`, sem `'unsafe-eval'` |

## Notas da implementação (19/10/2026)

- O cardio em TypeScript (`camera-rppg.ts`) é um porte fiel do `CardioMonitor` do Python (spec 022), sem infravermelho,
  respiração e variabilidade: mesmas ROIs (`esq`/`dir` = lado da imagem), aquecimento de 15 s, ≥ 15 quadros/s,
  Tarvainen λ = 300, ±0,2 Hz, limiar 0 dB. A paridade é conferida em teste com as mesmas séries sintéticas e o gabarito
  calculado pelo próprio Python.
- Arquivos soltos em `live/` com prefixo `camera-` (subpasta quebrava o SCR-13).
- No notebook sem janela: 12 a 19 quadros/s pela placa de vídeo (o processador fez 71 a 94 ms por quadro); abaixo de
  15 quadros/s o pulso fica em "sinal fraco", pela regra do Python.
- Três capturas de alerta são simuladas e o nome diz isso: pálpebra pintada numa foto não engana o MediaPipe.
- O painel instalado bloqueava o WebAssembly (CSP sem `'wasm-unsafe-eval'` e `.wasm` sem tipo): corrigido em
  `painel/desktop/rotaguard_painel.py` (CAM-12).
