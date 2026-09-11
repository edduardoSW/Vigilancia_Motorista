# Consolidado · avaliação da prévia v2 do site

RotaGuard (antes DriveSafe AI) · rodada de 11/09/2026 · 5 frentes · consolidado em 11/09/2026

> Convenções
> - `F1` a `F5` são os relatórios `01` a `05` desta pasta. `#N` é o número do problema na tabela do relatório,
>   `VNN` é a linha da tabela de veracidade da frente 5 (Anexo B) e `F4·7` é a pergunta 7 da frente 4.
> - `v2:N` é a linha N de `site-drivesafe/previa/v2/index.html` e `v1:N` é a linha N de `site-drivesafe/previa/index.html`.
>   Os dois arquivos saíram do branch e estão no commit `9e8ad60`.
> - Os relatórios usam o nome antigo (DriveSafe) e os caminhos de antes da reorganização do repositório. Neste
>   consolidado, as linhas de código e do `README.md` foram conferidas em 11/09, já nos caminhos novos. A tabela de
>   caminhos está na seção 9.
> - Várias decisões chegaram depois da avaliação (seção 5). A mais importante: o produto vai gravar clipes curtos, e
>   isso derruba a promessa "nenhuma imagem é gravada", que os avaliadores tinham mandado manter.

## 1. Resumo

- **Notas:** mensagem e personas **3**, direção de arte **2**, imagens e prompts **2**, estrutura e conversão **3**,
  técnica e veracidade **3**. Média de 2,6, com todas as frentes na faixa "inaceitável".
- **O que mais pesou:** o transporte de passageiros não aparece (a palavra "ônibus" não está na página) e não há
  nenhuma foto, vídeo ou mapa do setor.
- **Afirmações falsas nos lugares mais vistos:** "Em piloto com transportadoras", o título, "só o evento sai" e telas com
  recursos que não existem. São 12 falsas e 13 exageradas, em 60 afirmações.
- **Visual e conversão:** o visual é o esqueleto de landing de SaaS para desenvolvedor, com a paleta do app já recusado.
  A conversão está morta: o WhatsApp tem `href="#"` e, no celular, faltam o menu e o "Já é cliente? Entrar".
- **O que fica e o que cai:** a base da detecção que a página descreve (escada de 1, 3 e 6 s, calibração individual,
  funcionamento sem internet) é verdadeira e fica. A promessa "nenhuma imagem é gravada" cai com a decisão de 11/09 de
  gravar clipes curtos.

## 2. Quadro de notas

### 2.1 Notas por critério

**F1 · Mensagem, posicionamento e personas: 3/10**

| Critério | Nota | Motivo principal |
|---|---|---|
| Entende-se em 5 s o que é e para quem | 4 | O "o que é" passa; o "para quem" não |
| Dores de cada persona | 3 | Só a madrugada e o vídeo com sindicato, da P1 |
| Cobertura de carga e de passageiros | 1 | Nenhuma ocorrência de ônibus, passageiro ou fretamento |
| Prova e credibilidade | 2 | Piloto que não existe e ninguém por trás |
| Objeções (alarme falso, custo, LGPD, motorista) | 3 | Só a privacidade e a falta de sinal têm resposta |
| Chamada adequada à venda B2B | 4 | "Pedir piloto" é certo, mas o botão não tem link |
| Tom sério, pt-BR natural, sem jargão | 5 | Frases sóbrias, com PERCLOS, EAR e JSON no caminho |
| Diferença frente à videotelemetria | 5 | O fato está lá, mas como detalhe técnico |

**F2 · Direção de arte, tipografia, layout e identidade: 2/10**

| Critério | Nota | Motivo principal |
|---|---|---|
| Estrutura | 2 | Esqueleto de landing de SaaS, com o mesmo hero da v1 |
| Tipografia | 2 | Par padrão do `create-next-app`, mono como enfeite |
| Cor e contraste | 2 | Paleta do app recusado; texto auxiliar abaixo do AA |
| Composição e ritmo | 3 | Seis blocos de peso igual, nada quebra a grade |
| Presença do mundo real | 1 | Nenhum `<img>` nem `<video>` |
| Componentes que denunciam template | 1 | 29 sinais listados |
| Coerência com os sites do Matheus | 2 | Nenhum dos diferenciais dele (mídia real, atos, grade editorial) |
| Seriedade para transporte sem clichê | 3 | Contida, mas com o clichê da "IA que enxerga" |
| Estrada e mapa (requisito novo) | 1 | Só o texto "São Paulo → Curitiba · BR-116" |

**F3 · Imagens, vídeo e prompts: 2/10**

| Critério | Nota | Motivo principal |
|---|---|---|
| Adequação à divulgação para logística e passageiros | 2 | Setor só em texto; 5 de 14 peças são papel e tacógrafo |
| Cobertura de cenas por seção e persona | 1 | Nenhum ônibus, van, CCO, garagem ou instalação |
| Realismo e contexto brasileiro | 4 | Bons indícios, com importações ("roadside diner") |
| Sinais de imagem de IA a evitar | 3 | Os prompts pedem o que atrai artefato |
| Consistência como série fotográfica | 3 | Sem imagem-âncora, elenco nem aparelho fixo |
| Uso no layout | 3 | Só 2 de 10 peças têm área de texto; nenhuma tem recorte de celular |
| Cuidados legais e éticos | 4 | Proíbe marca, mas duas peças vigiam o motorista |
| Produção e vídeo | 3 | Sem modelo, quadro final, curadoria nem custo |

**F4 · Estrutura, navegação e conversão B2B: 3/10**

| Critério | Nota | Motivo principal |
|---|---|---|
| Jornada e ordem das seções | 4 | Passeio pelo produto; o piloto é a última seção e não funciona |
| Escaneabilidade | 5 | Títulos curtos que não dizem público nem benefício |
| Caminhos para carga e passageiros | 1 | Nenhum caminho para passageiros |
| Demonstração de como funciona | 5 | A melhor parte, sem celular e sem resultado da revisão |
| Provas | 2 | Só dados de demonstração e um piloto que não existe |
| Chamadas (piloto, WhatsApp, Entrar) | 1 | Tudo aponta para `#` |
| Celular (400 px) | 3 | Sem menu, sem "Entrar", painel perde a frota |
| Conteúdo de apoio à decisão | 1 | Só a ficha de especificações |
| Microcopy | 4 | Boas frases misturadas com contradições |
| Como medir a conversão | 0 | Nada é medido |

**F5 · Técnica, acessibilidade, SEO, idiomas e veracidade: 3/10**

| Critério | Nota | Motivo principal |
|---|---|---|
| Veracidade | 2 | 25 de 60 afirmações falsas ou exageradas, mais 7 sem prova |
| Acessibilidade | 4 | Texto auxiliar de 3,08 a 3,87:1; sem menu no celular; animação sem pausa |
| Desempenho | 6 | Página leve, com fonte externa e animação que roda fora da tela |
| SEO | 2 | Título de prévia; sem description, Open Graph, hreflang nem dados estruturados |
| Prontidão PT/EN | 2 | "PT · EN" é texto solto; textos presos no JavaScript |
| Alinhamento com a stack | 5 | Tokens prontos; resets sem camada quebrariam no Tailwind 4 |

### 2.2 Temas que mais de uma frente avaliou

Cada frente tem critérios próprios. Esta tabela junta os que medem a mesma coisa.

| Tema | F1 | F2 | F3 | F4 | F5 |
|---|---|---|---|---|---|
| Carga e passageiros | 1 | problema alta (#7) | 1 (cenas) | 1 | leitura P2 |
| Prova e veracidade | 2 | — | problema alta (#5) | 2 | 2 |
| Mundo real e imagens | — | 1 | 2 (adequação) | — | sem plano de mídia |
| Identidade e anti-template | — | 1 (componentes) | 3 (série) | — | Geist do `create-next-app` |
| Chamadas e celular | 4 | — | — | 1 (chamadas), 3 (celular) | problema alta (#8) |
| Linguagem e jargão | 5 | 2 (tipografia) | — | 5 (escaneabilidade), 4 (microcopy) | — |
| Contraste e legibilidade | — | 2 | — | — | 4 |
| Objeções e apoio à decisão | 3 | — | — | 1 | piloto não verificável |

### 2.3 Notas por persona

A frente 5 fez a leitura por persona sem nota numérica.

| Persona | F1 | F2 | F3 | F4 | F5 | Média |
|---|---|---|---|---|---|---|
| P1 Renata · segurança viária, carga | 5 | 3 | 3 | 4 | pede o nome da transportadora do piloto e não recebe | 3,75 |
| P2 Carlos · fretamento e turismo | 2 | 2 | 1 | 2 | sente que não é para ele ("caminhão") | 1,75 |
| P3 Juliana · CCO de ônibus urbano | 3 | 4 | 1 | 3 | espera alerta ativo e acha um painel que precisa estar aberto | 2,75 |
| P4 Marcos · diretor financeiro | 2 | 3 | 2 | 2 | trava no jurídico com "conforme a LGPD" | 2,25 |
| P5 José · motorista | 4 | 2 | 2 | 3 | o sindicato acha uma frase falsa ("só o evento sai") | 2,75 |

**Leitura:** P2 é a persona mais perdida, e as quatro frentes com nota concordam. P1 é a única para quem a página foi
escrita, e mesmo ela perde no comitê.

## 3. Problemas repetidos entre frentes

Quanto mais frentes apontam o mesmo problema, mais confiável ele é. A ordem abaixo junta a gravidade e o número de frentes.

### 3.1 Os oito mais graves

| # | Problema | Frentes (gravidade dada) | Evidência principal | Correção em que as frentes concordam |
|---|---|---|---|---|
| 1 | **O transporte de passageiros não existe** | F1 #2 crítica · F2 #7 alta · F3 #3 crítica · F4 #2 crítica · F5 leitura P2 | Nenhuma ocorrência de "ônibus", "passageiro", "fretamento" ou "urbano"; "caminhão" em `v2:268, 352, 403`; chamada "Comece com cinco caminhões" (`v2:403`) | Portas de segmento no topo; "veículo" ou "cabine" nos trechos comuns; cenas de ônibus; piloto descrito por segmento |
| 2 | **Afirma um piloto que não existe** | F1 #1 crítica · F2 #13 baixa (selo com ponto verde) · F3 #5 alta · F4 #5 alta · F5 #1 crítica (V02, V60) | "Em piloto com transportadoras" (`v2:229`) e "protótipo em piloto" (`v2:412`), contra "Não há frota em piloto documentada" (`contexto.md`, linha "Situação real") e `PENDENCIAS.md:210-212` | Status verdadeiro, sem ponto verde de "ao vivo" (texto na seção 8.1) |
| 3 | **Telas e demonstração mostram o que o produto não faz** | F1 #16 · F2 (restrição 2 do mapa) · F3 #4 e #5 alta · F4 #10 e #13 · F5 #4 alta e #13 (V12, V20, V23 a V27) | Tela de alarme na cabine (`v2:276-288`), mas o alarme só é sonoro (`caixa/vision/alarm.py:1`); rota BR-116 (`v2:320`) sem GPS no produto (`caixa/vision/context.py:32-33`; `servidor/backend/main.py:52`); curva do olho por evento (`v2:298, 334-339`) que o evento não carrega; "Crítico" volta a "Normal" em 2 s (`v2:486, 505`), e no código fica 10 s (`caixa/vision/risk.py:24`) | Mostrar só o que o código entrega, ou rotular "Tela conceitual". Sem rota, sem janela de programa e sem tela de alarme até o hardware ser definido |
| 4 | **Nenhuma foto, vídeo ou mapa do setor** | F2 #2 crítica · F3 #1 crítica · F1 rec. 2 · F4 entrega E · F5 A4 | Nenhuma tag `<img>` ou `<video>` em `v2`; tudo é SVG em JS (`v2:416-569`) ou tela em CSS; pedido do Matheus: "imagens relacionadas a isso" (`contexto.md`, "O que o Matheus pediu") | Produzir a série de mídia antes de fechar o layout; enquanto não houver, espaço marcado com o nome da cena |
| 5 | **A privacidade é dita além do que o código garante** | F1 #13 média · F4 leitura P4 e S6 · F5 #2 crítica e #12 (V29, V31, V32, V33) | "Só o evento sai dele" (`v2:352`), mas o estado ao vivo sai a cada 15 s (`caixa/vision/driver_monitor.py:182-207`; `caixa/vision/sync.py:59`); "conforme a LGPD" (`v2:353`) sem parecer nem RIPD (`README.md:464`); a política da caixa só consulta os consentimentos de perfil e de envio dos sinais de ativação, e o recebimento de eventos não confere o de monitoramento (`servidor/backend/routes/device_api.py:51-58, 107-144`) | Tirar "conforme a LGPD" e "só o evento sai". **Com a decisão de 11/09 sobre clipes curtos, nenhuma promessa de privacidade entra antes das regras dos clipes** (seção 6.2) e das brechas da seção 8.8 |
| 6 | **Conversão morta e celular sem navegação** | F1 #8 e #17 · F4 #1 crítica e #3 alta · F5 #8 alta e #16 | WhatsApp com `href="#"` (`v2:406`); "Entrar" com `href="#"` (`v2:219`), escondido abaixo de 640 px (`v2:48-49`); menu some abaixo de 992 px sem botão (`v2:44-45`); nenhum `tel:` | Link `wa.me` com mensagem por segmento, `tel:`, botão de menu e "Já é cliente? Entrar" em todas as larguras |
| 7 | **O motorista não tem voz e o visual é de vigilância** | F1 #7 alta · F2 #5 alta · F3 #6 alta · F4 #7 média · F5 leitura P5 | Rosto em pontos com mira e olhos contornados de vermelho (`v2:460-468`); "João Pereira · Crítico" (`v2:307`); a v1 dizia "O motorista vê os próprios dados e o que autorizou" (`v1:254`), e a v2 tirou | Seção "Para quem dirige", em segunda pessoa; decisões da revisão visíveis ("alarme falso", "motorista orientado"); motorista competente nas fotos; nenhuma sobreposição biométrica em rosto realista |
| 8 | **Título e promessas de tempo imprecisos** | F1 #3, #11 e #12 · F4 #8 e #17 · F5 #3 crítica e #6 alta (V03, V04, V13, V19) | "Microssono dura 1 segundo. O alarme também." (`v2:230`), com sirene de 2 s (`caixa/vision/alarm.py:18-21`); "antes de o caminhão sair da faixa" (`v2:268`); "avisado imediatamente" (`v2:273`) contra a fila sem internet (`v2:373`) e o envio a cada 5 s (`caixa/vision/sync.py:58-59, 82`) | Textos da seção 8.1 |

### 3.2 Outros problemas repetidos

| # | Problema | Frentes | Evidência principal | Correção |
|---|---|---|---|---|
| 9 | Esqueleto de SaaS para desenvolvedor e jargão técnico | F2 #1 crítica, #4 e #6 · F3 #1 · F1 #10 · F4 #10 e #12 · F5 A7 | Geist e Geist Mono (`v2:10, 28-29`); hero com texto e widget (`v2:58`); JSON (`v2:365-371`); PERCLOS e EAR (`v2:255, 454`); janela "— ▢ ✕" (`v2:301`) | Direção C com lista de proibições; jargão traduzido; ficha técnica separada para a TI |
| 10 | O uso de celular fica escondido na ficha técnica | F1 #5 alta · F4 #6 alta | Única menção em `v2:389`; o produto detecta celular na mão, no ouvido e olhando por mais de 2 s (`README.md:138-142`) | "Sono e celular" desde o topo e dentro da cena da cabine |
| 11 | Faltam objeções, oferta e quem está por trás | F1 #6 e #8 · F4 #4 e #14 · F5 V54 a V57 · F2 leitura P4 | Só a ficha técnica (`v2:379-397`); piloto numa frase (`v2:404`); rodapé sem empresa (`v2:412`) | Blocos "Como é o piloto", "Perguntas de quem decide" e "Quem faz", com as respostas da seção 7 |
| 12 | Ficha técnica exagerada | F1 #10 e #15 · F4 leituras P1 e P5 · F5 #5 alta (V35, V45, V49, V50) | "12 pontos por olho" (`v2:359`), mas são 6 (`caixa/vision/face.py:35-37`); "óculos escuros detectados" (`v2:391`); "Roda em Raspberry Pi" (`v2:392`), que nunca foi medido (`README.md:424`) | Textos da seção 8.1 |
| 13 | Contraste baixo e rótulos ilegíveis no celular | F2 #11 e #12 · F4 entrega B · F5 #7 alta e #16 | `#6f6f69` sobre `#0b0c0e` dá 3,87:1 (F5 A1); rótulo do SVG com 5,8 px em 400 px (`v2:442`) | Texto pequeno com 4,5:1 ou mais; rótulos em HTML, fora do SVG |
| 14 | Público antigo: universidades e editais | F1 #14 · F3 #11 · F4 #11 · F5 V58 | "Também atendemos universidades e editais de pesquisa." (`v2:404`) | Apagar |
| 15 | Efeitos já recusados e animação sem fim | F2 #10 · F3 #2 crítica · F5 #11 | Brilho vermelho (`v2:70`); laço de 9 s com `requestAnimationFrame` (`v2:476-533`); o roteiro de imagens antigo pede grão, tracejado e piscada | Movimento só onde explica algo, com pausa e versão parada |
| 16 | Nome disputado e marca genérica | F2 #14 · F4 microcopy · F5 #10 | "DriveSafe" já é usado pela Embitel e por um app no Google Play (F5 Anexo D); a marca alterna entre "DriveSafe" e "DriveSafe AI" (`v2:209, 412`) | **Resolvido em 11/09: RotaGuard.** Falta conferir no INPI |

## 4. Conflitos e decisão proposta

Os dois primeiros conflitos surgiram depois da avaliação: as decisões de 11/09 contrariam o que as frentes tinham
recomendado.

| # | Conflito | Quem diz o quê | Decisão proposta |
|---|---|---|---|
| 1 | **"Sem vídeo do motorista" como diferencial × clipes curtos** | F1 fez de "sem vídeo por projeto, não por configuração" o espaço do produto e a resposta ao sindicato e à P5. F4 respondia "Grava vídeo?" com "não" (pergunta frequente 1). F2 desenhou a direção C em torno da legenda "a imagem não passa daqui". F5 marcou "nenhuma imagem é gravada" como verdadeira, mas só para a caixa de hoje (V08, V37, V52). Em 11/09, o Matheus decidiu gravar clipes curtos quando um sinal se repete. | **Tirar "sem vídeo" do posicionamento, dos textos e das telas.** A fronteira da direção C continua como recurso, com a legenda trocada por algo verdadeiro depois das regras dos clipes (por exemplo: "a viagem inteira não sai daqui; saem o registro e, só quando um sinal se repete, um clipe curto"). Achar outro diferencial é a pergunta 17. A F1 mostra que a Nauto já só envia vídeo em incidente crítico, então "clipe só em evento", sozinho, não é exclusivo. |
| 2 | **Frota ao vivo × relatório na chegada** | F1 ("a empresa recebe o evento"), F4 (viagem com "trecho sem sinal" e "sinal volta"; frota ordenada por conexão) e F2 (Ato III: "o evento sobe como registro", CCO) contam o envio ao vivo como o fluxo principal. F5 confirmou "A frota inteira ao vivo" na API (V21). Em 11/09, o fluxo principal passou a ser: registro na caixa → recolhimento na chegada → relatório gerado ao conectar. O envio ao vivo virou secundário. | **No site, o fluxo principal é chegada → conexão → relatório.** A tela ao vivo só entra se o envio ao vivo continuar (pergunta 10), e como opção. O Ato III da direção C passa a mostrar a caixa voltando e o relatório saindo. Riscos para P1 e P3 na seção 6.2. |
| 3 | **Site claro × escuro** | F2 (#3 e as três direções): fundo claro, com a noite só na fotografia. F3 (pergunta 8 e D.3) ainda considera o site escuro da v2 e o âmbar da interface. F5 (A1 e A7) calculou os contrastes e os tokens sobre o fundo escuro da v2. O vault tem tema escuro como padrão (`meu-estilo-de-sites.md:83`, citado pela F2). | **Claro**, como prevê a direção C: neutros de concreto e asfalto nas partes de texto, escuro só dentro das cenas fotográficas e da tela do produto, sem âmbar na página. Recalcular os contrastes da F5 para a paleta clara. É exceção ao padrão escuro do vault por causa da recusa do app escuro; registrar na nota do projeto. |
| 4 | **Página única × páginas por segmento** | F4 (entregas C e D): home que distribui, 3 páginas de segmento e páginas por tema, porque o link circula por WhatsApp e LinkedIn. F1 (#2): duas entradas, Carga e Passageiros. F2 (direções A e C) e F3 (par gêmeo S01/S02): uma página só, com seletor que troca rota e fotos. | **Home única na direção C, com portas de segmento já na primeira tela** e a escolha caminhão ou ônibus antes do Ato II. **Páginas de segmento depois**, com os mesmos componentes e com URL e prévia de link próprias. Quantos segmentos entram (2 ou 3) é a pergunta 6. |
| 5 | **Cenas presas na rolagem × celular** | F2 (direção C): três cenas presas com ScrollTrigger. F4 (entrega E): no celular, nada de prender a rolagem, porque o pedido de piloto não pode ficar atrás de uma animação. | **Cenas presas só no computador.** No celular, a sequência vira quadros empilhados ou vídeo curto sem prender, com WhatsApp e "Ligar" sempre à vista no cabeçalho ou numa barra fixa. |
| 6 | **Lead-gate do vault × "sem formulário"** | F4 (I.1): `meu-estilo-de-sites.md:102` e `site-dra-jania.md:31, 160` pedem nome e telefone antes de abrir o WhatsApp; o contexto do site proíbe formulário. | **Sem lead-gate.** A origem vem do código na mensagem do WhatsApp (F4 entrega H). A área com PIN para baixar o app (decisão de 11/09) é acesso de cliente, não cadastro. Registrar a exceção na nota do projeto. |
| 7 | **Estrada rejeitada no app × estrada pedida no site** | O app recusou tracejado, marcos de km e animação de estrada (`PENDENCIAS.md:8`). No site, o Matheus pediu estradas e mapa-múndi. F2, F3 e F4 concordam: só com informação. Divergem no que o mapa-múndi diz: faixa da madrugada ao vivo (F2 e F3), mapa das fontes dos limiares (F4 S10) ou número mundial de mortes (`referencias.md:37`), que a F4 manda não usar na abertura. | **Estrada e mapa só como dado real ou navegação**, nunca como textura. O mapa-múndi entra **uma vez**, no Ato I da direção C, com a faixa da madrugada calculada e sem arcos entre continentes. As fontes dos limiares ficam na ficha técnica como lista com país e link, sem segundo mapa-múndi. Nenhum número mundial na abertura. |
| 8 | **"A frota sobre a malha" × nenhum pino de veículo** | F2 (direção C, Ato III, e direção A): a frota de exemplo aparece sobre a malha do Brasil. F3 (C.1, princípio 2), F4 (I.5) e F5 (V24): o produto não registra localização, então nada de pino de veículo, "frota ao vivo no mapa" ou rota com hora. | **No Ato III, a malha é fundo geográfico, sem pontos de veículo.** A frota aparece como lista ou tela recortada. Qualquer trajeto leva a legenda "rota ilustrativa · o RotaGuard não registra localização". Só muda se houver integração com rastreador (pergunta 12). |
| 9 | **Tela de alarme na cabine: manter × não existe** | F1, F2 e F4 querem manter "Pare em local seguro" e a tela do alarme (`v2:276-289`) como peça central. F3 (#4) e F5 (V20): no código o alarme é só sonoro, não existe tela e a frase "Pare em local seguro" não está no repositório. | **A tela sai como função.** O alarme aparece como som (sirene de 2 s) e pela consequência: parar em segurança (cena S04 da F3). "Pare em local seguro" continua como frase do site dirigida ao motorista, não como texto numa tela. Se a caixa tiver tela ou luz (pergunta 9), a tela volta rotulada como conceito. |
| 10 | **"Diário de bordo"** | `PENDENCIAS.md:215` ainda registra a direção como aprovada. F2: substituir como espinha e aproveitar três peças. F3: descartar 9 das 14 peças do roteiro, feitas para esse conceito. F4 (I.3): confirmar se ainda vale. | **Aposentado como espinha**, porque a direção C foi adotada. Ficam o tempo como dado (hora do evento, madrugada, direção contínua) e, se o Matheus quiser, "diário de bordo" como nome do registro que o relatório mostra, o que combina com o log como peça principal. Atualizar `PENDENCIAS.md`. |
| 11 | **Direções antes de codar × site já em construção** | F2 (rec. 1) e a regra do vault pedem 2 ou 3 direções mostradas antes da primeira linha de código. Em 11/09, o Matheus pediu o site direto em Next.js + Tailwind, sem rodada de prévias. | **Vale o pedido do Matheus.** A direção C é o ponto de partida e pode ser trocada. Registrar a exceção na nota do projeto e mostrar a primeira tela pronta, em 1440 e 400 px, antes de avançar para os Atos II e III. |
| 12 | **Imagem gerada × só foto real** | F3 (pergunta 1): IA pode ir ao site com a legenda "Imagem ilustrativa". F5 (rec. 8) e `PENDENCIAS.md:211`: nenhuma imagem de IA pode parecer o aparelho real, e a cabine pede foto real com consentimento. | **Agora, fotos provisórias de licença livre, com crédito.** IA só com a legenda "Imagem ilustrativa", nunca mostrando o aparelho como produto real nem uma instalação num cliente. A política final é a pergunta 22. |
| 13 | **Aparelho canônico da F3 × hardware novo** | F3 (D.6): câmera do tamanho de uma caixa de fósforo sobre o painel, com o processamento escondido atrás dele. Matheus (11/09): caixa com Raspberry Pi (provável Pi 4 de 4 GB) e câmera acoplada, recolhida na chegada e ligada por cabo para gerar o relatório. | **Revisar o bloco do aparelho em `docs/site/midia/`** para uma caixa única e removível, com câmera, e acrescentar a cena da chegada (a caixa sendo conectada na base). Medidas reais antes do render no Blender. Até lá, o aparelho não aparece em foto como produto final. |

## 5. O que já foi decidido desde a avaliação

Todas as decisões são de 11/09/2026, depois dos relatórios. **Nenhuma das mudanças de função abaixo existe no código
ainda.**

| Decisão | Efeito sobre a avaliação |
|---|---|
| **Pastas novas:** `docs/site/contexto.md`, `docs/site/personas.md` e `docs/site/avaliacoes/2026-09-11-previa-v2/`. O roteiro de mídia sai de `prompts-imagens.md` e passa para `docs/site/midia/` (`README.md` como índice, `00-regras-gerais.md`, `01-fundos.md`, `02-fotos.md`, `03-banners.md` e `04-videos.md`). | Os relatórios citam os caminhos antigos (seção 9). |
| **As prévias em HTML saíram do branch**, porque o Matheus não quer site em HTML. Continuam no commit `9e8ad60`. Os prints avaliados estão em `prints-avaliados/v1/` e `prints-avaliados/v2/`. | As linhas `v2:N` e `v1:N` só podem ser relidas pelo histórico do git. |
| **Repositório reorganizado** em `caixa/`, `servidor/`, `painel/`, `ferramentas/`, `implantacao/`, `tests/`, `docs/` e `site/`. | Caminhos de código mudam (seção 9). O `README.md` já usa RotaGuard, e os identificadores `DRIVESAFE_*` ainda não foram renomeados (`README.md:1-4`). |
| **Nome do produto: RotaGuard** (antes DriveSafe AI). | Responde a F2·5 e resolve o risco de "DriveSafe" já existir na categoria (F5 #10). **Falta conferir RotaGuard no INPI** e definir o domínio. |
| **Stack:** o site é feito já em Next.js + Tailwind (com next-intl), em `site/`, para o Matheus modificar. | A F5 A7 (tokens, primitivos, componentes e conteúdo tipado) vira guia de implementação. As versões da F5 A8 são de 11/09 e devem ser conferidas no registro na hora de instalar. |
| **Direção C "Escalas"** (mundo → Brasil → rodovia → cabine → frota) como ponto de partida. O Claude escolheu essa direção por juntar mapa-múndi, estradas, cabine e frota, que foram pedidos do Matheus. Ele pode trocar. Não houve rodada de prévias das três direções, por pedido dele. | Responde, de forma provisória, a F2·2 (estrutura), F2·6 e F3·8 (site claro, noite só nas fotos) e F4·20 ("Diário de bordo"). Os riscos da C continuam: custo, produto tarde demais para P1, peso no celular e o corte virar zoom (F2). |
| **Função do produto, nas palavras do Matheus:** "nem toda hora deve ser gravada, apenas as partes que o sensor detecta algo muito recorrente, tipo sonolência frequente durante muito tempo e algum tipo de uso de anfetamina, e o principal analisado e mais importante deve ser a log, que seria o registro. A empresa, quando o motorista chegar, deve recolher o equipamento e, ao conectar, o sistema deve reconhecer o equipamento e gerar o relatório. A funcionalidade dele vai ser basicamente essa; quanto às gravações, devem ser curtas." | **Não existe no código.** Hoje a caixa não grava imagem nenhuma (`README.md:165`) e envia os eventos pela rede ao servidor (`README.md:27-31`). Consequências: a pergunta "sem vídeo é regra permanente?" (F1·5) está **respondida: não**; toda frase do tipo "nenhuma imagem é gravada" passa a ser falsa para o produto; o fluxo principal vira registro na caixa, recolhimento e relatório ao conectar; e o envio ao vivo vira secundário. Riscos novos na seção 6.2. |
| **Hardware provável: Raspberry Pi 4 de 4 GB, com câmera acoplada.** O Matheus disse primeiro "provavelmente o 3"; sobre o Pi 3, depois disse "eu não sei" e pediu opinião. A recomendação dada foi o Pi 4 de 4 GB: CPU mais rápida, 4 vezes a memória do Pi 3, porta USB-C que funciona como dispositivo (a caixa ligada por cabo é reconhecida) e codificador H.264 no chip para os clipes, que o Pi 5 não tem. Cuidados: fonte de 5 V/3 A a partir de 12 ou 24 V, desligamento seguro e calor na cabine. | Responde em parte a F1·6, F2·7 e F4·7. Riscos e o que medir na seção 6.1. |
| **Pupila e pulseira:** a leitura de pupila, se vier, será no celular do motorista. A pulseira cardíaca fica para muito depois. | A pupila sai da caixa, o que muda o módulo de sinais de ativação dentro dela (seção 6.3). |
| **App instalável:** painel mais modo de teste com a câmera do próprio aparelho. Instaladores nativos para Windows, macOS, Linux e Android, gerados com Tauri 2 no GitHub Actions, e PWA no iPhone. O download fica no site, para quem entra com o PIN. | Responde a F5·6 (formato do painel) e em parte a F4·2 (destino de "Já é cliente? Entrar"). O site ganha uma área de download com PIN. Substitui o "formato do painel em aberto" de `PENDENCIAS.md:7`. |
| **Mídia provisória em produção por outro agente:** fotos de licença livre e mapas com dados reais (DNIT, IBGE, Natural Earth), além da divisão do roteiro em `docs/site/midia/`. | Ataca o problema 4. A série final, a âncora de estilo e a política de IA seguem em aberto. |

## 6. Riscos novos trazidos pelo hardware e pela nova função

Linhas de código e do `README.md` conferidas em 11/09, depois da reorganização.

### 6.1 Raspberry Pi 4 de 4 GB: por que ele, e o que ainda precisa ser medido

- **Por que não o Pi 3:**
  - O Pi 3 Model B e o B+ não funcionam como dispositivo USB. O modo "gadget" existe no Zero, Zero W e Zero 2 W, no 3
    Model A+, no Pi 4, no Pi 5 e no Compute Module 5
    ([raspberrypi.com, 21/01/2026](https://www.raspberrypi.com/news/usb-gadget-mode-in-raspberry-pi-os-ssh-over-usb/)).
    Com um Pi 3, "conectar por cabo e o sistema reconhecer" exigiria rede ou retirar o cartão.
  - O Pi 3 B+ tem 1 GB de memória
    ([ficha oficial](https://www.raspberrypi.com/products/raspberry-pi-3-model-b-plus/)).
- **O que a ficha oficial do Pi 4 diz**
  ([raspberrypi.com](https://www.raspberrypi.com/products/raspberry-pi-4-model-b/specifications/)):
  - processador Cortex-A72 de 64 bits a 1,8 GHz e versões com até 8 GB de memória;
  - alimentação de 5 V pela USB-C, com no mínimo 3 A;
  - H.264 com gravação em 1080p30 e porta CSI para câmera;
  - produção garantida até pelo menos janeiro de 2034;
  - a ficha não lista relógio com bateria.
- **O Pi 5, em comparação**
  ([raspberrypi.com](https://www.raspberrypi.com/products/raspberry-pi-5/)):
  - tem relógio com bateria e CPU "até três vezes mais rápida que a geração anterior";
  - lista só decodificador de vídeo, sem codificador no chip, o que é confirmado no fórum oficial
    ([Raspberry Pi Forums](https://forums.raspberrypi.com/viewtopic.php?t=376952)).
- **Ganho de CPU do Pi 4 sobre o Pi 3:** varia muito conforme o teste. Para este código, só medindo.
- **O que o repositório mediu:**
  - só um PC com Windows 11 e CPU de 12 threads: 26 fps e 11 ms por quadro, com o celular numa thread separada;
  - nesse PC, o detector de celular leva cerca de 73 ms por imagem de 640 px e o de mãos, cerca de 66 ms;
  - "No Raspberry Pi ainda não foi medido" (`README.md:415-424`), e o Pi real está na lista do que não foi testado
    (`README.md:448`).
- **O que pode faltar mesmo no Pi 4:**
  - A caixa roda quatro modelos: rosto, classificador de olho, detector de celular e pontos das mãos
    (`README.md:59-60, 135-136`). Agora ela também vai gravar clipes ao mesmo tempo.
  - Abaixo de cerca de 25 fps, a duração da piscada deixa de valer como gatilho (`README.md:131`), e os sinais de
    ativação perdem as sacadas e baixam a confiança (`caixa/vision/activation.py:59, 79, 291`).
  - Se o fps cair, o README manda desligar o celular com `--sem-celular` (`README.md:283`). Isso tira do produto a dor
    principal da P1 e da P3.
- **Energia e registro:**
  - O veículo tem 12 ou 24 V, e a placa pede 5 V com 3 A. Precisa de conversor e de desligamento seguro quando a
    ignição cai.
  - Na comunidade, a causa mais citada de cartão corrompido é cortar a energia durante uma gravação
    ([Raspberry Pi Forums](https://forums.raspberrypi.com/viewtopic.php?t=291792); fórum, não documentação oficial).
    Se o registro é a peça principal, perder o cartão é perder o produto.
- **Hora dos eventos sem relógio com bateria:**
  - Hoje a correção da hora depende de a caixa não ter reiniciado. A idade do evento só é calculada no mesmo boot
    (`caixa/vision/event_queue.py:94-96`).
  - Sem essa idade, o servidor usa o relógio da caixa ou, se a data for absurda, a hora do recebimento
    (`servidor/backend/routes/device_api.py:61-69`).
  > [!note] Hipótese, confirmar no teste
  > No fluxo "desliga na ignição e só conecta na chegada", a caixa reinicia antes de falar com o computador, e as horas
  > do relatório podem sair erradas. Soluções possíveis: relógio com bateria acoplado ou hora do GPS.
- **Calor:** entre 80 e 85 °C, os núcleos são reduzidos aos poucos, e 85 °C é o limite em todos os modelos
  ([documentação do Raspberry Pi](https://github.com/raspberrypi/documentation/blob/master/documentation/asciidoc/computers/raspberry-pi/frequency-management.adoc)).
  > [!note] Hipótese, medir
  > Caixa fechada numa cabine parada ao sol, gravando clipes, pode chegar a essa faixa.
- **Como medir antes de travar o hardware:**
  1. Rodar `caixa/run_monitor.py` num Pi 4 de 4 GB real, lendo um vídeo gravado. O log mostra fps e tempo por quadro a
     cada minuto (`README.md:318`).
  2. Testar três configurações: completo; completo gravando clipe; sem celular.
  3. Anotar fps médio e p95, memória e temperatura dentro da caixa.
  4. Cortar a energia no meio de uma gravação e conferir se o registro sobrevive e se a hora sai certa.
  - **Critério do próprio código:** 25 fps ou mais com o celular ligado.
  - **No site, até a medição:** "Testado em computador com Windows. Raspberry Pi: em preparação." (V50).

### 6.2 Clipes curtos e registro como peça principal

Nada disto existe no código. Hoje a caixa guarda uma fila de eventos em SQLite, sem imagem (`README.md:165, 180`), envia
tudo pela rede e apaga da caixa os eventos já enviados depois de 30 dias (`caixa/vision/event_queue.py:117`).

- **LGPD:**
  - Vídeo do rosto de um motorista identificado é dado pessoal e pode ser tratado como biométrico e, portanto, sensível
    (LGPD, art. 5º, II; leitura da ANPD detalhada em F5 C9).
  - **Retenção:** quanto tempo um clipe fica, e quem apaga (LGPD, art. 6º, III, necessidade; art. 16, eliminação ao fim
    do tratamento).
  - **Acesso:** quem assiste e com que registro. O servidor já tem trilha de auditoria (`servidor/backend/database.py:253`),
    mas não para clipes, que não existem.
  - **Criptografia na caixa:** a caixa sai do veículo todo dia. Uma caixa perdida com clipes sem criptografia expõe o rosto
    do motorista (LGPD, art. 46, medidas de segurança). Hoje a pasta da caixa não é criptografada (`README.md:180`).
  - O texto da lei foi conferido pela F5 em fontes secundárias. **Conferir no Planalto antes de citar no site.**
- **O motorista e o sindicato:** os medos da P5 voltam ao centro: ser filmado, "a empresa quer me vigiar" e imagem
  vazando (`personas.md:105-107`). As respostas da F1 e da F4 baseadas em "não grava" deixam de valer. Para ter o que dizer,
  faltam as regras: o que dispara um clipe, quanto dura, quem vê, quando apaga e se o motorista vê os próprios clipes
  (pergunta 18).
- **Clipe por "uso de anfetamina":**
  - Com a pupila fora da caixa, o módulo de ativação fica com quatro sinais de peso 0,15 cada, descritos como "literatura
    divergente" ou "hipótese" (`README.md:79-82`; `caixa/vision/activation.py:29-35`).
  - O módulo "não detecta droga e nunca deve ser apresentado assim" (`caixa/vision/activation.py:1`).
  - Nem o clipe, nem o relatório, nem o site podem dizer "anfetamina". O rótulo possível é "sinais compatíveis com
    ativação atípica".
  - A lei já prevê exame toxicológico para o motorista profissional (seção 6.3).
- **Integridade do registro:**
  - Se o log é a prova principal, precisa mostrar quando foi alterado. Caminhos possíveis: assinar cada evento com a chave
    da caixa e encadear os resumos (hash). A NIST descreve a checagem de integridade de log por comparação de resumos
    ([NIST SP 800-92](https://csrc.nist.gov/pubs/sp/800/92/final)).
  - O que já existe e ajuda: token próprio por caixa, com só o hash no servidor (`README.md:34-35`), e reenvio sem
    duplicar (`README.md:36`).
  - O que falta: assinatura dos eventos, cadeia de custódia (quem recolhe e quem conecta) e hora confiável (seção 6.1).
- **Operação por persona:**
  > [!note] Hipótese, confirmar nas conversas com as personas
  > - A P1 tem rotas SP–PR–SC–RS e operação 24 h (`personas.md:14`). Uma carreta que passa dias fora da base só
  >   entregaria o registro quando voltasse.
  > - A P3 tem 620 ônibus em 9 garagens (`personas.md:59`). Recolher e conectar 620 caixas por dia pesa.
  > - Para as duas, o envio ao vivo pode continuar necessário (pergunta 10).
- **No site:**
  - "nenhuma imagem é gravada", "0 imagens", "sem vídeo do motorista" e "só o evento sai" ficam proibidos;
  - clipes, relatório ao conectar e registro à prova de alteração só entram quando existirem.

### 6.3 Pupila no celular do motorista, pulseira e "uso de drogas"

- **Pupila no celular:**
  - O código diz que a pupila só é medida com câmera infravermelha. Em câmera comum, "a íris escura quase não se
    distingue da pupila" (`caixa/vision/pupil.py:1-5`; `README.md:88-90`).
    > [!note] Hipótese, confirmar
    > As câmeras que os celulares liberam para apps são coloridas, sem infravermelho. Se for assim, a leitura no celular
    > não tem a medida em que o módulo se baseia.
  - "A pupila responde muito mais à luz do que a qualquer substância" (`caixa/vision/pupil.py:7`). Antes e depois da rota,
    a comparação exige a mesma luz.
  - Ler no celular **durante** a rota bate de frente com o alerta de celular do próprio produto e com o CTB, art. 252
    (`README.md:142`). Só faz sentido com o veículo parado.
  > [!warning] Interpretação, confirmar com advogado
  > Se for o celular pessoal do motorista, a empresa trataria dado sensível num aparelho do empregado. Isso pesa na LGPD
  > e na relação de emprego.
- **Pulseira (adiada):** não existe no código (só uma opção antiga em `PENDENCIAS.md:164`). Quando voltar, os pontos são
  estes:
  - frequência cardíaca muda com emoção e estresse, temperatura, remédios e esforço
    ([American Heart Association](https://www.heart.org/en/health-topics/high-blood-pressure/the-facts-about-high-blood-pressure/all-about-heart-rate-pulse);
    a página recusou a leitura direta, e a lista veio do resumo da busca);
  - pulseira óptica erra mais com movimento
    ([Bent et al., 2020](https://www.nature.com/articles/s41746-020-0226-6));
  - é dado de saúde, portanto sensível (LGPD, art. 5º, II).
- **Nenhum desses sinais identifica droga sozinho:**
  - O código diz: "Estresse, cafeína, pouca luz, conversa e medicamentos causam os mesmos sinais"
    (`caixa/vision/activation.py:13-14`; `README.md:19-20`).
  - Não há base pública de motoristas sob efeito de anfetamina, e validar exige comitê de ética (`README.md:94-95, 455`).
  - Com sonolência presente, os sinais de ativação não são marcados (`caixa/vision/activation.py:297-298`;
    `README.md:86-87`). Depois de uma noite dirigindo, o que aparece é cansaço.
- **O que a lei já prevê para droga:** o motorista profissional faz exame toxicológico com janela de pelo menos 90 dias
  na admissão e no desligamento (CLT, art. 168, §6º), e o condutor das categorias C, D e E também faz (CTB, art. 148-A).
  O resultado é restrito ao interessado ([SETCESP, 2021](https://setcesp.org.br/noticias/alteracoes-exame-toxicologico-motoristas/)).
  > [!warning] Interpretação, confirmar com advogado
  > Um índice de pupila, pulseira ou câmera não substitui esse exame e não prova uso. Se chegar ao gestor como "indício de
  > droga", vai na direção contrária do sigilo que a lei dá ao exame.
- **No site:**
  - nunca "detecta drogas", "identifica uso de anfetamina" ou "exame";
  - se o módulo for citado: "sinais compatíveis com ativação atípica, sem diagnóstico" (F1, "O que NÃO pode ser
    prometido");
  - **proposta:** deixar pupila, pulseira e sinais de ativação fora do site de lançamento (pergunta 13).

### 6.4 Câmera infravermelha e óculos escuros

- **A caixa ainda precisa de câmera infravermelha**, mesmo sem medir pupila: é ela que funciona à noite e "atravessa
  muitos óculos escuros" (`README.md:278-280`). Nunca foi testada, assim como a Pi Camera Module e o buzzer
  (`README.md:449-450`).
- **Com câmera comum e óculos escuros**, o sistema desliga as medidas do olho: não dispara alarme falso, mas também não
  detecta sono pelos olhos (F5 V49 e C7).
- **No setor:**
  - quem usa câmera infravermelha diz o mesmo: os olhos precisam estar visíveis através da lente; lentes muito escuras ou
    espelhadas atrapalham; e, sem ver os olhos, o sistema não dispara alerta pelos olhos
    ([Digicore](https://digicore.com.au/sunglasses-and-fatigue-cameras-what-drivers-need-to-know/));
  - a Seeing Machines não recomenda óculos com aro grosso ou revestimento refletivo
    ([página do motorista](https://guardian.seeingmachines.com/driver-info-anz)) e publica uma lista de óculos testados
    ([PDF](https://tcp.seeingmachines.com/wp-content/uploads/Recommended-and-not-Recommended-Eyewear-Advice-for-Guardian.pdf)).
- **850 × 940 nm:**
  - a 850 nm, o iluminador aparece como um brilho vermelho escuro que o motorista vê e pode distrair à noite;
  - a 940 nm, a luz fica quase invisível e sofre menos interferência do sol
    ([Konica Minolta, via AZoSensors, 2021](https://www.azosensors.com/article.aspx?ArticleID=2163)).
- **Câmera acoplada ao Pi 4:**
  - a porta CSI aceita a Camera Module 3, que tem versão sem filtro infravermelho (NoIR) e precisa de iluminador separado
    ([raspberrypi.com](https://www.raspberrypi.com/products/camera-module-3/));
  - à noite, os clipes gravados com infravermelho saem em tons de cinza.
- **Efeito no site e nas imagens:** frases sobre noite e óculos só depois de decidir a câmera. As cenas noturnas de
  `docs/site/midia/` dependem de 850 ou 940 nm (pergunta 9).

## 7. Decisões que dependem do Matheus

As 5 frentes fizeram 59 perguntas, e as decisões de 11/09 criaram outras. Abaixo, 25, sem repetição, das mais importantes
para as menos importantes em cada grupo. "Frentes" indica de onde a pergunta veio.

**Responder primeiro, porque travam a publicação:** 18, 17, 3, 1, 10, 6, 19, 8, 14 e 4.

**Contato e acesso**

1. **Qual número atende no WhatsApp e na ligação? Quem responde e em quanto tempo?** · F1·9, F4·1, F5·10 · aberta
2. **Área de download com PIN: quem emite o PIN? Ela fica em "Já é cliente? Entrar"? O motorista também baixa o app?** ·
   F4·2, F5·6 · em parte: app nativo para Windows, macOS, Linux e Android, mais PWA no iPhone, com download no site
   para quem entra com o PIN (11/09)

**Oferta e piloto**

3. **Status real: alguma frota usa ou testa o produto, mesmo informalmente? Quem autoriza ser citado? Aceita o texto
   "Protótipo em testes · vagas para o primeiro piloto"?** · F1·1, F4·14, F5·1 · aberta
4. **Piloto: é pago ou gratuito? Quantos veículos por segmento, por quanto tempo, o que mede antes e depois e o que
   acontece no fim?** · F1·2, F4·4, F5·2 · aberta
5. **Cobrança: por veículo por mês, comodato ou venda? Qual o prazo? A instalação é cobrada? O modelo pode aparecer no
   site, mesmo sem valor?** · F1·3, F4·5 · aberta
6. **Segmentos no lançamento: carga e logística, fretamento e rodoviário e ônibus urbano entram juntos, ou começa por um?
   Vans e última milha entram?** · F1·8, F4·3 · aberta
7. **Aceita uma seção falando direto com o motorista, em segunda pessoa, e uma página para o gestor mandar aos
   motoristas?** · F1·11 · aberta. Com os clipes, essa seção precisa das respostas da pergunta 18

**Hardware e instalação**

8. **Confirma o Pi 4 de 4 GB e aceita medir antes de travar: detecção mais clipe, temperatura e corte de energia (seção
   6.1)? Qual câmera?** · F1·6, F4·7 · em parte: Pi 4 de 4 GB provável, com câmera acoplada (11/09)
9. **A caixa terá tela, luz de status ou luz de alerta? A câmera infravermelha será de 850 ou 940 nm?** · F3·2, F5·7 ·
   aberta
10. **Recolhimento na chegada:**
    - a caixa sai do veículo em toda chegada, todo dia?
    - quem conecta, e em que computador?
    - o envio ao vivo continua para quem passa dias fora da base (P1) ou tem centenas de veículos (P3)?
    - aceita um relógio com bateria ou a hora do GPS para o registro sair com a hora certa?

    Nova (11/09) · aberta
11. **Instalação e suporte:**
    - fixação de encaixe rápido para tirar e pôr a caixa;
    - conversor de 12 ou 24 V para 5 V/3 A, com desligamento seguro;
    - tempo por veículo e quem instala;
    - canal, horário, regiões e prazo de troca do suporte;
    - demonstração na garagem do cliente.

    F1·6 e 7, F4·6, 7 e 8 · aberta
12. **Integrações: o produto vai ler a velocidade do rastreador (e quem escreve essa integração)? Como fica o revezamento,
    com dois motoristas no mesmo aparelho? Relatório por garagem, linha e turno está nos planos?** · F1·12, F2·4, F4·9,
    10 e 11 · aberta
13. **Pupila no celular: celular pessoal ou da empresa, e só com o veículo parado? O site pode citar os "sinais
    compatíveis com ativação atípica"?** · F4·12 · em parte: pupila no celular, se vier, e pulseira muito depois (11/09).
    Proposta: nada disso no site de lançamento (seção 6.3)

**Prova e empresa**

14. **Quem aparece em "Quem faz": nomes, papéis, cidade, CNPJ e parcerias? O repositório pode ser citado?** · F1·4,
    F4·13 · aberta
15. **O nome RotaGuard já foi conferido no INPI? Qual é o domínio definitivo?** · F2·5, F5·8 e 9 · em parte: nome
    decidido em 11/09; INPI e domínio abertos
16. **O registro precisa valer como prova, em sinistro ou na Justiça do Trabalho? Nesse caso, aceita a assinatura por
    evento e a cadeia de custódia da seção 6.2?** · nova (11/09) · aberta
17. **Qual diferença o site vai defender frente à videotelemetria, agora que há clipes? Registro como produto, relatório
    na chegada, clipe só quando um sinal se repete?** · F1·5, F4 pergunta frequente 18 · em parte: "sem vídeo é
    permanente?" foi **respondida em 11/09: não**

**LGPD e jurídico**

18. **Clipes curtos:**
    - o que dispara um clipe e quanto ele dura;
    - onde fica e se é criptografado na caixa;
    - quem assiste, por quanto tempo fica e quando é apagado;
    - se o motorista vê os próprios clipes.

    Nova (11/09) · aberta
19. **Vai contratar parecer jurídico e RIPD?** Temas: vídeo do rosto, biometria, dado de saúde, relação de emprego,
    agregados, papéis de controlador e operador, encarregado. · F1·10, F4·15, F5·4 · aberta. Até lá, nada de "conforme a
    LGPD"
20. **Autoriza mexer no servidor e na caixa antes de publicar a seção de privacidade?** Itens: consentimento que bloqueia
    eventos, vídeo órfão apagado, HTTPS obrigatório, janela desligada por padrão, criptografia na caixa. · F5·3 · aberta

**Mídia e Magnific**

21. **Existe protótipo montado, transportadora ou garagem parceira para fotografar e filmar com autorização?** · F2·3,
    F3·3 · aberta
22. **Imagem gerada por IA pode ir ao site publicado com a legenda "Imagem ilustrativa", ou fica só como prévia até
    haver captação real? Aprova um elenco fixo gerado? Qual o saldo do Magnific e quem dispara as gerações?** · F3·1, 6
    e 7 · em parte: por ora, fotos provisórias de licença livre (11/09)
23. **Estrutura, tema e "Diário de bordo":**
    - estrutura A, B ou C?
    - topo com caminhão, ônibus ou os dois?
    - site claro ou escuro?
    - o "Diário de bordo" ainda vale?
    - a direção do site também guia o visual do app?

    F2·2, 6 e 9, F3·5 e 8, F4·16 e 20 · **respondida em 11/09, de forma provisória:** direção C; escolha caminhão ou ônibus
    antes do Ato II; página clara, com a noite só nas fotos; o "Diário de bordo" sai como espinha; estrada e mapa só como
    dado. Em aberto: o visual do app. Confirmar ao ver a primeira tela

**Mapa e medição**

24. **O mapa-múndi fica como faixa da madrugada, sem sugerir operação fora do Brasil? A versão em inglês serve a quem?
    A viagem de exemplo pode ser São Paulo → Curitiba pela BR-116?** · F2·1 e 8, F3·4, F4·17 e 18, F5·5 · em parte: a
    direção C abre com o mundo e a faixa da madrugada
25. **Medição: Umami na VPS ou Vercel (Pro, com ou sem Web Analytics Plus)? Aceita o código de origem na mensagem do
    WhatsApp?** · F4·19 · aberta

## 8. Plano da próxima versão

O site já está sendo construído em `site/` (Next.js + Tailwind + next-intl), na direção C. A ordem abaixo é a de execução.
**Onde o texto descreve uma função que ainda não existe (clipes, relatório ao conectar), ele só entra no site publicado
quando a função existir.**

### 8.1 Texto: corrigir antes de publicar

Cada frase de fato vira uma chave em `messages`, com a fonte registrada em `src/content/claims.ts` (sugestão da F5, rec.
1). Assim, a próxima rodada confere sem reler o código.

| Onde | Texto da v2 | Texto corrigido | Base |
|---|---|---|---|
| Selo e rodapé | "Em piloto com transportadoras" · "DriveSafe AI · protótipo em piloto" | "Protótipo em testes · vagas para o primeiro piloto" · "RotaGuard · protótipo em testes" | V02, V60 (depende da pergunta 3) |
| Título | "Microssono dura 1 segundo. O alarme também." | Título: "Gestão de fadiga e celular ao volante para frotas de carga e de passageiros." Apoio: "Olhos fechados por 1 segundo: alarme na cabine." | F1, hierarquia 1, sem o "sem vídeo do motorista"; V03, V04 |
| Subtítulo e prova | "Nenhuma imagem é gravada." · "0 imagens gravadas" | **Tirar.** Com os clipes curtos, deixa de valer para o produto | Decisão de 11/09; V08 era verdadeira só para a caixa de hoje |
| Na cabine | "O aviso chega antes de o caminhão sair da faixa." | "O alarme toca no primeiro segundo de olhos fechados." Linha opcional, que é conta e não promessa: "A 90 km/h, esse segundo são 25 metros." | V13; F1 #11 |
| Escada, 6 s | "O gestor é avisado no painel imediatamente." | "O evento fica no registro da caixa na hora. Na chegada, a empresa conecta a caixa e recebe o relatório." Só se o envio ao vivo continuar: "Com sinal, ele também chega ao painel em segundos." | V19; decisão de 11/09; pergunta 10 |
| Privacidade | "A imagem fica no caminhão. Só o evento sai dele." | **Rascunho, só depois das perguntas 18 e 19 e da função existir:** "Não grava a viagem inteira. Guarda o registro dos eventos e, só quando um sinal se repete, um clipe curto." | V28, V29; decisão de 11/09 |
| Privacidade | "com o consentimento do motorista, conforme a LGPD" | "O motorista registra as autorizações, com histórico, e pode baixar os próprios dados." | V32, V33 (depende da pergunta 19) |
| Privacidade | "A câmera transforma cada quadro em pontos do olho e descarta a imagem." | "A cada quadro, o aparelho mede o rosto, as mãos e o celular." A parte sobre descartar a imagem só volta com as regras dos clipes | V30; decisão de 11/09 |
| Calibração | "Cada motorista é comparado com ele mesmo descansado" | "Cada motorista é comparado com o próprio começo de viagem. Se ele já começar cansado, o sistema marca a calibração como suspeita." | V15 |
| Ficha | "12 pontos por olho" | "6 pontos por olho, mais a íris" | V35 |
| Ficha | "óculos escuros detectados" | "Com óculos escuros, o sistema percebe que não vê os olhos, não dispara alarme falso e avisa. Medir de óculos exige câmera infravermelha (em teste)." | V49 |
| Ficha | "No suporte, não conta" | "Celular parado no suporte não conta como celular na mão. Olhar para ele por mais de 2 s conta." | V45 |
| Ficha | "Raspberry Pi, Linux, Windows e macOS" | "Testado em computador com Windows. Raspberry Pi: em preparação." | V50; seção 6.1 |
| Ficha | "em validação com gravações reais" · "ou infravermelha" | "a validar com gravações reais" · "Câmera infravermelha: suporte em teste" | V41, V48 |
| Piloto | "Comece com cinco caminhões." · "Instalação acompanhada" · "relatório do período" · "Também atendemos universidades e editais de pesquisa." | Tirar até a oferta existir. Universidades: apagar | V54, V55, V57, V58 |
| Telas | Tela de alarme, rota BR-116, "Direção hoje", "21 rodando", curva do olho, PERCLOS ao vivo | Tirar, ou mostrar só o que existe com a legenda "Tela conceitual com dados de demonstração" | V20, V23 a V27 |
| Idioma | "PT · EN" | Só com a versão em inglês real, em links | V01 |

**O que nunca pode ser prometido** (lista completa em F1, "O que NÃO pode ser prometido", mais as decisões de 11/09):

- "nenhuma imagem é gravada", "sem vídeo do motorista" ou "só o evento sai";
- percentual de redução de acidentes;
- "evita acidentes" ou detecção de faixa;
- "sem alarme falso";
- **detecção de drogas, álcool ou "uso de anfetamina"**;
- "conforme a LGPD";
- registro "à prova de adulteração" antes de a assinatura existir;
- integração com rastreador ou relatório "aceito pela seguradora";
- central 24 h;
- escala testada;
- homologação.

### 8.2 Estrutura: home na direção C, páginas de segmento depois

1. **Primeira tela (Ato I, escala do mundo):**
   - o título da seção 8.1 e a linha de estágio verdadeira;
   - "Falar no WhatsApp" e as portas de segmento, que levam à escolha caminhão ou ônibus;
   - o atalho "Ver na cabine", que resolve o risco de o produto chegar tarde para a P1 (F2, riscos da direção C).
2. **Escalas do Brasil e da rodovia:**
   - a malha real, sem pinos;
   - a viagem noturna como fio (F4 S2), com os horários marcados como demonstração;
   - o fim da viagem passa a ser a chegada à base, não "o sinal volta".
3. **Ato II, cabine:**
   - sono **e** celular na mesma cena (problema 10);
   - a escada de 1, 3 e 6 s;
   - o alarme como som e a consequência: parar em segurança;
   - a fronteira de escala, com a legenda nova do conflito 1;
   - a parte para quem dirige (F4 S5), que só fecha depois das regras dos clipes.
4. **Ato III, frota:**
   - a caixa volta, é conectada e o registro vira relatório, com as três decisões da revisão;
   - a tela ao vivo só entra se continuar existindo (conflito 2);
   - depois, piloto, perguntas de quem decide, quem faz, ficha técnica com as fontes dos limiares, a chamada final por
     segmento e o rodapé.
5. **Depois do lançamento da home:**
   - páginas `/carga-e-logistica`, `/fretamento-e-rodoviario` e `/onibus-urbano` (as que a pergunta 6 confirmar);
   - `/motoristas`, `/piloto`, `/privacidade` e a área de download com PIN, com os mesmos componentes (F4 entrega D).
6. **Proibições da v3:**
   - os 29 sinais de template da F2: hero com texto e widget, rótulo mono, Geist com Geist Mono, fundo escuro com âmbar,
     janela falsa, JSON, mira e pontos no rosto, brilho, laço infinito, cartões iguais e selo com bolinha;
   - as proibições da direção C: zoom contínuo, globo 3D, arco de luz, ponto pulsando, partículas e âmbar.
   - Cenas presas só no computador (conflito 5), com no máximo 3 animações por tela.

### 8.3 Conversão

- **WhatsApp:** link `https://wa.me/55DDNNNNNNNNN?text=` com mensagem pronta por segmento e código de origem, por exemplo
  `[C1-LI]` (F4 entrega H). Sem lead-gate.
- **Ligar:** `tel:` no menu, na seção de piloto e no rodapé, e o número também em texto.
- **"Já é cliente? Entrar":** no cabeçalho, no menu do celular e no rodapé. Leva à área com PIN, que libera os
  instaladores (Windows, macOS, Linux e Android) e as instruções para instalar o PWA no iPhone (pergunta 2).
- **Celular:**
  - botão "Menu" com `aria-expanded`;
  - barra fixa embaixo com WhatsApp e Ligar;
  - botões com 44 px de altura, e 48 px no principal.
- **Idiomas:** PT e EN em links reais, que mantêm a mesma rota.
- **Medição sem rastrear pessoas:** eventos `whatsapp_clique`, `ligar_clique`, `segmento_escolha` e `entrar_clique`,
  mais UTM nos links espalhados. Ferramenta conforme a pergunta 25.

### 8.4 Mídia

- **Onde está o roteiro:** `docs/site/midia/`, com `README.md` como índice e as regras, fundos, fotos, banners e vídeos em
  `00` a `04`. Base: a lista de cenas, as regras de luz e lente, o checklist Brasil e o fluxo no Magnific da F3.
- **Âncora de estilo aprovada pelo Matheus antes da série:** cabine de carga de dia, a mesma cabine à noite e carreta
  na BR (S01, S01 noite e S07 da F3).
- **Cenas a revisar ou acrescentar com as decisões de 11/09:**
  - o aparelho vira caixa removível com câmera (conflito 13);
  - a instalação (S12) ganha a cena da chegada: alguém da base conectando a caixa num computador;
  - nenhuma cena sugere gravação contínua, nem mostra o rosto do motorista numa tela.
- **Enquanto a série não existe:**
  - fotos provisórias de licença livre, com crédito;
  - espaço marcado com o nome da cena onde ainda não houver foto;
  - legenda "Imagem ilustrativa" nas cenas de uso;
  - o aparelho nunca aparece como produto final.
- **Direção C:**
  - três sequências de quadros, uma por ato, com cerca de 6 MB no computador e 2,5 MB no celular por sequência;
  - no máximo 3 vídeos gerados.
- **Motorista:** sempre competente. Nunca dormindo, bocejando ou com sobreposição biométrica no rosto.

### 8.5 Mapas com dados reais

- **Fontes:**
  - mundo: Natural Earth, domínio público;
  - rodovias federais: SNV do DNIT;
  - limites e divisões: IBGE.
  - Preparar os mapas como arquivos estáticos simplificados, sem API de mapa rodando no site, com os créditos no rodapé.
- **Mapa-múndi:** uma vez, com a faixa da madrugada calculada, sem arcos entre continentes. Com movimento reduzido, fica
  parado.
- **Regra de honestidade:** mapa é contexto, não função.
  - Nenhum pino de veículo ou de evento; nenhuma "frota ao vivo no mapa".
  - Todo trajeto leva a legenda "rota ilustrativa".
  - A troca de escala é por corte ou máscara, nunca por zoom contínuo.

### 8.6 Acessibilidade

- **Contraste AA:** recalcular para a paleta clara da direção C. O piso é 4,5:1 para texto normal e 3:1 para texto
  grande. Os valores da F5 A1 foram medidos sobre o fundo escuro da v2 e não valem mais.
- **Tamanho de texto:** no mínimo 12 px nos rótulos e 14 px no texto de leitura. Rótulos de mapa e de tela em HTML,
  nunca dentro de SVG esticado. Testar a largura da B612 em português e em inglês.
- **Foco e semântica:**
  - estilo de `:focus-visible` e link "Pular para o conteúdo";
  - telas simuladas como `figure`, com legenda fixa e a parte animada em `aria-hidden`.
- **Movimento:**
  - `prefers-reduced-motion` ouvido também com a página aberta;
  - pausa em qualquer animação que dure mais de 5 s;
  - versão parada de cada cena;
  - nada rodando fora da tela.

### 8.7 SEO e PT/EN

- **Metadados por idioma:**
  - título, description e Open Graph de 1200 × 630;
  - `canonical`, `alternates.languages` com `x-default` e `sitemap` com alternates;
  - JSON-LD `Organization`. `Product` só com oferta real.
- **Páginas sem indexação:** prévias publicadas e a área com PIN levam `noindex`.
- **next-intl:**
  - `src/proxy.ts`;
  - `messages/pt-BR.json` e `messages/en.json` com todo o texto visível, inclusive rótulos de mapa e de tela;
  - números e horas pelo formatador.
- **Versões e prova:** travar as versões realmente instaladas na nota do projeto, conferidas no registro na hora (as da
  F5 A8 são de 11/09). A prova é `npm run build` e `npm run lint`.
- **Tailwind 4:** cuidado com os erros 52 a 54 do vault (classe que colide com utilitário, regra fora de camada,
  override de token dentro de camada).

### 8.8 Brechas de produto que sustentam a privacidade e o registro

Fazer em paralelo, antes de publicar a seção de privacidade. Depende da pergunta 20.

**Brechas que já existem no código (F5):**
1. Conferir o consentimento de monitoramento antes de aceitar eventos. Hoje o recebimento não confere, e a política da
   caixa só olha perfil e sinais de ativação (`servidor/backend/routes/device_api.py:51-58, 107-144`).
2. Apagar o vídeo órfão de análise quando o servidor reinicia no meio dela. Hoje o `_load` só marca "falhou"
   (`servidor/backend/test_session.py:325-336`). Avisar com clareza sobre `DRIVESAFE_MANTER_VIDEOS`
   (`servidor/backend/config.py:38`).
3. Exigir HTTPS entre a caixa e o servidor. O exemplo de instalação usa HTTP (`implantacao/raspberry-pi/device.env.example:4`).
4. Deixar a janela de vídeo desligada por padrão no veículo (`caixa/run_monitor.py:100-104`).
5. Rever o que vai no evento `calibracao_concluida` (`caixa/vision/drowsiness.py:521, 530`) e no estado ao vivo.
6. Testar som e buzzer no hardware do piloto antes de publicar "1 s de olhos fechados = alarme" (F5 #14).

**Requisitos novos, antes de o site citar clipes ou relatório ao conectar:**
7. Criptografia dos clipes e do registro na caixa.
8. Retenção e exclusão automática dos clipes, com prazo definido (pergunta 18).
9. Registro de quem assistiu cada clipe.
10. Assinatura dos eventos e cadeia de resumos (hash) no registro.
11. Hora confiável depois de reiniciar: relógio com bateria ou GPS.
12. Desligamento seguro quando a ignição cai.
13. Rótulo "sinais compatíveis com ativação atípica" em qualquer clipe ou relatório, nunca "anfetamina".

### 8.9 Fora do site (sugestões, não aplicadas)

- **Vault:**
  - registrar o erro "afirmar fato do produto no site sem conferir o código" (F5 rec. 9);
  - registrar "estrada como ornamento" (F2 rec. 8);
  - atualizar o erro 34 e `diferenciacao-visual.md`, que ainda sugerem a Geist;
  - atualizar `stack-padrao.md` com `proxy.ts` e `preload` no lugar de `priority`.
- **`PENDENCIAS.md`:**
  - tirar o "Diário de bordo" como direção aprovada e os públicos antigos;
  - trocar o "painel não deve ser web / formato em aberto" pela decisão do app de 11/09;
  - registrar a nova função (clipes, registro, recolhimento e relatório) e o Pi 4 de 4 GB como hardware provável.

## 9. Como reler as evidências

**Arquivos desta rodada** (`docs/site/avaliacoes/2026-09-11-previa-v2/`):
- relatórios: `01-mensagem-e-personas.md`, `02-direcao-de-arte.md`, `03-imagens-e-prompts.md`,
  `04-estrutura-e-conversao.md`, `05-tecnica-e-veracidade.md`;
- referências da rodada: `referencias.md`;
- prints avaliados: `prints-avaliados/v1/` (`previa-desktop.png`, `previa-celular.png`) e `prints-avaliados/v2/`
  (`previa-topo.png`, `previa-desktop.png`, `previa-celular.png`).

**Prévias em HTML (fora do branch):**

```bash
git show 9e8ad60:site-drivesafe/previa/v2/index.html > previa-v2.html   # linhas v2:N
git show 9e8ad60:site-drivesafe/previa/index.html > previa-v1.html      # linhas v1:N
```

**Roteiro de imagens avaliado pela frente 3:** deve estar no mesmo commit, em `site-drivesafe/prompts-imagens.md` (conferir
com `git show 9e8ad60:site-drivesafe/prompts-imagens.md`). O roteiro atual é o de `docs/site/midia/`.

**Caminhos antigos, citados nos relatórios, e onde estão agora:**

| Nos relatórios | Agora |
|---|---|
| `site-drivesafe/avaliacao/contexto.md` | `docs/site/contexto.md` |
| `site-drivesafe/avaliacao/personas.md` | `docs/site/personas.md` |
| `site-drivesafe/avaliacao/2026-09-11-previa-v2/` | `docs/site/avaliacoes/2026-09-11-previa-v2/` |
| `site-drivesafe/prompts-imagens.md` | `docs/site/midia/` (índice em `README.md`) |
| `site-drivesafe/previa/` | fora do branch; commit `9e8ad60` |
| `vision/...` | **`caixa/vision/...`** |
| `backend/...` | **`servidor/backend/...`** |
| `run_monitor.py` | `caixa/run_monitor.py` |
| `manage.py`, `start_system.py` | `servidor/` |
| `webapp/` | `painel/webapp/` |
| `dashboard/` | `painel/legado/` |
| `analisar_video.py`, `avaliar_*.py` e modelos de anotação | `ferramentas/` (anotações em `ferramentas/anotacoes/`) |
| `deploy/raspberry-pi/`, Docker e compose | `implantacao/` |
| testes | `tests/` |

- **Linhas dos relatórios:** são de antes da reorganização, e algumas mudaram. O `README.md` desceu de 3 a 7 linhas, e
  `DRIVESAFE_MANTER_VIDEOS` foi de `backend/config.py:34-35` para `servidor/backend/config.py:38`. Se não achar, procure o
  trecho citado.
- **Linhas de `contexto.md`** (por exemplo, `contexto.md:37`): são da versão de 11/09 anterior à atualização. O texto
  citado continua nas tabelas de `docs/site/contexto.md`.
- **Próxima rodada:** avalia o projeto Next em `site/`, com prints novos em 1440 px e 400 px, seguindo a skill
  `.claude/skills/avaliar-site-5-frentes/SKILL.md`.
