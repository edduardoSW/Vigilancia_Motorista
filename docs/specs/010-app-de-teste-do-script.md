# Spec 010 · App de teste do script (download para outros computadores)

| Campo | Valor |
|---|---|
| Status | aprovada (pedido do Matheus em 14/09/2026) → em implementação |
| PRD | RF-27 (novo), RF-01, RF-02, RF-04; RNF-10 (licenças) |
| Pedido | "quero que faça a questão de download agora para eu poder testar em outros computadores; a parte do dashboard da empresa e a conexão com esse script faça depois" |
| Código | `caixa/app_teste.py`, `caixa/textos_legais.py`, `caixa/run_monitor.py`, `caixa/vision/camera.py`, `caixa/vision/driver_monitor.py`, `implantacao/app-teste/`, `.github/workflows/app-teste.yml`, `site/src/content/downloads.ts`, `site/src/components/download-area.tsx` |
| Testes | `tests/test_app_teste.py`, `site/scripts/testes/downloads.test.mjs`, testes de fumaça e sem câmera do pacote em `implantacao/app-teste/build.py` |

## Contexto

O script da câmera (`caixa/run_monitor.py`) só roda com Python e dependências instaladas. O Matheus quer baixar pelo
site (área do PIN) e testar em outros computadores **sem instalar nada além do app**.

O painel da empresa e a conexão do script com ele ficam para depois (spec 007 continua valendo para o painel). Este
app roda **o mesmo código Python** do script, empacotado. Não é uma reimplementação: o que for testado é o que a caixa
roda.

## Decisões técnicas

1. **PyInstaller 6.22.3** (suporta Python 3.14) em modo pasta (`onedir`): abre mais rápido e é menos barrado por
   antivírus que o arquivo único. Os modelos de `caixa/vision/models/` vão dentro do pacote, sem download ao abrir.
2. **Tela de início em Tkinter** (vem com o Python): câmera (automática por padrão) ou vídeo, detecção de celular, som
   do alarme, calibração rápida e câmera infravermelha.
   - O monitoramento roda num **processo separado** do mesmo executável (`--monitor`), para a janela do OpenCV e a do
     Tk não disputarem a linha principal.
3. **Sem servidor:** nova opção `--sem-servidor` no `run_monitor.py`. Não inicia a sincronização e os eventos ficam na
   fila local. Sem ela, o script tentaria `localhost:8000` e encheria o registro de avisos.
4. **Dados e registro** na pasta do usuário, nunca ao lado do programa (a pasta de instalação pode ser só leitura):
   - Windows: `%LOCALAPPDATA%\RotaGuard\Teste`;
   - Linux: `$XDG_DATA_HOME/rotaguard/teste` (padrão `~/.local/share/rotaguard/teste`).

   O registro do teste fica em `registro-teste.log`.
5. **Plataformas: só Windows e Linux.**

   | Plataforma | Formato | Arquivo |
   |---|---|---|
   | Windows | Versão portátil (é a que o site oferece) | `RotaGuard-Teste-windows-x64.zip` |
   | Windows | Instalador Inno Setup por usuário, sem pedir administrador (só no CI) | `RotaGuard-Teste-windows-x64-setup.exe` |
   | Linux | pasta compactada | `RotaGuard-Teste-linux-x86_64.tar.gz` |

   **Sem Mac**, por decisão do Matheus em 14/09/2026: "deixe download apenas para Windows e Linux, pois não terá para
   Mac". O `build.py` recusa rodar no macOS.
6. **Build no GitHub Actions** (`app-teste.yml`), em Windows e Linux. Quando é enviada uma tag `teste-v*`, o workflow
   publica uma release com os arquivos e o `SHA256SUMS.txt`.
7. **Fim de vídeo:** com arquivo de vídeo como fonte, o monitoramento termina quando o vídeo acaba (antes ele reabria e
   recomeçava sem parar). Câmera ao vivo continua tentando reabrir como antes. Isso também permite o teste de fumaça
   automático do pacote.
8. **Nome visível RotaGuard** na janela da câmera e nas mensagens. Os identificadores `DRIVESAFE_*` não mudam.
9. **Câmera automática e sem fechar "sem lógica"** (retorno do teste de 14/09, abaixo):
   - `--camera auto` testa os índices 0 a 5 e usa a primeira câmera que abre **e manda imagem**. Câmera aberta sem
     imagem (em uso por outro programa) passa para a próxima. É o padrão do app.
   - No Windows, `OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS=0`. Medido neste computador em 14/09:
     - com as transformações de hardware do Media Foundation, a webcam levava 5,5 s para abrir e mais 10,6 s para
       ajustar 640x480;
     - sem elas, 0,5 s + 0,8 s até o primeiro quadro, com os mesmos ~30 fps;
     - DirectShow abriu em 1,7 s, mas a 15 fps.
   - `--espera-camera N`: sem imagem por N s (nunca chegou ou parou), o monitor sai com **código 3**. Câmera escolhida
     que nem abre sai com código 3 na hora. O app usa 15 s; a caixa continua com 0 (tenta reabrir para sempre).
   - A tela de início traduz o código 3 numa mensagem ("Nenhuma câmera respondeu…").
   - A tela acompanha o registro e mostra em que ponto está: procurando a câmera → câmera encontrada → teste em
     andamento.
   - Janela da câmera: fechar no X encerra o teste. Também encerram Esc, `q` e `Q`; `c` e `C` recalibram. O X só é
     aceito depois de o OpenCV informar a janela visível: onde a propriedade não existe, só as teclas encerram.
10. **Propriedades RotaGuard, sem o nome do computador** (pedido de 14/09):
    - O `.exe` do Windows leva as propriedades de versão: empresa RotaGuard, produto RotaGuard Teste, direitos autorais
      e nome original do arquivo.
    - O instalador leva `VersionInfo*` e `AppCopyright`.
    - O registro não escreve mais o nome do computador na linha de início.
    - O "Proprietário" e o "Computador" que o Windows mostra em Detalhes vêm do disco de quem baixou, não do arquivo.
11. **Download dentro do site** (pedido de 14/09):
    - Os arquivos ficam em `site/public/downloads/` e o site os serve em `/downloads/<arquivo>`.
    - A pasta fica fora do git (`site/.gitignore`), porque o GitHub recusa arquivo acima de 100 MB (o `.zip` do Windows
      tem 134 MB). É preciso copiar para lá o que o build gerou em `build/app-teste/pacotes/`.
    - A área de download confere cada arquivo com `HEAD` antes de oferecer o botão e mostra o tamanho. Arquivo que
      ainda não existe aparece como "Em preparação".
    - `NEXT_PUBLIC_ROTAGUARD_DOWNLOADS_BASE` troca a origem dos arquivos (por exemplo, a release do GitHub).
12. **Microsoft Store no futuro:** "futuramente irei fazer esse Microsoft Store (pacote MSIX)" (14/09).
    - A Store assina de novo o pacote MSIX, e o SmartScreen não mostra o aviso para app instalado por ela (documentação
      da Microsoft sobre opções de assinatura, ago/2026).
    - Até lá: `.zip` sem assinatura, com a instrução "Mais informações → Executar assim mesmo" no site.
13. **Privacidade, LGPD e termos numa seção, sem aceite** (pedido de 14/09: "não quero ter que aprovar nada para que
    comece a usar; apenas deixe lá em uma seção"):
    - `caixa/textos_legais.py` tem quatro abas: Privacidade, LGPD (Lei nº 13.709/2018), Termos de uso e Licenças.
    - Elas abrem pelo botão "Privacidade, LGPD e termos" da tela de início. Nada bloqueia nem condiciona o uso.
    - O texto descreve o que o código faz:
      - as imagens são analisadas na memória e não são gravadas nem enviadas;
      - ficam na pasta de dados `eventos.db`, `registro-teste.log` e `sirene.wav`;
      - nada sai do computador (`--sem-servidor`);
      - a calibração não é reaproveitada (sem `--consentimento-perfil`, nenhum perfil é salvo).
    - Direitos do art. 18 no próprio app:
      - "Abrir pasta de dados" (acesso);
      - "Apagar dados deste computador" (eliminação). `apagar_dados()` só aceita a pasta `RotaGuard/Teste` e pede
        confirmação na tela.
    - A aba Licenças resume os componentes e mostra o `THIRD_PARTY_NOTICES.md`.
    - O pacote leva esse arquivo e as pastas `*.dist-info` das bibliotecas, com os textos das licenças
      (`copy_metadata` no `.spec`). A da OpenCV cobre a FFmpeg (LGPL 2.1), que vai junto.
    - O `build.py` falha se o aviso ou a licença da OpenCV faltar no pacote.
    - O canal de contato fica "em preparação" enquanto `CONTATO_PRIVACIDADE` estiver vazio.
    - **Os textos são rascunho técnico: precisam de revisão de advogado antes de clientes.**

## Comportamento

- **Instalar e abrir no Windows**
  - Dado um computador Windows sem Python, quando a pessoa baixa o `.zip` pelo site, extrai e abre
    `RotaGuardTeste.exe`, então a tela de início aparece.
  - Ao clicar em "Iniciar teste", a câmera é encontrada sozinha e a janela abre em poucos segundos, com as medidas e o
    alarme.
- **Sem internet**
  - Dado o app aberto sem internet, quando o teste roda, então nada tenta falar com servidor e nenhum aviso de conexão
    aparece no registro.
- **Vídeo gravado**
  - Dado um arquivo de vídeo escolhido como fonte, quando o vídeo acaba, então o monitoramento termina sozinho e a tela
    de início volta a permitir outro teste.
- **Sem câmera ou câmera ocupada**
  - Dado um computador sem câmera livre, quando a pessoa clica em "Iniciar teste", então em até ~15 s a tela de início
    mostra "Nenhuma câmera respondeu…", com as últimas linhas do registro e o botão "Abrir pasta de registros".
  - Nada fecha sem explicação.
- **Fechar a janela da câmera**
  - Dado o teste em andamento, quando a pessoa fecha a janela da câmera no X ou aperta Esc ou Q, então o teste termina e
    a tela de início diz "Teste encerrado".
- **Privacidade e termos**
  - Dado o app aberto, quando a pessoa clica em "Iniciar teste" sem abrir nada, então o teste começa normalmente.
  - Quando ela clica em "Privacidade, LGPD e termos", abre uma janela com as quatro abas e os botões "Abrir pasta de
    dados", "Apagar dados deste computador" e "Fechar".
- **Apagar dados**
  - Dado nenhum teste em andamento, quando a pessoa confirma "Apagar dados deste computador", então os arquivos da pasta
    do teste somem e a pasta continua existindo, vazia.
  - Com teste em andamento, o app pede para encerrar o teste antes.
- **Baixar pelo site**
  - Dado o acesso com PIN, quando a pessoa abre a área do app, então Windows e Linux aparecem (sem macOS). Cada
    plataforma com arquivo em `/downloads` mostra "Baixar" e o tamanho; a que ainda não tem arquivo mostra
    "Em preparação".
- **Release**
  - Dada a tag `teste-v0.1.0`, quando o workflow roda, então a release recebe os 3 arquivos e o `SHA256SUMS.txt`, e
    cada pacote passou pelos testes de fumaça e sem câmera antes de ser publicado.

## Retorno do teste de 14/09/2026

- **O app fechou ao escolher a câmera:** "quando eu selecionei uma câmera e abri, o app fechou; isso não tem lógica".
  - Na primeira abertura, o app foi fechado por comando depois de 8 s, na conferência da tela de início (erro do
    processo, não do app).
  - A análise do código achou três casos reais de "sem lógica":
    - câmera escolhida que não existe: esperava para sempre, sem janela;
    - janela fechada no X: voltava a abrir;
    - câmera levando ~16 s para abrir sem nenhum aviso.
  - Viraram a decisão 9 e os critérios APT-13 a APT-18.
- **Câmera automática:** "a câmera deve ser reconhecida automaticamente" → decisão 9.
- **Download no site:** "coloque o download desse RotaGuard Teste dentro do site da RotaGuard" → decisão 11.
- **Nome nas propriedades:** "como propriedade coloque RotaGuard, não quero que deixe o nome do meu desktop" →
  decisão 10.
- **Plataformas:** "futuramente irei fazer esse Microsoft Store (pacote MSIX); deixe download apenas para Windows e
  Linux, pois não terá para Mac" → decisões 5 e 12.
- **Privacidade:** "coloque política de privacidade, LGPD e os termos dentro do script RotaGuard para ficar dentro da
  lei, porém não quero ter que aprovar nada para que comece a usar; apenas deixe lá em uma seção" → decisão 13.
- **Outros pedidos:**
  - celular no ouvido com a mão vazia → spec 009;
  - bocejo, olheiras, expressões ao redor dos olhos e movimento da cabeça → spec 011 (rascunho).

## Critérios de aceite

| ID | Critério | Teste |
|---|---|---|
| APT-01 | `pasta_dados()` devolve a pasta certa por sistema (com e sem `XDG_DATA_HOME` no Linux) | `tests/test_app_teste.py` |
| APT-02 | `argumentos_monitor()` monta a linha do monitor: câmera (`auto` por padrão), `--window`, `--sem-servidor`, `--data-dir`, `--espera-camera 15`; celular desligado → `--sem-celular`; som desligado → `--mute`; calibração rápida → `--calibration-min 60 --calibration-max 120` | `tests/test_app_teste.py` |
| APT-03 | `comando_monitor()` usa o próprio executável com `--monitor` quando empacotado, e `python app_teste.py --monitor` fora do pacote | `tests/test_app_teste.py` |
| APT-04 | `main()` sem argumentos abre a tela de início; com `--monitor` ou outros argumentos roda o monitor com eles | `tests/test_app_teste.py` |
| APT-05 | `--sem-servidor` existe (também por `DRIVESAFE_SEM_SERVIDOR`) e, com ela, a sincronização não é criada | `tests/test_app_teste.py` |
| APT-06 | Fonte em arquivo de vídeo: `OpenCVCamera` marca `terminou` no fim, e `DriverMonitor.run` termina em vez de reabrir | `tests/test_app_teste.py` |
| APT-07 | Câmera ao vivo continua reabrindo depois de falhas (sem regressão) | `tests/test_app_teste.py` |
| APT-08 | Título da janela da câmera com "RotaGuard" | `tests/test_app_teste.py` |
| APT-09 | Registro do monitor vai para `registro-teste.log` na pasta de dados, também quando o executável não tem console | `tests/test_app_teste.py` |
| APT-10 | Pacote: o executável roda um vídeo sintético com `--no-window --sem-servidor`, sai com código 0, o registro contém "Monitoramento finalizado" e não contém "Traceback" | teste de fumaça em `build.py` (local e CI) |
| APT-11 | Nomes dos arquivos iguais em `build.py`, no workflow e no site; o site serve de `/downloads` e a pasta está no `.gitignore` | `site/scripts/testes/downloads.test.mjs` |
| APT-12 | Suíte inteira do repositório continua verde; site com build, lint e testes verdes | provas |
| APT-13 | `run_monitor` liga `OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS=0` antes de abrir a câmera | `tests/test_app_teste.py` |
| APT-14 | `find_camera()` usa a primeira câmera que abre e manda imagem, fecha as que não servem e, sem nenhuma, levanta `CameraIndisponivel` com mensagem clara | `tests/test_app_teste.py` |
| APT-15 | `DriverMonitor.run(..., espera_camera_s=N)`: sem imagem por N s (nunca chegou ou parou) termina com `sem_imagem=True`; sem espera, segue tentando; `--espera-camera` padrão 0; `SAIDA_SEM_CAMERA == 3` no monitor e na tela | `tests/test_app_teste.py` |
| APT-16 | Janela: X (depois de visível), Esc, `q` e `Q` encerram; backend sem `WND_PROP_VISIBLE` não encerra sozinho | `tests/test_app_teste.py` |
| APT-17 | Tela de início: "Automática" por padrão; "Câmera N" → índice N−1; vídeo pelo caminho; mensagem de cada código de saída; fase do teste pelo registro | `tests/test_app_teste.py` |
| APT-18 | `run_monitor` com câmera inexistente e espera de 30 s sai com código 3 em menos de 25 s, explica que a câmera "não abriu" e não escreve o nome do computador no registro | `tests/test_app_teste.py` |
| APT-19 | Propriedades do `.exe` com empresa e produto RotaGuard, no formato que o PyInstaller carrega, sem o nome do computador | `tests/test_app_teste.py` |
| APT-20 | Pacote: câmera 9 com `--espera-camera 60` sai com código 3 em menos de 60 s, sem Traceback e com o aviso no registro | teste sem câmera em `build.py` |
| APT-21 | Seção com Privacidade, LGPD, Termos de uso e Licenças coerente com o app: cita a Lei nº 13.709/2018 e os arts. 11 e 18, "não é diagnóstico", `eventos.db`, `registro-teste.log`, a pasta de dados, "não envia imagens" (o app roda com `--sem-servidor`), os botões de abrir e apagar dados e a data da versão; diz que não é preciso aceitar nada; iniciar o teste não depende de aceite; o pacote leva `THIRD_PARTY_NOTICES.md` e os textos de licença das bibliotecas (FFmpeg/LGPL da OpenCV incluída) | `tests/test_app_teste.py` e verificação em `build.py` |
| APT-22 | `apagar_dados()` apaga os arquivos da pasta do teste (inclusive subpastas), mantém a pasta e recusa qualquer pasta que não seja `RotaGuard/Teste` | `tests/test_app_teste.py` |
| APT-23 | Sem Mac: nada de macOS no site (downloads, área de download, mensagens), no `build.py`, no `.spec` e no workflow | `site/scripts/testes/downloads.test.mjs` |

## Fora de escopo

- Painel da empresa, conexão do script com o painel e importação do registro (specs 004 e 007).
- Registro da viagem e trechos (specs 001 e 002).
- **Versão para Mac** (decisão de 14/09/2026).
- Assinatura digital agora: sem certificado, o Windows SmartScreen pede confirmação na primeira abertura. O caminho
  escolhido para o futuro é a Microsoft Store (decisão 12).
- Android e iPhone: o script Python não roda neles; o teste de câmera no celular vem com o app do painel (spec 007).
- Nome da câmera na lista (ex.: "Integrated Webcam"): o OpenCV não informa; a lista mostra "Câmera 1, 2…".
- Aceite obrigatório dos termos: fora por pedido do Matheus.

## Riscos

- **Antivírus:** executável sem assinatura pode ser barrado.
- **Linux:** a janela do OpenCV precisa de ambiente gráfico. O alarme usa `aplay`, `paplay` ou `pw-play` do sistema.
- **Tamanho:** o pacote passa de 130 MB por causa do MediaPipe e do OpenCV.
- **Site publicado:** os arquivos de `public/downloads` não vão pelo git. Quem publicar o site precisa copiá-los no
  deploy ou apontar `NEXT_PUBLIC_ROTAGUARD_DOWNLOADS_BASE` para outro lugar. Hospedagens costumam limitar o tamanho de
  arquivo estático.
- **Textos legais sem revisão jurídica:** descrevem o comportamento real do app, mas não substituem parecer de advogado.
  Para a caixa nas frotas (monitoramento de empregados), a LGPD e a CLT pedem análise própria.
- **Push do workflow:** o token do push precisa de permissão `workflow`.

## Perguntas para o Matheus

1. No site publicado, onde ficam os arquivos de 130 MB ou mais: release pública do GitHub (qualquer pessoa com o link
   baixa, mesmo com o PIN no site) ou um armazenamento de arquivos?
2. Para os textos legais: razão social, CNPJ e um canal de privacidade (e-mail ou telefone). Enquanto não houver, o app
   mostra "RotaGuard" e "canal de privacidade em preparação".
