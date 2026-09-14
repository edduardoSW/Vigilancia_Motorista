# RotaGuard Painel

O painel da empresa (a interface de `painel/app`) numa **janela própria do Windows**: sem navegador, sem barra de
endereço e sem servidor à vista. A janela é do pywebview com o WebView2 do Windows; a interface vai dentro do programa e
é servida só para ele, em `127.0.0.1`. Spec: `docs/specs/013-app-do-painel-no-computador.md`.

Por enquanto o painel mostra a prévia com **dados fictícios** (spec 012): não tem login, não fala com servidor e não
guarda nada entre aberturas.

## Baixar

| Sistema | Arquivo |
|---|---|
| Windows 10/11 64 bits | `RotaGuard-Painel-windows-x64.zip` (portátil: extraia e abra `RotaGuardPainel.exe`); instalador `RotaGuard-Painel-windows-x64-setup.exe` quando o build tiver o Inno Setup |

Os arquivos saem do build em `build/painel/pacotes/`; ainda não estão na área de download do site. Sem versão para
Linux e Mac nesta etapa.

É uma versão sem assinatura digital:

- Extraia o `.zip` antes de abrir. O `RotaGuardPainel.exe` precisa ficar junto da pasta `_internal`.
- Em "O Windows protegeu o computador", clique em **Mais informações → Executar assim mesmo**.
- O Windows 11 já traz o **WebView2 Runtime**. No Windows 10, se o app avisar que ele falta, instale o WebView2 Runtime
  (versão Evergreen) pelo site da Microsoft e abra o painel de novo.

O instalador é por usuário (não pede administrador), cria o atalho no menu Iniciar e oferece o ícone na área de
trabalho.

## Usar

1. Abra o **RotaGuard Painel** pelo menu Iniciar ou pelo `RotaGuardPainel.exe`.
2. A janela abre em 1440×900 e pode ser maximizada; menor que 1200×760 ela não fica.
3. Navegue pelas telas normalmente: a interface vai dentro do programa e não depende de internet.
4. Feche a janela para sair. O servidor interno para junto.

## Montar

No Windows, com o `.venv` do projeto (Python 3.14) e o Node.js para gerar a interface:

```powershell
.venv\Scripts\python.exe -m pip install -r painel/desktop/requirements.txt
.venv\Scripts\python.exe implantacao/painel/build.py                        # interface + pacote + verificação + .zip
.venv\Scripts\python.exe implantacao/painel/build.py --sem-build-interface  # empacota o painel/app/out que já existe
```

O `build.py` faz, em ordem:

1. confere que a porta 3001 está livre (buildar com o `next dev` do painel rodando corrompe o `.next`);
2. roda `npm run build` em `painel/app` (os passos 1 e 2 são pulados com `--sem-build-interface`);
3. roda o PyInstaller com `rotaguard-painel.spec` e confere `_internal/interface/index.html`, o ícone e as licenças no
   pacote;
4. roda `RotaGuardPainel.exe --verificar`: janela oculta, uma linha JSON e código 0 só se a página carregou com
   `lang="pt-BR"` e o aviso "dados fictícios" (limite de 60 s);
5. gera `build/painel/pacotes/RotaGuard-Painel-windows-x64.zip` e mostra tamanho e SHA-256. Com o Inno Setup
   instalado, gera também o instalador.

Outras opções: `--sem-fumaca` (pula a verificação; não usar em entrega), `--sem-instalador` e `--so-empacotar`
(reaproveita o `build/painel/dist`).

Para abrir direto do código, sem empacotar: `.venv\Scripts\python.exe painel/desktop/rotaguard_painel.py`
(`--depurar` liga as ferramentas de desenvolvedor, só fora do pacote). Testes:
`.venv\Scripts\python.exe tests/test_painel_desktop.py`.

| Arquivo | Para quê |
|---|---|
| `painel/desktop/rotaguard_painel.py` | janela, servidor local e verificação `--verificar` |
| `painel/desktop/requirements.txt` | versões travadas do pywebview, pythonnet e PyInstaller |
| `rotaguard-painel.spec` | PyInstaller: interface em `_internal/interface`, ícone, propriedades do `.exe` e licenças |
| `build.py` | monta, verifica e empacota |
| `rotaguard-painel.iss` | instalador Inno Setup por usuário |

## Limites

- Só Windows. No Linux, o pywebview precisa de GTK com WebKit2GTK (ou Qt): fica para depois.
- Sem assinatura digital; a Microsoft Store (pacote MSIX) é o caminho futuro.
- A interface precisa ser 100% local: a janela bloqueia fonte, imagem ou script vindos de fora.
