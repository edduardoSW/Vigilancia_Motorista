# Pendências — DriveSafe AI

Estado em 10/09/2026, 21h: **etapa 1 feita** (gestos de sono no script da câmera) e **ferramentas da etapa 2 prontas** (a etapa 2 espera as gravações). Este trabalho está num **branch separado** (não na `main`) porque não terminou.

## ⚠️ Ler antes de continuar: feedback do Matheus em 10/09, 16h40

1. **O painel de controle não deve ser web.** O `webapp/` (PWA) foi feito a partir de uma resposta marcada como "App web instalável", mas Matheus diz que nunca quis o painel na web. **Definir o formato antes de mexer no `webapp/`** (programa de computador? app de celular?). O backend (API, banco, regras de acesso, testes) serve para qualquer formato.
2. **O visual atual foi rejeitado**: "muito feio, cara de IA, paleta de cores horrenda, efeitos desnecessários, sem cara de algo profissional e sério". No redesign: paleta sóbria e contida, tipografia séria, **sem** efeitos decorativos (grão, tracejado de estrada, marcos de km, animação de estrada, piscada, contador rolando). Mostrar uma prévia concreta (imagem ou tela estática) e aprovar **antes** de codar.
3. O que Matheus quer ver funcionando agora é o **script da câmera** (`python run_monitor.py --window`), não o site.

## Como abrir o que já existe

| O quê | Como |
|---|---|
| App em **modo de teste local** (sem servidor e sem banco) | `abrir-app-local.cmd` (Windows) ou `python servir_app_local.py` → http://localhost:8765. Escolha uma conta de exemplo e entre com o PIN de teste combinado no chat. |
| Servidor completo (API + app com login real) | `python start_system.py` (ou `uvicorn backend.main:app`). Abra o app uma vez com `?modo=servidor` para ele usar a API (a escolha fica salva; `?modo=local` volta). |
| Primeiro acesso no modo servidor | `python manage.py criar-usuario --papel admin --nome "Seu nome" --email voce@exemplo.com` (ou `--celular`). Dados de exemplo: `python manage.py demo --com-alertas`. |
| Validar com gravações (etapa 2) | `python avaliar_gestos.py resultados/video_gestos.csv anotacao_gestos.csv` e `python avaliar_celular.py anotacao_celular.csv --resultados resultados/`. Roteiro na etapa 2; modelos de anotação em `modelos_anotacao/`. |
| Testes | `python tests/test_server_sync.py` (26) · `tests/test_politica_remota.py` (6) · `tests/test_modulos.py` (13) · `tests/test_detector.py` (11) · `tests/test_avaliacao.py` (7) · `tests/test_celular.py` (13) · `tests/test_face_touch.py` (12) · `tests/test_avaliar_gestos_celular.py` (5). Todos passaram em 10/09 com Python 3.14.5. Depois da etapa 1, rodados de novo em outra máquina com Python 3.14.2: todos passaram de novo (detecção, política remota e os 26 do servidor, depois de instalar o requirements.txt). |

## O que ficou pronto nesta etapa

- **Gestos de sono (etapa 1, 10/09 à noite)**: `vision/face_touch.py` conta olhos esfregados ou coçados e mão no
  rosto com os pontos das mãos que o celular já mede, desliga as medidas do olho tapado pela mão, soma um sinal leve
  ao risco e aparece na janela da câmera, no CSV do `analisar_video.py` e nos tipos de evento. Detalhes na etapa 1.
- **Ferramentas de validação (etapa 2, 10/09 à noite)**: `avaliar_gestos.py` e `avaliar_celular.py`, com modelos de
  anotação em `modelos_anotacao/`. Faltam as gravações.
- **Detecção** (feito antes): sonolência (módulo 1), sinais compatíveis com ativação atípica (2), linha de base individual (3), fusão de risco com histerese e regra de rebote (4), celular na mão/no ouvido/olhando, óculos escuros, avaliação com vídeos e datasets.
- **Backend multiempresa** (`backend/`): empresas, acessos por papel (equipe/admin, gestor, motorista), sessão em cookie com proteção CSRF, senha com scrypt, bloqueio após 5 erros, **sem cadastro aberto** (só a equipe cria logins, por e-mail ou celular; gestor só bloqueia), senha temporária obrigatória de trocar, auditoria, consentimentos LGPD com histórico, revisão de eventos, estado ao vivo dos dispositivos, política do servidor aplicada no dispositivo (`vision/remote_policy.py`), tempo real por WebSocket filtrado por empresa, modo teste (`/api/test-mode`: câmera ao vivo, marcação de piscadas, análise de vídeo), contato da equipe por celular (`DRIVESAFE_CONTATO_CELULAR`).
- **Banco**: SQLite por padrão; já aceita PostgreSQL por `DATABASE_URL=postgresql+psycopg://...` (plano: VPS no futuro).
- **App instalável (PWA)** em `webapp/`, direção visual "Cabine noturna": HTML/CSS/JS sem build, fontes Overpass locais, ícones próprios, service worker (só guarda a casca do app, nunca dados), tema noite/dia.
  - Telas completas: entrar (servidor: e-mail/celular + senha; local: conta de exemplo + PIN), criar senha no primeiro acesso, conta, **frota ao vivo**, **revisar eventos** (atalhos J/K, 1–3, Ctrl+Enter), página do motorista (dia hora a hora, 30 dias, autorizações, exportar dados), meu painel e minhas autorizações (motorista), minha empresa (gestor: política e bloquear acesso).
  - Telas só com lista (sem formulário ainda): motoristas, veículos, dispositivos, empresas, acessos, relatórios (com CSV).
  - **Modo local** (`webapp/assets/js/local/`): responde as mesmas rotas da API no navegador, com dados de exemplo fictícios e frota simulada ao vivo.

## O que falta, em 3 etapas

| Etapa | O quê | Depende de | Situação |
|---|---|---|---|
| **1. Gestos de sono no script da câmera** | coçar os olhos e mão no rosto | nada | **feita em 10/09, até 21h30** |
| **2. Calibrar e validar com gravações reais** | validar os gestos, celular com aparelhos reais, escolher a melhoria de precisão | Matheus gravar vídeos e juntar celulares | **ferramentas prontas em 10/09**; faltam gravar e anotar |
| **3. Painel e site** | conferir o app, modo teste no navegador e pelo servidor, formulários, site, documentação | definir o formato do painel e aprovar a prévia visual | a fazer |

### Etapa 1 — Gestos de sono no script da câmera (10/09, até 21h30) — feita

Pedido: contar quantas vezes a pessoa **coça ou esfrega os olhos** e **põe a mão no rosto**, gestos que aparecem
quando ela está com sono. É o que Matheus quer ver funcionando agora: o script da câmera, não o site.

> Hipótese, confirmar na etapa 2: escalas de sonolência avaliada por observador (por exemplo, a ORD de Wierwille e
> Ellsworth, 1994) citam esfregar olhos e rosto como sinal comportamental. Por isso o gesto entrou só como sinal leve.

- [x] **Reaproveitar o que já roda:** `vision/face_touch.py` usa as mãos do Hand Landmarker de `vision/phone.py`
  (mesma thread) e os pontos dos olhos e o `face_box` de `vision/face.py`. Nenhum modelo novo.
- [x] **Esfregar ou coçar o olho:** ponta ou nó do indicador ou do médio (pontos 6, 8, 10 e 12) a até 0,2 largura
  de rosto do centro de um olho, em vai e vem, por 0,5 s a 5 s; gestos a menos de 1,5 s viram um episódio só.
  - Mudança em relação ao plano: **2 inversões em até 2 s**, e não em 1 s, porque as mãos são medidas cerca de
    4 vezes por segundo (`DETECT_EVERY_S`). Amplitude mínima de 0,06 rosto, para o tremor dos pontos não contar.
  - O olho "sumir ou fechar" virou detalhe do evento (`fracao_olho_encoberto`), não exigência: com a mão em cima,
    os pontos do olho costumam continuar "abertos".
  - Vai e vem por mais de 5 s conta como mão no rosto.
- [x] **Mão no rosto:** pelo menos 3 pontos da mão na parte de cima do rosto (testa, olhos, bochechas) por 1 s ou
  mais. A faixa da boca fica de fora (comer, beber, tapar a boca no bocejo) e as bordas laterais também (mão na
  orelha). Nada conta com o celular no ouvido nem com a mão que segura o celular.
- [x] **Oclusão:** se os pontos do rosto somem com a mão na frente, vale o último rosto visto (até 2 s antes de a
  mão chegar, e enquanto ela continuar ali): o gesto continua contando e não gera o aviso de rosto não detectado. Enquanto a mão está no olho, `vision/engine.py` desliga as medidas do olho, como nos óculos
  escuros: o olho tapado não vira piscada, PERCLOS nem microssono.
- [x] **Falsos positivos cobertos nos testes:** ajustar os óculos (menos de 1 s, sem vai e vem), comer ou beber,
  coçar a orelha, passar a mão na testa (suor), segurar o celular perto do olho e celular no ouvido.
- [x] **Saídas:**
  - Métricas na janela: `coceiras_olhos_10min` e `maos_no_rosto_10min`, com rótulos em `webapp/assets/js/format.js`.
  - Eventos `olhos_esfregados` e `mao_no_rosto` (risco 1, no máximo 1 por tipo a cada 60 s, fora da fila de
    revisão), com nomes em `backend/alert_types.py` e `webapp/assets/js/local/alert-types.js`, categoria sonolência.
  - Sinal leve no risco: ficou em `vision/risk.py` (e não em `vision/drowsiness.py`), junto da regra de contexto.
    3 ou mais olhos esfregados em 10 min **com** outro sinal leve de sono levam ao risco alto em 5 min, em vez de 10.
    Sozinhos, não mudam o risco. Mão parada no rosto não pesa (mudado na etapa 2, pela fonte abaixo).
  - Janela da câmera (`draw_overlay`): gesto em andamento e contagem dos últimos 10 min.
  - `analisar_video.py`: as duas métricas no CSV de janelas, coluna `gesto_mao` no CSV de quadros e
    `gestos_maos` no resumo.
- [x] **Testes:** `tests/test_face_touch.py` (11 verificações, detector falso com mão de 21 pontos, no estilo de
  `tests/test_celular.py`, uma delas com o motor inteiro).

Ficou para a etapa 2:
- [ ] Ver na câmera de verdade (`python run_monitor.py --window`) se o vai e vem é pego a ~4 medidas por segundo.
  Se falhar, medir só as mãos (sem o detector de celular) com mais frequência enquanto houver mão perto do rosto.
- [ ] Coçar o nariz não tem teste próprio: só o raio do olho (0,2 rosto) separa os dois. Conferir em vídeo.
- [ ] Hoje a mão num olho desliga as medidas **dos dois** olhos. Desligar só o olho tapado exige mexer na abertura
  combinada de `vision/eyes.py`.

### Etapa 2 — Calibrar e validar com gravações reais

Depende de Matheus gravar vídeos e juntar celulares. Não mexe no painel.

**Ferramentas prontas em 10/09 à noite; faltam as gravações.**

Pronto nesta etapa:
- [x] `avaliar_gestos.py`: compara o `_gestos.csv` com a anotação manual. Mostra acertos, falsos positivos e perdidos
  por gesto e sem olhar o nome, a troca entre os dois gestos e os falsos positivos em cima de cada negativo anotado
  (óculos, nariz, comer...).
- [x] `avaliar_celular.py`: descrito na parte do celular, abaixo.
- [x] `analisar_video.py --celular` grava o `_gestos.csv` (cada episódio) e as medidas da caixa do celular em cada
  quadro do `_quadros.csv`.
- [x] Modelos de anotação em `modelos_anotacao/` (ponto e vírgula, ponto decimal).
- [x] Testes: `tests/test_avaliar_gestos_celular.py` (5) e mais 1 em `tests/test_face_touch.py` (12).

Roteiro para validar:
1. **Gravar** (~30 fps, rosto inteiro na imagem). Os primeiros 30 s ou mais com o rosto parado, olhos abertos e sem
   gestos: o `analisar_video.py` calibra com o começo do vídeo (1/3 de um vídeo curto, no mínimo 30 s).
   - Gestos: coçar um olho, os dois, com os nós dos dedos, mão parada na testa ou na bochecha; e os negativos
     (ajustar óculos, coçar o nariz, comer, beber, passar a mão no suor, celular no ouvido).
   - Celular: cada aparelho em cada situação, e os negativos (lista abaixo).
2. **Rodar** cada vídeo: `python analisar_video.py gravacao.mp4 --celular --saida resultados/`.
3. **Anotar** à mão copiando os modelos de `modelos_anotacao/`.
4. **Comparar**: `python avaliar_gestos.py resultados/gravacao_gestos.csv anotacao_gestos.csv` e
   `python avaliar_celular.py anotacao_celular.csv --resultados resultados/`.
5. **Ajustar** os limiares listados abaixo com os números e rodar os testes de novo.

#### Gestos de sono: validar a etapa 1
- [ ] Gravar vídeos com os gestos anotados à mão (coçar um olho, os dois, com os nós dos dedos, mão parada no rosto,
  ajustar óculos, coçar o nariz, comer, beber) e medir precisão e sensibilidade com o `avaliar_gestos.py`.
- [x] **Fonte da ORD conferida** (10/09, noite), só por fonte secundária: Wierwille e Ellsworth (1994), *Accident
  Analysis & Prevention* 26(5):571–581, DOI 10.1016/0001-4575(94)90019-1. Nas descrições reproduzidas por Wiegand et
  al. (VTTI, 2009, https://scholar.lib.vt.edu/VTTI/reports/ORD_Final_Report_022509.pdf), "rubbing the face or eyes" é
  maneirismo do nível **moderadamente sonolento**, que nem todos apresentam, **sem peso numérico**. O artigo de 1994
  não abriu (403).
- [x] **Tocar o rosto é comum acordado:** 26,4 toques/h em direção normal (5,1 a 90,7/h entre pessoas; 26,1/h com
  carga de trabalho baixa), em Ralph et al. (2022), *Ergonomics* 65(7):943–959, DOI 10.1080/00140139.2021.2004241
  (lido só o resumo). São uns 4 toques em 10 min: o limiar de 3 gestos somando mão no rosto disparava sem sono.
  **Mudança:** só olhos esfregados pesam no risco (`vision/risk.py`); mão parada no rosto é contada e mostrada.
- [ ] Nenhuma fonte deu a frequência de esfregar os olhos com sono e acordado: tirar das gravações (quantos por hora
  em cada estado) antes de mexer em `HAND_GESTURES_LIGHT_SIGNAL`.
- [ ] Mão no rosto varia muito entre pessoas: se voltar a pesar no risco, usar linha de base por motorista (como os
  z-scores do módulo 3).
- [ ] Ajustar com os dados: `EYE_RADIUS_FACES`, `RUB_MIN_AMPLITUDE_FACES`, `RUB_WINDOW_S`, `HAND_ON_FACE_MIN_S`,
  `UPPER_FACE_FRACTION` e `HAND_GESTURES_LIGHT_SIGNAL`.

#### Celular: calibrar com aparelhos reais (pedido de 10/09)

Matheus viu no teste com a câmera que "celular no ouvido" disparava junto com "celular na mão" e que **mão vazia na orelha virava celular**. Corrigido em `vision/phone.py` no mesmo dia, com testes em `tests/test_celular.py`:
- cada estado conta o próprio tempo;
- mão vazia na orelha não conta, nem falando (a regra da boca mexendo saiu);
- a mão só mantém "no ouvido" por 5 s depois de o aparelho ser visto na orelha;
- celular à vista longe da orelha é "na mão";
- a área do ouvido não pega mais a altura do queixo.

Os limiares ainda são chute e precisam de dados:

- [ ] **Teste de tamanho com vários celulares reais:** juntar aparelhos de tamanhos diferentes (compacto de uns 5,4", comum de 6,1", grande de 6,7" ou mais, dobrável), com e sem capinha, de cores diferentes, e um celular antigo pequeno.
  - Gravar cada um na mão (na frente do peito, na altura do queixo, digitando), no ouvido, no colo e no suporte.
  - Variar a distância da câmera e a luz (dia, noite com infravermelho).
- [x] **Medir em cada gravação** (automático desde 10/09 à noite, no `_quadros.csv` do `analisar_video.py --celular`):
  - confiança do EfficientDet;
  - largura e altura da caixa divididas pela largura do rosto;
  - proporção da caixa (alto/largo).
- [ ] Com a faixa sugerida pelo `avaliar_celular.py` (p5 a p95 em larguras de rosto), descartar em `vision/phone.py` as caixas pequenas ou grandes demais para um celular.
- [ ] **Negativos, que não podem virar celular:**
  - mão vazia na orelha, coçar a orelha, ajeitar o cabelo;
  - fone de ouvido com fio e sem fio;
  - carteira, controle remoto, maço de cigarro, copo;
  - crachá pendurado, óculos na mão.
- [ ] **Ajustar com os dados:** `PHONE_MIN_SCORE`, `PHONE_EAR_DX_FACES` e `PHONE_EAR_DY_FACES`, `EAR_RADIUS_FACES`, `PHONE_EAR_MEMORY_S`, `HAND_ON_PHONE_MARGIN` e `PHONE_MOVE_FACES`. Medir precisão e sensibilidade de cada estado (na mão, no ouvido, olhando) com anotação manual dos vídeos, usando o `avaliar_celular.py`.
- [x] `avaliar_celular.py` (10/09, noite): lê os `_quadros.csv` das gravações e a anotação; gera a tabela de tamanhos e confianças por aparelho, a matriz de confusão entre sem celular, na mão, no ouvido e olhando, o acerto por situação e a faixa sugerida de tamanho.

#### Decisão desta etapa
- Qual melhoria de precisão começar: teste de pupila com câmera infravermelha com o veículo parado, ou frequência cardíaca por pulseira BLE.

### Etapa 3 — Painel e site

**Antes de começar**, resolver o feedback do topo: definir o formato do painel (programa de computador? app de
celular?) e aprovar uma prévia visual. Os itens abaixo foram escritos para o `webapp/` atual e podem mudar com essa
decisão.

#### Conferir o app no navegador
- [ ] Nenhuma tela foi aberta num navegador ainda: só a sintaxe dos arquivos foi checada. Passar por todas as telas nos 3 perfis, em modo local, e corrigir o que quebrar (console do navegador).
- [ ] Visual: alinhamento vertical do texto nos botões com a Overpass, tema dia, celular (abas embaixo e "Mais"), faixa de 24 h, gráfico de 30 dias.
- [ ] Modo servidor no navegador: login real, primeiro acesso, tempo real, revisão, bloqueio de acesso.

#### Modo teste com câmera no navegador (modo local)
- [ ] Copiar `@mediapipe/tasks-vision` **1.0.1** (Apache-2.0; `vision_bundle.mjs` e a pasta `wasm/`) para `webapp/assets/vendor/` e `vision/models/face_landmarker.task` para `webapp/assets/models/`.
- [ ] Portar o essencial de `vision/eyes.py` e `vision/drowsiness.py` para JS, com os mesmos limiares: piscada começa em abertura 0,50 e termina em 0,60; microssono 1 s; sono 3 s; sem resposta 6 s; fechamento longo 0,5 s; PERCLOS P80 contando só fechamentos acima de 250 ms; sonolência com PERCLOS 3 min ≥ 0,12; atenção com PERCLOS ≥ 0,08 ou 1,5× a base; bocejo com abertura da boca ≥ 0,45 por 2 s; cabeceio ≥ 15°; rosto ausente 10 s; intervalo entre avisos 300 s (atenção), 120 s (sonolência), 600 s (rosto).
- [ ] Gravar os eventos no banco local (`local/server.js`: dispositivo "Este computador" e avisos `alert`/`device`), para aparecerem na revisão e na frota.
- [ ] Alarme sonoro (WebAudio), marcação de piscada com a barra de espaço e conferência de precisão.
- [ ] Se o teste no navegador rodar pelo servidor: em `backend/main.py`, CSP com `'wasm-unsafe-eval'` e `Permissions-Policy: camera=(self)`.
- [ ] Opcional: celular no navegador (EfficientDet-Lite0 + Hand Landmarker).

#### Telas do modo teste pelo servidor
- [ ] `/api/test-mode`: iniciar e parar, vídeo MJPEG, métricas pela mensagem `test_state` do WebSocket, marcar piscadas, `/blink-check`, baixar CSVs.
- [ ] Análise de vídeo: envio com progresso (`PUT /api/test-mode/analyses`), lista com mensagens `analysis`, downloads.

#### Formulários e filtros no app
- [ ] Criar e editar motoristas, veículos, dispositivos (token aparece uma vez), empresas, acessos (senha temporária) e vínculo dispositivo ↔ veículo/motorista. As rotas da API já existem e têm testes; no modo local faltam as rotas POST/PATCH em `local/server.js`.
- [ ] Filtros em Relatórios (período, categoria, motorista, veículo).
- [ ] Conta → "dados de teste" no modo local: restaurar exemplo, ligar/desligar simulação de eventos.

#### Site de apresentação (Next.js) — prévia estática pronta, aguardando aprovação
- [x] **Prévia estática da página inicial (10/09, noite):** `site-drivesafe/previa/index.html`, com prints
  `previa-desktop.png` (1440 px) e `previa-celular.png` (400 px). O "Diário de bordo" virou estrutura: cada seção
  é uma hora do dia e o disco de 24 h é o gráfico de um dia de exemplo. Segue o feedback do app: papel claro,
  grafite e um âmbar, IBM Plex Sans e Mono, **sem** grão, estrada, marcos de km, animação ou tela piscando (a
  madrugada é só uma seção escura). Texto só com o que o código faz; dados do disco e da madrugada marcados como exemplo.
- [ ] **Aprovar ou pedir ajustes na prévia antes de codar o Next.js.** Em aberto: número do WhatsApp (o botão está
  sem link), texto final, versão em inglês e as fotos. O `prompts-imagens.md` ainda pede disco animado, tela
  piscando e grão de filme, que o feedback cortou: revisar os prompts antes de gerar imagens.
- [ ] Rodada de referências com URLs (regra do vault) antes do Next.js: a prévia usou só os padrões do vault.
- [ ] Depois da aprovação: Next.js + next-intl (PT e EN), versões conferidas no registro na hora, prova com build + lint.
- Direção aprovada: **"Diário de bordo"**. O site é um dia de 24 h num disco de tacógrafo: começa de dia em papel claro, escurece na madrugada (a tela pisca no microssono) e amanhece no contato.
- PT e EN com next-intl. Públicos: transportadoras, investidores e editais, universidades e pesquisa.
- Contato **só por celular/WhatsApp** (sem cadastro) e link "Já é cliente? Entrar no app".
- Prompts de imagens, banners e vídeos: `site-drivesafe/prompts-imagens.md`. Salvar o que for gerado em `site-drivesafe/public/midia/originais/`.
- Versões: conferir no registro na hora (`npm view <pacote> version`). TypeScript fica em 6.0.x porque o typescript-eslint não aceita o 7. ESLint: se o `eslint-plugin-react` ainda quebrar no 10, travar 9.39.x com justificativa. A prova é build + lint.

#### Documentação
- [ ] README: app (perfis, modo local x servidor, PIN só no modo local, HTTPS para instalar fora do localhost), acessos criados só pela equipe, `DRIVESAFE_CONTATO_CELULAR`.
- [ ] THIRD_PARTY_NOTICES: fontes Overpass (SIL OFL 1.1, arquivos em `webapp/assets/fonts/`); MediaPipe Tasks Vision (Apache-2.0) quando entrar.
- [ ] Remover o painel antigo `dashboard/` (substituído por `webapp/`).
- [ ] Obsidian: notas do app e do site, com as referências de design (URLs) e as versões exatas.

#### Decisões desta etapa
- Onde hospedar o app para instalar no celular (precisa HTTPS): GitHub Pages, Vercel ou a futura VPS.
- Migração para PostgreSQL na VPS: falta um comando que copie os dados do SQLite.

## Cuidados
- O PIN do modo local fica só como hash em `webapp/assets/js/local/pin.js` e **não protege dados de verdade**: o modo local roda inteiro no navegador. Nunca usar o modo local com dados reais de motoristas.
- Não versionar `data/` (banco, perfis, linhas de base, filas e análises têm dados pessoais) nem arquivos `.env`.
