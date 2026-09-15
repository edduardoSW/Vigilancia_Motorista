# Onde parou · Painel da empresa · 15/09/2026, parte 2 (spec 019)

> Depois de usar o app, o Matheus disse: "o dashboard eu ainda achei que ficou um pouco confuso porem eu gostei muito, mas
> ainda não parece muito intuitivo". Pediu lista e card, modais no centro com o fundo desfocado, importar o termo do
> motorista, modo escuro, o motorista claro na viagem e os campos dos vídeos. No meio do trabalho: "apos acabar faça o
> push".
> Spec: `docs/specs/019-painel-mais-claro-lista-cards-tema-termo-videos.md` (implementada). PRD: RF-51 a RF-54.
> A rodada anterior do mesmo dia está em `onde-parou-2026-09-15.md`.

## O que mudou, pedido por pedido

| Pedido | O que ficou | Onde |
|---|---|---|
| Lista e card | Viagens, Momentos, Motoristas, Veículos, Caixas e Equipe com "Lista / Cards", com os mesmos itens, ordem e filtro. O padrão é cards, e a escolha fica guardada por pessoa pela ponte (`preferencias_salvar`) | `ui/view-toggle.tsx`, `ui/card-grid.tsx`, `session-provider.tsx` (`useVisao`) |
| Modais no centro com o fundo desfocado | O painel lateral acabou: toda janela, inclusive a busca rápida, abre no centro com o resto desfocado (`.veu`). A janela abre do começo, porque o foco inicial não rola | `ui/dialog.tsx`, `ui/drawer.tsx`, `ui/use-presence.ts`, `globals.css` |
| Ver antes de editar | Motorista, veículo e caixa abrem mostrando os dados; "Editar" troca para o formulário na mesma janela | `drivers/driver-details.tsx`, `vehicles/vehicle-details.tsx` |
| Importar o termo | "Importar termo assinado" (PDF, PNG ou JPEG até 10 MB, data da assinatura e versão), "Ver termo", "Histórico do termo" e "Registrar que revogou". Nada é apagado | `drivers/driver-term.tsx`; Python: `painel/desktop/cadastros.py` (`termo_importar`, `termo_ver`, `motorista_termos`) |
| Modo escuro | Claro, Escuro ou Igual ao Windows, por pessoa, no pé do menu e em Configurações › Aparência. Cores por papel, com contraste de 4,5:1 conferido nos dois temas | `globals.css`, `theme-options.ts`, `sidebar.tsx`, `settings/appearance-section.tsx`, `auth-gate.tsx`; Python: `painel/desktop/preferencias.py` |
| Motorista na viagem | O relatório mostra Veículo e Motorista em destaque (nome, matrícula, CNH, termo e "Ver cadastro"); Viagens mostra o motorista no card e na lista | `trip/trip-people.tsx`, `trips/trips-screen.tsx` |
| Campos dos vídeos | Todo momento tem o campo Vídeo. A janela do momento mostra, por trecho, Início, Fim, Duração, Câmera, Caixa, Coletado em, Fica guardado até e Situação; sem vídeo, diz o motivo | `trip/moment-dialog.tsx`, `trip/video-rules.ts`, `moment-list.tsx`, `content/demo.json` |
| Menos confuso | O Início começa por "O que fazer agora", com um card e um botão para cada tarefa. Os Primeiros passos viraram uma barra, e a caixa conectada virou uma linha no menu | `home/home-screen.tsx`, `sidebar.tsx` |

Os caminhos da tela são relativos a `painel/app/src/components/`.

## Contrato da ponte (acréscimos)

- `Estado` ganhou `tema`, `preferencias` e `videos_dias`; `Motorista.termo` ganhou `arquivo`.
- Métodos novos: `preferencias_salvar`, `termo_importar`, `termo_ver` e `motorista_termos`.
- Cópia de segurança no formato `rotaguard-copia/2`, com um zip de `painel.db` e dos arquivos dos termos.
- Banco: migração 2, com as colunas do arquivo no termo e a tabela `preferencias`.
- Detalhes em `docs/painel/contrato-painel.md`.

## Defeitos achados e corrigidos nesta rodada

1. **Alterar motorista sem mandar `termo` revogava o termo** no Python, e sem mandar `situacao` o motorista voltava a
   ativo. A tela sempre manda tudo, então nenhum teste pegou; foi achado na revisão. O teste veio antes da correção
   (`tests/test_painel_termos.py`, TER-02), e a correção está em `cadastros.py`: alteração sem a chave mantém o
   guardado.
2. **Demonstração da tela e Python diferentes** nas frases e na ordem das conferências do termo e das preferências, e o
   "abriu termo" era registrado antes de abrir. Agora estão iguais (`src/lib/demo-backend.ts`).
3. **Janela do momento abria já rolada**, com o topo do vídeo cortado: o foco no botão Confirmar rolava o corpo da
   janela. Agora o foco não rola e o quadro do vídeo tem altura máxima. Quem achou foi a captura; o roteiro passou a
   conferir `scrollTop` 0.
4. **Relatório cortava a situação do termo** com reticências, e **no escuro o botão do vídeo sumia no fundo**.
5. **Texto sobre o lima ilegível no escuro** (`text-verde` e `text-tinta`): agora usa `text-sobre-lima`, com teste
   (ESC-02).
6. Achados pelos agentes antes de terminar:
   - salvar preferências por cima de um valor estragado no banco não regravava (VIS-02);
   - cada edição do motorista criaria um termo novo sem o arquivo (TER-02).

## Provas rodadas

- Tela (`painel/app`):
  - `npx tsc --noEmit`: 0 erros;
  - `npx eslint src scripts`: 0 problemas;
  - `npm run build`: 13 páginas;
  - `npm test`: 54 de 54, com `shell.test.mjs` (MOD-01, VIS-01, ESC-01, ESC-02, VID-01, VID-02 e os anteriores), `cadastros.test.mjs` (TER e MOT) e `previa.test.mjs`.
- Python (`.venv\Scripts\python.exe tests\<arquivo>.py`):
  - contas 19, cadastros 15, configurações 10, termos 7, preferências 3, desktop 13 e script local 10, somando 77 verificações;
  - o agente também estragou de propósito 15 regras do termo e das preferências, e os testes pegaram as 15.
- Roteiro (`node scripts/conferir-telas.mjs`, com o Edge sem janela e `out/` servida em `127.0.0.1:3107`):
  - 102 conferências passaram, sem erro de JavaScript;
  - conferiu Lista e Cards, a janela no centro com o fundo desfocado, ver antes de editar, importar, ver e o histórico do termo, o motorista e os vídeos no relatório, o modo escuro (inclusive Igual ao Windows), o texto maior em 1200 × 760, a Consulta e o Supervisor.
- Capturas em `docs/painel/capturas-2026-09-15-parte-2/`, olhadas uma a uma.

## Não conferido

- O uso pela ponte do Python dentro do pacote, com a janela visível: importar o termo de verdade, abrir o PDF no leitor
  do computador e o tema guardado de uma abertura para outra.
- O tempo de um arquivo de 10 MB pela ponte do pywebview.
- Teclado nos cards: só Tab e Enter, sem as setas da tabela.
- Falha de disco no meio da importação: o código desfaz o banco e apaga o arquivo, mas sem teste.

## Perguntas para o Matheus (spec 019)

1. Todo momento deve ter vídeo? Hoje só sono repetido e celular têm; os outros dizem por que não têm.
2. Sem o arquivo do termo, os vídeos daquele motorista ficam trancados? Hoje basta o termo registrado.
3. O modelo do termo para imprimir entra agora?

## O que ainda falta no painel

- Ler a caixa de verdade (importação, spec 004): viagens, vídeos e caixa conectada ainda vêm do `demo.json`.
- Importar planilha (PLA-01), restaurar a cópia (BKP-02, agora com os termos), apagar vídeo vencido na abertura
  (CFG-06) e "Quem dirigiu?" na importação.
- Seção "Impressão" das configurações (spec 016).
- Instalador: precisa do Inno Setup.
- Nota do projeto na vault ("DriveSafe AI - Monitoramento de Motoristas") ainda descreve o painel como app no navegador.

## Pacote

- Montado com `python implantacao/painel/build.py --sem-instalador`, depois de conferir que o RotaGuard Painel estava
  fechado. Etapas: build da interface, PyInstaller e pacote conferido (interface com 96 arquivos).
- `RotaGuardPainel.exe --verificar` com a janela oculta: `"ok": true`, `lang` pt-BR, aviso de dados fictícios, scripts
  rodando, motor `edgechromium`, 3,8 s.
- `build/painel/pacotes/RotaGuard-Painel-windows-x64.zip`: 19,1 MB, SHA-256
  `5a9603221892945860616c0b6034099d7e7bb4cb3b865f79cb860f5e7a3cba0d`.
- O atalho da área de trabalho aponta para `build/painel/dist/RotaGuardPainel/RotaGuardPainel.exe`, que agora é este
  pacote.

## Git e vault

- Esta rodada e a anterior do mesmo dia vão num commit na branch `app-instalavel-em-andamento`, com push, como o
  Matheus pediu ("apos acabar faça o push"). A `main` continua em `18918ef`.
- Vault: os erros 127 (foco que rola a janela) e 128 (demonstração e Python diferentes) estão em
  `erros-que-a-ia-comete.md`, commitados e enviados.
