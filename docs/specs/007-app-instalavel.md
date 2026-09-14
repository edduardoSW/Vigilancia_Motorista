# Spec 007 · App instalável (painel + teste de câmera)

| Campo | Valor |
|---|---|
| Status | rascunho |
| PRD | RF-23, RF-24, RF-25, RF-26 (e a interface de RF-20 a RF-22, detalhados na spec 004) |
| Decisão do Matheus (11/09/2026) | "Painel + teste de câmera"; "Instaladores + PWA" |
| Código | `painel/webapp/` (interface), `painel/app/` (empacotamento Tauri 2, novo), `.github/workflows/app.yml` (novo) |

## Contexto

O painel existe como PWA em HTML, CSS e JS sem build (`painel/webapp/`), com modo servidor (API FastAPI) e modo local
(dados fictícios e PIN).

- **Formato:** o Matheus não quer o painel "na web". Ele quer **app instalável em qualquer aparelho**, baixado no site
  por quem entra com o PIN.
- **Visual:** o "Cabine noturna" continua rejeitado. O redesenho segue a linguagem do site (concreto e asfalto, Sofia
  Sans e B612), com prévia aprovada antes de codar visual.

## Decisões técnicas

1. **Um código de interface só.** `painel/webapp/` continua sendo a interface. O app nativo é uma casca **Tauri 2**
   que carrega esses arquivos empacotados (funciona sem internet).
   - Rust só existe na casca e nas funções nativas: descoberta da caixa na rede, arquivo e impressão.
2. **Plataformas:**
   - Windows: instalador NSIS `.exe`; no futuro, também pela Microsoft Store (pacote MSIX), que assina o app;
   - Linux: `.AppImage` e `.deb`;
   - Android: `.apk`;
   - iPhone e iPad: **PWA pelo Safari**. A Apple não permite instalar fora da App Store sem conta de desenvolvedor.
   - **Sem Mac:** "deixe download apenas para Windows e Linux, pois não terá para Mac" (14/09/2026).
3. **Build só no GitHub Actions** (`tauri-apps/tauri-action` e o CLI do Tauri para Android).
   - Este computador não tem Rust nem Android SDK, e não é do Matheus: nada de toolchain pesada instalada aqui.
   - Os arquivos vão para uma release de rascunho quando houver tag `app-v*`.
   - O site aponta para a pasta da release por `NEXT_PUBLIC_ROTAGUARD_DOWNLOADS_BASE`.
4. **Modo de teste de câmera** no app, com `@mediapipe/tasks-vision` (Apache-2.0) empacotado localmente, sem CDN.
   - As regras de olho e sonolência são as mesmas do Python: os mesmos limiares e as mesmas sequências de teste.
   - A equivalência é provada por arquivos-ouro: a mesma série sintética de medidas passa pelo Python e pelo JS e os
     eventos precisam coincidir.
5. **Versões:** Tauri CLI e crates na última estável conferida no registro na hora (`npm view @tauri-apps/cli
   dist-tags`, `cargo search tauri`), travadas no `Cargo.lock` e no `package-lock.json`.

## Comportamento

- **Instalar no Windows**
  - Dado um gestor com o PIN, quando entra no site e baixa o instalador de Windows, então instala o app RotaGuard, que
    abre sem navegador e sem barra de endereço.
- **Uso sem internet**
  - Dado o app instalado e sem internet, quando é aberto, então mostra o modo local de demonstração e o que foi
    importado da caixa (spec 004), sem quebrar.
- **Teste de câmera**
  - Dado o modo de teste, quando a pessoa fecha os olhos por 1 s diante da câmera do notebook ou do celular, então o
    app toca o alarme e registra `microssono`, igual ao script.
- **iPhone**
  - Dado um iPhone, quando a pessoa abre o link do app no Safari, então aparece a instrução "Compartilhar → Adicionar à
    Tela de Início" e o app abre em tela cheia.
- **Release**
  - Dada uma tag `app-v0.1.0`, quando o workflow roda, então a release de rascunho recebe os 4 arquivos com nomes
    fixos e checksums SHA-256.

## Critérios de aceite

| ID | Critério | Como provar |
|---|---|---|
| APP-01 | `painel/app/src-tauri/tauri.conf.json` válido: identificador `br.com.rotaguard.app` (a confirmar), janela sem barra de endereço, CSP sem `unsafe-inline` para script, arquivos do `painel/webapp` empacotados | teste que valida o JSON com o schema do Tauri 2 |
| APP-02 | Workflow `app.yml` com matriz Windows e Linux e job Android, sem macOS; artefatos com os nomes que o site espera (`RotaGuard-windows-x64-setup.exe`, `RotaGuard-linux-x86_64.AppImage`, `RotaGuard-linux-x86_64.deb`, `RotaGuard-android.apk`) e `SHA256SUMS.txt` | teste que lê o YAML e confere matriz e nomes; execução real no GitHub |
| APP-03 | PWA: `manifest.webmanifest` com nome RotaGuard, ícones 192, 512 e maskable, `display: standalone`; service worker que guarda só a casca, nunca dados; página de instrução do iPhone | teste de manifesto e do service worker |
| APP-04 | Ícones e nome RotaGuard em todas as plataformas (sem "DriveSafe" visível ao usuário) | busca automatizada nas strings visíveis |
| APP-05 | Modo de teste no JS: abertura do olho, piscada (começa em 0,50, termina em 0,60), microssono 1 s, sono 3 s, sem resposta 6 s, PERCLOS P80 (só fechamentos acima de 250 ms), bocejo (boca ≥ 0,45 por 2 s), cabeceio ≥ 15°, rosto ausente 10 s | testes JS com as mesmas sequências dos testes Python |
| APP-06 | Equivalência Python ↔ JS: arquivos-ouro gerados pelo Python (medidas por quadro → eventos) passam no JS com os mesmos eventos e tempos (tolerância de 1 quadro) | teste cruzado |
| APP-07 | Alarme sonoro no teste de câmera por WebAudio, com o mesmo padrão da sirene da caixa | teste de unidade do gerador de padrão |
| APP-08 | Sem dado real no modo local: o PIN só abre dados fictícios, com aviso visível | teste existente do modo local, adaptado |
| APP-09 | Assinatura e segredos: nenhum certificado, keystore ou chave no repositório; o workflow lê de `secrets` e, sem eles, gera artefato não assinado com aviso | teste que procura chave e keystore no repositório; revisão do YAML |

## Fora de escopo agora

- App nativo de iPhone na App Store.
- Versão para Mac (decisão de 14/09/2026).
- Assinatura de código paga no Windows: sem ela, o SmartScreen mostra aviso na primeira abertura. O caminho escolhido
  para o futuro é publicar na Microsoft Store (pacote MSIX), que assina o app (14/09/2026).
- Redesenho visual completo: vem depois da prévia aprovada pelo Matheus. Até lá, só troca de nome, ícone e tokens
  básicos.

## Perguntas para o Matheus

1. Identificador do app (padrão reverso de domínio, por exemplo `br.com.rotaguard.app`), que depende do domínio.
2. Onde publicar os arquivos: release do GitHub neste repositório (o dono é edduardoSW) ou outro lugar?
3. Assinatura:
   - conta de desenvolvedor Apple só se um dia houver app nativo de iPhone?
   - Windows: Microsoft Store (MSIX) no futuro; até lá, instalador sem assinatura?
   - quem guarda a keystore do Android?
4. O token usado no push tem permissão para criar workflows (`workflow`) e o repositório tem Actions habilitado?

## Riscos

- **Push do workflow:** sem permissão `workflow` no token, o push é recusado.
- **Build de Android** só é verificável rodando no GitHub.
- **Modo de teste no celular:** o desempenho do MediaPipe no navegador de celulares antigos pode ser baixo; medir.
- **Divergência entre Python e JS:** mitigada pelos arquivos-ouro (APP-06).
