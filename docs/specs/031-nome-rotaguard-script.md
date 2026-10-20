# Spec 031 · O app de teste passa a se chamar RotaGuard Script

| Campo | Valor |
|---|---|
| Status | implementada em 19 e 20/10/2026 (site, pacote, instalador, app, painel e central; o painel reconhece os dois nomes de processo e as duas pastas) |
| PRD | RF-27, RF-18 |
| Pedido | "troque o nome não quero que seja rotaguard test coloque rotaguard script" (19/10/2026) |
| Muda | specs 010, 018, 020, 023 e 026 (nome do app, do executável e do pacote) |

## Decisões

1. **Nome visível:** "RotaGuard Script" em toda tela, janela, texto legal, site (5 idiomas), painel, central,
   propriedades do `.exe` e atalho. "RotaGuard Teste" não aparece mais para quem usa.
2. **Arquivos distribuídos:** `RotaGuardScript.exe`, `RotaGuard-Script-windows-x64.zip`, `RotaGuard-Script-linux-x86_64.tar.gz`,
   instalador `rotaguard-script.iss`. O `.zip` antigo sai do site.
3. **Nomes internos do código ficam** (`caixa/app_teste.py`, `caixa/tela_teste/`, `implantacao/app-teste/`,
   `tests/test_app_teste.py`): trocar só o que a pessoa vê evita quebrar caminhos, CI e testes sem ganho para ela.
4. **Pasta de dados:** `%LOCALAPPDATA%\RotaGuard\Script` (Linux `$XDG_DATA_HOME/rotaguard/script`). Na primeira vez,
   se só existir a pasta antiga `Teste`, ela é movida para `Script` (eventos, resumos, trechos, conexão com a empresa);
   "Apagar dados" aceita as duas.
5. **Compatibilidade:** o painel reconhece o script aberto pelos dois nomes de processo (`RotaGuardScript.exe` e o
   antigo `RotaGuardTeste.exe`) e procura o anúncio nas duas pastas; a central aceita os dois nomes de programa.

## Critérios de aceite

| ID | Critério |
|---|---|
| NOM-01 | Nenhum texto visível do app, do site, do painel ou da central contém "RotaGuard Teste" (busca no `web/`, `messages/`, `out/` do painel e textos do servidor) |
| NOM-02 | O build gera `RotaGuardScript.exe` e `RotaGuard-Script-windows-x64.zip`, com as propriedades do `.exe` dizendo RotaGuard Script |
| NOM-03 | A área do PIN do site oferece "RotaGuard Script" com o arquivo novo; o arquivo antigo não está mais no site |
| NOM-04 | Pasta antiga `Teste` com dados → ao abrir, os dados aparecem na pasta `Script` e a antiga não existe mais; se as duas existirem, nada é sobrescrito |
| NOM-05 | O painel reconhece o script aberto com o nome novo e com o antigo |
| NOM-06 | Todos os testes Python, do painel e do site verdes; teste de fumaça do pacote |
