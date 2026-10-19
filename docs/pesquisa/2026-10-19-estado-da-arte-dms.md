# Pesquisa DMS: estado da arte aplicado ao script do RotaGuard

| Campo | Valor |
|---|---|
| Data | 19/10/2026 |
| Escopo | `caixa/vision/` (script da caixa e do RotaGuard Teste), normas de DMS, literatura de sonolência e distração, desempenho, celular |
| Lido no repositório | `docs/produto/PRD.md`, specs 009, 011 e 022, `drowsiness.py`, `eyes.py`, `eye_state.py`, `face.py`, `phone.py`, `face_touch.py`, `visibility.py`, `activation.py`, `risk.py`, `context.py`, `pupil.py`, `engine.py`, `calibration.py`, `camera.py`, `alarm.py`, trechos de `driver_monitor.py` |
| Lido na vault | `DriveSafe AI - Monitoramento de Motoristas/06`, `07` e `11` |
| Nada foi editado | Nem no repositório nem na vault. Só este arquivo e arquivos de apoio em `scratchpad/` (PDFs baixados, script de medição) |

> [!note] Como ler
> - **Fonte primária lida** = PDF ou código aberto e lido por mim (Euro NCAP v1.2, SD-202 v1.2, model cards do MediaPipe,
>   código do MediaPipe, tabelas do Hailo Model Zoo, licenças no GitHub).
> - **Secundária** = resumo de terceiros (marcado assim). **Hipótese** = não verificado; precisa de medida.
> - **Linhas de código** foram lidas em 19/10/2026 de manhã. `face.py`, `engine.py` e `driver_monitor.py` estavam sendo
>   editados por outra frente (malha e cardio da spec 022); as linhas desses três podem ter andado.

---

## 1. Normas e protocolos: o que um DMS precisa detectar

### 1.1 Euro NCAP 2026, Safe Driving · Driver Engagement (v1.2, julho de 2026, vale desde janeiro de 2026)

Lido no PDF do protocolo e no boletim técnico de teste SD-202 v1.2.
Fontes: [protocolo v1.2](https://cdn.euroncap.com/cars/assets/Euro_NCAP_Protocol_Safe_Driving_Driver_Engagement_v1_2_ebce03a443.pdf) ·
[SD-202 v1.2](https://cdn.euroncap.com/cars/assets/SD_202_Driver_Monitoring_Test_Procedure_v1_2_d3420cb629.pdf).

**Pontuação:** Driver Monitoring vale 25 dos 30 pontos do Driver Engagement. Estados transitórios (distração) = 15
pontos; não transitórios (sono, prejuízo, sem resposta) = 10. **A distração vale mais que a sonolência no protocolo**,
e é justamente o que o RotaGuard ainda não tem.

| Item | Regra do protocolo (seção) |
|---|---|
| Ligado | Ligado por padrão a cada viagem; não desliga com um toque; **sensibilidade não ajustável pelo motorista** (1.1) |
| Início | Até **1 min a ≥10 km/h** para começar a medir (1.1) |
| Velocidade | Distração, microssono, sono e sem resposta avisam a **≥20 km/h**; prejuízo (sonolência, álcool) a **≥50 km/h**, com aprendizado de **até 10 min** a ≥50 km/h (1.1) |
| Distração longa (LGA) | **Um** olhar fora da via de **3 a 4 s** (valor declarado pelo fabricante), precedido de 4 s olhando a via no teste. Movimentos: *owl* (cabeça), *lizard* (só olhos) e inclinação do corpo. Alvos: janelas, pé do passageiro, rosto do passageiro, central multimídia, porta-luvas, passageiro de trás; tarefas de direção: espelhos e painel (1.2.1). Tolerância do teste: 0,2 s (SD-202 4.1.1.1). *Owl* em até 0,48 s, *lizard* em até 0,16 s (SD-202 3.2.3.2) |
| Distração curta (VATS) | Olhares repetidos fora da via que somam **10 s numa janela de 30 s**; estratégias alternativas são aceitas; termina quando a atenção volta à via "tempo suficiente" (1.2.2). O SD-202 define `T_VATS_reset` (tempo mínimo de volta à via para zerar) como valor do fabricante; resumo da Seeing Machines diz **2 s** (secundária). Aviso esperado em `T_VATS ± 2,0 s` (SD-202 4.1.1.2) |
| Uso de celular | Tipo de VATS com o olhar indo ao celular. Básico: joelho (dentro e fora), **colo**, suporte no painel, carregador ou suporte dedicado, celular no centro do volante. Avançado (*lizard*): suporte no painel, celular na mão no volante (9–11 h ou 13–15 h), à vista do para-brisa ou do painel. No suporte dedicado o aviso pode ser suprimido **só se a tela não estiver visível** (1.2.3) |
| Sonolência | Detectar **KSS > 7 no mais tardar** (ou métrica equivalente), funcionando a partir de 50 km/h (1.3.2) |
| Microssono | Olho fechado por **1 a 2 s** (declarado); no teste, fecha os olhos até 4 s, tolerância 0,2 s (1.3.3; SD-202 4.1.2.2) |
| Sono | Olho fechado **3 s** (fixo) (1.3.4; SD-202) |
| Sem resposta | Olhar não volta à via **3 s depois do aviso de distração**, ou olhos fechados **6 s** (1.3.5) |
| Aviso | Visual + (sonoro e/ou háptico) **imediatamente** após classificar. **Microssono e sono têm aviso distinto e mais urgente** que distração e prejuízo (1.4.1, 1.4.2) |
| Não funciona | Se o sistema fica inoperante (óculos <15% de transmitância, mão às 12 h, máscara, boné, franja, maquiagem pesada), avisar o motorista **em até 10 s**; som no máximo 1 vez por viagem; visual permanente ou a cada 10 min (1.1.1.2) |
| Ruídos que **têm** de funcionar | Luz de 1 lux a 100.000 lux; óculos claros >70% de transmitância (inclusive aro grosso); barba curta (<20 mm) e longa (>150 mm); idade 16–80; Fitzpatrick 1–6; abertura palpebral de 6 a 12 mm; **falar** (1.1.1) |
| Comportamentos só descritos | Comer, rir, cantar, fumar, **coçar/esfregar o olho**, espirrar: o fabricante descreve o efeito (1.1.1.3) |
| Vídeo de teste | Gravado a **≥25 Hz** (SD-202 §1) |
| Avaliação na estrada | Avisos sem motivo (distração olhando a via; sonolência com o motorista alerta) podem tirar os pontos (SD-202 4.4) |

Prevalência na direção real (Seeing Machines, estudo naturalístico, secundária):
[lite paper](https://seeingmachines.com/wp-content/uploads/2026/01/Lite-Paper_European-NCAP-Driver-State-Monitoring-Protocols-Prevalence-of-Distraction-in-Naturalistic-Driving.pdf)
- distração longa **1 vez a cada 1,1 h**; VATS **1 a cada 4,8 h**;
- sistema que não separa espelho de olhar não ligado à direção **quase triplica** a taxa de alertas;
- olhares *lizard* (só olhos) são mais comuns que *owl*: só a cabeça perde boa parte das distrações;
- em veículo comercial, monitorar e avisar na cabine reduziu eventos de sonolência em 66% (Fitzharris et al., 2017,
  citado no mesmo texto).

### 1.2 União Europeia: GSR 2019/2144

**DDAW** (Regulamento Delegado 2021/1341). Texto lido via [LawPlayer](https://lawplayer.com/eu/act/32021R1341)
(o EUR-Lex devolveu página vazia, o mesmo erro 6 da nota `07 - Erros e aprendizados`;
[ELI oficial](https://eur-lex.europa.eu/eli/reg_del/2021/1341/oj/eng)):
- aviso a partir de **KSS ≥ 8** (pode avisar em 7) (Anexo I, Parte 1, 3.3.1);
- ativa acima de **70 km/h**, opera de **65 a 130 km/h**, começa a monitorar em até 5 min (3.1.4–3.1.6);
- validação: **≥10 participantes**, ≥10 eventos, dia e noite, KSS autoavaliado a cada ~5 min; sensibilidade média
  **> 40%** (ou limite inferior do IC 90% > 20%) (Parte 2, 3.1, 4.1, 5.1.2, 8.1);
- operação **sem biometria nem reconhecimento facial**; só os dados necessários, em **circuito fechado** (2.3).
  O DDAW foi pensado para sinais do veículo (volante, faixa); o RotaGuard é um DMS por câmera, mais próximo do ADDW.

**ADDW** (Regulamento Delegado 2023/2590). **O texto oficial não abriu** (EUR-Lex com desafio anti-robô). Números de
fontes secundárias ([ATIC, resumo do rascunho](https://www.atic-ts.com/brief-introduction-of-advanced-driver-distraction-warning-system-research-draft/),
[Seeing Machines](https://seeingmachines.com/understanding-advanced-driver-distraction-warning-addw-systems/)):
- ativa acima de 20 km/h;
- **Área 3** = abaixo de um plano **30° para baixo** do ponto de referência ocular (painel, console, colo); é a área de
  alerta obrigatório. Área 1 = fora de ±55° e teto; Área 2 = para-brisa e janelas + 10°;
- aviso com olhar na Área 3 por **3,5 s a ≥50 km/h**; **6 s a ≥20 km/h** (rascunho); **+1,5 s** em situação "não
  nominal" (óculos escuros, barba).

> [!note] Hipótese, confirmar
> Os 3,5 s / 6 s / +1,5 s / 30° do ADDW não foram lidos no Jornal Oficial. Usar como valor padrão configurável, nunca
> como "conforme a norma" em texto do site (RF-33).

### 1.3 Outras referências

- **NHTSA (diretrizes visual-manuais, 2013):** cada olhar fora da via ≤ **2 s**; total ≤ **12 s** por tarefa.
  [NHTSA](https://www.nhtsa.gov/sites/nhtsa.gov/files/strickland-distraction_guidelines_03122012.pdf)
- **Klauer et al. 2006 (100-Car, DOT HS 810 594):** olhar fora da via somando **>2 s** dobra o risco de quase-colisão ou
  colisão; sonolência multiplica o risco por 4 a 6.
  [NHTSA](https://www.nhtsa.gov/document/810594driverinattentionnearcrashcrashriskpdf)
- **AttenD (Kircher & Ahlström):** "balde" de atenção de **2 s** que esvazia quando o olhar sai do campo relevante para
  a direção (FRD) e enche quando volta; **0,1 s** de espera antes de voltar a encher; **1 s** de tolerância para
  espelhos e velocímetro antes de começar a esvaziar; distraído com o balde em 0; FRD = círculo de 90° ∩ janelas, sem
  os espelhos; aviso só acima de 50 km/h, sem seta, freio ou manobra brusca.
  [Kircher & Ahlström, 2010](https://pmc.ncbi.nlm.nih.gov/articles/PMC3242543)
- **PRC, *percent road centre* (Victor, Harbluk & Engström, 2005):** % do olhar num círculo de **8° de raio** centrado
  na **moda** (ângulo mais frequente); PRC e desvio-padrão do olhar foram mais sensíveis que medidas por olhar.
  Secundária: [SWOV](https://swov.nl/en/publicatie/sensitivity-eye-movement-measures-vehicle-task-difficulty),
  [arXiv 2104.05677](https://arxiv.org/pdf/2104.05677).
- **ISO 15007:2020 / SAE J2396:** duração do olhar conta **desde o início da transição** até sair do alvo
  (secundária, arXiv 2104.05677). Importa para medir 3 s "à moda Euro NCAP".
- **ISO/TR 21959-1:2020:** conceitos de desempenho e estado do motorista em automação SAE níveis 1–3; informativo, sem
  limiares. [ISO](https://www.iso.org/standard/78088.html)
- **SAE J3016:** os veículos da frota são nível 0–2: o DMS só **avisa** (não há "intervenção" de ADAS a que o Euro NCAP
  dá pontos). **SAE J2944** (medidas de desempenho de direção, ex.: posição na faixa) não se aplica: sem câmera de
  estrada (ADAS está fora de escopo no PRD §5).

### 1.4 Tabela: requisito → o RotaGuard já faz? → o que falta

| # | Requisito (fonte) | Faz hoje? | Onde (arquivo:linha) | Falta |
|---|---|---|---|---|
| N1 | Microssono 1–2 s (EN 1.3.3) | **Sim**, 1,0 s → `microssono`, nível 3, alarme | `drowsiness.py:28`, `71-75`, `345-369` | Medir câmera→som (O1, RNF-01). Som distinto e mais urgente (EN 1.4.2): hoje há uma sirene só (`alarm.py:18-45`) |
| N2 | Sono 3 s (EN 1.3.4) | **Sim** | `drowsiness.py:29`, `73` | idem |
| N3 | Sem resposta: 6 s de olho fechado **ou** sem voltar à via 3 s após aviso de distração (EN 1.3.5) | **Parcial**: só os 6 s | `drowsiness.py:30`, `74` | Ramo da distração (DMS-17) |
| N4 | Sonolência KSS ≥ 8 (EN 1.3.2; DDAW 3.3.1) | **Parcial**: PERCLOS 3 min ≥12%, piscada +25%, fechamentos longos, cabeceios, leves persistentes 10 min | `drowsiness.py:33-48`, `450-508`; calibração `calibration.py:59-92` | **Nenhuma validação contra KSS** (DMS-11); sem velocidade para "≥50 km/h" (DMS-13) |
| T1 | Distração longa 3–4 s, *owl* + *lizard* (EN 1.2.1) | **Não**. Só `olhando_celular` ≥2 s com celular confirmado | `phone.py:73-79`, `319-321`, `360-361`, `390-400` | Zonas do olhar (DMS-01, DMS-02, DMS-03) |
| T2 | VATS 10 s em 30 s (EN 1.2.2) | **Não** | — | DMS-01 |
| T3 | Uso de celular como VATS (colo, joelho, volante, suporte) (EN 1.2.3) | **Parcial**: na mão, no ouvido, olhando; suporte parado não conta | `phone.py:299-366`, `68-71` | Colo e joelho (o recorte vai até 2,4 rostos abaixo, `phone.py:46-48`); olhar repetido ao colo sem ver o aparelho (DMS-01) |
| T4 | ADDW: Área 3 por 3,5 s / 6 s (secundária) | **Não** | — | Zona "Área 3" no DMS-01 |
| G1 | Avisar só ≥20 km/h (distração) e ≥50 km/h (prejuízo) (EN 1.1) | **Parcial**: velocidade só por telemetria opcional; celular ignora "parado" | `context.py:31-66`; `engine.py:124` | Fonte de velocidade (DMS-13, pergunta ao Matheus) |
| G2 | Sensibilidade não ajustável pelo motorista (EN 1.1) | **Não se aplica no teste**; na caixa há `--mute` | `run_monitor.py:118` | Perfil de frota sem mudo nem ajuste acessível ao motorista (spec 005) |
| O1 | Avisar em ≤10 s quando não funciona (EN 1.1.1.2) | **Parcial**: `rosto_nao_detectado` e `olhos_nao_visiveis` aos 10 s, mas **só no registro**, sem som nem texto ao motorista | `drowsiness.py:67`, `399-409`; `engine.py:42`, `241-250` | DMS-04 |
| O2 | Óculos claros funcionam; escuros <15%: informar (EN 1.1.1.2) | **Parcial**: óculos escuros por luminância olho/bochecha + contraste | `visibility.py:12-20`, `73-98` | Reflexo na lente: `glare_fraction` é calculado e **não usado** (`face.py:163`, `310`) → DMS-07 |
| O3 | Luz 1 a 100.000 lux | **Não** com webcam RGB à noite | `pupil.py:31-65` (detecta IR) | Câmera NoIR + LEDs 940 nm (DMS-22) |
| O4 | Barba longa funciona; máscara, boné e franja: informar | **Não testado** | — | Bocejo com boca tapada (DMS-16); conjunto de teste |
| D1 | Fitzpatrick 1–6, abertura palpebral 6–12 mm, 16–80 anos | **Parcial**: perfil por motorista normaliza a abertura | `eyes.py:66-90`, `135-208`; `calibration.py:94-170` | Gravações diversas (§4.5) |
| D2 | Falar não pode gerar alerta | **Parcial**: bocejo exige 2 s | `drowsiness.py:50-52`, `385-397` | SIN-04 da spec 011 |
| W1 | Aviso imediato; micro/sono mais urgente que distração | **Parcial** | `driver_monitor.py:390-391`; `alarm.py:100` | DMS-04 |
| P1 | Circuito fechado, sem biometria (DDAW 2.3) | **Sim**: só números, nenhuma imagem | `engine.py:49` (`PRIVATE_KEYS`) | Manter; os campos novos entram com a mesma regra |
| N5 | Olhar fora da via >2 s dobra o risco (Klauer; NHTSA) | Só para celular | `phone.py:10-11`, `78` | Balde AttenD de 2 s como nível "atenção" (DMS-01) |

---

## 2. Distração visual pelo olhar e pela cabeça

### 2.1 O que já existe e serve de base

- **Íris em relação ao olho:** `gaze_x` e `gaze_y` em meias larguras do olho, + = direita e para baixo na imagem
  (`face.py:172-190`, campos `302-303`). Hoje só alimentam a entropia e as sacadas (`activation.py:171-182`) e o
  "olhando o celular" (`phone.py:390-400`).
- **Ângulo do olho:** `eye_angle = asin(1,25 × deslocamento)` (`activation.py:71`, `123-124`).
- **Olhar combinado aditivo** (cabeça + olho) já é usado para as células da entropia: `yaw + eye_h`, `pitch + eye_v`
  (`activation.py:182`).
- **Pose:** pitch positivo = cabeça baixa; yaw positivo = rosto virando para a direita da imagem (`face.py:10-12`,
  `rotation_to_euler`). Com a câmera de frente para o motorista e sem espelhar o quadro (nenhum `cv2.flip` no
  `caixa/`), **yaw positivo = motorista olhando para a esquerda dele** (lado do espelho do motorista no Brasil).
- **Base da calibração:** `pitch_baseline` e `yaw_baseline` = mediana dos 5–10 min (`calibration.py:102-107`).

Evidência de que olho + cabeça é necessário: em zonas de olhar, só a cabeça deu 79,8% de acerto ponderado; com olho e
íris, 94,9% (Tawari, Chen & Trivedi, 2014, [TRID](https://trid.trb.org/View/1349594)). O Euro NCAP exige *lizard*.

### 2.2 Fórmulas propostas

**(a) Ângulos do olho dentro da cabeça** (por quadro, olho aberto ≥0,6 e íris ≥10 px, como `activation.py:65-68`):

```
φh = asin(clip(k · (gaze_x − gx0), −1, 1))      k = 1,25 (activation.py:71); refinado na calibração guiada
φv = asin(clip(k · (gaze_y − gy0), −1, 1))      gx0, gy0 = mediana da íris olhando a frente
```

**(b) Direção do olhar na câmera** (forma exata; a aditiva vale até ~20°):

```
R  = M[:3,:3] da matriz de transformação facial, com as colunas normalizadas
d_olho = (sin φh · cos φv,  sin φv,  cos φh · cos φv)      vetor no referencial da cabeça
d = R · d_olho
yaw_g   = atan2(d_x, d_z)          pitch_g = asin(d_y)
aproximação: yaw_g ≈ yaw + φh,  pitch_g ≈ pitch + φv       (a mesma de activation.py:182)
```

> [!note] Hipótese, confirmar
> O sinal de `d_olho` precisa bater com a convenção do `rotation_to_euler` (`face.py`): conferir girando uma foto em 3D
> como no erro 7 da nota `07`. A matriz do MediaPipe usa uma câmera virtual de **63° de campo vertical**
> (`face_geometry_from_landmarks_graph.cc:71`, [código](https://github.com/google-ai-edge/mediapipe/blob/master/mediapipe/tasks/cc/vision/face_geometry/face_geometry_from_landmarks_graph.cc)),
> não a lente real: o ângulo absoluto tem viés, mas a **variação em relação à "frente"** é o que importa.

**(c) "Frente" do motorista = moda do olhar** (como o PRC):

```
histograma 2D de (yaw_g, pitch_g) em células de 2°, com decaimento exponencial (meia-vida 10 min)
só quadros com rosto, olho aberto e (se houver telemetria) velocidade ≥ 20 km/h
centro (yaw_c, pitch_c) = célula de maior peso, refinada pela média ponderada da vizinhança 3×3
Δyaw = yaw_g − yaw_c      Δpitch = pitch_g − pitch_c     (Δpitch > 0 = olhando para baixo)
```

Vantagem sobre a mediana da calibração (`calibration.py:102-103`): a moda ignora olhadas ao espelho e ao painel, e se
recentra quando o motorista ajusta o banco. A mediana continua servindo de valor inicial.

**(d) Zonas padrão** (Brasil, volante à esquerda; ângulos relativos à frente; **todos hipótese**, ajustáveis por
veículo):

| Zona | Δyaw | Δpitch | Tipo |
|---|---|---|---|
| Via (FRD) | −25° a +25° | −10° a +12° | via |
| Espelho do motorista | +35° a +70° | −15° a +15° | ligada à direção |
| Retrovisor interno | −15° a −35° | −20° a −5° | ligada à direção |
| Espelho do passageiro | −50° a −80° | −15° a +15° | ligada à direção |
| Painel (cluster) | −12° a +12° | +12° a +30° | ligada à direção |
| Central multimídia | −20° a −50° | +15° a +35° | não ligada |
| Colo / joelho (Área 3) | qualquer | ≥ +30° | não ligada |
| Fora (janela, passageiro, trás) | resto | resto | não ligada |

Histerese de 3° na borda e transição de 2 quadros (evita "pisca-pisca" na fronteira). O tempo do olhar conta desde o
início da transição (ISO 15007).

**(e) Calibração guiada de zonas** (opcional, 30 s no app de teste e na instalação): "olhe para o espelho esquerdo,
retrovisor, espelho direito, painel, rádio, colo", 3 s cada; guarda a mediana de (Δyaw, Δpitch) de cada alvo e o ganho
`k` do olho por regressão. Sem ela, valem as zonas padrão.

**(f) Regras de tempo** (rodam a cada quadro):

```
AttenD (nível "atenção", não alarme):
  B ∈ [0; 2 s];  na via há ≥0,1 s → B += Δt;  zona de direção → B parado no 1º segundo, depois B −= Δt;
  não ligada → B −= Δt;  B = 0 → "atencao_visual"

Distração longa (Euro NCAP 1.2.1):
  olhar contínuo fora da via em zona NÃO ligada à direção ≥ T_LGA = 3,0 s → evento distracao_longa + aviso
  zona ligada à direção (espelho, painel): só registra; aviso só se ≥ 6 s (hipótese, para não triplicar alertas)

VATS (Euro NCAP 1.2.2):
  A = soma dos olhares em zonas não ligadas nos últimos 30 s
  A zera quando o olhar fica na via ≥ T_reset = 2,0 s seguidos (secundária)
  A ≥ 10 s → evento distracao_repetida + aviso

Área 3 / ADDW (secundária):
  Δpitch ≥ 30° contínuo por 3,5 s (≥50 km/h) ou 6 s (20–50 km/h); +1,5 s com óculos escuros ou olhos não visíveis

Sem resposta (Euro NCAP 1.3.5):
  depois de um aviso de distração, olhar não volta à via em 3 s → nao_responsivo (nível 5, mesmo do olho fechado 6 s)
```

**(g) Modo degradado (óculos escuros, olhos tapados):** sem íris, vale só a cabeça (*owl*): a mesma regra com
`φh = φv = 0` e limites +1,5 s, como o "não nominal" do ADDW. O Euro NCAP chama isso de sistema degradado (definições).

### 2.3 Olhar para baixo não é olho fechado (risco de alarme falso hoje)

Olhando para baixo (colo, celular), a pálpebra desce e a fenda palpebral estreita; o olho continua vendo
(patente RE39539: o olho "ainda vê por uma fenda estreita no olhar para baixo", com PERCLOS medido de 75–80%;
[USPTO](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/RE39539)). No RotaGuard:
- o EAR cai; a regra de dois sinais usa `max` (`eyes.py:178-182`) e a de três usa a mediana (`eyes.py:183-185`);
- o EAR só é descartado com pitch ≥25° da base (`eyes.py:28`, `156-157`). **Um olhar *lizard* para o colo com a cabeça
  parada não passa nesse filtro.**

Proteção proposta (DMS-03), no `OpennessModel.openness` (`eyes.py:145-186`):
```
olhando_para_baixo = (eyeLookDownLeft+Right)/2 ≥ base + 0,35  E  (OCEC aberto ≥ 0,6  OU  íris com altura visível ≥ 40%)
se olhando_para_baixo: abertura = None, fonte = "olhar_para_baixo"  (não vira piscada, PERCLOS nem microssono)
                      e o quadro conta como zona "colo" no módulo de distração
```
`eyeLookDown*` já chega no dicionário `scores` (`face.py:262`) e é descartado hoje.

### 2.4 Velocidade

Sem velocidade, todo aviso de distração toca também no pátio e no semáforo. O Euro NCAP só exige aviso a ≥20 km/h e o
ADDW ativa acima de 20 km/h. Hoje a velocidade só vem de um arquivo de telemetria opcional (`context.py:31-66`).

> [!note] Conflito com o PRD
> O PRD tira "Localização e GPS" do escopo (§5). Um GPS USB lido **só para velocidade**, descartando a posição, ou o
> OBD-II, ou uma IMU, resolveriam. Decisão do Matheus (pergunta P1 no fim). Até lá: no app de teste, avisos de distração
> ligados; na caixa, opção "sem velocidade = sempre andando" registrada no log.

---

## 3. Sinais faciais de fadiga além do EAR

### 3.1 O que o script já calcula e joga fora (aproveitar primeiro, custo quase zero)

| Dado | Onde nasce | Uso hoje | Como aproveitar |
|---|---|---|---|
| **50 dos 52 blendshapes** | dicionário `scores`, `face.py:262` | só `eyeBlink*` (`263-264`) e `jawOpen` (`295`) | Periocular (spec 011), `eyeLookDown/Up/In/Out*` (olhar e DMS-03), `mouthPucker` e `noseSneer` (Vural 2010, só registro), `eyeSquint*` (sol e sorriso) |
| **roll** | `face.py:268`, `299` | nenhum módulo | Cabeça inclinada (spec 011, SIN-10); Vural 2010: *head roll* A' 0,78 |
| **mar** (abertura da boca pela geometria) | `face.py:258-260`, `296` | nenhum | Reserva do bocejo quando faltar blendshape; `jawOpen` alto com `mar` baixo sugere boca tapada ou barba (hipótese) |
| **glare_fraction** | `face.py:163`, `310` | nenhum | Reflexo nos óculos: tirar peso do EAR e da íris (DMS-07) |
| **Translação da matriz facial** (cm, câmera virtual) | `face.py:268` lê só a rotação | nenhum | Distância cabeça-câmera e deslocamento lateral: "inclinação do corpo" do Euro NCAP e "motorista fora da posição" (DMS-18) |
| **z dos 478 pontos** | `face.py:249` lê só x, y | nenhum | Olhar 3D e qual olho está mais perto (hipótese, baixa prioridade) |
| **gaze_x, gaze_y** | `face.py:185-186`, `302-303` | entropia, sacadas e "olhando celular" | Base da distração (DMS-01/02) |
| **iris_diameter_px** | `face.py:187`, `304` | só como filtro | Distância pela íris (11,7 mm), mais estável que a largura do rosto |
| **pupil_ratio** | `face.py:189-193` (só IR) | índice de ativação (`activation.py:165-169`) | Nada novo para sono: sem base de luz estável no carro, o teste de pupila em sonolência não se aplica (hipótese) |
| `profile.blink_rate_per_min`, `blink_duration_p90_s` | `calibration.py:152-154` | nenhum | Frequência de piscadas vs base; fração de piscadas acima do p90 da pessoa (DMS-06) |
| `profile.blink_opening_avr_median_s` | `calibration.py:163-167` | só z-score (`baseline.py:28`) | "Reabertura mais lenta" na regra (Johns: AVR da reabertura também sobe) |
| Lado da mão (*handedness*) | `phone.py:191-192` descarta | nenhum | Saber qual mão segura o celular; mão do lado da janela na orelha (hipótese) |
| Células do olhar a 5 Hz | `activation.py:178-182` | entropia | PRC e desvio do olhar (Victor 2005) sem custo (DMS-12) |

### 3.2 Sinais, evidência, medida e custo

| Sinal | Evidência | Como medir com o que temos | Custo | Recomendação |
|---|---|---|---|---|
| PERCLOS P80 | Wierwille 1994; Dinges 1998 (já citado em `eyes.py:5`). Revisão de 2019: duração da piscada e PERCLOS são os mais robustos ([Cori et al.](https://findanexpert.unimelb.edu.au/scholarlywork/1389995-narrative-review--do-spontaneous-eye-blink-parameters-provide-a-useful-assessment-of-state-drowsiness%3F)) | Já existe (`drowsiness.py:104-144`, `474-479`) | 0 | Manter |
| Duração da piscada | Caffier et al. 2003: duração sobe, frequência não (via [Watling & Smith, 2013](https://research.usq.edu.au/download/061ee5f254074a2db3f35720d30aaeaf5868b2f4db973765de29df44d2d13d6f/374449/Watling%26Smith%202013%20In%20the%20blink%20of%20an%20eye.pdf)); Ingre 2006 | Já existe, a meia amplitude (`eyes.py:211-233`) | 0 | Manter; exige ≥24 fps (`drowsiness.py:46`) |
| **Atraso/tempo de reabertura** | Schleicher et al. 2008 (129 pessoas): duração, **atraso da reabertura**, intervalo entre piscadas e velocidade padronizada do fechamento foram os melhores indicadores ([Ergonomics](https://www.ingentaconnect.com/content/10.1080/00140130701817062)) | Do traço que já existe (`eyes.py:244-260`): `t_min` (menor abertura) → `fechamento = t_min − início`, `reabertura = fim − t_min` | Mínimo | **Fazer** (DMS-06) |
| AVR fechamento e reabertura | Johns 2003/2005; Optalert põe a **média** do AVR do fechamento em 1º e o **desvio-padrão** em 2º ([patente](https://patents.google.com/patent/US7791491)) (fonte do fabricante) | Já existe a média (`drowsiness.py:432-437`, `466-472`); falta o desvio e a reabertura na regra | Mínimo | Fazer junto do DMS-06; só ≥28 fps (`eyes.py:37`) |
| Frequência de piscadas | Mista: Schleicher (intervalo é indicador), Caffier (frequência não mudou) | Já há contagem (`drowsiness.py:419-421`) e base (`calibration.py:154`) | 0 | Só complementar, nos dois sentidos |
| Cabeceio (pitch) | Já fundamentado em `drowsiness.py:11-12` | `NodTracker` (`drowsiness.py:151-206`) | 0 | Somar pico de velocidade angular (°/s) e "olho fechado no cabeceio" como reforço (hipótese) |
| **Roll da cabeça** | Vural 2010 (11 pessoas, simulador): *head roll* A' 0,78 entre sonolência moderada e aguda ([ICPR](https://research.sabanciuniv.edu/id/eprint/14818/1/esra_icpr2010.pdf)) | `roll` já calculado e descartado | 0 | Spec 011 (cabeça inclinada) |
| `eyeBlink` (AU45) | Vural 2010: A' 0,83 (melhor) | Já usado | 0 | Manter |
| `eyeSquint` (AU7) | Vural 2007: AU7 **caiu** no minuto antes de dormir (A' 0,86); Vural 2010: A' 0,72 | `scores["eyeSquintLeft/Right"]` | 0 | Guarda (sol e sorriso) e registro; nunca gatilho |
| `browOuterUp`/`browInnerUp` (AU2/AU1) | Vural 2007: sobrancelha erguida "para manter o olho aberto" (A' 0,81), com grande variação entre pessoas ([PDF](https://mplab.ucsd.edu/46/media/vesra.pdf)) | `scores` | 0 | Spec 011, só em relação à calibração |
| `browDown` (AU4) | Vural 2007: caiu (A' 0,79) | `scores` | 0 | Só registro |
| `mouthPucker` (AU18), `noseSneer` (AU9) | Vural 2010: A' 0,82 e 0,70 | `scores` | 0 | **Só registro** para validação; sem gatilho (amostra pequena, simulador) |
| `jawOpen` (bocejo) | Jie 2018; Giganti 2010; Vural 2007 (menos bocejo no minuto antes do sono) | Já existe (`drowsiness.py:385-397`) | 0 | Spec 011 (evento por bocejo) |
| Bocejo tapado pela mão | Jie 2018 aponta a perda do bocejo tapado | Mão na faixa da boca (hoje excluída em `face_touch.py:19-20`, `51`) + `jawOpen` subindo antes de a mão chegar | Baixo | Complementar (DMS-15) |
| `eyeLookDown/Up/In/Out` | Não é sinal de fadiga; é olhar | `scores` | 0 | DMS-03 e reforço do olhar quando a íris falha |
| `eyeWide` (AU5) | Sem evidência de sono | `scores` | 0 | Só registro |
| "Olhar vidrado" | **Cuidado.** Privação de sono **aumentou** a entropia estacionária do olhar, reduziu a taxa de fixação e a entropia previu saída de faixa (Shiferaw et al. 2018, 9 pessoas, pista fechada, [PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5797225/)). PRC ↑ e desvio do olhar ↓ marcam **carga cognitiva** (Victor 2005) | Células a 5 Hz já existem (`activation.py:182`, `203-209`) | Mínimo | PRC e desvio do olhar no registro (DMS-12) |
| Velocidade de pico das sacadas | Caiu depois de 1 noite sem dormir ([Sleep 2005](https://pubmed.ncbi.nlm.nih.gov/16268380)) | **Não mede a 30 fps**: subamostragem derruba o pico, mais em sacadas pequenas ([Mack et al. 2017](https://link.springer.com/article/10.3758/s13428-016-0848-4)); 60 Hz só para >10° | — | **Não fazer** com webcam; o código já conta só sacadas grandes (`activation.py:72-79`) |
| Olheiras | Ver spec 011, decisão 5 | — | — | Fora (concordo com a spec) |

> [!note] Conflito com o código
> `activation.py:38-44` conta a entropia de transição **acima** do normal como sinal de ativação atípica. Shiferaw 2018
> mostra a entropia do olhar **subindo com a privação de sono**. A guarda atual é `drowsiness_level ≥ 1`
> (`activation.py:297-298`), mas o olhar pode mudar antes de PERCLOS e piscadas. Proposta (DMS-12): exigir também
> ausência de piscadas longas e de PERCLOS acima da base para a entropia contar como ativação, e registrar o conflito na
> nota `03 - Ativacao...` da vault.

---

## 4. Robustez e qualidade do sinal

### 4.1 Filtro One Euro: o MediaPipe **já filtra** os pontos

No modo VIDEO/LIVE_STREAM com `num_faces = 1` (o caso do RotaGuard, `face.py:221-222`), o Face Landmarker aplica um
filtro One Euro nos pontos: `min_cutoff = 0,05`, `beta = 80`, `derivate_cutoff = 1,0`
(`face_landmarks_detector_graph.cc:156-167`; ligado só em modo de fluxo e com um rosto, `face_landmarker_graph.cc:448-460`;
[código](https://github.com/google-ai-edge/mediapipe/blob/master/mediapipe/tasks/cc/vision/face_landmarker/face_landmarks_detector_graph.cc)).
A documentação confirma: "Smoothing is only applied when num_faces is set to 1"
([guia](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker)).

Consequências:
- **Não pôr outro One Euro antes do EAR e das piscadas.** Filtrar de novo atrasa a pálpebra e infla duração e AVR.
- O filtro interno pode já alongar um pouco a piscada medida. Conta de ordem de grandeza (hipótese): pálpebra andando
  10 px em 100 ms num quadro de 640 px → corte ≈ 0,05 + 80 × 0,156 ≈ 12,5 Hz → α ≈ 0,72 a 30 fps (28% de atraso por
  quadro). **Medir:** rodar `ferramentas/avaliar_piscadas.py` no mesmo vídeo em modo VIDEO e IMAGE e comparar a duração
  (DMS-14).
- **Onde um One Euro próprio ajuda** (Casiez, Roussel & Vogel, CHI 2012, [página](https://gery.casiez.net/1euro/)):
  `α = 1 / (1 + τ/Te)`, `τ = 1/(2π·fc)`, `fc = min_cutoff + β·|dx̂|`; ajuste: β = 0 e `min_cutoff` ≈ 1 Hz parado, depois
  subir β até sumir o atraso nos movimentos rápidos.
  - **pose (yaw, pitch, roll) para as zonas** (3 números; `min_cutoff` ≈ 1 Hz, β ≈ 0,05 em graus, hipótese);
  - **vértices das ROIs do cardio** (`min_cutoff` ≈ 0,3 Hz): ROI tremendo é ruído no rPPG (hipótese);
  - **desenho da malha** só se ainda tremer na tela (a malha já sai filtrada; o tremor visível costuma vir da escala do
    desenho).

### 4.2 Óculos, reflexo e óculos escuros

- Hoje: óculos escuros = olho ≤45% da luminância da bochecha e contraste ≤18 por 1,5 s (`visibility.py:12-20`).
- **Reflexo** em óculos claros (o Euro NCAP exige funcionar com >70% de transmitância): `glare_fraction` > ~2% da
  região do olho (hipótese) → tirar o EAR da combinação naquele quadro, usar OCEC + `eyeBlink`, marcar `reflexo_oculos`
  no registro (DMS-07).
- **Infravermelho:** muitos óculos escuros deixam passar IR (`visibility.py:6`). Com 940 nm o sol interfere menos
  (absorção da água na atmosfera), mas o silício enxerga ~metade do que em 850 nm
  ([Commonlands](https://commonlands.com/blogs/technical/nir-imaging-machine-vision)). Transmitância de lentes em 940 nm
  não foi achada: medir com os óculos dos motoristas (DMS-22).

### 4.3 Luz ruim e taxa de quadros

- O Face Mesh piora com luz baixa, ruído e movimento, com mais tremor (model card, "Limitations",
  [PDF](https://storage.googleapis.com/mediapipe-assets/Model%20Card%20MediaPipe%20Face%20Mesh%20V2.pdf)).
- Webcam com pouca luz aumenta a exposição e **derruba o fps** (hipótese comum em webcams UVC) → a duração e o AVR se
  desligam abaixo de 24/28 fps (`drowsiness.py:46`, `eyes.py:37`). No app de teste: mostrar "luz baixa: medidas de
  piscada desligadas" quando o fps cair, em vez de silêncio.

### 4.4 Rosto parcial, boné, máscara, barba e ângulo da câmera

- Model card do Face Mesh V2: **não serve** para rosto virado >80°, com menos de 50% visível ou longe demais para o
  recorte de 192×192; inclinado da vertical "mais de 8°" (está escrito assim; provável erro de digitação para 80°,
  hipótese). Uso pretendido: AR, "not intended for human life-critical decisions" — registrar isso no RIPD e nos termos.
- **Boné:** a aba faz sombra nos olhos de dia; o IR resolve (hipótese). **Franja:** "informar se não funciona".
- **Máscara:** boca some → `jawOpen` inválido. Proposta (DMS-16): luminância e contraste da faixa da boca vs bochecha,
  como os óculos, desligando o bocejo e avisando "boca coberta".
- **Barba longa:** o Euro NCAP exige funcionar. Risco no `jawOpen` (hipótese); testar.
- **Ângulo:** o código já usa só o olho mais visível quando um tem <70% da largura do outro (`face.py:67-75`) e ignora o
  olho com yaw >30° da base (`eyes.py:26`). Recomendação de montagem: câmera com **≤20° de yaw e ≤20° de pitch** em
  relação ao rosto parado. Coluna do volante = melhor vista, mas o volante tapa (Euro NCAP testa a mão às 12 h);
  retrovisor e coluna A evitam o volante, com ângulo mais oblíquo e mais distância
  ([patentes e notas de fabricante, secundária](https://knowledge.powerfleet.com/hc/en-us/articles/22269433139474-When-do-we-recommend-a-dash-mount-vs-pillar-mount-driver-camera)).
  Para caminhão e ônibus, painel à esquerda do volante, baixo, é o compromisso mais provável (hipótese; testar no
  protótipo, DMS-25).

### 4.5 Pele escura e viés (o que dizem os model cards)

| Modelo | Avaliação | Resultado |
|---|---|---|
| Face Mesh V2 (pontos) | 1.700 imagens de 17 regiões; gênero e Fitzpatrick 1–6 | Erro (MAE/distância interocular) de **2,49% a 2,90%** entre tons de pele no rastreamento; diferença 0,41 p.p., abaixo do critério de 2,56%. Tom 1 (2,90%) e 6 (2,77%) foram os piores, com só 1,5% e 6,3% da amostra |
| Blendshape V2 | 511 rostos multivista, Monk 1–10 | MAD entre 0,192 e 0,210 por tom; dentro de 1 desvio-padrão (critério do card) |

Fontes: [Face Mesh V2](https://storage.googleapis.com/mediapipe-assets/Model%20Card%20MediaPipe%20Face%20Mesh%20V2.pdf) ·
[Blendshape V2](https://storage.googleapis.com/mediapipe-assets/Model%20Card%20Blendshape%20V2.pdf).

Leitura: o viés dos **pontos** é pequeno nas condições do card (celular, rosto de frente). O risco maior está na **luz**
(pele escura + pouca luz RGB = menos sinal) e no **rPPG**: a frequência cardíaca pela câmera cai bastante no tom mais
escuro ([Nowara, McDuff & Veeraraghavan, CVPRW 2020](https://openaccess.thecvf.com/content_CVPRW_2020/html/w19/Nowara_A_Meta-Analysis_of_the_Impact_of_Skin_Tone_and_Gender_CVPRW_2020_paper.html)).
O cardio já mostra "sinal fraco" (spec 022); manter assim e incluir tons 5–6 no conjunto de validação.

### 4.6 Pixels no olho: por que a pupila não sai na webcam

Câmera Module 3 NoIR padrão (66° horizontal, nota `11` da vault) a 70 cm: largura vista = 2 × 0,70 × tan 33° ≈ 0,91 m.

| Largura do quadro | px/mm | Distância entre olhos (63 mm) | Íris (11,7 mm) | Pupila? (`pupil.py:22` pede ≥24 px) |
|---|---|---|---|---|
| 640 | 0,70 | 44 px | **8 px** | Não |
| 1280 | 1,41 | 89 px | 16 px | Não |
| 1920 | 2,11 | 133 px | **25 px** | No limite |

Webcam de notebook (~70° a 55 cm, hipótese) em 640 px: íris ≈ 10 px. Conclusão: o EAR e os blendshapes vão bem em
640×480; a pupila (sinal mais forte do módulo 2) só com **1080p e recorte dos olhos em resolução cheia** (DMS-20). Modos
de vídeo da Camera Module 3: 1080p50, 720p100, 480p120 ([Adafruit](https://www.adafruit.com/product/5659), listagem do
revendedor).

---

## 5. Desempenho

### 5.1 Medido nesta máquina (19/10/2026)

Script `scratchpad/bench/bench_mp.py`, MediaPipe 1.0.1, quadro sintético 640×480 com rosto, 150 repetições.
**AMD Ryzen 5 5625U (6 núcleos, 12 threads) com a CPU a 96% de carga por outros programas** (Firefox, VS Code, outros
agentes): números **pessimistas**.

| Chamada | Mediana | p95 |
|---|---|---|
| Face Landmarker VIDEO, blendshapes + matriz (config atual, `face.py:217-228`) | 39,8 ms | 70,1 ms |
| Face Landmarker VIDEO sem blendshapes | 29,0 ms | 53,2 ms |
| Face Landmarker IMAGE (detector todo quadro) | 27,3 ms | 45,9 ms |
| Hand Landmarker VIDEO, 2 mãos, quadro inteiro | 54,3 ms | 83,7 ms |
| EfficientDet-Lite0 float16 (recorte 440×480) | 101,6 ms | 126,9 ms |
| EfficientDet-Lite0 int8 (mesmo recorte) | 86,7 ms | 107,8 ms |
| OCEC, 2 olhos | 3,35 ms | 8,19 ms |
| `cvtColor` + `mp.Image` | 0,20 ms | 1,79 ms |

A nota `06` da vault registra 26 fps e 11 ms por quadro lendo vídeo, sem a carga de hoje. Pontos práticos:
- Os blendshapes custaram ~10 ms a mais aqui. Valem: são a fonte do olhar para baixo, do periocular e do bocejo.
- Aqui o int8 foi **mais rápido** que o float16 em x86, o contrário do comentário de `phone.py:86` (73 × 106 ms). Com a
  máquina carregada não dá para concluir: **remedir com a máquina livre** antes de mexer.
- A 40 ms por quadro o rosto fica em ~25 fps: **abaixo dos 28 fps** do AVR. Prioridade de desempenho = manter o rosto em
  30 fps e jogar o resto para fora do caminho dele.

### 5.2 GPU, modos e agendamento

- **GPU:** "GPU support is currently limited to Ubuntu platforms" (docstring de `BaseOptions` no MediaPipe 1.0.1
  instalado no `.venv`). **Windows: só CPU.** No Pi não há caminho documentado (hipótese: não usar).
- **VIDEO vs LIVE_STREAM** ([guia Python](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker/python)):
  os dois rastreiam o rosto e evitam rodar o detector a cada quadro; VIDEO bloqueia e devolve o resultado; LIVE_STREAM
  devolve por callback e **ignora o quadro novo se ainda está ocupado**. Para o rosto, **manter VIDEO**: a ordem dos
  quadros e o carimbo de tempo importam para piscada e PERCLOS.
- **Thread de captura com "último quadro":** hoje a leitura e a análise são em série (`driver_monitor.py:421-462`). Se a
  análise fica mais lenta que a câmera, o buffer do driver entrega quadros velhos e a latência do alarme cresce
  (hipótese, depende do backend). Proposta (DMS-08): uma thread lê sem parar e guarda só o último quadro **com o
  instante da captura**; o loop analisa o mais novo e passa esse instante para `process_frame` (hoje vai `None` e o
  `analyze` usa o relógio na hora da análise). No picamera2, usar o carimbo do sensor nos metadados (hipótese:
  `SensorTimestamp`).
- **Agendamento inteligente** (DMS-09):
  - rosto: todo quadro;
  - mãos: 4 Hz como hoje (`phone.py:42`), mas **no recorte do motorista** (hoje roda no quadro inteiro, `phone.py:186-193`);
  - celular: **1 Hz de base**, sobe para 4 Hz quando há mão perto do rosto ou do colo, olhar para baixo ou celular visto
    nos últimos 5 s.
- **Processo separado no Pi** para mãos e celular (`multiprocessing` + memória compartilhada), para usar outros núcleos
  sem disputar com o rosto. Se o MediaPipe solta o GIL na inferência, a thread atual (`phone.py:236-238`) já paraleliza
  (hipótese; medir no Pi).
- **Resolução:** 640×480 basta para rosto e mãos (o MediaPipe recorta o rosto e redimensiona para 256×256). Mais
  resolução só para os recortes dos olhos (§4.6).

### 5.3 Raspberry Pi 4/5 e acelerador

| Plataforma | O que é realista | Base |
|---|---|---|
| Pi 4 (CPU) | Malha de 468 pontos a **~10 fps** | Tutorial com medida ([Core Electronics](https://core-electronics.com.au/videos/pose-estimation-and-face-landmark-tracking-with-raspberry-pi-and-opencv)). Com blendshapes e celular, menos. A duração e o AVR ficariam desligados (<24 fps) |
| Pi 5 (CPU) | **15 a 25 fps** só no rosto; 10 a 15 com mãos e celular | **Hipótese** (A76 ~2–3× o A72). Não achei medida publicada; o projeto [dms-face](https://github.com/youssefmedhat4/dms-face) mira o Pi 5 mas só publica números de Intel (~54 fps) |
| Pi 5 + AI HAT+ (Hailo-8L, 13 TOPS) | Tabela do Hailo Model Zoo (batch 1): `face_landmarks_lite` **432 fps**, `scrfd_500m` 588, `efficientdet_lite0` 92, `yolox_tiny` 214, `nanodet_repvgg` 620, `ssd_mobilenet_v1` 356 | [Hailo Model Zoo](https://github.com/hailo-ai/hailo_model_zoo/blob/master/docs/public_models/HAILO8L/HAILO8L_facial_landmark_detection.rst) (medido num i5 com PCIe Gen3 x4; o Pi 5 tem PCIe x1: esperar menos) |
| Pi 5 + AI HAT+ 2 (Hailo-10H) | Visão "equivalente ao AI HAT+ de 26 TOPS", 8 GB próprios | [revendedor](https://www.welectron.com/Official-Raspberry-Pi-AI-HAT-2) (secundária) |

> [!note] Hipótese, confirmar
> O `face_landmarks_lite` do Hailo é a malha antiga de 468 pontos, **sem íris e sem blendshapes**. Migrar para o Hailo
> exige rodar o modelo de blendshapes (entrada 146×2 pontos, [guia](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker))
> e a íris à parte na CPU. É trabalho grande (DMS-23): só vale se o Pi 5 sem acelerador não segurar ~25 fps no rosto.

---

## 6. Detecção de celular

### 6.1 Estado da arte e o que o Euro NCAP mede

- O Euro NCAP mede **o olhar repetido em direção ao celular** (VATS), com o aparelho no colo, no joelho, no volante ou
  no suporte (§1.1). Detectar o aparelho é reforço; o núcleo é **olhar para baixo/colo de forma repetida**.
- Sistemas comerciais e patentes juntam: aparelho perto da cabeça + mão perto do aparelho + fala (áudio) + direção do
  olhar, para cortar falso positivo (patentes US 9.714.037 e US 11.488.398, secundária). Não achei benchmark público de
  2024–2025 para "mão vazia na orelha".
- O model card do Hand Landmarker põe "mão segurando objetos" fora do escopo (já tratado em `phone.py:68-71`).
- Dados: o **DMD** (Vicomtech; 41 h, RGB + profundidade + IR, 37 motoristas, rótulos de falar ao celular e digitar) é
  liberado para **uso acadêmico e científico** por formulário ([DMD](https://dmd.vicomtech.org/)). Treinar modelo
  comercial com ele exige conferir a licença recebida (hipótese: não permite).

### 6.2 Modelos leves e licença (conferida no GitHub em 19/10/2026)

| Modelo | Licença | Observação |
|---|---|---|
| EfficientDet-Lite0/1/2 (MediaPipe, atual) | Apache-2.0 | COCO; classe "cell phone" fraca em objeto pequeno |
| YOLOX (Megvii) | **Apache-2.0** | Nano/Tiny bons para CPU; `yolox_tiny` no Hailo |
| NanoDet / NanoDet-Plus | **Apache-2.0** | Muito leve em ARM |
| PicoDet (PaddleDetection) | **Apache-2.0** | Exportar do Paddle para ONNX dá trabalho |
| RTMDet (MMDetection) | **Apache-2.0** | |
| DAMO-YOLO | **Apache-2.0** | |
| RT-DETR (lyuwenyu) | **Apache-2.0** | Pesado para CPU do Pi |
| D-FINE | **Apache-2.0** | Pesado para CPU do Pi |
| DEIM (Intellindust) | **Apache-2.0** (arquivo LICENSE) | |
| RF-DETR (Roboflow) | **Apache-2.0 só nos tamanhos N, S, M e L**; A, F, P, XL e 2XL são **PML 1.0** | Base DINOv2, ~30 M de parâmetros: pesado para o Pi |
| YOLO-NAS (Deci) | Código Apache, **pesos com licença não comercial** | Evitar |
| YOLOv5/v8/v11 (Ultralytics), YOLOv10 (THU-MIG), YOLOv12 | **AGPL-3.0** | Proibido (RNF-10) |
| YOLOv9, YOLOv6 | **GPL-3.0** | Evitar |

Fontes: API de licença do GitHub para cada repositório; [README do RF-DETR](https://github.com/roboflow/rf-detr);
[licença dos pesos YOLO-NAS](https://github.com/Deci-AI/super-gradients/blob/master/LICENSE.YOLONAS.md).
Os pesos pré-treinados no COCO herdam dúvidas da licença das imagens do COCO: perguntar ao advogado junto do RIPD
(hipótese).

### 6.3 Proposta para o RotaGuard

1. **Já (sem modelo novo):** "olhar repetido para o colo" pelo módulo de distração (DMS-01), com ou sem o aparelho
   visto. É o que o Euro NCAP mais cobra e não depende do detector.
2. **Já, com dados do próprio notebook:** classificador do **recorte da mão** (a mão vem do Hand Landmarker): "mão
   vazia" × "mão com celular", MobileNetV3-small (Apache-2.0) ou um modelo de ~100 KB. Ataca direto o falso positivo
   da mão vazia na orelha (spec 009, CEL-01/CEL-03), sem confiar no detector do COCO perto do rosto (DMS-10).
3. **Com a câmera IR:** reajustar um detector Apache (YOLOX-Nano ou NanoDet-Plus) com gravações da cabine em IR e
   classes `celular`, `celular_na_orelha`. Em 940 nm a tela do celular não brilha (a tela emite luz visível): o aparelho
   vira um retângulo escuro (hipótese), diferente do RGB do COCO (DMS-24).

---

## 7. Lista priorizada de melhorias

Esforço em horas com TDD (teste antes, ID do critério no nome do teste). Risco = risco de **alarme falso** que a
mudança traz ou tira. Spec sugerida: **026 · Distração visual pelo olhar** (DMS-01 a DMS-04, DMS-13, DMS-17) e
**027 · Qualidade do sinal e desempenho** (o resto); 011 continua sendo a dos sinais complementares.

### 7A. Dá para fazer agora, no notebook com webcam

| ID | Melhoria | Impacto | Esforço | Risco de alarme falso | Onde entra | Critério de aceite (testável) |
|---|---|---|---|---|---|---|
| **DMS-01** | **Distração visual**: zonas do olhar, balde AttenD (2 s), distração longa (3 s), VATS (10 s em 30 s, reset 2 s), Área 3, eventos `distracao_longa` e `distracao_repetida` com aviso | **Muito alto** (15 dos 25 pontos de DM do Euro NCAP; maior lacuna) | 14 h | Médio (cai com DMS-02 e DMS-13) | Novo `vision/distraction.py`; chamada em `engine.py` após `drowsiness.update` (`engine.py:117`); entra no risco como o celular (`risk.py:120-124`); cartão na tela (spec 023) | **DMS-01a** 4 s na frente + 3,2 s com Δyaw −45° (zona não ligada): 1 `distracao_longa` entre 3,0 e 3,1 s depois do início do olhar. **DMS-01b** 3,5 s no espelho do motorista: sem aviso, olhar registrado. **DMS-01c** olhares de 1,8 s a Δpitch +35° com 0,8 s na frente entre eles: `distracao_repetida` quando a soma passa de 10 s, com erro ≤ 0,2 s. **DMS-01d** mesmos olhares com 2,5 s na frente entre eles: nenhum evento. **DMS-01e** falar olhando a frente por 60 s: nenhum evento |
| **DMS-02** | **Frente automática** pela moda do olhar (PRC) + calibração guiada de zonas opcional (30 s) | Alto (sem isso as zonas erram) | 8 h | Reduz | Novo `vision/gaze.py`; campos `gaze_center_*` e `zonas` no `DriverProfile` (`eyes.py:66-90`) com padrão `None`; passo no app de teste | **DMS-02a** 70% do tempo em (12°, −5°) e 30% espalhado: centro a ≤ 2° em 60 s. **DMS-02b** deslocar tudo 10°: recentra em ≤ 120 s. **DMS-02c** perfil antigo sem os campos abre e usa as zonas padrão |
| **DMS-03** | **Olhar para baixo ≠ olho fechado** (`eyeLookDown` + OCEC + íris) | Alto (tira microssono falso olhando o colo; dá *lizard* para baixo) | 5 h | **Reduz** | `OpennessModel.openness` (`eyes.py:145-186`); `FaceMetrics.eye_look_down` (`face.py`, a partir de `scores`, `face.py:262`); máscara em `visibility.py:22-25` | **DMS-03a** 3 s com EAR a 35% do aberto, `eyeLookDown` 0,6 e OCEC 0,8: nenhum `microssono`, fonte `olhar_para_baixo`, quadro na zona colo. **DMS-03b** olho fechado de verdade (`eyeLookDown` 0,1, OCEC 0,1): `microssono` em 1,0 s ± 1 quadro |
| **DMS-04** | **Avisos por urgência**: sirene urgente (micro/sono/sem resposta), aviso de distração mais curto, aviso de celular, **sinal de "sem visão"** (som 1 vez por viagem + texto fixo) aos 10 s | Alto (Euro NCAP 1.1.1.2 e 1.4.2) | 5 h | Neutro | `alarm.py` (padrões no lugar de uma sirene, `alarm.py:18-45`, `trigger` em `100`); `driver_monitor.py:390-391` passa o nível | **DMS-04a** `microssono` toca o padrão urgente; `distracao_longa`, o de distração (sons diferentes por WAV/hash). **DMS-04b** óculos escuros por 10 s: 1 som "sem visão" e texto fixo; 2º episódio na mesma viagem: só texto |
| **DMS-05** | **Blendshapes no `FaceMetrics`** (periocular da spec 011 + `eyeLookDown/Up/In/Out`, `mouthPucker`, `noseSneer`, `eyeWide`) e as 52 colunas no `_quadros.csv` | Médio (base para validar tudo) | 4 h | Nenhum (só registro) | `face.py:262-316`; `ferramentas/analisar_video.py` | **DMS-05a** `scores` sintético: campos combinados como `combine_eyes` (`face.py:67-75`), `None` sem olho. **DMS-05b** o CSV tem as 52 colunas com nome do MediaPipe |
| **DMS-06** | **Dinâmica da piscada ampliada**: tempo de fechamento, **tempo de reabertura** (Schleicher), desvio do AVR, AVR de reabertura na regra, frequência vs base, fração acima do p90 da calibração | Médio-alto | 6 h | Baixo (entram como sinal leve) | `Blink` e `_eyelid_speeds` (`eyes.py:211-260`); `_window_details` e `_evaluate` (`drowsiness.py:414-508`) | **DMS-06a** piscada sintética a 30 fps com fechamento de 80 ms e reabertura de 300 ms: `reabertura_s` = 0,30 ± 0,04. **DMS-06b** abaixo de 28 fps: nenhum campo de velocidade na janela. **DMS-06c** reabertura mediana 1,4× a base por 5 min: motivo leve `reabertura_lenta`, nunca nível 2 sozinho |
| **DMS-07** | **Reflexo nos óculos** (`glare_fraction`) | Médio | 3 h | **Reduz** | `OpennessModel` (`eyes.py:159-186`); `face.py:163`; registro | **DMS-07a** `glare_fraction` 0,05: abertura sem o EAR, fonte sem `ear`. **DMS-07b** 0,0: igual a hoje |
| **DMS-08** | **Captura em thread com o último quadro** e carimbo da captura | Médio (latência do alarme, O1) | 4 h | Neutro | `driver_monitor.py:421-462`; `camera.py` | **DMS-08a** câmera falsa a 30 fps e análise falsa de 60 ms: idade do quadro analisado ≤ 50 ms em 95% (hoje cresce até o tamanho do buffer). **DMS-08b** o `timestamp` do `FaceMetrics` é o da captura |
| **DMS-09** | **Agendamento inteligente** de mãos e celular; mãos no recorte do motorista | Médio (fps do rosto ≥ 28) | 5 h | Neutro | `phone.py:42`, `174-193`, `240-248` | **DMS-09a** 10 s sem mão perto do rosto e sem olhar para baixo: ≤ 1,2 detecções de celular por s. **DMS-09b** mão chega à orelha: volta a 4 por s em ≤ 0,5 s. **DMS-09c** CEL-01 e CEL-02 continuam passando |
| **DMS-10** | **Classificador do recorte da mão** (vazia × com celular) para a orelha | Alto para o celular (spec 009) | 16 h + gravações | **Reduz** | `phone.py:121-138`, `299-318`; ferramenta de coleta em `ferramentas/` | **DMS-10a** nas gravações da spec 009 (mão vazia × aparelho): precisão ≥ 90% e sensibilidade ≥ 80% em "no ouvido" (metas sugeridas na spec 009) |
| **DMS-11** | **KSS no app de teste** (pergunta a cada 5 min, tecla 1–9) e ferramenta de sensibilidade no estilo DDAW | Alto (sem verdade de referência não há limiar) | 6 h | Nenhum | `caixa/app_teste.py`/`tela_teste`; novo `ferramentas/avaliar_kss.py` | **DMS-11a** sessão sintética com KSS 8 aos 20 min e `sonolencia` aos 22 min: sensibilidade 100%, atraso 2 min no relatório. **DMS-11b** sem resposta ao KSS em 30 s: registra "sem resposta", não "KSS 1" |
| **DMS-12** | **PRC, desvio do olhar e entropia estacionária** no registro; entropia só vale como ativação sem sinais de piscada lenta | Médio (corrige conflito do módulo 2) | 4 h | **Reduz** (ativação falsa no começo do sono) | `activation.py:188-213`, `272-303` | **DMS-12a** 60 s com 80% do olhar a ≤ 8° da moda: PRC = 0,80 ± 0,03. **DMS-12b** entropia z = +2,5 com piscada 1,2× a base: não conta como sinal de ativação |
| **DMS-13** | **Porta de velocidade**: distração ≥ 20 km/h e prejuízo ≥ 50 km/h quando houver velocidade; modo "sem velocidade" explícito no registro | Alto na caixa (alarme no pátio) | 3 h (+ fonte de velocidade) | **Reduz** | `context.py:46-77`; `engine.py:124`; `distraction.py` | **DMS-13a** telemetria 10 km/h + 4 s olhando o colo: sem aviso, olhar registrado. **DMS-13b** 30 km/h: aviso. **DMS-13c** sem telemetria: registro com `fonte_velocidade = "nenhuma"` |
| **DMS-14** | **Suavização certa**: One Euro só na pose (zonas) e nas ROIs do cardio; **medir** o efeito do filtro interno do MediaPipe na piscada (VIDEO × IMAGE) | Médio | 4 h | Reduz (pisca-pisca de zona) | Novo `vision/filtros.py`; `distraction.py`; `cardio.py`; `ferramentas/avaliar_piscadas.py` | **DMS-14a** degrau de 30° na pose: atraso ≤ 2 quadros; ruído de ±1° parado: saída ±0,3°. **DMS-14b** relatório VIDEO × IMAGE com a diferença de duração mediana no mesmo vídeo |
| **DMS-15** | **Bocejo tapado pela mão** | Baixo | 4 h | Baixo (só complementar) | `face_touch.py:46-58`, `98-104`; `drowsiness.py:385-397` | **DMS-15a** `jawOpen` sobe a 0,6 e a mão cobre a boca por 3 s: 1 `bocejo` com `tapado = true`. **DMS-15b** mão na boca sem boca abrindo antes (comer): nada |
| **DMS-16** | **Boca coberta (máscara)**: desliga o bocejo e avisa | Baixo-médio (Euro NCAP: informar) | 3 h | Reduz | `face.py` (faixa da boca); `visibility.py` | **DMS-16a** faixa da boca lisa e diferente da bochecha por 3 s: bocejo desligado e motivo `boca_coberta` |
| **DMS-17** | **Sem resposta pela distração**: olhar não volta à via 3 s após o aviso | Médio | 2 h | Baixo | `distraction.py`; `drowsiness.py:71-75` | **DMS-17a** aviso de distração + mais 3 s fora da via: `nao_responsivo` nível 5; voltou em 2 s: nada |
| **DMS-18** | **Postura** pela translação da matriz: distância e deslocamento lateral (inclinação do corpo, motorista fora da posição) | Baixo-médio | 3 h | Baixo | `face.py:266-268`; `FaceMetrics` | **DMS-18a** translação lateral sintética de 20 cm por 2 s: `fora_da_posicao`; 5 cm: nada |
| **DMS-19** | **Roteiro de verificação estilo SD-202** no app de teste: o app pede "olhe o colo 4 s", "feche os olhos 4 s" e mede o atraso do aviso | Alto para o pitch e para validar | 6 h | Nenhum | `caixa/tela_teste`; `ferramentas/` | **DMS-19a** roteiro gravado: relatório com atraso de cada aviso e "dentro de ±0,2 s" ou não |

### 7B. Depende do Pi, da câmera NoIR ou dos LEDs 940 nm

| ID | Melhoria | Impacto | Esforço | Risco | Onde entra | Critério de aceite |
|---|---|---|---|---|---|---|
| **DMS-20** | **Multirresolução**: captura em 1080p, MediaPipe em 640×360, recortes dos olhos em resolução cheia para OCEC e pupila | Alto para o módulo 2 (pupila) | 8 h | Neutro | `camera.py:80-111`; `face.py` (escala dos pontos); `pupil.py:68-126` | **DMS-20a** a 70 cm com Camera Module 3 em 1080p: íris ≥ 24 px e `pupil_quality = "ok"` em ≥ 80% dos quadros de olho aberto |
| **DMS-21** | **Perfil do Pi**: medir fps e latência no Pi 4 e no Pi 5, mãos e celular em processo separado, temperatura | Alto (RNF-01, RNF-02) | 8 h | Neutro | `driver_monitor.py:480-489`; spec 005 | **DMS-21a** rosto ≥ 10 fps no Pi 4 (RNF-02) e ≥ 24 fps no Pi 5 (hipótese de meta); latência câmera→som ≤ 1,5 s (O1) |
| **DMS-22** | **Validação em IR 940 nm**: MediaPipe, blendshapes e OCEC no infravermelho, de dia e de noite, com e sem óculos escuros; reajuste de `visibility.py` | Alto | 10 h + gravações | Reduz | `visibility.py:12-20`; `pupil.py:31-65` | **DMS-22a** 1 lux a 100.000 lux: rosto achado em ≥ 95% dos quadros; óculos escuros dos motoristas: medir a fração em que o olho continua medido |
| **DMS-23** | **Hailo-8L (opcional)**: rosto, detector de rosto e celular no acelerador; blendshapes e íris na CPU | Médio | 40 h | Neutro | `face.py` (novo analisador), `phone.py` | **DMS-23a** rosto ≥ 30 fps e mesmas saídas do `FaceMetrics` com erro do EAR ≤ 5% contra o MediaPipe na CPU |
| **DMS-24** | **Detector de celular reajustado** (YOLOX-Nano ou NanoDet-Plus, Apache) com gravações IR da cabine | Alto para o celular | 30 h + dados | Reduz | `phone.py:141-198` | **DMS-24a** nas gravações de teste: precisão ≥ 90% e sensibilidade ≥ 80% para celular na mão e no colo |
| **DMS-25** | **Posição da câmera**: comparar painel baixo à esquerda × coluna A × retrovisor no protótipo | Alto | 6 h | Reduz | Instalação (spec 005) | **DMS-25a** relatório com fração de quadros com rosto, EAR válido e íris ≥ 10 px em cada posição, com a mão às 12 h |
| **DMS-26** | **Cardio no IR** contra oxímetro (já na spec 022) | Baixo para segurança | — | Nenhum (fora do risco) | `cardio.py` | CAR-08 da spec 022 com gravação real |

### 7C. Ordem sugerida

1. DMS-05 → DMS-03 → DMS-02 → DMS-01 → DMS-17 → DMS-04 (a distração inteira, usando o que já é calculado).
2. DMS-08 → DMS-09 → DMS-14 (fps do rosto ≥ 28 e latência).
3. DMS-06 → DMS-07 → DMS-12 → DMS-11 → DMS-19 (qualidade da sonolência e verdade de referência).
4. DMS-10 (com as gravações da spec 009) e DMS-13 (quando houver fonte de velocidade).
5. Pi e IR: DMS-21 → DMS-22 → DMS-20 → DMS-25 → DMS-24 → DMS-23.

---

## 8. Perguntas para o Matheus

| # | Pergunta | Padrão até decidir |
|---|---|---|
| P1 | **Velocidade:** pode entrar um GPS USB lido **só para velocidade** (sem guardar posição), ou OBD-II, ou uma IMU? O PRD §5 tira GPS do escopo | Sem velocidade: avisos ligados, registro marca `fonte_velocidade = "nenhuma"` |
| P2 | Distração deve **tocar alarme** ou só registrar no começo? (Seeing Machines: separar espelho de distração evita triplicar os alertas) | Alarme só para distração longa e VATS em zona não ligada à direção |
| P3 | Posição da câmera no protótipo: painel baixo à esquerda, coluna A ou retrovisor? | Painel baixo à esquerda (hipótese) |
| P4 | Pi 4 (lista de compras da nota `11`) ou Pi 5 (recomendação de 14/09)? Afeta DMS-21 e DMS-23 | Medir no que chegar primeiro |
| P5 | Pode pedir KSS ao motorista no app de teste a cada 5 min (DMS-11)? | Ligado só no modo de validação |

## 9. Fontes

Primárias lidas:
- Euro NCAP, *Safe Driving – Driver Engagement Protocol* v1.2 (jul/2026): https://cdn.euroncap.com/cars/assets/Euro_NCAP_Protocol_Safe_Driving_Driver_Engagement_v1_2_ebce03a443.pdf
- Euro NCAP, *SD-202 Driver Monitoring Test Procedure* v1.2: https://cdn.euroncap.com/cars/assets/SD_202_Driver_Monitoring_Test_Procedure_v1_2_d3420cb629.pdf
- Model card Face Mesh V2: https://storage.googleapis.com/mediapipe-assets/Model%20Card%20MediaPipe%20Face%20Mesh%20V2.pdf
- Model card Blendshape V2: https://storage.googleapis.com/mediapipe-assets/Model%20Card%20Blendshape%20V2.pdf
- Face Landmarker (guia e Python): https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker · https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker/python
- Código do MediaPipe (filtro e câmera virtual): https://github.com/google-ai-edge/mediapipe/blob/master/mediapipe/tasks/cc/vision/face_landmarker/face_landmarks_detector_graph.cc · https://github.com/google-ai-edge/mediapipe/blob/master/mediapipe/tasks/cc/vision/face_landmarker/face_landmarker_graph.cc · https://github.com/google-ai-edge/mediapipe/blob/master/mediapipe/tasks/cc/vision/face_geometry/face_geometry_from_landmarks_graph.cc
- `BaseOptions` do MediaPipe 1.0.1 instalado (`.venv/Lib/site-packages/mediapipe/tasks/python/core/base_options.py:75-76`)
- Hailo Model Zoo, Hailo-8L: https://github.com/hailo-ai/hailo_model_zoo/tree/master/docs/public_models/HAILO8L
- Licenças (API do GitHub): YOLOX, NanoDet, PaddleDetection, RT-DETR, D-FINE, DEIM, RF-DETR, DAMO-YOLO, MMDetection, Ultralytics, YOLOv10, YOLOv12, YOLOv9, YOLOv6, super-gradients; https://github.com/roboflow/rf-detr ; https://github.com/Deci-AI/super-gradients/blob/master/LICENSE.YOLONAS.md
- Vural et al. 2010 (ICPR): https://research.sabanciuniv.edu/id/eprint/14818/1/esra_icpr2010.pdf
- Kircher & Ahlström 2010 (AttenD): https://pmc.ncbi.nlm.nih.gov/articles/PMC3242543
- One Euro: https://gery.casiez.net/1euro/

Secundárias ou só resumo:
- DDAW 2021/1341 (LawPlayer): https://lawplayer.com/eu/act/32021R1341 · ELI: https://eur-lex.europa.eu/eli/reg_del/2021/1341/oj/eng
- ADDW 2023/2590: https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=OJ%3AL_202302590 (não abriu) · https://www.atic-ts.com/brief-introduction-of-advanced-driver-distraction-warning-system-research-draft/ · https://seeingmachines.com/understanding-advanced-driver-distraction-warning-addw-systems/
- Seeing Machines, prevalência: https://seeingmachines.com/wp-content/uploads/2026/01/Lite-Paper_European-NCAP-Driver-State-Monitoring-Protocols-Prevalence-of-Distraction-in-Naturalistic-Driving.pdf
- NHTSA 2 s/12 s: https://www.nhtsa.gov/sites/nhtsa.gov/files/strickland-distraction_guidelines_03122012.pdf
- Klauer et al. 2006: https://www.nhtsa.gov/document/810594driverinattentionnearcrashcrashriskpdf
- Victor et al. 2005 (PRC): https://swov.nl/en/publicatie/sensitivity-eye-movement-measures-vehicle-task-difficulty · https://arxiv.org/pdf/2104.05677
- ISO/TR 21959-1: https://www.iso.org/standard/78088.html
- Tawari, Chen & Trivedi 2014: https://trid.trb.org/View/1349594
- Vural et al. 2007: https://mplab.ucsd.edu/46/media/vesra.pdf
- Schleicher et al. 2008: https://www.ingentaconnect.com/content/10.1080/00140130701817062
- Caffier et al. 2003, via Watling & Smith 2013: https://research.usq.edu.au/download/061ee5f254074a2db3f35720d30aaeaf5868b2f4db973765de29df44d2d13d6f/374449/Watling%26Smith%202013%20In%20the%20blink%20of%20an%20eye.pdf
- Cori et al. 2019 (revisão): https://findanexpert.unimelb.edu.au/scholarlywork/1389995-narrative-review--do-spontaneous-eye-blink-parameters-provide-a-useful-assessment-of-state-drowsiness%3F
- Johns/Optalert (patente): https://patents.google.com/patent/US7791491
- Shiferaw et al. 2018: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5797225/
- Sacadas e privação de sono (Sleep 2005): https://pubmed.ncbi.nlm.nih.gov/16268380
- Taxa de amostragem e pico de velocidade: https://link.springer.com/article/10.3758/s13428-016-0848-4
- Olhar para baixo e fenda palpebral (patente RE39539): https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/RE39539
- Nowara et al. 2020: https://openaccess.thecvf.com/content_CVPRW_2020/html/w19/Nowara_A_Meta-Analysis_of_the_Impact_of_Skin_Tone_and_Gender_CVPRW_2020_paper.html
- Pi 4 face mesh ~10 fps: https://core-electronics.com.au/videos/pose-estimation-and-face-landmark-tracking-with-raspberry-pi-and-opencv
- dms-face: https://github.com/youssefmedhat4/dms-face
- AI HAT+ 2: https://www.welectron.com/Official-Raspberry-Pi-AI-HAT-2
- Camera Module 3 NoIR: https://www.adafruit.com/product/5659
- 850 × 940 nm: https://commonlands.com/blogs/technical/nir-imaging-machine-vision
- Posição da câmera: https://knowledge.powerfleet.com/hc/en-us/articles/22269433139474-When-do-we-recommend-a-dash-mount-vs-pillar-mount-driver-camera
- DMD: https://dmd.vicomtech.org/

---

## 10. Resumo em 20 linhas

1. O Euro NCAP 2026 dá 15 dos 25 pontos de DMS à **distração**; o RotaGuard não tem distração pelo olhar (só "olhando o celular").
2. Números lidos no protocolo v1.2: distração longa 3–4 s; VATS 10 s em 30 s; microssono 1–2 s; sono 3 s; sem resposta 6 s ou 3 s sem voltar após aviso.
3. Sonolência: KSS > 7 (Euro NCAP) e KSS ≥ 8 (DDAW, validação com ≥ 10 pessoas e sensibilidade > 40%); o RotaGuard nunca foi comparado com KSS.
4. Microssono, sono e 6 s já batem com o protocolo (`drowsiness.py:28-30`); falta som distinto e mais urgente e o aviso de "sem visão" em ≤ 10 s.
5. DMS-01: módulo `distraction.py` com zonas, balde AttenD de 2 s, longa 3 s, VATS 10/30 com reset de 2 s e Área 3 (14 h).
6. DMS-02: "frente" pela moda do olhar (PRC, 8°) e calibração guiada de espelhos e painel (8 h).
7. DMS-03: olhar para baixo ≠ olho fechado, com `eyeLookDown` + OCEC + íris; tira microssono falso olhando o colo (5 h).
8. DMS-04: alarmes por urgência e sinal de "sem visão" (Euro NCAP 1.1.1.2 e 1.4.2) (5 h).
9. O script já calcula e joga fora: 50 blendshapes, `roll`, `mar`, `glare_fraction`, translação da matriz, z dos pontos, `blink_rate` e `p90` do perfil.
10. DMS-05: blendshapes no `FaceMetrics` e as 52 colunas no CSV de validação (4 h).
11. DMS-06: tempo de reabertura (Schleicher 2008), desvio do AVR (Optalert) e reabertura na regra (6 h).
12. Vural 2010: piscada A' 0,83, *lip pucker* 0,82, *head roll* 0,78, *lid tightener* 0,72: `roll` já existe e não é usado.
13. Conflito: a entropia do olhar sobe com a privação de sono (Shiferaw 2018), mas `activation.py` a conta como ativação (DMS-12).
14. O MediaPipe já aplica One Euro nos pontos (min_cutoff 0,05, beta 80): não filtrar de novo antes do EAR; filtrar só pose e ROIs do cardio.
15. Medido aqui, com a CPU carregada: rosto 40 ms, mãos 54 ms, celular 87–102 ms; GPU do MediaPipe só no Ubuntu.
16. DMS-08/09: captura em thread com o último quadro e celular a 1 Hz que sobe a 4 Hz com mão perto do rosto, para manter o rosto ≥ 28 fps.
17. Pupila só com 1080p e recorte dos olhos (íris ≥ 24 px); em 640 px a íris tem ~8 px (DMS-20, depende da câmera).
18. Celular: licenças conferidas; usar YOLOX, NanoDet, PicoDet ou RT-DETR (Apache); nada de Ultralytics, YOLOv10/12 (AGPL) nem pesos YOLO-NAS.
19. Celular agora: "olhar repetido ao colo" (DMS-01) + classificador do recorte da mão vazia × com celular (DMS-10).
20. Velocidade é a pergunta aberta: sem ela, a distração toca parado; GPS só para velocidade conflita com o PRD §5 (P1).
