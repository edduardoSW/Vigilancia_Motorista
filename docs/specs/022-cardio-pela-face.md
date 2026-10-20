# Spec 022 · Frequência cardíaca pela face (rPPG) e malha de pontos

| Campo | Valor |
|---|---|
| Status | implementada em 19/10/2026 (`tests/test_cardio.py`: 17 verificações, CAR-11 e CAR-13 com foto real e o modelo do MediaPipe); precisão real com webcam e IR ainda não medida |
| PRD | RF-16, RF-17, RNF-05, RNF-16 |
| Pedido | "quero colocar mais coisas referentes a cardio pois tem como saber as frequencias cardiacas com as faces e eu quero que na face tenha bolinhas para captação de tudo"; "eu ainda não tenho o raspberry pi e etc então é necessário que deixe o script mais completo e bonito possível" (19/10/2026) |
| Muda | Seção 5 do PRD: a "pulseira de frequência cardíaca" continua fora; a frequência cardíaca **pela câmera** entra |
| Specs irmãs | 009 e 011 (sinais de sono), 023 (tela do app de teste), 025 (câmera no navegador) |
| Código | `caixa/vision/cardio.py`, `caixa/vision/face.py`, `caixa/vision/engine.py` |
| Testes | `tests/test_cardio.py` (CAR-01 a CAR-14) |
| Pesquisa | relatório dos agentes de 19/10/2026, resumido na nota da vault `12 - Cardio pela face (rPPG)` |

## Contexto

- O Face Landmarker do MediaPipe já entrega 478 pontos por quadro (`caixa/vision/face.py`), mas o código só guarda os
  pontos dos olhos (`eye_points`).
- rPPG (fotopletismografia remota): a cada batimento a pele muda de cor de forma mínima. Medindo a cor média da testa e
  das bochechas por alguns segundos e filtrando a faixa de 0,7 a 3 Hz, sai a frequência cardíaca.
- Com câmera infravermelha (caixa, NoIR 940 nm) há um canal só: funciona pior e com menos amplitude. Com webcam RGB
  (app de teste) o algoritmo POS é o padrão da literatura sem treino.

## Decisões

1. **Pontos do rosto disponíveis para todos:** `FaceMetrics.landmarks` (478 × 2, em pixels) passa a existir quando o
   MediaPipe acha o rosto. No modo YuNet fica `None`.
2. **Módulo novo `vision/cardio.py`, só numpy** (sem scipy, para o pacote não crescer):
   - ROIs: testa e as duas bochechas, polígonos por índices fixos de pontos, longe de olhos, boca e sobrancelhas.
   - Por quadro: média de cada canal em cada ROI (recorte do retângulo envolvente + máscara do polígono), com
     timestamp. Custo alvo: menos de 2 ms por quadro em 640×480.
   - Reamostragem para 30 Hz pelo timestamp (a taxa de quadros real oscila).
   - **POS** (Wang et al., 2017) com janela de 1,6 s somada por sobreposição; **GREEN** quando o quadro é
     infravermelho/monocromático.
   - Remoção de tendência, passa-faixa 0,7 a 3,0 Hz (42 a 180 bpm), espectro numa janela de 10 s (mínimo 6 s), pico com
     interpolação parabólica, atualização a cada 1 s e suavização por mediana das últimas leituras.
   - **SNR** (de Haan): energia em ±0,2 Hz do pico e do 2º harmônico contra o resto da banda (com ±0,1 Hz, numa janela
     de 10 s, uma senoide limpa dá só 9,3 dB; com ±0,2 Hz, 29,1 dB: conferido na pesquisa de 19/10). Abaixo do limiar,
     não mostra número ("sinal fraco").
   - **Espectro:** Welch com janela de Hann e zero-padding até 2048 pontos. **ROIs** (modelo canônico do MediaPipe):
     testa 69, 108, 151, 337, 299, 296, 336, 9, 107, 66; bochecha esquerda 117, 118, 101, 36, 205, 187, 123; bochecha
     direita 346, 347, 330, 266, 425, 411, 352.
   - **Movimento**: deslocamento médio dos pontos acima do limiar pausa a medida ("parado para medir").
   - **Respiração** (experimental): banda 0,1 a 0,5 Hz do sinal de cor somado ao movimento vertical do nariz, janela de
     30 s.
   - **Variabilidade (RMSSD)** experimental: só com taxa ≥ 25 quadros/s e SNR alto, por detecção de picos na onda.
3. **Saída** `CardioReading`: `estado` (`sem_rosto`, `medindo`, `pronto`, `sinal_fraco`, `movimento`), `bpm`,
   `confianca` (0 a 1), `snr_db`, `respiracao_rpm`, `rmssd_ms`, `progresso` (0 a 1 até a primeira leitura), `onda`
   (últimos 6 s normalizados, para o gráfico), `historico_bpm` (últimos 120 valores), `canal` (`rgb` ou `ir`),
   `rois` (polígonos em pixels, para desenhar).
4. **Fora do risco por enquanto:** a frequência cardíaca não muda o nível de risco nem gera alarme até ser validada com
   gravações e um oxímetro de referência. Aparece na tela como informação.
5. **Privacidade (LGPD art. 11, dado de saúde):** nada de cardio vai para evento, fila, servidor ou registro. As chaves
   ficam em `PRIVATE_KEYS`. Texto na tela: "estimativa pela câmera, não é medida médica".
6. **Ligado por padrão no app de teste, desligado na caixa** até a validação (`--cardio` / `DRIVESAFE_CARDIO`).

## Cenários

- **Dado** um rosto parado sob luz estável **quando** passam 10 s **então** aparece um bpm com confiança.
- **Dado** o motorista virando a cabeça **quando** o movimento passa do limiar **então** o estado vira `movimento` e o
  último bpm bom fica esmaecido, sem número novo.
- **Dado** um quadro infravermelho **quando** o cardio roda **então** usa um canal só e marca `canal = "ir"`.

## Critérios de aceite

| ID | Critério |
|---|---|
| CAR-01 | Série sintética RGB de 72 bpm (pulso em G maior que em R e B) + ruído branco: erro ≤ 2 bpm depois do aquecimento de 15 s |
| CAR-02 | Mesma série a 55, 90 e 140 bpm: erro ≤ 3 bpm em cada |
| CAR-03 | Taxa irregular (quadros entre 22 e 34 ms): erro ≤ 3 bpm |
| CAR-04 | Só ruído: estado `sinal_fraco` e `bpm` `None` |
| CAR-05 | Durante o aquecimento (15 s): estado `medindo` e `progresso` crescente entre 0 e 1 (a estimativa interna começa aos 6 s) |
| CAR-06 | Variação lenta de iluminação (rampa de 30% em 10 s) não muda o bpm em mais de 3 bpm |
| CAR-07 | Pontos andando mais que o limiar: estado `movimento` |
| CAR-08 | Quadro monocromático (três canais iguais): `canal = "ir"` e ainda acha 72 bpm com SNR moderado |
| CAR-09 | Respiração sintética de 15 rpm somada ao sinal: `respiracao_rpm` entre 13 e 17 |
| CAR-10 | Sem rosto por mais de 2 s: estado `sem_rosto` e janelas zeradas |
| CAR-11 | Média das ROIs a partir de quadro e pontos reais: polígono da testa acima das sobrancelhas e dentro do rosto |
| CAR-12 | Nenhuma chave de cardio aparece em evento (`_decorate`) |
| CAR-13 | `FaceMetrics.landmarks` com 478 pontos quando há rosto (teste com MediaPipe, pulado se o modelo não carregar) |
| CAR-14 | Custo médio do `update` < 3 ms por quadro 640×480 nesta máquina |

## Fora de escopo

- Pressão arterial, SpO2, glicose, "estresse" ou qualquer diagnóstico.
- Usar a frequência cardíaca no nível de risco (depende de validação).

## Notas da implementação (19/10/2026)

- **Aquecimento de 15 s** antes do primeiro número e só com ≥ 15 quadros/s efetivos (pesquisa: a 10 quadros/s o erro
  médio foi 5,4 bpm e o máximo 36).
- **Tarvainen (λ = 300) por Cholesky em banda**, O(N): a inversa densa 300×300 levava 416 ms; o resultado é igual ao da
  fórmula densa (conferido em teste). **POS por somas acumuladas**, igual ao laço do Algoritmo 1 (conferido em teste).
- **Limiares** calibrados só com ruído sintético (hipótese até haver gravação): SNR 0 dB (ruído puro teve máximo de
  −1,8 dB em 3.000 janelas), movimento 0,10 (em distâncias entre os cantos dos olhos, em 0,5 s), respiração 12 dB.
- **RMSSD** só com SNR ≥ 10 dB e banda f0 ± 0,5 Hz (com 0,7–3 Hz o piso de um pulso regular dava 60 a 155 ms).
- **Nomes das bochechas**: `esq` e `dir` são o lado da **imagem** (117 é a bochecha direita do motorista).
- **Resumo local do app de teste** pode ter média, mínimo e máximo do bpm: fica só no computador da pessoa e nunca vai
  para evento, fila, central ou registro da viagem (RNF-16 e spec 026).
- **Modo YuNet** não tem os 478 pontos: o cardio fica indisponível e a tela diz isso (não "sem rosto").

## Revisão de 20/10/2026 (pedido: "fala que não consegue captar muito por causa da luz isso não faz sentido e quando não consegue simplesmente para de funcionar")

Causa: o portão de 15 quadros/s. Num notebook a ~12 quadros/s o código nunca mostrava número (no vídeo de teste, 90% do
tempo em "sinal fraco") e a tela pedia luz sem medir luz.

| ID | Critério |
|---|---|
| CAR-15 | Sinal bom, 4 s de ruído, bom de novo: o número volta em ≤ 5 s (medido: 3,0 s; antes 11 s) |
| CAR-16 | `motivo` medido: `pouca_luz` (luminância Y < 50), `luz_estourada` (> 25% saturado), `mexendo`, `camera_lenta` (< 10 quadros/s), `sinal_fraco`; `None` quando nada foi medido |
| CAR-17 | `progresso` e `segundos_para_medida` também na retomada depois de perder o sinal |
| CAR-18 | A partir de 10 quadros/s há número (janela de 12 s e confiança menor entre 10 e 15) |
| CAR-19 | POS, CHROM e GREEN: o vencedor precisa concordar com o POS ou com as últimas janelas |
| CAR-20 | Pico na borda da banda (a menos de 0,05 Hz de 0,7 ou 3,0 Hz) nunca vira número (o "42 bpm" da captura) |
| CAR-21 | Confiança abaixo de 0,40 não publica número; abaixo de 60 bpm o SNR exigido sobe 2 dB (ruído 1/f dava 46 a 55 bpm falsos) |
| CAR-22 | Ruído puro nunca vira número (máximo de −2,1 dB em 408 janelas) |

Resultado no vídeo de teste (pulso sintético de 72 bpm): a 12 quadros/s, de 0% para 100% do tempo com número, erro médio
de 0,05 bpm; a 8 quadros/s, sem número e com o motivo `camera_lenta` medido. Ferramenta:
`ferramentas/diagnosticar_cardio.py <vídeo> --bpm-real 72`. Os limiares de luz (50 e 25%) são hipótese até a webcam real.
