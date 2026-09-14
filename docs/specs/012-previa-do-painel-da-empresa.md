# Spec 012 · Prévia do painel da empresa

| Campo | Valor |
|---|---|
| Status | prévia 1 rejeitada em 14/09/2026 (aberta no navegador, cara de IA, confusa) → prévia 2 em imagem aprovada ("gostei") → construída em `painel/app` e empacotada na janela do app (spec 013) |
| PRD | RF-20, RF-21, RF-22 (interface), RF-26 (demonstração com dados fictícios); RF-25 depois (Tauri) |
| Pedido | "faça o dashboard teste para eu ver como vai ser mais ou menos; você já tem tudo para fazer" |
| Código | `painel/app/` (Next.js 16.3.5, React 19.3.0, Tailwind 4.3.3, TypeScript 6.0.3, ESLint 9.39.5) |
| Testes | `painel/app/scripts/testes/previa.test.mjs` (`npm test` em `painel/app`) |

## Contexto

O painel da empresa é o app que a garagem usa quando o veículo chega:
1. a caixa é recolhida e conectada;
2. o app reconhece a caixa;
3. importa o registro da viagem e confere a integridade;
4. monta o relatório para revisão humana.

O painel antigo (`painel/webapp`, HTML e JS sem build) tem login, papéis e ligação com a API, mas o visual foi
rejeitado ("Cabine noturna"). Antes de refazer tudo, o Matheus quer **ver como vai ficar**.

Fluxo confirmado por ele em 14/09: "o script ficará dentro do Raspberry no veículo; após acabar o trajeto, a empresa
irá pegar esse dispositivo, conectar no computador e, com esse app, exportar a log/vídeo etc. para visualizar e continuar
o processo". A tela Chegadas começa exatamente aí: caixa conectada, registro (log) e vídeos curtos puxados, relatório e
revisão.

## Retorno de 14/09/2026 e nova direção

**O que ele disse sobre a prévia 1:**
- "esse dashboard não deve ser web, eu falei que não era para ser web, mas sim um app instalável para usar no computador".
  - A prévia foi aberta no Firefox, em localhost. Erro do processo: o painel nunca aparece no navegador, nem como teste.
- "o visual está com muita cara de IA e confuso de se entender, eu não quero algo assim". Causas reconhecidas:
  - rótulo em maiúsculas em cada seção (erro 51 do vault);
  - faixas, pontinhos de gravidade e legenda de cores;
  - termos técnicos ("cadeia de hash", "blocos", "gravidade média");
  - informação demais numa tela.

**Escolhas dele:**
- **Estrutura:** entre "passo a passo", "lista + detalhe" e "relatório em página", pediu "mesclar todas as opções para fazer algo melhor".
- **Tecnologia:** "Python + janela nativa" (pywebview com WebView2, PyInstaller e instalador; spec 013). Substitui o
  Tauri 2 da spec 007.

**Direção da prévia 2** (imagens em `docs/painel/previa-2026-09-14/`):
- **Janela do app:** as viagens numa coluna à esquerda (jeito de programa de computador); a caixa conectada fica no
  topo dessa coluna, com o progresso.
- **Caixa conectada:** passo a passo em frases simples (caixa reconhecida, lendo o registro, conferindo se nada foi
  alterado, separando os vídeos curtos) e o botão "Abrir viagem" quando termina.
- **Viagem como página de relatório:**
  - resumo em frases;
  - uma barra só de direção e pausa, com os momentos numerados;
  - lista "Momentos para verificar" com hora, o que aconteceu em linguagem de garagem, vídeo e decisão na própria
    linha.
- **Momento, não evento solto:** eventos de um episódio repetido viram um momento só ("Sono repetido: olhos fechados 2
  vezes em 26 min"). Na viagem de exemplo, 6 eventos para revisar viram 4 momentos.
- **Fica de fora:** rótulo em maiúsculas, legenda de cores, pontinhos de gravidade, faixa de números e jargão.

## Decisões

1. **Prévia visual com dados fictícios**, sem servidor, sem login e sem salvar nada.
   - As ações de revisão mudam só a tela aberta.
   - Todas as telas avisam "dados fictícios".
2. **Stack igual à do site**, com exportação estática (`output: "export"`).
   - A pasta `out/` é a interface que o app Tauri vai carregar (spec 007). Isso substitui a decisão 1 da spec 007:
     `painel/webapp` fica como referência da lógica de API, não como interface.
   - Versões conferidas no npm em 14/09:
     - Next 16.3.5 (latest);
     - TypeScript 6.0.3: o `typescript-eslint` pede menos que 6.1, e o TypeScript 7 quebra o `next build` (erro 30 do
       vault);
     - ESLint 9.39.5, igual ao site. O ESLint 10 já saiu e o npm avisa que o 9 está sem suporte, mas os plugins do
       `eslint-config-next` só aceitam até o 9: `eslint-plugin-react` 7.37.5, `eslint-plugin-import` 2.32.0 e
       `eslint-plugin-jsx-a11y` 6.10.2.
3. **Identidade do site "Boa chegada"**:
   - fontes: Space Grotesk nos títulos e Manrope nos textos;
   - verde `#103e31`, tinta `#153c31`, papel `#fafcf7`, concreto `#f0f4ed`, grafite `#68766c`, fio `#dce3d8`, lima
     `#d5f669` e alarme `#a72d38`.
4. **Sem localização:** a linha ("São Paulo → Curitiba") é cadastro da escala da empresa. Nada de mapa, GPS ou
   rastreamento: o produto não registra localização.
5. **Não é diagnóstico:** sinais de sono e de ativação atípica são indícios para revisão humana.
6. **Mesmas regras do servidor:**
   - nomes e categorias dos eventos iguais aos de `servidor/backend/alert_types.py`;
   - entram na fila de revisão só eventos de categoria revisável com risco 2 ou mais;
   - direção contínua acima de 5 h 30 min (CTB, art. 67-C) e madrugada de 00:00 a 06:59 (RF-03).
7. **Telas:**
   - **Chegadas:** caixas conectadas agora, com as etapas da importação, e viagens do dia.
   - **Relatório da viagem:**
     - linha do tempo da viagem, com direção, pausas, madrugada e eventos;
     - contagem por tipo e episódios recorrentes com trecho curto;
     - saúde da caixa e integridade do registro;
     - botões de exportar (só visuais na prévia).
   - **Revisão:** fila com confirmar, alarme falso e motorista orientado.
   - **Frota:** veículos e caixas com a situação de cada um. Veículo em viagem aparece "sem dados até a coleta",
     porque o envio ao vivo é opcional e está desligado.
8. **Idioma:** pt-BR na prévia. O app final segue os idiomas do site.

Referências de design e direção visual: seção no fim desta spec, preenchida com a pesquisa de 14/09.

## Comportamento

- **Chegadas**
  - Dado o painel aberto, então aparecem as caixas conectadas, com as etapas da importação (reconhecida, registro
    importado, integridade conferida, trechos decifrados, relatório pronto) e o progresso da que ainda importa.
- **Relatório**
  - Dado o relatório de uma viagem, então a linha do tempo mostra direção, pausa, a faixa da madrugada e cada evento na
    hora certa.
  - O episódio recorrente aparece com o trecho curto e a situação da revisão.
- **Revisão**
  - Dado um item na fila, quando o gestor escolhe "Alarme falso", então o item sai da fila pendente e mostra quem
    revisou (na prévia, "você") e quando.
- **Frota**
  - Dado um veículo em viagem, então a frota diz que não há dados até a coleta.

## Critérios de aceite

| ID | Critério | Teste |
|---|---|---|
| PRV-01 | Exportação estática com a caixa conectada (`/`), Veículos e caixas (`/veiculos/`) e o relatório de cada viagem fictícia; as telas da prévia 1 (`/revisao/`, `/frota/`) não existem mais | `previa.test.mjs` (depois do build) |
| PRV-02 | Cada tela exportada avisa "dados fictícios" e usa `lang="pt-BR"` | `previa.test.mjs` (depois do build) |
| PRV-03 | Nenhum mapa, GPS, rastreamento, latitude ou longitude no código do painel | `previa.test.mjs` |
| PRV-04 | O relatório diz na tela que os alertas não são diagnóstico e ajudam a avaliação de quem verifica | `previa.test.mjs` (depois do build) |
| PRV-05 | Nenhum "DriveSafe" visível | `previa.test.mjs` |
| PRV-06 | Dados coerentes: tipos existentes no servidor, eventos dentro da viagem e em ordem, jornada cobrindo a viagem, episódio com recorrência | `previa.test.mjs` |
| PRV-07 | Só são revisados eventos que o servidor manda revisar; a fila tem pelo menos 3 itens e existe evento que não entra nela | `previa.test.mjs` |
| PRV-08 | Nome e categoria de cada tipo de evento iguais aos do servidor | `previa.test.mjs` |
| PRV-09 | Momentos agrupados: a viagem v-2240 mostra "4 momentos para você verificar" com "Sono repetido: olhos fechados 2 vezes", a v-3310 mostra 2, e a coluna de viagens mostra "4 para ver", "2 para ver" e "Revisada" | `previa.test.mjs` (depois do build) |
| PRV-10 | Sem os vícios da prévia rejeitada: nenhum rótulo em maiúsculas, legenda de gravidade ou fonte mono no código das telas | `previa.test.mjs` |
| PRV-11 | `npm run build`, `npm run lint` e `npm test` verdes; conferência visual da janela do app em 1440 × 900 contra as imagens aprovadas | provas |

## Fora de escopo

- Login real, papéis, API do servidor, importação real da caixa, PDF e CSV reais.
- Empacotamento Tauri e instaladores (spec 007).
- Idiomas além do pt-BR e layout de celular (a prévia é para desktop).
- Registro da viagem de verdade (spec 001) e trechos (spec 002).

## Riscos

- **Visual rejeitado de novo:** a prévia existe justamente para errar barato. Nada é integrado antes da aprovação.
- **Parecer painel "web":** a prévia roda no navegador só para ver. O produto é o app instalável que carrega essa mesma
  interface.

## Referências e direção visual (pesquisa de 14/09/2026)

Pesquisa feita na hora em produtos reais, bibliotecas de componentes e galerias. Da referência sai o princípio, nunca
a cópia do layout.

| Referência | Categoria | O que aproveitar |
|---|---|---|
| [Samsara Safety Inbox](https://www.samsara.com/blog/safety-inbox-faster-easier-management-of-safety-incidents) | produto real | Todos os eventos numa fila única, com poucas ações. Aqui viram Confirmado / Alarme falso / Motorista orientado |
| [Motive Quick View](https://gomotive.com/blog/faster-safety-event-reviews-and-coaching-insights/) | produto real | Revisar sem sair da lista: painel lateral com trecho, nota e próximo/anterior |
| [Linear Triage](https://linear.app/docs/triage) | produto real | Uma tecla por decisão (`1`, `2`, `3`) e o próximo item abre sozinho |
| [Linear, redesenho da interface](https://linear.app/now/how-we-redesigned-the-linear-ui) | produto real | Menos moldura e três papéis de cor. Base papel, contraste verde, lima só em seleção, foco e ação principal |
| [Vercel Geist Status Dot](https://vercel.com/geist/status-dot) | sistema de design | Ponto de situação que pulsa só enquanto importa; o rótulo é o próprio estado |
| [FMCSA, grade do diário eletrônico](https://eld.fmcsa.dot.gov/FAQ/Topics?name=ELD_Technical_Specifications) | convenção de mercado | Faixas de estado num eixo de horas, com períodos especiais sombreados. Aqui: direção e pausa, madrugada e eventos |
| [Stripe, gráficos do painel](https://support.stripe.com/questions/dashboard-home-charts-overview) | produto real | Todo número com período e base de comparação; detectado e confirmado separados |

**Anti-referências** (padrões a evitar):
- o layout `dashboard-01` do shadcn/ui: barra lateral larga, quatro cartões de KPI e gráfico de área;
- o TailAdmin: ícone em círculo colorido, porcentagem sem base e mapa;
- "fleet dashboard" de galeria: mapa como destaque, velocímetro, rosca para três números e cartão de vidro.

**Direção aplicada:**
- **Navegação:** barra fina no topo com as quatro telas e a caixa conectada à direita, sem barra lateral. A linha do
  tempo precisa da largura toda.
- **Números:** faixa de números em linha, com fios entre eles e sem cartões; Space Grotesk com algarismos tabulares.
- **Relatório:** a linha do tempo da viagem é a peça central.
- **Revisão:** tela dividida, com lista densa à esquerda e o evento à direita; teclas `1`, `2`, `3`, `J` e `K`.
- **Frota:** tabela densa com ponto de situação e frase-resumo no lugar de cartões.
- **Cores:** duas de gravidade (âmbar `#9a6700` e alarme `#a72d38`), e cor nunca é o único sinal (ícone e texto
  junto). O lima nunca vira texto sobre o papel: contraste de ~1,2:1.

**Cores validadas com o script do guia de visualização de dados** (`validate_palette.js`, modo claro):
- **Reprovada:** alarme `#a72d38` + âmbar `#9a6700` + cinza a 55% ficou abaixo do mínimo de visão normal (ΔE 14,6) e
  com cinza sem contraste.
- **Aprovada:** alarme `#a72d38` + âmbar `#b58300` + grafite `#68766c`. Separação para daltonismo ΔE 12,7, visão
  normal 15,7 e contraste de 3:1 ou mais em todas.
- **O único "falha" que fica é de propósito:** o grafite é neutro (sinal leve ou aviso), sem saturação. A gravidade
  também aparece no tamanho da marca (12, 10 e 8 px), na legenda e na tabela de eventos.

**Regras de gráfico aplicadas:**
- marcas finas com anel da cor do fundo e área de toque de 24 px;
- dica de hora e duração no mouse e no teclado;
- rótulo dentro da barra só quando cabe;
- grade em fio contínuo;
- madrugada em fundo liso, sem hachura: textura só como opção de acessibilidade;
- tabela de eventos como versão sem gráfico;
- números grandes na mesma fonte do texto, sem algarismos tabulares; tabulares só em colunas e no eixo.

**Não vai usar:**
- barra lateral;
- cartões de KPI com ícone em círculo e porcentagem sem base;
- mapa, velocímetro, gráfico de rosca e cartão de vidro;
- gradiente decorativo e hachura por padrão;
- lima como texto;
- cor de gravidade sem rótulo;
- linha tracejada de grade;
- "Crítico" colado ao nome do motorista;
- as cores do "Cabine noturna" (`#14110f`, `#f5b301`, `#ef5b40`);
- Inter, shadcn/ui, Radix, lucide e bibliotecas de gráfico.

## Perguntas para o Matheus

1. As quatro telas cobrem o que a garagem precisa no dia a dia, ou falta alguma (motoristas, relatórios mensais)?
2. O relatório da viagem deve ser o centro do painel (abrir direto nele quando a caixa conecta)?
3. Painel claro, como o site, ou escuro? A prévia é clara. O modo escuro teria cores próprias validadas, não a inversão
   automática.
4. A interface do app passa a ser esta (Next.js + Tailwind, exportada para o Tauri) no lugar do `painel/webapp`? A spec
   007 dizia que o `painel/webapp` seria a interface.
5. Se a estrutura não agradar, mostro 2 ou 3 estruturas diferentes antes de seguir.
