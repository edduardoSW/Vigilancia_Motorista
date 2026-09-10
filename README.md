# DriveSafe AI

Monitoramento de motoristas profissionais para frotas. Cada veículo tem um dispositivo (Raspberry Pi ou qualquer
computador com câmera) que analisa o rosto do motorista e dispara o alarme no veículo. Os eventos vão para um
servidor central, onde o dono da empresa acompanha a frota e exporta os dados.

O dispositivo mede:
- sonolência (fadiga e microssono);
- uso de celular;
- sinais compatíveis com ativação atípica, do tipo causado por estimulantes como o "rebite".

A partir disso, calcula um nível de risco de 0 a 3.

> **Importante:**
> - É um auxílio à segurança. Não substitui descanso, as pausas da Lei 13.103/2015 nem a atenção de quem dirige.
> - **O sistema não faz diagnóstico.** "Sinais compatíveis com ativação atípica" nunca significa "usou droga":
>   estresse, cafeína, pouca luz, conversa e medicamentos causam os mesmos sinais.
> - Os model cards do MediaPipe dizem que os modelos não foram feitos para decisões críticas à vida humana e põem
>   "qualquer forma de vigilância" fora do escopo. Detalhes em [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
> - Os limiares são pontos de partida baseados em estudos e precisam ser validados com vídeos reais da frota.

## Como funciona

```
Veículo 1: câmera → dispositivo (run_monitor.py) ──┐
Veículo 2: câmera → dispositivo                    ├── HTTP + token do dispositivo ──→ Servidor central ──→ Painel web
Veículo N: câmera → dispositivo ───────────────────┘                                  (FastAPI + banco)    e CSV
               └─ fila local (SQLite): sem internet, guarda os eventos e reenvia quando a conexão volta
```

- Cada dispositivo tem o **próprio token**. O servidor guarda só o hash, e um aparelho perdido é bloqueado
  com `manage.py revogar-dispositivo` sem afetar os outros.
- Reenviar o mesmo evento **não duplica** o registro.
- Raspberry Pi sem relógio de bateria pode ligar com a data errada. O dispositivo manda há quantos segundos
  o evento aconteceu (relógio monotônico) e o **servidor corrige o horário**.
- Horários ficam em **UTC** no banco e aparecem no fuso `America/Sao_Paulo`.

Dentro do dispositivo, cada quadro passa por:

```
captura (camera.py) → rosto e olhos (face.py, pupil.py) → olhos visíveis? (visibility.py)
  → módulo 1: sonolência (eyes.py, calibration.py, drowsiness.py)
  → módulo 2: sinais de ativação (activation.py)
  → módulo 3: linha de base e z-scores (baseline.py)
  → celular (phone.py, em thread separada) + contexto da viagem (context.py)
  → módulo 4: fusão, nível de risco e alertas (risk.py) → alarme e fila de eventos
```

O `vision/engine.py` liga tudo. Avaliação fica em `analisar_video.py`, `avaliar_piscadas.py` e `avaliar_dataset.py`.

## Módulo 1: sonolência

| Parte | Como |
|---|---|
| Rosto | MediaPipe Face Landmarker: 478 pontos, rosto virado até ~90° para o lado |
| Olho aberto ou fechado | Três sinais: EAR, pontuação de piscada do MediaPipe e classificador de olho OCEC. Com três sinais vale a maioria; com dois, os dois precisam concordar |
| Calibração individual | Nos primeiros **5 a 10 minutos** de cada viagem aprende o olho aberto e o fechado da pessoa e o padrão de piscadas. Um olho naturalmente pequeno não vira "fechado" |
| Cada piscada | Duração, amplitude, velocidade de fechamento e de abertura, e razão amplitude/velocidade (AVR, Johns et al.) |
| Janela deslizante | Piscadas por minuto, duração mediana, PERCLOS P80 de 60 s e 3 min, fechamentos acima de 500 ms |
| Bocejo | Boca aberta por 2 s ou mais (sinal complementar) |
| Cabeceio | Cabeça cai 15° ou mais em até 1 s, fica baixa de 0,3 a 3 s e volta. Olhar para baixo devagar não conta |

Piscada e fechamento são detectados com máquina de estados e limiar relativo ao olho aberto da própria pessoa,
nunca com limiar fixo. Os índices do olho e da íris foram conferidos no código do MediaPipe 1.0.1.

## Módulo 2: sinais compatíveis com ativação atípica

**O que se sabe:**
- O "rebite" é estimulante: durante o efeito o motorista **não** parece sonolento.
- Quando o efeito passa, vem o rebote: depressão, fadiga e sono (Takitane et al., 2013).

| Sinal | Evidência | Peso |
|---|---|---|
| Pupila maior que o normal da pessoa na mesma faixa de luz | Lisdexanfetamina dilatou a pupila a ~50 e ~500 lux (Kuijpers et al., 2025). É o sinal mais forte | 0,40 (0,25 quando a luz vem da própria imagem) |
| Frequência de piscadas fora do normal | Literatura divergente (aumento, nada ou redução): conta o desvio nos dois sentidos | 0,15 |
| Piscadas mais curtas que o normal | Hipótese coerente com ativação, não validada | 0,15 |
| Mais movimentos rápidos dos olhos (sacadas) | Hipótese; a 30 fps só as sacadas grandes aparecem | 0,15 |
| Olhar mais disperso (entropia de transição) | Álcool reduz (Shiferaw et al., 2019); aumento é associado a interferência, como ansiedade. Hipótese para estimulantes | 0,15 |

- **Saída:** índice de 0 a 1, confiança (baixa, média ou alta) e estado: sem sinais, sinais leves ou sinais
  compatíveis.
- **Regras para "sinais compatíveis":** pelo menos 2 sinais precisam convergir. Sonolência presente anula os sinais
  de ativação. Sem linha de base individual não há índice.
- **A pupila só é medida com câmera infravermelha:**
  - Em câmera RGB comum ela fica marcada como "não confiável" e desligada, sem estimativa.
  - Precisa de íris com 24 px ou mais de diâmetro na imagem (câmera perto ou em 1280×720).
- **Sem luz ambiente informada pela câmera, a confiança cai:**
  - O picamera2 informa a luz ambiente ("Lux").
  - Webcams comuns não informam; nesse caso a faixa de luz vem da própria imagem e o peso da pupila cai.
- **Limite:** não existe base pública de motoristas sob efeito de anfetamina. Este módulo não foi validado com usuários
  reais, e validar exige parceria com universidade e aprovação em comitê de ética (CEP/CONEP).

## Módulo 3: linha de base individual

- **Da viagem:** no fim da calibração, os quadros calibrados são reprocessados com o perfil final em janelas a cada
  30 s. Vira a média e a variação de cada métrica da pessoa naquele dia.
  - Precisa de ~2 min ou mais de calibração.
  - Roda numa thread para não travar a câmera.
- **Acumulada entre viagens:** só com **consentimento** (`--consentimento-perfil`).
  - A partir de 3 viagens, passa a ser a referência.
  - Calibração com sinais fora do habitual não entra na soma.
- **Z-scores:** todas as métricas dos módulos 1 e 2 são expressas também como desvio da linha de base.
  - Desvio-padrão com piso por métrica, porque poucas janelas dariam z enormes.
  - A pupila só é comparada na mesma faixa de luz.

## Módulo 4: fusão e alertas

| Nível | Quando | O que acontece |
|---|---|---|
| **3 Crítico** | Olhos fechados por 1 s (microssono), 3 s (sono) ou 6 s (sem resposta), com base no Euro NCAP 2026 | Sirene; evento de risco 3, 4 ou 5 |
| **2 Alto** | Piscadas 25% mais longas que o normal (Ingre et al., 2006), PERCLOS de 12% em 3 min (Owens et al., 2018), 3 fechamentos de 500 ms em 5 min, 3 cabeceios em 10 min, atenção persistente por 10 min, **rebote** ou celular no ouvido/olhando o celular | Sirene |
| **1 Atenção** | Piscadas 15% mais longas, pálpebra 30% mais lenta (AVR), PERCLOS acima do normal, 2 bocejos ou 2 cabeceios em 10 min, 1 fechamento longo, ativação atípica sustentada, celular na mão ou mais de 5 h 30 min ao volante | Evento, sem sirene |

- **Histerese:** o risco sobe na hora e desce um nível por vez. Só desce depois de o motivo sumir por 10 s (crítico)
  ou 60 s (alto e atenção).
- **Rebote:**
  - Gatilho: ativação atípica sustentada por 10 min e depois qualquer sinal de sonolência dentro de 1 h.
  - Sinais de sonolência que contam: nível de atenção, piscadas mais longas que o normal ou um fechamento longo.
  - Resultado: risco alto na hora, com evento `sonolencia_abrupta` e sirene.
- **Contexto:** de madrugada (00:00 a 06:59, picos de acidente por sono segundo Horne & Reyner, 1995) ou com mais de
  5 h 30 min ao volante (CTB art. 67-C), sinais leves por 5 min já viram risco alto.
  - Sem telemetria, "ao volante" é o tempo com rosto na câmera.
  - Pausa de 30 min zera a contagem.
- **Telemetria (opcional):** outro programa (GPS, OBD-II) escreve `{"velocidade_kmh": 72.5, "atualizado_em": 1757520000}` num
  arquivo. Com o veículo parado, uso de celular não gera alerta.
- O Crítico já funciona durante a calibração. Os outros níveis de sonolência dependem do perfil individual.
- Abaixo de ~25 fps a duração da piscada não é usada como gatilho; velocidade da pálpebra precisa de ~28 fps.

## Uso de celular

Modelos Apache 2.0 do MediaPipe: EfficientDet-Lite0 (classe "cell phone" do COCO) num recorte ao redor do motorista e
Hand Landmarker (21 pontos por mão). Rodam numa thread separada, ~4 vezes por segundo.

| Estado | Como é reconhecido | Alerta |
|---|---|---|
| Olhando o celular | Celular confirmado e cabeça ou olhos baixos | Depois de 2 s (limite de olhada da NHTSA): risco alto, sirene, evento `olhando_celular` |
| Celular no ouvido | Aparelho perto da orelha, ou mão na orelha com celular visto há pouco ou boca mexendo | Depois de 3 s: risco alto, sirene, evento `celular_no_ouvido` |
| Celular na mão | Celular confirmado com a mão nele ou se mexendo | Depois de 3 s: atenção, evento `celular_na_mao` (CTB art. 252, parágrafo único) |

- **Contexto:** no estudo naturalístico SHRP 2, discar, digitar e navegar com o celular na mão multiplicaram o risco
  de colisão de 2,7 a 12,2 vezes (Dingus et al., 2016).
- **Confirmação:** o celular só conta com pelo menos 2 detecções em 2 s.
- **Suporte:** celular parado sem mão (num suporte) não conta como "na mão".
- **Mão segurando objeto:** o model card do Hand Landmarker põe esse caso fora do escopo. Por isso o movimento do
  aparelho também vale como evidência.
- **Onde a câmera não vê:** celular no colo abaixo do campo da câmera só é percebido pela cabeça baixa.

## Robustez

| Situação | O que o sistema faz |
|---|---|
| Óculos de grau | Mede normalmente; reflexo forte marca a pupila como não confiável |
| Óculos escuros | Região do olho escura e lisa em relação à bochecha: desliga as medidas do olho na hora (sem microssono falso) e avisa com `olhos_nao_visiveis` após 10 s. Numa foto de teste: razão olho/bochecha 0,60 sem óculos e 0,20 com óculos pintados |
| Rosto parcialmente fora da imagem | Olho com algum ponto fora da imagem não é medido; vale o outro |
| Rosto virado ou cabeça muito inclinada | Quadros sem medida confiável não contam como olho fechado |
| Perda do rosto | Evento `rosto_nao_detectado` após 10 s |
| Iluminação variável | Pupila comparada só na mesma faixa de luz; câmera IR recomendada |

## Privacidade (LGPD)

- Processamento **local**. O dispositivo guarda e envia **só métricas e eventos**, nunca imagens.
- **Perfil e linha de base entre viagens:** só com `--consentimento-perfil`. Sem consentimento, a calibração vale
  apenas para a viagem.
- **Sinais de ativação (`--sinais-ativacao`):**
  - `local` (padrão): calculados no dispositivo e usados só no nível de risco. Nenhum evento leva essas métricas; o
    servidor recebe, por exemplo, `sonolencia_abrupta` sem dizer que houve ativação antes.
  - `enviar`: manda também o evento `ativacao_atipica` e as métricas. É **dado pessoal sensível** (LGPD, art. 5º, II
    e art. 11): exige base legal, consentimento e um Relatório de Impacto (RIPD).
  - `desligado`: não calcula.
- Vale passar pelo jurídico antes de colocar em produção (LGPD, CLT e as orientações dos model cards).

## Onde os dados ficam

| Onde | O quê |
|---|---|
| Dispositivo, pasta `~/.drivesafe` (ou `DRIVESAFE_DATA_DIR`) | `eventos.db` (fila local) e `sirene.wav`; com consentimento, também `perfis/<motorista>.json` e `linhas_de_base/<motorista>.json` |
| Servidor, `data/drivesafe.db` | Motoristas, veículos, dispositivos e alertas (SQLite em modo WAL). Para Postgres use `DATABASE_URL` |

---

## 1. Servidor central

### Com Python (3.10 ou mais novo)

```bash
python -m venv .venv
# Windows: .\.venv\Scripts\python.exe   |   macOS e Linux: .venv/bin/python
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python start_system.py --host 0.0.0.0
```

- O painel abre em `http://localhost:8000`.
- `--host 0.0.0.0` deixa os dispositivos da rede enviarem dados. O terminal mostra o IP que eles devem usar.
- Sem essa opção, o servidor só aceita conexões da própria máquina.
- Bancos da versão anterior são atualizados sozinhos na primeira execução, com os horários convertidos para UTC. Faça backup antes.

### Com Docker

```bash
docker compose up -d --build
docker compose exec servidor python manage.py criar-dispositivo --nome "Caminhão ABC-1234" --veiculo 1
```

Para usar Postgres:
1. Crie um arquivo `.env` com `POSTGRES_PASSWORD=...`.
2. Descomente `DATABASE_URL` no `docker-compose.yml`.
3. Suba com `docker compose --profile postgres up -d --build`.

### Cadastros pela linha de comando

| Comando | Para quê |
|---|---|
| `python manage.py criar-veiculo --placa ABC-1234 --modelo "Volvo FH" --tipo Caminhão` | Cadastra veículo |
| `python manage.py criar-motorista --nome "Ana Lima" --cnh SP123456 --telefone 11999990000` | Cadastra motorista |
| `python manage.py criar-dispositivo --nome "Caminhão ABC-1234" --veiculo 1 --motorista 1` | Cadastra dispositivo e **mostra o token uma única vez** |
| `python manage.py vincular-dispositivo 1 --veiculo 2 --motorista 0` | Troca o veículo ou motorista do dispositivo (0 desliga) |
| `python manage.py novo-token 1` | Gera token novo e invalida o anterior |
| `python manage.py revogar-dispositivo 1` | Bloqueia o dispositivo; os alertas antigos ficam |
| `python manage.py dispositivos` / `veiculos` / `motoristas` | Lista |

### Variáveis do servidor

| Variável | Padrão | Uso |
|---|---|---|
| `DATABASE_URL` | SQLite em `data/drivesafe.db` | Ex.: `postgresql+psycopg://usuario:senha@host:5432/drivesafe` |
| `DRIVESAFE_TIMEZONE` | `America/Sao_Paulo` | Fuso para exibir datas e calcular "hoje" |
| `DRIVESAFE_DEVICE_ONLINE_SECONDS` | `180` | Tempo sem contato até o dispositivo aparecer como offline |

---

## 2. Dispositivo de monitoramento

### Windows, macOS e Linux

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements-device.txt
export DRIVESAFE_DEVICE_TOKEN=dsk_...        # PowerShell: $env:DRIVESAFE_DEVICE_TOKEN="dsk_..."
.venv/bin/python run_monitor.py --server-url http://192.168.0.10:8000
```

- Para rodar servidor e dispositivo no mesmo computador, instale os dois arquivos de requisitos no mesmo `.venv`.
- **macOS Intel:** o MediaPipe não tem pacote para ele.
  - O agente entra no modo alternativo: YuNet mais classificador de olho.
  - Nesse modo ele detecta olho fechado e microssono, mas sem calibração, pose da cabeça, bocejo, sinais de
    ativação nem celular.
  - Esse modo ainda não foi validado com olho fechado real.
- **macOS:** na primeira execução, autorize o acesso à câmera para o Terminal.

Janela da câmera: `q` sai e `c` recalibra (por exemplo, na troca de motorista).

### Raspberry Pi

Requisitos:
- Raspberry Pi OS **64 bits**, Bookworm (Python 3.11) ou Trixie (Python 3.13). O MediaPipe só tem pacote para aarch64.
- Raspberry Pi OS exige ambiente virtual para instalar pacotes:

```bash
sudo apt install python3-venv alsa-utils
git clone <repositório> /opt/drivesafe && cd /opt/drivesafe
python3 -m venv .venv
.venv/bin/pip install -r requirements-device.txt
.venv/bin/python run_monitor.py --no-window --server-url http://IP-DO-SERVIDOR:8000
```

- **Câmera USB:** `--camera 0`.
- **Pi Camera Module:**
  1. `sudo apt install python3-picamera2`
  2. Crie o ambiente com `python3 -m venv --system-site-packages .venv`
  3. Use `--camera picamera2`
- **Câmera infravermelha (recomendada):**
  - 850 ou 940 nm, com iluminador; use `--camera-ir sim`.
  - Funciona de noite, atravessa muitos óculos escuros e é a única que permite medir a pupila.
  - O modo `auto` liga o infravermelho quando a imagem fica sem cor. Um vídeo feito de foto em tons de cinza também
    cai nisso, então fixe `sim` ou `nao` quando souber a câmera.
- **Desempenho:** a detecção de celular é a parte mais pesada. Se o fps cair demais no Pi, use `--sem-celular`.
- **Som:** o Raspberry Pi 5 não tem saída de áudio P2. Use:
  - um buzzer num pino GPIO (`--buzzer-pin 17`, pelo gpiozero do sistema);
  - uma caixa de som USB;
  - ou HDMI.
- **Iniciar sozinho ao ligar:** siga as instruções em [`deploy/raspberry-pi/drivesafe-monitor.service`](deploy/raspberry-pi/drivesafe-monitor.service) e copie [`device.env.example`](deploy/raspberry-pi/device.env.example) para `/etc/drivesafe/device.env`.
- **Com Docker, em Linux com webcam em `/dev/video0`:** `DRIVESAFE_DEVICE_TOKEN=dsk_... docker compose --profile dispositivo up -d --build`.
- **Posição da câmera:** de frente para o motorista, com o rosto ocupando boa parte da imagem. Com menos de ~30 px
  entre os olhos, a medida perde precisão.

### Opções do `run_monitor.py`

| Opção | Variável | Padrão |
|---|---|---|
| `--server-url` (ou `--api-url`) | `DRIVESAFE_SERVER_URL` | `http://localhost:8000` |
| `--token` | `DRIVESAFE_DEVICE_TOKEN` | vazio (eventos ficam na fila local) |
| `--camera` | `DRIVESAFE_CAMERA` | `0`; aceita `/dev/video0`, arquivo de vídeo, URL ou `picamera2` |
| `--width`, `--height` | `DRIVESAFE_WIDTH`, `DRIVESAFE_HEIGHT` | 640 × 480 |
| `--camera-ir` | `DRIVESAFE_CAMERA_IR` | `auto` (`sim` ou `nao`) |
| `--data-dir` | `DRIVESAFE_DATA_DIR` | `~/.drivesafe` |
| `--driver-key` | `DRIVESAFE_DRIVER_KEY` | `padrao` (um perfil por motorista) |
| `--consentimento-perfil` | `DRIVESAFE_CONSENTIMENTO_PERFIL` | desligado: nada é guardado entre viagens |
| `--calibration-min`, `--calibration-max` | `DRIVESAFE_CALIBRATION_MIN_S`, `..._MAX_S` | 300 e 600 s |
| `--no-calibration` | `DRIVESAFE_NO_CALIBRATION` | recalibra a cada início (pular exige perfil salvo com consentimento) |
| `--sinais-ativacao` | `DRIVESAFE_SINAIS_ATIVACAO` | `local` (`desligado` ou `enviar`) |
| `--celular` / `--sem-celular` | `DRIVESAFE_CELULAR` | ligado |
| `--telemetria` | `DRIVESAFE_TELEMETRIA_ARQUIVO` | sem telemetria |
| `--window` / `--no-window` | `DRIVESAFE_WINDOW` | automático (sem tela no Linux, sem janela) |
| `--buzzer-pin` | `DRIVESAFE_BUZZER_PIN` | alto-falante |
| `--mute` | `DRIVESAFE_MUTE` | som ligado |
| — | `DRIVESAFE_FACE_BACKEND` | `auto` (MediaPipe; se faltar, YuNet), `mediapipe` ou `yunet` |
| — | `DRIVESAFE_NO_EYE_CLASSIFIER` | classificador de olho ligado |
| — | `DRIVESAFE_DETECTAR_OCULOS_ESCUROS` | ligado |
| — | `DRIVESAFE_HEARTBEAT_S` | 60 s entre sinais de "estou vivo" |

A cada minuto o log mostra o desempenho: fps e tempo por quadro (média, p95 e máximo). A janela também mostra.

---

## 3. Analisar vídeos gravados

```bash
.venv/bin/python analisar_video.py video.mp4 --saida resultados/
.venv/bin/python analisar_video.py video.mp4 --saida resultados/ --celular --camera-ir nao
```

- Calibra com o começo do vídeo: 5 min, ou um terço dele se for curto. Com `--perfil`, usa um perfil salvo no lugar.
- Gera, em CSV com vírgula e ponto decimal:
  - `_quadros.csv`: medidas de cada quadro, inclusive íris, pupila, olhar, nível de risco e latência;
  - `_piscadas.csv`: início, fim, duração, amplitude, velocidades da pálpebra e AVR de cada piscada;
  - `_janelas.csv`: uma linha por segundo com métricas de janela, z-scores, sinais de ativação e nível de risco;
  - `_eventos.csv`: alertas que teriam disparado;
  - `_grafico.png`: EAR, abertura do olho e nível de risco ao longo do tempo;
  - `_resumo.json`: perfil, estatísticas gerais e por trecho, desempenho.
- Precisa do MediaPipe.

## 4. Avaliar o detector

### Piscadas contra anotação manual

```bash
.venv/bin/python avaliar_piscadas.py resultados/video_piscadas.csv anotacao.csv --tolerancia 0.25
```

- A anotação é um CSV com `inicio_s` (e `fim_s`) por piscada, ou `tempo_s`, ou quadros com `--fps`.
- **Saída:** precisão, recall, F1, erro de contagem e desvio de tempo, com a lista de pares, sobras e perdas.

### Dataset rotulado, com validação por sujeito

```bash
.venv/bin/python avaliar_dataset.py extrair lista.csv --saida avaliacao/ --calibracao 300
.venv/bin/python avaliar_dataset.py avaliar avaliacao/
.venv/bin/python -m pip install -r requirements-eval.txt     # só para a opção abaixo
.venv/bin/python avaliar_dataset.py avaliar avaliacao/ --classificador
```

- **`lista.csv`:** colunas `video;sujeito;rotulo;calibracao`.
  - Rótulo `alerta` ou `sonolento`; aceita `0`, `5` e `10`, como no UTA-RLDD.
  - `calibracao=sim` no vídeo alerta que dá a linha de base do sujeito. O começo desse vídeo fica fora da avaliação.
- **Métricas:**
  - precisão, recall e F1 por classe (prioridade: recall de "sonolento") e matriz de confusão;
  - falsos alarmes por hora nos vídeos alerta e latência até o primeiro alarme.
- **`--classificador`:** regressão logística deixando um sujeito de fora por vez. O mesmo motorista nunca fica no
  treino e no teste.
- **Janelas sobrepostas:** 60 s a cada 10 s não são independentes, então os números por janela são otimistas.
- **Licença:** UTA-RLDD, NTHU-DDD, DMD e outros costumam ser só para pesquisa. Confira antes de usar em produto.

## Painel e exportação

- **Painel:**
  - Cards com alertas do dia, críticos, dispositivos online e última ocorrência.
  - Lista de dispositivos com online/offline, fila local e câmera.
  - Lista de alertas com filtro por data, veículo e dispositivo.
- **Exportar CSV:** baixa os alertas filtrados no formato do Excel em português (`;`, vírgula decimal, acentos corretos).
- **Principais rotas da API:**

| Rota | Uso |
|---|---|
| `GET /api/devices` | Lista os dispositivos |
| `POST /api/devices/heartbeat` | Sinal de "estou vivo" do dispositivo (token) |
| `POST /api/events` | Recebe eventos em lote (token) |
| `GET /api/alerts` | Lista os alertas |
| `GET /api/alerts/export.csv` | Exporta os alertas em CSV |
| `GET /api/dashboard/stats` | Números do painel |
| `/ws` | Avisos em tempo real para o painel |

A documentação interativa fica em `/docs`.

## Tipos de evento

Todos levam em `details` o nível de risco na hora (`nivel_risco` de 0 a 3) e, havendo linha de base, os z-scores do módulo 1.

| Tipo | Risco | Significado |
|---|---|---|
| `nao_responsivo` | 5 | Olhos fechados por 6 s |
| `sono` | 4 | Olhos fechados por 3 s |
| `sonolencia_abrupta` | 4 | Sinais de sonolência logo depois de um período de ativação atípica (rebote) |
| `olhando_celular` | 4 | Olhando o celular por mais de 2 s |
| `microssono` | 3 | Olhos fechados por 1 s |
| `sonolencia` | 3 | Tendência de sonolência (piscadas longas, PERCLOS alto, fechamentos longos, cabeceios) |
| `celular_no_ouvido` | 3 | Celular no ouvido por mais de 3 s |
| `celular_na_mao` | 3 | Celular na mão por mais de 3 s |
| `atencao` | 2 | Primeiros sinais de sonolência |
| `direcao_continua` | 2 | Mais de 5 h 30 min ao volante sem pausa de 30 min |
| `ativacao_atipica` | 2 | Sinais compatíveis com ativação atípica sustentados (só no modo `enviar`) |
| `calibracao_suspeita` | 2 | Calibração com o motorista possivelmente já cansado |
| `rosto_nao_detectado` | 1 | Câmera sem ver o rosto por mais de 10 s |
| `olhos_nao_visiveis` | 1 | Óculos escuros ou olhos fora da imagem por mais de 10 s |
| `calibracao_concluida` | 1 | Perfil individual aprendido (métricas em `details`) |

## Desempenho medido

Neste computador (Windows 11, CPU de 12 threads, Python 3.14):

| Cenário | Resultado |
|---|---|
| Dispositivo lendo vídeo, com celular em thread separada | 26 fps, 11 ms por quadro em média (p95 14 ms) |
| `analisar_video.py --celular` (celular no mesmo quadro, a cada 0,25 s) | 22,8 ms por quadro em média, p95 87 ms |
| EfficientDet-Lite0 numa imagem de 640 px | float16 ~73 ms, int8 ~106 ms (int8 costuma ser mais rápido em ARM) |
| Hand Landmarker numa imagem de 640 px | ~66 ms |

No Raspberry Pi ainda não foi medido.

## O que foi testado e o que falta

**Testado:**
- **Ambiente:** Windows 11 com Python 3.14.5. Detector, módulos e avaliação também no Python 3.11.15, o mesmo do
  Raspberry Pi OS Bookworm.
- **Testes automáticos:**
  - `test_detector.py`: 11 testes;
  - `test_modulos.py`: 13 testes (AVR, cabeceio, óculos escuros, linha de base, ativação, histerese, rebote,
    contexto, privacidade);
  - `test_celular.py`: 10 testes, inclusive os modelos reais;
  - `test_avaliacao.py`: 7 testes;
  - `test_server_sync.py`: 15 testes.
- **Pupila:** em imagens sintéticas de olho infravermelho, erro de +0,01 a +0,03 na razão pupila/íris; recusa sem
  contraste.
- **Pose:** sinal de pitch e yaw conferido girando uma foto em 3D.
- **Óculos escuros:** conferido em duas fotos, com óculos pintados.
- **Celular:** numa foto real de motorista ao telefone, detectou o aparelho (0,71), as duas mãos e o estado
  "celular no ouvido", com alarme aos 3 s.
- **Ponta a ponta:** `run_monitor.py` lendo vídeo por 70 s com todos os módulos, calibração, perfil salvo com
  consentimento e reabertura da câmera; `analisar_video.py` com todos os arquivos de saída.

**Não testado ainda:**
- **Hardware e sistemas:** Raspberry Pi real, macOS e Linux.
- **Câmeras e acessórios:** câmera infravermelha e medida real da pupila, Pi Camera Module e a luz ("Lux") do
  picamera2, buzzer e som por `aplay` ou `afplay`.
- **Docker:** build (só a sintaxe do compose foi validada).
- **Classificador de olho com olho fechado real.**
- **Limiares com motoristas reais:** sonolência, cabeceio, óculos escuros, sacadas, entropia do olhar e celular
  (inclusive celular no colo e em suporte).
- **Módulo 2 com usuários reais de estimulantes:** exige comitê de ética.
- **Avaliação em dataset real:** o `avaliar_dataset.py` foi testado com dados sintéticos; o classificador
  (scikit-learn) não foi rodado aqui.

**Antes de colocar em produção:**
- Login no painel e HTTPS: hoje o painel e as rotas de leitura ficam abertos para quem acessa a rede.
- Limite de requisições por dispositivo.
- Validar os limiares com vídeos reais da frota e montar um conjunto próprio de vídeos com consentimento dos
  motoristas (LGPD).
- Revisão jurídica: LGPD (dado sensível e RIPD), CLT e as orientações de uso dos model cards.
- `yolov8n.pt` é AGPL-3.0: não usar em produto fechado sem licença da Ultralytics (o código não usa).

## Estrutura

```
backend/            API FastAPI, banco (SQLAlchemy), tokens, configuração
dashboard/          painel web (HTML, CSS, JS)
vision/             agente do dispositivo
  camera.py         captura: webcam, arquivo, URL ou Pi Camera (com a luz informada pelo picamera2)
  face.py           MediaPipe / YuNet: pontos do rosto, íris, olhar, luminância e medidas por quadro
  eye_state.py      classificador de olho OCEC (OpenCV DNN)
  pupil.py          razão pupila/íris em câmera infravermelha
  visibility.py     óculos escuros e olhos fora da imagem
  eyes.py           abertura relativa, perfil individual, piscadas, velocidade da pálpebra e AVR
  calibration.py    calibração de 5 a 10 min
  drowsiness.py     módulo 1: janelas, cabeceio, níveis de sonolência e eventos
  activation.py     módulo 2: sinais compatíveis com ativação atípica
  baseline.py       módulo 3: linha de base da viagem e acumulada, z-scores
  context.py        tempo ao volante, madrugada e telemetria
  phone.py          uso de celular
  risk.py           módulo 4: fusão, histerese, rebote e eventos de risco
  engine.py         liga os módulos a cada quadro
  driver_monitor.py loop da câmera, desempenho e janela
  evaluation.py     métricas de avaliação sem dependências
  alarm.py          sirene (Windows, macOS, Linux, buzzer GPIO)
  event_queue.py    fila local SQLite
  sync.py           envio ao servidor com reenvio
  models/           modelos (ver THIRD_PARTY_NOTICES.md)
deploy/raspberry-pi serviço systemd e exemplo de configuração
tests/              testes automáticos
run_monitor.py      inicia o dispositivo
analisar_video.py   analisa vídeos gravados
avaliar_piscadas.py compara piscadas detectadas com anotação manual
avaliar_dataset.py  avaliação em dataset rotulado, por sujeito
manage.py           cadastros do servidor
start_system.py     inicia o servidor
```

## Licenças e créditos

Modelos, bibliotecas, dados, estudos e leis usados estão em [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
