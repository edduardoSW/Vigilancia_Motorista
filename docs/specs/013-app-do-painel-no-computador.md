# Spec 013 · App do painel no computador (janela nativa)

| Campo | Valor |
|---|---|
| Status | aprovada (escolha do Matheus em 14/09/2026) → em implementação |
| PRD | RF-25 (app instalável; muda a casca do painel no computador de Tauri 2 para pywebview), RF-20, RF-21 e RF-22 (interface), RF-26 (demonstração com dados fictícios); RNF-10 (licenças), RNF-11 (qualidade) |
| Pedido | "esse dashboard não deve ser web, eu falei que não era para ser web mas sim um app instalável para usar no computador"; tecnologia escolhida: "Python + janela nativa" |
| Código | `painel/desktop/rotaguard_painel.py`, `painel/desktop/requirements.txt`, `implantacao/painel/` (`build.py`, `rotaguard-painel.spec`, `rotaguard-painel.iss`, `README.md`), `implantacao/app-teste/build.py` (`texto_versao_windows` com produto) |
| Testes | `tests/test_painel_desktop.py`; teste de fumaça do pacote (`--verificar`, janela oculta) em `implantacao/painel/build.py` |

## Contexto

A prévia do painel da empresa (spec 012) é uma exportação estática do Next.js em `painel/app/out/`. Em 14/09 ela foi
mostrada no navegador, e o Matheus respondeu: "esse dashboard não deve ser web, eu falei que não era para ser web mas
sim um app instalável para usar no computador". Na mesma conversa, escolheu **"Python + janela nativa"**: pywebview
com o WebView2 do Windows, PyInstaller e instalador, como o RotaGuard Teste (spec 010).

Esta spec cria a casca instalável: a mesma interface numa janela própria. A pessoa nunca vê navegador, aba, barra de
endereço ou servidor.

- Substitui a casca Tauri 2 da spec 007 (decisão 1) e o "RF-25 depois (Tauri)" da spec 012 **para o painel no
  computador com Windows**. Linux, Android e iPhone (PWA) continuam como estão na spec 007 até nova decisão.
- A interface (`painel/app/src`) não muda aqui: o redesenho segue na spec 012.

## Decisões técnicas

1. **Motor: pywebview 6.2.1 com WebView2** (o Edge Chromium embutido no Windows).
   - No Windows, o pywebview abre uma janela WinForms com o controle WebView2 pelo .NET Framework, usando o pythonnet
     3.1.0 (clr_loader 0.3.1, cffi 2.1.1). Todos têm pacote para o Python 3.14.
   - Versões estáveis conferidas com `pip index versions` em 14/09/2026 e travadas em `painel/desktop/requirements.txt`.
   - Neste computador: WebView2 Runtime 152.0.4191.66. O Windows 11 já traz o runtime; o Windows 10 pode precisar do
     instalador Evergreen da Microsoft (ver Riscos).
   - **Sem cair para o motor antigo:** sem WebView2, o pywebview troca sozinho para o MSHTML (Internet Explorer), que
     não roda a interface. O app confere o motor no evento `initialized` e recusa tudo que não seja `edgechromium`: a
     janela não abre e aparece o aviso para instalar o WebView2.
2. **Servidor local dentro do app.** A exportação usa endereços absolutos (`/_next/...`), então `file://` não funciona.
   - `ThreadingHTTPServer` da biblioteca padrão, só em `127.0.0.1` e em porta aleatória (porta 0). Sobe antes da
     janela e para quando ela fecha.
   - Sem `SO_REUSEADDR` e, no Windows, com `SO_EXCLUSIVEADDRUSE`, para outro programa não se ligar à mesma porta.
     Também não consulta o nome do computador ao ligar.
   - URL de pasta (`/`, `/veiculos/`, `/viagens/v-2240/`, e também `/veiculos` sem a barra) → `index.html` da pasta.
     A regra vale para qualquer rota da exportação, sem lista fixa de telas.
     Arquivo que não existe → tenta `<caminho>.html`. O resto → `404.html` com código 404.
   - `?consulta` e `#trecho` são ignorados; `%20` e os outros escapes são decodificados antes de procurar o arquivo.
   - **Travessia bloqueada:** segmento `.` ou `..` (também escrito `%2e%2e`), barra invertida, `:` (unidade de disco e
     fluxo alternativo do NTFS) e byte nulo respondem 404. O caminho final, já resolvido, precisa estar dentro da pasta
     da interface.
   - **Tipos MIME explícitos:** html, js, css, json, txt, woff2, svg, png e ico; desconhecido vai como
     `application/octet-stream`. Os payloads RSC (`.txt`) vão como `text/plain`, que o roteador do Next aceita no modo
     `export` (`next/dist/client/components/router-reducer/fetch-server-response.js`).
   - Só GET e HEAD, com `Cache-Control: no-cache` e `X-Content-Type-Options: nosniff`.
   - **Sem rede externa:** política de conteúdo só local (`default-src 'self'`, `connect-src 'self'`, fontes e imagens
     de `'self'` ou `data:`). Scripts e estilos em linha são permitidos porque a exportação do Next depende deles.
   - Sem registro de acesso: o executável de janela não tem console.
3. **Janela:**
   - título "RotaGuard" e ícone `implantacao/app-teste/rotaguard.ico` (no pacote, também dentro do `.exe`);
   - abre em 1440×900 e não encolhe abaixo de 1200×760;
   - no pacote, sem ferramentas de desenvolvedor, menu de contexto e atalhos do navegador (`debug=False`). `--depurar`
     liga isso só fora do pacote;
   - seleção de texto e zoom no padrão do pywebview (`text_select=False`, `zoomable=False`), sem ajuste próprio;
   - modo privado, que é o padrão do pywebview: a prévia não guarda cookies nem armazenamento local entre aberturas.
4. **Pasta da interface:** `pasta_interface()` devolve `painel/app/out` fora do pacote e `sys._MEIPASS/interface` no
   pacote.
5. **Verificação oculta `--verificar`** (teste de fumaça; nada aparece na tela):
   - cria a janela oculta (`hidden=True`: o pywebview mostra e esconde a janela com opacidade 0), espera o evento
     `loaded` e lê com `evaluate_js`:
     - `document.documentElement.lang`;
     - `document.body.innerText`;
     - só como informação, `Boolean(window.next)`, que mostra que os scripts rodaram com a política de conteúdo.
   - Imprime **uma linha JSON**: `ok`, `lang`, `aviso_dados_ficticios`, `scripts`, `caracteres`, `url`, `motor`,
     `segundos` e, quando falha, `erro`.
   - Sai com 0 só se `lang == "pt-BR"` e o texto tem "dados fictícios". A comparação do texto ignora maiúsculas, porque
     o `innerText` aplica `text-transform`. Qualquer outro caso sai com 1.
   - Limite rígido de 60 s: um vigia imprime o erro e encerra o processo com 1, mesmo que a janela trave.
6. **Empacotamento:**
   - PyInstaller 6.22.3 em modo pasta (`onedir`) `RotaGuardPainel`, sem console. Leva `painel/app/out` como
     `interface`, o ícone e as pastas `*.dist-info` (com as licenças) de pywebview, pythonnet, clr_loader, cffi,
     pycparser, bottle, proxy_tools e typing_extensions.
   - Propriedades do `.exe`: empresa "RotaGuard", produto "RotaGuard Painel", nome original `RotaGuardPainel.exe`, sem
     o nome do computador. Reaproveita `texto_versao_windows` do `implantacao/app-teste/build.py`, que ganhou os
     parâmetros de produto e executável (o padrão continua sendo o RotaGuard Teste).
   - `implantacao/painel/build.py`, em ordem:
     1. confere que a porta 3001 está livre (buildar com o `next dev` do painel rodando corrompe o `.next`);
     2. `npm run build` em `painel/app`;
     3. PyInstaller com `implantacao/painel/rotaguard-painel.spec`;
     4. confere `interface/index.html` dentro do pacote;
     5. roda `RotaGuardPainel.exe --verificar` (janela oculta);
     6. gera `RotaGuard-Painel-windows-x64.zip` e mostra tamanho e SHA-256.

     `--sem-build-interface` pula os passos 1 e 2 e empacota o `painel/app/out` que já existe (para quando a interface
     acabou de ser gerada ou está sendo reescrita). O build falha se não houver `painel/app/out/index.html`.
   - Instalador Inno Setup por usuário, sem pedir administrador, com atalho no menu Iniciar e ícone opcional na área de
     trabalho: `RotaGuard-Painel-windows-x64-setup.exe`. Só é compilado quando existe o `ISCC.exe`.
   - Versão: `ROTAGUARD_VERSAO` (tag `painel-vX.Y.Z`) ou o `version` de `painel/app/package.json`.
   - Saída em `build/painel/`, fora do git.

## Comportamento

- **Abrir o painel**
  - Dado um Windows com WebView2, quando a pessoa abre `RotaGuardPainel.exe`, então aparece a janela "RotaGuard" em
    1440×900 com o painel, sem navegador, aba ou barra de endereço.
  - Quando ela tenta diminuir a janela, então a janela para em 1200×760.
- **Navegar sem internet**
  - Dado o painel aberto e sem internet, quando a pessoa vai para outra tela (por exemplo, Veículos ou o relatório de
    uma viagem), então a tela abre dentro da mesma janela.
  - Dado um endereço que não existe, então aparece a página 404 da interface.
- **Fechar**
  - Dado o painel aberto, quando a pessoa fecha a janela, então o servidor local para junto e nada fica rodando.
- **Sem WebView2**
  - Dado um Windows sem o WebView2 Runtime, quando a pessoa abre o app, então aparece o aviso para instalar o WebView2
    e a interface não abre no motor antigo.
- **Tentativa de sair da pasta da interface**
  - Dado o servidor local, quando chega `/../segredo.txt` ou `/%2e%2e/segredo.txt`, então a resposta é a página 404 e
    nada fora da interface é lido.
- **Verificação do pacote**
  - Dado o pacote montado, quando o `build.py` roda `RotaGuardPainel.exe --verificar`, então nenhuma janela aparece na
    tela, sai uma linha JSON com `"ok": true` e o código é 0.
  - Dada uma interface que não carrega, quando passam 60 s, então sai a linha JSON com o erro e o código é 1.

## Critérios de aceite

| ID | Critério | Teste |
|---|---|---|
| PAC-01 | URL → arquivo, numa exportação de teste (sem depender das telas atuais): `/`, `/veiculos/`, `/veiculos` (sem barra), `/viagens/v-2240/`, `/_next/static/...`, payload RSC em pasta `$d$id` pedido com `%24`, `?consulta` e `#trecho` ignorados, `%20` e UTF-8 decodificados, `<caminho>.html` | `tests/test_painel_desktop.py` |
| PAC-02 | Travessia (`/../x`, `%2e%2e`, `..%2f`, `%5c`, `C:`, byte nulo) e arquivo faltando → 404 com a `404.html`; sem ela, 404 sem arquivo | `tests/test_painel_desktop.py` |
| PAC-03 | Tipos MIME: html, js, css, json, txt como `text/plain`, woff2, svg, png, ico; extensão desconhecida → `application/octet-stream` | `tests/test_painel_desktop.py` |
| PAC-04 | Servidor real em `127.0.0.1`, porta 0: `/` responde 200 `text/html` com a política de conteúdo só local; RSC como `text/plain`; caminho faltando → 404 com a página 404; HEAD sem corpo; `parar_servidor` fecha a porta e termina a thread | `tests/test_painel_desktop.py` |
| PAC-05 | `pasta_interface()` e `caminho_icone()` fora do pacote e no pacote (`sys._MEIPASS`) | `tests/test_painel_desktop.py` |
| PAC-06 | URL da janela sempre `http://127.0.0.1:<porta>/`, inclusive a que `main` passa para a janela | `tests/test_painel_desktop.py` |
| PAC-07 | Janela: título RotaGuard, 1440×900, mínimo 1200×760, oculta só no `--verificar`; no pacote `debug=False` mesmo com `--depurar`; ícone passado quando existe; o servidor responde com a janela aberta e para quando ela fecha | `tests/test_painel_desktop.py` (pywebview falso, sem janela) |
| PAC-08 | `--verificar`: uma linha JSON só; código 0 só com `lang` `pt-BR` e "dados fictícios"; código 1 com idioma errado, sem o aviso, página que não carrega ou interface ausente; janela destruída no fim | `tests/test_painel_desktop.py` (pywebview falso) |
| PAC-09 | Motor diferente de `edgechromium` (sem WebView2) é recusado: a verificação não roda, o aviso cita o WebView2 e o código é 1 | `tests/test_painel_desktop.py` (pywebview falso) |
| PAC-10 | Vigia de 60 s: ao estourar, imprime a linha de erro uma vez só e encerra com 1; cancelado, não faz nada | `tests/test_painel_desktop.py` |
| PAC-11 | Propriedades do `.exe` com RotaGuard, RotaGuard Painel e `RotaGuardPainel.exe`, sem o nome do computador, no formato do PyInstaller; as do RotaGuard Teste continuam iguais | `tests/test_painel_desktop.py` e `tests/test_app_teste.py` (APT-19) |
| PAC-12 | `build.py`: porta ocupada detectada; versão por `ROTAGUARD_VERSAO` ou `package.json`; nome `RotaGuard-Painel-windows-x64.zip`; `.spec` com a pasta `interface`, sem console e sem `debug`; `.iss` por usuário, com menu Iniciar, ícone opcional na área de trabalho, nome do instalador igual ao do `build.py` e `AppId` próprio | `tests/test_painel_desktop.py` |
| PAC-13 | `painel/desktop/requirements.txt` com todas as versões travadas (`==`) e iguais às instaladas no `.venv` | `tests/test_painel_desktop.py` |
| PAC-14 | Pacote: `npm run build` só com a porta 3001 livre; `_internal/interface/index.html` presente; `RotaGuardPainel.exe --verificar` com código 0 e `"ok": true`, sem janela visível; `.zip` com tamanho e SHA-256 | `implantacao/painel/build.py` |

## Fora de escopo

- **Versão Linux:** o pywebview precisa de GTK com WebKit2GTK (ou Qt) instalado no sistema. Fica para depois, com
  build e teste num Linux de verdade.
- **Assinatura digital:** sem certificado, o SmartScreen pede confirmação na primeira abertura.
- **Microsoft Store (pacote MSIX):** caminho futuro, como no app de teste (spec 010, decisão 12).
- Versão para Mac (decisão de 14/09/2026).
- Build no GitHub Actions: depois. O download na área do PIN do site entrou em 16/09/2026 (spec 020).
- Instalar o WebView2 pelo instalador (bootstrapper Evergreen): depois, se o Windows 10 der problema.
- Mudanças na interface (`painel/app/src`): redesenho da spec 012.
- Login, API, importação real da caixa e dados reais (specs 004 e 007).

## Riscos

- **Windows 10 sem WebView2:** o Windows 11 já vem com o runtime. O Windows 10 atualizado costuma recebê-lo junto do
  Edge, mas não é garantido. Sem ele, o app avisa e não abre a interface. Mitigação futura: bootstrapper Evergreen da
  Microsoft dentro do instalador.
- **.NET Framework:** o pywebview no Windows carrega o WinForms pelo .NET Framework 4.6.2 ou mais novo, que vem no
  Windows 10 e no 11. Uma instalação muito enxuta pode não ter.
- **Antivírus e SmartScreen:** executável sem assinatura pode ser barrado.
- **Política de conteúdo só local:** se o redesenho da interface puxar fonte, imagem ou script de fora, a janela
  bloqueia. O campo `scripts` do `--verificar` ajuda a perceber script barrado.
- **Pasta temporária do WebView2:** no modo privado, o pywebview cria o perfil do WebView2 numa pasta de `%TEMP%` e
  tenta apagá-la ao fechar. Na verificação de 14/09 ele não conseguiu apagar ("[WinError 32] O arquivo já está sendo
  usado por outro processo"), então pode sobrar uma pasta por abertura até o Windows limpar o `%TEMP%`.
- **Porta local:** enquanto o painel está aberto, outro programa do mesmo computador consegue ler
  `127.0.0.1:<porta>`. Hoje são só arquivos estáticos com dados fictícios. Quando houver dado real (spec 004), o
  servidor precisa de um segredo por sessão (token no endereço ou em cabeçalho).

## Perguntas para o Matheus

1. Quando o painel tiver dados reais, ele deve guardar sessão e preferências entre aberturas (sair do modo privado e
   usar `%LOCALAPPDATA%\RotaGuard\Painel`)?
2. Em computador sem WebView2 (Windows 10), basta o aviso ou o instalador já deve instalar o runtime?
3. ~~O painel entra agora na área de download do site (PIN), ao lado do RotaGuard Teste?~~ Respondida em 16/09: "coloque o
   downlaod do painel no site tambem" → spec 020.
4. ~~O PRD (RF-25) e a spec 007 ainda falam em Tauri 2.~~ Resolvido em 14/09: o PRD e a spec 007 foram atualizados
   para a janela em Python + WebView2, que o Matheus escolheu. Linux e Android seguem para depois.
