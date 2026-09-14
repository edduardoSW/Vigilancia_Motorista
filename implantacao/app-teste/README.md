# RotaGuard Teste

O script da caixa (`caixa/run_monitor.py`) empacotado para testar em qualquer computador Windows ou Linux, sem instalar
Python. Ele roda a detecção de sono e de uso de celular com a câmera do computador e toca o alarme, **sem servidor**.
Spec: `docs/specs/010-app-de-teste-do-script.md`.

## Baixar

Na área do cliente do site (PIN), que serve os arquivos em `/downloads`. Os arquivos também saem na release do
repositório quando o workflow roda:

| Sistema | Arquivo |
|---|---|
| Windows 10/11 64 bits | `RotaGuard-Teste-windows-x64.zip` (portátil: extraia e abra `RotaGuardTeste.exe`); instalador `RotaGuard-Teste-windows-x64-setup.exe` só na release |
| Linux x86_64 | `RotaGuard-Teste-linux-x86_64.tar.gz` |

Não há versão para Mac (decisão de 14/09/2026). No futuro, o Windows vai pela Microsoft Store (pacote MSIX), que assina
o app e tira o aviso do SmartScreen.

É uma versão de teste sem assinatura digital, então o sistema pede confirmação na primeira abertura:

- **Windows:** extraia o `.zip` antes de abrir. Em "O Windows protegeu o computador", clique em **Mais informações →
  Executar assim mesmo**. O `RotaGuardTeste.exe` precisa ficar junto da pasta `_internal`.
- **Linux:** `tar xzf RotaGuard-Teste-linux-x86_64.tar.gz && ./RotaGuardTeste/RotaGuardTeste`. Precisa de ambiente
  gráfico, e o som do alarme usa `aplay`, `paplay` ou `pw-play`.

## Usar

1. Abra o **RotaGuard Teste**.
2. Deixe a câmera em **Automática** (usa a primeira que abrir e mandar imagem), escolha outra ("Câmera 2") ou um
   **vídeo gravado**. Deixe marcadas as opções que quer testar: detecção de celular, som do alarme e calibração rápida
   (1 a 2 min).
3. Clique em **Iniciar teste**. A tela mostra quando a câmera foi encontrada e quando o teste começou.
4. Na janela da câmera: **Q** ou **Esc** encerra, **C** recalibra. Fechar a janela no X também encerra.

O microssono (olhos fechados por 1 s) vale desde o começo. Os níveis de sonolência começam depois da calibração.
Com vídeo gravado, o teste termina sozinho no fim do vídeo.

Se nenhuma câmera mandar imagem em 15 s (desconectada ou em uso por Teams, Zoom ou navegador), o teste termina e a tela
explica o que conferir. O monitor sai com o código 3 (`--espera-camera`).

O registro fica em `registro-teste.log`, na pasta de dados, que abre pelo botão **Abrir pasta de registros**:

- Windows: `%LOCALAPPDATA%\RotaGuard\Teste`;
- Linux: `~/.local/share/rotaguard/teste`.

## Privacidade, LGPD e termos

O botão **Privacidade, LGPD e termos**, na tela de início, abre as abas Privacidade, LGPD, Termos de uso e Licenças.
- Não é preciso aceitar nada para usar o app.
- Na mesma janela ficam **Abrir pasta de dados** e **Apagar dados deste computador**.
- Os textos estão em `caixa/textos_legais.py` e descrevem o que o app faz de verdade: se mudar o que ele grava ou
  envia, atualize os textos e os testes APT-21.
- É rascunho técnico: revisar com advogado antes de oferecer a clientes.
- Razão social, CNPJ e canal de privacidade ainda precisam ser definidos (`CONTATO_PRIVACIDADE`).

## Montar

Com as dependências da caixa instaladas, em Windows ou Linux:

```bash
python -m pip install -r caixa/requirements.txt pyinstaller==6.22.3
python implantacao/app-teste/build.py            # PyInstaller + testes do pacote + pacote do sistema atual
python implantacao/app-teste/build.py --sem-instalador   # Windows sem Inno Setup: só o .zip
```

- **Saída:** `build/app-teste/pacotes/` (fora do git).
- **Teste de fumaça:** roda o executável empacotado num vídeo sintético, com `--no-window --sem-servidor`. Ele exige
  código 0, "Monitoramento finalizado" no registro, nenhum Traceback e os modelos de celular e mãos carregados.
- **Teste sem câmera:** câmera 9 inexistente precisa sair com código 3, rápido, sem Traceback e com o aviso no registro.
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
| `rotaguard-teste.spec` | PyInstaller: modelos em `vision/models`, MediaPipe completo, ícone, propriedades do `.exe` e `THIRD_PARTY_NOTICES.md` |
| `build.py` | monta, testa e empacota (recusa macOS) |
| `rotaguard-teste.iss` | instalador Inno Setup por usuário (sem administrador) |
| `gerar_icone.py` | gera `rotaguard.ico` e `rotaguard.png` |

## Limites

- Sem versão para Mac.
- Não existe versão para Android nem para iPhone: o script é Python. O teste no celular vem com o app do painel
  (spec 007).
- É protótipo em validação: os limites ainda serão ajustados com gravações reais, e não é diagnóstico.
