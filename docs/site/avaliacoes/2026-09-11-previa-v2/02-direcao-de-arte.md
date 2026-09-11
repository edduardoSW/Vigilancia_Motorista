# Frente 2 · Direção de arte, tipografia, layout e identidade (anti-genérico)

Avaliador: agente 2 · 11/09/2026 · versão avaliada: `site-drivesafe/previa/v2/index.html`, com os prints
`previa-topo.png` (1440 × 860), `previa-desktop.png` (1440 × 5200) e `previa-celular.png` (400 × 7400)

Como ler as evidências:

- `v2:N` é a linha N de `site-drivesafe/previa/v2/index.html`. `v1:N` é a linha N de `site-drivesafe/previa/index.html`.
- As coordenadas dos prints estão em pixels do arquivo original.
- As notas do vault são citadas pelo nome e pela linha. Ficam em `C:\Users\Matheus Corte\Desktop\Obsidian\90 - Projetos\`,
  salvo quando o caminho é outro.
- O erro 75 **não está na cópia local** de `erros-que-a-ia-comete.md`, porque a pasta local do vault está 7 commits atrás
  do `origin/main`. Li o texto no commit `419c555`, sem alterar nada.
- Requisitos que chegaram durante a avaliação:
  - estrada e mapa-múndi no site (`prompts-2026-09.md:5040`);
  - stack final em Next.js, Tailwind CSS 4 e next-intl, com GSAP ScrollTrigger quando fizer sentido.

## Nota geral: 2/10

A v2 é uma página de SaaS para desenvolvedor, montada com as peças mais comuns do gênero: Geist com Geist Mono, quase preto
com âmbar, hero com texto e widget, janela falsa e JSON. Usa a mesma paleta do app que o Matheus já recusou e não tem uma
única imagem de caminhão, ônibus, estrada ou pessoa.

## Notas por critério

| Critério | Nota | Por quê | Evidência |
|---|---|---|---|
| Estrutura | 2 | É o esqueleto de landing de SaaS. Tem menu com botão cheio e hero com texto à esquerda e widget à direita. Depois vêm quatro seções com o mesmo cabeçalho (rótulo, título, parágrafo e um componente), uma faixa de contraste e a chamada final. O hero repete o que o erro 75 apontou como template na v1. | `v2:58` (grade 5fr/7fr); `v2:96-100` (mesmo espaçamento, fio e cabeçalho em toda seção); `v2:185`; `v2:196-198`; `v1:68-69`; erro 75 (commit `419c555`) |
| Tipografia | 2 | É o par que o `create-next-app` instala por padrão, sem nenhuma fonte de título. A hierarquia vem só do tamanho e do peso 600. A mono aparece em 21 regras como enfeite: rótulos, faixa de "prova", tabela e JSON. | `v2:10`, `v2:28-29`; o template oficial importa `Geist, Geist_Mono` ([layout.tsx do create-next-app](https://github.com/vercel/next.js/blob/canary/packages/create-next-app/templates/app/ts/app/layout.tsx)); `v2:62`, `v2:99` |
| Cor e contraste | 2 | Quase preto, âmbar e vermelho coral formam a paleta do app "Cabine noturna", recusada como "paleta horrenda". A isso se somam o verde de semáforo, 37 hex diferentes e um único bloco claro como respiro. O texto "dim" fica em cerca de 3,9:1 (cálculo meu, pela fórmula da WCAG) em tamanhos de 0,66 a 0,8 rem. | `v2:13`, `v2:21-23` contra `webapp/assets/css/app.css:50`, `:59`, `:64`; recusa em `prompts-2026-09.md:4956`; `v2:20`, usado em `v2:66`, `:83`, `:88`, `:133`, `:152`, `:199` |
| Composição e ritmo | 3 | São seis blocos de peso parecido, alinhados à esquerda e separados por fio. Nada sangra, nada muda de escala e nenhuma foto quebra a grade. O único contraste de ritmo é a seção clara. | `previa-desktop.png` y≈780 a 4700; `v2:96`; `v2:97` (cabeçalho com `max-width: 52rem` repetido cinco vezes) |
| Presença do mundo real | 1 | Não há nenhum `<img>` nem `<video>`. O caminhão é uma placa em texto, o rosto é uma nuvem de pontos e a estrada é a palavra "BR-116". Imagem de fundo, banner e seção coberta por imagem já estavam no primeiro pedido. | busca por `<img` e `<video` em `v2`: 0; `v2:320`; `prompts-2026-09.md:4748`, `:5022` |
| Componentes que denunciam template | 1 | São 29 sinais, listados abaixo, quase todos do catálogo de SaaS para desenvolvedor. | seção "Sinais de template" |
| Coerência com os sites do Matheus | 2 | Não tem nenhum dos diferenciais dos sites dele: mídia real, atos, grade editorial, fonte de título com personalidade, restrição de cor e lista de proibições. Coincide só no que o vault já marcou como convenção: tema escuro por padrão, mono nos rótulos e `clamp()`. | seção "Comparação com os sites do Matheus"; `diferenciacao-visual.md:86-96` |
| Seriedade para transporte sem clichê | 3 | É contida: não tem gradiente roxo nem foto de banco. Mas a seriedade é de ferramenta de programador, não de transporte. E traz o clichê da "IA que enxerga": visor com cantos, rosto em pontos e olhos contornados em vermelho com brilho. | `v2:365-371`, `v2:301`, `v2:460-468`, `v2:70`; `previa-topo.png` (653,140) a (1312,725) |
| Requisito novo: estrada e mapa (fora do briefing da v2) | 1 | Só existe o texto "São Paulo → Curitiba · BR-116", dentro do painel de demonstração. | `v2:320`; `prompts-2026-09.md:5040` |

## Leitura por persona

Leitura só pelo visual. A leitura da mensagem é da frente 1.

| Persona | O que o visual comunica em 5 s | O que falta ou incomoda | Nota |
|---|---|---|---|
| P1 Renata (carga pesada, 190 carretas) | "startup de software com demonstração de olhos" | nenhum caminhão, pátio ou carreta; nada diz "frota pesada" (`personas.md:25`) | 3 |
| P2 Carlos (fretamento, 56 anos) | "coisa de tecnologia", o equivalente visual do jargão em inglês de que ele desconfia (`personas.md:55`) | nenhum ônibus no site inteiro (`personas.md:48`); JSON e mono afastam | 2 |
| P3 Juliana (CCO, 620 ônibus) | o painel com semáforo e fila de revisão é o que mais se aproxima do mundo dela | uma janela de sistema operacional com "24 veículos" (`v2:304`) não mostra a escala de 9 garagens (`personas.md:59`) | 4 |
| P4 Marcos (financeiro) | "empresa nova de software" | é justamente a objeção dele: depender de empresa nova (`personas.md:95`) | 3 |
| P5 José (motorista, 58 anos) | olhos em vermelho dentro de uma mira, com a palavra "ALARME" | é imagem de vigilância, o oposto de "não tratar o motorista como suspeito" (`personas.md:115-118`) | 2 |

## Problemas, do mais grave ao menos grave

| # | Gravidade | Problema | Evidência | Impacto | Correção concreta |
|---|---|---|---|---|---|
| 1 | crítica | É o esqueleto de landing de SaaS, com o mesmo hero da v1. Da v1 para a v2, cores e fontes foram trocadas, mas a estrutura ficou: a v1 tinha uma "única seção escura" e a v2 tem uma "única seção clara". A v1 usava Plex Sans com Plex Mono; a v2, Geist com Geist Mono. | `v1:68-69` e `v2:58`; `v1:102` ("única seção escura") e `v2:185` ("única seção clara"); `v1:10` e `v2:10`; erros 33 e 40 (`erros-que-a-ia-comete.md:63-69`, `:225-230`); erro 75 (commit `419c555`) | O dono reconhece o template à primeira vista. É o terceiro "genérico" seguido (app, v1 e v2). | Parar de codar. Mostrar as 3 direções abaixo como prévia estática (um quadro de computador e um de celular) e escrever o que da v1 e da v2 fica proibido de voltar. |
| 2 | crítica | Não há nenhuma imagem do mundo do transporte: foto, vídeo, veículo, cabine, garagem, CCO ou gente. | nenhum `<img>` ou `<video>` em `v2`; `prompts-2026-09.md:4748`, `:5022` | Não cumpre o pedido central ("imagens relacionadas"), e P2 não se reconhece no site. | Produzir a série de fotos e vídeos **antes** do layout, com a frente 3, e desenhar as seções em volta dela. Enquanto as imagens não existirem, deixar o espaço marcado com o nome da cena, como no São Jorge (`site-saojorge.md:83-85`). |
| 3 | crítica | A paleta do app recusado foi reaplicada ao site. | `v2:13` `#0b0c0e`, `v2:21` `#ffb224`, `v2:22` `#ff5b4f`; no app: `app.css:50` `#14110f`, `:59` `#f5b301`, `:64` `#ef5b40`; recusa em `prompts-2026-09.md:4956` | Repete, ao pé da letra, a "paleta horrenda". | Fundo claro, com a noite entrando pela fotografia, não pelo tema da interface. Duas cores e um neutro (`awwwards-estudo.md:174-192`). Vermelho, âmbar e verde só dentro da tela do produto, onde indicam estado. |
| 4 | alta | A tipografia é o padrão do framework, sem fonte de título, e a mono é usada como enfeite. | `v2:10`, `:28-29`; 21 usos de `var(--mono)`; o template do Next importa Geist e Geist Mono | É o "fontes genéricas" da reclamação. O próprio vault ainda sugere a Geist como alternativa à Inter (`erros-que-a-ia-comete.md:74`, `diferenciacao-visual.md:130`), o que ficou desatualizado. | Par de fontes com o motivo escrito (ver as direções). Mono só para dado de máquina, ou nenhuma. Sugerir, sem aplicar, a atualização do erro 34 no vault. |
| 5 | alta | A iconografia é de vigilância sobre o motorista: mira com cantos, rosto em pontos e olhos contornados em vermelho com brilho. | `v2:460-461`, `:462-468`, `:497`, `:70`; `previa-topo.png` (704,230) a (1262,500) | Afasta P5 e o sindicato e contradiz a promessa de privacidade. | Mostrar o que o motorista vê e ouve: a tela de alarme na cabine e o aparelho instalado. Os pontos do olho ficam só no bloco de privacidade, sem mira, sem vermelho e com a legenda "isto não sai do veículo". |
| 6 | alta | A estética é de ferramenta de desenvolvedor: JSON com realce de sintaxe, janela com "— ▢ ✕", rótulos mono em caixa alta e "offline" em mono. | `v2:182-183`, `:365-371`, `:104-105`, `:301`, `:71`, `:83`, `:239` | P2 e P4 leem "startup de software", e quem compra para frota não lê JSON. | Mostrar o evento como **ficha de ocorrência** em português, com campos rotulados como numa papeleta. Recortar as telas do painel, sem a moldura do sistema operacional. |
| 7 | alta | O transporte de passageiros não aparece no visual. | nenhuma ocorrência de "ônibus" em `v2`; `v2:268`, `:352`, `:403` ("cinco caminhões") | Metade do público não se reconhece (`personas.md:48`). | Entrada dupla, carga e passageiros, cada uma com fotografia própria (ver a direção A). |
| 8 | alta | O processo produz template: as referências foram lidas só como texto e nenhuma era de fora do web design. A v2 não teve lista de proibições nem direções mostradas antes de codar. | nota 08 no commit `419c555`: "Lidas pelo WebFetch (resumo do HTML, sem ver a página renderizada)"; Linear como referência; `v2:7` sem proibições, enquanto o app tinha (`app.css:5`); `diferenciacao-visual.md:147-148`; erro 38 (`erros-que-a-ia-comete.md:94-98`) | Sem atrito no processo, a IA volta ao padrão do treino (Shin et al., em `diferenciacao-visual.md:24-47`). | Fazer a rodada de referências olhando prints, com pelo menos uma fonte de fora da web (as desta avaliação servem). Escrever a lista de proibições. Deixar o Matheus escolher antes da primeira linha de código. |
| 9 | média | O ritmo é uniforme e o rótulo repete o menu. | `v2:96-100`; os rótulos "Na cabine", "Painel da frota", "Privacidade" e "Especificações" (`v2:267`, `:296`, `:351`, `:382`) repetem o menu (`v2:212-215`); erro 51 (`erros-que-a-ia-comete.md:308-312`) | A leitura fica monótona e o rótulo não informa nada. | Variar a escala conforme o papel da seção (foto sangrando, lista editorial, ficha técnica). Só usar rótulo quando ele disser algo que o título não diz. |
| 10 | média | Efeitos que o dono já recusou: brilho vermelho, laço contínuo de 9 s com `requestAnimationFrame` e um equalizador falso. | `v2:70`, `:476-533`, `:170-171`, `:284`; `prompts-2026-09.md:4956` ("efeitos desnecessários") | Reforça a "cara de IA" e consome CPU mesmo com a página parada. | Movimento só onde explica algo: o alarme toca uma vez quando entra na tela, ou quando a pessoa aperta. Sem brilho e sem laço infinito. |
| 11 | média | O texto pequeno "dim" tem contraste baixo. | `#6f6f69` sobre `#0b0c0e` dá cerca de 3,9:1 (cálculo meu); `v2:20`, `:66`, `:83`, `:88`, `:133`, `:152`, `:199` | Reprova o nível AA para texto pequeno. A frente 5 confirma. | Piso de 4,5:1 no token de texto secundário. |
| 12 | média | No celular, os rótulos dentro do SVG ficam ilegíveis e o produto cai abaixo da dobra. | `v2:442` (13 px num `viewBox` de 800, cerca de 5,5 px em 340 px de largura); `v2:540` (10 px com `preserveAspectRatio="none"`); `previa-celular.png`: a demonstração só começa em y≈645, e os rótulos ficam ilegíveis em y≈837 e y≈3025 | O detalhe vira ruído, e a primeira tela não tem imagem. | Rótulos em HTML sobre a figura. No celular, a mídia vem antes do parágrafo. |
| 13 | baixa | O selo "Em piloto com transportadoras" usa pílula com ponto verde de "ao vivo". | `v2:60-61`, `:229`; `contexto.md:37` (não há piloto documentado) | Dá sinal visual de "ativo" a um fato que não existe. | Tirar o selo. O texto é com a frente 5. |
| 14 | baixa | A marca é genérica: um anel com arco no acento e um ponto no centro. | `v2:208-209` | Não identifica nada. | Decidir símbolo e nome depois de escolher a direção (pergunta 5). |
| 15 | baixa | O sistema não tem restrição: 37 hex, 20 cinzas escuros e 11 raios diferentes (1, 2, 5, 6, 8, 10, 12, 14 e 22 px, 50% e 999 px). | contagem no arquivo; `v2:50`, `:60`, `:69`, `:76`, `:103`, `:114`, `:126`, `:163`, `:164`, `:176`, `:544` | É o "tamanho uniforme de componente" com variações sem critério (`diferenciacao-visual.md:63`). | Tokens fechados por papel (erro 14, `erros-que-a-ia-comete.md:60-61`). |

## Sinais de template

| # | Sinal | HTML | Print | Por que denuncia |
|---|---|---|---|---|
| 1 | Geist e Geist Mono, do Google Fonts, como únicas famílias | `v2:10`, `:28-29` | site inteiro | É o par que o `create-next-app` instala sozinho. Ninguém escolheu. |
| 2 | Etiqueta em pílula com bolinha verde acima do título | `v2:60-61`, `:229` | `previa-topo.png` (128,175) a (371,203) | É o selo de anúncio do hero de SaaS, e o verde sugere sistema online. |
| 3 | Título em duas frases, com a segunda pintada no acento | `v2:62-63`, `:230` | topo (128,340) a (583,395) | Truque padrão de hero de startup. |
| 4 | Espaçamento entre letras bem negativo e peso 600 em sans geométrica | `v2:62`, `:99`, `:167` | todos os títulos | É a tipografia no estilo Vercel e Linear. |
| 5 | Par de botões: primário cheio no acento e secundário só com borda, raio de 8 px | `v2:50-53`, `:233-234` | topo (128,561) a (401,609) | Par de chamada de qualquer kit. |
| 6 | Faixa de "prova" com números em mono embaixo dos botões | `v2:66-67`, `:236-240` | topo (128,645) a (512,690) | É a faixa de estatísticas de SaaS, aqui sem nenhum dado de mercado. |
| 7 | Hero com texto à esquerda e widget à direita | `v2:58` | topo inteiro | Mesmo esqueleto que o erro 75 apontou na v1. |
| 8 | Cartão da demonstração com barra de título em mono caixa alta e ponto vermelho "ao vivo" | `v2:71-73`, `:244-247` | topo (655,142) a (1310,180) | Moldura de demonstração de ferramenta. |
| 9 | Visor com cantos de mira e rosto em nuvem de pontos | `v2:460-468` | topo (704,230) a (1262,500) | Clichê visual de visão computacional. |
| 10 | Brilho colorido em volta do cartão no alarme | `v2:70` | topo, borda vermelha com sombra | "Efeito desnecessário" já recusado. |
| 11 | Linha com quatro métricas e rótulos mono em caixa alta | `v2:80-85`, `:252-257` | topo y≈550 a 620 | Painel genérico de indicadores. |
| 12 | Gráfico de linha verde, no estilo de monitor cardíaco | `v2:471-474`, `:258` | topo (655,625) a (1310,688) | Símbolo pronto de "dado ao vivo". |
| 13 | Rótulo mono no acento acima de todo título de seção | `v2:98`, `:267`, `:296`, `:351`, `:382`, `:402` | desktop y≈946, 1685, 2831, 3718, 4467 | Convenção saturada (`diferenciacao-visual.md:90`). |
| 14 | O mesmo bloco de cabeçalho (rótulo, título e parágrafo) em todas as seções | `v2:97-100` | desktop, cinco vezes | A página vira uma sequência de cabeçalhos de seção. |
| 15 | Janela falsa com controles de sistema e sombra de 120 px | `v2:103-105`, `:301` | desktop y≈1940 a 2543 | Sinal clássico de landing de software. |
| 16 | Barra lateral com filtros em pílula e lista com bolinhas de semáforo | `v2:113-123`, `:305-314` | desktop y≈2000 a 2540 | Painel administrativo de kit. |
| 17 | Cartões de indicadores arredondados e iguais, em grade de quatro | `v2:130-135`, `:323-328` | desktop y≈2040 a 2090 | Tamanho uniforme de componente (`diferenciacao-visual.md:63`). |
| 18 | Tabela com minigráfico e botão "Revisar" | `v2:147-150`, `:336-338` | desktop y≈2290 a 2420 | Tabela de dashboard de template. |
| 19 | Aparelho falso com moldura em gradiente, raio de 22 px e brilho interno | `v2:163` | desktop y≈978 a 1365 | Mockup que imita objeto físico. |
| 20 | Equalizador falso de seis barras | `v2:170-171`, `:284` | desktop y≈1320 | Enfeite que não mede nada. |
| 21 | Escada de números grandes em mono, nas cores de semáforo | `v2:157-162`, `:270-274` | desktop y≈1180 a 1430 | Número em mono usado como prova. |
| 22 | Diagrama "entrada → saída" em dois cartões com seta | `v2:174-181`, `:355-375` | desktop y≈3120 a 3463 | Diagrama de SaaS de API. |
| 23 | Bloco de JSON com realce de sintaxe | `v2:182-183`, `:365-371` | desktop y≈3180 a 3350 | Sinal de ferramenta de desenvolvedor. |
| 24 | A única seção clara, no fim, como respiro | `v2:185-193`, `:379-397` | desktop y≈3575 a 4330 | É o recurso da v1 invertido (`v1:102`). |
| 25 | Faixa final com rótulo, título e botão alinhado à direita | `v2:196-198`, `:399-408` | desktop y≈4394 a 4680 | Faixa de chamada de kit. |
| 26 | Paleta quase preta de SaaS, com 20 cinzas escuros entre `#060708` e `#3b4047`, mais âmbar, vermelho e verde | `v2:13-27` e cores no JS | site inteiro | Tema escuro padrão com semáforo. |
| 27 | Logo em anel com arco no acento | `v2:208` | topo (128,19) a (150,41) | Símbolo genérico de medidor. |
| 28 | Menu fixo com logo, 4 links, idioma, "Entrar" e botão cheio, com fio embaixo | `v2:41-53`, `:205-222` | topo y 0 a 60 | Navegação de SaaS. |
| 29 | Raio de canto variando sem papel definido (11 valores) | ver o problema 15 | — | Kit montado, não sistema. |

## Comparação com os sites do Matheus

Li as notas do São Jorge (17/08), da Clínica Jéssica (19/08 a 09/09), do Marcão Vivacqua (13/08), da Fornalha Quintal (04/08), do
Morro Alto (24 a 31/07), da ACEX e da Dra. Jânia. O que diferencia esses sites não é paleta nem fonte. É mídia real,
narrativa, grade e restrição.

| O que os sites dele fazem | Onde está | O que a v2 faz | Evidência na v2 |
|---|---|---|---|
| Mídia real, ou gerada com curadoria, como estrutura da página | No Morro Alto, o hero é um paredão de 37 vídeos (`site-morro-alto.md:78-110`). Na Jéssica, há fotos reais no hero, nos protocolos e na galeria, e um recorte que vaza a seção (`site-clinica-jessica.md:54`, `:71`). No São Jorge, 7 sequências de quadros e um brasão 3D renderizado no Blender (`site-saojorge.md:37`, `:60-61`). No Marcão, o site inteiro é foto recortada e logo, sem texto (`site-marcao-vivacqua.md:12`). | nenhuma imagem | nenhum `<img>` |
| Narrativa em atos | São Jorge: Origem → Matéria → Domínio (`site-saojorge.md:38`) | cinco temas soltos | `v2:264-408` |
| Grade editorial assimétrica e listas no lugar de cartões | Jéssica: grades 7/5 e 5/7, tratamentos em lista numerada com numeral gigante e galeria em colagem com sobreposição (`site-clinica-jessica.md:44`, `:48`). Fornalha: 7/5 em 12 colunas, abas, índice lateral fixo e numeração tipográfica no lugar de ícone (`site-fornalha-quintal.md:61-63`). Morro Alto: cases em 2 grandes na diagonal e 4 pequenos (`site-morro-alto.md:461`). | hero 5/7, depois uma coluna com um componente por seção, em cartões arredondados | `v2:58`, `:97`, `:130-136` |
| Fonte de título com personalidade | Italiana (`site-clinica-jessica.md:164`), Marcellus (`site-saojorge.md:34`), Fraunces com Newsreader no corpo (`site-fornalha-quintal.md:37`), Instrument Serif junto da Geist (`site-morro-alto.md:222-224`), Cormorant (`site-dra-jania.md:19`), General Sans (`site-acex-partners.md:20`) | uma única sans em tudo | `v2:28` |
| Textura | Grão com `feTurbulence` (`site-clinica-jessica.md:220-223`; `site-fornalha-quintal.md:64`) | superfícies lisas com sombra | `v2:103`, `:163` |
| Restrição de cor | São Jorge: proporção 58/30/8/4 usada como partitura, com ouro no máximo duas vezes por tela (`site-saojorge.md:32`, `:55`). Morro Alto: excesso de ouro corrigido e escada de três superfícies (`site-morro-alto.md:208-216`). | 37 hex e três acentos | contagem no arquivo |
| Lista de proibições | Jéssica (`site-clinica-jessica.md:55`); o próprio app do DriveSafe tinha (`app.css:5`) | nenhuma | `v2:7` |
| Referência de fora do web design | Jéssica: a identidade da Aesop (`site-clinica-jessica.md:39`). App: o Manual Brasileiro de Sinalização (nota 08, `08 - App instalavel, modo local e pendencias.md:62`) | só páginas de produto, mais o Linear | commit `419c555` |
| Movimento com papel e rolagem coreografada | São Jorge: tokens de movimento, até 3 animações por tela e sequências presas à rolagem (`site-saojorge.md:57-58`, `:109-116`). Fornalha: só `transform` e `clip-path` (`site-fornalha-quintal.md:151-152`). ACEX: notebook 3D com zoom na rolagem (`site-acex-partners.md:98-106`). | um laço contínuo e um brilho; nada ligado à rolagem | `v2:521-533` |
| Peças desenhadas para o projeto, inclusive mapa | Fornalha: marca, selo, **mapa** e ornamentos desenhados, com a seção `mapa-como-chegar` e o componente `MapaQuarteirao` (`site-fornalha-quintal.md:20-21`, `:69-71`, `:86`) | logo genérico e nenhum mapa | `v2:208` |

Dois pontos:

- **O Morro Alto mostra que a Geist sozinha não é o problema.** Lá ela divide a página com a Instrument Serif e com um
  paredão de vídeo. Na v2 ela está sozinha, junto só da própria mono.
- **Onde a v2 coincide com o Matheus:** títulos com `cqi` (`v2:62`, `:99`, erro 49), tema escuro por padrão
  (`meu-estilo-de-sites.md:83`), mono nos rótulos e `prefers-reduced-motion` (`v2:516`). São os itens que
  `diferenciacao-visual.md:86-96` marcou como convenção. A v2 pegou o que é comum no estilo dele e deixou de fora o que é
  só dele. Uma ressalva: grão e textura também estavam no app recusado (`feedback-visual-sobrio-profissional.md:13`). No
  DriveSafe, a textura deve vir da fotografia, não de uma camada por cima da página.

## O conceito "Diário de bordo" ainda serve?

O conceito é o site como um dia de 24 h num disco de tacógrafo: papel de dia, escuro na madrugada com a tela piscando no
microssono e amanhecer no contato (nota 08, linhas 69-70; `prompts-imagens.md:3-4`).

**A favor:**

- **Serve aos dois segmentos.** O registrador de velocidade e tempo é obrigatório para passageiros com mais de 10 lugares e
  para carga acima de 4.536 kg (CTB, art. 105, II, [resumo](https://ctbdigital.com.br/artigo/art105/)).
- **É termo legal.** A Lei 13.103/2015, art. 2º, V, "b", cita "diário de bordo, papeleta ou ficha de trabalho externo" como
  forma de controlar a jornada ([resumo](https://www.metadados.com.br/blog/lei-no-13-1032015-controle-de-jornada-de-trabalho-de-motoristas)).
- **A madrugada é regra do produto, não decoração.** Ela pesa no cálculo do risco (`contexto.md:32`, `vision/context.py`).

**Contra, diante do objetivo novo:**

1. **Ordena o site pelo relógio, não pelas perguntas de quem compra.** P1 precisa entender em 30 s que o produto é para
   frota pesada, o que ele detecta e como o gestor fica sabendo (`personas.md:24-29`). Na v1, "Para a transportadora" caiu
   para as 18:00, a quinta seção (`v1:234-238`).
2. **É o dia de um motorista, não a operação de uma frota.** P3 pensa em 620 ônibus e 9 garagens (`personas.md:59`). P1
   pensa em rotas de SP ao RS (`personas.md:14`).
3. **A execução depende de efeitos já recusados:** página que escurece e tela que pisca (nota 08, linhas 69-70). Tela
   piscando ainda esbarra no critério de flashes da WCAG ([2.3.1](https://www.w3.org/WAI/WCAG22/Understanding/three-flashes-or-below-threshold.html)).
4. **O material pedido é fantasia de papel envelhecido:** "aged tachograph diagram paper… one very faint coffee ring"
   (`prompts-imagens.md:41-43`). É a armadilha do "Cabine noturna", "temático demais para um produto sério" (nota 08,
   linha 17; `feedback-visual-sobrio-profissional.md:13`).
5. **Não existe versão intermediária boa.** Diluído, o conceito virou template (erro 75, v1). Levado a sério, vira tema.
6. **Não carrega o que o dono pede agora:** fotos de caminhão e ônibus e "algo referente a estradas, mapa-múndi"
   (`prompts-2026-09.md:5022`, `:5040`). O disco é um diagrama abstrato.

> [!note] Hipótese, confirmar
> O disco de papel pode estar saindo de uso com a chegada do cronotacógrafo eletrônico. Se a maior parte das frotas de P1 e
> P3 já registra em formato digital, a metáfora envelhece a marca. Confirmar nas conversas de validação das personas.

**Veredito: substituir o conceito como espinha do site.** Três peças podem ser aproveitadas:

- **o tempo como dado:** hora do evento, direção contínua e madrugada, dentro da direção escolhida;
- **o nome "diário de bordo" como formato da ficha de ocorrência**, o registro que sai do veículo, porque o setor já conhece
  esse documento;
- **a noite na fotografia**, não no tema da interface.

Espaço e tempo juntos (km e hora) funcionam melhor que só o tempo. É o que a direção A faz.

## Estrada e mapa como recurso estrutural (requisito novo)

Duas restrições vêm antes das ideias.

1. **A estrada como enfeite já foi recusada.** O app tinha "faixas tracejadas de estrada, marcos de km, contador animado e
   placa com pálpebra" e foi julgado temático demais (`feedback-visual-sobrio-profissional.md:13`). Estrada e mapa só
   entram como dado real e como navegação, nunca como textura ou ornamento.
2. **O produto não registra localização.** O código só lê a velocidade enviada por outro programa, quando ele existe
   (`vision/context.py:32-33`; `README.md:124`), e o servidor bloqueia a geolocalização (`backend/main.py:52`).
   - Um evento "no km 318" não pode aparecer como função do produto.
   - Pode aparecer como viagem de exemplo, rotulada, ou pelo rastreador que a frota já tem, se essa integração existir
     (pergunta 4).
   - O painel da v2 já sugere rota (`v2:320`).

| Ideia | Clichê a evitar | Uso honesto | Veredito |
|---|---|---|---|
| Malha rodoviária do Brasil | mapa escuro com linhas brilhando e pontos pulsando | Geometria real das rodovias federais do SNV. O DNIT publica os arquivos em SHP e KML ([DNIT, PNV e SNV](https://www.gov.br/dnit/pt-br/assuntos/atlas-e-mapas/pnv-e-snv)). Simplificar em SVG, com traço grafite sobre fundo claro e uma rota em destaque. | **Usar.** Nenhum template tem esse desenho. |
| Rota que avança com a rolagem | "câmera" seguindo um ponto com zoom progressivo, o assunto de um tutorial da Codrops de 21/05/2026 ([Codrops](https://tympanus.net/codrops/2026/05/21/creating-scroll-driven-svg-map-animations-with-gsap/)); carrinho andando sobre a linha | Mapa em faixa fixo na lateral, como os mapas em tira do atlas *Britannia*, de Ogilby, de 1675 ([MapCarte](https://mapdesign.icaci.org/2014/04/mapcarte-118365-britannia-by-john-ogilby-1675/)). A linha só se desenha e funciona como índice das seções. | **Usar como navegação**, sem câmera e sem zoom. |
| Trechos de rodovia separando seções | faixa tracejada no centro, textura de asfalto, tacha refletiva, marco de km desenhado | No máximo dois fios com o recorte real do mesmo trecho da rota, na escala do mapa, sem animar a faixa. | **Evitar.** Só aceitável dessa forma. |
| Mapa-múndi com rotas | globo girando com arcos de luz; mapa pontilhado de "atuação global" | O produto é vendido no Brasil, então rota internacional seria promessa. O uso honesto é a **faixa da madrugada ao vivo**: a linha entre dia e noite, calculada pela hora, sobre um mapa-múndi de base pública ([Natural Earth, domínio público](https://www.naturalearthdata.com/about/terms-of-use/); exemplo desse dado no [timeanddate](https://www.timeanddate.com/worldclock/sunearth.html)). Liga o mundo ao risco da madrugada, que é regra do produto. | **Usar só assim, uma única vez**, ou não usar. |
| Sinalização viária | placa verde como botão, âmbar de placa, alfabeto de placa na página inteira | A lógica do marco quilométrico e a hierarquia de legibilidade do Manual Brasileiro de Sinalização de Trânsito, vol. III ([SENATRAN](https://www.gov.br/transportes/pt-br/assuntos/transito/senatran/manuais-brasileiros-de-sinalizacao-de-transito)), aplicadas a rótulos em texto ("km 0 · pátio"). | **Usar como regra**, nunca como desenho. |
| Dados de estrada | "X mil km monitorados" sem fonte | A Pesquisa CNT de Rodovias avalia a malha trecho a trecho e publica mapas ([CNT, 2025](https://cnt.org.br/documento/7df4efbc-4c55-44f9-b81e-9b8d4016f90e)). A PRF publica os acidentes por UF, rodovia e km ([PRF, dados abertos](https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dados-abertos-da-prf)). Sempre com a fonte na legenda (`contexto.md:46`). | **Usar com fonte.** A frente 5 confere. |

## Três direções estruturais

### Na stack aprovada (vale para as três)

- **Cores e tipos:**
  - viram tokens no `@theme` do Tailwind 4, com nomes pelo papel ("carta", "grafite", "rota", "fonte-titulo",
    "fonte-texto"), não pelo valor;
  - as variáveis das fontes do next/font entram pelo `@theme inline`, como na Fornalha (`site-fornalha-quintal.md:35`).
- **Fontes:**
  - todas as propostas estão no Google Fonts sob licença livre (OFL) e podem ser carregadas por `next/font/google`, que
    hospeda os arquivos no próprio site no build;
  - as de eixo variável declaram o eixo usado: largura na Archivo, tamanho óptico na Source Serif 4 e na Literata;
  - de propósito, nenhuma direção usa fonte do Fontshare. Não confirmei se a licença de lá permite hospedar os arquivos
    no próprio site, que é o que o next/font faz.
- **Movimento:** GSAP com ScrollTrigger (e DrawSVG ou sequência de quadros, conforme a direção). Os plugins são gratuitos
  desde 2025 ([Webflow](https://webflow.com/updates/gsap-becomes-free)). Versões conferidas no registro na hora de
  instalar, pela regra do vault.
- **next-intl:**
  - nenhum texto fica gravado dentro do SVG ou da imagem; rótulos de mapa, km e hora vêm das mensagens em PT e EN;
  - testar o comprimento dos títulos em inglês em cada direção.
- **Armadilhas já registradas com Tailwind 4:**
  - classes caseiras que colidem com utilitários (`overline`, `col-*`);
  - regras fora de camada que vencem as camadas (`site-fornalha-quintal.md:161-171`, `:198-204`).
- **Mapas:** preparados antes, como arquivo estático gerado a partir dos dados abertos, sem API de mapa em tempo de execução.

### Direção A · "Carta de rota"

**Ideia:** o site é uma viagem noturna real, contada como um mapa em faixa. No começo, o visitante escolhe se a viagem é de
**carga** ou de **passageiros**. A estrutura é a mesma; mudam a rota, as fotos e os exemplos.

**Sequência de seções.** Cada seção é um trecho, com km e hora no rótulo. Os km e as horas abaixo são ilustrativos.

0. **Partida.** Foto ou vídeo curto sangrando a tela: carreta saindo do pátio, ou ônibus saindo da garagem, no fim da
   tarde. Título curto e o seletor "Carga | Passageiros", como duas metades fotográficas (empilhadas no celular).
1. **km 0 · Pátio: o que vai no veículo.** Foto do aparelho instalado e uma ficha curta, com as medidas marcadas como
   pendentes de protótipo.
2. **km 40 · Primeiros minutos: a calibração.** Foto da cabine tirada do banco do passageiro: mãos no volante, rosto fora
   do quadro. O texto explica que cada motorista é comparado com ele mesmo.
3. **km 290 · 02:14: o alarme.** Vídeo mudo do para-brisa à noite, com a tela real do alarme na cabine por cima. A marca do
   evento aparece na faixa lateral.
4. **Base · CCO: o que o gestor vê.** Recorte do painel com a mesma viagem e a fila de revisão. A malha do Brasil aparece
   inteira pela primeira vez, com a frota de exemplo.
5. **O que sai do veículo.** A "ficha de ocorrência" (tipo, hora, duração e veículo), no formato de uma papeleta. A imagem
   ficou no trecho anterior.
6. **Chegada · piloto.** O piloto contado como itinerário: semana 1, instalação; semanas 2 a 4, calibração e relatório.
   WhatsApp e "Já é cliente? Entrar".
7. **Ficha técnica,** no fim, em tabela densa com fios, sem cartões.

**Recurso de layout principal:**

- **No computador:** uma faixa lateral fixa (a partir de 1280 px) mostra o mapa em tira da rota escolhida, com a geometria
  real. As seções ficam ancoradas nos pontos dessa faixa.
- **Conteúdo e fotos:** o conteúdo ocupa 7 de 12 colunas. As fotos sangram a tela em três momentos: partida, alarme e
  chegada.
- **No celular:** a faixa vira um fio fino no topo de cada seção, com "km 290 · 02:14", sem cobrir o conteúdo.

**Tipografia:** **Barlow Semi Condensed** nos títulos, nomes de lugar, km e rótulos do mapa, com algarismos tabulares.
**Literata** no texto corrido e nas legendas das fotos.

- **Motivo:** é a lógica do atlas rodoviário, com mapa e texto de guia.
- **Barlow:** nasceu da sinalização pública, das placas e dos ônibus da Califórnia ([jpt/barlow](https://github.com/jpt/barlow))
  e tem larguras que cabem em rótulo de mapa.
- **Literata:** foi feita para leitura longa no Google Play Books e tem eixo de tamanho óptico para legenda
  ([TypeTogether](https://www.type-together.com/literata-3)).
- **Sem mono:** km e hora usam os algarismos tabulares da Barlow.

**Cor:**

- carta clara (branco levemente acinzentado, não creme) e grafite para o texto e a malha;
- **uma única** cor de rota, um vermelho-carmim só na linha da viagem e nas marcas de evento;
- nenhuma seção escura: a madrugada aparece nas fotos;
- âmbar e verde ficam fora da página e só existem dentro da tela do produto.

**Fotografia e produto:**

- **Fotos:** série documental em quatro momentos (pátio ou garagem no fim da tarde, cabine à noite, para-brisa na estrada
  e base ou CCO de madrugada), em duas versões, carga e passageiros.
- **Produto como objeto:** o aparelho instalado. Se o hardware ainda não estiver definido, um render do Blender com o rótulo
  "protótipo".
- **Produto como tela:** o alarme e o painel, recortados.

**Movimento:**

- a linha da rota se desenha com a rolagem (DrawSVG com ScrollTrigger), e a marca de cada evento aparece quando a seção
  entra na tela;
- um único vídeo em laço (o para-brisa), mudo e com imagem de capa;
- sem câmera, sem zoom e sem parallax;
- com `prefers-reduced-motion`, a rota já vem desenhada.

**Estrada e mapa:**

- são a própria estrutura: a faixa é o índice, a malha real do SNV aparece no CCO e o marco de km vira rótulo de seção;
- o mapa-múndi não entra, porque a rota é brasileira.

**Na stack:**

- tokens `carta`, `grafite`, `malha` e `rota` no `@theme`;
- `Barlow_Semi_Condensed` e `Literata` por `next/font/google`;
- a faixa lateral é um componente de cliente com ScrollTrigger;
- o SVG da rota é gerado a partir do SNV e guardado em `public/`;
- os rótulos de km e hora vêm do next-intl.

**Onde cada persona é atendida:**

- **P1:** escolhe "Carga" e vê a carreta no pátio. A ficha técnica diz se o produto convive com o rastreador.
- **P2:** escolhe "Passageiros" e vê um ônibus rodoviário em viagem noturna.
- **P3:** no trecho "Base · CCO", com a fila de revisão e a malha com várias garagens.
- **P4:** em "Chegada · piloto" e na ficha técnica.
- **P5:** na calibração ("comparado com ele mesmo") e em "O que sai do veículo". Mãos no volante, nunca o rosto como alvo.

**Proibido nesta direção:** faixa tracejada, asfalto, tacha, placa verde ou âmbar desenhada, pin de mapa, linha brilhando,
câmera que segue um ponto, cartão arredondado, mono e fundo escuro de interface.

**Referências:**

| Referência | O que aproveitar | O que descartar |
|---|---|---|
| Ogilby, *Britannia* (1675), [MapCarte](https://mapdesign.icaci.org/2014/04/mapcarte-118365-britannia-by-john-ogilby-1675/) | a estrada como tira contínua, lida em sequência, com o que existe à margem | o pergaminho enrolado e o ornamento de época |
| SNV do DNIT, [PNV e SNV](https://www.gov.br/dnit/pt-br/assuntos/atlas-e-mapas/pnv-e-snv) | a geometria real das rodovias federais | a simbologia do visualizador |
| [Guia Quatro Rodas](https://pt.wikipedia.org/wiki/Guia_Quatro_Rodas) | a memória brasileira do atlas de estrada: mapa com texto de guia | nostalgia e visual retrô |
| [Codrops, mapa ligado à rolagem (2026)](https://tympanus.net/codrops/2026/05/21/creating-scroll-driven-svg-map-animations-with-gsap/) | a técnica de desenhar o traço com a rolagem | a câmera, o zoom e o marcador andando |

**Riscos:**

- A rota ligada à rolagem está em alta. Se ganhar câmera e zoom, vira o tutorial.
- A rota pode sugerir um rastreamento que o produto não faz (restrição 2 da seção anterior).
- As duas versões dobram a produção de fotos.
- A Barlow vem de placa de estrada, assim como a Overpass do app recusado. Para compensar: nunca em caixa alta de placa e
  nunca sobre cor de sinalização.
- Simplificar o SNV até virar um SVG leve dá trabalho.

### Direção B · "Relatório técnico"

**Ideia:** o site é um documento para o comitê que decide a compra (`personas.md:32-33`). Tem capítulos numerados, figuras
com legenda, notas de margem com fonte e ficha técnica, no formato de um relatório de investigação de segurança misturado com
catálogo de fabricante. É o oposto de uma landing.

**Sequência de seções:**

- **Capa:** foto documental grande (carreta ou ônibus na rodovia ao anoitecer) e um quadro-resumo de quatro linhas: o que é,
  para quem, como avisa e em que estado está (protótipo).
- **1. O problema na operação:** só fatos com fonte (CTB, art. 67-C; Lei 13.103), sem número inventado.
- **2. Como funciona:**
  - figura 1: câmera → aparelho → alarme → painel, em desenho técnico;
  - figura 2: vista explodida do aparelho, renderizada no Blender.
- **3. O que ele detecta:** tabela de sinais e limiares tirada do código, com a nota "limiares em validação".
- **4. Na cabine:** foto e tela do alarme, com chamadas numeradas na margem.
- **5. No CCO:** recorte do painel com anotações sobre triagem, revisão e relatório por garagem e linha.
- **6. Privacidade e o motorista:** o que sai do veículo e o que não sai, num capítulo escrito para o motorista.
- **7. Piloto:** cronograma em tabela.
- **8. Ficha técnica.**
- **9. Perguntas difíceis:** alarme falso, custo, LGPD e sindicato.
- **Anexo:** as fontes.

**Recurso de layout principal:**

- **Grade de documento:** uma coluna de texto (6 de 12) e uma coluna de margem (3 de 12) para legendas, chamadas
  numeradas e fontes. As figuras e as fotos de abertura de capítulo sangram a largura.
- **Sumário:** fixo à esquerda no computador; no celular, vira um botão "Sumário".
- **Versão para imprimir** (`@media print`): o gestor salva em PDF e leva ao comitê. É função, não enfeite.

**Tipografia:** **Source Serif 4** nos títulos (tamanho óptico de título) e no texto. **Archivo**, em larguras estreitas,
nas tabelas, legendas, chamadas e números tabulares.

- **Motivo:** é a cultura do relatório e da ficha técnica. A serifa argumenta; a grotesca estreita organiza a tabela.
- **Source Serif 4:** tem tamanhos ópticos da legenda ao título ([Adobe Fonts](https://fonts.adobe.com/fonts/source-serif-4)).
- **Archivo:** foi desenhada para impresso e tela e vai do ExtraCondensed ao Expanded num único arquivo variável
  ([Omnibus-Type](https://www.omnibus-type.com/fonts/archivo/)).
- **Sem mono.**

**Cor:**

- papel branco e tinta preta, com fios em cinza;
- **um único** vermelho-óxido de anotação, só nas chamadas de figura e no ponto crítico, como a caneta de quem revisa;
- fotos em cor natural;
- só tema claro.

**Fotografia e produto:**

- **Aberturas de capítulo:** foto documental (carreta à noite, ônibus na garagem, CCO urbano, instalação com ferramentas e
  motorista numa parada, retratado com respeito).
- **Produto como figura técnica:** um render explodido do aparelho feito no Blender, como o brasão do São Jorge
  (`site-saojorge.md:37`), e telas anotadas.

**Movimento:**

- o mínimo: o sumário marca o capítulo atual, e as chamadas de cada figura aparecem em sequência quando ela entra na tela;
- uma única sequência de quadros ligada à rolagem, a vista explodida, com 100 a 150 quadros, no limite de peso do São Jorge
  (`site-saojorge.md:60`).

**Estrada e mapa:**

- **Figura "Onde a madrugada pesa":** a malha federal do SNV com os trechos noturnos de duas viagens de exemplo, uma de carga
  e uma de passageiros.
- **Figura "Agora é madrugada aqui":** mapa-múndi com a faixa da noite calculada quando a página abre. É o único mapa-múndi
  do site e, na versão em inglês, dá o enquadramento global.
- **Aberturas de capítulo:** um pequeno mapa de localização do trecho da foto, na margem, como fazem os relatórios de
  investigação.

**Na stack:**

- tokens `papel`, `tinta`, `fio` e `anotacao` no `@theme`;
- `Source_Serif_4` (eixo de tamanho óptico) e `Archivo` (eixo de largura) por `next/font/google`;
- a folha de impressão fica numa camada própria do CSS;
- ScrollTrigger só para o sumário, as chamadas e a vista explodida;
- as notas de fonte vêm do next-intl nos dois idiomas.

**Onde cada persona é atendida:**

- **P1 e P4:** no formato de dossiê, na ficha técnica, nas fontes e na versão para imprimir.
- **P2:** na capa, com um resumo em linguagem simples, e no capítulo com ônibus.
- **P3:** no capítulo 5, com a triagem por garagem, linha e turno.
- **P5:** no capítulo 6, dirigido a ele.

**Proibido nesta direção:** cartão arredondado, ícone de biblioteca, número sem fonte, gradiente, fundo escuro, mono, selo e
carrossel.

**Referências:**

| Referência | O que aproveitar | O que descartar |
|---|---|---|
| [NTSB HAR-12/01](https://www.ntsb.gov/investigations/AccidentReports/Reports/HAR1201.pdf), sobre fadiga de motorista de ônibus e sistemas de monitoramento a bordo | capítulos numerados, figuras com legenda, mapa de localização e conclusões separadas das recomendações | o tom de investigação de acidente e o marketing pelo medo |
| [Pesquisa CNT de Rodovias 2025](https://cnt.org.br/documento/7df4efbc-4c55-44f9-b81e-9b8d4016f90e) | mapas do Brasil por trecho, com legenda e fonte | gráfico de pizza e selos |
| [Fichas técnicas do Volvo FH](https://www.volvotrucks.com.br/pt-br/trucks/models/volvo-fh/data-sheets.html) | a ficha técnica como peça de venda, densa e exata | a identidade da Volvo |
| [Marcopolo Paradiso G8 1800 DD](https://onibus.marcopolo.com.br/es/productos/marcopolo-g8/paradiso-g8-1800-dd) | o catálogo de ônibus: foto grande, detalhe e ficha | o render publicitário brilhante |

**Riscos:**

- **Ser lido como "só texto",** a queixa sobre a v1 (nota 08, commit `419c555`). Mitigação: foto grande em todo capítulo e
  figuras de verdade.
- **Página longa no celular.**
- **Tom frio para P2.**
- **Tudo precisa de fonte:** cada afirmação depende da frente 5.
- **Hora ao vivo exige cálculo certo:** o mapa-múndi depende de cálculo astronômico correto, com uma biblioteca pequena ou
  cálculo próprio testado.

### Direção C · "Escalas"

**Ideia:** o site muda de escala em três atos, do mapa-múndi ao olho do motorista, e depois volta à frota. A **privacidade
vira uma fronteira de escala**: a imagem só existe dentro da cabine, e das escalas acima dela só chega o evento.

**Sequência de seções:**

- **Ato I · A malha:**
  - começa na escala do mundo: mapa-múndi com a faixa da madrugada, título curto e botão "Pedir piloto" já na primeira tela;
  - corte seco para a escala do Brasil, com a malha federal do SNV;
  - termina na rodovia: foto ou vídeo de um trecho à noite, com carreta e ônibus.
- **Ato II · A cabine:**
  - antes da cena, o visitante escolhe caminhão ou ônibus. As duas sequências têm a mesma duração;
  - uma cena fica presa na tela, com sequência de quadros ligada à rolagem: veículo visto de fora → para-brisa → aparelho
    no painel → tela do alarme tocando;
  - na escala 1:1 aparece a representação do olho, com a legenda "isto não sai do veículo".
- **Ato III · A frota:**
  - o evento sobe como registro;
  - corte para o CCO (tela recortada), depois a frota sobre a malha, o piloto e a ficha técnica.

**Recurso de layout principal:**

- **Escala gráfica fixa** na borda da tela, marcando o ato e a escala: 1:40.000.000 → 1:5.000.000 → 1:50.000 → 1:20 → 1:1,
  e a volta. É a convenção dos mapas usada como navegação.
- **Fronteira da privacidade:** a régua tem um fio com a legenda "a imagem não passa daqui". É a promessa de privacidade
  desenhada.
- **Entre as cenas presas:** o conteúdo segue numa grade editorial 7/5.

**Tipografia:** **Sofia Sans** (Extra Condensed nos títulos de ato e nos números da escala; largura normal no texto) e
**B612** para a voz do instrumento: tela do alarme, painel, rótulos da régua e dados.

- **B612:** nasceu de uma pesquisa da Airbus com a ENAC sobre legibilidade nas telas de cabine de avião
  ([polarsys/b612](https://github.com/polarsys/b612)). É o paralelo mais direto possível com um alarme lido por um motorista
  cansado às 2 h.
- **Sofia Sans:** é um sistema tipográfico feito para uma cidade, com quatro larguras variáveis
  ([Lettersoup](https://www.lettersoup.de/sofia-sans/)). Permite título enorme e texto corrido na mesma família.
- **Sem mono.**

**Cor:**

- neutros de concreto e asfalto (cinzas sem azul), claros nas partes de texto;
- o escuro só existe dentro das cenas fotográficas;
- nenhum acento de marca na página: a única cor saturada é a do alarme do produto, definida no redesenho do app, e não é
  âmbar;
- no mapa-múndi, a noite é um véu preto translúcido.

**Fotografia e produto:**

- **Três sequências de quadros,** uma por ato, com captação real ou imagem convertida em vídeo com curadoria (as três
  origens do São Jorge, `site-saojorge.md:60-61`).
- **Mapa-múndi e malha** renderizados a partir de dados abertos.
- **O aparelho** em 3D, renderizado antes no Blender.
- **O produto** aparece no ponto alto do Ato II (o alarme) e no Ato III (o painel).

**Movimento:**

- três cenas presas na tela no site inteiro, uma por ato, com ScrollTrigger;
- a troca de escala é por corte ou máscara, **nunca por zoom contínuo**, com no máximo 3 animações por tela
  (`site-saojorge.md:58`);
- com `prefers-reduced-motion`, cada cena vira um quadro parado com legenda.

**Estrada e mapa:**

- formam o Ato I e o fundo do Ato III;
- mapa-múndi (com a faixa da madrugada), malha do Brasil e rodovia são três escalas da mesma história;
- a régua de escala é a navegação.

**Na stack:**

- tokens `concreto`, `asfalto`, `veu-noite` e `alarme` no `@theme`;
- `Sofia_Sans`, `Sofia_Sans_Extra_Condensed` e `B612` por `next/font/google`;
- as sequências de quadros são lidas de `public/`, num leitor em canvas, no mesmo modelo do `scroll-sequence.tsx` do São
  Jorge (`site-saojorge.md:109-116`);
- a régua é um componente de cliente com ScrollTrigger;
- os números da escala e as legendas vêm do next-intl.

**Onde cada persona é atendida:**

- **P1 e P2:** escolhem caminhão ou ônibus antes do Ato II.
- **P3:** no Ato III, com a frota sobre a malha e a triagem.
- **P4:** no fim do Ato III, com o piloto e a ficha técnica.
- **P5:** na fronteira "a imagem não passa daqui", explicada no Ato II.

**Proibido nesta direção:** zoom contínuo no estilo *Powers of Ten*, globo 3D, arco de luz, ponto pulsando, partículas,
brilho, visor de visão computacional fora da escala 1:1 e âmbar.

**Referências:**

| Referência | O que aproveitar | O que descartar |
|---|---|---|
| [Eames, *Powers of Ten* (1977)](https://www.eamesoffice.com/the-work/powers-of-ten/) | contar a história mudando de escala, com a medida escrita na tela | o zoom contínuo e a viagem até o átomo |
| [Natural Earth](https://www.naturalearthdata.com/about/terms-of-use/) e o SNV do DNIT | base de mapa sem problema de licença | — |
| São Jorge (`site-saojorge.md`) | atos, sequências de quadros, Blender e limite de peso | a paleta e a tipografia daquele cliente |
| Terminal Industries (`awwwards-estudo.md:204`) | logística contada pela rolagem sem virar folheto | narrativa longa demais para conversão |

**Riscos:**

- **Custo:** é a mais cara das três (três sequências, 3D e captação).
- **Produto tarde demais para P1:** o Ato I atrasa o produto. Mitigação: título e "Pedir piloto" na primeira tela, mais um
  atalho "Ver na cabine".
- **Peso no celular:** limite de cerca de 6 MB por sequência (`site-saojorge.md:60`).
- **Efeito:** se o corte virar zoom, cai no efeito recusado.
- **Largura da B612:** a fonte é larga; testar rótulos longos em português e em inglês.

## O que manter

- **A decisão de mostrar o produto funcionando** em vez de só descrevê-lo (`v2:243-260`). O sinal de abertura do olho é
  conteúdo real e deve ficar, redesenhado na linguagem da direção escolhida e sem mira.
- **A tela do alarme na cabine como peça central** (`v2:276-289`), com a interface real do produto, fotografada ou
  renderizada dentro de uma cabine.
- **A ficha técnica como lista com fios, sem cartões** (`v2:189-193`). É a parte mais próxima da Fornalha, onde a
  "densidade não precisa de card" (`site-fornalha-quintal.md:209-211`).
- **Os limiares de 1 s, 3 s e 6 s** como informação (`v2:270-274`), com outra forma.
- **Os títulos medidos em `cqi`** (`v2:62`, `:99`, erro 49) **e o cuidado com movimento reduzido** (`v2:516-520`).
- **As telas marcadas como "dados de demonstração"** (`v2:259`, `:344`).
- **A frase "A imagem fica no caminhão. Só o evento sai dele."** (`v2:352`), trocando "caminhão" por "veículo". É a semente da
  fronteira de escala da direção C e da ficha de ocorrência da direção A.

## Recomendações para a próxima versão (em ordem de prioridade)

1. **Não codar a v3 antes da escolha.** Mostrar as três direções como prévia estática, com um quadro de computador e um de
   celular cada e foto provisória. O Matheus escolhe (erro 75; `diferenciacao-visual.md:39-47`).
2. **Escrever a lista de proibições da v3** a partir dos 29 sinais acima. Nada do que veio da v1 e da v2 volta: hero com
   texto e widget, rótulo mono, par de sans com a mono da mesma família, fundo escuro com âmbar, janela falsa, JSON, mira e
   pontos no rosto, brilho, laço infinito, cartões iguais e selo com bolinha.
3. **Produzir a série de imagens e vídeos antes do layout**, com a frente 3: lista de cenas por seção e por segmento, com
   espaços reservados e nomeados.
4. **Preparar a base cartográfica real,** com o SNV do DNIT simplificado e o Natural Earth para o mundo. Escrever a regra de
   honestidade do mapa: contexto não é função, e nenhum evento aparece "num km" sem rótulo de exemplo.
5. **Fechar tipografia e cor com o motivo escrito na nota do projeto:** duas cores e um neutro, semáforo só dentro da tela do
   produto e contraste mínimo de 4,5:1 no texto pequeno. Tudo como tokens no `@theme` e fontes por `next/font`.
6. **Definir um limite de movimento por tela:** até 3 animações, todas ligadas à rolagem ou a um estado, nada em laço. Cada
   cena precisa de versão para movimento reduzido.
7. **Alinhar o site com o redesenho do app.** As telas do produto que aparecem no site são o app. Decidir a direção do site
   antes de redesenhar o app evita uma terceira paleta.
8. **Sugestões para o vault (não aplicadas):**
   - atualizar o erro 34 e `diferenciacao-visual.md:130`, que ainda citam a Geist como alternativa à Inter, embora Geist com
     Geist Mono seja hoje o padrão do `create-next-app`;
   - registrar "estrada como ornamento" como erro a evitar no DriveSafe;
   - lembrar que a cópia local do vault está 7 commits atrás do `origin/main`.

## Perguntas que só o Matheus responde

1. **O que o mapa-múndi deve dizer?** Pode ser atuação fora do Brasil, a versão em inglês ou só o clima de estrada. Se não
   houver operação fora do país, proponho a faixa da madrugada (direções B e C) ou só a malha brasileira (direção A).
2. **Qual estrutura:** rota (A), relatório (B) ou escalas (C)? Dá para usar a espinha de uma com uma peça de outra (por
   exemplo, A com a ficha técnica de B), mas não as três juntas.
3. **Vai haver fotos reais?** Caminhão, ônibus, cabine, garagem e CCO fotografados de verdade, ou tudo gerado com curadoria?
   A direção C depende disso.
4. **O produto vai integrar com o rastreador ou o GPS da frota?** Sem isso, nenhum evento pode aparecer "num km" como função
   do produto.
5. **Já existe logo ou nome final** ("DriveSafe" ou "DriveSafe AI")? Ou a direção escolhida deve propor o símbolo?
6. **Site claro ou escuro?** Depois da recusa do app escuro, um site claro, com a noite só nas fotos, é aceitável?
7. **Que aparelho pode aparecer nas imagens,** enquanto o hardware final não está definido (`contexto.md:38`)? Um render
   rotulado "protótipo" serve?
8. **Quais casos de exemplo dão a cara do site?** Uma viagem de carga (por exemplo, São Paulo a Curitiba pela BR-116) e uma
   operação de passageiros (rodoviário noturno ou urbano).
9. **A direção escolhida para o site também vai guiar o redesenho do app e do painel?**
