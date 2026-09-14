# Spec 011 · Sinais complementares de fadiga (bocejo, olhos e cabeça)

| Campo | Valor |
|---|---|
| Status | rascunho (pedido do Matheus em 14/09/2026) |
| PRD | RF-01 (amplia); RF-13, RF-14 e RF-15 (propostos, bloco 6.1 Caixa; o PRD não foi editado); RNF-02, RNF-05, RNF-11 |
| Pedido | "seria legal reconhecer bocejo é um pouco mais das olheiras e expressões proximas do olho pois pode ser um indicativo tambem, se a pessoa movimente muito a cabeça e etc tudo isso ajuda" |
| Código | `caixa/vision/face.py`, `caixa/vision/eyes.py`, `caixa/vision/calibration.py`, `caixa/vision/visibility.py`, `caixa/vision/drowsiness.py`, `caixa/vision/periocular.py` (novo), `caixa/vision/head_motion.py` (novo), `caixa/vision/engine.py`, `caixa/vision/baseline.py`, `caixa/vision/driver_monitor.py`, `ferramentas/analisar_video.py` |
| Testes | `tests/test_sinais_complementares.py` (novo); regressão em `tests/test_detector.py`, `tests/test_modulos.py`, `tests/test_face_touch.py` |

RF propostos (entram no PRD se a spec for aprovada):
- **RF-13** Bocejo visível na janela e registrado a cada ocorrência, além da contagem em 10 min.
- **RF-14** Sinais perto do olho: pálpebras baixas e sobrancelhas erguidas para manter o olho aberto. Medidos pela
  forma, em relação à calibração do motorista.
- **RF-15** Movimento da cabeça: variação acima do normal da viagem e cabeça inclinada por vários segundos, sem contar
  olhadas para o espelho.

Numeração: 011 é o próximo número livre. 004, 005, 006 e 009 estão reservados no PRD (§12) e ainda não têm arquivo.
RF-13 a RF-15 continuam o bloco da caixa (RF-01 a RF-12); a faixa RF-2x é do app.

## Contexto

**Já existe.** O Matheus não viu porque nada disso aparece na janela:
- **Bocejo:** `jawOpen` ≥ max(0,45; base da calibração + 0,30) por 2 s (`drowsiness.py:50-52`, `385-397`).
  - Conta em `bocejos_10min` (`drowsiness.py:423`), e 2 em 10 min viram o motivo leve `bocejos` (`drowsiness.py:493-494`).
  - Não gera evento próprio, não mede a duração e não aparece na janela (`driver_monitor.py:85-118`).
- **Cabeceio:** queda de 15° com volta em 0,3 a 3 s (`drowsiness.py:54-64`, `151-206`), contada em `cabeceios_10min`.
  - 2 em 10 min são sinal leve e 3 são forte (`drowsiness.py:487-491`).
  - Olhar para baixo devagar, ou por mais de 3 s, não conta (`drowsiness.py:189-191`; `tests/test_modulos.py:125-142`).
- **Pose:** pitch, yaw e roll a cada quadro (`face.py:90-92`, `264-266`). A calibração guarda só pitch e yaw de
  base (`calibration.py:102-103`, `eyes.py:82-83`).
- **Blendshapes:** estão ligados (`face.py:224-225`), mas só `eyeBlink` e `jawOpen` são lidos (`face.py:260-262`, `293`).
- **Luminância do olho e da bochecha:** usada só para detectar óculos escuros (`face.py:52-57`, `154-163`; `visibility.py:12-20`).
- **Olhos tapados:** óculos escuros e mão no olho desligam os sinais do olho (`visibility.py:22-41`, `engine.py:100-101`).
- **Modo YuNet:** sem pose, bocejo nem blendshapes (`face.py:320-322`).

**Falta:**
- bocejo visível e registrado a cada ocorrência;
- leitura das sobrancelhas e do aperto do olho;
- olho "meio fechado" (o PERCLOS só conta olho pelo menos 80% fechado, `eyes.py:21`);
- variação da cabeça e cabeça inclinada por vários segundos;
- regra explícita de como os sinais complementares entram no nível.

## Decisões técnicas

1. **Bocejo: mesma regra de hoje, agora visível e registrado.**
   - **Evidência:**
     - Motoristas sem dormir bocejaram mais que descansados. Os autores chamam o bocejo de "complementary cue"
       (Jie et al., 2018: simulador, 12 pessoas, 123 bocejos com média de 6,28 s).
     - A frequência de bocejo acompanha a sonolência e sobe antes de dormir (Giganti et al., 2010).
     - No minuto antes de dormir ou bater, o motorista bocejou **menos** (Vural et al., 2007).
     - Conclusão: é sinal precoce, nunca crítico, e a ausência de bocejo não quer dizer que o motorista está alerta.
   - **Limites:**
     - Medir só a abertura da boca confunde fala, sorriso e tosse, e perde o bocejo tapado com a mão (Jie et al., 2018).
     - Os 2 s seguidos já descartam a fala comum, porque a boca fecha antes e o episódio zera (`drowsiness.py:396-397`).
   - **Novo:**
     - O episódio termina quando a boca volta abaixo do limiar − 0,1, e aí sai o evento `bocejo`.
     - Boca aberta por mais de 15 s não é bocejo (canto longo, respiração pela boca).
     - Olho apertado no pico entra só como detalhe (`olhos_apertados`). Jie et al. usaram a região do olho para separar
       bocejo de fala.
   - **Recomendação:** mostrar ao vivo e registrar cada ocorrência, mantendo a contagem de 10 min.
     - Cada bocejo vira uma linha `evento` do registro (`docs/specs/001-registro-da-viagem.md:117`) e entra na linha do
       tempo do relatório.
     - Um bocejo dura cerca de 6 s e são poucos por hora, então o registro quase não cresce.
2. **Sinais perto do olho saem da forma do rosto (blendshapes), nunca da cor.**
   - **Evidência:**
     - Vural et al. (2007): 4 pessoas num jogo de direção, analisando o minuto antes de dormir ou bater.
       - Sobrancelha externa erguida (AU2) aumentou (A' 0,81): "many subjects raised their eyebrows in an attempt to keep
         their eyes open".
       - Pálpebra apertada (AU7) e sobrancelha abaixada (AU4) diminuíram (A' 0,86 e 0,79).
       - A variação entre pessoas foi forte: o AU2 foi o melhor sinal só no sujeito 2.
     - Sundelin et al. (2013): depois de 31 h acordado, avaliadores viram pálpebras mais caídas.
   - **Correspondência pelo nome (padrão ARKit):** `browOuterUp` ≈ AU2, `browInnerUp` ≈ AU1, `browDown` ≈ AU4,
     `eyeSquint` ≈ AU6/AU7, `eyeWide` ≈ AU5.
     > [!note] Hipótese, confirmar
     > Há um mapeamento validado por especialistas entre os blendshapes do MediaPipe e as AUs (*Blendshape features
     > meet action units*, 2026), mas a tabela não abriu.
   - **Confiabilidade:** os blendshapes são estimados a partir de 146 pontos 2D do rosto (Grishchenko et al., 2023).
     - Erro na região do olho de 3,95%. Para comparar: entre duas expressões diferentes a diferença é de 8,40%.
     - Como várias combinações de blendshapes dão expressões parecidas, comparar coeficientes diretamente é "error-prone
       and noisy".
     - Por isso não há limiar absoluto: vale só a variação em relação à mediana da própria calibração, suavizada ao longo
       de segundos, e só com |yaw − base| ≤ 20°.
   - **Pálpebras baixas:** abertura mediana nos quadros fora de piscada, numa janela de 60 s, até 0,80 por 2 min seguidos.
     - A abertura vem do `OpennessModel`, em que 1 é o olho aberto de costume (`eyes.py:135-137`).
     - Não conta com `eye_squint` acima de base + 0,20. Olho apertado é sol ou sorriso, e o AU7 diminui com o sono.
   - **Sobrancelhas erguidas com olho baixo:** `brow_outer_up` ≥ base + 0,20 por pelo menos 1 s, com abertura até 0,85.
     - 3 ou mais episódios em 10 min viram o motivo.
     - Sobrancelha erguida com o olho aberto (surpresa, fala) não conta.
   - **Só no registro:** `eye_wide` e `brow_down` são guardados como medianas, sem peso, para a validação.
3. **Movimento da cabeça: variação de pitch e roll em relação à viagem; yaw fica de fora.**
   - **Evidência:**
     - Vural et al. (2007, acelerômetro): a cabeça passou a se mexer mais com o sono, com roll grande acompanhando o
       volante, e ficou parada logo antes de dormir.
     - Azaddel et al. (2026, simulador): as flutuações da aceleração da cabeça aumentaram com a sonolência.
     - Popieul et al. (2003): quem estava sem dormir mexeu mais a cabeça, com movimentos mais extremos. Conferido só no
       resumo exibido na busca, porque IEEE e ResearchGate não abriram.
   - **Por que o yaw fica de fora:** olhar o espelho é movimento de yaw e faz parte da direção.
     - O Euro NCAP separa olhares ligados à direção (espelho) dos não ligados.
     - Olhares longos ao retrovisor têm risco menor (Mulhall et al., 2023).
   - **Medida:**
     - Pose amostrada a 5 Hz numa janela de 60 s, como o olhar em `activation.py:62`.
     - Desvio robusto (MAD × 1,4826) de pitch e de roll, em graus.
     - Exige pelo menos 50% de amostras válidas, como o PERCLOS (`drowsiness.py:48`).
     - Ficam de fora:
       - amostras com |yaw − base| > 20° e o 1 s seguinte;
       - celular na mão ou no ouvido;
       - mão no rosto (`engine.py:110-113`).
     - Base: mediana das janelas de 60 s da calibração, com piso de 1,5°.
   - **Cabeça mais instável:** max(razão do pitch, razão do roll) ≥ 2,0 por 2 min seguidos.
     - A queda da variação não é usada, porque a cabeça fica parada logo antes do sono (Vural et al.).
   - **Cabeça inclinada:** |roll − base| ≥ 15° por pelo menos 5 s, com yaw dentro de ±20°.
     - O episódio termina quando a inclinação cai abaixo de 10°.
     - 2 episódios em 10 min viram o motivo.
     - Os 15° vêm da faixa de 15° a 20° que os sistemas publicados usam para cabeceio (`drowsiness.py:11-12`).
4. **Como os sinais entram no nível.** Regra do produto: sinal complementar nunca decide sozinho.
   - **Complementares:** `bocejos`, `palpebras_baixas`, `sobrancelhas_erguidas`, `cabeca_mais_instavel` e
     `cabeca_inclinada`. O cabeceio continua sinal principal, como hoje.
   - **Bocejos sozinhos:** continuam levando ao nível 1.
   - **Sinais novos:** ainda não foram validados com a câmera da caixa. Só levam ao nível 1 com pelo menos 2
     complementares diferentes, com o motivo `sinais_complementares_convergentes`.
   - **Atenção persistente:** nenhum complementar conta nessa regra (`drowsiness.py:496-505`). Sem sinal principal, nunca
     chega a sonolência nem toca alarme.
     - **Isso muda o comportamento atual:** hoje, bocejos sozinhos por 10 min viram `sonolencia` com alarme (pergunta 2).
   - **Com sinal principal:** os complementares só entram em `motivos`, e os tempos de escalada não mudam.
5. **Olheiras: fora de escopo (recomendação).**
   - **O estudo não serve de base:** Sundelin et al. (2013) medem percepção humana de 10 rostos fotografados em estúdio
     às 14:30, depois de 31 h acordados. Não é medida automática nem mudança ao longo de uma viagem.
   - **É traço da pessoa:** a olheira costuma ser hereditária e junta pigmento, vasos, inchaço e a sombra da goteira
     lacrimal (Sarkar et al., 2016).
     - O valor absoluto de uma pessoa não diz nada sobre o sono.
     - A sombra muda com a direção da luz e com o pitch da cabeça.
   - **Luz e câmera pesam mais que a olheira:**
     - Durante a viagem, dia, noite, túnel, painel e a exposição automática da câmera mudam a luminância muito mais que
       a olheira.
     - À noite, a câmera infravermelha não tem cor (`pupil.py:52-65`), e a tonalidade da olheira some.
   - **Justiça:** a análise facial erra mais em pele escura (Buolamwini e Gebru, 2018, em classificação de gênero).
     Haveria risco de alerta desigual entre motoristas.
   - **Privacidade:** seria mais um dado de aparência guardado (LGPD, PRD §9) sem benefício comprovado.
   - **Nem em modo experimental:** só reavaliar se um estudo com a câmera infravermelha da caixa mostrar mudança dentro
     da viagem.
   - "Expressões próximas do olho" fica atendido pela decisão 2.
6. **Custo e privacidade.**
   - Os blendshapes já são calculados, e a pose é amostrada a 5 Hz. Nenhuma imagem é guardada, só números.
   - No modo YuNet, os campos novos ficam `None` e os sinais, desligados.
   - Sem perfil de calibração, valem só os gatilhos críticos, como hoje (`drowsiness.py:452-453`).
   - Todos os limiares são **iniciais, a validar com vídeos reais**. O `_quadros.csv` de `analisar_video.py`
     (`analisar_video.py:281-290`) ganha as colunas novas para essa validação.

## Comportamento

- **Bocejo de verdade**
  - Dado o perfil calibrado (base da boca 0,05), quando `jaw_open` sobe a 0,7 por 5 s e volta, então a janela mostra
    `Bocejo` a partir de 2 s.
  - Quando a boca fecha, sai 1 evento `bocejo` (nível 1, sem alarme) com `duracao_s` ≈ 5.
- **Fala não é bocejo**
  - Dada uma conversa com `jaw_open` indo de 0,1 a 0,6 três vezes por segundo durante 60 s, então nenhum bocejo é
    contado e nenhum evento sai.
- **Boca aberta por muito tempo**
  - Dada a boca em 0,6 por 20 s, então não conta como bocejo.
- **Só bocejos**
  - Dados 3 bocejos a cada 10 min durante 30 min, sem outro sinal, então o nível fica em 1: nenhum evento `sonolencia` e
    nenhum alarme.
- **Pálpebras baixas**
  - Dada abertura de 0,70 fora das piscadas por 3 min, então `abertura_mediana_60s` fica em cerca de 0,70 e
    `palpebras_baixas` aparece na janela.
  - Sozinho, o nível fica em 0. Junto com bocejos, vai a 1.
- **Olho apertado contra o sol**
  - Dada abertura de 0,70 com `eye_squint` em base + 0,40, então `palpebras_baixas` não aparece.
- **Sobrancelha contra o sono**
  - Dadas 3 subidas de `brow_outer_up` (base + 0,30 por 1,5 s) com abertura de 0,75 em 10 min, então
    `sobrancelhas_erguidas_10min` = 3.
  - As mesmas subidas com o olho totalmente aberto (abertura 1,0) dão 0.
- **Olhar o espelho não é cabeça instável**
  - Dado yaw a 45° por 1 s a cada 8 s durante 5 min, com pitch e roll parados, então a variação não passa do normal e
    `olhadas_laterais_60s` fica em pelo menos 7.
- **Cabeça instável**
  - Dada uma calibração com a cabeça quase parada (desvio de 1°), quando pitch e roll oscilam com desvio de 6° por 3 min,
    olhando para a frente, então aparece `cabeca_mais_instavel`.
- **Cabeça inclinada**
  - Dado roll de +20° por 8 s, então sai 1 evento `cabeca_inclinada`.
  - Por só 2 s, ou com yaw a 40°, nada.
- **Mudança de luz não vira olheira**
  - Dadas `eye_luminance` e `cheek_luminance` variando ±40%, então nenhum valor complementar da janela muda: nenhum
    sinal usa cor ou luminância.
- **Óculos escuros ou mão no olho**
  - Então os campos perto do olho ficam `None` e nenhum motivo desse grupo aparece.

## Contratos

**`FaceMetrics`** (`face.py:78-109`)
- Campos novos, `float | None` de 0 a 1: `brow_inner_up`, `brow_outer_up`, `brow_down`, `eye_squint` e `eye_wide`.
- Os lados esquerdo e direito são combinados como em `combine_eyes` (`face.py:67-75`), na função pura
  `periocular_from_scores(scores, width_left, width_right, right_in, left_in)`.
- Sem olho na imagem, os campos ficam `None`, como `blink_score` (`face.py:262`).

**Perfil e amostras**
- `Sample` (`eyes.py:40-58`) ganha `roll`, `brow_outer_up` e `eye_squint`.
- `DriverProfile` (`eyes.py:66-90`) ganha `roll_baseline`, `brow_outer_up_baseline`, `eye_squint_baseline`,
  `pitch_var_baseline` e `roll_var_baseline`, todos com padrão `None`.
- Um perfil antigo continua abrindo (`eyes.py:108-110`). Os sinais que dependem da base ficam desligados até recalibrar.

**Visibilidade e `Assessment`**
- `_EYE_SIGNALS` (`visibility.py:22-25`) ganha os 5 campos novos.
- `Assessment` (`drowsiness.py:86-101`) ganha `yawning: bool`, `yawns_10min`, `nods_10min`, `head_tilts_10min` e
  `complementary: list[str]`.

**Eventos** (`DetectedEvent`; no registro, linha `evento`)

| `alert_type` | Nível | Alarme | Quando | `details` |
|---|---|---|---|---|
| `bocejo` | 1 | não | fim do episódio | `duracao_s`, `abertura_boca_max`, `limiar_boca`, `olhos_apertados`, `bocejos_10min` |
| `cabeca_inclinada` | 1 | não | fim do episódio; no mínimo 60 s entre dois eventos | `duracao_s`, `inclinacao_graus`, `inclinacoes_cabeca_10min` |

**Janela de métricas** (`_window_details`, `drowsiness.py:414-448`). Chaves novas, que vão junto nos eventos `atencao`,
`sonolencia` e críticos:
- **Olho:** `abertura_mediana_60s`, `aperto_olhos_60s`, `olho_arregalado_60s`, `sobrancelha_abaixada_60s` e
  `sobrancelhas_erguidas_10min`.
- **Cabeça:** `variacao_pitch_60s`, `variacao_roll_60s`, `razao_variacao_cabeca`, `olhadas_laterais_60s` e
  `inclinacoes_cabeca_10min`.
- **`motivos`:** entram `palpebras_baixas`, `sobrancelhas_erguidas`, `cabeca_mais_instavel`, `cabeca_inclinada` e
  `sinais_complementares_convergentes`.
- **`METRIC_FLOORS`** (`baseline.py:22-38`), para os z-scores (`engine.py:161-162`):

  | Chave | Piso |
  |---|---|
  | `abertura_mediana_60s` | 0,05 |
  | `sobrancelhas_erguidas_10min` | 0,5 |
  | `variacao_pitch_60s` | 1,0 |
  | `variacao_roll_60s` | 1,0 |
  | `inclinacoes_cabeca_10min` | 0,5 |

**Janela do app** (`driver_monitor.py:85-118`). Só ASCII, porque a fonte do OpenCV não tem acentos (`driver_monitor.py:21`):

| Texto | Quando |
|---|---|
| `Bocejo` (cor de aviso) | bocejo em andamento há pelo menos 2 s |
| `Em 10 min: bocejos N, cabeceios N, cabeca inclinada N` | sempre, com MediaPipe |
| `Palpebras: NN% do normal` | quando houver `abertura_mediana_60s` |
| `Cabeca: variacao X.X graus (normal Y.Y)` | quando houver base da calibração |
| `Sinais complementares: palpebras baixas, sobrancelhas erguidas` | quando `complementary` não estiver vazio (nomes sem sublinhado) |

**Nível** (`drowsiness.py:450-508`)

| Situação | Nível | Alarme | Conta na atenção persistente |
|---|---|---|---|
| Bocejos (2 ou mais em 10 min), sozinhos | 1 | não | não (hoje conta) |
| 1 sinal novo, sozinho | 0 (só na janela de métricas e na janela do app) | não | não |
| 2 ou mais complementares diferentes | 1 | não | não |
| Sinal principal + complementares | o do sinal principal | o do sinal principal | só o sinal principal |

## Critérios de aceite

| ID | Critério | Teste |
|---|---|---|
| SIN-01 | `periocular_from_scores` lê `browInnerUp`, `browOuterUp*`, `browDown*`, `eyeSquint*` e `eyeWide*`, combina os lados como `combine_eyes` e devolve `None` sem olho na imagem | `tests/test_sinais_complementares.py` (precisa de numpy e opencv) |
| SIN-02 | `mask_eye_signals` zera os 5 campos novos | `tests/test_sinais_complementares.py` |
| SIN-03 | Boca em 0,7 por 5 s: `yawning` verdadeiro de 2 s até fechar; 1 evento `bocejo` nível 1 sem alarme, com `duracao_s` errando no máximo 0,2 s e `bocejos_10min` = 1 | `tests/test_sinais_complementares.py` |
| SIN-04 | Fala (0,1 ↔ 0,6 a 3 Hz por 60 s) e boca aberta por 20 s: nenhum bocejo contado e nenhum evento `bocejo` | `tests/test_sinais_complementares.py` |
| SIN-05 | Só bocejos (3 a cada 10 min por 30 min): nível máximo 1, nenhum evento `sonolencia`, nenhum alarme | `tests/test_sinais_complementares.py` |
| SIN-06 | Abertura de 0,70 fora das piscadas por 3 min: `abertura_mediana_60s` entre 0,65 e 0,75 e `palpebras_baixas` na janela; sozinho, nível 0 | `tests/test_sinais_complementares.py` |
| SIN-07 | Mesmo cenário com `eye_squint` em base + 0,40: `palpebras_baixas` não aparece | `tests/test_sinais_complementares.py` |
| SIN-08 | 3 sobrancelhas erguidas com abertura de 0,75: `sobrancelhas_erguidas_10min` = 3; com abertura de 1,0: 0 | `tests/test_sinais_complementares.py` |
| SIN-09 | Pitch e roll com desvio de 6° por 3 min (base de 1°): `cabeca_mais_instavel` aparece. Yaw a 45° por 1 s a cada 8 s, com pitch e roll parados: sem o motivo e com `olhadas_laterais_60s` ≥ 7 | `tests/test_sinais_complementares.py` |
| SIN-10 | Roll de +20° por 8 s: 1 evento `cabeca_inclinada`. Por 2 s, ou com yaw a 40°: nenhum | `tests/test_sinais_complementares.py` |
| SIN-11 | 1 sinal novo sozinho: nível 0. 2 complementares diferentes: nível 1 com `sinais_complementares_convergentes`. 30 min só com complementares: nunca nível 2 nem alarme | `tests/test_sinais_complementares.py` |
| SIN-12 | PERCLOS de 3 min acima de 12% junto com complementares: `sonolencia` sai no mesmo segundo que sem eles, com os motivos complementares incluídos | `tests/test_sinais_complementares.py` |
| SIN-13 | `eye_luminance` e `cheek_luminance` variando ±40%: todas as chaves complementares da janela ficam iguais às da execução sem variação | `tests/test_sinais_complementares.py` |
| SIN-14 | A calibração preenche as bases novas; um perfil salvo sem elas abre e deixa desligados os sinais que dependem da base | `tests/test_sinais_complementares.py` |
| SIN-15 | `draw_overlay` com um estado sintético mostra `Bocejo` e `Em 10 min: bocejos 1, cabeceios 0, cabeca inclinada 0`, e todo texto da janela é ASCII | `tests/test_sinais_complementares.py` (precisa de numpy e opencv) |
| SIN-16 | `test_detector.py`, `test_modulos.py`, `test_face_touch.py` e o resto da suíte continuam passando | provas |

## Fora de escopo

- Olheiras: medir, alertar ou registrar (decisão 5).
- Bocejo tapado com a mão: o MediaPipe perde a boca, e `face_touch.py` já exclui a faixa da boca
  (`face_touch.py:19-20`).
- Peso dos sinais novos:
  - no índice de ativação (módulo 2);
  - nos trechos por recorrência (spec 002);
  - no `resumo_minuto` (spec 001, linha 118);
  - no relatório (spec 004).
- Relação entre cabeça e volante (não há leitura do volante).
- Queda da variação da cabeça logo antes do sono.
- A mesma lógica no modo de teste JS do app (spec 007, APP-05).
- Ajuste dos limiares com vídeos reais (etapa de validação).

## Riscos

- **Pouca evidência:** Vural et al. tinham 4 pessoas num jogo de direção; Azaddel et al. e Jie et al. usaram simulador.
  Os sinais perto do olho mudam muito de pessoa para pessoa. Por isso entram só em relação à calibração e só como
  complemento.
- **Blendshapes instáveis:** pioram com a cabeça virada, pouca luz e óculos. Mitigação: limite de yaw de ±20°,
  suavização e máscara de visibilidade.
- **Trepidação:** ônibus e caminhão em estrada ruim sacodem a cabeça e aumentam a variação de pitch e roll sem nenhum
  sono. Sem acelerômetro não dá para descontar isso (pergunta 3).
- **Canto:** uma vogal sustentada por mais de 2 s é contada como bocejo.
- **Pálpebra baixa sem sono:** olhar para o painel ou a luz da cabine à noite fecham um pouco o olho. Se a calibração foi
  feita de dia, a base pode não valer à noite.
- **Janela do app poluída:** até 5 linhas a mais. Se atrapalhar, juntar numa só.
- **LGPD:** medida de expressão facial é dado pessoal e segue o mesmo tratamento das medidas de olho que já existem.

## Perguntas para o Matheus

1. **Olheiras:** concorda em deixar de fora, pelos motivos da decisão 5, e atender o pedido com pálpebras e sobrancelhas
   medidas pela forma do olho?
2. **Bocejos sozinhos:** hoje, bocejos por 10 min seguidos viram "sonolência" com alarme (`drowsiness.py:493-505`). Esta
   spec deixa em "atenção", sem alarme, para cumprir "sinal complementar nunca decide sozinho". Pode mudar?
3. **Acelerômetro:** a caixa vai ter um acelerômetro (IMU) para descontar o balanço da estrada? Sem ele,
   "cabeça instável" fica só no registro e não entra no nível.
4. **Relatório:** os eventos `bocejo` e `cabeca_inclinada` aparecem para o gestor no relatório (spec 004), ou só no
   registro e na área do motorista?

## Fontes

- Vural, E.; Cetin, M.; Ercil, A.; Littlewort, G.; Bartlett, M.; Movellan, J. (2007). *Drowsy Driver Detection Through
  Facial Movement Analysis*. HCI 2007, Springer. https://mplab.ucsd.edu/46/media/vesra.pdf ·
  https://link.springer.com/chapter/10.1007/978-3-540-75773-3_2
- Jie, Z.; Mahmoud, M.; Stafford-Fraser, Q.; Robinson, P.; Dias, E.; Skrypchuk, L. (2018). *Analysis of yawning behaviour
  in spontaneous expressions of drowsy drivers*. IEEE FG 2018. https://www.cl.cam.ac.uk/~mmam3/pub/FG2018-HBU-yawining.pdf
- Giganti, F.; Zilli, I.; Aboudan, S.; Salzarulo, P. (2010). *Sleep, Sleepiness and Yawning*. Em: *The Mystery of Yawning
  in Physiology and Disease*, Karger. https://karger.com/books/book/2691/chapter/5762608/Sleep-Sleepiness-and-Yawning
- Sundelin, T.; Lekander, M.; Kecklund, G.; Van Someren, E. J. W.; Olsson, A.; Axelsson, J. (2013). *Cues of Fatigue:
  Effects of Sleep Deprivation on Facial Appearance*. Sleep 36(9):1355-1360.
  https://academic.oup.com/sleep/article-abstract/36/9/1355/2453883
- Sundelin, T.; Lekander, M.; Sorjonen, K.; Axelsson, J. (2017). *Negative effects of restricted sleep on facial
  appearance and social appeal*. R. Soc. Open Sci. https://pubmed.ncbi.nlm.nih.gov/28572989/
- Axelsson, J. et al. (2010). *Beauty sleep: experimental study on the perceived health and attractiveness of sleep
  deprived people*. BMJ 341:c6614. https://pmc.ncbi.nlm.nih.gov/articles/PMC3001961/
- Sarkar, R. et al. (2016). *Periorbital Hyperpigmentation: A Comprehensive Review*. J Clin Aesthet Dermatol 9(1):49-55.
  https://pubmed.ncbi.nlm.nih.gov/26962392/
- Buolamwini, J.; Gebru, T. (2018). *Gender Shades: Intersectional Accuracy Disparities in Commercial Gender
  Classification*. PMLR 81. https://proceedings.mlr.press/v81/buolamwini18a.html
- Grishchenko, I. et al. (2023). *Blendshapes GHUM: Real-time Monocular Facial Blendshape Prediction*.
  https://arxiv.org/abs/2309.05782
- *Blendshape features meet action units: a clinical mapping for enhancing facial expression analysis* (2026). Lido só o
  resumo exibido na busca; a página deu erro 403. https://www.sciencedirect.com/science/article/pii/S2451958826001995
- Azaddel, R.; Rezaei, M.; Sadeghi-Bazargani, H.; Rasoulzadeh, Y. (2026). *Modeling behavioral indicators for driver
  drowsiness detection: a simulator-based study*. Traffic Inj Prev. https://pubmed.ncbi.nlm.nih.gov/42566753/
- Popieul, J. C.; Simon, P.; Loslever, P. (2003). *Using driver's head movements evolution as a drowsiness indicator*.
  IEEE Intelligent Vehicles Symposium. Lido só o resumo exibido na busca. https://ieeexplore.ieee.org/document/1212983/
- Mulhall, M. et al. (2023), por Seeing Machines: *Prevalence of Euro NCAP Defined Distraction in Naturalistic Driving*.
  https://seeingmachines.com/prevalence-of-euro-ncap-defined-distraction-in-naturalistic-driving/
