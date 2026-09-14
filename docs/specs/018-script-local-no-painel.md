# Spec 018 · Script local no painel

| Campo | Valor |
|---|---|
| Status | aprovada (pedido do Matheus em 14/09/2026) → em implementação |
| PRD | RF-50 (proposto): o painel reconhece o script da caixa aberto neste computador e captura os eventos dele |
| Pedido | "lembre-se: por enquanto local, e caso eu inicie o script no computador, deve reconhecer que ele está aberto e capturar as logs" (14/09/2026) |
| Specs irmãs | 010 (app de teste e pasta de dados), 013 (app do painel), 014 (sessão), 012 (tipos de evento) |
| Código | `caixa/vision/em_execucao.py`, `caixa/run_monitor.py`, `painel/desktop/script_local.py`, `painel/app/src/app/ao-vivo/page.tsx`, `painel/app/src/components/live/*` |
| Testes | `tests/test_painel_script_local.py` (SCR-01 a SCR-10), `painel/app/scripts/testes/ao-vivo.test.mjs` (SCR-11 a SCR-13) |

## Contexto

- O "script" é a detecção da caixa rodando neste computador, de dois jeitos:
  - o **RotaGuard Teste** (`caixa/app_teste.py`, pacote `RotaGuardTeste.exe`, spec 010): a tela de início abre um
    segundo processo do mesmo executável com `--monitor`;
  - o **monitor direto** em Python (`python caixa/run_monitor.py`).
- Os dois terminam em `run_monitor.main`.
- **Onde e como o script grava hoje** (conferido no código e neste computador em 14/09/2026):
  - pasta do RotaGuard Teste: `%LOCALAPPDATA%\RotaGuard\Teste` (Linux `$XDG_DATA_HOME/rotaguard/teste`), com
    `eventos.db`, `registro-teste.log` e `sirene.wav`;
  - pasta do monitor direto: `--data-dir`, `DRIVESAFE_DATA_DIR` ou `~/.drivesafe`;
  - eventos em SQLite, modo WAL, tabela `events` (`caixa/vision/event_queue.py`): `event_uid` (uuid4),
    `alert_type`, `risk_level`, `duration`, `details` (JSON), `occurred_at` (ISO UTC com milissegundos), `boot_id`,
    `monotonic`, `status`, `attempts`, `last_error`, `sent_at`;
  - `registro-teste.log`: texto técnico do `logging`, uma linha por mensagem.
- O registro da viagem da spec 001 (linhas JSON) ainda não existe no código: hoje só há a fila `eventos.db`.

## Decisões

1. **O script anuncia que está aberto.**
   - `run_monitor.main` grava `em_execucao.json` na pasta de dados logo depois de abrir a fila e o apaga no `finally`.
   - Campos: `formato` (`rotaguard-em-execucao/1`), `sessao` (uuid4 hex), `pid`, `programa`, `iniciado_em`,
     `camera`, `ultimo_sinal` e `pasta`.
   - O `ultimo_sinal` é renovado a cada 3 s (no máximo 5 s) numa thread própria. A gravação troca o arquivo inteiro
     (temporário + `os.replace`).
   - Nenhuma linha da detecção muda, e falha no anúncio nunca derruba o monitoramento.
2. **Câmera sem nome de aparelho:** o OpenCV não informa o nome (spec 010, fora de escopo). O índice 0 aparece como
   "Câmera 1", vídeo aparece como "Vídeo arquivo.mp4" e endereço de rede como "Câmera de rede", sem mostrar usuário e
   senha.
3. **Plano B para o pacote já instalado, que ainda não anuncia:** o painel procura o processo pelo nome, sem psutil.
   - Windows: `tasklist /FO CSV /NH`, com `RotaGuardTeste.exe`. O `tasklist` não mostra a linha de comando; o Python
     rodado direto do código já anuncia.
   - Linux: `ps -eo pid=,args=`, com `RotaGuardTeste`, `app_teste.py` ou `run_monitor.py`.
4. **Aberto** = anúncio com sinal de menos de 15 s e pid vivo, ou processo achado.
   - O pid é conferido só consultando o processo: no Windows, `OpenProcess` e `GetExitCodeProcess`; no Linux,
     `os.kill(pid, 0)`.
   - Nunca `os.kill` no Windows, onde o sinal 0 é Ctrl+C.
   - O painel nunca encerra processo.
5. **Captura só leitura.**
   - O painel abre `eventos.db` com `mode=ro`, lê os eventos novos pelo `rowid` e fecha em seguida, sem prender trava.
   - Copia para `capturas.db` na pasta de dados do painel, sem duplicar (chave: `event_uid` do script). Se a fila foi
     recriada (dados apagados no app de teste), a leitura recomeça do início e a chave evita repetição.
6. **Sessão** = cada vez que o script abriu.
   - Com anúncio, a chave é a `sessao` do anúncio. Pelo plano B, é o pid e a hora em que o painel o viu.
   - Ao fechar, a sessão ganha `encerrado_em`. O evento vai para a sessão aberta mais recente que cobre a hora dele.
7. **Preparação para a VPS:** `sessoes`, `eventos` e `fontes` nascem com `uid` (uuid4 hex), `criado_em` e
   `alterado_em` (ISO UTC). O módulo é Python puro, sem pywebview.
8. **Ponte:** `script_estado()` → `ScriptEstado` e `script_eventos(desde_id)` → `EventoScript[]`, pelos métodos de
   `ScriptLocal` (`estado`, `eventos`). `iniciar()` e `parar()` ligam a vigia (captura a cada 2 s).
9. **Tela "Teste neste computador"** (`/ao-vivo/`) e bloco `LiveScriptCard` no Início.
   - A tela consulta a situação a cada 3 s e os eventos a cada 2 s, e para ao sair.
   - Ponto pulsando só com o script aberto.
   - Com o script aberto, mostra os eventos desta sessão; fechado, os últimos capturados. Mais novos primeiro, e a
     linha nova entra suave.
   - Nomes dos tipos vêm de `tipos-de-evento.json`, com frase-resumo por categoria ("3 de sono e 1 de celular").

## Comportamento

- **Script fechado**
  - Dado nenhum script rodando, quando a tela abre, então aparece "O script não está aberto. Abra o RotaGuard Teste
    neste computador e ele aparece aqui sozinho." e os últimos eventos já capturados, sem ponto pulsando.
- **Abrir o RotaGuard Teste**
  - Dado o painel aberto, quando o Matheus inicia o teste, então em até ~3 s a linha muda para
    "Aberto desde 14:20 · Câmera 1", com o ponto pulsando.
  - Os eventos que o script registrar aparecem na lista em até ~2 s, no topo.
- **Pacote antigo, sem anúncio**
  - Dado o `RotaGuardTeste.exe` instalado antes desta versão, quando ele está aberto, então o painel mostra
    "Aberto desde <hora em que o painel o viu> · RotaGuard Teste".
- **Fechar o teste**
  - Dado o teste em andamento, quando a janela da câmera fecha normalmente, então o anúncio some e a tela volta a
    "não está aberto" em até ~3 s.
  - Se o processo for morto (sem apagar o anúncio), a tela volta a "não está aberto" em até 15 s.
- **Reabrir**
  - Dado o teste fechado, quando ele é aberto de novo, então começa outra sessão e a lista mostra só os eventos novos.
- **Nada muda no script**
  - Dado o painel capturando, quando o script grava eventos, então o script continua gravando normalmente e o
    `eventos.db` e o `em_execucao.json` nunca são alterados pelo painel.

## Critérios de aceite

| ID | Critério | Teste |
|---|---|---|
| SCR-01 | Sem anúncio e sem processo: `aberto: false`, campos nulos, `eventos: 0`, chaves na ordem do `ScriptEstado` | `tests/test_painel_script_local.py` |
| SCR-02 | Anúncio com sinal recente e pid vivo: aberto com `programa`, `desde` (= `iniciado_em`), `pid`, `camera`, `ultimo_sinal` e `pasta`, sem listar processos | idem |
| SCR-03 | Plano B: `RotaGuardTeste.exe` no `tasklist` ou `app_teste.py`/`run_monitor.py` no `ps` contam como aberto; outro python não; pid vivo sem psutil | idem |
| SCR-04 | Sinal de 15 s ou mais, pid morto ou anúncio ilegível = fechado; 14 s ainda aberto | idem |
| SCR-05 | Captura incremental (3, depois 0, depois 2), `eventos(desde_id)`, painel reaberto não duplica; registros com `uid` hex, `criado_em` e `alterado_em` | idem |
| SCR-06 | `eventos.db` e `em_execucao.json` com o mesmo hash depois da captura; conexão `mode=ro` recusa escrita; o script grava durante a captura | idem |
| SCR-07 | Fechar e reabrir o script cria outra sessão; eventos separados por sessão; sessões encerradas com `uid` | idem |
| SCR-08 | Lado do script: `em_execucao.json` com os campos, renovado a cada ≤ 5 s, apagado ao sair (só se for da mesma sessão); `run_monitor.main` cria o anúncio antes do `try` e o apaga no `finally`; texto da câmera sem endereço de rede | idem |
| SCR-09 | `iniciar()` captura sozinho em thread (2 s por padrão) e `parar()` encerra a thread | idem |
| SCR-10 | Pastas procuradas: `RotaGuard\Teste` (Windows), `rotaguard/teste` (Linux), `~/.drivesafe` e `DRIVESAFE_DATA_DIR` | idem |
| SCR-11 | Frase-resumo por categoria ("3 de sono e 1 de celular"; várias categorias com vírgula e "e"; vazio = "Nenhum evento") | `painel/app/scripts/testes/ao-vivo.test.mjs` |
| SCR-12 | Nome do tipo vem de `tipos-de-evento.json`; tipo desconhecido (ex.: `calibracao_suspeita`) não quebra | idem |
| SCR-13 | Tela consulta `script_estado` a cada 3 s e `script_eventos` a cada 2 s, para ao sair, ponto pulsando só aberto, `.anim-row`, frase de fechado exata, `LiveScriptCard` exportado, sem pílula, sem maiúsculas e sem fonte mono | idem |

## Fora de escopo

- **VPS e Raspberry Pi:** vêm depois. Hoje tudo é deste computador, e os `uid` preparam o envio.
- Copiar o `registro-teste.log`: é texto técnico (desempenho, carregamento de modelos). A tela mostra os eventos.
- Registro da viagem da spec 001 e trechos da spec 002: ainda não existem no código.
- Nome do aparelho da câmera (limitação do OpenCV, spec 010).
- Iniciar, parar ou encerrar o script pelo painel.
- Apagar eventos capturados pelo painel. A guarda segue a spec 016 quando for ligada.

## Riscos

- **Pacote antigo no Windows:** sem anúncio e sem linha de comando no `tasklist`, a tela de início parada (sem teste
  rodando) já conta como "aberto". O `desde` é a hora em que o painel viu o processo, e não há câmera.
- **Leitura de banco em WAL só para leitura:** o SQLite pode criar `eventos.db-shm`/`-wal` se não existirem. São
  arquivos de controle do próprio SQLite e não mudam os dados (SCR-06 confere o hash).
- **Custo do `tasklist`:** só roda quando não há anúncio válido, com cache de 2,5 s (a primeira chamada levou 0,87 s
  neste computador em 14/09).
- **Relógio:** sessão e sinal usam o relógio deste computador; o mesmo relógio grava os dois lados.
- **Privacidade:** os eventos copiados levam os `details` numéricos do script (sem imagem). Na empresa, valem as regras
  de acesso e guarda das specs 014 e 016.
