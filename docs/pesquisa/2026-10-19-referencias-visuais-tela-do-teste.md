# Referências visuais e guia de tela: RotaGuard Teste (spec 023)

Data: 19/10/2026. Pedido: rodada de referências antes da tela (regra 1b) e guia visual. Mudança de foco pedida pelo
Matheus no meio da pesquisa: **o relatório serve ao conteúdo do script** (o que `caixa/vision/*` mede). A tela Ao vivo
do painel (spec 025) ficou só como nota curta no fim (seção 8).

O que li antes de escrever:

- Specs `docs/specs/023-nova-tela-do-app-de-teste.md` e `025-camera-no-navegador.md`; a pesquisa
  `docs/pesquisa/2026-10-19-camera-no-navegador.md` (seção 2, "bolinhas") e `2026-10-19-pulso-pela-camera-rppg.md`.
- Visual atual: `painel/app/src/app/globals.css` (tokens claro e escuro), capturas `01-inicio`, `03-relatorio`,
  `04-momento-video`, `17-escuro-inicio`, `21-escuro-momento` de `docs/painel/capturas-2026-09-15-parte-2/` e
  `docs/site/prints/reformulacao-2026-09-11/computador-primeira-tela.png` (abri as imagens).
- Marcação que já existe da tela nova: `caixa/tela_teste/web/index.html` (ids citados abaixo são dela).
- Código do que o script mede: `vision/drowsiness.py`, `risk.py`, `driver_monitor.py`, `phone.py`, `face_touch.py`,
  `engine.py`, `cardio.py`, `face.py`, `eyes.py`, `calibration.py`, `context.py`, `visibility.py`, `activation.py`,
  `tela_teste/estado.py`, `sessao.py`, `resumo.py`, `app_teste.py`.
- Vault: `meu-estilo-de-sites.md`, `referencias-de-design.md`, `regras-de-componentes.md`, `diferenciacao-visual.md`,
  `erros-que-a-ia-comete.md` (erros 8 a 14, 33 a 38, 48 a 51, 75, 123, 124, 127, 168, 169, 177).

O painel usa Manrope (texto) e Space Grotesk (títulos) (`painel/app/src/app/layout.tsx:2-11`); a spec 023 manda fonte do
sistema porque o app de teste roda sem internet (TEL-14). O modo escuro do painel já é um neutro esverdeado em camadas
(`globals.css:49-79`), e é dele que este guia parte.

---

## 1. Referências escolhidas (5)

Busca feita de verdade em 19/10/2026 (WebSearch e WebFetch). Quatro categorias: instrumentação fora do web design,
monitor médico, galeria, registry de componentes e movimento. Onde a página não abriu para leitura automática, está dito.

| # | Categoria | Referência | Princípio a aproveitar | Como cruza com o estilo do Matheus | Clichê que ela carrega (descartar) |
|---|---|---|---|---|---|
| R1 | Instrumentação (fora do web design) | **ISA-101, IHM de alto desempenho** ("cinza é bom"). Guia aberto: https://open-exam-prep.com/study-guides/isa-cap/system-design-hmi-alarms-enterprise/hmi-design-isa101 · artigo "Going Gray": https://control.com/technical-articles/going-gray/ (403 para robô, achado pela busca) · Airbus "dark cockpit" (ICAO/Airbus, via busca): https://www2023.icao.int/ESAF/Documents/meetings/2017/AFI%20FOSAS%202017/Day%201%20Docs/Day_1_2_Airbuspihlo.pdf | Cor só no que está fora do normal; o normal fica neutro. Barra com **faixa normal sombreada + marcador do valor + marcas dos limites**, em vez de número solto. **Mini-tendência ao lado do número.** Prioridade codificada duas vezes (cor e forma). Piscar só para alarme ainda não reconhecido. | É a mesma regra do "um acento só": neutros esverdeados do painel em tudo, e cor apenas em atenção, alto e crítico. Dá a resposta para "risco sem alarmismo". | Estética SCADA (cinza bege, botões 3D). Fica a regra, não a cara. |
| R2 | Monitor médico | **Masimo Signal IQ e onda pleth** (via busca; o PDF da Masimo redireciona e não abriu): https://professional.masimo.co.uk/siteassets/uk/documents/pdf/clinical-evidence/whitepapers/lab5318b_whitepapers_signal_iq.pdf · ficha Rad-5: https://medaval.ie/docs/specs/Masimo-Rad-5-Specs.pdf · treino Alaris: https://nursing.lsuhsc.edu/AlarisTraining/spo2/t1/p05.htm | A **confiança fica desenhada embaixo da onda** (barra cuja altura é a confiança) e vira mensagem quando cai ("Low SIQ"). Oxímetros só mostram o número quando a qualidade passa do mínimo. Número grande à direita, onda à esquerda, na mesma linha. | É exatamente o contrato do `cardio.py` (estados `medindo`, `pronto`, `sinal_fraco`, `movimento`, número só com `pronto`). Traz a leitura de "monitor" sem copiar o equipamento. | Verde fósforo em fundo preto, coração vermelho piscando, grade quadriculada de ECG. Descartar tudo isso: aqui é estimativa, não exame. |
| R3 | Galeria | **Dribbble, monitores de sinais vitais** (achados pela busca; o Dribbble devolve página vazia, HTTP 202, para leitura automática, conferido em 19/10; abrir no navegador antes de usar): https://dribbble.com/shots/15865788--2021-Vital-signs-monitor-UI-medical-device · https://dribbble.com/tags/patient_monitoring · https://dribbble.com/search/monitoring-system (traz "Next-Gen Dashboard: Driver Monitoring System", Artonest) | Conferir olhando: o ritmo "uma linha por grandeza" (rótulo, onda ou barra, número) e a densidade. Não descrevo as imagens porque não consegui abri-las. | Serve de contraste: mostra o que o RotaGuard **não** quer ser (painel de carro de ficção, néon). A tela fica no ritmo das linhas, com a calma do painel. | Néon azul, glow, HUD de ficção científica com cantos chanfrados e fonte "tech". |
| R4 | Registry de componentes | **Motion Primitives, Sliding Number** (aberto): https://motion-primitives.com/docs/sliding-number · base dele, **NumberFlow** (aberto): https://number-flow.barvian.me/ | Contador que **rola só o dígito que mudou**, com **números tabulares** ("todos os números com a mesma largura, os dígitos não pulam") e `respectMotionPreference` ligado por padrão. Direção do rolo segue a tendência. | Movimento "com intenção" de `diferenciacao-visual.md` §3.5: anima só contador discreto (piscadas, eventos, bocejos), nunca valor contínuo. A tela de teste não tem build (TEL-14), então entra o **comportamento** em CSS próprio, não a biblioteca (erro 37). | Contador que sobe de 0 até o valor ao aparecer (efeito de landing). |
| R5 | Movimento | **Apple Face ID, cadastro do rosto** (aberto): https://support.apple.com/en-us/108411 ("Position your face inside the frame and gently move your head to complete the circle") · **Codrops, máscara 3D com MediaPipe** (achado pela busca, 403 para robô): https://tympanus.net/codrops/2026/09/06/building-a-real-time-3d-face-mask-with-mediapipe-threlte-and-three-js/ | Progresso desenhado **onde o olho já está** (em volta do rosto), com uma instrução curta, e a etapa seguinte anunciada. No Codrops: a malha precisa casar com o vídeo espelhado e recortado, senão os pontos "escorregam". | Calibração e aquecimento do cardio viram progresso no próprio vídeo e no anel do cardio (`cardio-anel` já existe), com texto em português simples. | Anel com brilho e partículas. Aqui é traço fino e texto. |

Fontes de apoio (dashboards escuros de alto nível), usadas para a escala de cor e a tipografia:
- Linear, redesenho (aberto): https://linear.app/now/how-we-redesigned-the-linear-ui — tirou cor do "chrome", texto
  neutro mais forte, tema gerado de 3 variáveis (base, acento, contraste) em LCH.
- Vercel Geist, cores (aberto): https://vercel.com/geist/colors — escala com papel por passo: 100 a 300 fundo, 400 a 600
  borda, 700 e 800 fundo forte, 900 e 1000 texto.
- Grafana, limiares (aberto): https://grafana.com/docs/grafana/latest/panels-visualizations/configure-thresholds/ —
  limiar desenhado como linha, linha tracejada ou região, na própria série.
- Okabe e Ito, cor para daltônicos (via busca): https://jfly.uni-koeln.de/color/

---

## 2. Cada medida do script e como mostrar

Legenda da coluna "/estado": **sim** = já sai em `tela_teste/estado.py:132-204`; **não** = o script calcula e a tela
não recebe.

### 2.1 Mostrar (já chega na tela)

| Medida (código) | /estado | Como mostrar | Estados vazios |
|---|---|---|---|
| Nível de risco 0 a 3 e motivos (`risk.py:37-45`, `130`) | sim | Selo no canto do vídeo (`chip-risco`) com **3 segmentos** (0 a 3 cheios) + palavra. No cartão (`card-risk`): régua de 4 passos Normal, Atenção, Alto, Crítico, com o passo atual marcado; motivos em até 3 frases (`texto_motivo`). | Antes da calibração terminar: "Só o microssono vale durante a calibração" (é o que `drowsiness.py:452-453` faz). |
| Alarme (`risk.alarm`) | sim | Nada novo na tela além do nível; o som já toca. Se o som estiver desligado (S), o selo ganha "som desligado" pequeno. | — |
| Rosto encontrado (`face_found`) | sim | Mensagem no centro do vídeo (`sem-rosto`) depois de 1 s sem rosto. Aos 10 s vira evento (`FACE_MISSING_EVENT_S`, `drowsiness.py:67`). | "Procurando o rosto. Centralize o rosto e chegue mais perto." |
| Olhos visíveis e motivo (`visibility.py:28-32`) | sim | Aviso no canto direito do vídeo (`chip-aviso`): "Olhos não visíveis (óculos escuros?)". Os números de olho ficam em "pausa", não em zero. | — |
| Infravermelho (`face.py:106`) | sim | Etiqueta "IR" ao lado do nome da câmera na barra de cima. | — |
| Calibração (`drowsiness.py:90-91`, `calibration.py:72-73`) | sim (só a fração) | Faixa de 4 px na borda de baixo do vídeo (`calibracao-barra`) + linha de texto acima: "Calibrando · 38 s de 60 s · olhe para a tela e pisque normalmente". A calibração rápida é de 60 a 120 s (`app_teste.py:79-81`). | Terminou: aviso curto "Calibração concluída" ou, se o evento `calibracao_suspeita` vier, "Calibração suspeita: pode já haver sinais de sono. Recalibre descansado (C)". |
| Abertura do olho (`openness`) | sim | Número grande em % (`abertura`) + gráfico de 60 s (`grafico-abertura`, série `series.abertura` de `sessao.py:289-302`) com **linha tracejada em 20%**: abaixo dela conta como "olho fechado" no PERCLOS (`P80_OPENNESS = 0.20`, `eyes.py:21`). As piscadas aparecem como vales. | Sem medida: "--" e o motivo (ver `frame_source` em 2.2). |
| Fechado há (`closed_for`) | sim | Só aparece quando > 0, com 1 casa: "Fechado há 1,4 s". Embaixo, uma régua com marcas em **1 s (microssono), 3 s (sono) e 6 s (sem resposta)** (`drowsiness.py:28-30`): o pitch vê o limiar chegando. | Escondido quando 0. |
| PERCLOS 60 s (`perclos_60s`) | sim | Barra horizontal com faixa normal sombreada (0 a 8%), marca em 12% (`ALERT_PERCLOS`, `drowsiness.py:34`) e o valor como marcador (R1). | `None` até ter 30 s válidos (`PERCLOS_MIN_VALID_FRACTION = 0.5`): "juntando 60 s". |
| Piscadas no último minuto e por minuto (5 min) | sim | Contador com rolo de dígito (R4) + "por min" com 1 casa. | `piscadas_por_min` é `None` até 60 s válidos: "precisa de 1 min". |
| Duração mediana da piscada | sim | "180 ms" + comparação com a calibração quando houver base (ver 2.2). | Só com 24 qps e 15 piscadas (`drowsiness.py:46-47`, `427`): "precisa de 15 piscadas (faltam 6)". |
| Fechamentos longos em 5 min | sim | Contador simples; 1 = atenção, 3 = alto (`drowsiness.py:35`, `481-485`): mostrar "1 de 3" com os 3 pontinhos. | 0. |
| Cabeça: inclinação, giro, rolagem (`pitch`, `yaw`, `roll`) | sim | Indicador de atitude (`horizonte`): linha do horizonte girada pela rolagem e deslocada pela inclinação; marcador de giro numa escala no topo. Números com sinal e texto: "+12° (cabeça baixa)". Pitch positivo = cabeça baixa (`drowsiness.py:152`). Marca em 15° (cabeceio, `NOD_MIN_DEG`). | Sem rosto: horizonte em grafite, sem números. |
| Cabeceios em 10 min | sim | Contador; 2 = atenção, 3 = alto (`drowsiness.py:36`, `43`). | 0. |
| Boca: abertura (`jaw_open`) e bocejos em 10 min | sim | Barra (`boca-barra`) com marca no limiar do bocejo, `max(0,45; base + 0,30)` (`drowsiness.py:386-388`). Acima do limiar, a barra mostra o tempo até contar: "bocejo? 1,2 s de 2,0 s" (`YAWN_MIN_S`). Bocejo é sinal complementar, nunca crítico: cor neutra sempre. | — |
| Coração (todo o `CardioReading`, `cardio.py:123-136`) | sim | Ver 3.5. | Ver 3.5. |
| Celular: estado, duração, confiança, mãos (`phone.py:97-108`) | sim | Linha de estado (`celular-estado`) + **tempo até o alerta**: olhando 2 s, no ouvido 3 s, na mão 3 s (`phone.py:78-80`) como barrinha que enche. No vídeo: cantos em laranja (já desenhados, `driver_monitor.py:79-84`) com a confiança ao lado, fora da caixa: "celular 0,78". | "Nenhum celular" em grafite. Desligado nas opções: "Desligado nas opções". |
| Gestos: esfregando os olhos, mão no rosto, contagens em 10 min (`face_touch.py:73-80`) | sim | Gesto em andamento como aviso no vídeo; contagens no cartão. Olhos esfregados 3 vezes em 10 min contam como sinal leve (`risk.py:26`, `76`); mão no rosto não pesa: dizer isso em texto pequeno ("contado, não pesa no risco"). | 0. |
| Olhar (`gaze_x`, `gaze_y`, em meias larguras do olho, `face.py:95-97`) | sim | Ponto num retângulo que representa o olho (`olhar-ponto`), com a região "olhando para baixo" marcada (`LOOK_DOWN_GAZE = 0.25`, `phone.py:74`). Texto: "Olhando para a frente / para baixo / para o lado". | Sem íris: "--". |
| Desempenho: qps, latência média e p95, tempo da malha | sim | Linha discreta no rodapé (`card-perf`). Qps abaixo de 24 fica em atenção, com o porquê: "abaixo de 24 qps a duração da piscada não vale" (`drowsiness.py:8`, `46`). | — |
| Eventos (linha do tempo, `resumo.py:94-110`) | sim | Ver 3.9. | "Nenhum evento ainda. Para ver um alerta, feche os olhos por 2 segundos" (já está no HTML). |
| Resumo (`resumo.py:126-163`) | sim, na fase `resumo` | Ver 3.10. | — |

### 2.2 O script calcula e a tela não mostra hoje

Ordem de importância para o pitch e para quem testa. Para cada um, o que precisa entrar no `/estado`.

1. **PERCLOS de 3 min** (`drowsiness.py:438-439`). É o PERCLOS que **decide** o risco (`drowsiness.py:474-479`); a tela
   só mostra o de 60 s. Mostrar o de 3 min como principal, com a marca de 12%, e o de 60 s como "agora". Expor
   `window["perclos_3min"]` em `olhos`.
2. **"Comparado com você"**: `duracao_base_ms`, `razao_duracao`, `perclos_base`, `avr_fechamento_ms`,
   `avr_fechamento_base_ms`, `razao_avr_fechamento`, `amplitude_mediana` (`drowsiness.py:428-447`, `460`, `470`).
   É o diferencial do produto (linha de base individual) e hoje não aparece. Linha pequena sob cada número:
   "+18% que na sua calibração" com a marca de +15% (atenção) e +25% (alto) (`drowsiness.py:33`, `39`).
3. **Por que a abertura sumiu** (`Assessment.frame_source`, `drowsiness.py:94`; valores em `eyes.py:146-186`):
   `rosto_virado` (giro acima de 30°), `rosto_pequeno` (olhos a menos de 30 px), `sem_referencia`, ou os sinais usados
   (`ear+pontuacao+classificador`). Mostrar o motivo no lugar do número ("Rosto virado: abertura em pausa") e, no modo
   detalhado, quais sinais concordaram.
4. **Mão tapando o olho ou o rosto** (`FaceTouchAssessment.eye_covered`, `face_hidden`, `face_touch.py:76-77`). O motor
   pausa as medidas do olho (`engine.py:114-116`), mas a tela não sabe: parece falha. Aviso: "Mão no olho: medidas do
   olho em pausa".
5. **Contexto da viagem** (`context.py:68-77`: `madrugada`, `direcao_continua_h`, `limite_direcao_excedido`). A
   madrugada faz sinal leve virar alto em 5 min em vez de 10 (`risk.py:79-84`). Selo discreto "Madrugada: sinais leves
   pesam mais" e o tempo contínuo na barra de cima.
6. **Histerese do risco** (`risk.py:153-161`, `HOLD_DOWN_S` em `risk.py:24`). O motivo `reducao_gradual_do_risco`
   chega, mas não quanto falta. Expor os segundos até baixar e mostrar "Volta para Atenção em 42 s se nada mudar":
   explica por que o risco não cai na hora (pergunta certa num pitch).
7. **Calibração em detalhe**: piscadas contadas ao vivo (`Calibrator.live_blinks`, `calibration.py:66`), duração
   mínima (`min_seconds`, para a contagem regressiva em segundos) e, no fim, o perfil (`profile.summary()`,
   `drowsiness.py:521`: olho aberto, olho fechado, piscadas, duração mediana).
8. **Cada piscada** (`Blink`, `eyes.py:212-220`: duração, amplitude, velocidade fechando e abrindo; já passam pelos
   `blink_listeners`, `drowsiness.py:227`). Marcar cada piscada como um tique no gráfico de abertura, com a duração ao
   passar o mouse; a última piscada em texto: "última: 160 ms".
9. **Os três sinais do olho** (`ear_left`, `ear_right`, `blink_score`, `eye_open_prob`, `face.py:82-87`). Num modo
   "detalhes" (fechado por padrão): olho direito e esquerdo separados e os três sinais em barrinhas.
10. **Qualidade da imagem**: distância (`eye_distance_px`, `face.py:93`), luz e reflexo (`eye_luminance`,
    `cheek_luminance`, `glare_fraction`, `face.py:101-104`), olhos dentro da imagem (`eyes_in_frame`). Viram dicas
    curtas ("chegue mais perto", "pouca luz no rosto", "reflexo nos óculos") em vez de números.
11. **Tempo sem os olhos** (`Visibility.hidden_for`, `visibility.py:32`): contador no aviso "Olhos não visíveis há 4 s"
    (o evento sai aos 10 s, `engine.py:42`).
12. **Pupila e sinais de ativação** (`pupil_ratio`, `pupil_quality`, `face.py:99-100`; `ActivationAssessment`,
    `activation.py:86-93`; `risk.activation_sustained`, `risk.rebound`, `risk.py:44-45`). A janela antiga do OpenCV
    mostrava os dois (`driver_monitor.py:252-260`) e a tela nova perdeu. São dados sensíveis (o próprio `engine.py:6-9`
    trata como privados). **Decisão do Matheus** (pergunta 1 na seção 7).

### 2.3 Dois defeitos achados na leitura (fora do visual, mas bloqueiam a demo)

- **`draw_overlay` usa `metrics` sem definir** (`caixa/vision/driver_monitor.py:252-255`). A alteração não commitada
  trocou `metrics, drowsy, risk = state.metrics, ...` por `drowsy, risk = ...` (`git diff`), e as linhas da pupila
  continuam lendo `metrics.pupil_ratio`. Resultado esperado: `NameError` a cada quadro na janela do OpenCV
  (`--janela-opencv` e caixa com janela), fora do `try` de `_show` (`driver_monitor.py:453-462`), que só pega
  `cv2.error`. Não rodei; é leitura do código. Pede teste antes da correção (regra 2b).
- **Resumo soma o máximo da janela de 10 min, não o total**: bocejos, cabeceios, olhos esfregados e mão no rosto
  (`resumo.py:88-92`, `159-162`). Num teste de 20 min com 3 bocejos em cada metade, o resumo diz 3, não 6. Ou somar os
  eventos/contagens novas, ou rotular "máximo em 10 min".

---

## 3. Guia visual concreto da tela do teste

### 3.1 Grade e proporção

O vídeo é 4:3 (câmera pedida em 640×480; o quadro é ampliado para 960 de largura antes da malha, `sessao.py:38`,
`119-131`). Em notebook, **a altura limita o vídeo**: a largura vem da altura (`largura = altura × 4/3`), e os cartões
ficam com o resto. Duas colunas: vídeo e linha do tempo à esquerda (fixos, sem rolar); cartões à direita (só eles
rolam). Assimetria de propósito (7/5, `diferenciacao-visual.md` §3.1), não a pilha de cartões iguais.

| Tela | Área útil (estimada) | Barra de cima | Vídeo | Linha do tempo | Cartões |
|---|---|---|---|---|---|
| 1366×768 em janela | ~1366×690 (barra de tarefas e título do Windows) | 48 px | **712×534** (52% da largura) | faixa de 72 px: trilha de 24 px + último evento + "ver todos" | 618 px: 2 colunas de ~300 px |
| 1366×768 em tela cheia (F) | 1366×768 | 48 px | 816×612 (60%) | 72 px | 514 px: 1 coluna (ou 2 de 250 com cartões pequenos) |
| 1920×1080 em tela cheia | 1920×1080 | 56 px | **1141×856** (59%) | 120 px: trilha + 3 linhas | 731 px: 2 colunas de ~357 px |
| Celular (só spec 025) | 360 a 430 de largura | 44 px | largura toda, 3:4 em retrato | abaixo dos cartões | 1 coluna |

Regras:
- `grid-template-columns: auto minmax(0, 1fr)`; o vídeo com `height: calc(var(--altura-util) - 48px - 72px - 36px)` e
  `aspect-ratio: 4 / 3`. Nunca `object-fit: cover` no vídeo: a malha está desenhada dentro do quadro, então não
  desalinha, mas o corte some com a borda da imagem e com o rosto de quem senta de lado.
- Cartões com `grid-template-columns: repeat(auto-fit, minmax(260px, 1fr))`. **Tamanhos diferentes por importância**:
  Risco, Olhos e Coração ocupam a largura toda da coluna (classe `wide`, já no HTML); Cabeça, Boca, Celular e mãos,
  Atenção em meia largura; Desempenho vira uma linha de rodapé, não um cartão.
- Acima da dobra em 1366×690: Risco, Olhos e Coração inteiros. O resto rola.
- Usar a mesma compensação de altura do painel (`--altura-janela`, erro 124) se a tela de teste ganhar "texto maior".
- Margens: 12 px em 1366, 16 px em 1920. Espaço entre cartões 10 a 12 px. Cartão com 14 a 16 px de respiro interno.

### 3.2 Tipografia

- Fonte: `"Segoe UI Variable Text", "Segoe UI", system-ui, -apple-system, Roboto, "Noto Sans", sans-serif` (spec 023,
  decisão 8). Horários e durações da linha do tempo: `ui-monospace, "Cascadia Mono", Consolas, monospace`, 12 px.
- **Todo número**: `font-variant-numeric: tabular-nums lining-nums`. Sem isso o "1" e o "8" mudam a largura e o
  número treme 4 vezes por segundo.
- Escala (raiz `font-size: clamp(13px, 0.45vw + 7px, 15px)`: 13 px em 1366, 15 px em 1920):

| Papel | Tamanho | Peso | Cor |
|---|---|---|---|
| Leitura grande (abertura %, bpm) | 2,75 rem, `line-height: 1`, `letter-spacing: -0.02em` | 600 | tinta |
| Unidade junto do número ("%", "bpm", "s") | 0,45 em do número, separada por espaço fixo (U+00A0) | 500 | grafite |
| Nome do nível de risco | 1,75 rem | 600 | cor do nível |
| Valor secundário (PERCLOS, piscadas) | 1,0625 rem | 500 | tinta |
| Rótulo (dt) | 0,9 rem (mín. 12 px) | 500 | grafite |
| Título do cartão | 0,95 rem, frase normal | 600 | grafite |

- **Sem overline em caixa alta em todo cartão** (erro 51): o título do cartão é frase curta ("Olhos", "Coração").
- Vírgula decimal e sinal de menos de verdade: `Intl.NumberFormat("pt-BR")`, "1,4 s", "−8°" (U+2212), "+12°".
- Casas: abertura 0 casas; PERCLOS 1 casa; "fechado há" 1 casa; bpm 0 casas; ângulos 0 casas; qps 0 casas.

### 3.3 Cor dos estados (medida, não suposta)

Regra de R1: **normal não tem cor**. Lima `#d5f669` é a cor da medição e da marca (malha, regiões do pulso, onda,
"ao vivo", botão "Novo teste"), **nunca um estado**. Verde `#5cc79a` só no ponto "ao vivo".

Contraste e distância medidos com script próprio (WCAG 2.x; daltonismo pelas matrizes de Machado et al. 2009,
severidade total; ΔE76 em Lab), arquivo `scratchpad/contraste.py`:

| Estado | Escuro (tela do teste) | Contraste no cartão `#151b18` | Claro (resumo impresso, painel) | Contraste no branco | Desenho além da cor |
|---|---|---|---|---|---|
| Normal | texto `#e6ebe8` | 14,5:1 | texto `#173b30` | 12,3:1 | 0 segmentos, sem moldura |
| Atenção | `#f0cc5c` | 11,2:1 | `#946a00` | 4,86:1 (4,71 no papel) | 1 segmento, contorno |
| Alto | `#f08c4a` | 7,1:1 | `#9c3d0c` | 6,8:1 | 2 segmentos, fundo tingido 14% |
| Crítico | `#ff6b81` | 6,4:1 | `#b0204f` | 6,6:1 | 3 segmentos, selo cheio + moldura do vídeo |

- Menor ΔE76 entre atenção, alto e crítico, escuro: 36,9 normal · 24,0 protan · 14,7 deutan · 15,3 tritan.
  Claro: 31,3 · 16,5 · 9,6 · 12,3.
- Comparação: com o crítico do painel (`#ff8a80`) e um laranja/âmbar comuns, o escuro caía para 8,7 (deutan) e 8,0
  (tritan); no claro, atenção x alto caía para **2,3 em deutan** (indistinguível). Por isso o crítico vai para um
  vermelho-rosado e cada nível tem desenho próprio (segmentos, contorno, tingido, cheio).
- Texto sobre selo cheio: `#0e1311` sobre atenção 12,1:1, alto 7,6:1, crítico 6,9:1; branco sobre os três do claro
  4,9 a 6,8:1; `#103e31` sobre lima 9,8:1.
- Cuidado medido: lima x atenção em deutan dá só ΔE 7,6. Lima nunca aparece colado a um selo de atenção sem texto.
- `#6f7a75` (apagado do escuro) dá 3,9:1 no cartão: só para texto grande ou desligado, nunca para rótulo.
- **Decisão do Matheus**: trocar o crítico também no painel (pergunta 3).

### 3.4 Malha de pontos (o desenho é do Python, `driver_monitor.py:99-171`)

O que já está bom: só dois tons no rosto (neutro claro e lima), cantos do celular em laranja, antisserrilhado com 4 bits
de fração (`SHIFT`), desenho só no retângulo do rosto, quadro ampliado para 960 antes de desenhar. Ajustes:

1. **JPEG com croma 4:4:4.** Medi (`scratchpad/jpeg_teste.py`, quadro 960×720 com 40 traços de 1 px em lima): no
   padrão 4:2:0 a saturação do traço caiu de 140 para **66** (o lima vira cinza-esverdeado) e o erro médio no traço foi
   25,4; com `cv2.IMWRITE_JPEG_SAMPLING_FACTOR_444` a saturação ficou em 131 e o erro em 8,6. Custo: 33 KB → 49 KB por
   quadro (q80), ~1,2 MB/s a 25 qps em `127.0.0.1`. OpenCV 5.0.0 desta máquina tem a opção. Conferir o TEL-11 depois.
2. **Hierarquia em 4 camadas, opacidades diferentes**: regiões do pulso (preenchimento 8% a 24% no ritmo da onda, já
   assim, `driver_monitor.py:145`) → 478 pontos, raio 1 px a ~50% → contorno do rosto e sobrancelhas a ~30% (hoje usam
   a mesma camada dos pontos, 55%; separar) → olhos, íris e boca em lima a 100%. Centro da íris em verde, 1,5 px.
3. **Contorno escuro de 1 px sob o lima dos olhos** (traço preto a 35%, 2 px, antes do lima de 1 px): em pele clara o
   lima (L* 92) quase some.
4. **A malha não muda de cor com o risco.** Ela é medida, não alarme. O estado vai no selo e na moldura.
5. Opcional, bom para o pitch: **preencher o contorno do olho a 30% quando a abertura cai abaixo de 20%**. Quem fecha
   o olho vê o olho "acender" no mesmo instante em que o número cai. Medir no TEL-11 (são dois polígonos pequenos).
6. Modos: `completa` no pitch (`MALHA_PADRAO`, `sessao.py:32`); sugerir `essencial` quando o qps cair abaixo de 20.
   Mostrar o modo atual no controle segmentado com a tecla ao lado ("Malha · M").
7. Espelhamento: o quadro inteiro vira junto no `<img>` (`espelhar` no `/estado`); textos e selos ficam fora da camada
   espelhada.
8. Sem suavizar os pontos para "ficar bonito": tremor real é informação para quem testa.

### 3.5 Coração (`cardio.py:123-136`) à moda de monitor, sem parecer equipamento médico

- Uma linha: **onda à esquerda (60%) e número à direita** (R2). Unidade "bpm" pequena. Embaixo do número, o estado em
  palavras.
- **Onda em lima, 1,5 px**, a mesma cor das regiões da testa e das bochechas no vídeo: mesma cor = mesma fonte. Rola
  da direita para a esquerda (6 s, `onda` normalizada de −1 a 1), sem grade, sem brilho, sem varredura de monitor, linha
  de base apagada a 10%. Não é ECG: nada de desenho PQRST.
- **Confiança embaixo da onda** (R2): faixa fina de 4 px cuja altura ou preenchimento é `confianca` (0 a 1), com o SNR
  em dB no `title`. Hoje o HTML tem `cardio-confianca-barra` ao lado; mover para baixo da onda.
- Estados:

| `estado` | Número | Onda | Texto |
|---|---|---|---|
| `desligado` | — | — | "Desligado nas opções" (cartão encolhe para uma linha) |
| `sem_rosto` | "--" grafite | vazia | "Sem rosto" |
| `medindo` | anel `cardio-anel` contando os 15 s de aquecimento (`AQUECIMENTO_S`, `cardio.py:58`; `progresso`) e os segundos no meio | grafite a 50% (existe sinal, ainda não confiável) | "Medindo · fique parado" |
| `pronto` | bpm, atualizado no máximo 1 vez por segundo | lima | "estimativa pela câmera" |
| `sinal_fraco` | `ultimo_bpm` a 40% de opacidade, nunca um número novo | grafite tracejada | "Sinal fraco · mais luz no rosto, menos movimento" |
| `movimento` | `ultimo_bpm` a 40% | grafite tracejada | "Movimento · fique parado" |

- Respiração (`respiracao_rpm`, "rpm" escrito "por min"), variabilidade (`rmssd_ms`) com a etiqueta "experimental",
  tendência (`historico_bpm`, últimos 120) como linha pequena com faixa mín.–máx. Canal `ir` vira etiqueta "IR".
- Aviso fixo, pequeno, sempre visível: "estimativa pela câmera, não é medida médica" (já no `card-aside`).
- Nada de coração desenhado batendo, número que sobe contando, vermelho.

### 3.6 "Sinal fraco", "calibrando", "sem rosto" e outros estados do vídeo

Um aviso por vez no vídeo, nesta prioridade:

1. Erro de câmera (fase `erro`): painel no lugar do vídeo, com as dicas que já vêm do servidor.
2. Abrindo (fase `abrindo`): retângulo do vídeo em `#0a0e0c` com o texto da etapa (`etapa`), sem esqueleto brilhando.
3. Sem rosto há mais de 1 s: texto centralizado sobre o vídeo escurecido a 40%.
4. Mão na frente do rosto (2.2, item 4): "Mão na frente do rosto · medidas do olho em pausa".
5. Olhos não visíveis: selo no canto superior direito, com contador (2.2, item 11).
6. Rosto virado ou pequeno (`frame_source`): selo "Rosto virado · abertura em pausa".
7. Imagem parada (nenhum quadro novo há 2 s): o ponto "ao vivo" vira atenção e o texto "Imagem parada há 3 s".
8. Calibração: faixa na borda de baixo (3.1) — convive com os avisos 5 a 7.

Em todos: o número fica "--" ou esmaecido, **nunca zero** (zero é uma medida).

### 3.7 Nível de risco sem alarmismo

- Palavras do próprio código e da spec: "sinais compatíveis com", "não é diagnóstico" (`risk.py:3-4`). Crítico diz o
  fato: "Olhos fechados há 1,8 s", não "Motorista dormindo".
- Cor só em três lugares: selo do vídeo, moldura do vídeo (2 px em alto, 3 px em crítico) e cartão de risco. O resto da
  tela não muda de cor.
- Crítico: faixa no topo do vídeo, entra em 180 ms, com o contador "fechado há"; **não pisca**. Ao subir de nível, um
  único pulso de 600 ms na moldura (como `painel-pulso`); ao descer, nada se mexe, só o texto "Risco baixando aos
  poucos" e a contagem (2.2, item 6).
- Motivos em até 3 frases curtas (`texto_motivo`). Sem caveira, sem triângulo em cada linha, sem "ALERTA!".

### 3.8 Animações

Ajudam (todas somem com `prefers-reduced-motion`, menos a onda e o vídeo, que são dado):

| O quê | Como | Duração |
|---|---|---|
| Onda do pulso | rola com o quadro (é dado, fica mesmo com movimento reduzido) | contínua |
| Contadores discretos (piscadas, eventos, bocejos, cabeceios) | rolo do dígito que mudou (R4), com números tabulares | 160 ms |
| Valores contínuos (abertura, ângulos, qps) | **troca seca**, texto 4 vezes por segundo (a pesquisa da spec 025 já faz assim) | 0 |
| Mudança de nível | troca de cor do selo | 160 ms |
| Subida para alto ou crítico | um pulso na moldura | 600 ms, uma vez |
| Evento novo na linha do tempo | entra 4 px de cima (`anim-row`), fundo tingido que some | 180 ms + 2 s |
| Barra da calibração | largura com transição linear | 300 ms |
| Anel do aquecimento do cardio | `stroke-dashoffset` linear | 1 s |
| Aviso (toast) | `anim-toast` | 200 ms |

Atrapalham: número contando ao aparecer; coração batendo; brilho, glow e sombra colorida; varredura "scanner" sobre o
rosto; esqueleto cintilante no vídeo; cartão que levanta no hover (os cartões não são clicáveis); a lista de eventos
rolando sozinha enquanto a pessoa lê; qualquer coisa piscando mais de 3 vezes por segundo (WCAG 2.3.1).

### 3.9 Linha do tempo (`trilha` e `eventos`)

- Trilha: eixo da sessão inteira (marcas por minuto, rótulo a cada 5), altura 24 px. Cada evento é uma marca:
  **forma pela categoria** (`resumo.py:104`): sonolência = círculo, celular = quadrado, sistema = traço fino,
  jornada = triângulo, ativação = losango; **cor pelo nível do evento** (`risk_level` 1 a 5: 1 neutro, 2 atenção,
  3 alto, 4 e 5 crítico). Evento com duração vira barra da largura da duração.
- Lista: hora em mono, rótulo, duração à direita, tabular. Passar o mouse ou focar uma linha acende a marca na trilha.
- Cabeçalho: "7 eventos · último há 12 s" (o "há" conta sozinho).

### 3.10 Resumo ao encerrar

- Placas (`tiles`): duração, eventos, PERCLOS médio, piscadas por min, frequência cardíaca média com uma **barra de
  faixa** (mínima a máxima, traço na média) e o número de leituras; aviso do cardio logo abaixo.
- Tempo em cada nível (`tempo_por_nivel_s`, `resumo.py:156`): barra empilhada na ordem normal → crítico com as cores
  da 3.3 e o rótulo com % e tempo; normal em grafite.
- Eventos por tipo: barras horizontais ordenadas, rótulo à esquerda, número à direita.
- Tempo com celular (`celular_s`), bocejos, cabeceios, esfregados (com a ressalva de 2.3).
- "Salvar resumo" mostra o caminho gravado num aviso; "Novo teste" é o único botão cheio em lima.

---

## 4. Microinterações e detalhes de produto profissional

1. **Atalhos visíveis**: cada botão da barra de cima com a tecla num `<kbd>` (11 px, mono, borda 1 px): "Encerrar
   Q", "Recalibrar C", "Malha M", "Som S", "Tela cheia F". Q, C e M são os mesmos da janela do OpenCV
   (`driver_monitor.py:463-468`).
2. **Foco**: `:focus-visible` com contorno lima de 2 px e 2 px de afastamento no escuro (15,4:1), verde no claro. Só no
   teclado.
3. **Relógio da sessão** em `mm:ss` tabular, `h:mm:ss` depois de 1 h; ao lado, "ao vivo · 29 qps" com o ponto que pulsa
   (`pulse-dot`) e para quando a imagem para.
4. **Avisos curtos** (canto inferior esquerdo da coluna do vídeo, no máximo 2, 4 s, pausam no hover,
   `aria-live="polite"`): calibração concluída, malha trocada ("Malha: essencial"), som ligado/desligado, resumo salvo.
   Crítico nunca vai para aviso: é a faixa do vídeo (`role="alert"` uma vez por episódio).
5. **Contadores que só existem quando importam**: "fechado há", "celular há", "olhos não visíveis há", "bocejo? 1,2 de
   2,0 s". Aparecem com o valor, somem quando zeram.
6. **Limiar sempre desenhado** junto do valor (R1 e Grafana): 20% na abertura, 12% no PERCLOS, 1/3/6 s no fechado,
   15° na cabeça, limiar do bocejo, 2/3 s no celular. Quem olha entende o "porquê" sem ler a spec.
7. **Definição ao passar o mouse** nos termos técnicos (rótulo com sublinhado pontilhado e `title`): PERCLOS = "parte
   do tempo com o olho pelo menos 80% fechado". Sem ícone de "?" em todo cartão.
8. **Modo apresentação** com F: esconde a linha de desempenho e o cursor depois de 3 s parado.
9. **Mesmo evento, mesmo lugar**: o evento novo acende na trilha e na lista ao mesmo tempo; clicar na linha mostra
   duração e nível.
10. **Formatação única** em toda a tela: vírgula decimal, espaço fixo antes da unidade, menos verdadeiro, horário
    `hh:mm:ss`.

---

## 5. Não faça (específico destas telas)

1. Gradiente roxo, azul ou qualquer gradiente de fundo; glassmorphism no vídeo ou nos cartões; glow em traço, número ou
   borda.
2. Ícone em todo cartão; emoji; coração desenhado; caveira, sirene ou triângulo de alerta repetido.
3. Vermelho na onda do pulso ou nas regiões do rosto (a pesquisa da spec 025 sugeria vermelho: trocar por lima).
4. Cor de risco na malha. A malha é medida; quem fala o risco é o selo.
5. Lima como cor de estado (ele parece âmbar para deuteranopes, ΔE 7,6).
6. Número zero quando não há medida. "--" ou o último valor esmaecido, com o motivo.
7. bpm novo com sinal fraco ou em movimento; bpm sem o aviso "estimativa pela câmera, não é medida médica".
8. Contador animado de 0 até o valor; tween em valor contínuo; número sem `tabular-nums`.
9. Piscar a tela inteira ou o selo em crítico; overlay vermelho sobre o vídeo.
10. Grade quadriculada de ECG, verde fósforo, fonte de "monitor", cantos chanfrados de HUD de ficção.
11. Overline em caixa alta em cada cartão (erro 51); cartões todos do mesmo tamanho.
12. Texto de marketing na tela ("IA de última geração", "monitoramento inteligente"). A tela diz o que mede.
13. "Detecta sono com X% de precisão" ou "mede a frequência cardíaca" (pesquisa da spec 025, §7).
14. Qualquer endereço `http(s)://` externo nos arquivos de `web/` (TEL-14): nada de fonte do Google, CDN ou ícone remoto.
15. `object-fit: cover` cortando o rosto; texto espelhado junto com o vídeo.
16. Cartão que levanta no hover sem ser clicável; animação sem `prefers-reduced-motion`.

---

## 6. Lista de verificação olhando a captura (VIS-01 a VIS-30)

Tirar capturas em 1366×768 (janela) e 1920×1080 (tela cheia), nas fases `calibrando`, `rodando` com risco normal,
`rodando` com crítico (olhos fechados 2 s), sem rosto, e `resumo`.

| ID | Conferir na captura |
|---|---|
| VIS-01 | O vídeo é o maior elemento: ≥ 50% da largura em 1366×768 e ≥ 55% em 1920×1080, inteiro (sem corte) e 4:3. |
| VIS-02 | Em 1366×768 em janela, Risco, Olhos e Coração aparecem inteiros sem rolar. |
| VIS-03 | Vídeo e linha do tempo não rolam junto com os cartões. |
| VIS-04 | Risco, Olhos e Coração ocupam a largura da coluna; os outros cartões são menores. |
| VIS-05 | Os 478 pontos são discretos (claros, ~50%); olhos, íris e boca se destacam em lima; contorno do rosto mais fraco que os pontos. |
| VIS-06 | O lima dos olhos aparece nítido e saturado (não cinza-esverdeado) ao ampliar a captura em 400%. |
| VIS-07 | Testa e bochechas têm contorno lima e preenchimento leve; com o cardio `pronto`, a mesma cor está na onda. |
| VIS-08 | A malha tem a mesma cor em risco normal e em crítico. |
| VIS-09 | Em risco normal não há cor de estado na tela (só neutros, o lima da medição e o ponto "ao vivo"). |
| VIS-10 | Em crítico: selo cheio com 3 segmentos, moldura do vídeo e faixa "Olhos fechados há X s"; o resto da tela continua neutro. |
| VIS-11 | Cada nível tem desenho próprio (0 a 3 segmentos; contorno, tingido, cheio) e a palavra escrita; a captura em escala de cinza ainda mostra o nível. |
| VIS-12 | Nenhum número de medida mostra "0" sem medida: sem rosto, aparecem "--" ou valores esmaecidos com o motivo. |
| VIS-13 | Sem rosto: uma mensagem só, centralizada, com o que fazer. |
| VIS-14 | Calibrando: faixa na borda de baixo do vídeo + texto com segundos e instrução. |
| VIS-15 | Cardio `medindo`: anel com segundos; nenhum bpm. `sinal_fraco`/`movimento`: bpm anterior esmaecido e o motivo; onda grafite tracejada. |
| VIS-16 | O aviso "estimativa pela câmera, não é medida médica" aparece no cartão do coração e no resumo. |
| VIS-17 | A onda não tem grade, brilho nem forma de ECG; é lima (pronto) ou grafite (não confiável). |
| VIS-18 | A confiança do pulso aparece logo abaixo da onda. |
| VIS-19 | Todo número está alinhado em coluna (tabular) e usa vírgula decimal; unidades menores e em grafite. |
| VIS-20 | Abertura do olho tem linha em 20%; PERCLOS tem marca em 12%; "fechado há" tem marcas 1, 3 e 6 s. |
| VIS-21 | Cabeça mostra sinal e palavra ("+12° cabeça baixa") e a marca de 15°. |
| VIS-22 | Celular detectado: cantos laranja no vídeo com a confiança fora da caixa e a barra de tempo até o alerta no cartão. |
| VIS-23 | Linha do tempo: marcas com forma por categoria e cor por nível; lista com hora em mono. |
| VIS-24 | Barra de cima mostra as teclas (Q, C, M, S, F) junto dos botões, o relógio e "ao vivo · N qps". |
| VIS-25 | Nenhum emoji, ícone decorativo por cartão, gradiente, glow ou vidro fosco. |
| VIS-26 | Títulos de cartão em frase normal; nenhum overline repetido. |
| VIS-27 | Textos em português com acento; nenhuma palavra de marketing. |
| VIS-28 | Texto pequeno legível: rótulos ≥ 12 px e contraste ≥ 4,5:1 (grafite `#9fa9a4` no cartão escuro dá 7,2:1). |
| VIS-29 | Resumo: barra empilhada do tempo por nível na ordem normal → crítico, faixa mín.–máx. do bpm e botões Abrir pasta, Salvar resumo, Novo teste (só este em lima). |
| VIS-30 | Com foco no teclado, o elemento focado tem contorno visível de 2 px. |

---

## 7. Perguntas para o Matheus

1. **Pupila e sinais de ativação** (2.2, item 12) voltam na tela nova? A janela antiga mostrava. São sensíveis; se sim,
   num bloco "Detalhes" fechado, com "não é diagnóstico".
2. **Fonte**: fica a do sistema (spec 023) ou levamos a Manrope em arquivo local para casar com o painel e o site (não
   quebra o TEL-14, que só proíbe endereço externo)?
3. **Crítico novo** (`#ff6b81` escuro, `#b0204f` claro): só no teste ou também no painel (hoje `--color-alarme`)?
4. Liberar a entrada no `/estado` dos campos da 2.2 (PERCLOS 3 min, "comparado com você", motivo da abertura, mão no
   olho, contexto, histerese, calibração em detalhe)? Cada um entra com teste antes (regra 2b).

---

## 8. Nota curta: tela Ao vivo do painel (spec 025)

- Mesmos tokens da 3.3 e a mesma regra "normal sem cor"; o painel em modo claro usa a coluna "claro".
- A malha é desenhada em canvas no navegador (pesquisa da spec 025, §2): tamanho interno `clientWidth ×
  devicePixelRatio` limitado a 2; pontos de 1,5 px CSS; no celular (largura < 600 px ou qps < 20) começar em
  `essencial`. Trocar o vermelho sugerido para regiões e onda por lima.
- Celular em retrato: vídeo na largura toda, preso no topo (~45% da altura), selo de risco sobre o vídeo, cartões em
  uma coluna abaixo. **Botão "Parar câmera" sempre visível** (CAM-09), fora da área que rola.
- Nome na tela: "teste no navegador" (spec 025, decisão 2); a caixa continua sendo a referência.

---

## 9. Fontes

Abertas por WebFetch em 19/10/2026: Linear (redesenho), Vercel Geist (cores), Grafana (limiares), guia ISA-101
(open-exam-prep), Apple Face ID (support.apple.com/en-us/108411), Motion Primitives (Sliding Number), NumberFlow.
Achadas pela busca e não abertas para leitura automática (bloqueio a robô ou redirecionamento): control.com "Going Gray",
PDF Airbus/ICAO, PDF Masimo Signal IQ, Dribbble (202 vazio), Codrops (403). Origin UI agora redireciona para
https://coss.com/ui.

- https://open-exam-prep.com/study-guides/isa-cap/system-design-hmi-alarms-enterprise/hmi-design-isa101
- https://control.com/technical-articles/going-gray/
- https://www2023.icao.int/ESAF/Documents/meetings/2017/AFI%20FOSAS%202017/Day%201%20Docs/Day_1_2_Airbuspihlo.pdf
- https://professional.masimo.co.uk/siteassets/uk/documents/pdf/clinical-evidence/whitepapers/lab5318b_whitepapers_signal_iq.pdf
- https://medaval.ie/docs/specs/Masimo-Rad-5-Specs.pdf
- https://nursing.lsuhsc.edu/AlarisTraining/spo2/t1/p05.htm
- https://dribbble.com/shots/15865788--2021-Vital-signs-monitor-UI-medical-device
- https://dribbble.com/tags/patient_monitoring
- https://dribbble.com/search/monitoring-system
- https://motion-primitives.com/docs/sliding-number
- https://number-flow.barvian.me/
- https://support.apple.com/en-us/108411
- https://tympanus.net/codrops/2026/09/06/building-a-real-time-3d-face-mask-with-mediapipe-threlte-and-three-js/
- https://linear.app/now/how-we-redesigned-the-linear-ui
- https://vercel.com/geist/colors
- https://grafana.com/docs/grafana/latest/panels-visualizations/configure-thresholds/
- https://jfly.uni-koeln.de/color/
- Machado, Oliveira e Fernandes (2009), "A Physiologically-based Model for Simulation of Color Vision Deficiency"
  (matrizes usadas no script de contraste).
