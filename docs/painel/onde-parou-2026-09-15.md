# Onde parou · Painel da empresa · 15/09/2026

> Retomada de `onde-parou-2026-09-14.md` (pedido do Matheus: "continue o dashboard de onde parou").
> A casca da interface está pronta e foi conferida em captura, sem janela visível. O núcleo Python está na seção própria.

## Casca da interface (itens 1 a 8 de 14/09)

| Item | Situação | Onde |
|---|---|---|
| 1. Menu | Pronto: as 7 áreas na ordem da spec 014, mais "Teste neste computador"; some o que a função não abre; a barrinha desliza até a tela aberta; "N para ver" em Viagens; quem entrou e "Sair" embaixo | `painel/app/src/components/sidebar.tsx`, `menu.ts` |
| 2. Busca rápida (Ctrl+K) | Pronto: telas da própria função, viagens, motoristas, veículos e capítulos do guia, sem acento; Enter abre (motorista e veículo no painel lateral, por `?abrir=`) | `command-palette.tsx`, `command-search.ts` |
| 3. Início | Pronto: Primeiros passos (só administrador, com "Esconder"), caixa conectada, "Para verificar", avisos (CNH vencendo, caixa com problema, cópia com mais de 7 dias) e o teste neste computador | `src/components/home/` |
| 4. Viagens | Pronto: abas "Para verificar", "Revisadas" e "Todas", busca, dia da chegada; a linha abre o relatório, que ganhou "Voltar para Viagens" e o link do Guia | `src/components/trips/trips-screen.tsx`, `src/app/viagens/` |
| 5. Decisões e vídeo pela ponte | Pronto: confirmar, alarme falso, orientado e desfazer (com "Desfazer" no aviso); Consulta vê o momento sem vídeo e sem botões; vídeo trancado sem termo; vídeo aberto fecha quando a tela bloqueia | `decisions-provider.tsx`, `moment-list.tsx`, `moment-actions.ts` |
| 6. Texto maior | Pronto: 115% com a altura da janela compensada; conferido em 1200 × 760 | `src/app/globals.css`, `auth-gate.tsx` |
| 7. Cópia na demonstração | Pronto: aceita a senha escolhida na hora (10 caracteres ou mais), não a senha de quem entrou | `src/lib/demo-backend.ts` |
| 8. Testes da tela | Pronto: `shell.test.mjs` (MEN-01, MEN-02, EQP-02, ENT-07, GUI-07) e `previa.test.mjs` com as rotas novas e a tela Viagens | `painel/app/scripts/testes/` |

## Mudanças no contrato da ponte (valem para a tela e para o Python)

- `Estado` ganhou `texto_maior` (vale para todos deste computador, inclusive na tela de entrar).
- `config_ler()` passou a ser só do administrador, como diz a spec 016 (CFG-01).
- Métodos novos: `inicio_resumo()` (última cópia e Primeiros passos escondidos) e `primeiros_passos_esconder(esconder)`.
- CPF da lista sempre mascarado como `•••.•••.247-••`; CPF mascarado que volta da tela quer dizer "manter o guardado".
- A demonstração do Python passa a criar as duas decisões de exemplo da viagem v-1187, iguais às da tela.
- `docs/painel/contrato-painel.md` atualizado; MEN-02 (busca rápida) entrou na spec 014.

## Defeitos achados e corrigidos na tela

1. **Editar motorista com CPF não salvava.** O Python devolvia o CPF como `***.982.247-**`; a tela não reconhecia, sumia com ele e acusava "O CPF tem 11 números". Teste MOT-02 em `cadastros.test.mjs`; lado Python na seção abaixo.
2. **Hora de quem decidiu 3 h adiantada.** A decisão gravada pelo Python vem em UTC e a tela recortava o texto. Agora mostra no relógio do computador.
3. **Painel lateral e diálogos presos na tela.** A animação de entrada da tela usa `transform`, que prende o `position: fixed`: o painel do motorista terminava na altura da lista. Painéis e diálogos passaram a abrir numa camada da janela (`src/components/ui/layer.tsx`). Isso já existia antes desta retomada; ninguém tinha aberto as telas.
4. **Texto maior.** O zoom aumentava também a altura da janela (o pé do menu sumia); depois o rodapé do menu passou por cima de quem entrou; e as tabelas cortavam texto no meio da letra. Corrigido com a altura compensada, o menu mais estreito com texto maior e reticências nas células.
5. **Linha dos momentos desalinhada** quando uma linha já tinha decisão, e a busca de Viagens com o texto de ajuda cortado.

Os erros 3 e 4 viraram os erros 123 e 124 em `erros-que-a-ia-comete.md` da vault.

## Provas rodadas em 15/09 (tela)

- `npx tsc --noEmit` em `painel/app`: 0 erros.
- `npx eslint src scripts`: 0 erros e 1 aviso de propósito (`_senha` em `demo-backend.ts`).
- `npm run build`: 13 páginas exportadas (Início, Viagens, Motoristas, Veículos, Equipe, Configurações, Guia, Teste neste computador, 404 e os 3 relatórios).
- `npm test`: 38 de 38.
- `node scripts/conferir-telas.mjs`, com a pasta `out/` servida em `127.0.0.1:3107` e o Edge sem janela: todas as conferências passaram. O roteiro entra pela demonstração, navega clicando no menu, digita na busca no ritmo de gente e confere o endereço e a tela depois de cada ação; confere também Consulta, Supervisor, painel lateral, diálogo e texto maior em 1200 × 760. Capturas em `docs/painel/capturas-2026-09-15/`.

## Provas rodadas em 15/09 (Python)

- `.venv\Scripts\python.exe tests\<arquivo>.py`: contas 19, cadastros 15, configurações 10, desktop 13 e script local
  10, somando 67 verificações. Todas rodadas de novo depois das correções 4 e 5 do núcleo.
- Pacote (`implantacao/painel/build.py` e `RotaGuardPainel.exe --verificar`): ver a seção "Pacote".

## Pacote

- `python implantacao/painel/build.py --sem-instalador` (70 s): build da interface, PyInstaller, pacote conferido
  (interface com 95 arquivos) e `RotaGuardPainel.exe --verificar` com a janela oculta: `"ok": true`, `lang` pt-BR,
  aviso de dados fictícios, scripts rodando, motor `edgechromium`, 8,8 s.
- `build/painel/pacotes/RotaGuard-Painel-windows-x64.zip`: 19,0 MB, SHA-256
  `74e509e53f9f47ef6bcb5761fc123cfe7801ac6ac92f61764ebb4bdeda3796b3`.
- O atalho "RotaGuard Painel" da área de trabalho aponta para `build/painel/dist/RotaGuardPainel/RotaGuardPainel.exe`,
  que agora é o pacote novo.
- Instalador (`-setup.exe`) não gerado: o Inno Setup não está instalado neste computador.
- **Não conferido:** o app aberto com a janela visível e o uso pela ponte do Python dentro do pacote (entrar, cadastrar,
  decidir). O `--verificar` confere só a primeira tela; o roteiro de telas usa a demonstração em memória.

## Núcleo Python

Os três testes que faltavam existem e passam. Foram escritos por um agente em paralelo, com o teste antes de cada
correção, e aqui foram revisados (diff) e rodados de novo.

| Arquivo | Resultado | Critérios |
|---|---|---|
| `tests/test_painel_contas.py` | 19 de 19 | ENT-01 a ENT-09, EQP-01 (3 funções × 25 métodos da ponte), EQP-03, EQP-04, ATV-01 a ATV-03, INI-01 e INI-02 (Início, spec 017), `texto_maior` no `estado()` |
| `tests/test_painel_cadastros.py` | 15 de 15 | MOT-01 a MOT-07, VEI-01, VEI-02, CXA-01 a CXA-03, CAD-01, CAD-02 e as decisões de demonstração |
| `tests/test_painel_configuracoes.py` | 10 de 10 | CFG-01 a CFG-07, BKP-01, BKP-03 e o `cryptography` travado e com licença no pacote |
| `tests/test_painel_desktop.py` | 13 de 13 | PAC-01 a PAC-13 |
| `tests/test_painel_script_local.py` | 10 de 10 | SCR-01 a SCR-10 |

### Defeitos do núcleo achados e corrigidos

1. **Registro de atividades escondia linha apagada.** Com os gatilhos do banco removidos, apagar a última linha e
   entrar de novo deixava o registro "íntegro". Agora a ponta guardada é conferida antes de acrescentar e, se não bate,
   fica uma marca de quebra (`atividades.py`).
2. **CPF mascarado fora do formato da tela** (`***.982.247-**`): agora `•••.•••.247-••`, e o CPF mascarado que volta
   mantém o guardado (`cadastros.py`).
3. **Nome nos relatórios diferente da tela** (`juliana P.`): mesma regra do `nomeCurto` (`cadastros.py`).
4. **Senha digitada no campo de usuário ia para o registro de atividades** como "em quê" (ENT-03). Achado na revisão
   do trabalho do agente: agora usuário que não existe fica sem alvo, com "usuário não cadastrado" (`contas.py`). A
   demonstração da tela faz o mesmo.
5. **Orientação em alarme falso era aceita**, e trocar confirmado por alarme falso mantinha "orientado" (EQP-04).
   Agora a orientação só vale em momento confirmado (`cadastros.py`).

A demonstração da tela também foi alinhada ao Python: acesso desativado responde `sem_permissao`, só o toque da tela
renova o tempo sem uso e os dias desde a cópia nunca ficam negativos.

### O que ficou parcial

- **ENT-02:** o arquivo da empresa da spec 003 não tem assinatura da RotaGuard nem nome da empresa. Um arquivo alterado
  com estrutura válida, ou de outra empresa, passa (o painel mostra "Empresa 7"). Precisa de um formato com assinatura.
- **Dependem de funcionalidade que ainda não existe** (só a regra pura foi testada): PLA-01, BKP-02, importação de
  viagem (partes do MOT-06 e do CXA-03), relatório usando a regra de descanso (VEI-02), viagens e momentos na
  exportação do motorista (MOT-07), regra guardada na viagem (CFG-04), apagar vídeos na abertura (CFG-06) e a marca
  "em apuração" (CFG-07).
- **ATV-01:** sem chave secreta, quem mexe no arquivo com cuidado ainda consegue recalcular a cadeia inteira.
- **Sem teste, para decidir:** entrar com a tela bloqueada troca a sessão (nos dois lados; o contrato diz que só
  `estado`, `desbloquear`, `sair` e `tocar` passam); `ler_chaveiro` exige chave pública em toda caixa; a espera por
  senha errada fica só na memória (fechar e abrir o app zera).

## O que ainda falta no painel

- **Ler a caixa de verdade** (importação, spec 004): viagens e caixa conectada ainda vêm do `demo.json`, nos dois modos (demonstração e arquivo da empresa). A faixa "Prévia com dados fictícios" continua em todas as telas.
- Importar planilha (PLA-01), restaurar cópia (BKP-02), apagar vídeo vencido na abertura (CFG-06), modelo do termo para imprimir e "Quem dirigiu?" na importação.
- Configurações: a seção "Impressão" da spec 016 não existe ainda.
- Viagens: filtro por veículo e motorista é pela busca de texto, sem seletor próprio.
- No Python, "Últimos 30 dias" dos motoristas sai sempre 0, porque as viagens ainda não ficam no banco do painel.
- Abrir o pacote novo com a janela visível e usar de verdade pela ponte do Python (a verificação oculta confere só a
  primeira tela). O instalador precisa do Inno Setup.
- Atualizar a nota do projeto na vault ("DriveSafe AI - Monitoramento de Motoristas"): ela ainda descreve o painel como
  app no navegador (10/09), antes da decisão de 14/09 pelo app de janela.

## Perguntas que continuam com o Matheus

- Raspberry Pi 5 com 4 GB no lugar do Pi 4 (recomendação de 14/09).
- As perguntas ainda abertas nas specs 014 a 017 (funções, planilha de RH, "em apuração", suporte no guia).

## Git

- Nada foi commitado nesta retomada. A branch continua `app-instalavel-em-andamento`.
