# Spec 002 · Trechos curtos por recorrência

| Campo | Valor |
|---|---|
| Status | **rascunho**, aprovada em 11/09/2026 com ajustes (modo `registro` dos sinais de ativação; `cryptography` instalado) |
| Cobre | RF-07; RF-05 (gatilho por sinais de ativação, sempre "não é diagnóstico"); RNF-05 na parte da caixa (AES-GCM, chave por caixa); RNF-07; objetivo O5; perguntas Q1 e Q2 do PRD |
| Depende de | spec 001 (registro), spec 003 (chave da caixa), spec 005 (medir no Pi 4; codificador H.264 do chip, se valer), spec 006 (consentimento) |
| Usada por | spec 003 (coleta dos arquivos), spec 004 (importador usa `decifrar_trecho` e `ler_quadros_avi`) |
| Código previsto | `caixa/vision/trechos.py` (buffer, detector, gravador, AVI), `caixa/vision/cifra_trechos.py` (formato cifrado; só `cryptography`), `caixa/run_monitor.py` |
| Testes previstos | `tests/test_trechos.py` |

## 1. Contexto e vínculo com o PRD

- Palavras do Matheus (PRD §11): "nem toda hora deve ser gravada, apenas as partes que o sensor detecta algo muito
  recorrente, tipo sonolência frequente durante muito tempo e algum tipo de uso de anfetamina […] As gravações devem
  ser curtas."
- PRD §1: as videotelemetrias gravam a viagem inteira e isso gera atrito com motoristas e sindicato. O5: nenhum vídeo
  fora dos gatilhos, no máximo 20 s por trecho, trechos criptografados na caixa.
- Q1 (o que é "muito recorrente") e Q2 (duração e limites) ainda são perguntas abertas. Esta spec usa os padrões do
  PRD em constantes que mudam num lugar só (§4).
- **Hoje a caixa nunca guarda imagem** (README, "Privacidade": "O dispositivo guarda e envia só métricas e eventos,
  nunca imagens"). Esta spec abre uma exceção, só por gatilho, e o README precisa mudar junto na implementação.

## 2. Visão geral

```
quadro da câmera ──(no máximo 10 por s)──> thread JPEG: reduz para 640 px e comprime
                                              └──> buffer circular em memória (últimos 10 s, com teto de bytes)

estado do motor (eventos, nível de sonolência, ativação) ──> detector de recorrência ──> gatilho
gatilho ──> linha `recorrencia` no registro ──> confere limites ─┬─> aceito: 10 s antes + 10 s depois
                                                                 │     └──> thread de gravação: AVI MJPEG → AES-256-GCM
                                                                 │           → arquivo → linha `trecho_gravado`
                                                                 └─> recusado: linha `trecho_descartado` com o motivo
```

- Fora de um gatilho, os quadros só passam pela memória e são descartados.
- A detecção nunca espera a compressão nem a gravação.

## 3. Comportamento (Dado / Quando / Então)

| # | Dado | Quando | Então |
|---|---|---|---|
| T1 | Viagem com sinais abaixo dos critérios | Passam horas | Nenhum arquivo, nenhuma pasta `trechos/`, nenhuma linha de recorrência ou trecho |
| T2 | 2 microssonos nos últimos 30 min | Acontece o 3º microssono | Linha `recorrencia` (`microssonos_30min`); trecho de 10 s antes a 10 s depois do 3º; `trecho_gravado` |
| T3 | Nível de sonolência ≥ 2 há 14 min 59 s (interrupções menores que 60 s) | Completa 15 min | Gatilho `sonolencia_15min` e trecho |
| T4 | Modo `registro` ou `enviar` (com consentimento) e sinais compatíveis com ativação atípica há 10 min | Completa 10 min | Gatilho com o motivo "sinais compatíveis com ativação atípica (não é diagnóstico)" e trecho |
| T5 | Modo `local` ou `desligado`, ou `registro` pedido sem consentimento | O mesmo de T4 | Nada: nem gatilho, nem trecho, nem menção a ativação no registro (D1) |
| T6 | 12 trechos já aceitos na viagem | Novo gatilho | `recorrencia` + `trecho_descartado` `limite_por_viagem` |
| T7 | Trecho de sonolência aceito há 6 min | Novo gatilho de sonolência | `trecho_descartado` `intervalo_minimo`; um gatilho de ativação no mesmo período grava normalmente |
| T8 | Trechos no disco somando o teto (2 GiB) | Novo gatilho | `trecho_descartado` `teto_de_disco`; nenhum trecho existente é apagado |
| T9 | Trecho em captura (dentro dos 10 s depois) | Chega outro gatilho | Entra na lista `gatilhos` do mesmo trecho; um arquivo só |
| T10 | Trecho em captura | A viagem termina | O trecho é gravado com o que tem (`cortado: fim_da_viagem`) antes do `fim_viagem`; buffer zerado |
| T11 | Trecho em captura | A câmera para | Depois de 12 s sem quadro a captura fecha (`cortado: camera_sem_imagem`) e grava |
| T12 | `cryptography` não instalado | A viagem começa | `estado_aparelho` `trechos_indisponiveis`; nenhum quadro guardado; cada gatilho vira `trecho_descartado` `cifra_indisponivel`. Nunca grava sem cifra |
| T13 | Energia cortada entre o gatilho e o fim da gravação | A caixa liga de novo | A linha `recorrencia` já está no registro; a verificação conta `recorrencias_sem_trecho` |

## 4. Padrões (constantes em `caixa/vision/trechos.py`, reunidas em `ConfigTrechos`)

| Constante | Padrão | Origem |
|---|---|---|
| `SEGUNDOS_ANTES` / `SEGUNDOS_DEPOIS` | 10 / 10 | Q2 |
| `FPS_TRECHO` | 10 | Direção técnica; basta para ver o rosto e o gesto |
| `LARGURA_TRECHO_PX` | 640 (mantém a proporção; imagem menor não é ampliada) | Direção técnica |
| `QUALIDADE_JPEG` | 70 | Hipótese |
| `TETO_MEMORIA_BYTES` | 64 MiB (buffer + capturas + fila de gravação) | Hipótese: ~5 MB de buffer, ~9 MB por captura |
| `MICROSSONOS_GATILHO` / `JANELA_MICROSSONOS_S` | 3 / 1.800 | Q1 |
| `NIVEL_SONOLENCIA_GATILHO` | 2 (`drowsiness.py:88`: 2 = sonolência, 3 = perigo) | Q1 |
| `SONOLENCIA_CONTINUA_S` / `SONOLENCIA_TOLERANCIA_S` | 900 / 60 | Q1 / hipótese: o nível é reavaliado a cada 1 s (`drowsiness.py:306-308`) e pode oscilar |
| `ATIVACAO_CONTINUA_S` / `ATIVACAO_TOLERANCIA_S` | 600 / 120 | Q1; os mesmos 10 min e 2 min da regra de rebote (`risk.py:27-28`), em constantes próprias porque Q1 pode mudar sem mexer no rebote |
| `MAX_TRECHOS_POR_VIAGEM` | 12 | Q2 |
| `INTERVALO_MIN_MESMO_TIPO_S` | 600 | Q2 |
| `TETO_DISCO_BYTES` | 2 GiB (`--trechos-teto-disco-gb`) | RNF-07 |
| `RESERVA_LIVRE_BYTES` | 200 MiB | Hipótese: o registro é mais importante que o vídeo e nunca pode ficar sem espaço por causa dele |
| `CAMERA_PARADA_FECHA_S` | `SEGUNDOS_DEPOIS` + 2 | — |
| `ESPERA_FECHAR_S` | 30 | Tempo máximo esperando a gravação no encerramento |

## 5. Detector de recorrência

Entradas, todas já produzidas pelo motor (nenhuma mudança em `vision/`):

| Entrada | De onde vem |
|---|---|
| Microssono | Evento `microssono` em `state.events`: um por fechamento de 1 s ou mais (`drowsiness.py:353-364`); `sono` e `nao_responsivo` do mesmo fechamento não contam de novo |
| Nível de sonolência | `state.drowsiness.level` (`drowsiness.py:88`). Sem perfil individual fica em 0 fora dos fechamentos (`drowsiness.py:452-453`): o critério de 15 min só vale depois da calibração |
| Ativação | `state.activation.compatible` (`activation.py:95-97`): exige linha de base, 2 ou mais sinais convergindo e confiança mínima. Só lida nos modos `registro` e `enviar` |

Regras:

| Gatilho | Critério | Dispara quando | Depois do disparo |
|---|---|---|---|
| `sonolencia_recorrente` | `microssonos_30min` | O microssono recebido faz 3 ou mais nos últimos 1.800 s | Os microssonos contados são consumidos: o próximo precisa de 3 novos |
| `sonolencia_recorrente` | `sonolencia_15min` | Nível ≥ 2 contínuo por 900 s; queda abaixo de 2 por menos de 60 s não interrompe, por 60 s ou mais zera | A contagem recomeça do instante do disparo |
| `ativacao_atipica_recorrente` | `ativacao_10min` | `compatible` contínuo por 600 s; lacuna menor que 120 s não interrompe | A contagem recomeça do instante do disparo |

Motivo gravado (texto fixo):
- `microssonos_30min`: "sonolência recorrente: 3 microssonos em 30 min"
- `sonolencia_15min`: "sonolência recorrente: 15 min seguidos em nível de sonolência"
- `ativacao_10min`: **"sinais compatíveis com ativação atípica (não é diagnóstico)"**

```python
@dataclass
class Gatilho:
    tipo: str          # sonolencia_recorrente | ativacao_atipica_recorrente
    criterio: str      # microssonos_30min | sonolencia_15min | ativacao_10min
    motivo: str
    instante: float    # relógio monotônico do quadro que disparou
    valores: dict      # {"microssonos": 3, "janela_s": 1800} | {"sonolencia_s": 900.4} | {"ativacao_s": 600.2}

class DetectorRecorrencia:
    def __init__(self, config: ConfigTrechos = ConfigTrechos())
    def observar(self, t: float, microssonos: int, nivel_sonolencia: int,
                 ativacao_compativel: bool | None) -> list[Gatilho]   # None = ativação não observada (modo local)
```

## 6. Buffer circular e captura

- **Amostragem:** no loop da câmera, `observar(frame, state)` só entrega o quadro se `t ≥ próxima amostra`
  (1/`FPS_TRECHO` s). A entrega é uma referência numa fila de 2 posições; fila cheia pula o quadro e conta em
  `quadros_pulados`. Redução e JPEG rodam na thread `rotaguard-trechos-jpeg` (o OpenCV solta o GIL nessas funções).
- **Suposição:** o quadro entregue não é modificado depois. Conferido: a janela desenha numa cópia
  (`driver_monitor.py:69`) e o celular converte para outra matriz (`phone.py:171`).
- **Buffer:** lista de (`t`, bytes JPEG, largura, altura) só em memória. Sai o que tem mais de `SEGUNDOS_ANTES` s e,
  se passar do teto de memória, o mais antigo.
- **Captura aceita:** copia do buffer os quadros com `t ≥ instante − SEGUNDOS_ANTES` e acrescenta os que chegam até
  `instante + SEGUNDOS_DEPOIS`. O primeiro quadro depois disso fecha a captura. Se a captura bater no teto de memória,
  para de receber quadros (`cortado: memoria`).
- **Fim da viagem** (`fechar()`): fecha a captura aberta, espera a gravação até `ESPERA_FECHAR_S`, esvazia o buffer e
  zera os contadores de memória.
- Com `--sem-trechos`, nenhum quadro é copiado nem entregue à fila.

## 7. Arquivo do trecho

### 7.1 Vídeo: AVI com MJPEG, montado em memória

- Os quadros já estão em JPEG no buffer. O AVI com MJPEG (Motion JPEG) é só um contêiner em volta deles: **não há
  nova codificação** e o custo de CPU no Pi 4 fica perto de zero.
- **Nenhuma imagem sem cifra toca o disco.** O `cv2.VideoWriter` só escreve num caminho de arquivo; um temporário no
  cartão SD pode ser recuperado depois de apagado.
- Abre no VLC, no ffmpeg e no OpenCV. O app (spec 004) pode ler os JPEGs direto com `ler_quadros_avi`.
- **Custo:** fica 5 a 10 vezes maior que H.264. Estimativa: 30 a 45 KB por quadro de 640×480 com qualidade 70, logo
  6 a 9 MB por trecho de 20 s e 70 a 110 MB numa viagem com os 12 trechos. Com o teto de 2 GiB, cabem ~20 viagens
  cheias sem coleta.
- O codificador H.264 do chip do Pi 4 fica como opção da spec 005. O campo `formato` do `trecho_gravado` já permite
  outro valor.

> [!note] Hipótese, confirmar
> Tamanho por quadro e tempo de JPEG por quadro no Pi 4 não foram medidos: dependem da imagem real da cabine
> (câmera infravermelha em tons de cinza comprime melhor).

### 7.2 Cifra

```
bytes 0-7    "RGTRECHO"
byte  8      versão = 1
bytes 9-20   nonce: 12 bytes de os.urandom
resto        AES-256-GCM: texto cifrado + etiqueta de 16 bytes
```

- Chave: `K_trechos = derivar_chave(chave_caixa, b"rotaguard/trechos/aes-256-gcm/v1")` (HKDF-SHA256, spec 001 §4.2).
- Dados associados (AAD): `"RGTRECHO"` + versão + `viagem_id` + `"\n"` + número com 3 dígitos. Arquivo trocado de
  viagem ou de número falha ao decifrar.
- Gravação: `trechos/trecho-NNN.enc.parcial` → `write` → `fsync` → `rename` para `trecho-NNN.enc` → `fsync` da pasta
  → SHA-256 dos bytes cifrados → linha `trecho_gravado`.
- O nome do arquivo não revela o motivo.

### 7.3 Funções públicas

`caixa/vision/cifra_trechos.py` (depende só de `cryptography` e de `vision/registro.py`):

```python
MAGICA = b"RGTRECHO"; VERSAO = 1
class TrechoInvalido(Exception): ...
def cifra_disponivel() -> bool
def cifrar_trecho(conteudo: bytes, chave_caixa: bytes, viagem_id: str, numero: int) -> bytes
def decifrar_trecho(cifrado: bytes, chave_caixa: bytes, viagem_id: str, numero: int) -> bytes   # TrechoInvalido
```

`caixa/vision/trechos.py`:

```python
def montar_avi_mjpeg(quadros: list[bytes], largura: int, altura: int, fps: float) -> bytes
def ler_quadros_avi(avi: bytes) -> list[bytes]

class GravadorTrechos:
    def __init__(self, registro, chave_caixa: bytes, dir_viagens: Path, config: ConfigTrechos = ConfigTrechos(),
                 modo_ativacao: Callable[[], str] = lambda: "local", background: bool = True,
                 escritor: Callable[[Path, bytes], None] | None = None,
                 uso_disco: Callable[[], int] | None = None, espaco_livre: Callable[[], int] | None = None)
    def observar(self, frame, state) -> None         # ouvinte do DriverMonitor
    def tick(self, agora_mono: float | None = None) -> None   # fecha captura se a câmera parou
    def fechar(self, timeout: float = ESPERA_FECHAR_S) -> None
    quadros_em_memoria: int; bytes_em_memoria: int; trechos_aceitos: int
```

`background=False` roda JPEG e gravação na própria chamada (testes), como o `PhoneMonitor` (`phone.py:200`).

## 8. Linhas no registro (tipos da spec 001)

| Tipo | Quando | `dados` |
|---|---|---|
| `recorrencia` | No instante do gatilho, antes de conferir limites | `gatilho`, `criterio`, `motivo`, `valores`, `instante_mono` |
| `trecho_gravado` | Depois do `rename` do arquivo | `numero`, `arquivo` (relativo à pasta da viagem), `recorrencias` [seq], `gatilhos` [{`gatilho`, `criterio`, `motivo`}], `inicio_utc`, `fim_utc`, `inicio_mono`, `fim_mono`, `duracao_s`, `antes_s`, `depois_s`, `quadros`, `quadros_pulados`, `fps`, `largura`, `altura`, `formato` (`"avi-mjpeg"`), `cifra` (`"AES-256-GCM"`), `kdf` (`"HKDF-SHA256"`), `bytes`, `sha256`, `cortado` (`null`, `memoria`, `fim_da_viagem` ou `camera_sem_imagem`) |
| `trecho_descartado` | Limite batido ou falha | `recorrencias` [seq], `gatilhos`, `motivo`, `detalhe`, `numero` (se já tinha), e os números do motivo: `trechos_na_viagem`, `segundos_desde_o_ultimo`, `uso_disco_bytes`, `teto_disco_bytes`, `espaco_livre_bytes` |

- `inicio_utc` e `fim_utc` saem do relógio da caixa (`utc_agora − (mono_agora − t_quadro)`) e podem estar errados.
  `inicio_mono` e `fim_mono` deixam o importador corrigir pela regra da spec 001 §6.4.

## 9. Limites, na ordem em que são conferidos

| # | Situação | Resultado |
|---|---|---|
| 1 | Já existe captura aberta | O gatilho entra em `gatilhos` dessa captura e marca o instante do seu tipo |
| 2 | Cifra indisponível | `cifra_indisponivel` |
| 3 | `trechos_aceitos` = 12 | `limite_por_viagem` |
| 4 | Último aceito do mesmo tipo há menos de 600 s | `intervalo_minimo` (gatilho recusado não reinicia a contagem) |
| 5 | Buffer vazio | `sem_imagem` |
| 6 | Soma dos `*/trechos/*.enc` de todas as viagens + estimativa passa do teto | `teto_de_disco` |
| 7 | Espaço livre menor que a estimativa + `RESERVA_LIVRE_BYTES` | `disco_cheio` |

- Na gravação, 6 e 7 são conferidos de novo com o tamanho real. Falha de escrita → `erro_de_gravacao`; só o
  `.parcial` da própria tentativa (cifrado e incompleto) é removido, e a linha registra isso.
- **Esta spec nunca apaga um `.enc`.** Quando o teto é atingido, os trechos novos são recusados e registrados. Apagar
  depois da coleta confirmada é da spec 003. Isso atende o RNF-07 ("nunca apaga trecho ainda não coletado sem
  registrar").

## 10. Privacidade

- Buffer só na memória. Nenhum arquivo, nem temporário, com imagem sem cifra.
- **D1, decidida pelo coordenador em 11/09/2026: modo `registro`.**
  - Motivo: o modo `local` promete que as métricas de ativação ficam na caixa e só mexem no nível de risco (README,
    "Privacidade"; `engine.py:223-235`). O registro e os trechos são entregues à empresa na coleta. Um trecho marcado
    "sinais compatíveis com ativação atípica" é inferência sobre dado pessoal sensível (LGPD, art. 5º, II, e art. 11).
  - Novo valor `registro` em `--sinais-ativacao`: os sinais entram no registro (spec 001 §5.1) e podem gerar trecho,
    mas **não** vão ao vivo (eventos e estado ao vivo iguais ao `local`).
  - Exige o mesmo consentimento do `enviar` (`sinais_ativacao_envio`). Sem ele, a caixa se comporta como `local`.
    Pela linha de comando, o consentimento é `--consentimento-sinais-ativacao`
    (`DRIVESAFE_CONSENTIMENTO_SINAIS_ATIVACAO`).
  - `enviar` também grava no registro e gera trecho.
  - Com a configuração padrão (`local`), continua **sem trecho por ativação**; só por sonolência.
  - **Tarefa da spec 006:** incluir `registro` em `ACTIVATION_POLICIES` (`servidor/backend/database.py:23`) e, em
    `device_policy` (`servidor/backend/routes/device_api.py:51-58`), trocar `registro` por `local` sem o
    consentimento, como já é feito com `enviar`. Esta spec não mexe em `servidor/`.
- O motivo de ativação é sempre "sinais compatíveis com ativação atípica (não é diagnóstico)". Nenhum texto usa
  "droga", "anfetamina", "rebite" ou "uso de".
- **Swap:** se o Raspberry Pi OS mandar o buffer para o arquivo de troca (`dphys-swapfile`), quadros sem cifra podem
  ir para o cartão. Recomendação à spec 005: desligar a troca ou usar zram.
- Retenção depois da coleta (Q4), quem vê os trechos e auditoria de acesso: specs 003 e 004.
- RNF-10 (licenças): `cryptography` é Apache-2.0 ou BSD-3-Clause, à escolha. Registrar em `THIRD_PARTY_NOTICES.md`.

## 11. Dependência nova

- `cryptography==50.0.1` em `caixa/requirements.txt`.
  - Última estável conferida em 11/09/2026 com `pip index versions cryptography`.
  - Tem pacote pronto (wheel `cp311-abi3-manylinux_2_34_aarch64`) para o Raspberry Pi OS Bookworm (Python 3.11) e
    Trixie (Python 3.13), conferido com `pip install --dry-run --platform manylinux_2_34_aarch64`.
  - Instalado no `.venv` em 11/09/2026 (Windows, Python 3.14.5).
- Sem a biblioteca, a caixa roda normalmente, com trechos desligados e registrados (T12).

## 12. Integração prevista

- **`caixa/run_monitor.py`:**
  - Opções novas: `--trechos` / `--sem-trechos` (`DRIVESAFE_TRECHOS`, **ligado**) e `--trechos-teto-disco-gb`
    (`DRIVESAFE_TRECHOS_TETO_GB`, 2).
  - Trechos precisam do registro: com `--sem-registro`, ficam desligados e o log avisa.
  - `GravadorTrechos(registro, chave, dir_viagens, config, modo_ativacao=lambda: engine.activation_mode)`: lê o modo a
    cada quadro, porque a política do servidor pode trocá-lo em execução (`remote_policy.py:83`).
  - Entra em `monitor.listeners` **depois** do `ObservadorRegistro`, para o evento de microssono já estar no registro
    quando a `recorrencia` for escrita.
  - A thread de relógio da spec 001 chama também `gravador.tick()`.
  - No `finally`: `gravador.fechar()` antes de `observador.fechar(motivo)`.
  - `--sinais-ativacao registro` sem `--consentimento-sinais-ativacao` vira `local`, com aviso no log (D1).
- **`caixa/vision/engine.py`:** `registro` entra em `ACTIVATION_MODES`, mais a constante dos modos que gravam
  ativação no registro. Nada muda no filtro dos eventos nem no `share_activation`.
- **`caixa/vision/driver_monitor.py` e `caixa/vision/remote_policy.py`:** nenhuma mudança. Tudo o que o detector
  precisa já está no `DriverState`, e a política do servidor já aceita qualquer valor de `ACTIVATION_MODES`.
- **Serviço systemd (spec 005):** o tempo de parada precisa cobrir `ESPERA_FECHAR_S` (30 s); o padrão do systemd é
  90 s.
- **README e THIRD_PARTY_NOTICES:** atualizar a privacidade ("nunca imagens" vira "imagens só em trechos por
  recorrência, cifrados") e a licença do `cryptography`.

## 13. Critérios de aceite

| ID | Critério (teste em `tests/test_trechos.py`, quadros sintéticos com numpy) |
|---|---|
| TRE-01 | O buffer guarda só os últimos `SEGUNDOS_ANTES` s, no máximo `FPS_TRECHO` quadros por segundo, em JPEG com largura de até 640 px e a proporção mantida; 5 min de quadros sem gatilho não criam nenhum arquivo nem pasta |
| TRE-02 | `bytes_em_memoria` nunca passa do teto de memória; ao passar, sai o quadro mais antigo |
| TRE-03 | **Nada fora de gatilho (obrigatório):** 40 min de estados abaixo dos critérios (2 microssonos em 30 min, 14 min de sonolência, 9 min de ativação compatível no modo `enviar`) não geram nenhum `.enc`, nenhuma chamada ao escritor de arquivo e nenhuma linha `recorrencia`, `trecho_gravado` ou `trecho_descartado` |
| TRE-04 | 3 microssonos em até 30 min disparam `sonolencia_recorrente` (`microssonos_30min`) no instante do 3º; 3 espalhados por mais de 30 min não disparam; depois do disparo a contagem recomeça |
| TRE-05 | Nível de sonolência ≥ 2 por 15 min dispara `sonolencia_15min`; interrupção menor que 60 s não zera; interrupção de 60 s ou mais zera |
| TRE-06 | Nos modos `registro` e `enviar`, ativação compatível por 10 min (lacunas menores que 120 s) dispara `ativacao_atipica_recorrente` com o motivo exato "sinais compatíveis com ativação atípica (não é diagnóstico)"; nenhuma linha do registro contém "droga", "anfetamina", "rebite" ou "uso de" |
| TRE-07 | Nos modos `local` e `desligado`, o mesmo cenário não gera gatilho, trecho nem linha que mencione ativação; o modo é lido a cada quadro, então trocar de `registro` para `local` no meio da viagem para de contar |
| TRE-08 | O trecho tem os quadros de `instante − 10 s` a `instante + 10 s`, em ordem (brilho crescente dos quadros sintéticos), dura no máximo 20 s mais um quadro e, decifrado, abre no OpenCV como AVI com o número de quadros e o tamanho declarados em `trecho_gravado`; `ler_quadros_avi` devolve os mesmos JPEGs |
| TRE-09 | Com o escritor atrasado 2 s, `observar()` continua retornando em menos de 50 ms e a detecção segue; a linha `trecho_gravado` chega depois |
| TRE-10 | O arquivo começa com `RGTRECHO` e versão 1 e decifra com a chave da caixa; chave errada, 1 byte alterado, viagem trocada ou número trocado levantam `TrechoInvalido`; o escritor nunca recebe bytes que comecem com `RIFF`, e nenhum arquivo em disco contém o cabeçalho `AVI ` |
| TRE-11 | `trecho_gravado` traz número, arquivo, gatilhos com motivo, início e fim (UTC e monotônico), duração, quadros, fps, largura, altura, formato, cifra, bytes e SHA-256; o SHA-256 confere com o arquivo e `verificar_viagem` (REG-23) aceita |
| TRE-12 | Com o máximo de 12, o 13º gatilho gera `trecho_descartado` `limite_por_viagem` e nenhum arquivo |
| TRE-13 | Segundo gatilho do mesmo tipo antes de 10 min gera `trecho_descartado` `intervalo_minimo`; gatilho do outro tipo no mesmo período grava |
| TRE-14 | Com o uso de disco no teto (padrão 2 GiB, configurável), o gatilho gera `teto_de_disco`; com espaço livre abaixo da estimativa mais a reserva, `disco_cheio`; nos dois casos os `.enc` existentes continuam lá com o mesmo SHA-256 |
| TRE-15 | Sem biblioteca de cifra: `estado_aparelho` `trechos_indisponiveis` no início, nenhum quadro entra no buffer e cada gatilho vira `recorrencia` + `trecho_descartado` `cifra_indisponivel` |
| TRE-16 | Gatilho durante uma captura aberta vira mais um item em `gatilhos` do mesmo trecho (um arquivo só) e conta o intervalo do seu tipo |
| TRE-17 | `fechar()` com captura aberta grava o trecho (`cortado: fim_da_viagem`) antes do `fim_viagem`; câmera sem quadro por mais de `SEGUNDOS_DEPOIS` + 2 s fecha a captura (`cortado: camera_sem_imagem`) |
| TRE-18 | Depois de `fechar()`, `quadros_em_memoria` e `bytes_em_memoria` são 0; com trechos desligados, nenhum quadro é copiado |
| TRE-19 | A linha `recorrencia` é escrita no instante do gatilho, antes do arquivo; viagem interrompida entre o gatilho e a gravação aparece em `resumo.recorrencias_sem_trecho` da verificação |
| TRE-20 | Trechos ligados por padrão; `--sem-trechos` desliga; `--sem-registro` desliga os trechos junto; `caixa/requirements.txt` fixa `cryptography==50.0.1` |
| TRE-21 | Modo `registro`: aceito pelo motor e pela política do servidor; na linha de comando, sem `--consentimento-sinais-ativacao` vira `local`; no `registro`, os eventos da fila e o `live_status` não levam métricas de ativação (iguais ao `local`) |

## 14. Fora de escopo

- Apagar trechos depois da coleta, retenção (Q4), quem vê e auditoria de acesso (specs 003 e 004).
- Converter para H.264, tocar no app ou exportar (spec 004); codificador por hardware do Pi 4 (spec 005).
- Gravação contínua e vídeo ao vivo (PRD §5).
- Áudio.
- Borrar ou anonimizar o rosto no trecho.
- Decidir Q1 e Q2: os valores são os padrões do PRD.
- Consentimento de monitoramento (spec 006).

## 15. Riscos

| Risco | Impacto | Resposta |
|---|---|---|
| Vídeo do rosto é dado pessoal, possivelmente biométrico ou de saúde (PRD §9) | Alto | Só por gatilho, buffer em memória, AES-GCM, nome de arquivo neutro, ativação só com `registro` ou `enviar` e consentimento (D1); parecer jurídico antes de piloto |
| Servidor ainda não conhece o modo `registro` | Médio | A caixa aceita pela linha de comando; o servidor fica para a spec 006 (§10) |
| Buffer paginado para o cartão pela troca do sistema | Médio | Recomendação à spec 005: desligar a troca ou usar zram |
| Chave provisória no mesmo cartão dos trechos | Médio | A cifra só protege de verdade com a guarda de chave da spec 003 |
| Critérios de Q1 sem validação com motoristas reais | Médio | Constantes num lugar só; validar com as gravações da etapa 2 |
| JPEG a 10 quadros por segundo pesar no Pi 4 | Médio | Thread separada, fila de 2 com quadro pulado contado; medir na spec 005 |
| Corte de energia antes de o trecho ir para o disco | Baixo | `recorrencia` já gravada; `recorrencias_sem_trecho` na verificação |
| MJPEG ocupa mais disco que H.264 | Baixo | Teto de 2 GiB com recusa registrada; H.264 do chip como opção da spec 005 |

## 16. Decisões tomadas nesta spec

1. **D1: modo `registro`** (§10): ativação no registro e em trechos só com `registro` ou `enviar` e consentimento;
   nada ao vivo no `registro`.
2. **AVI com MJPEG montado em memória**, e não `cv2.VideoWriter` nem H.264 (§7.1): zero nova codificação e nenhum
   arquivo sem cifra no disco.
3. **AES-256-GCM com AAD** amarrando viagem e número, chave derivada por HKDF da chave da caixa (§7.2).
4. **Linha `recorrencia`** antes do vídeo, para o fato sobreviver a um corte de energia.
5. **Gatilho durante captura entra no mesmo trecho**, em vez de gravar dois vídeos sobrepostos.
6. **Nunca apagar `.enc` nesta spec**: no teto, recusa e registra.
7. **Reserva de 200 MiB** de espaço livre para o registro nunca ficar sem disco por causa de vídeo.
8. **Tolerância de 60 s** na sonolência contínua (hipótese), para oscilação de 1 s do nível não zerar os 15 min.
9. **Integração pelo ouvinte que já existe** no `DriverMonitor`: nenhuma mudança em `engine.py` nem em
   `driver_monitor.py`.
