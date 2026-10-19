# RotaGuard Script

O script da caixa (`caixa/run_monitor.py`) empacotado para testar em qualquer computador Windows ou Linux, sem instalar
Python. Ele roda a detecção de sono e de uso de celular com a câmera do computador e toca o alarme, **sem servidor**.
Specs: `docs/specs/010-app-de-teste-do-script.md` (pacote e download) e `023-nova-tela-do-app-de-teste.md` (tela).

## Baixar

Na área do cliente do site (PIN), que serve os arquivos em `/downloads`. Os arquivos também saem na release do
repositório quando o workflow roda:

| Sistema | Arquivo |
|---|---|
| Windows 10/11 64 bits | `RotaGuard-Script-windows-x64.zip` (portátil: extraia e abra `RotaGuardScript.exe`); instalador `RotaGuard-Script-windows-x64-setup.exe` só na release |
| Linux x86_64 | `RotaGuard-Script-linux-x86_64.tar.gz` |

Não há versão para Mac (decisão de 14/09/2026). No futuro, o Windows vai pela Microsoft Store (pacote MSIX), que assina
o app e tira o aviso do SmartScreen.

É uma versão de teste sem assinatura digital, então o sistema pede confirmação na primeira abertura:

- **Windows:** extraia o `.zip` antes de abrir. Em "O Windows protegeu o computador", clique em **Mais informações →
  Executar assim mesmo**. O `RotaGuardScript.exe` precisa ficar junto da pasta `_internal`.
- **Linux:** `tar xzf RotaGuard-Script-linux-x86_64.tar.gz && ./RotaGuardScript/RotaGuardScript`. Precisa de ambiente
  gráfico, e o som do alarme usa `aplay`, `paplay` ou `pw-play`.

## Usar

1. Abra o **RotaGuard Script**. A janela é uma página HTML (pywebview com o WebView2 do Windows; sem ele, abre no
   navegador padrão) servida só para este computador, em `127.0.0.1`, com uma chave nova a cada abertura.
2. Deixe a câmera em **Automática** (usa a primeira que abrir e mandar imagem), escolha outra da lista (a tela procura
   as câmeras 1 a 5 e diz se estão livres ou em uso) ou um **vídeo gravado**, que toca no tempo dele.
3. Escolha o que medir: celular e mãos, frequência cardíaca (estimativa pela câmera, não é medida médica), som do
   alarme, calibração rápida (1 a 2 min) e câmera infravermelha.
4. Clique em **Iniciar teste**. A tela do teste mostra o vídeo com a malha do rosto, o nível de risco, olhos, coração,
   cabeça, boca, celular e mãos, atenção, desempenho e a linha do tempo dos eventos.
5. Atalhos: **Q** ou **Esc** encerra, **C** recalibra, **M** troca a malha (completa, pontos, essencial, desligada),
   **S** liga ou desliga o som, **F** tela cheia.
6. Ao encerrar, aparece o resumo (duração, eventos, PERCLOS, piscadas e frequência cardíaca). **Salvar resumo** grava
   JSON e CSV em `resumos/`, na pasta de dados.

O microssono (olhos fechados por 1 s) vale desde o começo. Os níveis de sonolência começam depois da calibração.
Com vídeo gravado, o teste termina sozinho no fim do vídeo.

Se nenhuma câmera mandar imagem em 15 s (desconectada ou em uso por Teams, Zoom ou navegador), a tela explica o que
conferir e o app continua aberto para tentar de novo.

A janela antiga do OpenCV continua: `RotaGuardScript.exe --janela-opencv` (Q ou Esc encerra, C recalibra, M malha).

O registro fica em `registro-teste.log`, na pasta de dados (botão **Abrir pasta** na tela de início):

- Windows: `%LOCALAPPDATA%\RotaGuard\Teste`;
- Linux: `~/.local/share/rotaguard/teste`.

## Enviar para a empresa (spec 026)

Para uma empresa ver os testes deste computador no painel dela:

1. No painel, a empresa gera um código em "Gerar código para outro computador" (8 letras e números, vale 30 min, uso
   único).
2. Na tela de início do RotaGuard Script, em **Enviar para a empresa**, digite o código (com ou sem hífen) e clique em
   **Conectar**. O endereço padrão é `https://rotaguard.acexpartners.com.br` ("Outro endereço da central" troca).
3. Conectado e com **Enviar para a empresa** ligado, cada teste manda: o sinal de que o teste está aberto (com o nível
   de risco), os eventos, o resumo do teste e **trechos de vídeo** de 16 s (8 s antes e 8 s depois) dos alertas, com a
   malha e a hora na imagem. A frequência cardíaca nunca sai do computador.
4. Os trechos só são gravados com o app conectado e o envio ligado. Ficam em `trechos/` na pasta de dados (WebM VP8;
   `.rgclip` se o VP8 não abrir) e aparecem no resumo com player.
5. Tudo vai antes para a fila em `central/fila.db`: sem internet, fica na fila e sobe depois. Desligar o envio para na
   hora; **Desconectar este computador** apaga o token (`central.json`). Se a empresa desconectar o computador no
   painel, a tela mostra "A empresa desconectou este computador" e para, sem apagar nada local.

## Privacidade, LGPD e termos

O botão **Privacidade, LGPD e termos**, na tela de início, abre as abas Privacidade, LGPD, Termos de uso e Licenças.
- Não é preciso aceitar nada para usar o app.
- Na mesma janela ficam **Abrir pasta de dados** e **Apagar dados deste computador**.
- Os textos estão em `caixa/textos_legais.py` e descrevem o que o app faz de verdade: se mudar o que ele grava ou
  envia, atualize os textos e os testes APT-21.
- É rascunho técnico: revisar com advogado antes de oferecer a clientes.
- Razão social, CNPJ e canal de privacidade ainda precisam ser definidos (`CONTATO_PRIVACIDADE`).

## Montar

Com as dependências do app de teste instaladas (as da caixa mais o pywebview), em Windows ou Linux:

```bash
python -m pip install -r caixa/requirements-app-teste.txt pyinstaller==6.22.3
python implantacao/app-teste/build.py            # PyInstaller + testes do pacote + pacote do sistema atual
python implantacao/app-teste/build.py --sem-instalador   # Windows sem Inno Setup: só o .zip
```

- **Saída:** `build/app-teste/pacotes/` (fora do git).
- **Teste de fumaça:** roda o executável empacotado num vídeo sintético, com `--no-window --sem-servidor`. Ele exige
  código 0, "Monitoramento finalizado" no registro, nenhum Traceback e os modelos de celular e mãos carregados.
- **Teste sem câmera:** câmera 9 inexistente precisa sair com código 3, rápido, sem Traceback e com o aviso no registro.
- **Teste da tela (TEL-16):** `RotaGuardScript.exe --verificar-tela` sobe o servidor sem janela e confere a página, o
  CSS, o JS, o `/estado` e o 403 sem a chave. O build também falha se `_internal/tela_teste/web` faltar.
- **Licenças:** o pacote leva o `THIRD_PARTY_NOTICES.md` e as pastas `*.dist-info` das bibliotecas, com os textos das
  licenças (a da OpenCV cobre a FFmpeg, LGPL 2.1). O build falha se faltarem.
- **Propriedades:** no Windows, o `.exe` sai com empresa e produto RotaGuard (`propriedades-windows.txt` gerado pelo
  `build.py`). O registro não escreve o nome do computador.
- **Site:** copie os pacotes para `site/public/downloads/` (fora do git, porque o GitHub recusa arquivo acima de
  100 MB). A área de download confere cada arquivo e mostra "Em preparação" para o que faltar.

  ```powershell
  New-Item -ItemType Directory -Force site/public/downloads
  Copy-Item build/app-teste/pacotes/* site/public/downloads/
  ```
- **Release:** `git tag teste-v0.1.0 && git push origin teste-v0.1.0`. O workflow `app-teste.yml` monta Windows e
  Linux, passa cada pacote pelos testes e publica a release com `SHA256SUMS.txt`. Para o site baixar da release, use
  `NEXT_PUBLIC_ROTAGUARD_DOWNLOADS_BASE=https://github.com/edduardoSW/Vigilancia_Motorista/releases/latest/download`.

| Arquivo | Para quê |
|---|---|
| `rotaguard-script.spec` | PyInstaller: modelos em `vision/models`, página da tela em `tela_teste/web`, MediaPipe completo, pywebview, ícone, propriedades do `.exe` e `THIRD_PARTY_NOTICES.md` |
| `build.py` | monta, testa e empacota (recusa macOS) |
| `rotaguard-script.iss` | instalador Inno Setup por usuário (sem administrador) |
| `gerar_icone.py` | gera `rotaguard.ico` e `rotaguard.png` |

## Limites

- Sem versão para Mac.
- Não existe versão para Android nem para iPhone: o script é Python. O teste no celular vem com o app do painel
  (spec 007).
- É protótipo em validação: os limites ainda serão ajustados com gravações reais, e não é diagnóstico.
