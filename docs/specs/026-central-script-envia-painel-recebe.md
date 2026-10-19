# Spec 026 · Central na VPS: o script envia, o painel executável recebe

| Campo | Valor |
|---|---|
| Status | implementada em 19/10/2026: central (`tests/test_central_api.py` 22), app de teste (`tests/test_trechos.py` 13) e painel (`tests/test_painel_central.py` 13); ponta a ponta contra a central de PRODUÇÃO pela internet: pareamento, envio, cardio barrado, trecho WebM baixado com SHA-256 conferido e revogação |
| PRD | RF-63, RF-64, RF-65, RF-66, RF-07 (trechos), RNF-15, RNF-17 |
| Pedido | "mas o painel eu quero que seja executavel e tipo uma pessoa em outro computador use o script e eu no meu computador consiga ver os resultados e gravação da outra pessoa que usou no computador dela" (19/10/2026); "mesmo que a vps caia eu quero que o projeto continue caso tenha os arquivos do painel e script baixados no dispositivo para rodalos localmente" |
| Substitui | publicação da spec 024 (painel no navegador): o painel continua executável; o código web fica no repositório, desligado |
| Specs irmãs | 002 (trechos por recorrência), 018 (script local no painel), 021 (VPS), 023 (tela do app de teste) |
| Código | `servidor/` (central), `caixa/vision/sync.py`, `caixa/vision/trechos.py`, `caixa/tela_teste/`, `caixa/app_teste.py`, `painel/desktop/central.py`, `painel/desktop/ponte.py`, `painel/app/src/lib/bridge.ts`, telas do painel |
| Testes | `tests/test_central_api.py` (CEN-01 a CEN-12), `tests/test_trechos.py` (TRE-01 a TRE-08), `tests/test_painel_central.py` (PCE-01 a PCE-10) |

## Contexto

- O servidor central (`servidor/`, FastAPI) já é multiempresa: empresas, usuários com função e login, aparelhos com
  token `dsk_…` (`manage.py criar-dispositivo`), recebe eventos em lote (`POST /api/events`) e sinal de vida
  (`POST /api/devices/heartbeat`), e lista alertas por empresa (`GET /api/alerts`).
- O script já sabe enviar a fila de eventos para um servidor com token e reenviar quando a conexão volta
  (`caixa/vision/sync.py`).
- O que falta: parear o computador de outra pessoa sem linha de comando, gravar e enviar **trechos de vídeo**, mandar o
  **resumo da sessão**, e o **painel executável** buscar tudo na central.

## Como fica

```
Computador da outra pessoa              VPS (rotaguard.acexpartners.com.br)            Seu computador
RotaGuard Teste ──eventos, resumo, trechos──▶ /api (central) ◀──busca a cada 30 s── RotaGuard Painel (executável)
   (tudo salvo local antes; fila)                (SQLite + pasta de trechos)              (tudo salvo local depois)
```

## Decisões

1. **Central = `servidor/` na VPS**, só a API, em `https://rotaguard.acexpartners.com.br/api/…` (o Caddy manda
   `/api/*` para o container `rotaguard_central`). O app web antigo do servidor (`painel/webapp`) não é publicado.
   Container `morro-alto-os-rotaguard-central`, volume `rotaguard_central_dados` (banco + trechos).
2. **Pareamento por código** (sem token na mão):
   - no painel, "Gerar código para outro computador" → a central cria um aparelho pendente e devolve um código curto
     (`ABCD-2345`, sem letras ambíguas) válido por 30 minutos e de uso único;
   - no RotaGuard Teste, "Conectar à empresa" → digita o código → recebe o token do aparelho e o nome da empresa;
   - o token fica só na pasta de dados do app de teste; "Desconectar" apaga.
3. **O que o script envia** (só depois de conectado, com aviso claro na tela do que vai e o indicador "enviando para
   <empresa>"; pode ser desligado a qualquer momento nas opções):
   - eventos (o que já existe, sem nenhum dado de cardio: dado de saúde fica no computador);
   - início e fim de cada sessão de teste, com o resumo (contagens, PERCLOS médio, piscadas por minuto, duração);
   - **trechos de vídeo** dos momentos relevantes (decisão 5).
4. **Local primeiro (RNF-15):** tudo é gravado no computador antes de enviar; sem internet ou com a VPS fora, a fila
   guarda e reenvia depois. O painel mostra o que já baixou e avisa "sem conexão com a central". Nada no teste ou no
   painel trava por falta da central.
5. **Trechos (spec 002 aplicada ao teste):**
   - buffer circular dos últimos 8 s em memória (quadros reduzidos para 640 px de largura, ~15 por segundo);
   - gatilhos: olhos fechados ≥ 1 s (microssono e acima), celular na mão/ouvido/olhando ≥ 3 s, olhos esfregados e
     cabeceio; grava 8 s antes + 8 s depois (16 s);
   - no máximo 20 trechos por sessão e 30 s entre dois trechos;
   - o vídeo vai **com a malha de pontos desenhada** (mesmo quadro da tela) e marca d'água com hora e tipo;
   - formato que o WebView2 do painel toca: MP4 H.264 se o OpenCV do pacote gravar `avc1`; senão WebM VP8/VP9; senão
     quadros JPEG num `.rgclip` (zip com `indice.json`) tocado por canvas no painel. O formato escolhido fica no
     metadado;
   - SHA-256 de cada trecho conferido na central e no painel.
6. **O que o painel busca:** `GET /api/sync/novidades?desde=<cursor>` devolve, da empresa da pessoa logada, aparelhos
   (com "testando agora" pelo sinal de vida), sessões, eventos e metadados de trechos; `GET /api/trechos/{uid}/arquivo`
   baixa o vídeo. O painel guarda tudo no banco local (tabelas com `uid`, sem duplicar) e os vídeos na pasta de dados.
7. **Login do painel na central:** Configurações › Central: endereço (padrão
   `https://rotaguard.acexpartners.com.br`), e-mail ou telefone e senha de um usuário gestor ou administrador da
   central (criado pela RotaGuard com `manage.py criar-usuario`). O painel guarda só o token de sessão, nunca a senha.
   Só quem tem a permissão `ver_video` no painel vê os trechos.
8. **Telas novas no painel:** "Testes à distância" no menu (ou dentro de Ao vivo): cada computador conectado, "testando
   agora" com risco atual, sessões com resumo, linha do tempo dos eventos e os trechos com player; o mesmo visual de
   lista e cards da spec 019.
9. **Segurança:** HTTPS; token de aparelho só envia (não lê nada); token de usuário só lê a própria empresa; troca de
   código com limite de tentativas por IP; trecho até 25 MB; nomes de arquivo gerados pela central; trechos guardados
   fora de pasta pública; auditoria de quem baixou cada trecho.
10. **Painel web não publicado:** a spec 024 foi implementada e testada antes deste pedido, mas não vai para a VPS.
    O código fica em `painel/web/` e no transporte "servidor" do `bridge.ts`, só ativo no build web. Na VPS fica só
    esta central de dados.

## Critérios de aceite

| ID | Critério |
|---|---|
| CEN-01 | Gestor logado gera código; código tem 8 caracteres do alfabeto sem ambíguos e expira em 30 min |
| CEN-02 | Trocar código válido devolve token `dsk_…` uma vez; segunda troca do mesmo código falha |
| CEN-03 | Código expirado ou errado falha; mais de 10 trocas erradas por minuto do mesmo IP → 429 |
| CEN-04 | Aparelho envia sessão (início, fim, resumo) e ela aparece em `novidades` só para a empresa dele |
| CEN-05 | `PUT /api/trechos/{uid}` com SHA-256 certo grava; SHA-256 errado → 422; acima de 25 MB → 413 |
| CEN-06 | Token de aparelho não lê `novidades` nem baixa trecho (403) |
| CEN-07 | Usuário de outra empresa não vê nem baixa (404) |
| CEN-08 | `novidades` com cursor devolve só o que mudou depois dele, em ordem, sem repetir |
| CEN-09 | Baixar trecho registra auditoria |
| CEN-10 | Evento com chave de cardio é recusado ou tem a chave removida (dado de saúde não sai do computador) |
| CEN-11 | Aparelho "testando agora" quando o último sinal de vida tem menos de 30 s |
| CEN-12 | Testes antigos do servidor (`tests/test_server_sync.py`, `tests/test_politica_remota.py`) continuam passando |
| TRE-01 | Sem gatilho, nenhum trecho é gravado |
| TRE-02 | Microssono gera um trecho com ~8 s antes e ~8 s depois (±1 s) |
| TRE-03 | Dois gatilhos a menos de 30 s geram um trecho só |
| TRE-04 | Limite de 20 trechos por sessão |
| TRE-05 | O arquivo abre: MP4/WebM lido de volta pelo OpenCV, ou `.rgclip` com `indice.json` coerente |
| TRE-06 | Metadado com uid, tipo, início, fim, duração, formato e SHA-256 conferindo com o arquivo |
| TRE-07 | Sem conexão, trechos e sessão ficam na fila e sobem quando a central volta (teste com servidor de mentira) |
| TRE-08 | Desligar "Enviar para a empresa" para o envio e não apaga nada local |
| PCE-01 | Conectar com usuário e senha certos guarda o token; senha não é gravada em lugar nenhum |
| PCE-02 | Senha errada mostra erro e não guarda nada |
| PCE-03 | Busca de novidades grava aparelhos, sessões, eventos e trechos no banco local sem duplicar |
| PCE-04 | Trecho baixado confere SHA-256; diferente é descartado e tentado de novo |
| PCE-05 | Central fora do ar: a tela mostra "sem conexão" e os dados já baixados |
| PCE-06 | Gerar código no painel mostra o código e a validade |
| PCE-07 | Função Consulta não vê trechos (permissão `ver_video`) |
| PCE-08 | Ponte: novos métodos no contrato (`central_*`, `remotos_*`) também na demonstração em memória |
| PCE-09 | Desconectar apaga o token e para a busca, mantendo o que já foi baixado |
| PCE-10 | Build, lint e testes do painel sem erro |

## Fora de escopo

- Vídeo ao vivo de outro computador (só trechos e estado "testando agora").
- Sincronizar cadastros do painel (motoristas, veículos) com a central.
- Painel no navegador.

## Riscos

- Trecho com rosto é dado pessoal (e a malha, biométrico): aviso claro no app de teste antes de enviar, prazo de guarda
  na central (padrão 30 dias, pergunta Q4 do PRD) e parecer jurídico antes de usar com motoristas de clientes.

## Contrato da central (v1)

Base: `https://rotaguard.acexpartners.com.br`. JSON em UTF-8; datas ISO 8601 em UTC com `Z`; ids públicos são `uid`
(uuid4 hex, 32 caracteres). Erro: `{"detail": "<mensagem em português>"}` com o código HTTP.

Autenticação:
- **usuário** (painel): `POST /api/auth/login` já existe; o painel manda `Authorization: Bearer <token de sessão>` (a
  central passa a aceitar o token no cabeçalho além do cookie).
- **aparelho** (script): `Authorization: Bearer dsk_…`.

| Método e rota | Quem | Corpo / parâmetros | Resposta |
|---|---|---|---|
| `POST /api/pareamento/codigos` | usuário gestor ou admin | `{"nome": "Notebook da Ana"}` (opcional) | `201 {"codigo": "ABCD2345", "expira_em": "...", "aparelho_uid": "..."}` |
| `POST /api/pareamento/trocar` | ninguém (limite por IP) | `{"codigo": "ABCD-2345", "computador": "Notebook da Ana", "programa": "RotaGuard Teste 0.x"}` (hífen e minúsculas aceitos) | `200 {"token": "dsk_...", "aparelho_uid": "...", "empresa": {"uid": "...", "nome": "..."}}` |
| `POST /api/devices/heartbeat` | aparelho | já existe; `status` pode trazer `sessao_uid` e `risk_level` | já existe |
| `POST /api/events` | aparelho | já existe; `details` pode trazer `sessao_uid` e `trecho_uid` | já existe |
| `PUT /api/sessoes/{sessao_uid}` | aparelho | `{"iniciada_em", "encerrada_em" (ou null), "programa", "camera", "resumo": {...}}` (idempotente: reenviar atualiza) | `200 {"uid": "..."}` |
| `PUT /api/trechos/{trecho_uid}` | aparelho | corpo binário; cabeçalhos `X-RotaGuard-Sessao`, `X-RotaGuard-Tipo` (tipo do evento), `X-RotaGuard-Inicio`, `X-RotaGuard-Fim`, `X-RotaGuard-Formato` (`mp4`, `webm` ou `rgclip`), `X-RotaGuard-Sha256`, `X-RotaGuard-Evento` (uid do evento, opcional) | `201 {"uid": "...", "tamanho": n}`; mesmo uid e mesmo SHA-256 de novo → `200` (idempotente) |
| `GET /api/sync/novidades?desde=<cursor>&limite=500` | usuário | `desde` vazio = tudo | `200 {"cursor": "<opaco>", "mais": bool, "aparelhos": [...], "sessoes": [...], "eventos": [...], "trechos": [...]}` |
| `GET /api/trechos/{trecho_uid}/arquivo` | usuário | — | o arquivo, com `Content-Type` do formato e `X-RotaGuard-Sha256` |
| `DELETE /api/pareamento/aparelhos/{aparelho_uid}` | usuário admin | — | `204` (token do aparelho deixa de valer) |

Itens de `novidades` (todos com `uid` e `alterado_em`):
- `aparelhos`: `uid`, `nome`, `computador`, `programa`, `pareado_em`, `ultimo_sinal`, `testando_agora` (bool), `risco_atual` (0 a 3 ou null), `sessao_atual_uid`.
- `sessoes`: `uid`, `aparelho_uid`, `iniciada_em`, `encerrada_em`, `programa`, `camera`, `resumo` (objeto).
- `eventos`: `uid` (o `event_uid` do script), `aparelho_uid`, `sessao_uid`, `tipo`, `nivel_risco`, `duracao_s`, `ocorrido_em`, `detalhes` (sem cardio), `trecho_uid`.
- `trechos`: `uid`, `aparelho_uid`, `sessao_uid`, `evento_uid`, `tipo`, `inicio`, `fim`, `duracao_s`, `formato`, `tamanho`, `sha256`, `recebido_em`.

`resumo` da sessão (o mesmo do arquivo salvo pela tela do teste, spec 023, sem cardio): `duracao_s`, `eventos_por_tipo`
(objeto tipo → contagem), `perclos_medio`, `piscadas_por_minuto`, `trechos` (contagem), `fps_medio`.

## Mudanças no contrato

Implementado na central em 19/10/2026 (`servidor/`, testes em `tests/test_central_api.py`). Nenhuma rota, campo ou
formato da tabela acima mudou; o que segue são escolhas onde o contrato deixava aberto e campos **acrescentados**
(quem não os ler continua funcionando).

**Login do painel (escolha):**
- `POST /api/auth/login` com o cabeçalho `X-RotaGuard-Cliente: painel` **ou** `"token": true` no corpo devolve, além dos
  campos de sempre (`id`, `name`, `email`, `role`, `company`, `must_change_password`…), `"token": "<token de sessão>"`
  e `"expira_em"`. Nesse modo **não há cookie** e o cabeçalho `X-DriveSafe: 1` não é exigido.
- O app web antigo continua igual: sem esse cabeçalho/campo, exige `X-DriveSafe: 1` e a sessão vai no cookie
  (`token` vem `null`).
- Token do painel vale **30 dias desde o último uso** (renova sozinho enquanto o painel busca). Sair:
  `POST /api/auth/logout` com o Bearer → 204.
- Com `Authorization: Bearer <token de sessão>` não se exige `X-DriveSafe` nem em POST/PATCH/DELETE.
- Usuário criado com senha temporária só consegue `GET /api/auth/me`, `POST /api/auth/password` e sair até trocar a
  senha (403 "Troque a senha temporária…"). Crie o gestor do painel com `DRIVESAFE_SENHA_INICIAL`.

**Códigos de status (escolha):**
- `POST /api/pareamento/trocar`: código errado, vencido, já usado ou anulado → `400`; mais de 10 erros por minuto do
  mesmo IP → `429` com `Retry-After` (vale até para código certo, até a janela passar).
- `POST /api/pareamento/codigos`: motorista → `403`; equipe (admin sem empresa) precisa mandar `"company_id"` (senão
  `400`); mais de 20 códigos ainda válidos na empresa → `429`.
- `PUT /api/sessoes/{uid}`: uid que não é UUID → `422`; uid de sessão de outro aparelho → `409`; resumo acima de
  16 KB → `413`; `encerrada_em` antes de `iniciada_em` → `422`.
- `PUT /api/trechos/{uid}`: `X-RotaGuard-Sessao`, `X-RotaGuard-Formato`, `X-RotaGuard-Sha256`, `X-RotaGuard-Tipo`,
  `X-RotaGuard-Inicio` e `X-RotaGuard-Fim` obrigatórios (`422` se faltarem ou vierem inválidos); só
  `X-RotaGuard-Evento` é opcional. A central confere a assinatura do arquivo (mp4 com `ftyp`, webm com cabeçalho EBML,
  rgclip = zip) → `422` se não bater. Mesmo uid com outro SHA-256, de outro aparelho, ou já apagado pelo prazo → `409`.
  Mais de 20 trechos na mesma sessão do mesmo aparelho → `409`. Mais de 100 trechos do mesmo aparelho em 24 h
  (`DRIVESAFE_TRECHOS_POR_DIA`) → `429` com `Retry-After`: um token vazado não enche o disco da VPS. Acima de 25 MB
  → `413` (pelo `Content-Length` ou durante o envio). Para o script: `409` e `422` não adiantam reenviar igual; `429`,
  `5xx` e falta de rede, sim.
- `GET /api/trechos/{uid}/arquivo`: aparelho → `403`; outra empresa ou uid inexistente → `404`; arquivo apagado pelo
  prazo de guarda → `410` (o painel não deve tentar de novo). `Content-Disposition: attachment`.
- `GET /api/sync/novidades`: aparelho → `403`; motorista → `403`; cursor que não veio da central → `400` (busque de
  novo com `desde` vazio). `limite` de 1 a 1000 (padrão 500).
- `DELETE /api/pareamento/aparelhos/{uid}`: além da equipe (admin), o **gestor da mesma empresa** desconecta
  computadores pareados por código (dispositivo de frota criado pela equipe: `403`); outra empresa → `404`. Um uid de
  código ainda não trocado anula o código (`204`).

**Campos acrescentados:**
- `novidades` traz também `"agora"` (hora da central, ISO com `Z`), para o painel julgar "testando agora" sem depender
  do relógio do próprio computador.
- `aparelhos[]` traz também `revogado_em` (data ou null): aparelho desconectado.
- `trechos[]` traz também `apagado_em` (data ou null): arquivo apagado pelo prazo de guarda; o download dá `410`.
- Formato dos ids: `eventos[].uid` e `trechos[].evento_uid` saem como UUID com hífens, minúsculo (é como o servidor já
  guarda o `event_uid` do script). Todos os outros (`aparelho_uid`, `sessao_uid`, `trecho_uid`, `uid` de aparelho,
  sessão e trecho) saem com 32 caracteres hexadecimais minúsculos, seja qual for a forma de UUID que o script mandar.

**Comportamento (para o script e o painel):**
- O cursor é opaco; por dentro é o número de sincronização do último item entregue. Qualquer criação ou alteração
  ganha número novo, então o mesmo item pode voltar depois do cursor quando muda (ex.: aparelho com novo sinal de
  vida, sessão que encerrou, trecho ligado ao evento, trecho apagado, aparelho desconectado). Use `uid` para atualizar
  o registro local, sem duplicar.
- `testando_agora` = sinal de vida (heartbeat ou envio de eventos) há menos de 30 s **e** sessão aberta. A sessão
  aberta vem de `status.sessao_uid` no heartbeat (mandar `null` ao parar o teste) ou de `PUT /api/sessoes` com
  `encerrada_em: null`; `PUT` com `encerrada_em` preenchido fecha. Quando o sinal some, a central marca o aparelho
  como "não testando" e isso chega ao painel pelo cursor.
- Evento e trecho se ligam nos dois sentidos, chegue qual chegar primeiro: `trecho_uid` nos `details` do evento ou
  `X-RotaGuard-Evento` no trecho.
- Cardio: a central remove dos `details` do evento e do `resumo` da sessão as chaves `bpm`, `cardio`,
  `frequencia_cardiaca`, `rppg`, `respiracao_rpm`, `rmssd_ms`, `snr_db` e qualquer chave começando com `cardio_`, sem
  diferença de maiúsculas e em qualquer nível; também na saída das novidades.
- `GET /api/health` (alias de `/health`) para o Caddy e o monitoramento; toda resposta `/api/*` sai com
  `Cache-Control: no-store`.
- IP para o limite de tentativas e a auditoria: `X-Forwarded-For` só é considerado quando a conexão vem de rede
  interna (10/8, 172.16/12, 192.168/16, loopback, link-local, fc00::/7), isto é, do Caddy na rede docker.

**Operação na VPS:**
- Volume em `/app/data`: banco `drivesafe.db`, trechos em `trechos/<uid da empresa>/<uid do trecho>.<formato>` e o
  segredo dos códigos `segredo-central.key` (criado na primeira vez; ou `DRIVESAFE_SEGREDO_CENTRAL`). Apagar o segredo
  só invalida códigos ainda não trocados.
- Empresa e gestor: `python manage.py criar-empresa --nome "…"` e
  `DRIVESAFE_SENHA_INICIAL='…' python manage.py criar-usuario --papel gestor --nome "…" --email … --empresa "<nome ou id>"`.
- Prazo de guarda (cron diário): `python manage.py apagar-trechos-antigos --dias 30` (também limpa envios
  interrompidos com mais de um dia e códigos vencidos).
- O Caddy precisa aceitar corpo de até 25 MB em `/api/*` (`request_body { max_size 26MB }`).
