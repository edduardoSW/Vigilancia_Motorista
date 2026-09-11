# Spec 001 · Registro da viagem

| Campo | Valor |
|---|---|
| Status | **rascunho**, aprovada em 11/09/2026 com ajustes (assinatura trocável com Ed25519; modo `registro` dos sinais de ativação) |
| Cobre | RF-06, RNF-03, RNF-04 do PRD 1.0; objetivo O2; riscos "registro contestado como prova" e "corte de energia" |
| Depende de | spec 003 (ID e chave da caixa), spec 005 (fonte do relógio e temperatura no Pi 4), spec 006 (consentimento, RF-12) |
| Usada por | spec 002 (linhas de recorrência e trecho), spec 003 (coleta), spec 004 (importador usa `verificar_viagem`) |
| Código previsto | `caixa/vision/registro.py` (só biblioteca padrão), `caixa/vision/observador_registro.py`, `caixa/run_monitor.py` |
| Testes previstos | `tests/test_registro.py` |

## 1. Contexto e vínculo com o PRD

- Palavras do Matheus (PRD §11): "o principal analisado e mais importante deve ser a log, que seria o registro. A
  empresa, quando o motorista chegar, deve recolher o equipamento e, ao conectar, o sistema deve reconhecer o
  equipamento e gerar o relatório."
- PRD §3: o registro é a peça principal da caixa. O2: 100% dos eventos no relatório, e qualquer alteração ou remoção
  detectada.
- **Hoje** os eventos só vão para a fila SQLite (`caixa/vision/event_queue.py:32`). Ela muda de estado (`status`,
  `attempts`) e apaga enviados depois de 30 dias (`event_queue.py:117`), sem nenhuma integridade. Serve para o envio
  ao vivo, que continua opcional (RF-11), mas não serve como registro.
- Esta spec cria um **arquivo separado, só por acréscimo, encadeado por hash e selado com a chave da caixa**. A fila
  continua como está.

## 2. Termos

| Termo | Significado |
|---|---|
| Viagem | Uma execução do `caixa/run_monitor.py`, do início do monitoramento ao encerramento. Se a caixa reinicia no meio do caminho, começa uma viagem nova e a anterior é fechada como interrompida (§7). O relatório (spec 004) pode juntar viagens seguidas |
| Chave da caixa | Segredo simétrico de pelo menos 32 bytes, **injetado** por quem cria o registro. Geração e guarda são da spec 003 |
| Par Ed25519 da caixa | Chave privada só na caixa; a empresa verifica com a chave pública. Gerado no pareamento (spec 003) |
| Assinador | Objeto que assina as linhas: `hmac-sha256` (com a chave da caixa) ou `ed25519` (com a chave privada), §4.2 |
| Linha assinada | Linha com os campos `alg` e `assinatura` (§4.2) |
| Boot | Período entre ligar e desligar o sistema. Identificado por `boot_id` (`event_queue.py:19`); dentro dele, `time.monotonic()` é comparável |

## 3. Onde fica

```
<dir_viagens>/                     padrão <data-dir>/viagens  (--viagens-dir, DRIVESAFE_VIAGENS_DIR)
  contador_viagens                 último número de viagem (gravação atômica: temporário + fsync + rename)
  000042-9f3ac1d2/                 <número com 6 dígitos>-<8 hex aleatórios>
    registro.jsonl                 o registro (esta spec)
    registro.trava                 trava exclusiva enquanto a viagem está aberta (§7)
    trechos/                       trechos cifrados (spec 002)
```

- A pasta **não** leva data no nome: o relógio da caixa pode estar errado (§6). A ordem entre viagens é a do número.
- Se `contador_viagens` sumir ou estiver ilegível, o próximo número é o maior número de pasta existente + 1.
- Buraco na numeração depois da coleta (spec 003) mostra viagem apagada.

## 4. Formato da linha

Um objeto JSON por linha, em UTF-8, terminado em `\n`. Campos **nesta ordem**:

| Campo | Tipo | Conteúdo |
|---|---|---|
| `seq` | inteiro | 1, 2, 3… sem buracos |
| `utc` | texto | Relógio de parede da caixa, ISO 8601 em UTC com milissegundos e `Z`. **Pode estar errado** (§6) |
| `mono` | número | `time.monotonic()` em segundos, 3 casas. Ordem e duração confiáveis dentro do mesmo boot |
| `tipo` | texto | §5 |
| `dados` | objeto | Chaves em ordem alfabética; sem `NaN` nem `Infinity` (viram `null`) |
| `prev` | texto | `hash` da linha anterior; na linha 1, 64 zeros |
| `alg` | texto | Só nos tipos assinados: `hmac-sha256` ou `ed25519` |
| `assinatura` | texto | Só nos tipos assinados: hex minúsculo, 64 caracteres (HMAC) ou 128 (Ed25519) |
| `hash` | texto | SHA-256 em hex minúsculo |

Exemplo (quebrado aqui só para caber):

```json
{"seq":7,"utc":"2026-09-11T03:15:00.123Z","mono":8123.456,"tipo":"evento",
 "dados":{"alerta":"microssono","detalhes":{"fechado_s":1.02,"nivel_risco":3},"duracao_s":1.02,"nivel":3},
 "prev":"5f0c…e1","hash":"9ab4…07"}
```

### 4.1 Regra do hash (sobre os bytes gravados)

1. `B` = bytes da linha sem o `\n` final.
2. `B` precisa terminar em `,"hash":"` + 64 hex + `"}`. `corpo` = `B` sem esse sufixo, mais `}`.
3. `hash = SHA-256(corpo)`.

Por que bytes e não "JSON canônico" reserializado: o importador pode estar em outra linguagem, e número em ponto
flutuante e escape de acento saem diferentes entre Python e JavaScript (`1.0` × `1`, `1e-07` × `1e-7`). Com a regra
por bytes, a verificação não depende do serializador.

### 4.2 Assinatura (algoritmo trocável)

- Tipos assinados: `selo`, `ajuste_relogio`, `fim_viagem`, `viagem_interrompida`.
- Nesses tipos, os três últimos campos são `"alg":"…","assinatura":"<hex>","hash":"…"`. `corpo` (§4.1) termina em
  `,"assinatura":"<hex>"}`; `corpo_sem_assinatura` = `corpo` sem esse sufixo, mais `}`. O `alg` fica dentro de
  `corpo_sem_assinatura` e também é assinado.
- Mensagem assinada, igual nos dois algoritmos: `"rotaguard/registro/v1\n" + corpo_sem_assinatura`.
- `corpo_sem_assinatura` contém `prev`: a assinatura cobre **a cadeia inteira até ali e o conteúdo da própria linha**.

| `alg` | Quando | Chave | Assinatura |
|---|---|---|---|
| `ed25519` | **Produção**, quando a caixa tem o par de chaves da spec 003 | Privada só na caixa; a empresa verifica com a pública (32 bytes) | 64 bytes (128 hex). Precisa do `cryptography` para assinar e para verificar |
| `hmac-sha256` | Testes e caixa sem par de chaves | `K_reg = HKDF-SHA256(chave_caixa, salt vazio, info = "rotaguard/registro/hmac/v1", 32 bytes)`, como no RFC 5869 | 32 bytes (64 hex). Assina e verifica só com a biblioteca padrão |

- `inicio_viagem.dados.assinatura` = {`alg`, `id_chave`} e, no HMAC, `kdf` = `"HKDF-SHA256"`.
  - `id_chave`: 16 hex. No Ed25519, início do SHA-256 da chave pública; no HMAC, início do
    `HMAC-SHA256(K_reg, "rotaguard/registro/id-chave/v1")`. Serve para o importador escolher a chave; não revela a
    chave.
- **Por que HMAC com chave derivada:** separa a chave do HMAC da chave AES dos trechos (spec 002) e de outros usos
  da spec 003. Vazar um uso não entrega o outro.
- **Por que Ed25519 em produção:** o HMAC é simétrico, então quem verifica também poderia forjar (§8.3). Com Ed25519,
  só a caixa assina.
- **Troca para um algoritmo mais fraco:** quem tem a chave HMAC poderia reescrever uma viagem inteira como
  `hmac-sha256`. O importador de produção chama a verificação com `exigir_alg="ed25519"` (§8), e linha com outro
  `alg` vira problema.

## 5. Tipos de linha

| Tipo | Quando | `dados` mínimos | Assinada |
|---|---|---|---|
| `inicio_viagem` | Sempre a linha 1 | `formato` = `"rotaguard-registro/1"`, `viagem_id`, `numero`, `caixa` {`id` (spec 003; `null` até lá), `hostname`, `plataforma`, `versao_software`}, `relogio` (§6), `assinatura` {`alg`, `id_chave`, e `kdf` no HMAC} (§4.2), `selo_a_cada_s`, `config` {`camera`, `largura`, `altura`, `sinais_ativacao`, `celular`, `trechos`, `calibracao_min_s`, `calibracao_max_s`}, `motorista` (`null`; spec 006), `viagens_interrompidas_fechadas` [ids] | não |
| `calibracao` | Início e fim de cada calibração | `fase` (`inicio` ou `fim`), `motivo` (`inicio_da_viagem` ou `recalibracao`); no fim, `resultado` (`concluida`, `suspeita` ou `sem_dados`). As métricas do perfil ficam no `evento` `calibracao_concluida`/`calibracao_suspeita`, como na fila | não |
| `evento` | Cada evento que hoje vai para a fila (`driver_monitor.py:176-177`) | `alerta`, `nivel`, `duracao_s`, `detalhes`. `detalhes` é o mesmo dicionário já filtrado por `engine._decorate` (`engine.py:223-235`) | não |
| `resumo_minuto` | A cada 60 s de relógio monotônico, **mesmo sem quadros** | `janela_s`, `quadros`, `fps`, `nivel_risco_max`, `nivel_risco_fim`, `fracao_rosto`, `fracao_olhos_visiveis`, `celular` {estado: segundos, só os não zerados}, `em_calibracao`, `camera_ok`, `latencia_p95_ms`, `temperatura_cpu_c` (`null` se não houver leitura), `direcao_continua_h`, `madrugada`. `ativacao` {`estado`, `indice`, `confianca`, `sinais`} **só nos modos `registro` e `enviar`** (§5.1) | não |
| `estado_aparelho` | Mudança de estado da caixa | `evento` (`camera_sem_imagem`, `camera_voltou`, `trechos_indisponiveis`, `chave_temporaria`) e `detalhes`. A spec 005 acrescenta temperatura alta e estrangulamento térmico | não |
| `recorrencia`, `trecho_gravado`, `trecho_descartado` | Definidos na spec 002 | — | não |
| `selo` | A cada 300 s monotônicos desde o último selo (ou do início) | `ate_seq` (seq da linha anterior) | **sim** |
| `ajuste_relogio` | Salto do relógio detectado, ou medida externa da hora (§6) | §6.3 | **sim** |
| `fim_viagem` | Encerramento normal. É a última linha; depois dela só pode vir `ajuste_relogio` | `motivo` (`normal`, `desligamento` ou `erro`), `detalhe`, `linhas`, `duracao_s` | **sim** |
| `viagem_interrompida` | Na inicialização seguinte, para viagem sem fechamento (§7) | `boot_id` (o atual), `ultima_seq_valida`, `ultimo_utc`, `ultimo_mono`, `verificacao` {`integra`, `problema`}, `linha_truncada` {`bytes`, `sha256`} ou `null`, `quebra_de_linha_acrescentada`, `fechada_pela_viagem` | **sim** |

### 5.1 Sinais de ativação no registro

| Modo (`--sinais-ativacao`) | Consentimento `sinais_ativacao_envio` | No registro | Ao vivo (fila e servidor) |
|---|---|---|---|
| `desligado` | — | nada | nada |
| `local` | — | nada (só mexe no nível de risco) | nada |
| `registro` (**novo**) | exigido; sem ele vira `local` | `resumo_minuto.ativacao` e trechos por ativação (spec 002) | nada, como no `local` |
| `enviar` | exigido (servidor, `device_api.py:55`) | igual ao `registro` | eventos e métricas, como hoje |

- O `registro` existe porque a coleta na chegada também entrega os dados à empresa: é o mesmo nível de exposição do
  `enviar`, sem o envio ao vivo. Decisão do coordenador em 11/09/2026 (D1 da spec 002).
- Os eventos continuam os da fila, já filtrados por `engine._decorate` (`engine.py:223-235`): no `registro`, nenhum
  evento leva métricas de ativação. O que entra é o resumo por minuto e o trecho.
- Na linha de comando, `registro` só vale com `--consentimento-sinais-ativacao`
  (`DRIVESAFE_CONSENTIMENTO_SINAIS_ATIVACAO`); sem a opção, a caixa usa `local` e avisa no log. O `enviar` pela linha
  de comando continua como hoje: conferir consentimento nele é da spec 006.
- Pela política do servidor, a caixa aceita `registro` (lista `ACTIVATION_MODES`, `engine.py:34`). **Tarefa da
  spec 006:** incluir `registro` em `ACTIVATION_POLICIES` (`servidor/backend/database.py:23`) e, em `device_policy`
  (`device_api.py:51-58`), trocar `registro` por `local` sem o consentimento, como já é feito com `enviar`.

## 6. Relógio

O Raspberry Pi 4 não tem relógio com bateria (RTC). Sem internet não há NTP, e depois de um corte de energia o
`fake-hwclock` devolve a hora do último desligamento. As horas do registro podem sair erradas. Regras:

### 6.1 Âncora no início

`inicio_viagem.dados.relogio`:

| Campo | Conteúdo |
|---|---|
| `fonte` | `ntp` (sincronizado), `rtc` (relógio com bateria), `sistema` (Windows ou macOS: o sistema cuida da hora, não dá para conferir daqui) ou `sem_fonte_confiavel` |
| `detalhe` | De onde veio a conclusão (ex.: `"/run/systemd/timesync/synchronized"`) |
| `boot_id` | `current_boot_id()` (`event_queue.py:19`) |
| `plausivel` | Ano ≥ 2024 |

A própria linha tem `utc` e `mono`: é a âncora da viagem.

Detecção no Linux (função injetável `detectar_fonte_relogio()`):
- `ntp`: existe `/run/systemd/timesync/synchronized`, ou `adjtimex` sem o bit `STA_UNSYNC`.
- `rtc`: `/sys/class/rtc/rtc0/since_epoch` legível, com ano ≥ 2024 e diferença de até 5 s para a hora do sistema.
- Senão, `sem_fonte_confiavel`.

> [!note] Hipótese, confirmar
> A detecção de `ntp` e `rtc` foi escrita pela documentação do systemd e do kernel, sem Pi 4 em mãos. Com o módulo
> DS3231, o Raspberry Pi OS acerta a hora pela regra do udev (`hwclock-set`), e não pelo `hctosys` do kernel; por isso a
> checagem compara as duas horas. A spec 005 confirma no hardware.

### 6.2 Toda linha com UTC e monotônico

- Ordem e duração saem sempre de `mono`, dentro do mesmo boot. Uma viagem inteira fica num boot só.
- Linhas escritas por outro boot (`viagem_interrompida`, `ajuste_relogio` depois do fechamento) levam `boot_id` em
  `dados` e ficam fora da linha do tempo da viagem.

### 6.3 `ajuste_relogio`, sem reescrever linhas antigas

| Campo | Conteúdo |
|---|---|
| `origem` | `salto_detectado` (a própria caixa) ou `coleta`, `ntp`, `manual` (medida externa) |
| `referencia` | `ntp`, `rtc`, `app_na_coleta` ou `desconhecida` |
| `utc_caixa` | Hora da caixa no instante da medida |
| `utc_referencia` | Hora certa no mesmo instante, ou `null` se não há referência confiável |
| `deslocamento_s` | `utc_referencia − utc_caixa`, ou `null` |
| `salto_s` | Só em `salto_detectado`: `(Δutc − Δmono)` entre duas checagens |
| `boot_id` | Boot de quem escreveu a linha |

- **Salto detectado:** a cada checagem (~1 s), se `|Δutc − Δmono| > 2 s`, a caixa escreve `ajuste_relogio` com
  `origem` = `salto_detectado`. `referencia` é a fonte detectada depois do salto; se for `ntp` ou `rtc`,
  `utc_referencia` é o `utc` da própria linha.
- **Medida externa:** `registrar_ajuste_relogio(...)` (§9) acrescenta a linha numa viagem aberta ou já fechada. A
  spec 003 usa na coleta, com a hora do computador que conecta a caixa.

### 6.4 Horas confiáveis na verificação

A verificação devolve `horario` = {`confiavel`, `metodo`, `motivo`, `fonte_inicio`, `saltos`, `ajustes`} e, em cada
linha, `utc_corrigido`.

A primeira situação que se aplica, de cima para baixo, decide:

| # | Situação | `confiavel` | `metodo` | `utc_corrigido` de cada linha do boot da viagem |
|---|---|---|---|---|
| 1 | Há `ajuste_relogio` **no mesmo boot** com referência `ntp`, `rtc` ou `app_na_coleta` | sim | `monotonico` | `utc_referencia + (mono − mono_ajuste)`, pela âncora mais próxima em `mono` |
| 2 | `fonte` do início é `ntp` | sim | `monotonico` | `utc_inicio + (mono − mono_inicio)` |
| 3 | `fonte` do início é `rtc` e há ajuste de **outro boot** (coleta) | sim | `deslocamento_constante` | `utc + deslocamento_s`: o RTC continuou contando desligado e o ajuste mede a deriva dele |
| 4 | `fonte` do início é `rtc`, sem ajuste | sim, com `motivo` `rtc_sem_conferencia` | `monotonico` | `utc_inicio + (mono − mono_inicio)` |
| 5 | Sem fonte no início e só ajuste de outro boot | **não** | `nenhum` | `null`: com `fake-hwclock`, o tempo desligado entre a viagem e a coleta se perde, e o deslocamento da coleta não vale para a viagem |
| 6 | Sem fonte e sem ajuste | **não** | `nenhum` | `null` |

- Sem hora confiável, ordem e durações continuam valendo (por `mono`); só a hora do dia fica em aberto.
- O relógio monotônico também deriva (cristal comum: dezenas de ppm, ~2 s em 12 h). O resultado informa a
  distância em horas até a âncora usada.

## 7. Durabilidade, energia e recuperação

### 7.1 Escrita

- Arquivo aberto com `os.open(O_WRONLY | O_APPEND | O_CREAT)`. Cada linha sai numa única chamada `os.write`, com o
  `\n`, seguida de `os.fsync`, **antes** de a função retornar.
- Pasta da viagem com `fsync` do diretório ao criar (Linux).
- **Nenhuma operação trunca, apaga ou altera bytes já gravados**, nem na recuperação.
- Custo estimado: uma linha por minuto, mais eventos e selos. Numa viagem de 12 h, ~1.000 `fsync` e ~300 KB.

- Onde cada linha é escrita:
  - `resumo_minuto`, `selo`, `estado_aparelho` de câmera e `ajuste_relogio` saem da thread de relógio (§9), fora do
    loop da câmera;
  - `evento`, `calibracao` e `recorrencia` saem do ouvinte do quadro, que roda **depois** do alarme
    (`driver_monitor.py:178-179`, ouvintes em `:238`). O `fsync` não atrasa o alarme; pode atrasar em alguns
    milissegundos o quadro seguinte a um evento.

> [!note] Hipótese, confirmar
> Tempo de `fsync` no cartão SD do Pi 4 não foi medido (spec 005). Como as linhas são raras, não deve pesar.

### 7.2 Trava

- `registro.trava` recebe trava exclusiva do sistema (`fcntl.flock` no Linux e no macOS, `msvcrt.locking` no Windows)
  enquanto a viagem está aberta.
- O sistema solta a trava se o processo morre. A recuperação pula viagem com trava tomada, para dois processos na
  mesma caixa não se atropelarem.

### 7.3 Recuperação ao iniciar

`RegistroViagem.iniciar(...)` chama `fechar_viagens_interrompidas(...)` antes de abrir a viagem nova. Para cada pasta
cuja última linha válida não é `fim_viagem` nem `viagem_interrompida`, e cuja trava está livre:

1. **Final do arquivo sem `\n`:**
   - se o pedaço final é uma linha válida e encadeada, acrescenta `\n` (`quebra_de_linha_acrescentada: true`);
   - senão, acrescenta `\n` e guarda em `linha_truncada` o tamanho e o SHA-256 do pedaço. O pedaço fica no arquivo.
2. Roda a verificação.
3. Acrescenta `viagem_interrompida` assinada, com `prev` = `hash` da última linha válida e `seq` = seguinte.

Nenhuma linha completa anterior se perde. Registro vazio (0 linhas válidas) recebe `viagem_interrompida` como linha 1.

Decisão: **não retomar** a viagem depois do reinício. O boot muda, o `mono` recomeça do zero e juntar dois boots
numa cadeia só complicaria a verificação. Fechar e abrir outra deixa a interrupção explícita no relatório.

### 7.4 Falha de escrita

- Disco cheio ou erro no cartão: o monitoramento e o alarme **continuam**.
- O registro loga o erro, marca `falhou = True` e **para de escrever**, porque escrever depois de uma escrita parcial
  deixaria lixo no meio do arquivo.
- Na inicialização seguinte a viagem é fechada como interrompida (§7.3).

## 8. Verificação (contrato para o importador, spec 004)

```python
def verificar_registro(caminho: Path, chave_caixa: bytes | None = None, chave_publica: bytes | None = None,
                       exigir_alg: str | None = None) -> VerificacaoRegistro
def verificar_viagem(pasta: Path, chave_caixa: bytes | None = None, chave_publica: bytes | None = None,
                     exigir_alg: str | None = None) -> VerificacaoRegistro   # também confere os trechos
```

- `chave_caixa` verifica as linhas `hmac-sha256`, só com a biblioteca padrão.
- `chave_publica` (32 bytes) verifica as linhas `ed25519`, com o `cryptography`. O módulo só importa o
  `cryptography` quando encontra uma linha `ed25519` e há chave pública.
- `exigir_alg`: toda linha assinada precisa ter esse `alg`. Produção usa `"ed25519"`.

### 8.1 `VerificacaoRegistro`

| Campo | Conteúdo |
|---|---|
| `integra` | `True` se nenhuma linha completa tem problema e todas as assinaturas que puderam ser conferidas conferem |
| `assinaturas_verificadas` | `True` só se **todas** as linhas assinadas foram conferidas (chave certa para o `alg` de cada uma e, no Ed25519, `cryptography` instalado) |
| `motivo_sem_verificacao` | Quando não verificou: `sem_chave`, `sem_chave_publica` ou `cryptography_ausente` |
| `algoritmos` | Conjunto de `alg` encontrados nas linhas assinadas |
| `problema` | `ProblemaRegistro` do **primeiro** problema, ou `None` |
| `final_truncado` | `nao`, `recuperado` (pedaço identificado por `viagem_interrompida`) ou `pendente` (arquivo termina sem `\n`) |
| `fechamento` | `fim_viagem`, `viagem_interrompida` ou `aberta` |
| `ultima_seq_assinada`, `linhas_depois_da_ultima_assinatura` | Quanto do final só tem a proteção do hash |
| `horario` | §6.4 |
| `resumo` | `viagem_id`, `numero`, `linhas`, `por_tipo`, `eventos_por_alerta`, `inicio_utc`, `fim_utc`, `inicio_utc_corrigido`, `fim_utc_corrigido`, `duracao_s` (por `mono`), `minutos_resumidos`, `recorrencias`, `trechos_gravados`, `trechos_descartados`, `recorrencias_sem_trecho` |
| `linhas` | Lista de {`numero_linha`, `conteudo` (dict), `utc_corrigido`, `confiavel`}; `confiavel` é falso a partir de `problema.desde_linha` |
| `trechos` | Só em `verificar_viagem`: [{`numero`, `arquivo`, `existe`, `sha256_confere`}] e `trechos_integros` |

`ProblemaRegistro`: `linha` (1 = primeira do arquivo), `seq` (encontrada), `tipo`, `detalhe`, `desde_linha`
(primeira linha em que não dá mais para confiar).

### 8.2 Tipos de problema, na ordem em que cada linha é checada

| Tipo | Quando | `desde_linha` |
|---|---|---|
| `arquivo_ausente` | Não existe `registro.jsonl` | — |
| `json_invalido` | Linha completa que não é JSON, não tem os campos com os tipos certos ou não tem o sufixo do hash. Exceção: pedaço truncado recuperado (§7.3) | a própria |
| `alterada` | SHA-256 do corpo diferente de `hash` | a própria |
| `linha_faltando` | `seq` maior que a esperada, e a esperada não aparece depois (o detalhe diz quais faltam) | a própria |
| `fora_de_ordem` | `seq` menor que a esperada (repetida ou antiga), ou maior e a esperada aparece mais adiante | a própria |
| `encadeamento_quebrado` | `prev` diferente do `hash` da linha anterior (linha trocada ou inserida com hash refeito) | a anterior |
| `assinatura_ausente` | Tipo assinado sem `alg` ou sem `assinatura` | a própria |
| `algoritmo_desconhecido` | `alg` diferente de `hmac-sha256` e `ed25519`, ou assinatura com tamanho que não é o do `alg` | a própria |
| `algoritmo_nao_aceito` | `exigir_alg` informado e a linha usa outro `alg` | a linha seguinte à última assinatura válida |
| `assinatura_invalida` | A assinatura não confere (só quando há chave para o `alg`) | a linha seguinte à última assinatura válida |
| `primeira_linha_invalida` | Linha 1 não é `inicio_viagem` (nem `viagem_interrompida` de registro vazio) | 1 |
| `linha_apos_fechamento` | Depois de `fim_viagem` ou `viagem_interrompida`, linha que não é `ajuste_relogio` | a própria |
| `monotonico_regrediu` | `mono` menor que o da linha anterior do mesmo boot | a própria |
| `pasta_nao_confere` | Só em `verificar_viagem`: `viagem_id` da linha 1 diferente do nome da pasta | 1 |

### 8.3 O que a verificação prova, e o que não prova

- **Sem chave:** detecta corrupção e edição que não refaz os hashes. Não detecta quem reescreve a cadeia inteira.
- **Com chave:** detecta qualquer mudança até a última linha assinada. As linhas depois da última assinatura (no
  máximo ~5 min de uma viagem que não foi fechada) só têm o hash; o resultado diz quantas são.
- **Limite do HMAC:** é simétrico. Quem verifica com a chave também pode forjar um registro. Por isso o HMAC fica
  para testes e para caixa sem par de chaves.
- **Com Ed25519:** só quem tem a chave privada, que fica na caixa, consegue assinar. A empresa verifica com a chave
  pública e não consegue forjar. Com `exigir_alg="ed25519"`, uma viagem reescrita como `hmac-sha256` é recusada.
- **O que nenhum dos dois cobre:** quem copiar a chave privada do cartão da caixa assina como ela. A guarda da chave
  é da spec 003.

## 9. Funções públicas

`caixa/vision/registro.py` (só biblioteca padrão, para o importador rodar sem OpenCV nem MediaPipe):

```python
MIN_CHAVE_BYTES = 32
SELO_A_CADA_S = 300.0
SALTO_RELOGIO_S = 2.0

@dataclass
class Relogio:                       # injetável nos testes
    utc: Callable[[], datetime]
    mono: Callable[[], float]

class Assinador(Protocol):          # interface trocável
    alg: str                         # "hmac-sha256" | "ed25519"
    id_chave: str                    # 16 hex
    def assinar(self, mensagem: bytes) -> bytes

class AssinadorHmac:                 # só biblioteca padrão
    def __init__(self, chave_caixa: bytes)
class AssinadorEd25519:              # precisa do cryptography; recebe a chave privada de 32 bytes
    def __init__(self, chave_privada: bytes)
    chave_publica: bytes             # 32 bytes, para a empresa verificar

class RegistroViagem:
    @classmethod
    def iniciar(cls, dir_viagens: Path, assinador: Assinador, info: dict | None = None,
                relogio: Relogio | None = None, fonte_relogio: Callable[[], dict] = detectar_fonte_relogio,
                fsync: Callable[[int], None] = os.fsync) -> "RegistroViagem"
    viagem_id: str; numero: int; pasta: Path; seq: int; ultimo_hash: str; falhou: bool
    def acrescentar(self, tipo: str, dados: dict) -> dict | None   # thread-safe; None se `falhou`
    def tick(self) -> None                                          # selo vencido e salto do relógio
    def fechar(self, motivo: str = "normal", detalhe: str | None = None) -> None   # fim_viagem; idempotente

def fechar_viagens_interrompidas(dir_viagens: Path, assinador: Assinador, **opcoes) -> list[str]
def registrar_ajuste_relogio(pasta: Path, assinador: Assinador, utc_caixa: str, utc_referencia: str | None,
                             origem: str = "coleta", referencia: str = "app_na_coleta") -> dict
def verificar_registro(caminho: Path, chave_caixa=None, chave_publica=None, exigir_alg=None) -> VerificacaoRegistro
def verificar_viagem(pasta: Path, chave_caixa=None, chave_publica=None, exigir_alg=None) -> VerificacaoRegistro
def derivar_chave(chave_caixa: bytes, finalidade: bytes) -> bytes   # HKDF-SHA256 (RFC 5869), também usada pela spec 002
def detectar_fonte_relogio() -> dict
```

`caixa/vision/observador_registro.py` (liga o motor ao registro):

```python
class ObservadorRegistro:
    def __init__(self, registro: RegistroViagem, modo_ativacao: Callable[[], str],
                 temperatura: Callable[[], float | None] = ler_temperatura_cpu,
                 latencia: Callable[[], dict | None] = lambda: None)
    def observar(self, frame, state) -> None        # ouvinte do DriverMonitor (driver_monitor.py:139-140)
    def tick(self, agora_mono: float | None = None) -> None   # resumo_minuto, câmera sem imagem, registro.tick()
    def iniciar_relogio(self) -> None               # thread que chama tick() a cada 1 s
    def fechar(self, motivo: str = "normal", detalhe: str | None = None) -> None   # resumo parcial + fim_viagem
```

## 10. Comportamento (Dado / Quando / Então)

| # | Dado | Quando | Então |
|---|---|---|---|
| C1 | Caixa ligada, sem viagem aberta | O monitoramento inicia | Pasta nova `<numero>-<hex>`, linha 1 `inicio_viagem` com a fonte do relógio, `boot_id` e `mono` |
| C2 | Viagem em andamento | O motor gera um evento | Linha `evento` com os mesmos dados que foram para a fila, gravada com `fsync` |
| C3 | Viagem em andamento | Passam 60 s | Linha `resumo_minuto`, mesmo se a câmera parou (`quadros: 0`, `camera_ok: false`) |
| C4 | Viagem em andamento | Passam 5 min desde o último selo | Linha `selo` assinada |
| C5 | Viagem em andamento | O motorista aperta `q`, o systemd manda SIGTERM ou dá erro | `resumo_minuto` parcial e `fim_viagem` assinado com o motivo; trava solta |
| C6 | Energia cortada no meio de uma linha | A caixa liga de novo | Linhas completas preservadas; pedaço identificado; `viagem_interrompida` assinada; viagem nova aberta |
| C7 | Caixa sem RTC e sem internet | A viagem termina e a caixa é coletada | `horario.confiavel = false`, ordem e durações certas; a coleta acrescenta `ajuste_relogio`, que só corrige a hora se a regra da §6.4 permitir |
| C8 | NTP sincroniza no meio da viagem | O relógio salta mais de 2 s | `ajuste_relogio` assinado; a verificação corrige as linhas anteriores pelo `mono` |
| C9 | Alguém edita uma linha e refaz os hashes | O importador verifica com a chave | `assinatura_invalida` no primeiro selo depois da edição, com o intervalo suspeito |
| C10 | Modo de sinais de ativação `local` | O resumo do minuto é escrito | Nenhuma métrica de ativação no registro |
| C11 | Cartão cheio | Uma escrita falha | O alarme continua; o registro para de escrever; na próxima inicialização a viagem é fechada como interrompida |
| C12 | Caixa com par Ed25519 | O importador verifica com a chave pública e `exigir_alg="ed25519"` | Íntegra; a mesma viagem reescrita com HMAC é recusada (`algoritmo_nao_aceito`) |
| C13 | Modo `registro` com consentimento | O resumo do minuto é escrito | `ativacao` no registro; nada de ativação na fila nem no estado ao vivo |

## 11. Integração prevista

- **`caixa/run_monitor.py`:**
  - Opções novas: `--registro` / `--sem-registro` (`DRIVESAFE_REGISTRO`, **ligado**) e `--viagens-dir`
    (`DRIVESAFE_VIAGENS_DIR`, padrão `<data-dir>/viagens`).
  - Chaves **provisórias até a spec 003**, que gera o par Ed25519 e a chave simétrica no pareamento:
    - chave simétrica: `obter_chave_caixa(data_dir)` lê `DRIVESAFE_CHAVE_CAIXA_ARQUIVO` ou cria
      `<data-dir>/chave_caixa_provisoria.bin` com 32 bytes aleatórios (permissão 0600) e avisa no log. Se não conseguir
      gravar, usa chave só em memória e escreve `estado_aparelho` `chave_temporaria`: a cadeia continua verificável,
      as assinaturas não;
    - assinador: `obter_assinador(data_dir, chave_caixa)` usa Ed25519 se existir chave privada em
      `DRIVESAFE_CHAVE_ASSINATURA_ARQUIVO` ou `<data-dir>/chave_assinatura_ed25519.pem` (PEM PKCS#8 ou 32 bytes
      crus); senão, HMAC com a chave simétrica. Não gera par de chaves.
  - `--sinais-ativacao registro` e `--consentimento-sinais-ativacao` (§5.1).
  - `RegistroViagem.iniciar(...)` antes de abrir a câmera; `ObservadorRegistro` entra em `monitor.listeners`;
    `iniciar_relogio()`; no `finally`, `observador.fechar(motivo)` (`desligamento` no SIGTERM, `erro` no
    `RuntimeError`, `normal` no resto).
- **`caixa/vision/driver_monitor.py`:** nenhuma mudança obrigatória. O ouvinte por quadro já existe
  (`driver_monitor.py:238-244`) e recebe `(frame, state)` depois de os eventos irem para a fila.
- **`caixa/vision/engine.py`:** só acrescentar `registro` em `ACTIVATION_MODES` e a constante com os modos que
  gravam ativação no registro (`registro`, `enviar`). O filtro dos eventos (`engine.py:223-235`) e o
  `share_activation` (`engine.py:71`) continuam valendo só para `enviar`.
- **`caixa/vision/remote_policy.py`:** nenhuma mudança; a leitura já aceita qualquer valor de `ACTIVATION_MODES` e
  troca desconhecido por `local` (`remote_policy.py:78-82`).
- **Modo teste do servidor** (`servidor/backend/test_session.py`): não cria registro. Não é viagem.
- **README:** atualizar "Onde os dados ficam" e as opções do `run_monitor.py` na implementação.

## 12. Critérios de aceite

| ID | Critério (teste em `tests/test_registro.py`) |
|---|---|
| REG-01 | A linha 1 é `inicio_viagem` com `formato`, `viagem_id`, `numero`, `relogio` {`fonte`, `detalhe`, `boot_id`, `plausivel`} e `config`; a pasta se chama `<numero com 6 dígitos>-<8 hex>`; o número cresce entre viagens e sobrevive a `contador_viagens` apagado |
| REG-02 | Toda linha tem os campos na ordem `seq, utc, mono, tipo, dados, prev, [alg, assinatura], hash`; `seq` começa em 1 sem buracos; `prev` da linha 1 = 64 zeros; `hash` confere pela regra de bytes da §4.1, recalculada no teste sem usar o código do registro |
| REG-03 | Só acréscimo: depois de novas linhas e de uma recuperação, os bytes que já estavam no arquivo continuam idênticos |
| REG-04 | `fsync` é chamado uma vez por linha, antes de `acrescentar` retornar |
| REG-05 | Cada evento de `state.events` vira uma linha `evento` com `alerta`, `nivel`, `duracao_s` e os mesmos `detalhes` que vão para a fila |
| REG-06 | `resumo_minuto` sai a cada 60 s monotônicos com os campos mínimos, inclusive sem quadros (`quadros: 0`, `camera_ok: false`), e `temperatura_cpu_c` fica `null` quando não há leitura |
| REG-07 | `calibracao` registra `inicio` e `fim` com `resultado` (`concluida`, `suspeita`, `sem_dados`) e `motivo` `recalibracao` quando o motorista recalibra |
| REG-08 | `estado_aparelho` `camera_sem_imagem` depois de 5 s sem quadro e `camera_voltou` quando a imagem volta, uma linha por mudança |
| REG-09 | `selo` assinado a cada 300 s monotônicos; `fim_viagem` assinado é a última linha e solta a trava; `derivar_chave` confere com o caso de teste 1 do RFC 5869 |
| REG-10 | Viagem intacta: `verificar_viagem` com a chave dá `integra`, `fechamento` `fim_viagem` e `resumo` com as contagens por tipo e por alerta iguais às escritas |
| REG-11 | Linha com conteúdo alterado → `alterada` na linha certa |
| REG-12 | Linha removida → `linha_faltando` na linha seguinte, com as seqs que faltam no detalhe |
| REG-13 | Duas linhas trocadas de lugar → `fora_de_ordem` |
| REG-14 | Linha editada com os hashes refeitos até o fim: sem chave, passa com `assinaturas_verificadas` falso; com chave, `assinatura_invalida` no primeiro selo depois da edição, com `desde_linha` logo depois do selo anterior |
| REG-15 | Chave HMAC errada → `assinatura_invalida` na primeira linha assinada; chave com menos de 32 bytes → `ValueError`; nem a chave da caixa, nem a derivada, nem a privada Ed25519 aparecem nos bytes do registro |
| REG-16 | Viagem sem `fim_viagem` (processo morto) → na inicialização seguinte, `viagem_interrompida` assinada; a viagem nova lista o id em `viagens_interrompidas_fechadas`; a antiga verifica `integra` com `fechamento` `viagem_interrompida` |
| REG-17 | Arquivo cortado num byte qualquer no meio de uma linha → linhas completas preservadas, pedaço identificado em `linha_truncada` {`bytes`, `sha256`} e verificação `integra` com `final_truncado` `recuperado`; linha final completa sem `\n` continua valendo; pedaço inválido no meio sem `viagem_interrompida` correspondente → `json_invalido` |
| REG-18 | Viagem com a trava tomada por outro registro aberto não é tocada pela recuperação |
| REG-19 | Falha de escrita injetada → `acrescentar` e `observar` não levantam exceção, `falhou` fica verdadeiro e nada mais é escrito; a inicialização seguinte fecha a viagem como interrompida |
| REG-20 | Nos modos `local` e `desligado`, nenhuma linha contém chaves de ativação (`PRIVATE_KEYS`, `engine.py:39-40`) nem `ativacao`; nos modos `registro` e `enviar`, o `resumo_minuto` traz `ativacao`; no `registro`, os eventos e o estado ao vivo continuam sem ativação, como no `local` |
| REG-21 | Relógio: salto de mais de 2 s entre checagens gera `ajuste_relogio` assinado; `registrar_ajuste_relogio` acrescenta em viagem já fechada sem mudar os bytes anteriores; `horario.confiavel`, `metodo` e `utc_corrigido` seguem a tabela da §6.4 nos seis casos |
| REG-22 | `mono` que regride no mesmo boot → `monotonico_regrediu`; linha depois do fechamento que não é `ajuste_relogio` → `linha_apos_fechamento` |
| REG-23 | `verificar_viagem` confere cada arquivo de `trecho_gravado` (existe e SHA-256) e acusa `pasta_nao_confere` quando o `viagem_id` não bate com a pasta |
| REG-24 | Linha de comando: registro ligado por padrão, `--sem-registro` desliga e `--viagens-dir` tem padrão `<data-dir>/viagens`. Ponta a ponta com câmera e analisador falsos: `DriverMonitor.run` gera `inicio_viagem`, `evento`, `resumo_minuto` e `fim_viagem`, e a verificação dá `integra` |
| REG-25 | Assinador trocável: toda linha assinada tem `alg`; viagem assinada com `AssinadorEd25519` verifica com a chave pública (assinaturas de 128 hex) e falha com outra chave pública; Ed25519 sem chave pública → `assinaturas_verificadas` falso e `motivo_sem_verificacao` `sem_chave_publica`; `exigir_alg="ed25519"` numa viagem HMAC → `algoritmo_nao_aceito`; `alg` desconhecido → `algoritmo_desconhecido`; a verificação de uma viagem HMAC roda num processo em que importar `cryptography` falha |

## 13. Fora de escopo

- Identidade da caixa, geração e guarda da chave, pareamento, coleta e apagar depois da coleta (spec 003).
- Importador, relatório, PDF e CSV (spec 004). Esta spec entrega só a função de verificação.
- Detecção da fonte do relógio confirmada no Pi 4, módulo DS3231, temperatura alta e estrangulamento térmico
  (spec 005).
- Consentimento de monitoramento e identificação do motorista no registro (spec 006, RF-12). O campo
  `inicio_viagem.dados.motorista` fica `null`.
- Enviar o registro ao servidor ao vivo. A fila SQLite segue igual.
- Retomar a mesma viagem depois de reinício (§7.3).
- Gerar e guardar o par Ed25519 e a chave simétrica da caixa (spec 003). Esta spec só assina com o que recebe.
- Servidor aceitar o modo `registro` e conferir o consentimento dele (spec 006, §5.1).

## 14. Riscos

| Risco | Impacto | Resposta |
|---|---|---|
| Hora errada sem RTC nem NTP | Alto: o registro é a prova principal | §6: fonte registrada, `mono` em toda linha, `ajuste_relogio`, `horario.confiavel` na verificação; RTC DS3231 recomendado pela spec 005 |
| HMAC simétrico permite forjar a quem tem a chave | Alto, se o registro for usado contra o motorista | Ed25519 em produção (§4.2) e `exigir_alg="ed25519"` no importador; HMAC só em testes e caixa sem par |
| Adulteração nos últimos minutos antes de um corte, por quem tem acesso físico ao cartão entre o corte e a religação | Médio | Selo a cada 5 min; a verificação informa as linhas sem assinatura |
| Chave provisória no mesmo cartão do registro | Médio: quem copia o cartão copia a chave | Provisório; guarda da chave é da spec 003 |
| Cartão SD corrompido | Médio | Só acréscimo, `fsync`, verificação aponta a primeira linha ruim; cartão de alta resistência (PRD §9) |
| Nome de campo ou regra mudar depois de haver registros de campo | Médio | `formato` = `"rotaguard-registro/1"` na linha 1 |

## 15. Decisões tomadas nesta spec

1. **Hash sobre os bytes gravados** (§4.1), e não sobre JSON reserializado: verificação independente de linguagem.
2. **Chaves derivadas por HKDF** (§4.2): uma para o HMAC do registro, outra para o AES dos trechos.
3. **Assinatura dentro da linha**, cobrindo `prev`, `alg` e o conteúdo, em `selo`, `ajuste_relogio`, `fim_viagem` e
   `viagem_interrompida`.
3a. **Algoritmo trocável** (ajuste aprovado): `ed25519` em produção, `hmac-sha256` em testes e sem par de chaves;
   `exigir_alg` contra a troca para o mais fraco.
4. **Pasta numerada, sem data** (§3), porque a hora pode estar errada.
5. **Recuperação sem truncar** (§7.3): o pedaço cortado fica no arquivo, identificado pelo SHA-256.
6. **Trava de arquivo** para a recuperação não fechar viagem de outro processo vivo.
7. **Não retomar viagem** depois de reinício: fecha como interrompida e abre outra.
8. **Linha `recorrencia`** (definida na spec 002) entra no registro no instante do gatilho, antes do vídeo: um corte
   de energia pode perder o trecho, mas não o fato.
9. **Ativação no registro só nos modos `registro` e `enviar`**, os dois com consentimento (§5.1; D1 da spec 002).
10. **Registro só com biblioteca padrão** para HMAC, para o importador verificar sem OpenCV, MediaPipe nem
    `cryptography`; o `cryptography` só é importado para linhas `ed25519`.
