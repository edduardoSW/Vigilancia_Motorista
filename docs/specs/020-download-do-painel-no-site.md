# Spec 020 · Download do painel no site

| Campo | Valor |
|---|---|
| Status | implementada em 16/09/2026 (60 testes do site, `tsc`, lint e build sem erro; 49 conferências na tela com `area-de-download.mjs`, inclusive o download real do `.zip`; capturas olhadas em `docs/site/prints/2026-09-16-download-do-painel/`) |
| PRD | RF-25 (painel instalável), RF-32 (área do PIN com o download por plataforma), RF-33 (nada sem base no código) |
| Pedido | "coloque o downlaod do painel no site tambem" (16/09/2026). Responde a pergunta 3 da spec 013 ("O painel entra agora na área de download do site (PIN), ao lado do RotaGuard Teste?") |
| Specs irmãs | 010 (app de teste e área de download), 013 (pacote do painel), 014 (primeiro uso do painel) |
| Código | `site/src/content/downloads.ts`, `site/src/components/download-area.tsx`, `site/src/app/globals.css`, `site/messages/*.json` |
| Testes | `site/scripts/testes/downloads.test.mjs` (DPA-01 a DPA-04), `site/scripts/testes/i18n.test.mjs` (SITE-03); `site/scripts/testes/area-de-download.mjs` (DPA-05, com o site rodando) |

## Contexto

A área do PIN do site (`/app`) oferece só o RotaGuard Teste (spec 010). O pacote do painel já sai do
`implantacao/painel/build.py` como `RotaGuard-Painel-windows-x64.zip` (spec 013), mas só existe em
`build/painel/pacotes/` neste computador.

## Decisões

1. **Mesma página, dois blocos.** A área do PIN passa a ter o **RotaGuard Painel** e, abaixo, o **RotaGuard Teste**.
   - O painel vem primeiro porque é o produto da empresa; o teste é para experimentar a detecção.
   - Cada bloco tem nome, uma frase do que é, a lista de arquivos no mesmo formato de hoje e a instrução de uso.
   - O aviso de versão sem assinatura digital vale para os dois e fica no fim.
2. **Painel só para Windows**, com o arquivo portátil `RotaGuard-Painel-windows-x64.zip`, o mesmo nome que o
   `build.py` do painel gera.
   - O Linux do painel está fora de escopo na spec 013, então o site não lista um arquivo que nenhum build gera. A linha
     do fim passa a dizer que o painel para Linux e o app para celular estão em preparação.
   - O instalador `.exe` só sai com o Inno Setup e não é oferecido, como no app de teste.
3. **Mesma conferência por arquivo.** Antes de mostrar "Baixar", a página confere o arquivo com `HEAD` e mostra o
   tamanho; arquivo ausente aparece como "Em preparação". A situação é guardada **por arquivo**, não por plataforma,
   porque agora dois apps têm Windows.
4. **Arquivo servido pelo próprio site**, em `site/public/downloads/` (fora do git), copiado de
   `build/painel/pacotes/`. A cópia de 16/09 é o pacote conferido em 15/09 (19,1 MB, SHA-256
   `5a9603221892945860616c0b6034099d7e7bb4cb3b865f79cb860f5e7a3cba0d`); depois dele só mudou um documento.
5. **Primeiro uso explicado em uma frase:** na primeira abertura, "Ver demonstração" e criar o administrador (spec 014),
   e o aviso do WebView2 no Windows 10 (spec 013). Nada de texto a mais (erro 77 da vault).
6. **Pergunta frequente** sobre o acesso ao aplicativo passa a citar o painel para Windows.

## Comportamento

- **Ver os dois apps**
  - Dado o acesso com PIN, quando a pessoa abre a área do app, então vê o bloco RotaGuard Painel com Windows e, abaixo,
    o bloco RotaGuard Teste com Windows e Linux. Nenhum cita macOS.
- **Baixar o painel**
  - Dado o `RotaGuard-Painel-windows-x64.zip` em `/downloads`, quando a página confere o arquivo, então o Windows do
    painel mostra "Baixar" e o tamanho dele, sem misturar com o tamanho do Windows do app de teste.
  - Ao clicar em "Baixar", o navegador baixa `RotaGuard-Painel-windows-x64.zip`.
- **Arquivo que falta**
  - Dado um arquivo ausente em `/downloads` (hoje, o Linux do app de teste), então só aquele item aparece como
    "Em preparação"; os outros continuam com "Baixar".
- **Celular**
  - Dada uma tela de 320 ou 390 px, então a página não rola para o lado e nada dos blocos passa da borda.

## Critérios de aceite

| ID | Critério | Teste |
|---|---|---|
| DPA-01 | `downloads.ts` oferece o painel com `RotaGuard-Painel-windows-x64.zip` em `/downloads`, e o `implantacao/painel/build.py` gera esse mesmo nome | `downloads.test.mjs` |
| DPA-02 | Painel só com Windows (sem Linux nem Mac); app de teste continua com Windows e Linux | `downloads.test.mjs` |
| DPA-03 | Ordem painel → teste; cada arquivo com endereço único, que é a chave da situação na página | `downloads.test.mjs` |
| DPA-04 | Mensagens nos 5 idiomas com o bloco do painel (nome, frase, Windows e primeiro uso); o português não diz mais que o painel está em preparação, e a pergunta frequente cita o painel | `downloads.test.mjs` e `i18n.test.mjs` |
| DPA-05 | Na tela, com o arquivo copiado: os dois blocos, "Baixar" e tamanho certos por arquivo, "Em preparação" no que falta, clique em "Baixar" do painel baixando o arquivo com o mesmo SHA-256, sem rolagem lateral de 320 a 1440 px nos 5 idiomas e sem erro de JavaScript; capturas olhadas | `site/scripts/testes/area-de-download.mjs` (Edge sem janela, com o site rodando), capturas em `docs/site/prints/2026-09-16-download-do-painel/` |

## Fora de escopo

- Painel para Linux, instalador `.exe` e publicação do painel numa release do GitHub (spec 013).
- Assinatura digital e Microsoft Store.
- Publicar o site: `public/downloads/` fica fora do git, então um deploy feito pelo git não leva os arquivos.

## Riscos

- **Base externa:** com `NEXT_PUBLIC_ROTAGUARD_DOWNLOADS_BASE` apontando para a release do GitHub, o painel só
  aparece se o `.zip` dele estiver na mesma release, e hoje só existe workflow do app de teste.
- **Pacote velho no site:** a cópia em `public/downloads/` não se atualiza sozinha. Depois de cada build do painel, é
  preciso copiar o `.zip` de novo.
