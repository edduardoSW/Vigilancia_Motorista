# Onde parou · Painel da empresa · 14/09/2026, 15:00

> Trabalho **pela metade**. Nada aqui foi visto funcionando na janela: sem `npm run build`, sem pacote novo, sem abrir o app.

## Como chegou aqui

- **Pedido do Matheus (14/09, 14:11)**, depois de aprovar as prévias `docs/painel/previa-2026-09-14-parte-2/`:
  "gostei pode fazer mas deixe um pouco menos com cara de ia e quero algo mais dinamico ... acabe isso em no maximo 1 hora e meia".
- **Escopo:** telas de Entrar, Motoristas, Veículos e caixas, Equipe, Configurações e Guia de uso (specs 014 a 017), mais o
  "script local" (spec 018: o painel reconhece o RotaGuard Teste aberto neste computador e copia os eventos dele).
- **Divisão:** 5 agentes com um contrato comum (nomes, tipos, permissões, divisão de arquivos), prazo 15:05.
  O contrato estava só na pasta temporária da sessão e foi copiado para `docs/painel/contrato-painel.md`.
- **Queda às 14:40:** a janela do Claude fechou. Três agentes tinham terminado; o **núcleo Python** e a **casca da
  interface** foram interrompidos no meio.
- **Retomada das 14:41 às 15:00**, por pedido do Matheus ("continue de onde ele parou até 15 horas, após isso pare e anote
  onde parou"): medir o estado real, deixar compilando, corrigir o lint, anotar e subir no GitHub.

## Estado de cada parte

| Parte | Situação | Onde está |
|---|---|---|
| Script local (spec 018) | **Pronto.** Testes SCR-01 a SCR-13 passando | `painel/desktop/script_local.py`, `caixa/vision/em_execucao.py`, `painel/app/src/app/ao-vivo/`, `painel/app/src/components/live/` |
| Cadastros: motoristas, veículos, caixas (spec 015) | **Telas prontas.** Validadores 11 de 11 | `painel/app/src/components/drivers/`, `vehicles/`, `src/lib/validators.ts` |
| Equipe, Configurações, Guia (specs 014, 016, 017) | **Telas prontas.** Guia 5 de 5 | `painel/app/src/components/team/`, `settings/`, `guide/`, `src/content/guide.ts` |
| Núcleo Python (contas, cadastros, configurações, cópia, ponte) | **Interrompido. Código escrito, sem os testes próprios** | `painel/desktop/` |
| Casca da interface (entrada, menu, Início, Viagens) | **Interrompido. Entrada pronta, menu e Início não** | `painel/app/src/` |

### Núcleo Python: o que existe

- Módulos: `dados.py`, `contas.py`, `atividades.py`, `cadastros.py`, `configuracoes.py`, `copia.py` e `ponte.py`.
  Todos importam sem erro, e a `Ponte` tem 33 métodos públicos.
- `rotaguard_painel.py` já cria a janela com `js_api=ponte`, e a ponte liga e desliga o `ScriptLocal`.
- `tests/test_painel_desktop.py` continua com 13 de 13.

### Núcleo Python: o que falta

- **Nenhum dos testes do núcleo existe:** `tests/test_painel_contas.py`, `test_painel_cadastros.py` e
  `test_painel_configuracoes.py`. O código veio antes do teste, então cada critério precisa de teste e o que falhar
  precisa ser corrigido: ENT-01 a 09, EQP-01/03/04, ATV-01 a 03, MOT-01 a 07, VEI-01/02, CXA-01 a 03, CAD-01/02,
  CFG-01 a 07, BKP-01.
- **Conferir se estes ajustes pedidos no meio do caminho entraram:**
  - dígito verificador da CNH com a mesma variante do `validators.ts` (há "desconto" em `cadastros.py`, falta provar com teste);
  - `acao` do registro como frase curta ("adicionou pessoa" aparece em `contas.py`; faltam as outras);
  - `campo` com o nome exato da propriedade nos erros;
  - `veiculo_salvar` com `caixa_id` vinculando a caixa;
  - `motorista_salvar` com `termo.versao: null`;
  - `cryptography` presente no `.venv` para a cópia de segurança.

### Casca da interface: o que existe

- `src/lib/bridge.ts`, `src/lib/demo-backend.ts` (já com `script_estado` e `script_eventos`), `session-provider.tsx`
  e as peças de `src/components/ui/`.
- `globals.css` com `.anim-enter`, `.anim-row` e `.pulse-dot`.
- `layout.tsx` com `SessionProvider`, `ToastProvider`, `DecisionsProvider` e `AuthGate`.
- `auth-gate.tsx` completo: ativar, criar administrador, código de recuperação, entrar com espera, recuperar acesso,
  trocar senha, tela bloqueada e vigia de uso.

### Casca da interface: o que falta

1. **`sidebar.tsx` novo.** O menu ainda é o da prévia antiga e **não tem link** para Motoristas, Equipe, Configurações,
   Guia de uso e "Teste neste computador". As telas existem, mas não se chega nelas pelo menu. Itens sem permissão
   precisam sumir.
2. **`command-palette.tsx` (Ctrl+K).** Nunca foi criado. O import pendurado foi tirado do `auth-gate.tsx` para compilar;
   ao criar, voltar a montar `<CommandPalette />` quando `fase === "app"` e a tela não estiver bloqueada.
3. **Início (`src/app/page.tsx`):** `LiveScriptCard`, o que falta verificar hoje, CNH vencendo e Primeiros passos.
4. **`src/app/viagens/page.tsx`:** não existe. Lista com abas "Para verificar", "Revisadas" e "Todas".
5. **Decisões pela ponte:** `decisions-provider.tsx` e `moment-list.tsx` ainda não usam a ponte. Consulta não vê vídeo;
   `video_abrir` com "Vídeo trancado: falta o termo de ciência".
6. **Texto maior:** falta `html[data-texto-maior]` no `globals.css` e aplicar `aparencia.texto_maior` ao abrir.
7. **Cópia de segurança na demonstração:** conferir se `copia_fazer` aceita qualquer senha com 10+ caracteres
   (spec 016, decisão 5).
8. **Testes:** criar `scripts/testes/shell.test.mjs` (MEN-01, EQP-02, ENT-07) e atualizar `previa.test.mjs` (PRV-01 com
   as rotas novas; PRV-09 olhando a tela Viagens).

## O que foi feito na retomada (14:41 às 15:00)

- `src/components/ui/data-table.tsx`: o tipo do id virou genérico (texto ou número). Resolveu 4 erros de tipo na Equipe
  sem mexer em Motoristas e Veículos.
- `src/components/auth-gate.tsx`: saiu o import de `command-palette`, que não existe (item 2 acima).
- `src/components/ui/use-presence.ts`: o estado de "montado" é ajustado na renderização, não dentro do efeito (regra
  `react-hooks/set-state-in-effect`). O comportamento de abrir e fechar é o mesmo.
- `src/components/ui/toast.tsx`: o id do aviso sai da própria lista, sem ler ref na renderização.
- `src/lib/demo-backend.ts`: `let` que nunca muda virou `const`.
- `docs/painel/contrato-painel.md`: cópia do contrato dos agentes.

## Provas rodadas na retomada

- `npx tsc --noEmit` em `painel/app`: 0 erros.
- `npm test` em `painel/app`: 29 de 29 (script local, cadastros, guia e prévia).
- `tests/test_painel_desktop.py`: 13 de 13. `tests/test_painel_script_local.py`: 10 de 10.
- `npx eslint src scripts`: 0 erros e 1 aviso (`_senha` sem uso em `src/lib/demo-backend.ts:226`; é de propósito, tira a
  senha do objeto que vai para a tela).
- **Não rodado:** `npm run build`, `implantacao/painel/build.py`, `--verificar` com a interface nova e qualquer olhada
  nas telas. O atalho "RotaGuard Painel" da área de trabalho ainda abre o pacote antigo.

## Ordem para continuar

1. **Casca da interface**, itens 1 a 8 acima. O menu vem primeiro, porque sem ele as telas novas ficam escondidas.
2. **Testes do núcleo Python**, com os ajustes a conferir.
3. **Integração:** `npm run build`, `npm run lint`, `npm test`, todos os testes Python, `implantacao/painel/build.py` e
   `--verificar`. Capturas das telas sem janela visível, sem fechar o app do Matheus.
4. **Mostrar ao Matheus** as capturas abrindo as imagens (não por link relativo).

## Perguntas que continuam com o Matheus

- **Raspberry Pi 5 com 4 GB** no lugar do Pi 4: recomendação feita na tarde de 14/09, esperando confirmação para atualizar PRD e spec 005.
- **Perguntas das prévias:** a 1 ("contas em um computador por garagem ou em vários?") foi respondida: por enquanto tudo
  local. Conferir nas specs 014 a 016 se já há resposta para as outras três:
  - Consulta pode ver vídeos?
  - CPF opcional e prazos de 30 dias para vídeos e 5 anos para registros?
  - Viagem com revezamento de motoristas?

## Git

- Commit na branch `app-instalavel-em-andamento`, enviada ao GitHub.
- A `main` ficou em `18918ef`, porque o painel está pela metade. Levar para a `main` quando o Matheus pedir.
