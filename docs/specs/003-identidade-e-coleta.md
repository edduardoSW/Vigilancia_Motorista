# Spec 003 · Identidade da caixa e coleta na chegada

| Campo | Valor |
|---|---|
| Status | **rascunho** |
| Cobre | RF-08, RF-09 e RNF-06 do PRD 1.0; pergunta Q3 (padrão: rede pelo USB-C do Pi 4 ou do escritório **e** pen drive); parte do O3 (tempo até o relatório) |
| Depende de | spec 001 (pasta da viagem, `fechar_viagens_interrompidas`, `verificar_registro`, `verificar_viagem`, `registrar_ajuste_relogio`, `derivar_chave`), spec 002 (`trechos/*.enc`), spec 005 (bipes, subtensão, pausa do monitor, RTC) |
| Usada por | specs 001 e 002 (chave da caixa e par Ed25519), spec 004 (pasta coletada, manifesto, medida do relógio, chaves), spec 007 (app: descoberta e chaveiro) |
| Código previsto | `caixa/coleta/` (identidade, protocolo, serviço, manifesto, diário, anúncio, exportação, cliente), `caixa/run_coleta.py`, `ferramentas/coletar_caixa.py`, `servidor/backend/identidade_caixa.py`, `servidor/manage.py`, `servidor/backend/database.py`, `implantacao/raspberry-pi/` |
| Testes previstos | `tests/test_identidade_coleta.py` |

## 1. Contexto e vínculo com o PRD

- Matheus, 11/09/2026: "A empresa, quando o motorista chegar, deve recolher o equipamento e, ao conectar, o sistema
  deve reconhecer o equipamento e gerar o relatório."
- PRD:
  - RF-08: ID único e chave própria, pareada com uma empresa. Hoje só existe token de dispositivo no servidor.
  - RF-09: coleta ao conectar, pelo cabo USB-C do Pi 4 como rede, pela rede do escritório ou por pen drive; manifesto
    assinado; marca a viagem como coletada e só apaga depois da confirmação do app.
  - RNF-06: nenhuma porta aberta sem autenticação; nada trafega sem autenticação e integridade.
- **Hoje:**
  - O dispositivo se autentica no servidor com token Bearer `dsk_...`, e o banco guarda só o hash
    (`servidor/backend/security.py:28-31`, `servidor/backend/routes/device_api.py:29-38`).
  - Não há identidade na caixa nem coleta local. Tudo depende do envio ao vivo (`caixa/vision/sync.py`), que continua
    opcional (RF-11).
- **Specs 001 e 002 (aprovadas):** recebem uma chave da caixa **injetada** e derivam dela, por HKDF-SHA256, a chave do
  HMAC do registro e a do AES-GCM dos trechos (spec 001 §4.2; spec 002 §7.2).
- **Coordenador, 11/09:** recomendação aceita de gerar também um **par Ed25519** da caixa. A chave privada assina o
  registro em produção (`alg=ed25519`). Esta spec define onde as chaves ficam, as permissões, a rotação, a revogação e
  como o app obtém o que precisa para verificar e decifrar.
- Para esta spec **a viagem é uma pasta opaca**. A coleta não lê o formato do registro: usa as funções públicas da
  spec 001.

## 2. Termos

| Termo | Significado |
|---|---|
| Chave da caixa | 32 bytes, simétrica. É a "chave da caixa" das specs 001 e 002 |
| Par Ed25519 | Par de assinatura gerado **na caixa**. A semente (chave privada) nunca sai dela |
| `kid` | 16 primeiros caracteres hex do SHA-256 da chave pública Ed25519 |
| Raiz de pareamento | 32 bytes guardados no servidor, fora do banco. Deles saem as chaves das caixas |
| Chave de coleta | Subchave da chave da caixa, usada só no protocolo de coleta, no manifesto e no pedido e recibo do pen drive |
| Chaveiro de coleta | Arquivo com as chaves de coleta e as chaves públicas das caixas de uma empresa, para o computador que coleta |
| Geração | Número da chave de uma caixa; sobe a cada troca de chave |
| App | Quem coleta: hoje o `ferramentas/coletar_caixa.py`; depois o app instalável (spec 007), com o mesmo protocolo |
| Coletada | Viagem cujo manifesto o app conferiu e confirmou |
| Diário da coleta | `<data-dir>/coleta/diario.jsonl`: fatos da coleta, só por acréscimo |

## 3. Visão geral

```
PAREAMENTO (técnico, uma vez por caixa)
  servidor: manage.py parear-caixa ──> pareamento.json (id, geração, chave da caixa)
  caixa:    run_coleta.py identidade instalar ──> gera o par Ed25519 ──> chave-publica.json (assinado pela caixa)
  servidor: manage.py registrar-chave-publica      manage.py chaveiro-coleta ──> chaveiro.json (computador de coleta)

CHEGADA, PELA REDE (cabo USB-C no computador, ou rede do escritório)
  app  ── descobre (mDNS ou IP fixo) ──> desafio-resposta nos dois sentidos ──> mede o relógio
  caixa ── fecha viagens interrompidas; acrescenta ajuste_relogio em cada viagem não coletada
  app  ── lista ──> manifesto assinado ──> baixa ──> confere hashes e verificar_viagem ──> confirma
  caixa ── marca coletada ──> apaga só depois da retenção, de pedido explícito ou por falta de espaço

CHEGADA, POR PEN DRIVE (alternativa)
  app  ── prepara pedido assinado no pen drive
  caixa ── confere o pedido ──> exporta com manifesto ──> 2 bipes
  app  ── importa e confere ──> escreve recibos ──> caixa, na próxima inserção, marca coletadas
```

## 4. Chaves

### 4.1 O que existe, onde fica e quem tem

| Material | Onde fica | Quem tem | Para quê |
|---|---|---|---|
| Raiz de pareamento | Servidor: arquivo `DRIVESAFE_RAIZ_CAIXAS_ARQUIVO` (padrão `data/raiz-caixas.key`), 0600, **fora do banco** | Servidor | Derivar a chave de cada caixa |
| Chave da caixa | Caixa: `<data-dir>/identidade/caixa.json`. Servidor: não guarda, deriva quando precisa | Caixa, servidor | Specs 001 e 002 derivam as delas; esta spec deriva a de coleta |
| Semente Ed25519 | Caixa: `identidade/caixa.json` | **Só a caixa** | Assinar o registro em produção (spec 001, `alg=ed25519`) |
| Chave pública Ed25519 | Caixa, servidor (tabela nova), chaveiro, pasta coletada | Qualquer verificador | Verificar o registro |
| Chave de coleta | Caixa (derivada na hora), chaveiro | Caixa, computador de coleta | Protocolo, manifesto, pedido e recibo |
| Chave do registro (HMAC) | Derivada (spec 001 §4.2) | Caixa, servidor | Verificar o HMAC do registro, só no servidor (spec 004) |
| Chave dos trechos (AES) | Derivada (spec 002 §7.2) | Caixa, servidor | Decifrar trechos, só para gestor e admin, com auditoria (spec 004) |

**Mínimo privilégio:** o computador de coleta recebe só a chave de coleta. Pelo HKDF, ela não leva às chaves do registro
nem dos trechos. Quem opera a coleta baixa trechos cifrados e não consegue abri-los.

### 4.2 Derivações

HKDF-SHA256 do RFC 5869, sal vazio, 32 bytes: a mesma `derivar_chave` da spec 001 §4.2.

| Chave | Chave de entrada | `info` |
|---|---|---|
| Chave da caixa | Raiz de pareamento | `"rotaguard/caixa/v1\n" + id_caixa + "\n" + geracao` |
| Chave de coleta | Chave da caixa | `"rotaguard/coleta/hmac/v1"` |
| Chave do MAC da chave pública | Chave da caixa | `"rotaguard/chave-publica/hmac/v1"` |
| Registro e trechos | Chave da caixa | Specs 001 §4.2 e 002 §7.2 |

- **Impressão digital** para mostrar ao técnico: 16 primeiros hex de `SHA-256("rotaguard/impressao/v1\n" + chave da caixa)`.
  Não permite recuperar a chave.
- **Por que derivar da raiz em vez de sortear e guardar no banco:**
  - backup ou vazamento do banco não entrega nenhuma chave;
  - o servidor não precisa de biblioteca nova (só `hmac` e `hashlib`).
  - Custo: a raiz vira o segredo mais importante do servidor. Perdê-la impede decifrar trechos e verificar o HMAC de
    viagens; o backup dela fica separado do banco (§16).

### 4.3 Arquivos

`pareamento.json`: sai do servidor e entra na caixa. Apagar depois de instalar.

```json
{"formato":"rotaguard-pareamento/1","id_caixa":"rg-abcdefghijkl","geracao":1,"chave_caixa":"<base64>",
 "empresa_id":1,"dispositivo_id":3,"criado_em":"2026-09-11T15:00:00.000Z"}
```

`<data-dir>/identidade/caixa.json`: pasta 0700, arquivo 0600, dono `drivesafe`.

```json
{"formato":"rotaguard-identidade/1","id_caixa":"rg-abcdefghijkl","geracao":1,"chave_caixa":"<base64>",
 "ed25519":{"semente":"<base64>","publica":"<base64>","kid":"<16 hex>"},
 "empresa_id":1,"dispositivo_id":3,"instalada_em":"2026-09-11T15:10:00.000Z"}
```

`<data-dir>/identidade/chave-publica.json`: público, assinado pela caixa com a chave do MAC da chave pública (regra de
bytes da §7.2, rótulo `rotaguard/chave-publica/v1`). O computador de coleta não tem essa chave e não consegue forjar o
arquivo.

```json
{"formato":"rotaguard-chave-publica/1","id_caixa":"rg-abcdefghijkl","geracao":1,"alg":"ed25519",
 "publica":"<base64>","kid":"<16 hex>","criada_em":"2026-09-11T15:10:00.000Z","assinatura":"<64 hex>"}
```

`chaveiro.json`: computador de coleta, 0600 (no Windows, dentro da pasta do usuário).

```json
{"formato":"rotaguard-chaveiro-coleta/1","empresa_id":1,"gerado_em":"2026-09-11T15:20:00.000Z",
 "caixas":[{"id_caixa":"rg-abcdefghijkl","dispositivo_id":3,"nome":"Caminhão ABC-1234","geracao_atual":1,
            "chaves_coleta":{"1":"<base64>"},
            "chaves_publicas":[{"geracao":1,"kid":"<16 hex>","publica":"<base64>"}],
            "revogada_em":null}]}
```

- `id_caixa`: `rg-` + 12 caracteres de base32 minúsculo (`a-z`, `2-7`), sorteados; único no banco.
- Servidor, tabela `devices`: colunas novas `box_id` (única), `box_generation`, `box_paired_at`, `box_revoked_at`.
- Servidor, tabela nova `box_signing_keys`: `device_id`, `box_id`, `generation`, `kid` (único), `public_key`,
  `registered_at`, `replaced_at`.
- O banco não tem coluna para chave secreta nenhuma.

### 4.4 Permissões

- **POSIX:**
  - Pasta `identidade/` 0700; arquivos com segredo 0600, criados com `os.open(..., 0o600)`.
  - Gravação atômica: temporário na mesma pasta, `fsync`, `os.replace`, `fsync` da pasta.
- **Ao carregar:** permissão aberta a grupo ou outros é corrigida para 0600 com aviso. Se não der para corrigir, a
  identidade é recusada.
- **Windows** (desenvolvimento e computador de coleta): o limite é a pasta do usuário; a checagem de modo não se aplica.
- **Usuário:** monitor e serviço de coleta rodam com o mesmo usuário `drivesafe`. Os dois precisam assinar (o registro e
  o `ajuste_relogio`).

### 4.5 Rotação e revogação

| Situação | O que fazer | Efeito |
|---|---|---|
| Suspeita de vazamento, cartão clonado ou trocado | Coletar tudo; `manage.py parear-caixa --dispositivo ID --nova-geracao`; na caixa, `identidade instalar ... --substituir` | Geração sobe. Chave da caixa, chave de coleta e par Ed25519 novos. A caixa apaga a identidade anterior. As chaves públicas antigas continuam no servidor para verificar viagens antigas (o registro diz o `kid`) |
| Caixa roubada ou perdida | `manage.py revogar-dispositivo ID` (já existe, `servidor/manage.py:193-197`) | Revoga o token e a identidade. O chaveiro passa a trazer `revogada_em`. O cliente recusa a caixa sem `--aceitar-revogada`. O relatório (spec 004) marca as viagens dessa caixa |
| Caixa muda de empresa | Coletar tudo; revogar; `vincular-dispositivo` e `parear-caixa --nova-geracao` na empresa nova | O chaveiro da empresa antiga não traz mais a caixa |
| Chaveiro de coleta perdido | Nova geração nas caixas daquela empresa | Não há rotação só da chave de coleta nesta versão (§15) |

- Apagar a identidade antiga no cartão SD não garante que os bytes somem (memória flash). Por isso a rotação troca
  **todas** as chaves.
- Troca de chave com viagem aberta não é suportada: o técnico coleta antes (o registro guarda a chave na abertura).

### 4.6 Como o app obtém o que precisa

| Precisa | Material | Hoje (esta spec) | Depois (specs 004 e 007) |
|---|---|---|---|
| Coletar: autenticar, conferir manifesto, pedido e recibo | Chave de coleta | `manage.py chaveiro-coleta`, auditado | Rota autenticada do servidor para gestor e admin, com auditoria; guardada no cofre do sistema do app |
| Verificar a assinatura Ed25519 do registro | Chave pública pelo `kid` | Chaveiro e `chave-publica.json` na pasta coletada | Servidor |
| Verificar o HMAC do registro (fase atual da spec 001) | Chave do registro | Só o servidor deriva | Importador no servidor |
| Decifrar trechos | Chave dos trechos | Só o servidor deriva | Servidor decifra para gestor e admin, com auditoria (Q4); ou o esquema da pergunta P2 |
| Registrar a chave pública de uma caixa | `chave-publica.json` assinado pela caixa | `manage.py registrar-chave-publica` | O app envia ao servidor o arquivo que recebeu na coleta; o servidor confere a assinatura |

**Recomendação para os trechos (pergunta P2, muda a spec 002):**
- O que mudaria: cifrar a chave de cada trecho para uma chave pública X25519 da empresa (troca efêmera X25519 + HKDF +
  AES-GCM, como o HPKE), em vez de derivá-la da chave da caixa.
- Justificativa:
  - A caixa é o equipamento mais exposto a roubo. Hoje a chave da caixa e os trechos ficam no **mesmo cartão**: quem
    leva o cartão abre os trechos ainda não coletados.
  - Com a chave pública, a caixa não consegue abrir nem os próprios trechos depois de gravados. Só quem tem a chave
    privada da empresa abre.
  - O servidor também deixa de precisar da chave da caixa para abrir trechos.
- Custo: guardar e distribuir a chave privada da empresa (specs 004 e 007). O arquivo de pareamento ganharia o campo
  `chave_publica_trechos`.
- Até a decisão, vale o que a spec 002 aprovou.

## 5. Comportamento (Dado / Quando / Então)

| # | Dado | Quando | Então |
|---|---|---|---|
| C1 | Dispositivo cadastrado no servidor | O técnico roda `parear-caixa` | `id_caixa` novo, geração 1 e `pareamento.json`; na tela, só ID, geração e impressão digital |
| C2 | `pareamento.json` no Pi | `identidade instalar` | Identidade gravada com permissão restrita; par Ed25519 gerado na caixa; `chave-publica.json` pronto para o servidor |
| C3 | Caixa pareada; cabo USB-C no computador | O Pi liga pelo cabo e o link sobe | Serviço só no `usb0` (`10.211.77.1:8470`), anunciado como `_rotaguard._tcp`; sem autenticação, só o desafio responde |
| C4 | App com o chaveiro da empresa | Conecta | Desafio-resposta nos dois sentidos; mede o relógio; a caixa acrescenta `ajuste_relogio` nas viagens; o app baixa, confere e confirma |
| C5 | Caixa de outra empresa ou falsa | App tenta coletar | Sem chave no chaveiro, não autentica; com prova da caixa errada, o app aborta |
| C6 | Arquivo diferente do manifesto | App confere o hash | Não confirma; a caixa não marca coletada; nova execução refaz |
| C7 | Viagem aberta pelo monitor (trava tomada) | App lista | Aparece como `em_andamento` e não é baixada |
| C8 | Viagem coletada há 30 dias | App conecta de novo | A caixa apaga a pasta e registra no diário |
| C9 | Sem rede para a caixa | Pen drive com pedido assinado inserido na caixa | Exporta com manifesto e dá 2 bipes; no escritório o app importa, confere e escreve recibos; na próxima inserção a caixa marca coletadas |
| C10 | Pen drive qualquer, sem pedido | Inserido na caixa | Nada é escrito nem copiado |
| C11 | Caixa roubada | Empresa revoga | Chaveiro marca revogada; o cliente recusa sem opção explícita |
| C12 | Cabeçote multimídia do veículo com USB de dados | Enumera o gadget | Sem chave, nada é entregue; o monitor não pausa (só pausa com sessão autenticada, §6.9) |

## 6. Protocolo de coleta, versão 1

### 6.1 Transporte e descoberta

- **HTTP/1.1 sem TLS**, ligado só ao IPv4 da interface de coleta, **nunca em `0.0.0.0`**. Porta `8470`
  (`DRIVESAFE_COLETA_PORTA`).
- **Interfaces:**
  - `DRIVESAFE_COLETA_INTERFACES`, padrão `usb0`;
  - `DRIVESAFE_COLETA_REDES` (redes permitidas), padrão `10.211.77.0/29`;
  - rede do escritório: acrescentar `eth0` ou `wlan0` e a sub-rede do escritório.
- **Link USB:** caixa em `10.211.77.1/29`. O computador recebe `10.211.77.2` a `.6` por DHCP servido só no `usb0`,
  **sem gateway e sem DNS**, para o computador não passar a navegar pela caixa.
- **mDNS/DNS-SD:** tipo `_rotaguard._tcp.local.`, instância `<id_caixa>`, TXT `id=<id_caixa>` e `v=1`. Publicado só no
  IP da interface ativa, com `zeroconf`.
- **Vigia da conexão:** a cada 2 s confere link, IP e rede permitida de cada interface; sobe e derruba servidor e
  anúncio.
- **Confidencialidade:** autenticação e integridade em tudo, mas o conteúdo **não é cifrado no transporte** nesta
  versão. Os trechos já chegam cifrados (spec 002); o registro vai em claro. Ver pergunta P1.

### 6.2 Codificação

- Nonces, provas, MACs e sessão: base64url sem `=`.
- Hashes e assinaturas dentro de arquivos: hex minúsculo.
- Horários: ISO 8601 em UTC com milissegundos e `Z`.
- Textos assinados: UTF-8, partes separadas por `\n`. `id_caixa`, nonces e sessão não contêm `\n`.
- Todos os MACs e provas: HMAC-SHA256.

### 6.3 Autenticação: desafio-resposta nos dois sentidos

1. `POST /v1/desafio` com `{"nonce_app": "<32 bytes>"}`. Resposta:
   `{"protocolo":"rotaguard-coleta","versao":1,"id_caixa","geracao","nonce_caixa":"<32 bytes>","prova_caixa","relogio"}`.
   - `prova_caixa = HMAC(chave_coleta, "rotaguard/coleta/v1\nprova-caixa\n" + id_caixa + "\n" + nonce_app + "\n" + nonce_caixa)`
2. O app confere `prova_caixa` com a chave de coleta daquela caixa e geração. Se não confere, **aborta**: caixa falsa ou
   chave errada.
3. `POST /v1/sessao` com `{"nonce_app","nonce_caixa","prova_app"}`. Resposta: `{"sessao":"<16 bytes>","ociosidade_max_s":600}`.
   - `prova_app = HMAC(chave_coleta, "rotaguard/coleta/v1\nprova-app\n" + id_caixa + "\n" + nonce_caixa + "\n" + nonce_app)`
   - `nonce_caixa`: uso único, vale 60 s, no máximo 32 pendentes (sai o mais antigo).
4. `chave_sessao = HMAC(chave_coleta, "rotaguard/coleta/v1\nsessao\n" + id_caixa + "\n" + nonce_app + "\n" + nonce_caixa)`

A prova da caixa cobre um nonce sorteado por ela: a rota aberta não assina texto escolhido por quem pergunta.

### 6.4 Requisições autenticadas

- **Cabeçalhos da requisição:**
  - `X-RotaGuard-Sessao`;
  - `X-RotaGuard-Seq`: inteiro, começa em 1 e só cresce;
  - `X-RotaGuard-Mac = HMAC(chave_sessao, "rotaguard/coleta/v1\nrequisicao\n" + sessao + "\n" + seq + "\n" + METODO + "\n" + alvo + "\n" + sha256hex(corpo))`,
    em que `alvo` é o caminho com a query exatamente como foi enviado.
- **Resposta:** `X-RotaGuard-Mac = HMAC(chave_sessao, "rotaguard/coleta/v1\nresposta\n" + sessao + "\n" + seq + "\n" + status + "\n" + sha256hex(corpo))`.
  - Arquivo servido em fluxo: `sha256hex(corpo)` é o do manifesto, repetido em `X-RotaGuard-Sha256`. Se o arquivo
    mudou no disco, o hash do cliente não bate e ele não confirma.
- MAC errado, `seq` repetida ou menor, sessão desconhecida ou ociosa por mais de 600 s: **401**.

### 6.5 Rotas

| Rota | Autenticação | Corpo | Resposta |
|---|---|---|---|
| `POST /v1/desafio` | não | `nonce_app` | §6.3 |
| `POST /v1/sessao` | não | `nonce_app`, `nonce_caixa`, `prova_app` | `sessao` |
| `GET /v1/identidade` | sim | — | `id_caixa`, `geracao`, `kid` e `chave_publica` (texto exato do `chave-publica.json`) |
| `POST /v1/relogio` | sim | `utc_app`, `rtt_ms` | §6.7 |
| `GET /v1/viagens` (`?incluir_coletadas=1`) | sim | — | §6.6 |
| `GET /v1/viagens/{id}/manifesto` | sim, com relógio já medido na sessão | — | Bytes do manifesto (§7) |
| `GET /v1/viagens/{id}/arquivos/{caminho}` | sim | — | Bytes do arquivo |
| `POST /v1/viagens/{id}/confirmacao` | sim | `hash_manifesto`, `utc_app` | `{"coletada":true}` |
| `DELETE /v1/viagens/{id}` | sim | `hash_manifesto` | `{"apagada":true}` |
| `POST /v1/sessao/encerrar` | sim | — | 204 |

Erros, com corpo `{"erro":"<código>"}`. Sem autenticação o corpo é sempre `{"erro":"nao_autenticado"}`, inclusive em
rota que não existe.

| HTTP | Código |
|---|---|
| 401 | `nao_autenticado` |
| 404 | `nao_encontrado` (só depois de autenticado) |
| 409 | `em_andamento`, `relogio_pendente`, `manifesto_mudou`, `nao_coletada` |
| 411, 413 | `tamanho` (POST sem `Content-Length` ou corpo acima de 64 KB) |
| 429 | `muitas_tentativas` (5 provas erradas do mesmo IP em 10 min bloqueiam por 60 s) |

### 6.6 Lista de viagens

- **Pasta:** `DRIVESAFE_VIAGENS_DIR`, padrão `<data-dir>/viagens` (spec 001 §3). Só entram subpastas com nome
  `^[0-9]{6,}-[0-9a-f]{8}$`.
- **Antes de listar:** o serviço chama `fechar_viagens_interrompidas(dir_viagens, chave_caixa)` (spec 001 §7.3). Uma
  viagem cortada pela energia sai fechada mesmo quando o monitor não subiu (câmera quebrada, por exemplo).
- **Estado:**
  - `em_andamento`: trava `registro.trava` tomada por outro processo;
  - senão, pelo `fechamento` de `verificar_registro(pasta/registro.jsonl)` sem chave (spec 001 §8.1): `fim_viagem` →
    `fechada`, `viagem_interrompida` → `interrompida`, `aberta` → `aberta_sem_fechamento` (baixável, sinalizada).
- **Item:** `{"id_viagem","estado","coletada","arquivos","total_bytes","hash_manifesto"}` (hash só se já houve manifesto).
- Por padrão só as não coletadas; `?incluir_coletadas=1` inclui as coletadas ainda guardadas. A resposta traz `relogio`.

### 6.7 Relógio

- Desafio, lista e todo manifesto trazem `relogio = {"utc","monotonico_ms","boot_id"}`
  (`boot_id` por `current_boot_id`, `caixa/vision/event_queue.py:19-25`).
- `POST /v1/relogio` com `{"utc_app": <hora do app ao enviar>, "rtt_ms": <ida e volta medida na requisição anterior>}`:
  1. `utc_caixa` = hora da caixa ao receber; `utc_referencia = utc_app + rtt_ms / 2`.
  2. Para cada viagem **não coletada e com a trava livre**:
     `registrar_ajuste_relogio(pasta, chave_caixa, utc_caixa, utc_referencia, origem="coleta", referencia="app_na_coleta")`
     (spec 001 §6.3 e §9).
  3. Só depois disso a sessão pode pedir manifesto. Manifesto antes: 409 `relogio_pendente`.
  4. Diário: `relogio_medido`, com `utc_app`, `utc_caixa` e `deslocamento_ms`.
  5. Opcional: com `DRIVESAFE_COLETA_AJUSTAR_RELOGIO=1` e deslocamento acima de 2 s, a caixa acerta o relógio do
     sistema (e o RTC, se houver) **depois** do passo 2.

     > [!note] Hipótese, confirmar
     > Acertar o relógio exige permissão (regra do polkit para `timedatectl set-time`). Só com o Pi em mãos.
- **Resposta:** `{"relogio":{...},"deslocamento_ms": utc_referencia − utc_caixa,"incerteza_ms": rtt_ms/2 + 1,"viagens_ajustadas":[...]}`.
  O sinal é o mesmo do `deslocamento_s` da spec 001 §6.3: **hora do app menos hora da caixa**.
- Viagem com a trava tomada não recebe o ajuste: só o monitor escreve nela.
- **Limite sem RTC:** o ajuste não corrige viagens de boots anteriores (spec 001 §6.4, casos 5 e 6). A caixa desliga
  entre a viagem e a coleta, e o tempo desligado se perde. Por isso o **RTC DS3231 entra como requisito de hardware**
  (spec 005 §3).
- No pen drive não há medida de relógio (§8).

### 6.8 Confirmação, diário e retenção

- **Confirmação:** `POST /v1/viagens/{id}/confirmacao` com `hash_manifesto` = SHA-256 dos bytes recebidos.
  - Igual ao manifesto atual: grava `coletada` no diário e responde.
  - Diferente: 409 `manifesto_mudou`, sem marcar.
  - Repetida: mesma resposta, sem linha nova.
  - Nada é apagado nesse momento.
- **Diário** `<data-dir>/coleta/diario.jsonl`:
  - só acréscimo, uma linha JSON por fato, com `fsync`;
  - tipos: `relogio_medido`, `coletada`, `exportada`, `pedido_usado`, `apagada`;
  - campos comuns: `tipo`, `utc_caixa`, `monotonico_ms`, `boot_id`; e os do tipo (`id_viagem`, `hash_manifesto`,
    `utc_app`, `origem` = `rede` ou `pen_drive`, `motivo`).
- **A caixa apaga a pasta de uma viagem coletada só quando:**
  1. um app autenticado informa hora (`/v1/relogio`, confirmação ou recibo) igual ou maior que o `utc_app` da
     confirmação mais `DRIVESAFE_COLETA_RETENCAO_DIAS` (padrão 30, Q4);
  2. `DELETE /v1/viagens/{id}` autenticado traz o `hash_manifesto` confirmado;
  3. o espaço livre do disco fica abaixo de 500 MiB: apaga as coletadas mais antigas até sair da faixa.

     > [!note] Hipótese, confirmar
     > 500 MiB = reserva de 200 MiB da spec 002 mais margem para o sistema. Ajustar com o cartão real.
- **Nunca apaga:** viagem não coletada; viagem com a trava tomada; nem conta prazo pelo relógio da caixa (sem RTC ele
  para quando a caixa desliga e salta depois de um corte).

### 6.9 Coleta ativa: sinal para o monitor

- Enquanto houver sessão autenticada que chegou pela interface USB, o serviço mantém `<data-dir>/coleta/coleta-ativa`
  com `{"boot_id","monotonico_ms"}`.
- O arquivo é renovado a cada 30 s e apagado 120 s depois da última requisição, ou quando o link cai.
- Arquivo de outro boot, ou com mais de 120 s, vale como inativo (corte de energia não deixa o sinal preso).
- Só sessão **autenticada** liga o sinal: um cabeçote multimídia que enumere o USB não pausa o monitoramento.
- O uso pelo monitor é da spec 005 (PI4-17).

## 7. Manifesto

### 7.1 Conteúdo, com os campos nesta ordem

| Campo | Conteúdo |
|---|---|
| `formato` | `"rotaguard-manifesto/1"` |
| `id_caixa`, `geracao`, `kid` | Identidade atual da caixa |
| `id_viagem` | Nome da pasta |
| `estado` | §6.6 |
| `relogio` | `{utc, monotonico_ms, boot_id}` no momento em que o manifesto foi gerado |
| `arquivos` | `[{caminho, tamanho, sha256}]`, ordenados pelos bytes UTF-8 do caminho |
| `ignorados` | `[{caminho, motivo}]`, motivo `nome_invalido`, `link_simbolico` ou `tipo_especial` |
| `total_bytes` | Soma dos tamanhos |
| `assinatura` | §7.2 |

- **Caminhos:** relativos à pasta da viagem, separador `/`, até 4 níveis; cada parte casa
  `^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$`.
- **Ficam fora sem aparecer em `ignorados`:** `registro.trava` (trava da spec 001) e nomes terminados em `.parcial`
  (gravação em andamento da spec 002).
- **Só inteiros, textos e booleanos**, sem número com casa decimal.
- **Cache** em `<data-dir>/coleta/manifestos/<id_viagem>.json`, com caminho, tamanho e `mtime` de cada arquivo:
  - enquanto nada muda, o mesmo manifesto (mesmos bytes) é servido de novo;
  - qualquer mudança, inclusive um `ajuste_relogio` novo, gera manifesto novo, e a confirmação do antigo recebe 409.

### 7.2 Assinatura sobre os bytes (mesma regra da spec 001 §4.1 e §4.2)

1. `B` = bytes do manifesto, terminados em `,"assinatura":"` + 64 hex + `"}`.
2. `corpo` = `B` sem esse sufixo, mais `}`.
3. `assinatura = HMAC-SHA256(chave_coleta, "rotaguard/manifesto/v1\n" + corpo)`.
4. `hash_manifesto = SHA-256(B)`.

- A verificação não reserializa JSON: funciona igual em Python, JavaScript ou Rust.
- A mesma regra vale para `chave-publica.json` (rótulo `rotaguard/chave-publica/v1`), pedido
  (`rotaguard/pedido-exportacao/v1`) e recibo (`rotaguard/recibo-coleta/v1`) do pen drive.

## 8. Pen drive

```
<mídia>/RotaGuard/
  pedidos/<id_caixa>.json                      escrito pelo app
  recibos/<id_caixa>/<id_viagem>.json          escrito pelo app
  <id_caixa>/
    chave-publica.json                         escrito pela caixa
    <id_viagem>/...                            cópia exata da pasta da viagem
    <id_viagem>.coleta/manifesto.json
    exportacao.json                            escrito por último pela caixa: marca o fim
```

| Arquivo | Conteúdo | Rótulo da assinatura (chave de coleta) |
|---|---|---|
| Pedido | `{"formato":"rotaguard-pedido-exportacao/1","id_caixa","nonce","utc_app","assinatura"}` | `rotaguard/pedido-exportacao/v1` |
| Recibo | `{"formato":"rotaguard-recibo-coleta/1","id_caixa","id_viagem","hash_manifesto","utc_app","assinatura"}` | `rotaguard/recibo-coleta/v1` |
| `exportacao.json` | `{"formato":"rotaguard-exportacao/1","id_caixa","geracao","kid","relogio","viagens":[{id_viagem, hash_manifesto}],"relogio_medido":false}` | não assinado (cada manifesto já é) |

- **Automático:**
  - A caixa procura `RotaGuard/pedidos/<id_caixa>.json` a cada 5 s nas mídias montadas sob `DRIVESAFE_COLETA_MIDIAS`
    (padrão `/media`, até 2 níveis).
  - Pedido com assinatura válida e `nonce` nunca usado: processa os recibos, exporta, grava `exportacao.json`, faz
    `sync` e dá **2 bipes curtos**. Erro: **1 bipe longo**.
  - O `nonce` vai para o diário (`pedido_usado`) e não vale de novo.
  - Sem pedido válido, **não escreve nem copia nada**.
- **Comando local** `run_coleta.py exportar --destino DIR`: para o técnico com acesso ao terminal da caixa. Não exige
  pedido, porque quem tem o terminal já tem os arquivos. Também processa recibos.
- Exportar **não marca coletada**; só o recibo marca.
- Não há medida de relógio: `relogio_medido: false`.

> [!note] Hipótese, confirmar
> Montagem automática de pen drive no Raspberry Pi OS Lite (regra do udev com `systemd-mount`) e a latência de
> `sync` num pen drive barato. Só com o Pi em mãos.

## 9. Cliente de coleta

### 9.1 Descoberta

- Junta, sem repetir `id_caixa`:
  - caixas anunciadas por mDNS (espera padrão 3 s);
  - o IP fixo do link USB (`10.211.77.1:8470`);
  - endereços passados à mão.
- Sem `zeroconf` instalado, usa só o IP fixo e os endereços.

### 9.2 Coleta, passo a passo

1. Desafio; confere `prova_caixa` (§6.3). Caixa ausente do chaveiro, revogada (sem `--aceitar-revogada`) ou com prova
   errada: para aquela caixa.
2. Sessão; `GET /v1/identidade` e guarda `chave-publica.json`.
3. `POST /v1/relogio` com o `rtt_ms` medido na sessão.
4. Lista. Para cada viagem que não está `em_andamento`:
   1. manifesto: confere a assinatura, `id_caixa` e `id_viagem`;
   2. se `<destino>/<id_caixa>/<id_viagem>/` já existe e confere com o manifesto, não baixa de novo;
   3. senão, baixa cada arquivo para `<id_viagem>.parcial/`, conferindo tamanho e SHA-256 em fluxo;
   4. roda `verificar_viagem(pasta)` da spec 001 **sem chave** (cadeia, fechamento e SHA-256 dos trechos) e guarda o
      resultado;
   5. renomeia `.parcial` para a pasta final e grava a pasta `.coleta`;
   6. **só então** confirma.
5. Hash errado: não confirma e relata falha. A próxima execução apaga a `.parcial` e refaz.
6. Registro com problema na verificação **ainda é confirmado**. Confirmar quer dizer "recebi exatamente o que a caixa
   tem"; o problema vai para o relatório (spec 004) e a prova da adulteração fica guardada na cópia da empresa.

### 9.3 Pasta de destino

```
<destino>/<id_caixa>/
  <id_viagem>/                 cópia exata; verificar_viagem roda aqui (a spec 001 compara o nome da pasta)
  <id_viagem>.coleta/
    manifesto.json             bytes recebidos
    relogio.json
    chave-publica.json
    verificacao.json           resultado de verificar_viagem, sem chave
```

`relogio.json`, entregue ao importador (spec 004):

```json
{"formato":"rotaguard-medicao-relogio/1","id_caixa":"rg-abcdefghijkl",
 "caixa":{"utc":"2026-09-11T08:00:00.000Z","monotonico_ms":41234,"boot_id":"..."},
 "app":{"utc_envio":"2026-09-11T18:00:00.000Z","utc_recebimento":"2026-09-11T18:00:00.004Z","rtt_ms":4},
 "deslocamento_ms":36000002,"incerteza_ms":3,"ajuste_registrado_na_viagem":true}
```

- `deslocamento_ms` = hora do app − hora da caixa.
- O importador aplica a tabela da spec 001 §6.4. `ajuste_registrado_na_viagem` diz se a linha `ajuste_relogio` entrou
  no registro (falso em viagem com a trava tomada e em pen drive).

### 9.4 Resumo para o app

O comando imprime um JSON: `{"caixas":[{"id_caixa","coletadas":[...],"ja_coletadas":[...],"falhas":[{"id_viagem","motivo"}],"relogio":{...}}]}`.
Saída 0 com tudo certo, 1 com alguma falha, 2 com erro de uso ou de chaveiro.

## 10. Implantação no Raspberry Pi 4

> [!note] Hipótese, confirmar
> Tudo desta seção foi escrito pela documentação, sem Pi 4 em mãos.

- **Modo gadget:** `dtoverlay=dwc2,dr_mode=peripheral` no `config.txt` e módulo `libcomposite`.
- **Script** `implantacao/raspberry-pi/usb-gadget-rotaguard.sh`, pelo configfs:
  - função ECM (Linux e macOS) e RNDIS com descritor de sistema da Microsoft (Windows);
  - endereços MAC fixos, derivados do número de série do Pi.
- **Rede:** `usb0` estático em `10.211.77.1/29`; `dnsmasq` só no `usb0`, faixa `.2` a `.6`, sem `router` e sem
  `dns-server`.
- **Serviço** `implantacao/raspberry-pi/rotaguard-coleta.service`: `User=drivesafe`,
  `ExecStart=/opt/drivesafe/.venv/bin/python caixa/run_coleta.py servir`, `Nice=10`, `Restart=always`, mesmo
  `EnvironmentFile` do monitor.
- **Energia na coleta:** pelo cabo, o Pi 4 é alimentado pelo computador.
  - Porta USB-A dá de 500 a 900 mA; a documentação do Pi 4 cita ~600 mA de consumo típico da placa.
  - Recomendação: porta USB-C do computador (1,5 A ou mais) ou hub com fonte. Subtensão aparece no bit 0 do
    `vcgencmd get_throttled` (spec 005, PI4-10).
- **Windows:** reconhecimento do RNDIS pelo descritor de sistema no Windows 11. Se falhar, testar NCM.
- **Tempo:** meta de até 60 s do cabo ligado às viagens baixadas (o boot leva ~30 a 40 s), para caber nos 2 min do O3.

## 11. Contratos com outras specs

| Com | O que esta spec usa ou entrega |
|---|---|
| 001 | **Usa:** `DRIVESAFE_VIAGENS_DIR`, nome da pasta, `registro.trava`, `fechar_viagens_interrompidas`, `verificar_registro`, `verificar_viagem`, `registrar_ajuste_relogio`, `derivar_chave`. **Entrega:** `carregar_identidade()` e `chave_da_caixa()`, que substituem a `obter_chave_caixa` provisória (spec 001 §11). **Pedidos:** (a) `fechar_viagens_interrompidas` tomar a trava da pasta enquanto conserta, porque monitor e serviço de coleta podem chamar ao mesmo tempo; (b) `inicio_viagem.dados.caixa` levar `id`, `geracao` e `kid`; (c) `alg = "ed25519"` assinando com `IdentidadeCaixa.semente_ed25519` |
| 002 | Arquivos `trechos/trecho-NNN.enc`; `*.parcial` fica fora do manifesto; a coleta nunca abre trecho. A coleta libera espaço apagando coletadas (§6.8, item 3). A pergunta P2 pode mudar a chave dos trechos |
| 004 | Recebe a pasta coletada (§9.3), `relogio.json`, manifesto e chaves públicas, e segue a §4.6 sobre quem tem cada chave. Verificação do HMAC do registro e decifragem dos trechos ficam no servidor |
| 005 | Perfil pi4, bipes do pen drive pelo alarme, subtensão na coleta, pausa do monitor pelo `coleta-ativa` (PI4-17), RTC DS3231 |
| 006 | O modo `registro` dos sinais de ativação (o servidor precisa aceitar; tarefa da 006) deixa o registro coletado mais sensível e reforça a pergunta P1 |
| 007 | O app reimplementa o protocolo da §6 com os vetores da §13, ou chama o cliente Python |

## 12. Funções públicas

Identificadores novos em português, como nas specs 001 e 002 (`RegistroViagem`, `verificar_viagem`). Colunas novas do
banco em inglês, como o resto do esquema.

```python
# caixa/coleta/identidade.py  (instalar precisa de `cryptography` para gerar o Ed25519; carregar não)
class CaixaNaoPareada(RuntimeError): ...
@dataclass(frozen=True)
class IdentidadeCaixa:
    id_caixa: str; geracao: int; empresa_id: int | None; dispositivo_id: int | None
    chave_publica: bytes; kid: str
    chave_caixa: bytes = field(repr=False); semente_ed25519: bytes = field(repr=False)
    chave_coleta: bytes          # propriedade: derivar_chave(chave_caixa, b"rotaguard/coleta/hmac/v1")
    impressao: str               # propriedade
def instalar_identidade(data_dir: Path, arquivo_pareamento: Path, substituir: bool = False,
                        forcar: bool = False) -> IdentidadeCaixa
def carregar_identidade(data_dir: Path) -> IdentidadeCaixa          # CaixaNaoPareada
def chave_da_caixa(data_dir: Path) -> bytes

# caixa/coleta/protocolo.py  (só biblioteca padrão)
def derivar_chave(chave: bytes, info: bytes) -> bytes                # igual à da spec 001
def assinar_json(conteudo: dict, chave: bytes, rotulo: str) -> bytes
def conferir_json(dados: bytes, chave: bytes, rotulo: str) -> dict   # AssinaturaInvalida
def prova_caixa(...); def prova_app(...); def chave_sessao(...); def mac_requisicao(...); def mac_resposta(...)

# caixa/coleta/servico.py
@dataclass
class FuncoesViagem:           # padrão: as funções da spec 001; falsas nos testes
    fechar_interrompidas: Callable; estado: Callable; registrar_ajuste_relogio: Callable
class ServicoColeta:           # regras, sem rede
    def __init__(self, identidade, dir_viagens, data_dir, funcoes: FuncoesViagem, relogio=None,
                 retencao_dias: int = 30, espaco_livre=None, ajustar_relogio_sistema=None)
class ServidorColeta:          # ThreadingHTTPServer ligado a um IP
    def __init__(self, servico: ServicoColeta, host: str, porta: int, interface_usb: bool = False)
class VigiaConexao:            # interfaces → sobe e derruba servidor e anúncio
    def __init__(self, servico, interfaces, redes, porta, ler_interfaces=None, anuncio=None)
    def tick(self) -> None

# caixa/coleta/anuncio.py
class AnuncioMdns:  def publicar(self, id_caixa, ip, porta); def retirar(self)
# caixa/coleta/exportacao.py
def exportar_viagens(servico, destino: Path) -> dict
class VigiaMidias:  def tick(self) -> None
# caixa/coleta/cliente.py
def carregar_chaveiro(caminho: Path) -> Chaveiro
class ClienteColeta:
    def descobrir(self, espera_s: float = 3.0, enderecos=()) -> list[CaixaEncontrada]
    def coletar(self, caixa: CaixaEncontrada, destino: Path) -> dict
def preparar_midia(midia: Path, chaveiro) -> dict
def importar_midia(midia: Path, destino: Path, chaveiro) -> dict

# servidor/backend/identidade_caixa.py  (só biblioteca padrão)
def carregar_ou_criar_raiz(caminho: Path) -> bytes
def derivar_chave_caixa(raiz: bytes, id_caixa: str, geracao: int) -> bytes
def parear_dispositivo(db, dispositivo, raiz, nova_geracao: bool = False) -> dict
def registrar_chave_publica(db, raiz, dados: bytes, substituir: bool = False)
def chaveiro_coleta(db, raiz, empresa) -> dict
```

Linha de comando:

| Comando | Para quê |
|---|---|
| `python servidor/manage.py parear-caixa --dispositivo ID --saida ARQ [--nova-geracao]` | Gera ou troca a identidade |
| `python servidor/manage.py registrar-chave-publica ARQ [--substituir]` | Guarda a chave pública da caixa |
| `python servidor/manage.py chaveiro-coleta --empresa ID --saida ARQ` | Exporta o chaveiro de coleta |
| `python caixa/run_coleta.py identidade instalar ARQ [--substituir] [--forcar]` | Instala a identidade na caixa |
| `python caixa/run_coleta.py identidade mostrar` | ID, geração, impressão e `kid` |
| `python caixa/run_coleta.py servir` | Serviço de coleta (vigia da conexão e das mídias) |
| `python caixa/run_coleta.py exportar --destino DIR` | Exportação local |
| `python ferramentas/coletar_caixa.py descobrir \| coletar \| preparar-midia \| importar-midia` | Cliente |

## 13. Critérios de aceite

Testes em `tests/test_identidade_coleta.py`, sem hardware: servidor real em `127.0.0.1` com porta livre, pastas de
viagem sintéticas, funções da spec 001 falsas quando o módulo ainda não existir, relógios falsos. Prioridade P1 = laço
"conectar, reconhecer, baixar e confirmar"; P2 = robustez e endurecimento.

| ID | P | Critério |
|---|---|---|
| COL-01 | P1 | `manage.py parear-caixa --dispositivo ID --saida ARQ` gera `id_caixa` único (`rg-` + 12 base32 minúsculos), geração 1, grava `box_id`, geração e data no dispositivo e escreve `pareamento.json`; a saída mostra só ID, geração e impressão; dispositivo já pareado ou revogado é recusado sem `--nova-geracao`, que sobe a geração e limpa a revogação |
| COL-02 | P1 | A chave da caixa é `derivar_chave(raiz, "rotaguard/caixa/v1\n<id>\n<geração>")`; a raiz tem 32 bytes, fica em `DRIVESAFE_RAIZ_CAIXAS_ARQUIVO` e é criada com permissão restrita na primeira vez; nenhum valor de chave aparece em nenhuma tabela do banco (o teste varre o SQLite) |
| COL-03 | P1 | `run_coleta.py identidade instalar ARQ` valida o arquivo, gera o par Ed25519 na caixa, grava `identidade/caixa.json` de forma atômica com 0600 (pasta 0700) em POSIX e escreve `chave-publica.json` assinado; outro `id_caixa`, ou geração menor ou igual, é recusado sem `--forcar`; geração maior exige `--substituir` e troca todas as chaves |
| COL-04 | P1 | `carregar_identidade` devolve ID, geração, `kid`, chave pública e as chaves; `chave_da_caixa` devolve 32 bytes; `repr` não mostra segredo; sem identidade, `CaixaNaoPareada` com a instrução de pareamento; permissão aberta em POSIX é corrigida para 0600 com aviso; `run_monitor.py` loga ID e `kid`, ou avisa que a caixa não está pareada, sem parar o monitoramento |
| COL-05 | P1 | `derivar_chave` confere com o caso de teste 1 do RFC 5869 e com a `derivar_chave` da spec 001 quando ela existir; servidor e caixa derivam as mesmas chaves de caixa, coleta e MAC da chave pública (teste cruzado entre `servidor/backend/identidade_caixa.py` e `caixa/coleta/`) |
| COL-06 | P1 | `manage.py registrar-chave-publica ARQ` confere a assinatura com a chave derivada da raiz e grava `kid`, chave e geração; assinatura errada, caixa desconhecida ou geração acima da atual são recusadas; repetir é idempotente; outro `kid` na mesma geração só com `--substituir`; registro e troca vão para a auditoria |
| COL-07 | P1 | `manage.py chaveiro-coleta --empresa ID --saida ARQ` traz só caixas da empresa, com geração atual, chave de coleta de cada geração, chaves públicas registradas e `revogada_em`; nunca a chave da caixa, a raiz, a chave do registro nem a dos trechos; arquivo com permissão restrita; exportação auditada |
| COL-08 | P1 | `revogar-dispositivo` marca a identidade revogada; o chaveiro traz `revogada_em`; o cliente recusa a caixa revogada sem `--aceitar-revogada` |
| COL-09 | P1 | Nenhuma linha de log, `repr`, mensagem de exceção ou saída de comando, em pareamento, instalação, carga, sessão, exportação, importação e cliente, contém a raiz, a chave da caixa, as subchaves ou a semente, em hex, base64 ou base64url |
| COL-10 | P1 | Sem autenticação só `POST /v1/desafio` e `POST /v1/sessao` respondem; qualquer outra rota, existente ou não e com qualquer método, dá 401 com o corpo genérico |
| COL-11 | P1 | Desafio-resposta nos dois sentidos com a chave de coleta; nonce da caixa de uso único e validade de 60 s; prova errada, nonce repetido ou vencido dão 401; o cliente aborta quando a prova da caixa não confere |
| COL-12 | P1 | Cada requisição autenticada leva sessão, `seq` crescente e MAC sobre sessão, `seq`, método, alvo e SHA-256 do corpo; MAC errado, corpo alterado, `seq` repetida e sessão ociosa por mais de 600 s dão 401; o cliente recusa resposta com MAC errado |
| COL-13 | P2 | 5 provas erradas do mesmo IP em 10 min dão 429 por 60 s; no máximo 32 desafios pendentes (sai o mais antigo); POST sem `Content-Length` dá 411 e corpo acima de 64 KB dá 413 |
| COL-14 | P1 | O vigia liga o servidor só no IPv4 da interface configurada, com link e IP dentro da rede permitida; nunca em `0.0.0.0`; desliga quando o link cai ou o IP sai da rede (leitor de interfaces falso) |
| COL-15 | P2 | O anúncio `_rotaguard._tcp.local.` com TXT `id` e `v` é publicado só no IP da interface ativa e retirado quando ela cai; sem `zeroconf`, aviso no log e o serviço continua pelo IP |
| COL-16 | P1 | `GET /v1/identidade` devolve ID, geração, `kid` e o texto exato de `chave-publica.json`, que o servidor aceita em `registrar-chave-publica` |
| COL-17 | P1 | A lista chama `fechar_viagens_interrompidas` antes de ler; mostra só pastas `<número>-<hex>` com estado (`fechada`, `interrompida`, `aberta_sem_fechamento`, `em_andamento` com a trava tomada), arquivos e bytes; por padrão só as não coletadas; manifesto e arquivos de viagem `em_andamento` dão 409 |
| COL-18 | P1 | `POST /v1/relogio` chama `registrar_ajuste_relogio(pasta, chave_caixa, utc_caixa, utc_app + rtt/2, origem="coleta", referencia="app_na_coleta")` em cada viagem não coletada com a trava livre, antes de qualquer manifesto da sessão (manifesto antes dá 409 `relogio_pendente`); responde `deslocamento_ms` = referência − caixa e `incerteza_ms`; grava `relogio_medido` no diário; com `DRIVESAFE_COLETA_AJUSTAR_RELOGIO=1` e deslocamento acima de 2 s, chama o ajuste do relógio do sistema depois dos registros |
| COL-19 | P1 | O manifesto tem os campos da §7.1 na ordem, arquivos ordenados com tamanho e SHA-256 corretos e assinatura pela regra de bytes, recalculada no teste sem o código da coleta; `registro.trava` e `*.parcial` ficam fora; link simbólico e nome inválido vão para `ignorados`; sem mudança, o mesmo manifesto; com arquivo mudado (inclusive por `ajuste_relogio`), manifesto novo |
| COL-20 | P1 | Só caminhos do manifesto são servidos; `..`, caminho absoluto, `%2e%2e`, barra invertida e link simbólico dão 404; a resposta leva `X-RotaGuard-Sha256` igual ao manifesto |
| COL-21 | P1 | A confirmação com o SHA-256 dos bytes do manifesto atual grava `coletada` no diário com `fsync`; hash de manifesto antigo ou errado dá 409 sem marcar; repetir é idempotente; nada é apagado |
| COL-22 | P1 | A viagem coletada só é apagada com hora de app autenticado a partir de confirmação + retenção (padrão 30 dias), com `DELETE` e o hash confirmado, ou com espaço livre abaixo do limite (mais antigas primeiro); viagem não coletada, viagem com trava tomada e passagem do relógio da caixa nunca apagam; cada exclusão vai para o diário |
| COL-23 | P2 | Sessão autenticada pela interface USB cria e renova `coleta/coleta-ativa`; o arquivo some 120 s depois da última requisição ou quando o link cai; arquivo de outro boot ou vencido vale como inativo; sessão pela rede do escritório não cria o arquivo |
| COL-24 | P1 | `run_coleta.py exportar --destino DIR` copia viagens não coletadas e fora de andamento para `RotaGuard/<id_caixa>/`, com `manifesto.json` e `chave-publica.json`; confere o SHA-256 do que escreveu, faz `fsync` e grava `exportacao.json` por último; registra `exportada`; não marca coletada; processa recibos presentes |
| COL-25 | P2 | O vigia de mídias só exporta com `RotaGuard/pedidos/<id_caixa>.json` assinado e `nonce` inédito; pedido ausente, com assinatura errada ou `nonce` repetido não escreve nem copia nada; o resultado chama os bipes (2 curtos ou 1 longo; alarme falso) |
| COL-26 | P2 | Recibo assinado com o hash do manifesto exportado marca a viagem como coletada, com o `utc_app` do recibo valendo para a retenção; recibo com assinatura errada ou hash diferente é ignorado com aviso |
| COL-27 | P1 | `descobrir` junta mDNS (anúncio falso), IP fixo e endereços dados sem repetir `id_caixa`; sem `zeroconf`, usa só IP e endereços |
| COL-28 | P1 | `coletar` autentica, mede o relógio, baixa em `.parcial`, confere assinatura, tamanhos e hashes, roda a verificação da spec 001 sem chave, grava a pasta final e a `.coleta` (§9.3) e só então confirma; arquivo corrompido no servidor faz a viagem falhar sem confirmação; nova execução refaz a parcial e não baixa de novo viagem íntegra no destino |
| COL-29 | P2 | `preparar-midia` escreve pedidos assinados para as caixas do chaveiro; `importar-midia` confere manifestos e hashes como a COL-28, copia para o destino e escreve recibos assinados e pedidos novos |
| COL-30 | P1 | `ferramentas/coletar_caixa.py` imprime o resumo JSON da §9.4 e sai com 0 (tudo certo), 1 (alguma falha) ou 2 (uso ou chaveiro inválido) |
| COL-31 | P2 | `rotaguard-coleta.service`, o script do gadget USB e as configurações de rede existem, com as seções e chaves obrigatórias, `ExecStart` apontando para arquivo do repositório e DHCP sem gateway e sem DNS (teste de estrutura; o funcionamento real só com o Pi) |
| COL-32 | P1 | Os vetores da §14 são recalculados pelo teste e batem com o texto desta spec |

## 14. Vetores de teste

Calculados em 11/09/2026 com a regra desta spec. O teste COL-32 recalcula.

| Entrada ou saída | Valor |
|---|---|
| Raiz | `a5` repetido 32 vezes |
| `id_caixa`, geração | `rg-abcdefghijkl`, 1 |
| Chave da caixa | `72de750c3bc4902b499d7aea45082528177927483df813873b4858b06defc470` |
| Chave de coleta | `47d4e91a02a070538586db5454eadf393753c56b55f6e88f4045790872c8b78b` |
| Chave do MAC da chave pública | `6cb04920c26655445f21f837ccb6eaf0725ef047438fe4480586a3f39234ed29` |
| Impressão | `256e16802f1fe563` |
| `nonce_app` (`11` × 32) | `ERERERERERERERERERERERERERERERERERERERERERE` |
| `nonce_caixa` (`22` × 32) | `IiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiI` |
| `prova_caixa` | `XCO4DXgXWCtxZvu8-vZFXR0hzfR61vYg_0NcBgSsFJk` |
| `prova_app` | `lcfR4cH186Rme0nHOBiKCWxB9BTJc5P_vANw11Jfmzk` |
| Chave da sessão | `03380278d02abef6fb03148f8c061e4fe14c1ba9d8a6f7f5a7dfc37913836d28` |
| Sessão (`33` × 16) | `MzMzMzMzMzMzMzMzMzMzMw` |
| MAC de `GET /v1/viagens`, `seq` 1, corpo vazio | `GeX8sYXyJDZ5wOUce8046xAsoTRHOVbu3csVC1jWW64` |
| MAC da resposta 200 `{"viagens":[]}`, `seq` 1 | `SVlnqihpahHR-ihTeNicAUL1HOIDajHZVtrjwgtZqvI` |

Manifesto de exemplo (arquivo `registro.jsonl` com o conteúdo `{"seq":1}` + `\n`), bytes exatos:

```
{"formato":"rotaguard-manifesto/1","id_caixa":"rg-abcdefghijkl","geracao":1,"kid":"0123456789abcdef","id_viagem":"000042-9f3ac1d2","estado":"fechada","relogio":{"utc":"2026-09-11T18:00:00.000Z","monotonico_ms":5000123,"boot_id":"boot-exemplo"},"arquivos":[{"caminho":"registro.jsonl","tamanho":10,"sha256":"40fe96e5dc9e9822902a3f343389fa3cd531c145a19eb55881b0be5e9b0962e7"}],"ignorados":[],"total_bytes":10,"assinatura":"26d17cd3f34fbc069433456ccdbfb2aed4f1c4aafab18607030284b4d4347fd1"}
```

`hash_manifesto` = `22c10b38d5fd0fd87dedb8dbc377ee3bd00ed4b379b369d7bce0742dcb3dd97a`

## 15. Fora de escopo

- Tela do app instalável, rota HTTP do servidor que entrega o chaveiro e cofre de chaves do app (specs 004 e 007).
- Importador e relatório (spec 004); formato do registro e dos trechos (specs 001 e 002).
- Cifrar o transporte e a exportação (pergunta P1) e cifrar trechos para a chave pública da empresa (pergunta P2).
- Autenticar a caixa no servidor com a chave nova, no lugar do token `dsk_` (continua como está).
- Rotação só da chave de coleta, sem trocar a geração.
- Retomar download no meio de um arquivo (`Range`): os arquivos são pequenos (spec 002: 6 a 9 MB por trecho).
- Migrar viagens gravadas com a chave provisória da spec 001: a cadeia e os hashes continuam verificáveis, as
  assinaturas não.
- Apagar de forma segura no cartão SD (memória flash não garante).
- Mais de uma empresa na mesma caixa.

## 16. Riscos

| Risco | Impacto | Resposta |
|---|---|---|
| Registro em claro na rede do escritório e no pen drive | Alto: dado pessoal, e sensível no modo `registro` da spec 006 | Padrão só no cabo USB (ponto a ponto); pergunta P1 |
| Caixa ou cartão roubado com a chave da caixa e os trechos juntos | Alto | Revogação (§4.5); pergunta P2 (chave pública da empresa) |
| Raiz de pareamento perdida ou copiada junto com o banco | Alto | Arquivo fora do banco, backup separado, caminho configurável; aviso no log quando fica em `data/` |
| Quem tem a raiz deriva a chave do HMAC do registro | Médio: registro com HMAC não protege o motorista do servidor | Ed25519 gerado só na caixa; `kid` anotado pelo técnico na instalação e presente no registro; troca de chave pública auditada |
| Porta USB do computador não alimenta o Pi 4 | Médio | Porta USB-C ou hub com fonte; subtensão registrada (spec 005) |
| Windows não reconhecer o gadget RNDIS | Médio | ECM + RNDIS com descritor; plano B NCM; pen drive |
| Sem RTC, horário das viagens não é corrigível na coleta | Alto (spec 001 §6.4) | DS3231 como requisito (spec 005) |
| Chaveiro de coleta vazado | Médio: permite baixar registros (não abre trechos) | Mínimo privilégio (§4.1); nova geração; cofre no app (spec 007) |
| Conflito de contrato com a spec 001 (trava na recuperação, `kid` no registro) | Médio | Pedidos explícitos na §11 |
| Monitor e serviço de coleta disputando o cartão durante a coleta | Baixo | Pausa pelo `coleta-ativa` (spec 005, PI4-17) |

## 17. Perguntas para o Matheus

| # | Pergunta | Padrão usado até a resposta |
|---|---|---|
| P1 | O registro da viagem trafega em claro na rede e no pen drive (os trechos já vão cifrados). Cifrar também? Custo: mais trabalho no app (spec 007) | Não cifrar; coleta pela rede do escritório só ligando por configuração. Recomendação: cifrar antes de liberar a rede do escritório |
| P2 | Chave dos trechos derivada da chave da caixa (spec 002 aprovada) ou cifrada para a chave pública da empresa (§4.6)? | Derivada, como aprovado. Recomendação: chave pública da empresa |
| P3 | A coleta pela rede do escritório entra ligada? | Não: só o cabo USB-C; escritório por configuração |
| P4 | Quem opera a coleta e recebe o chaveiro: gestor, técnico ou funcionário do pátio? | Gestor e admin da empresa |
| P5 | Os 30 dias da Q4 valem também para a cópia na caixa depois da coleta, ou a caixa apaga logo depois da confirmação? | 30 dias na caixa |
| P6 | Pen drive só com pedido assinado pelo app? | Sim; sem pedido, nada é copiado |
| P7 | O servidor com a raiz de pareamento fica com a equipe RotaGuard (multiempresa) ou com cada empresa? | Equipe RotaGuard |
| P8 | Pausar o monitoramento enquanto a caixa está no computador pelo cabo USB (spec 005, PI4-17)? | Sim, só com sessão autenticada |

## 18. Decisões tomadas nesta spec

1. **Chave da caixa derivada de uma raiz no servidor**, fora do banco (§4.2).
2. **Par Ed25519 gerado na própria caixa** na instalação; a chave privada nunca sai (§4.1).
3. **Chave de coleta separada** por HKDF: o computador de coleta não abre trechos nem forja o registro (§4.1).
4. **Chave pública assinada com uma subchave que o computador de coleta não tem** (§4.3).
5. **HTTP com desafio-resposta nos dois sentidos e MAC em cada requisição e resposta**, sem TLS (§6). TLS com chave
   compartilhada não existe no Python 3.11 do Bookworm, e certificado autoassinado exigiria outra distribuição de
   confiança.
6. **Serviço separado do monitor** (`run_coleta.py`): a coleta funciona com câmera quebrada ou monitor parado.
7. **Relógio medido antes do manifesto**, com o sinal da spec 001 (§6.7).
8. **Assinatura sobre os bytes**, com a mesma regra da spec 001 (§7.2).
9. **Retenção contada pela hora do app**, nunca pelo relógio da caixa (§6.8).
10. **Pen drive só com pedido assinado e recibo assinado** (§8). Modo "armazenamento em massa" pelo USB-C foi
    descartado: expõe os arquivos a qualquer computador sem autenticação.
11. **Pasta coletada é cópia exata**; metadados na pasta `.coleta` ao lado (§9.3), para `verificar_viagem` conferir o
    nome.
12. **Confirmar mesmo com registro adulterado** (§9.2): a confirmação atesta o transporte; a adulteração vai para o
    relatório.
