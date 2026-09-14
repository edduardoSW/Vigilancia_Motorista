# O que mudar · RotaGuard

Documento de passagem para outra IA. Escrito em 11/09/2026, a pedido do Matheus: "pause tudo que está fazendo […]
anote tudo o que falta e deixe todas as reclamações que eu fiz anotadas".

**Contexto do repositório**

- Repositório `edduardoSW/Vigilancia_Motorista`, branch `app-instalavel-em-andamento`. **Nunca** mexer na `main`.
- Commits desta sessão:
  - `4141045`: reorganização + PRD;
  - `440e14e`: site Next "Escalas", **rejeitado**;
  - depois: site "Boa chegada", feito por outra IA, mídia, specs e este documento.
- **Push feito para `app-instalavel-em-andamento` em 11/09/2026** (seção 0).

---

## 0. Estado verificado em 11/09/2026, depois do site feito pela outra IA

Conferido no código e rodando as provas, não de memória.

| Área | Estado real | Prova |
|---|---|---|
| Site | **Refeito na direção "Boa chegada"** (outra IA): Space Grotesk + Manrope, verde profundo, branco e lima, foto de estrada e ônibus interestadual no topo, caixa em destaque com pontos clicáveis, seletor ônibus ou carga, etapas da viagem, relatório de exemplo, FAQ e contato. Régua lateral, mapa-múndi e "escalas" saíram. **Falta o Matheus aprovar o visual.** | `npm run build`: 23 páginas, sem erro · `npm run lint`: 0 erros, 1 aviso (`site/scripts/testes/navegador.mjs:38`) · `npm test`: **49 de 49 passando** |
| Idiomas | pt-BR, en, es, fr, zh-CN **traduzidos** (o teste que acusava cópia do português passa) | `site/scripts/testes/i18n.test.mjs` |
| PIN | **Em `localStorage`**, como o Matheus pediu: hash SHA-256 com sal em `site/src/lib/acesso-local.ts`, sessão de 12 h, pausa de 15 min após 5 erros. O PIN não está em nenhum arquivo (conferido por busca). É barreira de demonstração, não segurança de produção. | `site/scripts/testes/acesso-local.test.mjs` |
| Downloads do app | **Atualizado em 14/09:** oferece o RotaGuard Teste (script empacotado) servido pelo próprio site em `/downloads`. O Windows `.zip` sai do build local; o Linux só do CI e aparece "em preparação" enquanto não houver arquivo. **Sem Mac** (14/09) | `site/src/components/download-area.tsx`, spec 010 |
| Imagens | 5 ilustrações de IA (ônibus na serra, carreta, motorista, coleta na garagem, caixa conceitual), originais em `docs/site/midia/originais/`, WebP no site. **Nenhum crédito do Magnific foi gasto.** | `docs/site/midia/README.md` |
| Vídeo do produto | **Parcial:** estudo local no Blender com giro e montagem (`site/public/midia/rotaguard/estudo-engenharia.mp4`, 10 s, 800 × 500). **Faltam as tomadas da caixa dentro do caminhão e do ônibus** e uma versão em resolução maior. A geometria do Blender não é idêntica à caixa da imagem de IA. | `docs/produto/3d/render_site.py` |
| Prompts | Direção atual em `docs/site/midia/05-direcao-boa-chegada.md`. Os arquivos `00` a `04` são **histórico** da direção rejeitada (ainda citam mapas e ônibus urbano). O `prompts-imagens.md` obsoleto foi apagado. | `docs/site/midia/README.md` |
| Script da caixa | **Sem mudança desde a reorganização.** A detecção existente funciona; nada do registro, dos trechos, da coleta ou do Pi 4 foi implementado. | 8 scripts, 93 verificações (rodados na reorganização) |
| Specs | 001 (registro) e 002 (trechos) **aprovadas**; 003 (identidade e coleta) **rascunho incompleto**; 007 (app) rascunho; 008 (site) atualizada pela outra IA; 004, 005, 006 e 009 **não escritas** | `docs/specs/` |
| App instalável e painel | **App de teste do script feito em 14/09** (spec 010, seção 0.1). **Painel: nada feito** (sem Tauri; o painel continua o PWA antigo com visual rejeitado), e a conexão do script com ele fica para depois, como o Matheus pediu | `caixa/app_teste.py`, `painel/webapp/` |
| Skill claude-watch | **Não instalada** (`~/.claude/skills/watch` não existe) | busca no disco |

### 0.1 Atualização de 14/09/2026 (app de teste do script)

- **Pedido:** "quero que faça a questão de download agora para eu poder testar em outros computadores; a parte do
  dashboard da empresa e a conexão com esse script faça depois".
- **Feito:**
  - **RotaGuard Teste** (spec 010): o script da caixa empacotado com PyInstaller, com tela de início.
    - Câmera automática; aviso claro sem câmera; X/Esc/Q encerram.
    - Propriedades RotaGuard no `.exe`; registro sem o nome do computador.
    - Atalho na área de trabalho deste computador.
  - O site serve o pacote em `/downloads`: `site/public/downloads/`, fora do git pelo limite de 100 MB do GitHub.
  - Seção **Privacidade, LGPD e termos** no app, sem aceite obrigatório, com botões para abrir e apagar os dados do
    teste e a aba de licenças de terceiros. Falta revisão de advogado, razão social, CNPJ e canal de privacidade.
  - **Sem Mac** nos downloads; Windows no futuro pela Microsoft Store (MSIX).
  - Workflow `.github/workflows/app-teste.yml` para Windows e Linux (sem Mac): **ainda não enviado nem rodado**.
- **Retorno do teste do Matheus** e o que virou:
  - "a câmera deve ser reconhecida automaticamente" → feito.
  - "o app fechou" → na primeira vez a janela foi fechada por comando na conferência. Corrigidos também os casos reais:
    câmera inexistente esperava para sempre, o X reabria a janela e a câmera levava ~16 s para abrir.
  - Mão vazia na orelha virando celular → spec 009, CEL-01 corrigido. Falta calibrar com gravações.
  - Bocejo, olheiras, expressões dos olhos e movimento da cabeça → spec 011 em rascunho.
    - Bocejo e cabeceio **já existiam**, mas não apareciam na janela.
    - Olheiras: recomendação de ficar fora (luz, câmera infravermelha, tom de pele).
- **Provas de 14/09:**
  - suíte Python com 110 verificações e 0 falhas;
  - site com build ok, lint com 0 erros, 53 de 53 testes e `tsc` sem erro;
  - pacote Windows com teste de fumaça e teste sem câmera (`implantacao/app-teste/build.py`).

### 0.2 Painel da empresa: parado em 14/09/2026 às 15:00 (trabalho pela metade)

- A construção de todas as telas do painel (app de janela própria, spec 012 a 018) foi interrompida: a janela do
  Claude fechou às 14:40 com 2 dos 5 agentes ainda trabalhando (núcleo Python e casca da interface).
- **Onde parou, o que está pronto, o que falta e a ordem para continuar:** `docs/painel/onde-parou-2026-09-14.md`.
- Contrato comum dos agentes (nomes, tipos, permissões): `docs/painel/contrato-painel.md`.

---

## 1. Reclamações do Matheus (palavras dele, em ordem)

### 10/09/2026 (sessão anterior)

1. App "Cabine noturna": "muito feio, cara de IA, paleta de cores horrenda, efeitos desnecessários, sem cara de algo
   profissional e sério".
2. Painel: "esse painel de controle em momento nenhum eu falei que ele vai ser web".
3. Prévia v1 do site (HTML): "horrível, totalmente genérico", "você só colocou texto".
4. Detecção de celular: celular no ouvido disparava junto com celular na mão, e mão vazia na orelha virava celular.

### 11/09/2026 (esta sessão)

5. Prévia v2 (HTML): "o site que foi feito está totalmente ridículo. Eu quero que seja algo como divulgação de um produto
   para empresas de logística e transporte de pessoas, então deve ter imagens relacionadas a isso. Além disso, o site
   está muito genérico, totalmente genérico, com fontes genéricas, layout genérico, tudo que eu literalmente não quero e
   que nenhum site que eu fiz tem".
6. "Na porra do prompt de imagens, faça algo pensado." "O prompt dos fundos, imagens e vídeos devem ser muito pensados."
7. "No site deve ter algo referente a estradas, mapa-múndi etc." (pedido dele; a execução foi rejeitada depois, item 20).
8. "Eu falei que o site deve ser em Tailwind e Next." "Por que ainda continua fazendo o site em HTML? Eu não pedi para
   fazer isso."
9. "Quero que tenha melhor organização nas pastas do projeto também, pois está muito bagunçado."
10. Nome: primeiro "DriveSafe AI", depois **"nome do projeto é rotaguard"**.
11. "Faça o site em Next e Tailwind, já quero modificar nessa versão."
12. "O md das fotos, vídeos e imagens de fundo eu quero que separe para ficar mais organizado."
13. "Preciso que faça a questão do app ser instalável em qualquer dispositivo, para colocar a opção de baixar no site
    quando a pessoa estiver logada com aquele PIN, e eu preciso que deixe o script pronto, sem nenhuma pendência […] com
    no máximo 5 agentes testando e avaliando."
14. "Quero que utilize conceitos e coloque na regra global: usar técnicas como SDD, PRD, specs, TDD e criar hooks para
    criar guardrails."
15. "Quero que passe a utilizar a skill claude watch […] coloque isso na regra global também, na hora que tiver que
    analisar e falar sobre vídeos."
16. "No site a língua deve ter inglês, francês, português, chinês e espanhol, com a bandeira e o nome dos países em
    dropdown no nav."
17. "Os ônibus que eu digo não são os que transitam em cidade, mas sim os de empresas que transitam entre estados. Esse é
    o principal foco."
18. "Os vídeos do Magnific não devem ficar salvos no Magnific, somente aqui." "No Magnific só tem 14,8 mil créditos
    sobrando, então economize."
19. "As fotos eu vou fazer com o ChatGPT, então já é importante você me mandar os prompts das fotos e as coisas de fundo
    para eu fazer logo, e rode o npm para eu ver o site e abra no Firefox."
20. Site v3 (Next, direção "Escalas"): **"que porra de site é esse: fontes padrões, layout padrão, muito texto, nenhuma
    direção criativa de designer de um produto, essa barra lateral ridícula, logo ridícula, paleta de cores totalmente
    genérica, footer e todo o resto do site totalmente feios, essa ideia do mapa-múndi totalmente ridícula"**.
21. **"Navbar totalmente feio, ridículo, cards e botões totalmente padrões."**
22. **PIN:** "por que a porra da parte do login de colocar o PIN não está permitida ainda? Eu falei que o site deveria
    estar em local storage por enquanto." O PIN está com o Matheus: por regra dele, não gravar em arquivo nem em commit.
23. **"Parece que você não pensa e fez as personas e as coisas à toa. As outras versões do site em HTML estavam a mesma
    bosta dessa versão. Joguei tokens e tokens fora para nada."**
24. **"Onde está o prompt das fotos, vídeos etc., que até agora não apareceu? E, já que o site está uma merda, esses prompts
    devem estar iguais, ruins e horrorosos."**
    - Os prompts existem em `docs/site/midia/`, mas ele não os encontrou.
    - O arquivo que ele abria (`Downloads/Vigilancia_Motorista-main/site-drivesafe/prompts-imagens.md`) era a cópia velha
      de 10/09, fora do repositório, e foi apagada.

### O que essas reclamações exigem da próxima IA

| Tema | Regra |
|---|---|
| Site | Direção criativa de **design de produto**: a caixa RotaGuard como herói visual, imagem forte de caminhão e **ônibus rodoviário interestadual**, **pouquíssimo texto**, tipografia e logo com personalidade, paleta própria, navbar, cards, botões e footer desenhados. Nada com cara de template. |
| Processo visual | **Mostrar referências reais de sites de produto e uma prévia concreta antes de codar**, e deixar o Matheus escolher. As três versões (v1, v2 e v3) falharam por pular isso. |
| Proibido voltar | Barra ou régua lateral, mapa-múndi como conceito, "escalas", paleta cinza "concreto", Sofia Sans e B612, logo de barra de escala, blocos de texto longos, estética SaaS (hero texto + widget, janela falsa, JSON, pílulas), fundo escuro com âmbar, efeitos gratuitos |
| Stack | Next.js + Tailwind (nunca HTML estático) |
| Entregas | Mostrar o resultado direto ao Matheus (links clicáveis, prompts colados no chat quando ele pedir), sem obrigá-lo a procurar |
| Custos | Economizar tokens e créditos do Magnific; nada de retrabalho sem direção aprovada |

---

## 2. Decisões do Matheus que continuam valendo

| Tema | Decisão |
|---|---|
| Nome | **RotaGuard** (identificadores `DRIVESAFE_*`, `drivesafe.db` ainda não renomeados no código) |
| Público | Transportadoras de carga e **empresas de ônibus rodoviário interestadual** (foco principal nos ônibus). **Ônibus urbano está fora.** |
| Produto | Caixa com Raspberry Pi e câmera no veículo. **O principal é o registro (log) da viagem.** Grava **só trechos curtos** quando algo se repete muito (sonolência frequente por muito tempo; sinais compatíveis com uso de anfetamina, sempre "não é diagnóstico"). Na chegada, a empresa **recolhe a caixa, conecta, o sistema reconhece o equipamento e gera o relatório**. Envio ao vivo é secundário. |
| Hardware | Pi 3 "eu não sei" → recomendado **Raspberry Pi 4 de 4 GB**: CPU ~3× mais rápida, 4× memória, USB-C como dispositivo (ligar por cabo e ser reconhecida), codificador H.264 no chip. Cuidados: fonte 5 V/3 A a partir de 12/24 V, desligamento seguro, calor, **relógio com bateria (RTC DS3231)**, porque o Pi não guarda a hora sem internet. |
| Futuro (não agora) | Pupila medida no **celular do motorista**; pulseira de frequência cardíaca |
| App | "Painel + teste de câmera" (mesmas regras do script), instalável: **instaladores Windows, Linux e Android (Tauri 2, GitHub Actions) + PWA no iPhone**. Download no site para quem entra com o PIN. **Sem Mac**; Windows no futuro pela Microsoft Store (MSIX) (14/09). |
| PIN no site | **Por enquanto em `localStorage`** (conferência no navegador). Guardar só hash no código, nunca o PIN. |
| Idiomas do site | pt-BR, en, es, fr, zh-CN, com dropdown de bandeira + país no nav |
| Fotos | O Matheus gera no **ChatGPT** com os prompts de `docs/site/midia/` |
| Vídeo do produto | Caixa em fundo branco girando 360°, montagem dos componentes, depois dentro de caminhão e ônibus. Arquivos salvos **no projeto**, não no Magnific. **Economizar créditos** (14,8 mil disponíveis). |
| Método | SDD: PRD → specs → TDD, com hooks de guardrail (já na regra global `~/.claude/CLAUDE.md`, seção 2b) |
| Vídeos para análise | Skill `watch` (claude-watch) na regra global (seção 2c). **Instalação bloqueada** pelo classificador de permissões (ver 4.6). |
| Agentes | No máximo 5 agentes ao mesmo tempo |

---

## 3. Onde está cada coisa (estado real)

```
Vigilancia_Motorista-main/
├── caixa/          script da câmera (run_monitor.py + vision/)      93 verificações de teste passando
├── servidor/       backend FastAPI, manage.py, start_system.py
├── painel/         webapp/ (PWA, visual rejeitado) e legado/
├── ferramentas/    analisar_video.py, avaliar_*.py, anotacoes/, modelos/
├── implantacao/    Dockerfiles, compose, raspberry-pi/               (Docker não foi rodado)
├── tests/
├── site/           Next.js 16 + Tailwind 4 + next-intl, direção "Boa chegada" (aguarda aprovação)
│   ├── src/components/product-home.tsx   página inicial inteira
│   ├── src/lib/acesso-local.ts           PIN em localStorage (só hash + sal)
│   └── public/midia/rotaguard/           imagens WebP e vídeo do estudo 3D
├── docs/
│   ├── produto/PRD.md                 PRD completo do RotaGuard
│   ├── produto/3d/                    caixa_rotaguard.py (modelo peça por peça) e render_site.py (vídeo do estudo)
│   ├── specs/                         001 e 002 aprovadas · 003 rascunho · 007 rascunho · 008 site
│   └── site/
│       ├── midia/README.md            índice da mídia atual
│       ├── midia/05-direcao-boa-chegada.md  prompts da direção atual
│       ├── midia/00 a 04              histórico da direção rejeitada (não usar como fonte)
│       ├── midia/originais/           PNGs originais das 5 imagens
│       ├── midia/video-local/         .blend do estudo (quadros de trabalho fora do git)
│       ├── prints/reformulacao-2026-09-11/  prints do site atual
│       ├── avaliacoes/2026-09-11-previa-v2/  avaliação em 5 frentes + 00-consolidado
│       └── personas.md, contexto.md, dados-mapas.md
├── PENDENCIAS.md   DESATUALIZADO (é de 10/09; ainda fala de DriveSafe e site HTML)
└── o-que-mudar.md  este arquivo
```

Worktrees locais (fora do repositório, em `Downloads/Vigilancia_Motorista-main/worktrees/`, **não vão no push**):

| Worktree / branch | Estado |
|---|---|
| `registro-trechos` / `rg/registro-trechos` | Specs 001 e 002 (já copiadas para a branch principal) e `tests/test_registro.py` começado, sem commit, sem implementação |
| `identidade-coleta` / `rg/identidade-coleta` | Rascunho da spec 003 (já copiado para a branch principal, incompleto) |
| `contexto-deteccao` / `rg/contexto-deteccao` | Nada feito |

---

## 4. O que falta

### 4.1 Site (prioridade do Matheus)

- [x] Visual refeito na direção "Boa chegada" (outra IA): régua lateral, mapa-múndi, escalas, Sofia Sans/B612 e paleta
  concreto saíram.
- [x] PIN em `localStorage` (hash + sal, 12 h, pausa após 5 erros), com teste.
- [x] Ônibus rodoviário interestadual como foco principal; carga e logística como segundo segmento.
- [x] Traduções en, es, fr e zh-CN (teste `SITE-03` passa).
- [x] `site/AGENTS.md` e `site/CLAUDE.md` (gerados pelo `next dev`) commitados.
- [ ] **O Matheus aprovar o visual novo.** Se não aprovar: referências de sites de produto e prévia antes de mexer
  (itens 20 a 23).
- [ ] **Logo:** hoje é o nome em texto (`wordmark.tsx`). Falta um símbolo aprovado.
- [ ] **Contato:** número de WhatsApp e telefone, domínio, preço e oferta de piloto (variáveis vazias em
  `site/.env.example`; o site mostra "contato em preparação").
- [x] **Downloads:** RotaGuard Teste servido em `/downloads` (14/09, spec 010).
- [ ] **Downloads no site publicado:** decidir onde ficam os arquivos de 130 MB ou mais (release do GitHub ou
  armazenamento de arquivos). O painel instalável continua pendente (4.5).
- [ ] **Imagens:** as 5 são ilustrações de IA e a caixa é conceito. Trocar por fotos reais e pelo design final quando
  houver. As fotos que o Matheus gerar no ChatGPT entram em `docs/site/midia/originais/` e são convertidas por
  `site/scripts/preparar-midia.mjs`.
- [ ] Aviso de lint em `site/scripts/testes/navegador.mjs:38` (expressão sem efeito).
- [ ] Publicar o site: hospedagem, domínio e `NEXT_PUBLIC_ROTAGUARD_INDEXAR=1` só quando for ao ar.
- Como rodar: `cd site && npm install && npm run dev` → http://localhost:3000/pt-BR · provas: `npm run build`,
  `npm run lint`, `npm test` (`node scripts/testes/navegador.mjs` confere no Edge sem janela).

### 4.2 Prompts de fotos, fundos, banners e vídeos

- **Fonte atual:** `docs/site/midia/README.md` (índice) e `docs/site/midia/05-direcao-boa-chegada.md` (prompts das
  5 imagens e do vídeo usados no site).
- **Histórico:** `00-regras-gerais.md` a `04-videos.md` são briefs longos da direção rejeitada. Ainda citam mapas, "Atos"
  e ônibus urbano (S06, S10, S14). Servem só como banco de ideias.
- [x] `docs/site/midia/README.md` criado.
- [x] `docs/site/prompts-imagens.md` obsoleto apagado.
- [ ] Se o Matheus for gerar mais fotos no ChatGPT: escrever os prompts novos na linguagem da direção "Boa chegada" e
  **colar no chat** para ele ver (item 24), em vez de apontar arquivo histórico.

### 4.3 Vídeo do produto (pedido do item 18)

- [x] Estudo local no Blender com giro e montagem: `site/public/midia/rotaguard/estudo-engenharia.mp4` (10 s, 800 × 500),
  gerado por `docs/produto/3d/render_site.py` sobre o modelo `caixa_rotaguard.py`. Nenhum crédito gasto.
- [ ] **Fundo branco em resolução maior** (1920 × 1080): o pedido era a caixa em fundo branco girando 360° e a montagem.
  O estudo atual é pequeno e de engenharia.
- [ ] **Unificar a aparência da caixa:** a imagem de IA (`caixa-conceito`) e o modelo do Blender são desenhos diferentes.
  Escolher um e fazer o outro seguir.
- [ ] Materiais do Blender: no teste, o vidro saiu claro e o alumínio cinza-claro em vez de grafite; conferir no render
  atual.
- Blender 5.2.1 em `C:\Program Files\Blender Foundation\Blender 5.2\blender.exe`. Render por linha de comando:
  `caixa_rotaguard.py -- montar|stills` e `render_site.py -- <pasta> video`.
- [ ] **Caixa dentro do caminhão e do ônibus (Magnific, pago, economizar):** ainda **não gerado**.
  - só para a caixa **dentro da cabine do caminhão e do ônibus rodoviário**: 2 imagens com o render como referência de
    produto e 2 clipes curtos de imagem para vídeo;
  - rodar `simulate_cost` antes;
  - saldo em 11/09: **14.854 créditos**; meta de gasto: até ~2.000.
- [ ] Juntar os clipes localmente com ffmpeg (instalado via winget). **Baixar tudo para o projeto** e não deixar
  guardado no Magnific (o MCP não tem ferramenta de apagar criação; verificar pasta/`folders_delete`).

### 4.4 Script da caixa ("pronto sem nenhuma pendência")

- **Nada deste bloco foi implementado.** A detecção que já existia continua funcionando (93 verificações).
- [ ] Registro da viagem e trechos curtos: specs 001 e 002 **aprovadas** (em `docs/specs/`, ainda com status
  `rascunho`) com ajustes que **ainda não foram escritos nelas**:
  - modo `registro` para sinais de ativação, com consentimento;
  - assinatura trocável HMAC → Ed25519;
  - `cryptography==50.0.1`.

  Implementar com TDD.
- [ ] Identidade da caixa, coleta na chegada (rede pelo USB-C do Pi 4 ou rede do escritório + pen drive), manifesto
  assinado e relógio: spec 003 em **rascunho incompleto**; terminar a spec antes do código.
- [ ] Perfil Raspberry Pi 4: autoteste de som, temperatura, desligamento seguro, swap desligada/zram, comando `--medir`
  (spec 005).
- [ ] Contexto e consentimento (spec 006):
  - regra de descanso de passageiros (30 min a cada 4 h, CTB art. 67-C §1º-A);
  - servidor recusa evento sem consentimento de monitoramento;
  - envio ao vivo opcional;
  - apagar vídeo órfão do modo teste;
  - HTTPS obrigatório fora do localhost;
  - valor `registro` em `ACTIVATION_POLICIES`.
- [ ] Pendências de detecção que fecham só com código (spec 009):
  - mão num olho desliga só aquele olho;
  - teste de coçar o nariz;
  - medir mãos com mais frequência perto do rosto;
  - "Crítico" mantido 10 s.
- [ ] Mesclar as branches das worktrees no `app-instalavel-em-andamento`, rodar a suíte inteira e fazer uma rodada de
  avaliação e correção (no máximo 5 agentes, como ele pediu).
- **Não fecha só com código (depende do Matheus ou de hardware):**
  - gravações reais para calibrar gestos e celular (etapa 2);
  - medir fps e latência no Pi 4;
  - testar som, buzzer, câmera infravermelha e modo USB gadget na placa;
  - parecer jurídico e RIPD (LGPD: vídeo do rosto é dado pessoal, possivelmente sensível).

### 4.5 App instalável

- [x] **App de teste do script** (spec 010, 14/09):
  - pacote Windows local com testes de fumaça e sem câmera;
  - site servindo o `.zip`.
- [ ] **App de teste, o que falta:**
  - enviar o workflow `app-teste.yml` e rodar com a tag `teste-v0.1.0` (gera o Linux e o instalador do Windows);
  - decidir a hospedagem dos arquivos no site publicado;
  - assinatura: futuramente publicar na Microsoft Store (pacote MSIX), que assina e tira o aviso do Windows;
  - revisão de advogado dos textos de privacidade, LGPD e termos do app.
- [ ] **Spec 009, CEL-03:** gravações de mão vazia na orelha e de celular real na orelha para calibrar
  `EAR_CONFIRM_HITS`.
- [ ] **Spec 011** (rascunho): aprovar os sinais de bocejo visível, olhos e cabeça, e responder se bocejo sozinho
  pode continuar tocando alarme.
- [x] **Painel da empresa como app de computador** (specs 012 e 013, 14/09):
  - **Primeira prévia rejeitada:** aberta no navegador ("não deve ser web") e visual "com muita cara de IA e confuso".
  - **Segunda prévia aprovada ("gostei"):** mistura de lista + detalhe, passo a passo e relatório em página.
    - Telas: caixa conectada, viagem com resumo em frases, momentos para verificar (vídeo e decisão na linha) e
      veículos e caixas.
    - Construída em `painel/app`, com dados fictícios.
  - **App de janela própria:** Python + pywebview/WebView2 (`painel/desktop`), com pacote em
    `build/painel/pacotes/RotaGuard-Painel-windows-x64.zip`. O instalador (Inno Setup) só sai no CI.
  - **Falta:**
    - ligar à caixa de verdade (specs 001, 003 e 004);
    - versão Linux;
    - responder as perguntas das specs 012 e 013.
- [ ] Spec 004 (importação e relatório): não escrita.
  - O app reconhece a caixa, confere o registro, decifra os trechos e gera PDF e CSV.
- [ ] Spec 007 (rascunho pronto em `docs/specs/007-app-instalavel.md`):
  - casca Tauri 2 para `painel/webapp`;
  - workflow `.github/workflows/app.yml` (Windows, Linux, Android; sem Mac);
  - PWA do iPhone;
  - modo de teste de câmera em JS com arquivos-ouro comparando com o Python.
  - Não há Rust nem `gh` neste computador: build só no GitHub Actions. O repositório é público e sem workflows.
- [ ] Redesenho visual do painel (o "Cabine noturna" continua rejeitado), com prévia aprovada antes.
- Perguntas abertas: identificador do app, onde publicar os instaladores, assinatura (Windows pela Microsoft Store no futuro; keystore Android),
  permissão `workflow` no token.

### 4.6 Regras globais e ferramentas

- **Feito:**
  - `~/.claude/CLAUDE.md` ganhou as seções 2b (SDD + PRD + specs + TDD + guardrails) e 2c (vídeos com a skill `watch`);
  - `~/.claude/hooks/guardrails.mjs` está registrado em `~/.claude/settings.json`, com 21 casos testados.
  - O hook bloqueia:
    - escrita na cópia obsoleta do vault;
    - segredos em arquivo;
    - o PIN (por HMAC, com a chave em `guardrails.config.json`, que é local);
    - push na main e `--no-verify`;
    - commit de `.env`/banco;
    - versão beta/rc/canary.
  - E pede confirmação para ferramenta paga do Magnific.
- [ ] **Instalar a skill claude-watch.** A cópia automática foi bloqueada pelo classificador de permissões. Para o
  Matheus instalar: clonar `https://github.com/alexlarcheveque/claude-watch` e copiar a pasta `skill/` para
  `C:\Users\Matheus Corte\.claude\skills\watch\`. Ajustes recomendados:
  - legendas `pt.*,en.*` em `lib/ytdlp-fetch.sh`;
  - `python` no lugar de `python3` em `lib/whisper-fallback.sh`;
  - abrir o relatório com `cmd.exe //c start`.
  - yt-dlp e ffmpeg já estão instalados.
- [ ] Hooks do projeto (`.claude/settings.json` do repositório): planejados, não criados.
  - Bloquear site em HTML fora de `painel/`.
  - Checar sintaxe Python após editar.
  - Lembrar de rodar testes antes de encerrar.

### 4.7 Documentação, git e vault

- [ ] Reescrever `PENDENCIAS.md`: está em 10/09, com DriveSafe e site HTML. Este arquivo é a lista atual.
- [x] README do `site/` atualizado pela outra IA para a direção "Boa chegada".
- [x] Tudo commitado e **push feito** para `app-instalavel-em-andamento` em 11/09/2026 (usuário `MatheusCortes02`).
  - Ficaram fora do git de propósito: os quadros de trabalho do vídeo (`docs/site/midia/video-local/frame-*.png`) e os
    backups `*.blend1`.
  - As worktrees `rg/*` são locais e não foram enviadas.
- [ ] Vault Obsidian (`C:\Users\Matheus Corte\Desktop\Obsidian`): nada foi registrado nesta sessão.
  - A cópia local está 7 commits atrás e há mudanças de outras sessões.
  - Para registrar: commitar só os arquivos próprios e mesclar `origin/main`, sem stash.
  - Registrar:
    - nota do projeto (RotaGuard);
    - as três rejeições do site (erro novo: "conceito abstrato no lugar de direção de design de produto"; "construir
      visual sem referência nem prévia");
    - as referências.

---

## 5. Alertas para não repetir

- **Honestidade do texto:**
  - nada de "em piloto", "conforme a LGPD" ou percentual de redução de acidentes;
  - nada de "detecta drogas" ("sinais compatíveis, não é diagnóstico");
  - nada de "nunca grava vídeo" (grava trechos curtos por recorrência);
  - nada de mapa com pino de evento (não há GPS).
- **Versões:** conferir no registro na hora. TypeScript travado em 6.0.3 (o typescript-eslint aceita `<6.1`) e ESLint
  em 9.39.5 (o eslint-plugin-react quebra no 10). Prova = build + lint + testes.
- **Tailwind 4:** token fora de camada, regra de elemento em `@layer base`, primitivo em `@layer components`.
- **Peso:** mapas em SVG inline deixaram o HTML com 4,6 MB. Resolvido com simplificação (`lib/svg-path.ts`, 521 KB),
  mas é sinal de cuidado com mídia pesada.
- **Computador:** não é do Matheus. Sem Docker e com o mínimo de instalação.
- **Segredos:** o PIN e as chaves ficam fora de arquivos e commits.
