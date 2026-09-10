# Pendências — DriveSafe AI

Estado em 10/09/2026, 17h. Este trabalho está num **branch separado** (não na `main`) porque não terminou.

## Como abrir o que já existe

| O quê | Como |
|---|---|
| App em **modo de teste local** (sem servidor e sem banco) | `abrir-app-local.cmd` (Windows) ou `python servir_app_local.py` → http://localhost:8765. Escolha uma conta de exemplo e entre com o PIN de teste combinado no chat. |
| Servidor completo (API + app com login real) | `python start_system.py` (ou `uvicorn backend.main:app`). Abra o app uma vez com `?modo=servidor` para ele usar a API (a escolha fica salva; `?modo=local` volta). |
| Primeiro acesso no modo servidor | `python manage.py criar-usuario --papel admin --nome "Seu nome" --email voce@exemplo.com` (ou `--celular`). Dados de exemplo: `python manage.py demo --com-alertas`. |
| Testes | `python tests/test_server_sync.py` (26) · `tests/test_politica_remota.py` (6) · `tests/test_modulos.py` (13) · `tests/test_detector.py` (11) · `tests/test_avaliacao.py` (7) · `tests/test_celular.py` (10). Todos passaram em 10/09 com Python 3.14.5. |

## O que ficou pronto nesta etapa

- **Detecção** (feito antes): sonolência (módulo 1), sinais compatíveis com ativação atípica (2), linha de base individual (3), fusão de risco com histerese e regra de rebote (4), celular na mão/no ouvido/olhando, óculos escuros, avaliação com vídeos e datasets.
- **Backend multiempresa** (`backend/`): empresas, acessos por papel (equipe/admin, gestor, motorista), sessão em cookie com proteção CSRF, senha com scrypt, bloqueio após 5 erros, **sem cadastro aberto** (só a equipe cria logins, por e-mail ou celular; gestor só bloqueia), senha temporária obrigatória de trocar, auditoria, consentimentos LGPD com histórico, revisão de eventos, estado ao vivo dos dispositivos, política do servidor aplicada no dispositivo (`vision/remote_policy.py`), tempo real por WebSocket filtrado por empresa, modo teste (`/api/test-mode`: câmera ao vivo, marcação de piscadas, análise de vídeo), contato da equipe por celular (`DRIVESAFE_CONTATO_CELULAR`).
- **Banco**: SQLite por padrão; já aceita PostgreSQL por `DATABASE_URL=postgresql+psycopg://...` (plano: VPS no futuro).
- **App instalável (PWA)** em `webapp/`, direção visual "Cabine noturna": HTML/CSS/JS sem build, fontes Overpass locais, ícones próprios, service worker (só guarda a casca do app, nunca dados), tema noite/dia.
  - Telas completas: entrar (servidor: e-mail/celular + senha; local: conta de exemplo + PIN), criar senha no primeiro acesso, conta, **frota ao vivo**, **revisar eventos** (atalhos J/K, 1–3, Ctrl+Enter), página do motorista (dia hora a hora, 30 dias, autorizações, exportar dados), meu painel e minhas autorizações (motorista), minha empresa (gestor: política e bloquear acesso).
  - Telas só com lista (sem formulário ainda): motoristas, veículos, dispositivos, empresas, acessos, relatórios (com CSV).
  - **Modo local** (`webapp/assets/js/local/`): responde as mesmas rotas da API no navegador, com dados de exemplo fictícios e frota simulada ao vivo.

## O que falta (ordem sugerida)

### 1. Conferir o app no navegador — prioridade
- [ ] Nenhuma tela foi aberta num navegador ainda: só a sintaxe dos arquivos foi checada. Passar por todas as telas nos 3 perfis, em modo local, e corrigir o que quebrar (console do navegador).
- [ ] Visual: alinhamento vertical do texto nos botões com a Overpass, tema dia, celular (abas embaixo e "Mais"), faixa de 24 h, gráfico de 30 dias.
- [ ] Modo servidor no navegador: login real, primeiro acesso, tempo real, revisão, bloqueio de acesso.

### 2. Modo teste com câmera no navegador (modo local)
- [ ] Copiar `@mediapipe/tasks-vision` **1.0.1** (Apache-2.0; `vision_bundle.mjs` e a pasta `wasm/`) para `webapp/assets/vendor/` e `vision/models/face_landmarker.task` para `webapp/assets/models/`.
- [ ] Portar o essencial de `vision/eyes.py` e `vision/drowsiness.py` para JS, com os mesmos limiares: piscada começa em abertura 0,50 e termina em 0,60; microssono 1 s; sono 3 s; sem resposta 6 s; fechamento longo 0,5 s; PERCLOS P80 contando só fechamentos acima de 250 ms; sonolência com PERCLOS 3 min ≥ 0,12; atenção com PERCLOS ≥ 0,08 ou 1,5× a base; bocejo com abertura da boca ≥ 0,45 por 2 s; cabeceio ≥ 15°; rosto ausente 10 s; intervalo entre avisos 300 s (atenção), 120 s (sonolência), 600 s (rosto).
- [ ] Gravar os eventos no banco local (`local/server.js`: dispositivo "Este computador" e avisos `alert`/`device`), para aparecerem na revisão e na frota.
- [ ] Alarme sonoro (WebAudio), marcação de piscada com a barra de espaço e conferência de precisão.
- [ ] Se o teste no navegador rodar pelo servidor: em `backend/main.py`, CSP com `'wasm-unsafe-eval'` e `Permissions-Policy: camera=(self)`.
- [ ] Opcional: celular no navegador (EfficientDet-Lite0 + Hand Landmarker).

### 3. Telas do modo teste pelo servidor
- [ ] `/api/test-mode`: iniciar e parar, vídeo MJPEG, métricas pela mensagem `test_state` do WebSocket, marcar piscadas, `/blink-check`, baixar CSVs.
- [ ] Análise de vídeo: envio com progresso (`PUT /api/test-mode/analyses`), lista com mensagens `analysis`, downloads.

### 4. Formulários e filtros no app
- [ ] Criar e editar motoristas, veículos, dispositivos (token aparece uma vez), empresas, acessos (senha temporária) e vínculo dispositivo ↔ veículo/motorista. As rotas da API já existem e têm testes; no modo local faltam as rotas POST/PATCH em `local/server.js`.
- [ ] Filtros em Relatórios (período, categoria, motorista, veículo).
- [ ] Conta → "dados de teste" no modo local: restaurar exemplo, ligar/desligar simulação de eventos.

### 5. Site de apresentação (Next.js) — não começou
- Direção aprovada: **"Diário de bordo"**. O site é um dia de 24 h num disco de tacógrafo: começa de dia em papel claro, escurece na madrugada (a tela pisca no microssono) e amanhece no contato.
- PT e EN com next-intl. Públicos: transportadoras, investidores e editais, universidades e pesquisa.
- Contato **só por celular/WhatsApp** (sem cadastro) e link "Já é cliente? Entrar no app".
- Prompts de imagens, banners e vídeos: `site-drivesafe/prompts-imagens.md`. Salvar o que for gerado em `site-drivesafe/public/midia/originais/`.
- Versões: conferir no registro na hora (`npm view <pacote> version`). TypeScript fica em 6.0.x porque o typescript-eslint não aceita o 7. ESLint: se o `eslint-plugin-react` ainda quebrar no 10, travar 9.39.x com justificativa. A prova é build + lint.

### 6. Documentação
- [ ] README: app (perfis, modo local x servidor, PIN só no modo local, HTTPS para instalar fora do localhost), acessos criados só pela equipe, `DRIVESAFE_CONTATO_CELULAR`.
- [ ] THIRD_PARTY_NOTICES: fontes Overpass (SIL OFL 1.1, arquivos em `webapp/assets/fonts/`); MediaPipe Tasks Vision (Apache-2.0) quando entrar.
- [ ] Remover o painel antigo `dashboard/` (substituído por `webapp/`).
- [ ] Obsidian: notas do app e do site, com as referências de design (URLs) e as versões exatas.

### 7. Decisões em aberto
- Qual melhoria de precisão começar: teste de pupila com câmera infravermelha com o veículo parado, ou frequência cardíaca por pulseira BLE.
- Onde hospedar o app para instalar no celular (precisa HTTPS): GitHub Pages, Vercel ou a futura VPS.
- Migração para PostgreSQL na VPS: falta um comando que copie os dados do SQLite.

## Cuidados
- O PIN do modo local fica só como hash em `webapp/assets/js/local/pin.js` e **não protege dados de verdade**: o modo local roda inteiro no navegador. Nunca usar o modo local com dados reais de motoristas.
- Não versionar `data/` (banco, perfis, linhas de base, filas e análises têm dados pessoais) nem arquivos `.env`.
