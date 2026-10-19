# Spec 030 · Painel sem dados fictícios

| Campo | Valor |
|---|---|
| Status | aprovada (pedido do Matheus em 19/10/2026) → em implementação |
| PRD | RF-20, RF-21, RF-26, RF-40, RF-66 |
| Pedido | "no painel ainda tem muitos dados mockados a partir de agora remova esses dados mockados" (19/10/2026) |
| Muda | RF-26 ("modo local de demonstração com PIN e dados fictícios"), spec 012 (prévia com dados fictícios), spec 014 (ativar em demonstração) |
| Código | `painel/app/src/content/*`, `painel/app/src/lib/demo-backend.ts`, telas do painel, `painel/desktop/ponte.py`, `painel/desktop/cadastros.py` (`carregar_demonstracao`, `DEMO_EMPRESA`) |
| Testes | `tests/test_painel_*.py`, `painel/app/scripts/testes/*.test.mjs` (SDF-01 a SDF-12) |

## Contexto

O painel nasceu como prévia (spec 012) com viagens, momentos, motoristas, veículos e caixas fictícios, a faixa
"Prévia com dados fictícios" e a ativação "demonstração". Hoje já existem dados reais: os testes que chegam da
central (spec 026), o script aberto neste computador (spec 018), a câmera do aparelho (spec 025) e os cadastros que a
empresa faz. O painel instalado do Matheus foi ativado em 15/09 no modo demonstração.

## Decisões

1. **Nenhum dado fictício no painel instalado.** Viagens, momentos, motoristas, veículos, caixas, equipe e números do
   Início só mostram o que existe de verdade. Onde não há nada, **estado vazio** claro com o próximo passo (ex.:
   Viagens: "Nenhuma viagem ainda. As viagens aparecem quando uma caixa for conectada a este computador.").
2. **Sai a faixa "Prévia com dados fictícios"** e o indicador fixo "Caixa conectada 64%" do menu: o menu mostra a
   situação real ("Nenhuma caixa conectada"; "Central: conectado como …" quando houver).
3. **Início com números reais:** testes de hoje (central e script local), alertas dos testes, computadores
   "testando agora", motoristas e veículos cadastrados, CNH vencendo. Sem número inventado.
4. **Ativação sem modo demonstração:** a primeira tela cria a empresa (nome digitado) e o administrador, sem carregar
   nada; o arquivo da empresa continua como hoje.
5. **Migração automática do painel já ativado em demonstração** (o do Matheus): ao abrir, se `meta.modo =
   demonstracao`, o painel faz uma cópia `painel.db.antes-de-remover-demonstracao` e apaga só os registros da
   demonstração (motoristas, veículos, caixas, vínculos, termos e decisões que vieram de `carregar_demonstracao`,
   reconhecidos pelos `uid` da demonstração), mantém as contas, as preferências, as atividades e tudo que a pessoa
   cadastrou, registra "removeu os dados de demonstração" nas atividades e passa `modo` para `local`.
6. **Os dados fictícios só existem nos testes:** o conteúdo fictício e a demonstração em memória (`demo-backend.ts`)
   saem do pacote do app e viram fixture de teste (ex.: `scripts/testes/fixtures/`). Fora da janela do app (build,
   capturas) a interface usa um transporte vazio, não fictício.
7. **Telas que dependem de viagem importada da caixa** (relatório da viagem, momentos, vídeos da viagem) ficam com
   estado vazio até a importação da caixa existir (spec 004); as regras puras (formato, decisões, permissões) continuam
   com teste.
8. **Guia de uso:** imagens e textos que mostravam dados fictícios passam a falar dos estados reais (o capítulo de
   alertas continua, ele explica os tipos).

## Critérios de aceite

| ID | Critério |
|---|---|
| SDF-01 | O `out/` do build do app não contém nenhum nome, placa ou empresa da demonstração (lista de termos fictícios conferida por teste) |
| SDF-02 | A faixa "Prévia com dados fictícios" não existe mais |
| SDF-03 | Menu sem "Caixa conectada 64%": mostra a situação real |
| SDF-04 | Painel ativado do zero: Viagens, Motoristas, Veículos, Caixas mostram estado vazio com o próximo passo |
| SDF-05 | Início mostra só números reais (testes, alertas, computadores, cadastros) e zero quando não há |
| SDF-06 | Ativação não oferece demonstração; cria empresa e administrador sem carregar registros |
| SDF-07 | Migração: banco em `demonstracao` com cadastros da demonstração + 1 motorista cadastrado pela pessoa → depois de abrir, só o motorista da pessoa fica; contas e atividades intactas; cópia de segurança criada; `modo = local` |
| SDF-08 | Migração roda uma vez só e registra a atividade |
| SDF-09 | Testes à distância e Ao vivo continuam funcionando com dados reais (central e script local) |
| SDF-10 | Cadastrar motorista, veículo e equipe continua funcionando e aparece nas listas |
| SDF-11 | Todos os testes Python e do painel verdes; build, lint e `rotaguard_painel.py --verificar` sem erro |
| SDF-12 | Capturas das telas vazias e com dados reais em `docs/painel/capturas-2026-10-19-sem-demonstracao/`, conferidas |
