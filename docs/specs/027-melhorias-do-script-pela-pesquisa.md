# Spec 027 · Melhorias do script a partir da pesquisa de 19/10/2026

| Campo | Valor |
|---|---|
| Status | pacotes 1 e 2 implementados em 19/10/2026 (`test_alarme_risco` 23, `test_distracao` 29, `test_rosto_perdido` 8, `test_calibracao_robusta` 9); pacotes 3 (desempenho) e 4 (validação no app) pendentes; limiares validados só com dados sintéticos |
| PRD | RF-01, RF-02, RF-03, RF-04, RF-19 (novo: distração pelo olhar), RF-20 (novo: avisos por urgência), RNF-01, RNF-02 |
| Pedido | "pesquise mais para ver se consegue melhorar tudo ao maximo"; "essas pesquisas devem ser de acordo com o conteudo do script para deixalo mais completo ao maximo"; "é necessario que deixe o script mais completo e bonito possivel" (19/10/2026) |
| Pesquisa | `docs/pesquisa/2026-10-19-estado-da-arte-dms.md` (IDs DMS-xx), `docs/pesquisa/2026-10-19-alarme-calibracao-e-registro.md` (SCR-Axx, ALM, CAL, CTX, PER, RSK), `docs/pesquisa/2026-10-19-datasets-e-validacao.md` (VAL-xx), `docs/pesquisa/2026-10-19-referencias-visuais-tela-do-teste.md` (VIS-xx) |
| Specs irmãs | 009, 011 (sinais complementares), 022 (cardio), 023 (tela do teste), 026 (trechos e central) |

Os critérios de aceite são os da pesquisa, com o mesmo ID, para manter a rastreabilidade (pesquisa → spec → teste).
Cada pacote é implementado por TDD; o teste leva o ID no nome ou na mensagem.

## Achados que motivam a spec (todos reproduzidos com dados sintéticos na pesquisa)

1. **Microssono com o rosto perdido não dispara alarme** (`eyes.py:290-292`, `drowsiness.py:399-409`): olho fecha, a
   cabeça cai e o rosto sai da imagem em 0,6 a 0,9 s → nada toca. É o caso mais perigoso.
2. **Um som só para tudo e sem interromper** (`alarm.py:16-131`): o Euro NCAP 2026 (§1.4.2) pede aviso de microssono e
   sono distinto e mais urgente que o de distração.
3. **Não há distração pelo olhar**: 15 dos 25 pontos de monitoramento do motorista no Euro NCAP 2026. Só existe
   "olhando o celular" com o aparelho confirmado (`phone.py:360`).
4. **Olhar para o colo só com os olhos vira microssono** (o filtro de pitch de 25° de `eyes.py:28` não pega).
5. **Calibração aceita motorista já sonolento** (`calibration.py:168`) e erra a referência de olho fechado em 57% a
   10 quadros/s (`calibration.py:114`).
6. **Risco volta a zero em ~2 min depois de sonolência** (`risk.py:24`), sem pausa real.
7. **Calculado e descartado:** 50 dos 52 blendshapes (`face.py:262`), `roll`, `mar`, `glare_fraction`, translação da
   matriz facial, frequência e p90 de piscada do perfil.
8. **Sem aviso ao motorista quando o sistema não enxerga** (só no registro aos 10 s).
9. **Entropia do olhar contada como ativação** (`activation.py:38-44`), mas ela sobe com a privação de sono
   (Shiferaw 2018).

## Decisões (padrões até o Matheus dizer o contrário)

| Pergunta da pesquisa | Padrão |
|---|---|
| Voz no alarme | Só tons sintetizados por enquanto (4 sinais); frase gravada pela equipe depois. Piper é GPL-3.0: fora |
| Orçamento de avisos de celular | A partir do 6º na hora, som suave; o crítico nunca é limitado |
| Memória de sonolência | Depois de nível 2 por sono, o risco fica ≥ 1 até pausa de 15 min ou 30 min sem sinais |
| "Limite de 5 h 30" sem telemetria | Vira `tempo_com_rosto_h` (estimativa); o limite legal só com ignição ou acelerômetro no Pi |
| Distração toca alarme? | Sim, aviso curto e suave (distinto do de sono), dentro do orçamento por hora |
| Velocidade | Sem GPS (PRD §5). Sem fonte de velocidade, a distração roda em modo "sem velocidade", registrado como tal; no Pi, ignição ou IMU |
| KSS no app de teste | "Modo validação", desligado por padrão: pergunta a cada 5 min (teclas 1 a 9) |
| Trechos | 16 s (spec 026); revisão simples, sem ORD |
| Horas dormidas | Não perguntar por enquanto |
| Pupila e sinais de ativação na tela | Seção recolhida "Sinais avançados (experimental)", só local |

## Pacotes

### Pacote 1 · Alarme, risco e contexto (`alarm.py`, `risk.py`, `context.py`, `event_queue.py`)

| ID | O quê | Critério (resumo; detalhe na pesquisa) |
|---|---|---|
| ALM-03 | 4 sinais sintetizados (`info`, `distracao`, `sonolencia`, `critico`) | WAVs determinísticos; ≥ 4 harmônicos; `critico` com maior taxa de pulsos; celular nunca gera `critico` |
| ALM-04 | Reprodução interrompível com preempção | `critico` interrompe `distracao` em ≤ 100 ms; `stop()` para em ≤ 100 ms |
| ALM-05 | Autoteste do som ao ligar (RF-04) | toca `info` uma vez; sem player registra `sem_saida_de_som` |
| ALM-06 | Escalonamento: sonolência por 5 min → estágio mais urgente | — |
| ALM-07 | Memória de sonolência | nível ≥ 1 até pausa ≥ 15 min ou 30 min sem sinais |
| ALM-08 | Orçamento de avisos não críticos | do 6º aviso de celular na hora em diante, som suave e linha no registro |
| CTX-01 | `pausa_sugerida` e `pausa_detectada` | rosto ausente 18 min depois da sugestão → `pausa_detectada` ≈ 1080 s |
| CTX-02 | Janelas circadianas 02–06 (forte) e 14–16 (moderado) | 03h → forte; 15h → moderado; 01h → nada |
| CTX-03 | Sem telemetria não afirma limite legal | `limite_direcao_excedido = null`, `tempo_com_rosto_h` preenchido |
| CTX-04 | Regra de passageiros (4 h) com telemetria | aviso de descanso em 4 h |
| PER-01 | PERCLOS por quadros (AAA) além do atual | os dois nos detalhes |
| RSK-01 | `sono_estimado` (faixa de KSS com confiança) e canais sono × distração | texto fixo "estimativa, não é medida de KSS nem diagnóstico"; celular sozinho não mexe no canal de sono |
| FIL-01 | Fila com `synchronous=FULL` | `PRAGMA synchronous` = 2 |
| DMS-04 | "Sem visão": aviso uma vez por viagem aos 10 s sem enxergar os olhos | som `info` + texto fixo |

### Pacote 2 · Olhar, distração, piscada e calibração (`face.py`, `eyes.py`, `drowsiness.py`, `calibration.py`, `activation.py`, `visibility.py`, novos `gaze.py`, `distraction.py`, `filtros.py`, `engine.py`)

| ID | O quê |
|---|---|
| ALM-01 / ALM-02 | Microssono com rosto perdido vira "possível sono" (alarme crítico em ≤ 2,0 s); pegar algo no chão de olho aberto não toca |
| DMS-05 | Blendshapes em `FaceMetrics` e as 52 colunas no CSV de validação |
| DMS-03 | Olhar para baixo ≠ olho fechado (`eyeLookDown` + OCEC + íris) |
| DMS-02 | "Frente" automática pela moda do olhar (raio 8°) e calibração guiada opcional |
| DMS-01 | Distração: zonas, balde de 2 s, distração longa 3 s, olhares repetidos 10 s em 30 s, Área 3 abaixo de 30°; eventos `distracao_longa` e `distracao_repetida` |
| DMS-17 | Sem resposta pela distração: olhar não volta 3 s depois do aviso |
| DMS-06 | Dinâmica da piscada: tempo de reabertura, desvio do AVR, frequência vs base, fração acima do p90 |
| DMS-07 | Reflexo nos óculos (`glare_fraction`) tira peso do EAR e da íris |
| DMS-12 | PRC e entropia no registro; entropia só conta como ativação sem piscada lenta |
| DMS-14 | One Euro só na pose e nas ROIs do cardio (o MediaPipe já filtra os pontos) |
| DMS-18 | Postura pela translação da matriz (`fora_da_posicao`) |
| CAL-01 | Referência de olho fechado robusta à taxa de quadros |
| CAL-02 / CAL-03 | Calibração com sono moderado vira suspeita; calibração alerta não muda |

### Pacote 3 · Desempenho (`camera.py`, `driver_monitor.py`, `phone.py`)

| ID | O quê |
|---|---|
| DMS-08 | Captura em thread com o último quadro; `timestamp` da captura |
| DMS-09 | Celular a 1 Hz, subindo a 4 Hz com mão perto do rosto (rosto ≥ 28 fps no notebook) |

### Pacote 4 · Validação no app de teste e nas ferramentas (`caixa/tela_teste/`, `ferramentas/`)

| ID | O quê |
|---|---|
| DMS-11 | KSS a cada 5 min no modo validação e `ferramentas/avaliar_kss.py` (sensibilidade estilo DDAW) |
| DMS-19 | Roteiro de verificação estilo Euro NCAP SD-202 no app: "olhe o colo 4 s", "feche os olhos 4 s", mede o atraso do aviso — ótimo para o pitch |
| VAL (F1, F2) | Clipe curto calibra; tempo pelo carimbo do quadro (fps variável); avaliador por evento com latência, falsos alarmes por hora e intervalo de confiança; `avaliar_cardio.py` |

### Depende do Pi (fica registrado, fora desta rodada)

SCR-P01 a P08 e DMS-20 a DMS-26 da pesquisa: latência real do alarme, saída de som e nível na cabine, botão "ciente" e
LED, ignição/IMU, energia e cartão, H.264 no Pi 4 × Pi 5, multirresolução para a pupila, validação em IR 940 nm,
posição da câmera, detector de celular Apache (YOLOX-Nano ou NanoDet-Plus) treinado com gravações da cabine.

## Fora de escopo

- GPS (PRD §5). Diagnóstico de qualquer tipo.
- Trocar o detector de celular agora (depende de gravações).

## Validação (pesquisa de datasets)

- Primeiro a gravação própria com a equipe (protocolo na pesquisa, §3), depois NITYMED, YawDD e UL-DD (CC BY; pedir
  acesso). NTHU-DDD, DMD, PURE, MMPD e outros proíbem uso por empresa.
- Nenhum número de desempenho vai para o pitch sem relatório em `docs/validacao/` com commit, versões e intervalo de
  confiança.

## Notas da implementação (19/10/2026)

- **RSK-02** (decisão do coordenador): o nível 1 do olhar ("atenção visual", ex.: olhada de 3 s ao espelho) fica só
  no canal de distração, para a tela; do nível 2 em diante entra nos motivos e no risco geral. Teste em
  `tests/test_alarme_risco.py`.
- **Sons** (`caixa/vision/alarm.py`): `info` 0,56 s, `distracao` 0,42 s, `sonolencia` 0,92 s, `critico` 1,72 s com 9,3
  pulsos por segundo; fluxo de áudio sempre aberto (a chamada volta em ~1 ms; antes `sd.stop()` travava a câmera por
  214 a 332 ms). No alto-falante a troca leva 95 a 145 ms.
- **Rosto perdido** (ALM-01): alarme crítico 1,03 s depois do fechamento; olho aberto antes de o rosto sumir não toca.
- **Distração** (DMS-01): distração longa aos 3,00 s (cabeça ou só olhos; 4,5 s sem íris), olhares repetidos aos 18,00 s
  no cenário de teste; espelho por 3,5 s não avisa. Sem fonte de velocidade, os eventos levam `modo_velocidade:
  "sem_velocidade"`.
- **Calibração guiada** pronta para a tela chamar: `engine.distraction.start_guided_calibration()`,
  `guided_target(zona)`, `finish_guided_calibration(perfil)`.
- **Pendentes**: DMS-14b (efeito do filtro interno do MediaPipe na piscada, depende de vídeo real) e o One Euro nas
  ROIs do cardio.
