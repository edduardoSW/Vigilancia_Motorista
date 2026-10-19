# Pesquisa: pulso pela câmera (rPPG) no script da caixa RotaGuard

Data: 19/10/2026. Autor: subagente de pesquisa (Claude). Nenhum arquivo do repositório foi alterado.
Protótipos e figuras ficaram só no scratchpad (caminhos no fim).

Legenda: **[fonte]** = afirmação com link; **[código]** = lido no repositório (`arquivo:linha`);
**[medido]** = rodei aqui, em sinal sintético; **Hipótese** = sem fonte, precisa medir ou confirmar.

---

## 0. Onde isso entra no código atual (leitura do repositório)

- **Fluxo por quadro** [código]: `DriverMonitor.run` lê o quadro → `process_frame` → `FaceAnalyzer.analyze(frame, timestamp)`
  devolve `FaceMetrics` → `DriverStateEngine.update(metrics, frame)` → alarme e eventos
  (`caixa/vision/driver_monitor.py:172-183`, `caixa/vision/engine.py:97-129`).
- **Os 478 pontos não saem do `face.py`** [código]: `points` (478×2, em pixels) é montado em `face.py:247`, mas
  `FaceMetrics` guarda só os 12 pontos dos olhos e os 2 das orelhas (`face.py:299`, `face.py:313`). O módulo novo
  precisa de um campo `landmarks` em `FaceMetrics` (é só referenciar o array que já existe; custo zero).
  - Não pesa na calibração: `Sample.from_metrics` copia só campos escalares nomeados (`eyes.py:41-62`).
- **Modo infravermelho já é detectado** [código]: `InfraredDetector` decide pela maioria dos últimos 90 quadros sem
  cor (`pupil.py:31-58`) e `FaceMetrics.infrared` chega pronto (`face.py:106`, `face.py:238`). O rPPG deve usar isso
  para trocar POS (cor) por canal único (IR).
- **Frame chega ao engine** [código]: `engine.update(metrics, frame)` já recebe o quadro (usado pelo celular,
  `engine.py:110`). É o ponto natural para `self.cardio.update(frame, metrics)`.
- **Avaliação a cada 1 s** [código]: `EVALUATE_EVERY_S = 1.0` (`engine.py:35`, `engine.py:119-121`). A estimativa de
  pulso (janela de 10 s, passo 1 s) cabe nesse mesmo ritmo.
- **Privacidade já tem molde** [código]: `PRIVATE_KEYS` tira métricas sensíveis de qualquer evento fora do modo
  "enviar" (`engine.py:39-40`, `engine.py:223-235`); `live_status` só manda ativação com "enviar"
  (`driver_monitor.py:207-209`). O pulso deve entrar exatamente nesse esquema (ou mais restrito).
- **YuNet não tem pontos do rosto** (`face.py:320-322`): sem MediaPipe, o pulso fica desligado.
- **Câmera** [código]: 640×480 por padrão (`camera.py:35`, `run_monitor.py:76-77`); o Picamera2 entrega BGR em
  `RGB888` (`camera.py:105-107`) e já lê metadados por quadro (só `Lux` hoje, `camera.py:123-127`). Exposição,
  ganho e balanço de branco **não são travados** em lugar nenhum (Hipótese de impacto, ver §4).
- **scipy não é dependência** [código]: `caixa/requirements.txt` só tem `mediapipe==1.0.1` e
  `opencv-contrib-python==5.0.0.93` (numpy vem junto).

### Conflitos com o que já está decidido (apontar ao Matheus antes de seguir)

1. **PRD §5, "Fora de escopo agora"**: "Pulseira de frequência cardíaca […] ficam 'para muito depois'"
   (`docs/produto/PRD.md:63-64`). O pedido novo é pulso **pela câmera**, não pulseira, mas é o mesmo dado (frequência
   cardíaca). Precisa virar decisão registrada no PRD (RF novo) antes da spec.
2. **Regras de imagem do site** proíbem "número de batimentos, ícone de coração, linha de eletrocardiograma"
   (`docs/site/midia/00-regras-gerais.md:387`). Mostrar bpm na janela de teste não fere a regra (ela é das peças do
   site), mas mostra que o posicionamento até aqui evitou "cara de saúde". Vale ele decidir se o pulso aparece só no
   app de teste/demonstração.
3. **RNF-10 (licenças)**: as duas bibliotecas de rPPG mais conhecidas não passam (ver §7).

---

## 1. Algoritmos clássicos sem treino

### 1.1 Comparação

| Método | Ideia | Com movimento / luz variando | Custo |
|---|---|---|---|
| GREEN (Verkruysse 2008) | média do verde | o pior: no benchmark do POS teve SNR médio −1,90 dB contra 5,16 dB do POS [fonte: Wang 2017, Tabela I] | mínimo |
| CHROM (de Haan & Jeanne 2013) | 2 sinais de crominância, `S = X − αY` | bom; ~2º lugar em rotação/fala | baixo |
| PBV (de Haan & van Leest 2014) | projeção na assinatura do volume sanguíneo | o melhor em exercício físico, um pouco pior parado [fonte: Wang 2017, §VI.4] | baixo (3×3 por janela) |
| POS (Wang 2017) | plano ortogonal ao tom de pele, `h = S1 + αS2` | melhor média geral: SNR 5,16 dB [fonte: Wang 2017, Tabela I] | baixo |
| LGI (Pilz 2018) | remove a 1ª componente (SVD) | bom no PURE, fraco no UBFC [fonte: rPPG-Toolbox] | baixo (SVD 3×3) |
| OMIT (Casado & López 2023) | QR em vez de SVD, mesma ideia do LGI | entre os melhores num comparativo [fonte: PMC9598377] | baixo |

Benchmarks independentes (MAE em bpm) do rPPG-Toolbox [fonte: [arXiv 2210.00716, Apêndice G, Tabelas 7 e 8](https://arxiv.org/html/2210.00716v3)]:

| Método | UBFC-rPPG | PURE | MMPD (celular, movimento, luz e pele variadas) |
|---|---|---|---|
| GREEN | 19,73 | 10,09 | 21,68 |
| ICA | 16,00 | 4,77 | 18,60 |
| CHROM | 4,06 | 5,77 | 13,66 |
| LGI | 15,80 | 4,61 | 17,08 |
| PBV | 15,90 | 3,92 | 17,95 |
| **POS** | **4,08** | **3,67** | **12,36** |

- No MMPD, todos os métodos sem treino têm correlação quase nula com a referência (POS ρ = 0,18) [mesma fonte]:
  **em condição difícil (movimento, luz e celular), o clássico quebra**. Isso é o que esperar dentro de um caminhão.
- Kim, Lee & Sohn (2021) também usaram POS e CHROM por terem "relatively less spread in MAE and PCC"
  [fonte: [PMC8659899](https://pmc.ncbi.nlm.nih.gov/articles/PMC8659899/)].
- Comparativo de métodos: "The best performing rPPG methods in all categories were the POS, LGI, and OMI methods"
  [fonte: [PMC9598377](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9598377/)].
- **Recomendação de padrão no Pi: POS** (melhor SNR médio em Wang 2017; no Toolbox empata com o CHROM no UBFC e é o
  melhor no PURE e no MMPD; sem filtro interno, sem treino, poucas linhas de numpy). CHROM como segunda opinião barata (pode votar com o POS). Em câmera IR monocromática nenhum dos dois
  se aplica (precisam de 3 canais): usa-se canal único (§4).

### 1.2 POS, passo a passo (Wang, den Brinker, Stuijk & de Haan, IEEE TBME 64(7), 2017)

Texto do Algoritmo 1, conferido no preprint [fonte: [pure.tue.nl, preprint TBME-00467-2016](https://pure.tue.nl/ws/files/31563684/TBME_00467_2016_R1_preprint.pdf)]:

```
Entrada: N quadros. Inicializa H = zeros(N), l = 32 (câmera de 20 fps) → l = ceil(1,6 s × fs)
para n = 1..N:
  C(n) = [R(n), G(n), B(n)]ᵀ                       ← média espacial da pele (ROI)
  m = n − l + 1; se m > 0:
    Cn = C[m..n] / média(C[m..n]) por canal          ← normalização temporal
    S  = [[0, 1, −1], [−2, 1, 1]] · Cn               ← projeção
    h  = S1 + (σ(S1)/σ(S2)) · S2                     ← "alpha-tuning"
    H[m..n] += h − média(h)                           ← overlap-add
Saída: H (sinal de pulso)
```

- Janela: "l = 32 given a 20 fps camera, which measures cardiac activities in 1.6 s […] [40, 240] beat per minute".
- Sobreposição: "the window slides 1 frame for the overlap-adding (i.e., overlap-adding length is thus l−1)".
- O POS original **não usa passa-faixa** ("even the commonly used band-pass filtering is not used"); a filtragem
  fica no pós-processamento (§3).
- Ordem dos canais: **R, G, B**. O OpenCV entrega BGR: inverter antes (`rgb = bgr[..., ::-1]`).

Versão numpy vetorizada (testada aqui, ver §9.4):

```python
def pos(rgb, fs, win_s=1.6):            # rgb: (N, 3) em R, G, B, amostrado uniformemente
    n = rgb.shape[0]; l = int(np.ceil(win_s * fs))
    w = np.lib.stride_tricks.sliding_window_view(rgb, (l, 3))[:, 0]   # (N-l+1, l, 3)
    cn = w / w.mean(axis=1, keepdims=True)
    s1 = cn[..., 1] - cn[..., 2]                    # G − B
    s2 = -2 * cn[..., 0] + cn[..., 1] + cn[..., 2]  # −2R + G + B
    sd2 = s2.std(axis=1, keepdims=True)
    alpha = np.divide(s1.std(axis=1, keepdims=True), sd2, out=np.zeros_like(sd2), where=sd2 > 0)
    h = s1 + alpha * s2
    h -= h.mean(axis=1, keepdims=True)
    out = np.zeros(n)
    for k in range(h.shape[0]):                     # overlap-add
        out[k:k + l] += h[k]
    return out
```

### 1.3 CHROM, passo a passo (de Haan & Jeanne, IEEE TBME 60(10), 2013)

- Eixos de projeção: `[[3, −2, 0], [1.5, 1, −1.5]]`, e o CHROM usa `S1 − α·S2` porque os dois sinais saem em
  antifase [fonte: Wang 2017, nota 6, citando o CHROM].
- Forma usada no rPPG-Toolbox (lida no código-fonte, só como referência; **não copiar**, licença no §7)
  [fonte: [CHROME_DEHAAN.py](https://github.com/ubicomplab/rPPG-Toolbox/blob/main/unsupervised_methods/methods/CHROME_DEHAAN.py)]:
  janela 1,6 s (par), passo de meia janela (50%), Butterworth ordem 3 de 0,7 a 2,5 Hz em X e Y, janela de Hann e
  overlap-add.

```
para cada janela de l amostras (passo l/2):
  Cn = C / média(C)            (por canal)
  X = 3·Rn − 2·Gn
  Y = 1,5·Rn + Gn − 1,5·Bn
  Xf, Yf = passa_faixa(X), passa_faixa(Y)
  α = σ(Xf) / σ(Yf)
  S_janela = (Xf − α·Yf) · hann(l)
  overlap-add com 50%
```

- **Armadilha medida aqui** [medido]: filtrar X e Y **dentro** da janela de 1,6 s com FFT não funciona (resolução de
  0,625 Hz; o pulso de 55 bpm caiu fora da banda e o erro foi a 19–71 bpm). Ou se usa IIR (Butterworth, como o
  Toolbox), ou se filtra X e Y na janela longa (10 s) com a normalização por média móvel de 1,6 s e só o α é por
  sub-janela. Com a segunda forma o CHROM ficou com erro < 1 bpm nos casos sem ruído extra (§9.4).

### 1.4 Os outros (para completar; conferir na fonte antes de implementar)

Forma descrita nas implementações de referência (pyVHR e rPPG-Toolbox). **Hipótese** quanto aos detalhes exatos:
- **GREEN**: `p = G / média(G) − 1`.
- **PBV**: `Cn` normalizado (3×l); `Pbv = σ(Cn por canal) / ‖σ‖`; `W = Pbv · (Cn·Cnᵀ)⁻¹`; `p = W·Cn / (Pbv·W)`.
- **LGI**: `U = SVD(C·Cᵀ)`; `P = I − u1·u1ᵀ`; `p = (P·C)[1]`.
- **OMIT**: `Q, R = QR(C)`; `P = I − q1·q1ᵀ`; `p = (P·C)[1]`.

---

## 2. Regiões da pele (ROI) a partir dos pontos do MediaPipe

### 2.1 O que a literatura diz

- Kim, Lee & Sohn (Sensors 2021) dividiram o rosto em regiões pelo **MediaPipe Face Mesh** e testaram 7 métodos. As 5
  melhores: **malar direita (1º), glabela (2º), testa medial inferior (3º), testa medial superior (4º), malar
  esquerda (5º)**. As 5 piores: laterais do nariz e lábio superior. Com POS no UBFC: MAE 1,85 bpm (TOP-5) vs 7,26
  (BOT-5) [fonte: [PMC8659899](https://pmc.ncbi.nlm.nih.gov/articles/PMC8659899/)]. O artigo **não lista os índices
  em texto** (só numa figura).
- Testa e bochechas são as três ROI mais promissoras na literatura revisada pelo CinC 2024
  [fonte: [CinC2024-459](https://www.cinc.org/archives/2024/pdf/CinC2024-459.pdf)]; bochechas com o Face Mesh deram
  a melhor FC num estudo de Durham [fonte: [durham-repository 1748767](https://durham-repository.worktribe.com/OutputFile/1748767)].
- Listas de índices de alta prioridade do pyVHR (fato, não código; a biblioteca é GPL) [fonte:
  [pyVHR `extraction/utils.py`, classe MagicLandmarks](https://github.com/phuselab/pyVHR/blob/master/pyVHR/extraction/utils.py)]:
  - testa: `10, 67, 69, 104, 108, 109, 151, 299, 337, 338`
  - bochecha (lado esquerdo da imagem): `36, 47, 50, 100, 101, 116, 117, 118, 119, 123, 126, 147, 187, 203, 205, 206, 207, 216`
  - bochecha (lado direito da imagem): `266, 280, 329, 330, 346, 347, 348, 355, 371, 411, 423, 425, 426, 427, 436`

### 2.2 Polígonos propostos (conferidos no modelo canônico do MediaPipe)

Desenhei os polígonos sobre o `canonical_face_model.obj` oficial do MediaPipe (Apache-2.0)
[fonte: [mediapipe/modules/face_geometry/data](https://github.com/google-ai-edge/mediapipe/blob/master/mediapipe/modules/face_geometry/data/canonical_face_model.obj)]
e conferi visualmente: nenhum toca sobrancelha, olho, nariz ou boca (figura em
`C:\Users\MATHEU~1\AppData\Local\Temp\claude\c--Users-Matheus-Corte-Downloads-Vigilancia-Motorista-main-Vigilancia-Motorista-main\b92b8a20-6be0-44e6-8616-27345e1b8984\scratchpad\mp\rois_small.png`).

```python
# Ordem do contorno; "esquerda/direita" = lado da IMAGEM (o 33 do face.py, olho direito do motorista, fica à esquerda).
TESTA            = (69, 108, 151, 337, 299, 296, 336, 9, 107, 66)   # testa medial inferior + glabela alta
TESTA_ALTA       = (109, 10, 338, 337, 151, 108)                     # opcional: perto do cabelo/boné
BOCHECHA_ESQ_IMG = (117, 118, 119, 100, 36, 205, 187, 123)           # malar
BOCHECHA_DIR_IMG = (346, 347, 348, 329, 266, 425, 411, 352)           # espelho exato da anterior
```

- Margens: a borda de baixo da testa segue a linha de cima das sobrancelhas (`66→107` e `336→296`); a borda de cima
  das bochechas fica uma fileira abaixo da pálpebra inferior (`117-118-119` / `346-347-348`); a borda de baixo
  (`187-205-36`) fica acima do sulco da boca (`216`, `92`) e longe da asa do nariz.
- **Evitar**:
  - olhos (piscar muda a intensidade na frequência das piscadas), sobrancelhas, boca (fala), laterais do nariz (piores
    regiões de Kim 2021);
  - **barba**: a parte baixa da bochecha some em quem tem barba. Não dá para saber pelos pontos; a ponderação por
    SNR (abaixo) derruba a ROI ruim sozinha. **Hipótese**: um teste extra de "pele" (desvio-padrão alto dentro da
    ROI = textura de barba) ajudaria;
  - **testa alta**: cabelo, franja e boné. Por isso fica fora por padrão;
  - **bochecha do lado que vira**: com |yaw| > ~25° a bochecha do fundo fica oblíqua e pequena (**Hipótese**:
    limiar a calibrar; `face.py` já usa a razão de larguras dos olhos com 0,7, `face.py:50`).
- **Pixels saturados ou escuros**: excluir da máscara `≥ 250` (o `face.py` já usa 250 como reflexo, `face.py:57`) e
  `≤ 15`. ROI com menos de ~200 px úteis é descartada (**Hipótese**; Kim 2021 relata média de 696 px nas TOP-5 contra
  ~25 000 no rosto inteiro, e mesmo assim acertaram mais).
- **Pontos tremendo**: Nowara 2018 viu, no carro, que redetectar os pontos "had detrimental effects on the rPPG
  signals" porque a ROI muda um pouco a cada quadro [fonte: [MERL TR2018-067](https://www.merl.com/publications/docs/TR2018-067.pdf),
  §4.3.1]. Suavizar os vértices (média exponencial ou filtro One Euro) antes de montar a máscara.

### 2.3 Combinação das ROIs ponderada por SNR

1. Extrair o pulso de cada ROI separadamente (POS em cada uma).
2. Para cada ROI, espectro e SNR (§3.6) na janela de 10 s.
3. Peso `w_i = max(0, 10^(SNR_i/10))` (potência relativa); ROI com SNR abaixo do piso tem peso 0.
4. Pulso final = soma dos pulsos normalizados (`p_i / σ(p_i)`) × peso, **ou** média dos espectros ponderada (mais
   robusta a fase diferente entre ROIs). Recomendo a soma de espectros (**Hipótese**; é o que o distancePPG faz em
   espírito, com pesos por região, citado em Nowara 2018 §4.1.1).
5. Concordância entre ROIs vira parte da confiança: se a testa e uma bochecha concordam em ±5 bpm, a confiança sobe.

---

## 3. Processamento do sinal

### 3.1 Taxa de quadros irregular

O loop do Pi não tem fps fixo (análise síncrona, `driver_monitor.py:223-249`). Guardar `(t, média RGB por ROI)` com o
carimbo do quadro e **reamostrar por interpolação linear numa grade uniforme** (30 Hz na webcam; 15 ou 20 Hz no Pi)
antes do POS:

```python
grid = np.arange(t[0], t[-1], 1 / fs)
rgb_u = np.stack([np.interp(grid, t, rgb[:, c]) for c in range(3)], axis=1)
```

- Buraco > 0,5 s (rosto perdido, olho tampado): **zerar o buffer**; não interpolar por cima (**Hipótese**: limiar).
- Teste [medido]: com tremor de ±30% do intervalo entre quadros, o erro continuou < 1 bpm (§9.4).

### 3.2 Remoção de tendência (Tarvainen, Ranta-Aho & Karjalainen, IEEE TBME 49(2), 2002)

`z_estacionário = (I − (I + λ²·D₂ᵀD₂)⁻¹)·z`, com D₂ a matriz de segunda diferença (N−2 × N)
[fonte: referência citada em [physiozoo](https://physiozoo.readthedocs.io/en/1.0.2/mhrv/sections/mhrv.rri.html);
forma idêntica no `utils.detrend` do rPPG-Toolbox, que usa `lambda_value ** 2`].

- **λ depende do fs**: o mesmo número dá cortes muito diferentes. Medi o corte (−3 dB) com N = 300 e fs = 30 Hz
  [medido]: λ = 100 → 0,60 Hz (perto demais de 0,7 Hz: come pulso de 42–50 bpm); λ = 200 → 0,42 Hz;
  **λ = 300 → 0,34 Hz (recomendado)**; λ = 500 → 0,27 Hz.
- **Custo**: resolver o sistema 300×300 a cada janela custou 18,8 ms [medido]. Como N é fixo depois da
  reamostragem, **pré-calcular a matriz uma vez** e aplicar como produto: 0,03 ms por janela [medido].

### 3.3 Passa-faixa 0,7–3,5 Hz (42–210 bpm)

- Em numpy puro: zerar o espectro (rFFT) fora de 0,7–3,5 Hz e voltar (irFFT) na janela de 10 s. Simples e sem fase.
- Com scipy: Butterworth ordem 2 ou 3 + `filtfilt` (o Toolbox usa 0,75–2,5 Hz, que corta FC acima de 150 bpm;
  para motorista em repouso serve, mas 3,5 Hz é mais seguro).

### 3.4 Estimativa da frequência

- **Janela de 10 s, passo de 1 s** (casa com `EVALUATE_EVERY_S`).
- **Resolução**: 10 s dão 0,1 Hz = **6 bpm** de resolução nativa; o próprio Nowara escolheu o erro de 6 bpm porque
  "6 bpm is the expected frequency resolution on a 10 second window assuming no zero-padding" [fonte:
  [MERL TR2018-067](https://www.merl.com/publications/docs/TR2018-067.pdf), §4.1.1]. Por isso:
  zero-padding (nfft 4096) + **interpolação parabólica do pico** + rastreamento temporal.
- Welch: segmentos de 8 s com 50% de sobreposição dentro da janela, Hann. Pico só dentro de 0,7–3,5 Hz.
- **Harmônico**: se houver pico em `f/2` dentro da banda com potência ≥ ~50% do pico principal, preferir `f/2`
  (**Hipótese**: regra a calibrar; erro clássico é pegar o 2º harmônico).

```python
def pico_parabolico(f, p):
    i = indice_do_maximo_na_banda
    a, b, c = p[i-1], p[i], p[i+1]
    return f[i] + 0.5 * (a - c) / (a - 2*b + c) * (f[1] - f[0])
```

### 3.5 Rastreamento temporal

- Estado: mediana das últimas 5 estimativas aceitas (5 s). Estimativa que salta > 10 bpm da mediana em 1 s só é
  aceita se repetir em 2 janelas seguidas (**Hipótese**: limites a calibrar com UBFC/PURE).
- Alternativa: Kalman 1D com estado = FC, processo σ ≈ 2 bpm/s, medição σ ∝ 1/SNR. Mais elegante, mesmo efeito;
  começar pela mediana (mais fácil de testar).

### 3.6 Qualidade: SNR no estilo de Haan

`SNR = 10·log10( Σ (U(f)·P(f)) / Σ ((1 − U(f))·P(f)) )`, com `U(f) = 1` em volta da fundamental e do 1º harmônico.
A largura varia na literatura: ±0,2 Hz [fonte: patente US 11229372, citando de Haan 2013,
[uspto](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11229372)], ou ±6 bpm na fundamental e
±12 bpm no harmônico [fonte: [arXiv 2107.13193](https://arxiv.org/pdf/2107.13193)]. O POS usa a mesma métrica: "the
ratio between the energy around the first two harmonics and remaining parts in the frequency spectrum" [fonte: Wang
2017, §V.B]. **Sem referência (sem oxímetro), usar o próprio pico estimado como f0.**

- Recomendação: `U` = `f0 ± 0,1 Hz` e `2·f0 ± 0,2 Hz`; soma em 0,7 a 7 Hz (o harmônico de 3,5 Hz vai até 7 Hz).
- [medido] Com ruído puro (sem pulso), o SNR ficou entre −7,7 e −3,3 dB; com pulso detectável, POS ficou entre
  +1 e +3 dB e GREEN entre +3 e +6 dB. **O piso tem de ser calibrado em dados reais** (§10), mirando ≤ 5% de número
  falso em trechos sem pulso.

### 3.7 Regra para NÃO mostrar número

Mostrar "Pulso estimado: 72 bpm" só quando **tudo** abaixo vale; senão, mostrar o estado ("medindo…", "sinal fraco",
"muito movimento", "luz ruim", "câmera lenta"):

1. rosto encontrado e MediaPipe ativo em ≥ 90% dos últimos 10 s;
2. fps efetivo ≥ 15 (abaixo disso o erro piorou muito no sintético: 10 fps → MAE 5,4 bpm e máximo 36 bpm [medido]);
3. movimento da cabeça abaixo do limite (deslocamento médio dos pontos < X% da distância entre os olhos por
   segundo; **Hipótese**: X a calibrar) e sem mão no rosto (`face_touch`, já existe);
4. sem mudança brusca de exposição/ganho na janela (§4.3);
5. SNR combinado ≥ piso calibrado **e** pelo menos 2 ROIs concordando em ±5 bpm, ou 1 ROI com SNR bem acima do piso;
6. 3 janelas seguidas consistentes (aquecimento de ~12 a 15 s).

Mostrar sempre inteiro, com "estimado" no texto, e nunca cor de alarme.

---

## 4. Câmera NoIR e LEDs de 940 nm

### 4.1 Funciona com um canal só?

Sim, com perda de qualidade:
- O pulso em 940 nm é **cerca de 10 vezes mais fraco** que no RGB: "The rPPG signal is IR (blue) is about 10 times
  weaker than in RGB" [fonte: [Nowara et al., SparsePPG, CVPRW 2018](https://openaccess.thecvf.com/content_cvpr_2018_workshops/papers/w27/Nowara_SparsePPG_Towards_Driver_CVPR_2018_paper.pdf),
  Fig. 3]. Motivo: a hemoglobina absorve muito menos no infravermelho e o sensor é menos sensível lá (mesma fonte, §3).
- No laboratório, parado, 30 fps, 640×640, câmera com filtro passa-banda de 940 nm de 10 nm e dois iluminadores
  Bosch [fonte: mesma, §4.1]:

  | | IR (940 nm) RMSE / PTE6 | RGB RMSE / PTE6 |
  |---|---|---|
  | SparsePPG | 13,6 bpm / 79,7% | 9,6 bpm / 88,5% |
  | distancePPG | 14,7 / 77,7% | 9,7 / 88,4% |
  | CHROM | só RGB | 13,6 / 85,9% |

  (PTE6 = % do tempo com erro < 6 bpm.)
- **Com luz variando, o IR ganha**: luzes acendendo e apagando → IR RMSE 2,4 bpm (PTE6 95,1%) contra RGB 26,1 bpm
  (PTE6 0%) [fonte: mesma, Tabela 2]. Exatamente o cenário da estrada à noite (faróis, postes).
- No carro de verdade, os dois problemas foram movimento grande da cabeça (o rastreador de pontos falhou a 20 mph)
  e variação de luz; no IR a variação foi bem menor que no RGB, mas existiu (sol vazando no filtro) [fonte: mesma,
  §4.3].
- Dataset de motoristas (MR-NIRP Car, 940 nm, 30 fps): um método de aprendizado profundo teve MAE 5,1 bpm parado na
  garagem, 8,7 parado dirigindo, 12,0 com movimento na garagem e 14,8 com movimento dirigindo
  [fonte: [arXiv 2411.00919, Tabela II](https://arxiv.org/html/2411.00919v1)]. O artigo da revista com o
  AutoSparsePPG (Nowara et al., IEEE T-ITS 2020, doi 10.1109/TITS.2020.3038317) não abriu aqui (servidor recusou);
  números dele não conferidos.

### 4.2 O que muda no RotaGuard

- **A Camera Module 3 NoIR não tem filtro IR nenhum** ("capture both visible light and infrared light")
  [fonte: [Raspberry Pi, documentação da câmera](https://www.raspberrypi.com/documentation/accessories/camera.html)].
  Os testes de Nowara usaram filtro passa-banda de 10 nm; sem ele, de dia entra luz visível e solar misturada.
  Consequências (**Hipótese**, medir):
  - **noite** (só LED 940 nm): imagem praticamente cinza → modo canal único (média dos 3 canais, que no IR recebem
    quase o mesmo); qualidade esperada pior que a do laboratório da MERL (sem filtro e LEDs mais fracos);
  - **dia** com NoIR: cores "lavadas"/rosadas porque o IR soma em todos os canais. O POS assume a assinatura do
    pulso no RGB visível ([0,33; 0,77; 0,53], Wang 2017 nota 6); com IR somado, essa assinatura muda. Tratar como
    "RGB contaminado": tentar POS e GREEN e deixar o SNR decidir; esperar pior que webcam.
  - Um filtro passa-banda de 940 nm na lente melhoraria muito a robustez à luz (é o que a literatura usou), mas
    mudaria o resto do script (de dia a imagem fica só com o que o LED ilumina). Decisão de hardware para o Matheus.
- **LED com PWM**: driver de LED barato com PWM pode bater com a taxa de quadros e criar oscilação de intensidade
  dentro de 0,7–3,5 Hz. Usar driver de corrente constante. (**Hipótese** sem fonte específica, mas mecanismo de
  aliasing conhecido; medir com a câmera apontada para uma parede.)
- **850 vs 940 nm**: muitos sistemas de motorista usam 940 nm porque a absorção da água no ar cria um "vale" de luz
  solar perto de 940 nm [fonte: Nowara 2018, §3]. Trocar para 850 nm daria pulso mais forte (**Hipótese**), mas o
  brilho vermelho do LED aparece para o motorista e a luz solar atrapalha mais.

### 4.3 Exposição, ganho, balanço de branco e foco

- Exposição/ganho automáticos mudam a intensidade em degraus e o balanço de branco automático muda a cor (que é
  justamente o que o POS e o CHROM medem). **Hipótese** forte: travar ou compensar.
- No picamera2, `set_controls({"AeEnable": False, "ExposureTime": ..., "AnalogueGain": ...})` desliga o automático
  [fonte: [fórum Arducam](https://forum.arducam.com/t/set-exposure-time-and-exposure-compensation-using-picamera2-class/7187);
  em libcamera recente, definir ExposureTime/AnalogueGain coloca o AE em manual, [patch 16511](https://patchwork.libcamera.org/patch/16511/)].
  - Travar a exposição pode prejudicar o resto do script em luz que muda (olhos, celular). Alternativa melhor
    (**Hipótese**): deixar o automático, **ler `ExposureTime`, `AnalogueGain` e `ColourGains` dos metadados por
    quadro** (o `camera.py` já lê `Lux` da mesma forma) e descartar a janela quando eles mudam, ou dividir a média
    da ROI por (exposição × ganho) se a imagem estiver em escala linear.
- Câmera 3 tem foco automático motorizado [fonte: documentação Raspberry Pi]: foco contínuo "respirando" muda
  escala e brilho. Travar o foco (modo manual) depois de focar no rosto (**Hipótese**).
- **Compressão**: "even low-level compression noticeably lowers the BVP SNR" [fonte: McDuff, Blackford & Estepp, IEEE
  FG 2017, [PDF](https://microsoft.com/en-us/research/uploads/prod/2020/11/McDuff_2017_Impact2.pdf)]. Webcam em MJPEG
  perde sinal; o Picamera2 entrega quadro sem compressão (bom). Vídeo gravado em H.264 para o app de teste: pior.

---

## 5. Outras métricas: o que dá e o que não prometer

| Métrica | Viável? | Requisitos | Mostrar na demonstração? |
|---|---|---|---|
| **Pulso médio (bpm)** | Sim, parado e com luz razoável | ≥ 15 fps, janela 10 s, rosto ≥ ~100 px de altura de testa (**Hipótese**) | **Sim**, como "estimado", com estado de qualidade |
| **Tendência do pulso** (subiu/caiu em relação ao início da viagem) | Sim, em médias de minutos | muitas janelas válidas | Sim, como gráfico simples, sem interpretação |
| **Respiração (rpm)** | Parcial | janela 30–60 s, cabeça parada | Só como "experimental" |
| **SDNN** (variabilidade) | Fraco | 60 s parado, 30 fps sem compressão | Não |
| **RMSSD** | Ruim | idem | **Não** |
| **LF/HF, HF** | Não validado em vídeo | ≥ 2–5 min limpos | **Não** |
| **SpO2, pressão, estresse** | Não (precisa de outro hardware/calibração) | — | **Nunca** |

### 5.1 Variabilidade (HRV)

- Com o PURE (30 fps, 640×480, compressão sem perdas, ~1,1 m, referência por oxímetro de dedo), em 56 gravações:
  SDNN de 60 s teve correlação r = 0,841 com a referência; **RMSSD só r = 0,529**; pNN50 r = 0,657; frequência
  não avaliada. Os autores pedem validação com ECG e 5 min [fonte: Finžgar & Podržaj, PeerJ 2020,
  [PMC6953345](https://pmc.ncbi.nlm.nih.gov/articles/PMC6953345)].
- Taxa de amostragem: em PPG simulado, "the minimal sampling frequency of PPG for accurate HRV analysis is higher
  than expected", e a interpolação ajuda [fonte: Béres et al., Measurement Science Review 2019,
  [PDF](https://www.measurement.sk/2019/msr-2019-0030.pdf)]; a 20 Hz os valores absolutos não batem, mas a
  tendência sim (Baek et al. 2017, citado na mesma busca). Com 30 fps o intervalo entre quadros é 33 ms; a
  diferença típica entre batimentos seguidos em repouso é de dezenas de ms. **Hipótese**: interpolação cúbica do
  pico até ~5 ms ajuda, mas o ruído de forma de onda do rPPG domina.
- Conclusão: **no Pi (10–20 fps, IR fraco, movimento) HRV não é viável**. Na webcam, só SDNN de 60 s parado, e só
  como curiosidade de laboratório; não mostrar ao motorista nem à empresa.

### 5.2 Respiração

- Fusão de movimento do rosto + rPPG: MAE 1,33 rpm e 86,53% dentro de ±2 rpm em 22 pessoas, 5–30 rpm, com
  respiração controlada [fonte: [Samsung Research, ICASSP 2024](https://research.samsung.com/research-papers/Multimodal-Breathing-Rate-Estimation-Using-Facial-Motion-and-RPPG-From-RGB-Camera)].
- Pela modulação do vídeo-PPG + movimento da cabeça: erro relativo < 2% entre 0,2 e 0,4 Hz, piorando perto de
  0,1 e 0,5 Hz [fonte: [Universidad de Zaragoza](https://zaguan.unizar.es/record/86511/files/texto_completo.pdf)].
- Para o RotaGuard (**Hipótese**): sinal 1 = movimento vertical lento de pontos estáveis (ponte do nariz 6/168,
  queixo 152), normalizado pela distância entre os olhos; sinal 2 = componente lenta (0,1–0,5 Hz) da intensidade
  da testa e a variação de amplitude do pulso. Welch em 30–60 s, banda 0,1–0,5 Hz (6–30 rpm). No caminhão, a
  vibração e a direção mexem a cabeça nessa mesma faixa: **não prometer**; mostrar só "experimental" no app de teste.

---

## 6. Pulso e sono ao volante: o que se sustenta

- Revisão sistemática (19 estudos, 14 sobre sonolência; todos observacionais, qualidade baixa, amostras de 4 a 10
  pessoas em alguns): alerta → FC maior; sonolência → **HF maior** (parassimpático). LF/HF é **contraditório**
  ("reduced LF/HF" no resumo, mas um estudo achou 3,18 alerta vs 4,33 sonolento). Um estudo achou queda de 28% do
  RMSSD como sinal sensível, o que contraria a ideia geral de "mais HRV com sono". Sensibilidade relatada 47–95%
  [fonte: Burlacu et al., Rev. Cardiovasc. Med. 2021, [IMR Press](https://www.imrpress.com/journal/RCM/22/3/10.31083/j.rcm2203090/htm)].
- Estrada real, 43 motoristas, privação de sono, ECG: classificador por HRV com AUC 0,76; com tempo de direção e
  dia/noite, AUC 0,88 [fonte: Lu et al., IEEE T-ITS 2022, [Chalmers](https://research.chalmers.se/en/publication/527879)].
  Ou seja: o **contexto** (horário, horas ao volante) pesa tanto quanto o coração, e o RotaGuard já tem esse contexto
  (`context.py`).
- Esses estudos usaram **ECG ou sensor de contato**. Nada disso foi validado com rPPG de câmera IR num caminhão.

**Como usar sem diagnosticar** (proposta):
1. Fase 1 (demo): mostrar só o pulso estimado e o estado de qualidade. Não entra no risco.
2. Fase 2 (depois de validar com gravações): registrar a **tendência do pulso em relação ao início da própria
   viagem** (média por minuto, só janelas boas) como métrica privada, igual às do módulo 2 (`MODULE2_METRICS`,
   `PRIVATE_KEYS`). Uma queda lenta e sustentada junto com sinais oculares de sono pode virar **motivo leve**
   ("pulso abaixo do início da viagem junto com sinais de sono"), nunca sozinho, nunca alarme.
3. Ativação atípica: estimulantes, café, estresse, conversa e calor sobem o pulso; o mesmo cuidado do
   `activation.py` vale (desvio da linha de base pessoal, peso baixo, confiança). **Hipótese**; não integrar antes de
   dados.
4. Texto sempre "sinais compatíveis com", "estimado", "não é medição médica".

---

## 7. Bibliotecas: licença e se vale depender

Licenças conferidas na API do GitHub em 19/10/2026:

| Biblioteca | Licença | Pode no produto (RNF-10)? | Observação |
|---|---|---|---|
| pyVHR (phuselab) | **GPL-3.0** | **Não** | [GitHub](https://github.com/phuselab/pyVHR) |
| rPPG-Toolbox (ubicomplab) | **Responsible AI Source Code License** (RAIL), não é OSI | **Não** | §3.2.a proíbe "Surveillance: […] Detect or infer […] health and medical conditions" e exige repassar as restrições a todos os usuários ([LICENSE](https://github.com/ubicomplab/rPPG-Toolbox/blob/main/LICENSE)). Um sistema que a empresa usa para acompanhar o motorista bate de frente. |
| yarppg (SamProell) | MIT | Sim | Não está no PyPI (`pip index versions yarppg` → não encontrado); puxa `hydra-core`, `pandas`, `scipy` ([pyproject](https://github.com/SamProell/yarppg/blob/master/pyproject.toml)). Peso demais para o Pi. |
| remotebiosensing/rppg | Apache-2.0 | Sim | Framework de benchmark (PyTorch); útil para comparar, não para a caixa. |
| vitallens-python | MIT | Sim (só modos locais) | `method="pos"` roda local sem chave; o modo bom manda vídeo para API na nuvem ([README](https://github.com/Rouast-Labs/vitallens-python)). Mandar rosto para fora **contraria o PRD**. |
| NeuroKit2 | MIT | Sim | Útil para HRV/respiração **em ferramentas de análise**, não na caixa. `neurokit2` 0.2.13 no PyPI. |
| HeartPy | MIT (API do GitHub) | Sim | Idem. |
| scipy | BSD-3-Clause | Sim | **1.18.1** é a última estável (`pip index versions scipy`); tem roda `cp314` para Windows (37 MB) e Linux aarch64; exige Python ≥ 3.12. |
| numpy | BSD | já presente | 2.5.4 é a última no PyPI; o `.venv` está com 2.5.3. |

**Recomendação: implementar em numpy puro** dentro de `caixa/vision/cardio.py`:
- POS, CHROM, detrend, FFT, Welch e SNR cabem em ~250 linhas de numpy (protótipo no scratchpad);
- não aumenta o pacote do app de teste nem o Pi;
- código próprio, sem risco de licença; citar os artigos (Wang 2017, de Haan 2013, Tarvainen 2002) no
  `THIRD_PARTY_NOTICES.md` só como referência bibliográfica.
- **scipy só nos testes** (opcional): conferir o filtro e o Welch de numpy contra `scipy.signal` (BSD-3, versão
  1.18.1). Se o Matheus preferir usar scipy no produto, fixar `scipy==1.18.1` e medir o tamanho do PyInstaller.

---

## 8. LGPD

- Pulso é **dado referente à saúde** e, portanto, **dado pessoal sensível** (art. 5º, II). Só pode ser tratado nas
  hipóteses do art. 11: consentimento "de forma específica e destacada, para finalidades específicas" (inciso I), ou
  sem consentimento quando indispensável para uma das alíneas do inciso II (obrigação legal, proteção da vida ou da
  incolumidade física, tutela da saúde por profissional de saúde, entre outras)
  [fonte: [texto do art. 11](https://lgpd-brasil.info/capitulo_02/artigo_11); resumo de
  [lec.com.br](https://lec.com.br/lgpd-e-o-mito-do-consentimento-para-tratamento-dos-dados-de-saude)].
- § 4º do art. 11: veda comunicar ou compartilhar dado de saúde para obter vantagem econômica (com exceções de
  serviços de saúde) [mesma fonte].
- **Empresa e motorista**: o consentimento de empregado tende a ser questionado por desequilíbrio de poder
  (**Hipótese** jurídica; parecer de advogado). A base "proteção da vida ou da incolumidade física" (art. 11, II,
  "e") pode caber para alerta local de segurança, mas não para guardar pulso no relatório da empresa. Decisão de
  advogado, já prevista no PRD (RNF-05, "RIPD e base legal com advogado").
- **ANVISA**: software com finalidade de diagnóstico ou prevenção pode ser dispositivo médico (RDC 657/2022); a
  norma exclui software "para bem-estar" [fonte: [RDC 657/2022 compilada](https://antigo.anvisa.gov.br/documents/10181/5141677/RDC_657_2022_COMP.pdf/d2da154d-bd76-40ba-87ee-3d9baadb5dd3)].
  O enquadramento depende da finalidade declarada: nunca dizer que o RotaGuard "monitora a saúde" ou "detecta
  problema cardíaco".

**Cuidados de produto e texto** (proposta):
1. **Desligado por padrão na caixa** (`--cardio desligado|local`); no app de teste, opção "Estimar pulso pela câmera
   (experimental)".
2. Processamento só local; **não gravar** o pulso em disco no modo padrão; nunca em evento, `live_status` ou registro
   da viagem sem base legal definida (usar `PRIVATE_KEYS`, ou um modo próprio ainda mais restrito).
3. Texto da janela: "Pulso estimado pela câmera: 72 bpm (sinal bom). Não é medição médica." Nunca "frequência
   cardíaca medida", "batimento anormal", "arritmia", "estresse", "saúde".
4. Atualizar `caixa/textos_legais.py` (seção LGPD, item 1, hoje fala só de "medidas do rosto", `textos_legais.py:76-78`)
   para citar o pulso estimado como dado de saúde e dizer que não sai do computador.
5. RIPD (art. 38) da caixa precisa incluir o pulso antes de qualquer piloto.
6. Se um dia o pulso pesar no nível de risco, a pessoa pode pedir revisão de decisão automatizada (art. 20).
   **Hipótese** jurídica; confirmar com advogado.

---

## 9. Arquitetura proposta: `caixa/vision/cardio.py`

### 9.1 Encaixe

```
face.py   FaceMetrics.landmarks = points (478×2, px)      ← campo novo; None no YuNet
engine.py self.cardio = CardioMonitor(...) se modo != "desligado"
          update(): reading = self.cardio.update(frame, metrics, state_extras)   (todo quadro, barato)
          _evaluate(): a cada 1 s → self.cardio.evaluate(t)                      (estimativa)
          DriverState.cardio = CardioReading
driver_monitor.py draw_overlay: 1 linha "Pulso estimado: 72 bpm (sinal bom)" ou o estado
run_monitor.py    --cardio {desligado,local} (padrão: desligado na caixa; app de teste liga pela opção)
camera.py (fase 2) metadados ExposureTime/AnalogueGain/ColourGains por quadro → CardioMonitor
```

### 9.2 Classes

```python
FOREHEAD = (69, 108, 151, 337, 299, 296, 336, 9, 107, 66)
CHEEK_IMG_LEFT = (117, 118, 119, 100, 36, 205, 187, 123)
CHEEK_IMG_RIGHT = (346, 347, 348, 329, 266, 425, 411, 352)

@dataclass
class RoiSample:            # um quadro
    t: float
    means: dict[str, tuple[float, float, float] | None]   # R, G, B por ROI (ou I,I,I no IR)
    pixels: dict[str, int]
    motion: float           # deslocamento médio dos pontos / distância entre olhos
    infrared: bool

class RoiSampler:
    """Suaviza os vértices (EMA), monta máscara por ROI no recorte (cv2.fillPoly + cv2.mean),
    exclui pixels ≥ 250 e ≤ 15, descarta ROI pequena ou bochecha do lado virado (|yaw| alto)."""
    def sample(self, frame_bgr, landmarks, yaw, infrared, t) -> RoiSample: ...

class PulseExtractor:       # funções puras, testáveis
    def pos(rgb, fs) / chrom(rgb, fs) / mono(x) -> np.ndarray

class SpectralEstimator:
    """Reamostra, detrend (matriz Tarvainen pré-calculada por N), passa-faixa por FFT, Welch,
    pico parabólico, checagem de f/2, SNR (U = f0±0,1 Hz e 2f0±0,2 Hz)."""
    def estimate(self, t, signal) -> tuple[bpm, snr_db, spectrum]

class HeartRateTracker:
    """Mediana das últimas 5 estimativas aceitas; salto > 10 bpm só depois de 2 janelas."""

class RespirationEstimator:  # experimental; janela 30–60 s; movimento vertical (6, 168, 152) + base lenta da testa

@dataclass
class CardioReading:
    state: str              # desligado | sem_pontos_do_rosto | aguardando_rosto | medindo | camera_lenta |
                            # movimento | luz_instavel | sinal_fraco | ok
    bpm: int | None         # só preenchido com state == "ok"
    confidence: float       # 0–1 (SNR, concordância entre ROIs, cobertura, fps)
    snr_db: float | None
    rois: tuple[str, ...]   # ROIs usadas
    method: str             # "pos" | "mono_ir"
    fps: float | None
    resp_rpm: float | None  # experimental
    updated_at: float

class CardioMonitor:
    def __init__(self, window_s=10.0, step_s=1.0, fs_rgb=30.0, fs_min=15.0): ...
    def update(self, frame_bgr, metrics) -> CardioReading       # todo quadro: RoiSampler + buffer
    def evaluate(self, t) -> CardioReading                       # 1 vez por segundo
    def window_metrics(self) -> dict                             # para a linha de base, fase 2 (privado)
```

### 9.3 Custo por quadro

Medido nesta máquina (x86, Windows, numpy 2.5.3, OpenCV do `.venv`) [medido]:
- médias de 3 ROIs com máscara poligonal no recorte: **0,08 ms por quadro**;
- POS vetorizado em 10 s a 30 Hz: **1,2 ms** (o laço Python do algoritmo original: 18 ms);
- CHROM: 2,0 ms;
- detrend: 18,8 ms resolvendo o sistema, **0,03 ms** com a matriz pré-calculada;
- estimativa completa a cada 1 s (antes de pré-calcular o detrend): 24 ms.

Pi 4/5: **Hipótese** de 4 a 8 vezes mais lento → ~0,5 ms por quadro + ~10–20 ms por segundo. Desprezível perto do
MediaPipe. O gargalo real é o **fps do loop** (RNF-02 pede ≥ 10 fps no Pi 4; o pulso quer ≥ 15). Fase 2
(**Hipótese**): amostrar as ROIs em todo quadro da câmera (30 fps) com os últimos pontos conhecidos, numa linha
separada, e rodar o MediaPipe a 10–15 fps.

### 9.4 Resultado do protótipo em sinal sintético [medido]

Sintético: pele RGB (180, 130, 100), pulso multiplicativo com a assinatura [0,33; 0,77; 0,53], amplitude 0,3%, ruído
gaussiano por canal, 12 s a 30 fps, 8 sementes por caso; erro = |estimado − verdadeiro| em bpm.

| Caso | POS MAE (máx) | CHROM MAE (máx) | GREEN MAE (máx) |
|---|---|---|---|
| 45–180 bpm, parado, luz estável | 0,4–0,7 (≤ 2,0) | 0,6–0,8 (≤ 1,9) | 0,2–0,5 (≤ 0,8) |
| luz variando 2% | 0,5–0,6 (≤ 1,5) | 0,5–0,7 (≤ 1,4) | 0,1–0,6 (≤ 1,2) |
| tremor de ±30% no intervalo | 0,3–0,9 (≤ 2,1) | 0,4–0,9 (≤ 2,1) | 0,2–0,7 (≤ 1,1) |
| ruído 2× | **6–16 (até 116)** | **6–71 (até 148)** | 0,4–0,6 (≤ 1,2) |
| 10 / 15 / 20 fps (POS, 72 bpm) | 5,4 (36) / 0,7 (1,2) / 0,6 (1,2) | — | — |
| IR mono, amplitude 0,3% | — | — | 1,4–1,9 |
| IR mono, amplitude 0,03% (10× mais fraco) | — | — | **31–85 (falha)** |

Leitura honesta:
- O sintético **não diz qual algoritmo é melhor no mundo real**. Aqui o ruído é independente por canal e o verde tem
  o pulso mais forte, então o GREEN ganha; nos dados reais o ruído vem de movimento e luz (correlacionado entre
  canais), e aí o POS ganha (Tabela I de Wang 2017 e rPPG-Toolbox). O sintético serve para **testar o código**
  (critérios abaixo), não para escolher o método.
- O caso "ruído 2×" e o "IR 10× mais fraco" mostram o comportamento que importa: quando não há sinal, o erro vira
  número aleatório. Por isso a regra do §3.7 (não mostrar) é obrigatória.

### 9.5 Critérios de aceite (rascunho para a spec)

Gerador sintético em `tests/` (numpy, semente fixa), sem vídeo real. Pontos do rosto falsos tirados do modelo
canônico do MediaPipe (Apache-2.0; guardar só os 2D dos índices usados como fixture, com aviso de licença).

| ID | Critério | Como testar |
|---|---|---|
| CAR-01 | Pulso RGB correto | Série RGB sintética, 12 s a 30 fps, 72 bpm, ruído σ = 0,2% e luz variando 2%: erro < 3 bpm em 20 de 20 sementes; repetir para 45, 55, 110, 150 e 180 bpm |
| CAR-02 | Quadros irregulares | Mesma série com tremor de ±30% no intervalo e 5% de quadros perdidos: erro < 3 bpm |
| CAR-03 | Não inventa número | Série só com ruído (amplitude 0): `state != "ok"` e `bpm is None` em ≥ 95% das janelas |
| CAR-04 | IR monocromático | `metrics.infrared = True`, canal único, 72 bpm, amplitude 0,3%: usa `mono_ir` e erro < 3 bpm; com amplitude 10× menor: não mostra número (CAR-03) |
| CAR-05 | Câmera lenta | fps efetivo < 15: `state == "camera_lenta"`, sem número |
| CAR-06 | Rosto perdido | Sem rosto por > 0,5 s: buffer zerado, `state == "aguardando_rosto"` no quadro seguinte; número some em ≤ 1 s |
| CAR-07 | Movimento | Pontos deslocando > limite em > 30% da janela: `state == "movimento"`, sem número |
| CAR-08 | Harmônico | Pulso com 2º harmônico de amplitude 0,8× a fundamental: devolve a fundamental (erro < 3 bpm) |
| CAR-09 | Rastreamento | Uma janela isolada com +40 bpm não muda o valor mostrado em mais de 5 bpm |
| CAR-10 | Detrend | Corte de −3 dB da matriz de Tarvainen com λ escolhido entre 0,25 e 0,45 Hz a 30 Hz; tendência linear forte removida sem deslocar o pico |
| CAR-11 | SNR | Senoide em f0 + ruído branco de SNR conhecido: SNR calculado cresce com o SNR verdadeiro (monotônico) e fica < piso com ruído puro |
| CAR-12 | Quadro inteiro | Quadro sintético 640×480 com as três ROIs (polígonos dos pontos canônicos) pulsando a 72 bpm e fundo com ruído: `CardioMonitor` fim a fim dá erro < 3 bpm |
| CAR-13 | Pixels ruins | ROI com 50% de pixels em 255: esses ficam fora; ROI com < mínimo de pixels úteis é descartada |
| CAR-14 | Cabeça virada | yaw > limite: a bochecha do lado virado sai de `rois` |
| CAR-15 | Combinação | Uma ROI com pulso e duas só com ruído: o resultado segue a ROI boa (erro < 3 bpm) |
| CAR-16 | Privacidade | Com modo "local": nenhuma chave de pulso em `event.details`, `live_status()` nem no registro; teste no estilo dos de `PRIVATE_KEYS` |
| CAR-17 | YuNet | Sem `landmarks`: `state == "sem_pontos_do_rosto"`, nada quebra |
| CAR-18 | Texto | Textos da janela contêm "estimado" e nunca "diagnóstico", "doença", "arritmia", "saúde" |
| CAR-19 | Desempenho | `update` p95 ≤ 1 ms e `evaluate` ≤ 15 ms nesta máquina; no Pi: medir e registrar (não marcar como feito sem a placa) |
| CAR-20 | Respiração (experimental) | Pontos 6/168/152 oscilando a 15 rpm (0,5% da distância entre os olhos) + ruído, 60 s: erro < 2 rpm; com cabeça mexendo a 0,3 Hz forte: estado "movimento" |

Validação em dado real (não automática no CI): rodar UBFC-rPPG e PURE pelo `ferramentas/` e registrar MAE, RMSE,
PTE6 e % de tempo com número mostrado. Meta inicial (**Hipótese**): MAE ≤ 5 bpm no UBFC com POS, perto dos 4,08 do
Toolbox.

---

## 10. Datasets para validar

| Dataset | Conteúdo | Como obter | Licença / termos |
|---|---|---|---|
| **UBFC-rPPG** | Logitech C920, 30 fps, 640×480, RGB 8 bits sem compressão, ~1 m; oxímetro CMS50E; conjunto 1 (8 vídeos) e 2 (42 vídeos, jogo de matemática) | Pasta do Google Drive na [página do dataset](https://sites.google.com/view/ybenezeth/ubfcrppg) | "shared for research purpose"; sem licença formal. Citar Bobbia et al., Pattern Recognition Letters 2017. Confirmar uso por empresa com os autores |
| **PURE** | 10 pessoas, 60 sequências de 1 min, 6 situações (parado, falando, translação lenta e rápida, rotação ~20° e ~35°), 30 Hz, 640×480; oxímetro CMS50E 60 Hz; FC 42–148 bpm | Pedido por e-mail a nikr-datasets-request@tu-ilmenau.de, **só de e-mail institucional acadêmico** ([TU Ilmenau](https://www.tu-ilmenau.de/universitaet/fakultaeten/fakultaet-informatik-und-automatisierung/profil/institute-und-fachgebiete/institut-fuer-technische-informatik-und-ingenieurinformatik/fachgebiet-neuroinformatik-und-kognitive-robotik/data-sets-code/pulse-rate-detection-dataset-pure)) | Empresas não são atendidas "due to licensing restrictions": **RotaGuard não consegue pedir** sem parceria acadêmica |
| **MR-NIRP Indoor** | 8 pessoas, 15 vídeos, RGB + NIR 940 nm, parado e com movimento | Google Drive pela [página da Rice](https://computationalimaging.rice.edu/mr-nirp-dataset/) | Sem licença na página; pede citação (Nowara et al., CVPRW 2018). Ler o README da pasta |
| **MR-NIRP Car** | 19 pessoas, 190 vídeos, dirigindo e parado na garagem, dia/noite, sol/chuva, RGB + NIR 940 e 975 nm, 30 fps, oxímetro | Mesma página | Idem; citar Nowara et al., IEEE T-ITS 2020. **É o mais parecido com o RotaGuard** |
| **MMPD** | Celular, movimento, luzes e tons de pele variados | Pelo rPPG-Toolbox | Não conferido aqui |

- Para validar a câmera real (NoIR + LED 940 nm no Pi), nada substitui **gravação própria** com oxímetro de dedo de
  referência (tipo CMS50E, o mesmo dos datasets). Com motoristas reais, exige consentimento e, se for pesquisa,
  comitê de ética (o `activation.py` já registra essa exigência, linhas 16-17).
- O uso desses datasets para desenvolver produto comercial **não está claro** em nenhum dos quatro: perguntar aos
  autores antes de publicar números.

---

## 11. Arquivos deste trabalho (scratchpad, fora do repositório)

- Protótipo POS/CHROM/GREEN/Welch/SNR/detrend:
  `C:\Users\MATHEU~1\AppData\Local\Temp\claude\c--Users-Matheus-Corte-Downloads-Vigilancia-Motorista-main-Vigilancia-Motorista-main\b92b8a20-6be0-44e6-8616-27345e1b8984\scratchpad\proto_cardio.py`
- Versão corrigida (CHROM com filtro na janela longa, detrend pré-calculado, varredura de λ):
  `C:\Users\MATHEU~1\AppData\Local\Temp\claude\c--Users-Matheus-Corte-Downloads-Vigilancia-Motorista-main-Vigilancia-Motorista-main\b92b8a20-6be0-44e6-8616-27345e1b8984\scratchpad\proto2.py`
- Figura das ROIs no modelo canônico:
  `C:\Users\MATHEU~1\AppData\Local\Temp\claude\c--Users-Matheus-Corte-Downloads-Vigilancia-Motorista-main-Vigilancia-Motorista-main\b92b8a20-6be0-44e6-8616-27345e1b8984\scratchpad\mp\rois_small.png`
- Texto extraído dos artigos POS e SparsePPG:
  `C:\Users\MATHEU~1\AppData\Local\Temp\claude\c--Users-Matheus-Corte-Downloads-Vigilancia-Motorista-main-Vigilancia-Motorista-main\b92b8a20-6be0-44e6-8616-27345e1b8984\scratchpad\papers\`

O que **não** foi verificado: desempenho no Raspberry Pi; qualidade real com a NoIR e LEDs de 940 nm; números do
AutoSparsePPG (servidor recusou); texto oficial do art. 11 no Planalto (conexão recusada; usei espelho);
detalhes exatos de PBV, LGI e OMIT.

---

## 12. Resumo (15 linhas)

1. Dá para estimar o **pulso médio** pela câmera; HRV, LF/HF, SpO2 e "estresse" não devem ser prometidos.
2. Algoritmo padrão: **POS** (Wang 2017): empata com o CHROM no UBFC (MAE 4,08 contra 4,06) e é o melhor sem treino no PURE (3,67) e no MMPD (12,36).
3. Implementar em **numpy puro** em `caixa/vision/cardio.py`; pyVHR é GPL-3.0 e o rPPG-Toolbox tem licença RAIL, que proíbe inferir saúde em vigilância.
4. ROIs: testa `69,108,151,337,299,296,336,9,107,66` e malares `117,118,119,100,36,205,187,123` e `346,347,348,329,266,425,411,352` (conferidas no modelo canônico).
5. Combinar as ROIs por SNR, excluir pixels saturados, tirar a bochecha do lado virado e suavizar os pontos.
6. Processamento: reamostrar pelo carimbo de tempo, detrend de Tarvainen com λ ≈ 300 a 30 Hz (corte 0,34 Hz) e matriz pré-calculada, passa-faixa 0,7–3,5 Hz.
7. Depois: Welch, pico parabólico, checagem de f/2, janela de 10 s com passo de 1 s e mediana das últimas 5.
8. Só mostrar número com SNR acima do piso calibrado, ≥ 15 fps, pouco movimento, ROIs concordando e ~15 s de aquecimento.
9. IR 940 nm: o pulso fica ~10× mais fraco (Nowara 2018), mas resiste melhor à luz variando; a NoIR sem filtro passa-banda tende a ficar pior que isso.
10. Travar ou registrar exposição, ganho, balanço de branco e foco; usar driver de LED de corrente constante.
11. Custo desprezível (0,08 ms por quadro + ~2 ms por segundo no x86); o limite real é o fps do Pi.
12. Fadiga: a literatura aponta pulso menor e HF maior com sono, mas com evidência fraca e só com ECG; usar como tendência pessoal privada, sem pesar no risco até validar.
13. LGPD: é dado de saúde (art. 5º II e art. 11): desligado por padrão, só local, fora de eventos, texto "estimado, não é medição médica", RIPD e advogado.
14. Antes da spec, registrar no PRD a mudança em relação à "pulseira de FC para muito depois" (§5).
15. Validar com UBFC e MR-NIRP Car (o PURE só aceita pedido acadêmico) e com gravação própria + oxímetro; critérios CAR-01 a CAR-20 testáveis com sinal sintético.
