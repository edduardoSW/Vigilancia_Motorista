# Pesquisa · Alarme, calibração, escalas, jornada e registro do script RotaGuard

| Campo | Valor |
|---|---|
| Data | 19/10/2026 |
| Escopo | Conteúdo do script da câmera (`caixa/vision/` e `caixa/run_monitor.py`), PRD (RF-01 a RF-07, Q1, Q2), specs 001, 002, 009 e 011 |
| Método | Leitura do código, busca em normas e artigos (URLs no fim) e 5 experimentos curtos rodados no notebook com o código real do repositório |
| Repositório | Nenhum arquivo do repositório foi alterado |

> [!note] Como ler
> Toda afirmação sobre o script tem `arquivo:linha`. Fonte externa tem número `[n]` com a URL na seção 8.
> O que não foi conferido na fonte original, ou só foi medido com dados sintéticos, está marcado como hipótese.

---

## 0. Achados que pedem ação antes do resto

1. **Bug: a janela do OpenCV quebra.** `draw_overlay` usa `metrics` sem definir a variável
   (`caixa/vision/driver_monitor.py:252-255`). A mudança ainda não commitada trocou
   `metrics, drowsy, risk = state.metrics, ...` por `drowsy, risk = ...` (`driver_monitor.py:225`).
   - Reproduzido: `NameError: name 'metrics' is not defined` (script `scratchpad/scripts/check_overlay.py`).
   - `_show` só captura `cv2.error` (`driver_monitor.py:460`), e a chamada fica fora de `try` no laço
     (`driver_monitor.py:434-435`). Com `--window`, o monitoramento termina no primeiro quadro.
   - Os testes não pegam o erro: `tests/test_app_teste.py:327` troca `draw_overlay` por uma função falsa.
2. **Microssono não dispara quando a cabeça cai e o rosto some.** O rastreador zera depois de 0,5 s sem medida
   (`eyes.py:290-292`, `MAX_FRAME_GAP_S` em `eyes.py:29`), e o contador de olho fechado volta a 0.
   - Experimento `exp_cabeca.py`: com o rosto visível, olhos fechados por 5 s geram 120 quadros com alarme e os eventos
     `microssono` e `sono`.
   - Se o rosto some 0,6 s ou 0,9 s depois de o olho fechar: **0 alarmes e 0 eventos** nos 4 s seguintes. O evento
     `rosto_nao_detectado` só sai depois de 10 s, e sem alarme (`drowsiness.py:67`, `399-409`).
   - Cabeça caindo para a frente durante o sono é um cenário clássico. O Euro NCAP classifica como "sem resposta"
     quem fica 6 s de olhos fechados ou não volta o olhar em 3 s depois de um aviso [1].
   > [!note] Hipótese, confirmar
   > Experimento com dados sintéticos. Com câmera real, o MediaPipe pode continuar achando o rosto inclinado por algum
   > tempo. A falha de lógica existe; a frequência dela só aparece em vídeo real.
3. **O mesmo som para tudo.** Microssono, sonolência, celular e rebote tocam a mesma sirene
   (`driver_monitor.py:352-353` → `alarm.py:100-107`). O Euro NCAP 2026 exige que os avisos de microssono e de sono sejam
   **distintos e mais urgentes** que os de distração e de prejuízo [1, §1.4.2].
4. **Pendências fora do escopo, encontradas no caminho:**
   - O PRD cita as specs 005 e 006 (`PRD.md:331-332`), mas os arquivos não existem em `docs/specs/`.
   - A spec 002 fixa `cryptography==50.0.1` (`002:253`). A última estável no PyPI hoje é **50.0.2**
     (`pip index versions cryptography`, 19/10/2026). O `.venv` tem a 50.0.1.

---

## 1. Alarme e intervenção

### 1.1 O que as normas e os estudos dizem

**Quando avisar, e com que urgência**
- **Euro NCAP 2026, Driver Engagement v1.2** [1], lido no PDF:
  - **microssono:** fechamento curto, de 1 a 2 s (§1.3.3);
  - **sono:** olho fechado por 3 s (§1.3.4);
  - **sem resposta:** olhos fechados por 6 s, ou olhar que não volta em 3 s depois de um aviso de distração (§1.3.5);
  - **sonolência:** KSS 7 ou mais "at the latest" (o texto extraído mostra ">7"), funcionando a partir de 50 km/h
    (§1.3.2);
  - aviso visual e (sonoro e/ou háptico) **imediatamente** depois da classificação (§1.4.2);
  - para sonolência, sugerir área de descanso no navegador vale como alternativa ao aviso (§1.4.2);
  - aprendizado de até **10 min** no início da viagem (§1, requisitos gerais);
  - nos estados passageiros (distração), o aviso pode ser suprimido depois de o motorista reconhecer o primeiro, e volta
    a valer a cada viagem nova (§1.4.1);
  - a sonolência só termina no fim da viagem, ou no "fim do estado" se o sistema também detectar microssono e sono
    (tabela de §1.4.3).
- **Regulamento (UE) 2021/1341, DDAW** [2]:
  - aviso **obrigatório** em KSS 8 ou mais e **permitido** em KSS 7 (§3.3.1);
  - avisos que podem "cascade and intensify" até o motorista reconhecer, e melhora no comportamento conta como
    reconhecimento (§3.4.1.1);
  - som com a maior parte da energia entre **200 e 8.000 Hz** e entre **50 e 90 dB** (§3.4.3.2);
  - fala com o mesmo vocabulário do texto visual (§3.4.3.3);
  - aviso visual constante quando o sensor está tapado (§3.5.3);
  - validação: no mínimo 10 participantes, KSS informado a cada ~5 min, sensibilidade média acima de 40% (Parte 2,
    §3.1, §5.1 e §8.1).

**Desenho do som**
- **IEC 60601-1-8** (alarmes médicos), referência de prioridade sonora:
  - pulsos com fundamental entre 150 e 1.000 Hz e pelo menos 4 harmônicos, para o som não sumir em pontos da sala;
  - alta prioridade com pulsos mais curtos e rajadas mais rápidas que a média.
  > [!note] Hipótese, confirmar
  > Números lidos em guias de fabricantes e numa nota da Texas Instruments [3]. As fontes divergem (4 ou 5
  > harmônicos). A norma é paga e não foi lida.
- **ISO 7731** (sinais de perigo): o sinal precisa ficar cerca de 15 dB(A) acima do ruído de fundo [4]. A edição de
  1986 falava em 13 dB.
- **ISO 15006:2011** (som no veículo) e **ISO 15005:2017** (diálogo com o motorista): só o escopo foi conferido [5][6].
  Os valores ficam na cláusula 4.2 da 15006, que é paga. Para números, o DDAW [2] é a referência aberta mais próxima.
- **Urgência percebida** (Edworthy et al., 1991; Hellier et al., 1993) [7]:
  - sobe com fundamental mais alta, pulsos mais rápidos, mais repetições e harmônicos irregulares;
  - menos tempo entre pulsos diminui o tempo de reação (Suied et al., 2008) [7];
  - o efeito some sob carga alta de trabalho.
- **Para acordar quem dormiu:** onda quadrada de 520 Hz acordou mais gente, com limiar menor, que tons puros agudos
  (~3 kHz) (Bruck & Thomas, 2009) [8].
  - Pessoas privadas de sono acordam pior. Uma revisão recomenda cerca de 90 dB(A) para alarmes de quarto [9].

**Voz ou bipe**
- Não há vencedor único [10]:
  - ícones sonoros (buzina, pneu) deram a reação mais rápida, com mais respostas indevidas (Graham, 1999);
  - fala ajudou quando informava direção ou local do perigo;
  - em alguns estudos o bipe foi mais rápido que a fala.
- **Leitura para o RotaGuard:** primeiro um tom para despertar ou chamar atenção. Depois, se for o caso, uma frase curta
  que diga **o que fazer**. O DDAW só exige que a fala bata com o texto visual [2, §3.4.3.3].

**Fadiga de alarme**
- Alarmes falsos derrubam confiança e obediência ("cry wolf"; Lees & Lee, 2007; Breznitz, 1984) [11].
- Alarme "desnecessário mas compreensível" não fez o mesmo estrago [11].
- Escalonar funciona: **alertas em vários estágios** reduziram saídas de faixa mais que alertas de estágio único,
  principalmente de madrugada (Gaspar et al., 2017; 72 motoristas, simulador) [12].

**Pausa, cochilo e café**
- 30 min de pausa com cochilo de menos de 15 min, ou café (~150 mg de cafeína), funcionam, e os dois juntos funcionam
  melhor (Horne & Reyner, 1999) [13].
- 200 mg de cafeína mais cochilo curto reduziram os incidentes a 9% do placebo; só cafeína, a 34% (Reyner & Horne,
  1997, 12 pessoas, simulador) [14].
- Cochilo de 30 min tem mais sono profundo e mais inércia do sono que um de 10 min. Mesmo assim, as evidências sobre
  cochilos curtos são mistas (revisão de 2017) [15].
- Ar frio e rádio não funcionaram (Reyner & Horne, 1998). Janela aberta e música também não, em estrada real
  (Schwarz et al., 2012) [16].
- **O alerta não fez o motorista parar mais.** NHTSA, DOT HS 813 439 (2023), 72 motoristas acordados havia 18 h:
  - a notificação de sonolência reduziu saídas de faixa (0,104 contra 0,266 por minuto);
  - não mudou a frequência, o momento nem a duração das pausas [17].
- A pausa ajuda por pouco tempo: os eventos críticos caíram na hora seguinte à pausa (FMCSA, motoristas de caminhão) [18].

**Tempo de reação**
- Referência clássica de freio: ~0,7 s quando esperado, ~1,25 s em sinal comum e ~1,5 s com surpresa (Green, 2000) [19].
  Os valores foram lidos em fonte secundária.
- O O1 do PRD pede alarme em até 1,5 s depois de 1 s de olhos fechados (`PRD.md:52`, RNF-01 em `PRD.md:157`).

### 1.2 O que o script faz hoje

| Ponto | Código | Situação |
|---|---|---|
| Som | `alarm.py:16-46`: 2 senoides puras de 2.000 e 1.000 Hz, 5 ciclos de 150 ms com 50 ms de pausa, **2,0 s**, pico 0,8 da escala, sem envelope | Medido em `exp_som.py`: energia em 1 e 2 kHz e nada relevante acima (−52 dB em 3 kHz). Fica dentro de 200–8.000 Hz, mas sem harmônicos [3] e longe dos 400–520 Hz que acordam melhor [8] |
| `sirene.wav` | Gerado pelo próprio script a cada início em `<data-dir>/sirene.wav` (`alarm.py:76`; `run_monitor.py:211`). Existe em `~/.drivesafe/sirene.wav` neste notebook. Listado em `textos_legais.py:47` | Nenhum arquivo de terceiros: já é síntese própria |
| Nível do alarme | Um só: `trigger()` sem argumentos (`alarm.py:100`) | Sem níveis, sem distinção sono × celular |
| Interrupção | `trigger()` ignora pedidos enquanto toca (`alarm.py:104`); `_play` bloqueia em `subprocess.run` ou `winsound.PlaySound` síncrono (`alarm.py:113-119`) | Não dá para parar quando o olho abre, nem trocar por um som mais urgente no meio |
| Buzzer | `gpiozero.Buzzer.beep` liga e desliga (`alarm.py:64-74`, `111-112`) | O `Buzzer` só liga e desliga, sem tons; o `TonalBuzzer` (buzzer passivo) toca notas [20]. Com buzzer ativo, a urgência só muda pelo ritmo |
| Autoteste do som (RF-04) | Só procura um player e avisa no log (`alarm.py:83-98`) | RF-04 continua "Parcial" (`PRD.md:82`): não toca nada ao ligar e não registra "sem som" |
| Microssono | Alarme em todo quadro com olho fechado por ≥ 1 s (`drowsiness.py:366-368`), na prática sirene contínua | Correto pelo Euro NCAP; falha quando o rosto some (achado 2) |
| Sonolência (nível 2) | Evento com alarme a cada 120 s enquanto durar (`drowsiness.py:69`, `310-311`), e alarme ao subir para ≥ 2 com espera de 60 s (`risk.py:32`, `131-134`) | Repete o mesmo som, sem escalar |
| Celular | Alarme com espera de 30 s (`phone.py:82`, `386-388`), somado ao risco (`risk.py:120-124`) | Mesma sirene do microssono (achado 3). Distração frequente vira o alarme mais ouvido e ensina o motorista a ignorar a sirene [11] |
| Histerese | O risco desce um nível por vez, depois de 10 s (crítico) ou 60 s (`risk.py:24`, `153-161`) | Bom contra oscilação. Para sonolência é curto demais: o Euro NCAP mantém o estado até o fim da viagem ou do estado [1, §1.4.3] |
| Pausa | Nada | Não há sugestão de pausa nem verificação de que houve pausa |
| Olhos não visíveis ou rosto perdido | Eventos `olhos_nao_visiveis` e `rosto_nao_detectado` depois de 10 s, sem som (`engine.py:42`, `241-250`; `drowsiness.py:399-409`) | Na caixa sem tela, o motorista nunca sabe que não está sendo monitorado. O DDAW pede aviso visual constante nesse caso [2, §3.5.3] |

### 1.3 Proposta de desenho do alarme

**Quatro sinais distintos, todos sintetizados com numpy, sem arquivo de terceiros**

| Sinal | Quando | Padrão (proposta) | Por quê |
|---|---|---|---|
| `info` | Calibração concluída, "não vejo seus olhos", autoteste | 1 a 2 notas suaves (~520 e 660 Hz), 200 ms, uma vez | Baixa prioridade; não pode soar como alarme |
| `distracao` | Celular | 2 pulsos médios (~660 Hz com harmônicos), nunca contínuo; espera própria | O Euro NCAP separa estado passageiro de não passageiro [1] |
| `sonolencia` | Risco 2 por sonolência ou rebote | Rajada 3+2 com harmônicos (no estilo da alta prioridade da IEC 60601-1-8 [3]) e, em seguida, frase curta | Urgente, mas diferente do crítico; a fala diz o que fazer [2] |
| `critico` | Microssono, sono, sem resposta, cabeça caiu (achado 2) | Pulsos rápidos e curtos (~70 ms), alternando 880 e 1.175 Hz com harmônicos, contínuo até o olho abrir; volume máximo configurado | Mais urgente que todos [1, §1.4.2]; pulsos rápidos aceleram a reação [7] |

- **Protótipo pronto para ouvir**, gerado em 6,5 ms (`scratchpad/scripts/exp_som.py`):
  - `scratchpad/sons/atencao.wav` (0,70 s);
  - `scratchpad/sons/alto.wav` (1,15 s);
  - `scratchpad/sons/critico.wav` (1,76 s);
  - `scratchpad/sons/sirene_atual.wav`, para comparar.
  - As frequências são **ponto de partida**: precisam de teste de escuta com motoristas e de medida na cabine.
- **Preempção:** o crítico interrompe qualquer outro som, e nenhum som inferior interrompe o crítico. É preciso trocar a
  reprodução bloqueante (`alarm.py:109-131`) por:
  - um fluxo de áudio aberto o tempo todo (`sounddevice` 0.5.6, PortAudio, licença MIT, conferido no PyPI);
  - ou o `aplay` em `subprocess.Popen` com `terminate()`;
  - no Windows, `winsound.PlaySound` com `SND_ASYNC` e `SND_PURGE` para parar.
- **Escalonamento** (o DDAW permite "cascade and intensify" [2]; estágios funcionam melhor [12]):
  1. sonolência detectada → `sonolencia` + frase "Sinais de sono. Procure um local seguro para parar.";
  2. sinais por mais 5 min → repete com volume maior e frase "Pare e descanse 15 a 20 minutos";
  3. microssono → `critico` contínuo até o olho abrir. Depois de abrir, o risco fica alto e vem a frase de pausa.
- **Anti-fadiga de alarme:**
  - **espera por tipo** (já existe: `risk.py:33`, `drowsiness.py:69`, `phone.py:82`) e espera própria para cada sinal;
  - **orçamento por hora** para `distracao`: passou de N por hora, o som fica mais suave ou só visual (LED), e o fato
    vai para o registro. **Nunca** se aplica ao `critico`;
  - **reconhecimento** sem botão: olho aberto e olhando para a frente por 2 s encerra o estágio. Com botão físico na
    caixa (Pi), o reconhecimento desliga só a repetição, nunca a detecção;
  - **contador** `alarmes_por_hora` por tipo no `resumo_minuto` (spec 001 §5), para medir o O4. A função
    `false_alarms_per_hour` já existe em `evaluation.py:104`.
- **Memória de sonolência** (Euro NCAP: o estado só termina no fim da viagem ou do estado [1]):
  - depois de um nível 2 por sonolência, o risco não desce abaixo de 1 até detectar pausa de ≥ 15 min;
  - pausa = rosto ausente, ou telemetria parada (`context.py:64-66`), ou 30 min sem nenhum sinal;
  - hoje cai a 0 em cerca de 2 min (`risk.py:24`).
- **Sugestão de pausa e verificação** (o alerta sozinho não faz parar [17]; o que muda a decisão é a empresa ver no
  relatório):
  - eventos novos `pausa_sugerida` e `pausa_detectada` (com duração) no registro;
  - o relatório mostra "pausa sugerida às 03:12; parou às 03:40 por 18 min" ou "não parou";
  - **pausa recente:** o efeito dura cerca de 1 h [13][18]. Sinais de sono nessa hora sobem de nível mais rápido, como a
    regra de rebote que já existe (`risk.py:103-118`).
- **Frase de voz:** texto curto, em pt-BR, igual ao do relatório.
  - Opção A (recomendada): gravar 4 ou 5 frases com a voz da equipe e guardar em WAV próprio, sem dependência e sem
    licença de terceiros.
  - Opção B: `espeak-ng` no Pi pelo `apt` (programa GPL-3.0 chamado como processo; voz robótica).
  - Opção C: `piper-tts` 1.8.0. O código mantido passou a GPL-3.0 em 2025 e cada voz tem licença própria [21]. Exige
    análise de licença (RNF-10).
  - **Decisão do Matheus.**
- **Nível sonoro no Pi** (RNF-01): o DDAW pede 50–90 dB [2]; a ISO 7731 pede ~15 dB acima do ruído [4]; quem dormiu
  precisa de mais [9].
  - Proposta: crítico calibrado na instalação para 85–90 dB(A) na altura da cabeça do motorista, medido com decibelímetro.
  > [!note] Hipótese, confirmar
  > Ruído de cabine de caminhão moderno não foi achado em fonte confiável: os estudos dos anos 1970 mediam 84–88 dB(A),
  > e os trucks de 2007–2008 ficavam abaixo do limite de 8 h da NIOSH [22]. Medir na frota.

---

## 2. Calibração individual e linha de base

### 2.1 Estado da arte

- **Limiar fixo não serve:** a abertura natural do olho varia entre pessoas. O "Modified EAR" (Dewi et al., 2022) e uma
  patente de calibração personalizada (EP 4105827) definem o limiar por pessoa, a partir da média e do desvio do EAR nas
  piscadas [23].
- **Diferenças individuais grandes:** o intercepto da duração de piscada variou muito entre pessoas, além do efeito do
  sono (Ingre et al., 2006) [24]. Medir a mudança em relação à própria pessoa é o padrão.
- **O EAR depende da pose:** é uma razão de distâncias 2D e distorce com a rotação da cabeça. O Eyelid Angle, feito
  com pontos 3D do MediaPipe, variou bem menos entre ângulos de câmera (Wolter et al., 2025) [25].
  - No mesmo trabalho, a duração do fechamento mudou 32% entre 30 e 50 Hz: a taxa de quadros pesa na medida [25].
- **Tempo de calibração:** o Euro NCAP aceita até 10 min de aprendizado [1]. O DDAW tira da validação a fase de
  aprendizado ou os primeiros 30 min [2, Parte 2 §8.2].
- **Calibrar com o motorista já sonolento:** 4 min de olhos antes de dirigir previram microssonos (duração da piscada,
  AUC 0,79; PERCLOS, AUC 0,96 sem significância) (Mulhall et al., 2020, 15 pessoas) [26].
  - A própria calibração é uma "avaliação antes da viagem" e serve para apontar quem já começa com sono.
- **Escala populacional:** a Johns Drowsiness Scale (Optalert) é calculada a cada minuto, de 0 a 10, a partir da razão
  amplitude/velocidade (AVR). O normal fica entre 0 e 4, **sem ajuste individual** [27]. Indício de que a AVR tem norma
  populacional útil para apontar calibração suspeita. A validação é quase toda do fabricante.
- **Mistura de duas gaussianas e Otsu** para separar aberto de fechado: aparecem em trabalhos de imagem binarizada [28].
  Não achei estudo com EAR contínuo. Fica como técnica de engenharia, não como evidência.

### 2.2 O que o script faz (pontos fortes)

- Calibra de 5 a 10 min até 100 piscadas (`calibration.py:59`; `run_monitor.py:92-95`). Bate com os 10 min do Euro NCAP.
- O microssono já é detectado durante a calibração (`run_monitor.py:244-245`; `drowsiness.py:345-369`).
- Abertura relativa: 1 = aberto habitual, 0 = fechado (`eyes.py:135-186`), com EAR, pontuação do MediaPipe e classificador
  combinados por máximo ou mediana (`eyes.py:174-185`). O P80 é relativo à amplitude da pessoa (`eyes.py:21`).
- Duração da piscada e AVR são invariantes à escala do EAR (`eyes.py:6-8`, `222-233`). Mudança de câmera ou de distância
  afeta pouco esses dois sinais.
- Confere calibração sonolenta por PERCLOS ≤ 10% e maior fechamento < 1 s (`calibration.py:36-38`, `168`). Se suspeita,
  mantém o perfil anterior (`drowsiness.py:522-527`) e não salva.
- A linha de base da viagem reprocessa os quadros da calibração em janelas de 30 s (`baseline.py:139-159`), com piso de
  desvio por métrica (`baseline.py:22-38`). A acumulada só entra com consentimento e com calibração não suspeita
  (`engine.py:237-239`).

### 2.3 Lacunas, com experimento

**(a) A referência de olho fechado piora com poucos quadros por segundo** (`calibration.py:114`)
- `ear_closed` = mediana do menor EAR de cada piscada completa. A 10 fps, a piscada de ~100 ms tem 1 ou 2 quadros, e o
  "menor EAR" raramente pega o fundo.
- Experimento `exp_calib.py`: o `Calibrator` real recebeu piscadas sintéticas com EAR aberto 0,30 e fechado 0,06.

| fps | `ear_closed` calculado | Erro |
|---|---|---|
| 30 | 0,064 | +7% |
| 15 | 0,071 | +18% |
| 10 | 0,094 | +57% |

- Efeito a 10 fps (o mínimo do RNF-02, `PRD.md:158`): um olho só **69% fechado** já conta como "80% fechado" no PERCLOS
  e no microssono. Conta: (0,24·r − 0,034)/0,206 ≤ 0,2 ⇒ r ≤ 0,31.
- **Proposta:**
  - usar um percentil baixo dos mínimos (P15–P20) só das piscadas com pelo menos 3 quadros abaixo de 50%;
  - ou estimar o fundo pela curva da piscada (interpolação parabólica nos quadros do vale);
  - com fps < 20, marcar `ear_closed_estimated` e registrar a qualidade da calibração.

> [!note] Hipótese, confirmar
> A forma das piscadas é sintética (fechamento linear de 70–100 ms). Confirmar com `ferramentas/avaliar_piscadas.py`
> em vídeo real gravado a 10 e a 30 fps.

**(b) Calibração com sono moderado passa como "alerta"** (`calibration.py:168`)
- Experimento `exp_calib2.py`: piscadas 48% mais longas (mediana de 229 ms contra 155 ms) e um fechamento de 0,76 s.
  - Resultado: PERCLOS 1% e maior fechamento 0,76 s, então `looked_alert=True`. O perfil é salvo e entra na acumulada.
- Consequência: o gatilho de piscadas 1,25× mais longas (`drowsiness.py:33`, `461-462`) passa a exigir 287 ms em vez
  de 193 ms. A detecção fica menos sensível na viagem toda.
- A comparação com a linha de base acumulada (`engine.py:224-230`) só procura **ativação**. Lá a duração conta só para
  baixo (`activation.py:38-44`, `DIRECTION["duracao_mediana_ms"] = -1`), então piscada **mais longa** que o habitual
  nunca marca a calibração como suspeita.
- **Proposta:** a calibração fica "suspeita de sono" se qualquer um destes acontecer:
  1. z da duração mediana ≥ +1,5 em relação à acumulada, quando houver ≥ 3 viagens (`baseline.py:46`);
  2. 1 ou mais fechamentos ≥ 500 ms, a definição de microssono comportamental de Mulhall [26];
  3. AVR de fechamento acima de uma norma populacional (a definir com dados; a JDS mostra que isso existe [27]);
  4. calibração na madrugada ou depois de mais de 4 h de direção (`context.py`): não muda o resultado, só baixa a
     qualidade (`baseline.py:47-48`).
- Calibração suspeita **não** entra na acumulada. Com perfil salvo, usa o perfil salvo. O relatório diz "viagem começou
  com sinais de sono" (`calibracao_suspeita`, `drowsiness.py:535`).

**(c) Sem nova calibração automática** (`eyes.py:188-195`)
- Com perfil, as referências ficam fixas a viagem inteira. A nova calibração só acontece pela tecla `c`
  (`driver_monitor.py:465-466`) ou pela política do servidor.
- Mudam no caminho: luz (dia, noite, túnel), câmera infravermelha ligando, óculos, banco ou câmera mexidos.
- **Cuidado central:** adaptar a referência de "aberto" aos poucos **apaga o próprio sinal de sono**. A pálpebra cai com
  o sono (spec 011, decisão 2) e a abertura mediana baixa devagar.
- **Proposta: nova calibração só em degrau com causa física**, nunca em deriva lenta:
  - gatilhos:
    - `eye_distance_px` muda mais de 15% e fica assim por 60 s (câmera ou banco mexidos);
    - mediana de pitch ou yaw muda mais de 8° e fica assim por 2 min;
    - troca de faixa de luz ou de modo infravermelho (`activation.py:114-120`; `face.py`);
    - óculos entram ou saem (`visibility.py`);
  - o que recalcula: só as referências de aberto e fechado (EAR, pontuação, classificador), em 2 min, sem pedir nada ao
    motorista. Duração, AVR e linha de base continuam;
  - o que nunca dispara nova calibração: queda gradual do EAR aberto sem mudança de escala, pose ou luz.
  - Cada nova calibração vira linha `calibracao` com `motivo` (`recalibracao_automatica:<causa>`) no registro (spec 001,
    `001:116`).
- **Pose:** testar o EAR 3D com o `z` dos 478 pontos (Eyelid Angle [25]), ou a correção por pitch, em vídeo com cabeça
  inclinada (`ferramentas/analisar_video.py`). Hoje o quadro só é descartado acima de 25° de pitch ou 30° de yaw
  (`eyes.py:26-28`).

**(d) PERCLOS diferente do da literatura** (`drowsiness.py:290-297`)
- O script só conta fechamentos de mais de 250 ms (`calibration.py:30`). O estudo da AAA (Owens et al., 2018), base do
  limiar de 12% (`drowsiness.py:7`, `34`), contou **todos os quadros** com a pálpebra mais de 80% fechada, a 15 fps, em
  3 min. As piscadas entram nessa conta [29].
- Para o mesmo olho, o PERCLOS do script sai menor que o da AAA. Então 12% no script é mais rígido (menos sensível) que
  12% no estudo.
- **Proposta:** calcular os dois (`perclos_3min` e `perclos_quadros_3min`), registrar os dois, usar o "por quadros"
  contra o limiar de 12% e reajustar com dados.

> [!note] Hipótese, confirmar
> O tamanho da diferença depende da taxa de piscadas: a 15–20 piscadas/min de ~100 ms com o olho fechado, as piscadas
> sozinhas somam alguns pontos percentuais. Medir com vídeo.

---

## 3. Escalas de sonolência: dar significado aos números

### 3.1 As escalas

| Escala | O que é | Uso no RotaGuard |
|---|---|---|
| **KSS** (Karolinska, 1–9) | Autoavaliação dos últimos ~5 min: 7 "sono, sem esforço para ficar acordado", 8 "algum esforço", 9 "muito esforço, lutando contra o sono" [2, apêndice] | É a referência legal do DDAW (aviso obrigatório em KSS 8 [2]) e do Euro NCAP (KSS 7 ou mais [1]). Não dá para medir dirigindo sem perguntar, mas dá para **perguntar no app de teste a cada 5 min**, como o DDAW faz na validação [2] |
| **PVT** (tarefa de vigilância psicomotora) | Tempo de reação a estímulos; lapso = resposta > 500 ms (10 min) ou > 355 ms na versão de 3 min (PVT-B) [30] | Impossível dirigindo. Serve antes e depois de sessões de teste, como verdade de campo, e talvez como teste de prontidão no pátio (questão trabalhista, decisão do Matheus) |
| **ORD** (avaliação de sonolência por observador) | Avaliadores treinados dão nota ao rosto em vídeo; a versão do VTTI vai de 0 a 100 sobre 60 s antes do evento [31] | Confiável entre avaliadores e correlacionada com KSS, posição na faixa, EOG e EEG (17 pessoas, 2023) [31]. A concordância com o autorrelato foi fraca em estrada (Ahlström) [31]. **Conflito:** a ORD usa 60 s, e o trecho do O5 tem no máximo 20 s (`PRD.md:56`). Com 20 s, a revisão humana dos trechos não é ORD validada |
| **JDS** (Optalert, 0–10) | Combinação de medidas da piscada, AVR incluída, a cada minuto, com norma populacional [27] | Inspira o "índice populacional" para apontar calibração suspeita (2.3 b) |

### 3.2 Quanto os números do olho dizem

- **No mesmo motorista ao longo do tempo:** KSS e lapsos do PVT andam juntos (r = 0,75) [32]. Entre pessoas, bem menos.
- **Entre pessoas:** PERCLOS × KSS deu r = 0,44 num estudo [32].
- PERCLOS só foi aceitável em **resolução baixa (> 20 min)**. Em janelas de 3 min e por pessoa, a correlação caiu muito
  (Sommer & Golz, 2010; 16 pessoas, simulador) [33].
- Em outro protocolo, o PERCLOS foi a única tecnologia válida entre seis (Mallis) [32]. A literatura diverge.
- Motoristas costumam **perceber** o sono (Williamson et al., 2014; Anderson et al.): o KSS alto previu frenagem de
  emergência nos 15 min seguintes, e nenhum evento grave aconteceu sem sintoma antes. Revisão sistemática de 2021 [34].
- A duração da piscada sobe de forma curvilínea, mais forte no KSS alto (Ingre et al., 2006) [24].
  - Os percentuais "+10% no KSS 7, +23% no 8, +32% no 9" citados em `drowsiness.py:6` **não foram conferidos**: o texto
    completo não abriu.

### 3.3 O `risk.py` faz sentido?

**Faz, na estrutura.**
- O nível vem do pior sinal, com histerese (`risk.py:126-161`).
- O contexto só antecipa e nunca dispara sozinho (`risk.py:77-86`; `context.py:7`).
- Sinais complementares não decidem sozinhos (spec 011, decisão 4).
- O rebote depois de ativação está separado (`risk.py:103-118`).
- Os limiares fortes batem com a literatura:
  - PERCLOS de 3 min ≥ 12% (`drowsiness.py:34`) = AAA [29];
  - microssono, sono e sem resposta em 1, 3 e 6 s (`drowsiness.py:28-30`) = Euro NCAP [1].

**O que muda:**
1. **Separar sono de distração.** Hoje o celular entra no mesmo nível de 0 a 3 (`risk.py:120-124`).
   - Proposta: `risco_sono` (0–3) e `distracao` (0–2) em canais separados; o alarme escolhe o som pelo canal (seção 1.3).
   - O `nivel_risco` do evento pode continuar como o máximo, para o painel.
2. **Faixa de KSS estimada, com honestidade.** Novo campo `sono_estimado` no `resumo_minuto` e no relatório. Não altera
   alarme nem nível:

   | Nível do script | Critério já existente | Faixa declarada | Base |
   |---|---|---|---|
   | 0 | Sem sinais | "sem sinais de sono" (não diz "KSS ≤ 6") | — |
   | 1 atenção | Duração ≥ 1,15× a base, PERCLOS ≥ máx(8%, 1,5× a base), 1 fechamento longo, 2 bocejos ou 2 cabeceios (`drowsiness.py:39-44`) | "sinais compatíveis com KSS 6–7" | Curvilinearidade de Ingre [24]; aviso opcional do DDAW no KSS 7 [2] |
   | 2 alto | Duração ≥ 1,25×, PERCLOS ≥ 12%, ≥ 3 fechamentos longos em 5 min, ≥ 3 cabeceios (`drowsiness.py:33-36`) | "sinais compatíveis com KSS ≥ 8" | AAA [29]; aviso obrigatório do DDAW no KSS 8 [2] |
   | 3 crítico | Olho fechado ≥ 1 s | "sono comportamental (microssono)" | Euro NCAP [1] |

   - Junto, sempre: `confianca` (fps, fração válida, calibração suspeita ou não, `ear_closed_estimated`) e o texto fixo
     "estimativa, não é medida de KSS nem diagnóstico".
   - Fora isso, publicar só a faixa, nunca um "KSS 7,4": a correlação entre pessoas é moderada e varia com a janela
     [32][33].
3. **A sonolência se mantém** (memória de sonolência, seção 1.3), em vez de descer a 0 depois de 60 s.
4. **Validar como o DDAW:** sessões no app de teste com KSS a cada 5 min. Verdadeiro positivo = aviso com KSS vizinho
   ≥ 7. Sensibilidade por participante, com média > 40% [2]. Falsos alarmes por hora em sessões de KSS ≤ 6. Sem isso,
   o O4 (`PRD.md:55`) continua "Aberto".

---

## 4. Contexto da jornada

### 4.1 O que dizem as fontes

- **Hora do dia:**
  - picos de acidentes ligados ao sono por volta de 02h, 06h e 16h (Horne & Reyner, 1995, 679 acidentes) [35]; a SWOV
    resume como 02h–06h e 14h–16h [35];
  - dirigir entre 2h e 5h: OR 5,6 (IC 1,4–22,7); ≤ 5 h de sono nas últimas 24 h: OR 2,7; sentir-se sonolento: OR 8,2
    (Connor et al., 2002, caso-controle) [36].
- **Horas acordado:** depois de 17–19 h sem dormir, o desempenho em alguns testes ficou igual ou pior que com 0,05% de
  álcool no sangue (Williamson & Feyer, 2000). Na maior parte dos testes, segundo o resumo oficial [37].
- **Tempo ao volante:**
  - risco de evento crítico maior na 11ª hora que da 8ª à 10ª;
  - em uma análise, as chances de acidente subiram a partir da 6ª hora;
  - a pausa reduz o risco na hora seguinte [18].
- **Lei** (CTB, art. 67-C, incluído pela Lei 13.103/2015) [38]:
  - no máximo **5 h 30 de direção ininterrupta** (caput);
  - **carga:** 30 min de descanso a cada 6 h, com fracionamento, sem passar de 5 h 30 contínuas (§1º);
  - **passageiros:** 30 min a cada 4 h, com fracionamento (§1º-A);
  - 11 h de descanso em 24 h, com 8 h seguidas no primeiro período (§3º);
  - **"tempo de direção" é só o período "efetivamente ao volante"** entre a origem e o destino (§4º).
- **Fiscalização:** Resolução CONTRAN 525/2015, por tacógrafo, diário de bordo ou ficha de trabalho [39].
  > [!note] Hipótese, confirmar
  > Não achei norma que a revogue nem confirmação de que segue em vigor depois das consolidações do CONTRAN. Conferir no
  > gov.br.

### 4.2 O que o `context.py` faz e o que muda

| Ponto | Código | Problema | Proposta |
|---|---|---|---|
| Madrugada | `NIGHT_HOURS = range(0, 7)` (`context.py:22`) | Larga demais (00h–06h59) e sem a tarde | Duas janelas com peso: **forte** 02h–06h (Connor, Horne & Reyner [35][36]); **moderada** 14h–16h [35]. A forte mantém o efeito de hoje (`risk.py:79-84`); a moderada só entra no relatório e na faixa de confiança |
| Tempo de direção sem telemetria | Rosto visível = dirigindo (`context.py:55`) | **Contraria o §4º do art. 67-C** [38]. Motorista de caminhão descansa e come **dentro da cabine**: o rosto continua na câmera, o descanso nunca conta e `limite_direcao_excedido` fica ligado sem motivo | Sem telemetria, **não afirmar** limite legal: trocar para `tempo_com_rosto_h` com `fonte: "camera"` e linguagem "estimativa". O limite legal só com sinal de movimento (Pi: ignição ou IMU, seção 6). No notebook, testar a hipótese do fluxo óptico no fundo da imagem (janela lateral) para detectar movimento |
| Passageiros | Só a regra de carga (`context.py:19-21`) | RF-03 "Parcial" (`PRD.md:81`) | `tipo_veiculo` (Q5, padrão carga): carga 5 h 30 contínuas; passageiros também 4 h com 30 min. Evento `descanso_previsto_em_atraso` sem alarme sonoro, só `info` e registro |
| Pausa fracionada | Só 30 min seguidos zeram (`context.py:20-21`, `61-62`) | Conservador, correto sem telemetria | Com telemetria, somar frações (§1º) e registrar cada uma |
| Tempo na viagem | Não usado | O risco cresce com as horas ao volante [18] | `horas_desde_inicio` como fator leve, como a madrugada (só antecipa) |
| Horas acordado | Não existe | Sem sensor, não dá para medir | Pergunta opcional no início ("dormiu quantas horas?"), registrada como autorrelato. **Decisão do Matheus** (privacidade, LGPD) |
| Relógio | Ignora ano < 2024 (`context.py:28`, `70`) | Bom. Sem RTC, a hora do Pi pode estar errada mesmo com ano válido (spec 001 §6) | Usar a hora só se `relogio.fonte` for `ntp` ou `rtc` (spec 001 §6.1); senão, `madrugada: null` |

---

## 5. Registro da viagem e trechos curtos (specs 001 e 002)

### 5.1 Registro só por acréscimo

- **Hash encadeado e MAC:** é o desenho clássico de log seguro.
  - Schneier & Kelsey (1999): cada registro depende do anterior, e registro removido quebra a verificação do seguinte.
  - A propriedade de "forward integrity" (Bellare & Yee, 1997) usa **chave que evolui**: quem toma o equipamento no
    instante T não consegue forjar registros de antes de T [40].
- **A spec 001 está bem desenhada:** hash sobre os bytes gravados (§4.1), HMAC com chave derivada por HKDF (§4.2),
  Ed25519 em produção (§4.2) e `exigir_alg` contra a troca para o algoritmo mais fraco.
  - **O que falta:** com a chave privada Ed25519 guardada no cartão, quem leva a caixa depois da viagem e lê a chave
    reassina a viagem inteira (`001:330`).
  - **Proposta (opcional):** além do Ed25519, um HMAC com chave evolutiva: `K_{i+1} = HKDF(K_i, "rotaguard/selo/v1")` a
    cada selo, apagando `K_i`. A empresa recebe `K_0` no pareamento (spec 003).
  - Efeito: quem pega a caixa no instante T não consegue reescrever selos anteriores a T sem ser detectado.
  - Custo: a verificação calcula a cadeia de chaves; o HMAC é simétrico, então a empresa poderia forjar com `K_0`. Por
    isso fica **junto** do Ed25519, nunca no lugar dele.
- **Corte de energia e cartão SD:**
  - a consistência depois de queda depende do sistema de arquivos; o mesmo protocolo de append, `rename` e `fsync` se
    comporta diferente entre os sistemas de arquivos do Linux (Pillai et al., OSDI 2014) [41];
  - a spec 001 já prevê `fsync` por linha, `fsync` do diretório e recuperação sem truncar (§7).
  - **Medido no notebook** (`exp_bench.py`): linha JSON com SHA-256, HMAC e `fsync` em mediana 2,0 ms (p95 4,8 ms).
  - Com ~1.000 linhas em 12 h (`001:226`), o custo é desprezível. No cartão do Pi, medir (spec 005).
  - Na prática, as medidas são raiz somente leitura com overlay, partição de dados separada e cartão de alta
    resistência [42]. Fontes de fórum: tratar como prática, não medida.
- **JSONL ou SQLite WAL:**
  - para o **registro**, JSONL. Mostra o "só acréscimo" no nível de byte, qualquer linguagem verifica e o importador não
    precisa de SQLite. O SQLite reescreve páginas, e "só acréscimo" deixa de ser verificável;
  - para a **fila**, que muda de estado, SQLite. Mas `PRAGMA synchronous=NORMAL` (`event_queue.py:39`) em WAL **pode
    perder transação confirmada** num corte de energia: a base fica íntegra, mas não durável (documentação do SQLite) [43].
  - O comentário "seguro com WAL" vale para integridade, não para durabilidade.
  - Medido: `FULL` custa 2,2 ms por INSERT contra 0,09 ms. Eventos são raros, então **usar `FULL`** até o registro
    existir.

### 5.2 Trechos de vídeo

- **Buffer em memória** (spec 002 §6) com JPEG por quadro:
  - medido 1,6 ms por quadro de 640×480 com qualidade 70 no notebook, numa imagem sintética de 13,6 KB. A spec estima
    30–45 KB num rosto real (`002:141`);
  - AES-256-GCM de 9 MB: 37 ms (`cryptography` 50.0.1). Tudo cabe numa thread separada.
- **Codificação:**
  - **MJPEG em AVI montado em memória** (decisão da spec 002, `002:134-146`): sem nova codificação e sem arquivo sem
    cifra. Correto para começar;
  - **`cv2.VideoWriter`** só escreve em caminho de arquivo, o que deixaria imagem sem cifra no cartão. A spec já descarta;
  - **PyAV** (`av` 19.0.1 no PyPI; não está no `.venv`) codifica H.264 **direto para `BytesIO`**. É o caminho para
    reduzir 5–10× o tamanho sem tocar o disco. Dá para testar no notebook com libx264.
    > [!note] Hipótese, confirmar
    > Não foi testado nesta pesquisa.
  - **Pi 4:** codificador H.264 no chip (`h264_v4l2m2m`). Aceita até o perfil High, nível 4.2. O modo CBR tem relato
    de travar o `/dev/video11` [44]. O `picamera2` tem `H264Encoder` com `CircularOutput` (buffer em segundos antes do
    gatilho), mas só para câmera CSI, não webcam USB [45].
  - **Pi 5:** **não tem codificador H.264.** A Raspberry Pi (white paper de maio de 2026) mediu libx264 em 1080p30 com
    60–90% de um núcleo no modo de baixa latência (ultrafast, zerolatency) [46].
    - Por proporção de pixels, 640×480 a 10 fps seria ~1/20 disso. Hipótese a medir.
- **Cifra:**
  - `AESGCM`: nonce de 12 bytes que **nunca** se repete com a mesma chave; limite de 2³¹−1 bytes por chamada [47];
  - nonce aleatório por arquivo com chave derivada por viagem está correto (`002:153-162`);
  - 12 trechos por viagem ficam muito longe de qualquer limite;
  - a AAD que amarra viagem e número (`002:161`) é boa prática.
- **Corte de energia:** a linha `recorrencia` gravada antes do vídeo (`002:201`) garante o fato mesmo sem o trecho.
- **Swap:** zram ou swap desligado, para o buffer não ir ao cartão (`002:246`).

### 5.3 O que dá para fazer e testar já no notebook

- **Spec 001 inteira:** `registro.py` só com a biblioteca padrão, testes REG-01 a REG-25 com relógio e `fsync`
  injetáveis, e corte simulado truncando o arquivo num byte qualquer.
- **Spec 002 inteira:** buffer, detector, AVI, cifra e testes TRE-01 a TRE-21 com quadros sintéticos. Só a medida no
  Pi fica para depois.
- **Codificador trocável** (`formato` em `trecho_gravado`, `002:203`), com teste do PyAV + libx264 em memória.
- **Fila com `synchronous=FULL`.**

---

## 6. Lista priorizada

Impacto: A = alto, M = médio, B = baixo. Esforço estimado em horas (estimativa minha, sem medir).
Os IDs `ALM-`, `CAL-`, `CTX-` e `REG-` são sugestões de critério de aceite para as specs.

### 6.1 Dá para fazer agora, no notebook

| ID | O quê | Imp. | h | Arquivo | Critério de aceite testável |
|---|---|---|---|---|---|
| SCR-A01 | Corrigir `metrics` indefinido em `draw_overlay` | A | 0,5 | `driver_monitor.py:221-255` | **UI-01:** `draw_overlay` **real** com estado sintético (com e sem `pupil_ratio`) devolve imagem do mesmo tamanho, sem exceção; o teste não troca `draw_overlay` por função falsa |
| SCR-A02 | Fechamento continua contando quando o rosto some logo depois de o olho fechar e a cabeça descer ("possível sono") | A | 5 | `eyes.py:289-293`; `drowsiness.py:345-369`, `399-409` | **ALM-01:** olho fechado 0,6 s, pitch subindo e rosto perdido → alarme crítico em ≤ 2,0 s do fechamento e evento `sono_rosto_perdido` (cenário do `exp_cabeca.py`). **ALM-02:** olhos abertos, cabeça desce e o rosto some 3 s (pegar algo no chão) → nenhum alarme crítico |
| SCR-A03 | Quatro sinais sonoros sintetizados (`info`, `distracao`, `sonolencia`, `critico`), com harmônicos e envelope | A | 6 | `alarm.py:16-46`; `risk.py:37-45` (`RiskAssessment` ganha `alarm_kind`) | **ALM-03:** os 4 WAVs são determinísticos (mesmo SHA-256 em duas gerações); cada pulso tem ≥ 4 harmônicos entre 200 e 8.000 Hz, a ≤ 15 dB do maior; `critico` tem a maior taxa de pulsos; celular nunca gera `critico` |
| SCR-A04 | Reprodução que pode ser interrompida, com preempção, e autoteste ao ligar (RF-04) | A | 5 | `alarm.py:49-131`; `run_monitor.py:211` | **ALM-04:** com player falso, `critico` durante `distracao` interrompe em ≤ 100 ms; `stop()` com o olho aberto para em ≤ 100 ms. **ALM-05:** no início, toca `info` uma vez e registra `estado_aparelho` `sem_saida_de_som` quando nenhum player existe |
| SCR-A05 | Escalonamento por tempo, memória de sonolência e orçamento de alarmes não críticos | A | 6 | `risk.py:24-33`, `126-161`; `drowsiness.py:69` | **ALM-06:** sonolência por 5 min → 2º estágio mais urgente. **ALM-07:** depois de nível 2 por sono, o risco não fica abaixo de 1 até pausa ≥ 15 min ou 30 min sem sinais. **ALM-08:** 20 alertas de celular em 1 h → a partir do N-ésimo, som suave e linha no registro; o crítico nunca é limitado |
| SCR-A06 | Sugestão e verificação de pausa (`pausa_sugerida`, `pausa_detectada`) e "pausa recente" por 1 h | M–A | 4 | `risk.py`; `context.py:46-62` | **CTX-01:** depois de `pausa_sugerida`, rosto ausente 18 min → `pausa_detectada` com `duracao_s` ≈ 1080; sinal leve na hora seguinte sobe para nível 2 em ≤ 60 s |
| SCR-A07 | Frases de voz curtas (WAV próprio) depois do tom | M | 3 + gravação | `alarm.py` | **ALM-09:** `sonolencia` toca tom e depois frase; o texto da frase é igual ao do evento no registro (DDAW §3.4.3.3) |
| SCR-A08 | Referência de fechado robusta à taxa de quadros | M–A | 3 | `calibration.py:110-114` | **CAL-01:** cenário do `exp_calib.py` a 10, 15 e 30 fps → \|ear_closed − 0,06\| ≤ 0,012; a 10 fps, `qualidade_calibracao` ≠ "boa" |
| SCR-A09 | Apontar calibração com sono moderado | A | 4 | `calibration.py:36-38`, `168`; `engine.py:221-239` | **CAL-02:** cenário do `exp_calib2.py` (duração +48%, fechamento de 0,76 s) → calibração suspeita; com perfil salvo, o perfil salvo continua; a acumulada não muda. **CAL-03:** calibração alerta → nada muda (regressão) |
| SCR-A10 | Nova calibração automática só em degrau com causa física | M–A | 8 | `eyes.py:188-208`; `drowsiness.py:257-260`; `visibility.py` | **CAL-04:** degrau de +25% no EAR aberto junto com `eye_distance_px` +20% → novas referências em ≤ 2 min, sem evento de sono. **CAL-05:** queda lenta de 15% no EAR aberto em 20 min, sem mudança de escala, luz ou pose → **sem** nova calibração, e o PERCLOS sobe |
| SCR-A11 | PERCLOS também "por quadros", como a AAA | M | 2 | `drowsiness.py:290-297`, `438-441` | **PER-01:** 3 min com piscadas de 120 ms a 20/min e nenhum fechamento longo → `perclos_quadros_3min` > 0 e `perclos_3min` = 0; os dois saem nos detalhes |
| SCR-A12 | `sono_estimado` (faixa de KSS com confiança) e canais sono × distração | M | 4 | `risk.py:37-45`, `120-131`; `engine.py:252-263` | **RSK-01:** cada nível gera a faixa da tabela 3.3, com o texto fixo "estimativa, não é medida de KSS nem diagnóstico"; celular sozinho mantém `risco_sono` = 0 |
| SCR-A13 | Verdade de campo no app de teste: KSS a cada 5 min e PVT-B de 3 min antes e depois; relatório de sensibilidade e alarmes falsos por hora | A | 10 | `caixa/tela_teste/`; `evaluation.py:104-118`; `ferramentas/` | **VAL-01:** sessão sintética com KSS e alarmes marcados → sensibilidade por participante pela regra do DDAW (Parte 2 §5.1.4) e falsos alarmes/h iguais ao cálculo manual |
| SCR-A14 | Contexto: janelas 02–06 e 14–16, regra de passageiros, sem "limite legal" baseado só no rosto | M | 5 | `context.py:19-22`, `55`, `68-77`; `risk.py:79-92` | **CTX-02:** 03h → `circadiano: "forte"`; 15h → `"moderado"`; 01h → `null`. **CTX-03:** sem telemetria, rosto visível por 6 h → `limite_direcao_excedido` = `null` e `tempo_com_rosto_h` = 6. **CTX-04:** passageiros + telemetria → aviso de descanso em 4 h |
| SCR-A15 | Fila com `synchronous=FULL` | M | 0,5 | `event_queue.py:39` | **FIL-01:** `PRAGMA synchronous` devolve 2 depois de abrir o `EventStore` |
| SCR-A16 | Spec 001 (`registro.py`), com chave evolutiva opcional | A | 20 | novo `caixa/vision/registro.py` | REG-01 a REG-25 da spec 001; **REG-26** (opcional): chave evolutiva apagada depois de cada selo; quem só tem a chave atual não reassina selo anterior sem `assinatura_invalida` |
| SCR-A17 | Spec 002 com codificador trocável e PyAV em memória; atualizar `cryptography` para 50.0.2 | A | 20 | novo `caixa/vision/trechos.py` e `cifra_trechos.py`; `caixa/requirements.txt` | TRE-01 a TRE-21; **TRE-22:** com PyAV + libx264, o trecho decifrado abre como MP4 com o número de quadros declarado e nenhum arquivo do disco contém `ftyp` sem cifra |

### 6.2 Depende do Raspberry Pi (ou de hardware na caixa)

| ID | O quê | Imp. | h | Onde | Critério de aceite |
|---|---|---|---|---|---|
| SCR-P01 | Latência real do alarme (O1, RNF-01) e taxa de quadros real (RNF-02) | A | 4 | spec 005 | **PI-01:** com microfone ou osciloscópio, do 1º quadro com o olho fechado até o som do microssono ≤ 2,5 s (1 s de fechamento + 1,5 s), p95 em 20 ensaios |
| SCR-P02 | Saída de som: Pi 4 (saída de 3,5 mm) ou Pi 5 (USB ou I2S com amplificador); volume ALSA fixado no boot; nível na cabeça do motorista | A | 4 | spec 005; `alarm.py` | **PI-02:** `critico` ≥ 85 dB(A) e ≥ 15 dB acima do ruído medido na cabine em movimento; `info` ≤ 70 dB(A) |
| SCR-P03 | Buzzer: o ativo (`Buzzer`) só muda o ritmo; o passivo (`TonalBuzzer`) toca notas | M | 2 | `alarm.py:64-74`, `111-112` | **PI-03:** os quatro sinais se distinguem só pelo ritmo no buzzer ativo (teste de escuta com 5 pessoas, ≥ 90% de acerto) |
| SCR-P04 | Botão "ciente" e LED de estado (monitorando, sem ver os olhos, calibrando) | M | 4 | `driver_monitor.py`; GPIO | **PI-04:** com os olhos tapados por 10 s, o LED fica no estado "sem monitorar" até voltar (DDAW §3.5.3); o botão só silencia a repetição |
| SCR-P05 | Sinal de movimento: fio de ignição com optoacoplador e/ou IMU | A | 6 | `context.py:31-62` | **PI-05:** motorista na cabine com o motor desligado por 30 min → conta como descanso; o tempo de direção segue o §4º do art. 67-C |
| SCR-P06 | Energia e cartão: medir `fsync` no SD; cartão de alta resistência; raiz somente leitura com overlay; zram; RTC DS3231; desligamento seguro | A | 8 | spec 005 | **PI-06:** 50 cortes de energia aleatórios → 0 linhas completas perdidas, `viagem_interrompida` em todos, sistema sobe em todos |
| SCR-P07 | H.264: Pi 4 (`h264_v4l2m2m` ou `picamera2` com `CircularOutput`) × Pi 5 (libx264) a 640×480 e 10 fps | M | 6 | spec 005; `trechos.py` | **PI-07:** CPU média do codificador ≤ 15% de um núcleo e nenhum quadro de detecção perdido por causa dele |
| SCR-P08 (opcional) | Ruído da cabine pelo microfone da câmera, **só o nível RMS**, nunca áudio, para ajustar o volume | B–M | 6 | `alarm.py` | **PI-08:** nenhum byte de áudio sai da memória; o volume sobe 1 passo a cada 5 dB de ruído. **Decisão do Matheus** (LGPD) |

### 6.3 Ordem sugerida

1. **Agora:** A01 → A02 → A15 → A03 + A04 → A05 → A09 → A08.
2. **Depois:** A11 → A12 → A14 → A06 → A13, para começar a validar o O4.
3. **Em seguida:** A16 e A17 (specs 001 e 002) e A10.
4. **Com o Pi:** P01, P02, P05 e P06 primeiro.

---

## 7. Perguntas para o Matheus

1. **Voz:** frases gravadas pela equipe (recomendado), `espeak-ng` ou Piper (licença GPL-3.0 e das vozes)?
2. **Orçamento de alarmes de celular:** depois de quantos avisos por hora o som fica suave? Sugestão: 6 por hora.
3. **Memória de sonolência:** depois de "sonolência", o risco só volta a 0 depois de pausa de 15 min ou 30 min sem
   sinais. Pode?
4. **"Limite de 5 h 30" sem telemetria:** trocar por "tempo com rosto na câmera (estimativa)" até haver sinal de
   ignição ou IMU?
5. **Verdade de campo:** colocar KSS a cada 5 min e PVT-B de 3 min no RotaGuard Teste, para as sessões de validação?
6. **ORD:** a revisão humana dos trechos fica como revisão simples (20 s), ou os trechos passam a 60 s para permitir
   ORD? Isso muda o O5 e a Q2.
7. **Horas dormidas:** perguntar ao motorista no início da viagem (autorrelato, dado pessoal)?

---

## 8. Fontes

1. Euro NCAP, *Safe Driving – Driver Engagement Protocol*, v1.2, julho de 2026, §1.3.2–1.3.5 e §1.4. Lido no PDF (texto
   extraído em `scratchpad/fontes/euroncap_de_v12.txt`).
   https://cdn.euroncap.com/cars/assets/Euro_NCAP_Protocol_Safe_Driving_Driver_Engagement_v1_2_ebce03a443.pdf
2. Regulamento Delegado (UE) 2021/1341, DDAW, Anexo I. Lido em espelho do texto, que avisa que o EUR-Lex prevalece.
   https://lawplayer.com/eu/act/32021R1341 · https://www.efta.int/eea-lex/32021R1341
3. IEC 60601-1-8, resumos secundários (a norma não foi lida):
   https://cuidevices.com/blog/a-guide-to-iec-60601-1-8-and-medical-alarm-systems ·
   https://ti.com/document-viewer/lit/html/sszt261 ·
   https://puiaudio.com/news/key-updates-to-iec-60601-1-8-what-engineers-need-to-know
4. ISO 7731 (15 dB acima do ruído), por fontes secundárias:
   https://yadda.icm.edu.pl/baztech/element/bwmeta1.element.baztech-2b466ffb-550d-460d-82ac-a90a05ea171b/c/Zera.pdf ·
   https://products.pfannenberg.com/de-en/Signaling-Technologies/Audible-Signaling/Loudness-is-not-everything/ ·
   https://patents.google.com/patent/US7346172
5. ISO 15006:2011, escopo: https://www.iso.org/standard/55322.html ·
   https://webstore.ansi.org/preview-pages/ISO/preview_ISO+15006-2011.pdf
6. ISO 15005:2017, escopo: https://webstore.ansi.org/preview-pages/ISO/preview_ISO+15005-2017.pdf
7. Edworthy, Loxley & Dennis (1991); Hellier, Edworthy & Dennis (1993); Suied, Susini & McAdams (2008):
   https://researchportal.plymouth.ac.uk/en/publications/improving-auditory-warning-design-quantifying-and-predicting-the- ·
   https://www.mcgill.ca/mpcl/files/mpcl/suied_2008_jepappl.pdf
8. Bruck, Thomas & Rouillard (2009), *J Sleep Res* 18(2): https://vuir.vu.edu.au/2059/ ·
   https://publications.iafss.org/publications/fss/9/403
9. Bruck (revisão), *The who, what, where and why of waking to fire alarms*: https://vuir.vu.edu.au/1393/
10. Voz × bipe × ícone sonoro: Graham (1999) https://informahealthcare.com/doi/full/10.1080/001401399185108 ·
    Bella et al. (2017) https://iris.uniroma3.it/bitstream/11590/328698/7/Bella%20TR-F%202017%20-%20pre%20print.pdf ·
    https://research.tudelft.nl/files/133147536/s12193_022_00390_6.pdf
11. Lees & Lee (2007), alarmes imperfeitos: https://user.engineering.uiowa.edu/~csl/publications/pdf/Lees%20Lee%202007.pdf
12. Gaspar et al. (2017), *Traffic Inj Prev* 18(sup1):S58-S63:
    https://iro.uiowa.edu/esploro/outputs/journalArticle/Evaluating-driver-drowsiness-countermeasures/9984627294802771
13. Horne & Reyner (1999), *Occup Environ Med* 56:289: https://oem.bmj.com/content/56/5/289
14. Reyner & Horne (1997), *Psychophysiology* 34(6):721-5: https://pubmed.ncbi.nlm.nih.gov/9401427/
15. Cochilos curtos e inércia do sono: https://pmc.ncbi.nlm.nih.gov/articles/PMC4763354/ ·
    https://digital.library.adelaide.edu.au/items/3314e5ee-e2af-4e68-a541-99e22d7a654d
16. Reyner & Horne (1998), *Sleep* 21(1):46-50: https://www.ncbi.nlm.nih.gov/pubmed/9485532 · Schwarz et al. (2012):
    https://swov.nl/en/publicatie/car-countermeasures-open-window-and-music-revisited-real-road-popular-hardly-effective
17. NHTSA, *In-Vehicle Drowsy Driving Detection and Alerting*, DOT HS 813 439 (2023), lido no PDF:
    https://rosap.ntl.bts.gov/view/dot/67405
18. FMCSA, tempo de tarefa e pausas: https://trid.trb.org/view/1108816 ·
    https://vtechworks.lib.vt.edu/handle/10919/55114
19. Green (2000), *Transportation Human Factors* 2(3), por fonte secundária:
    https://lists.techfak.uni-bielefeld.de/pipermail/systemsafety/2015-July/002119.html
20. gpiozero, `Buzzer` e `TonalBuzzer`: https://gpiozero.readthedocs.io/en/stable/api_output.html
21. Piper TTS, licença (fontes secundárias): https://gitee.com/vhow/piper1-gpl ·
    https://www.promptquorum.com/pt/power-local-llm/piper-tts-review
22. Ruído na cabine de caminhão: https://www.ioa.org.uk/system/files/publications/D%20WILLIAMS%20W%20TEMPEST%20NOISE%20AND%20THE%20LORRY%20DRIVER.pdf ·
    https://ince.publisher.ingentaconnect.com/contentone/ince/ncej/2014/00000062/00000003/art00003
23. Dewi et al. (2022), *PeerJ CS*: https://peerj.com/articles/cs-943 · patente EP 4105827:
    https://data.epo.org/gpi/EP4105827A1
24. Ingre et al. (2006), *J Sleep Res* 15(1):47-53: https://swov.nl/nl/publicatie/subjective-sleepiness-simulated-driving-performance-and-blink-duration-examining
25. Wolter, Berrio Perez & Shan (2025), *Blinking Beyond EAR*: https://arxiv.org/html/2511.19519v1
26. Mulhall et al. (2020), *Accid Anal Prev*: https://ahro.austin.org.au/austinjspui/handle/1/22230
27. Johns Drowsiness Scale: https://www.optalert.com/?p=1707 · https://pmc.ncbi.nlm.nih.gov/articles/PMC4418540
28. Mistura de gaussianas e Otsu no estado do olho: https://ejournal.raharja.ac.id/index.php/ccit/article/view/3614
29. Owens et al. (2018), AAA Foundation, *Prevalence of Drowsy-Driving Crashes* (lido no PDF):
    https://www.michiganautolaw.com/wp-content/uploads/2018/08/AAA-FTS-study-Prevalence-of-Drowsy-Driving-February-2018.pdf
30. Basner, Mollicone & Dinges (2011), PVT-B: https://pmc.ncbi.nlm.nih.gov/articles/PMC3197786
31. ORD: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10166535/ ·
    https://vtechworks.lib.vt.edu/items/62e6aa6a-a034-4141-a8fa-b170c7904af9 ·
    https://etrr.springeropen.com/articles/10.1007/s12544-015-0188-y
32. KSS, PVT e PERCLOS: https://research.monash.edu/en/publications/awareness-of-sleepiness-temporal-dynamics-of-subjective-and-objec/ ·
    https://researchdiscovery.drexel.edu/esploro/outputs/doctoral/991021889097704721 ·
    https://xnjdxb.swjtu.edu.cn/en/article/doi/10.3969/j.issn.0258-2724.2014.04.025
33. Sommer & Golz (2010), IEEE EMBC: https://swov.nl/en/publicatie/evaluation-perclos-based-current-fatigue-monitoring-technologies-paper-presented-2010
34. Percepção do sono: https://www.psychologicalscience.org/news/motr/can-people-tell-when-theyre-too-sleepy-to-drive-safely.html ·
    https://research.birmingham.ac.uk/en/publications/i-think-im-sleepy-therefore-i-am-awareness-of-sleepiness-while-dr
35. Horne & Reyner (1995), *BMJ* 310:565: https://www.bmj.com/content/310/6979/565 ·
    https://swov.nl/nl/publicatie/sleep-related-vehicle-accidents
36. Connor et al. (2002), *BMJ* 324:1125: https://pubmed.ncbi.nlm.nih.gov/12003884/
37. Williamson & Feyer (2000), *Occup Environ Med*: https://www.infrastructure.gov.au/infrastructure-transport-vehicles/road-transport-infrastructure/safety/publications/2000/Fatig_Alc
38. CTB, art. 67-C (Lei 13.103/2015): https://modeloinicial.com.br/lei/CTB/codigo-transito-brasileiro/art-67c ·
    https://ctbdigital.com.br/artigo-comentarista/466/
39. Resolução CONTRAN 525/2015: https://www.gov.br/transportes/pt-br/assuntos/transito/conteudo-contran/resolucoes/resolucao5252015c.pdf
40. Schneier & Kelsey (1999), *Secure Audit Logs to Support Computer Forensics*:
    https://www.schneier.com/academic/archives/1999/05/secure_audit_logs_to.html
41. Pillai et al. (2014), OSDI: https://research.cs.wisc.edu/adsl/Publications/alice-osdi14.html
42. Raspberry Pi e cartão SD em corte de energia (fóruns): https://community.tmpdir.org/t/raspberry-pi-and-sd-card-corruption/444 ·
    https://lemmy.ndlug.org/post/268904/837675
43. SQLite, `synchronous` em WAL: https://sqlite.org/forum/forumpost/9d6f13e346231916?raw ·
    https://avi.im/blag/2025/sqlite-fsync/
44. `h264_v4l2m2m` no Pi 4: https://lists.mplayerhq.hu/pipermail/ffmpeg-devel/2022-March/294446.html ·
    https://ffmpeg.org/pipermail/ffmpeg-user/2024-May/057955.html
45. `picamera2`, `CircularOutput`: https://deepwiki.com/raspberrypi/picamera2/6.1-file-and-circular-outputs ·
    https://lists.libcamera.org/pipermail/libcamera-devel/2022-July/031974.html
46. Raspberry Pi Ltd, *H.264 encoding performance on Raspberry Pi 5 series computers*, RP-010033-WP-1 (lido no PDF):
    https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-010033-WP-1-H.264%20encoding%20performance%20on%20Raspberry%20Pi%205_series%20computers.pdf
47. `cryptography`, AEAD (`AESGCM`): https://cryptography.io/en/latest/hazmat/primitives/aead/

### Experimentos desta pesquisa (scratchpad)

Pasta base: `C:\Users\MATHEU~1\AppData\Local\Temp\claude\c--Users-Matheus-Corte-Downloads-Vigilancia-Motorista-main-Vigilancia-Motorista-main\b92b8a20-6be0-44e6-8616-27345e1b8984\scratchpad\`

| Script | O que prova |
|---|---|
| `scripts\check_overlay.py` | `NameError` em `draw_overlay` |
| `scripts\exp_cabeca.py` | Microssono perdido quando o rosto some |
| `scripts\exp_calib.py` | Viés de `ear_closed` por fps; calibração muito sonolenta é apontada |
| `scripts\exp_calib2.py` | Calibração com sono moderado passa como alerta |
| `scripts\exp_som.py` | Espectro da sirene atual e três sons candidatos em `sons\` |
| `scripts\exp_bench.py` | `fsync`, SQLite NORMAL × FULL, JPEG, AES-GCM no notebook (não vale para o Pi) |

- Todos rodaram com o Python 3.14.5 do `.venv` do repositório: numpy 2.5.3, OpenCV 5.0.0, cryptography 50.0.1.
- No PyPI, em 19/10/2026: numpy 2.5.4, cryptography 50.0.2, av 19.0.1, sounddevice 0.5.6.
