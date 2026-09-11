# Frente 3 · Imagens, vídeo e prompts (com ideias para o Magnific)
Avaliador: agente 3 · 11/09/2026 · versão avaliada: `site-drivesafe/previa/v2/index.html` (com `previa-topo.png`,
`previa-desktop.png` e `previa-celular.png`) e `site-drivesafe/prompts-imagens.md`

> **Requisitos que chegaram no meio da avaliação (coordenador, 11/09).** (1) O site deve ter "algo referente a
> estradas, mapa-múndi etc.". (2) O prompt de fundos, imagens e vídeos deve ser "muito pensado", separando FUNDOS,
> IMAGENS DE SEÇÃO, BANNERS e VÍDEOS, com objetivo, persona, composição, luz, lente, paleta, proibições, recortes,
> variações e fluxo no Magnific para cada peça. O método de referência é o do próprio Matheus: shot list numerada,
> sequências de 100 a 150 quadros para rolagem, image-to-video com curadoria e objeto 3D no Blender
> (`Obsidian/90 - Projetos/site-saojorge.md:37`, `:55-61`). Os dois pedidos estão nos Anexos B, C e F.

**Índice:** nota · notas por critério · leitura por persona · problemas · o que manter · recomendações · perguntas ·
Anexo A (diagnóstico linha a linha do prompt atual) · Anexo B (cenas necessárias) · Anexo C (estradas e mapas) ·
Anexo D (regras da nova série) · Anexo E (Magnific) · Anexo F (esqueleto do novo arquivo) · Fontes

## Nota geral: 2/10
A prévia v2 não tem uma única foto, vídeo ou mapa do setor, e o único roteiro de imagens que existe foi escrito para
um conceito já abandonado, cobre só caminhão e pede exatamente os efeitos que o Matheus rejeitou (grão, tracejado de
estrada, piscada).

## Notas por critério

| Critério | Nota | Por quê | Evidência |
|---|---|---|---|
| Adequação à divulgação para logística e passageiros | 2 | Na v2, o setor só aparece em texto e só como "caminhão". No prompt, 5 das 14 peças são papel e disco de tacógrafo ou faixa refletiva, sem produto nem frota | `previa/v2/index.html`: nenhuma tag `<img>`, `<video>` ou `background-image` (a busca só acha o `clip-path` da linha 436); todo visual é SVG gerado em JS (`:416-569`) ou tela falsa em CSS (`:276-289`, `:300-343`); "caminhão" em `:268`, `:352`, `:403`. `prompts-imagens.md:36-57`, `:101-109`, `:134-142`, `:177-182` |
| Cobertura de cenas por seção e persona | 1 | Nenhum ônibus, van ou VUC, gestor ou CCO, garagem, instalação ou cena de operação de dia | Busca por ônibus, bus, van, VUC, gestor, CCO, garagem e instalação em `prompts-imagens.md` só acha `:83`. P2 exige "ônibus, não só caminhão" (`personas.md:48`) |
| Realismo e contexto brasileiro | 4 | Há bons indícios (BR de pista simples, terra vermelha, pasto), mas o resto é genérico ou importado: "trucking culture", "roadside diner", lâmpada de sódio. Nada sobre caminhão de cabine avançada, faixa central amarela ou placa ilegível | `prompts-imagens.md:15`, `:116`, `:126`, `:98` |
| Sinais de imagem de IA a evitar | 3 | A lista de negativos cobre mãos e pele plástica, mas os prompts pedem justamente o que atrai artefato: "cinematic", fundo desfocado em tudo, poeira no ar, chuva com rastro de farol, mãos no volante, copo na mão, olho em close extremo | Negativos em `:23-27`. Pedidos em `:17`, `:65-67`, `:75-77`, `:88`, `:127`. Kamali et al. 2025 classificam "excessivamente cinematográfico" e pele cerosa como artefatos de estilo, e objeto segurado de forma improvável como artefato funcional |
| Consistência como série fotográfica | 3 | O bloco de estilo comum é bom. Mas as peças misturam scan de papel, macro, infravermelho em preto e branco, drone, retrato e textura, sem imagem-âncora, elenco ou aparelho fixo | `:12-19`, `:36-142` |
| Uso no layout (texto, recortes, proporções) | 3 | Cada peça tem proporção e lugar no site (bom), mas só 2 de 10 definem área livre para texto e nenhuma tem recorte de celular. O 21:9 vira uma faixa de 171 px na largura de 400 px do print de celular | Área livre só em `:118` e `:140-141`. 21:9 em `:112`. `previa-celular.png` tem 400 px de largura |
| Cuidados legais e éticos | 4 | Proíbe logo e marca, explica o motivo e avisa que a pessoa é gerada. Faltam regras para placa legível, referência de terceiros e rótulo de imagem ilustrativa. Duas peças vigiam ou estigmatizam o motorista | Bom: `:17-18`, `:29-30`, `:131`. Ruim: `:70-79`, `:161-168` |
| Produção (modelo, consistência, ampliação) e vídeo | 3 | Pede loop, vídeo sem áudio e versão parada (bom). Não define modelo, quadro inicial e final, referência, ampliação, curadoria nem custo. Os 4 vídeos são clichês ou efeitos já rejeitados | `:146-152`. "Veo, Kling, Runway ou Sora" em `:148`. V1 em `:156-158`, V2 em `:163-165`, V3 em `:172-174` |

## Leitura por persona

As imagens são decisivas nesta frente: cada persona só se reconhece se vir o próprio veículo e o próprio trabalho.

| Persona | O que precisa ver em imagem | O que a v2 e o prompt entregam | Nota para as imagens |
|---|---|---|---|
| P1 Renata (carga, 190 carretas) | Carreta em BR, operação noturna, aparelho plausível na cabine, alguém revisando o evento | v2: nada. Prompt: cabine de madrugada (03), pátio (06) e aparelho mal posicionado (05). O papel de tacógrafo lembra controle de jornada, que ela já tem (`personas.md:21`) | 3 |
| P2 Carlos (fretamento, 38 ônibus) | Ônibus, noite, passageiros protegidos, garagem | Nenhum ônibus. A chamada da v2 é "Comece com cinco caminhões" (`index.html:403`): ele fecha a aba | 1 |
| P3 Juliana (CCO, 620 ônibus urbanos) | Ônibus urbano, CCO, escala, câmera que olha só o motorista | Nada disso. O rosto em pontos no topo (`index.html:243-259`) e o olho infravermelho (`prompts-imagens.md:70-79`) sugerem vigilância, argumento pronto para o sindicato (`personas.md:75`) | 1 |
| P4 Marcos (financeiro, caminhões, vans e VUCs) | Frota mista, van e VUC, instalação rápida | Nenhuma van, VUC ou instalação | 2 |
| P5 José (carreteiro, 58) | Motorista tratado com respeito e competente no trabalho | Retrato "cansado", de boné gasto, com café de beira de estrada (`:126-128`), piscada lenta (`:163-165`) e olho em close (`:75-77`): ele se vê como suspeito (`personas.md:116-118`) | 2 |

## Problemas, do mais grave ao menos grave

| # | Gravidade | Problema | Evidência | Impacto | Correção concreta |
|---|---|---|---|---|---|
| 1 | crítica | A v2 não tem nenhuma imagem, vídeo ou mapa do setor | Nenhuma tag `<img>`, `<video>` ou `background-image` em `previa/v2/index.html`. Os visuais são SVG desenhado em JS (`:416-569`) e telas falsas em CSS (`:276-289`, `:300-343`). Os prints `previa-desktop.png` e `previa-celular.png` mostram só cartões escuros. O pedido do Matheus está em `contexto.md:7-8` | Descumpre o pedido explícito ("imagens relacionadas a isso") e deixa a página com cara de SaaS genérico | Produzir a série do Anexo B (15 imagens de seção, 5 fundos, 4 banners, 6 vídeos) seguindo a política de IA que o Matheus decidir (pergunta 1) |
| 2 | crítica | O prompt de imagens é de um conceito abandonado e repete os efeitos rejeitados | Direção "Diário de bordo" em `prompts-imagens.md:1-4`. Grão de filme em `:15`, `:54`, `:67`, `:77`, `:88`, `:98`, `:118`, `:128`, `:158`, `:164`. Faixa tracejada em movimento em `:156-157`. Piscada em `:163-165`. Papel e disco de tacógrafo em `:36-57`, `:139-141`, `:179-181`. A memória do projeto registra a rejeição de "grão, tracejados, animação de estrada, piscada" (`feedback-visual-sobrio-profissional.md:13-15`), e a própria pendência pede revisão (`PENDENCIAS.md:213`) | Quem gerar a partir desse arquivo repete o "Cabine noturna" rejeitado em 10/09 | Descartar 9 das 14 peças (Anexo A) e reescrever o arquivo no esqueleto do Anexo F |
| 3 | crítica | Só há caminhão: nenhum ônibus, van ou VUC, gestor ou CCO, garagem, instalação ou cena de dia | A busca desses termos em `prompts-imagens.md` só acha `:83`. P2: "ônibus, não só caminhão" (`personas.md:48`) e "ver funcionando na garagem" (`:54`). P3: CCO e triagem (`:68-74`). P4: vans e VUCs (`:82`). Na v2, a palavra "ônibus" não aparece | Metade do público (passageiros) e o comprador financeiro não se reconhecem | Cenas S02, S05, S06, S08 a S14 do Anexo B, e topo em "par gêmeo" carga e passageiros com o mesmo enquadramento |
| 4 | alta | O aparelho é descrito de forma implausível e mudaria a cada geração | O prompt põe o computador exposto no painel e a câmera "high near the windshield" (`prompts-imagens.md:86-88`). O README pede câmera "de frente para o motorista, com o rosto ocupando boa parte da imagem" (`README.md:283-284`). O manual do Seeing Machines Guardian manda montar o sensor no painel a até ±20° da linha reta de visão do motorista (ManualsLib). A v2 desenha uma tela com alarme visual (`index.html:276-289`), mas no código o alarme é só sonoro: alto-falante ou buzzer (`vision/alarm.py:1`, `README.md:277-280`) | A foto promete hardware que não existe e cada imagem mostraria um aparelho diferente. P1 e P4 perdem a confiança | Usar a descrição canônica fixa do Anexo D.6 e o modelo do Blender como referência de produto em toda cena. Sem tela e sem luz de alerta até o hardware ser definido |
| 5 | alta | A imagem pode virar afirmação falsa | O protótipo está marcado como "testado sem hardware real" (`Obsidian/DriveSafe AI - Monitoramento de Motoristas/00 - DriveSafe AI.md:4`, `:81`). Não há frota em piloto (`contexto.md:37`), mas a v2 diz "Em piloto com transportadoras" (`index.html:229`). O produto não tem localização: a única ocorrência é `geolocation=()`, que bloqueia o recurso (`backend/main.py:52`), e a velocidade só chega por arquivo externo (`README.md:124`). A v2 mostra a rota "São Paulo → Curitiba · BR-116" (`index.html:320`). A ideia de "luz de alerta do aparelho" também não existe no código | Foto de "instalação num cliente" ou mapa com veículos ao vivo vira prova inventada. P4 desconfia de promessa sem fonte (`personas.md:95`) | Legenda "Imagem ilustrativa" nas cenas de uso. Mapas só como contexto geográfico, sem veículo, rota ao vivo ou evento. Nenhuma luz de alerta |
| 6 | alta | Há peças que vigiam ou estigmatizam o motorista | Olho infravermelho em close extremo (`prompts-imagens.md:70-79`). Piscada que "fica fechada um momento a mais" (`:163-165`). Retrato "tired", boné gasto e café (`:126-128`). Rosto em pontos no topo da v2 (`index.html:243-259`). Medos do P5: ser filmado e vigiado (`personas.md:105-107`) e imagem que humilhe (`:116-118`). Os model cards do MediaPipe põem vigilância fora do escopo (`00 - DriveSafe AI.md:21-22`) | Dá argumento ao sindicato e à CIPA e contradiz "Nenhuma imagem é gravada" (`index.html:231`) | Nunca mostrar rosto realista com sobreposição biométrica. Mostrar o motorista competente (S04, S13, S14). O alarme aparece pela consequência: parar e descansar |
| 7 | alta | O texto dos prompts atrai sinais de IA | "cinematic documentary" (`:67`). "shallow depth of field" no bloco global (`:17`). "dust particles in the air" (`:88`). Chuva com rastros de farol (`:65-66`). Mãos no volante (`:65`). Copo na mão (`:127`). "no text, no letters, no numbers" como negação dentro do prompt (`:17`). Kamali et al. 2025 listam "excessivamente cinematográfico" e pele cerosa como artefato de estilo; objeto segurado de forma improvável é artefato funcional, o mais difícil de notar. O guia do Veo 3.1 recomenda descrever o que se quer em vez de negar | Resultado com "cara de IA", o mesmo motivo da rejeição de 10/09 | Aplicar as regras do Anexo D: horários canônicos, profundidade de campo moderada, textura real, mãos fora de foco ou em gesto simples, exclusões escritas como descrição positiva |
| 8 | alta | Não há área de texto nem recorte de celular | Cada peça tem uma só proporção (`prompts-imagens.md:36-142`). Área livre só em `:118` e `:140-141`. O 21:9 de `:112` vira faixa de 171 px nos 400 px do `previa-celular.png`. O padrão do Matheus é 4:5 em card com foto (`Obsidian/90 - Projetos/Padroes/regras-de-componentes.md:67`) | Imagem boa no computador fica inutilizável no celular | Master 3:2 com zona segura, ou núcleo 4:5 expandido para 16:9 e 21:9 (Anexo B.1). Campos de recorte obrigatórios no esqueleto |
| 9 | média | O contexto brasileiro é raso e tem importações | "Brazilian highway trucking culture" (`:15`) é genérico e puxa caminhão americano. "roadside diner" (`:126`) é conceito dos EUA. "sodium street lamps" (`:98`). Nada sobre cabine avançada, faixa central amarela, direção à esquerda ou placa Mercosul ilegível | É artefato "sociocultural" (Kamali et al. 2025) e brasileiro percebe na hora | Checklist Brasil do Anexo D.4, com fontes (Autopapo, DETRAN-PR, IBGE) |
| 10 | média | Não há método de produção nem de consistência | "Veo, Kling, Runway ou Sora" (`:148`). Faltam modelo, imagem-âncora, referências de estilo, produto e personagem, ampliação, curadoria e custo. O loop é pedido sem quadro inicial e final (`:150`) | 14 imagens que não parecem da mesma série e crédito gasto às cegas | Fluxo do Anexo E: Space com nós duplicados, Relight, Expand, Upscale Precision e quadro inicial igual ao final |
| 11 | média | Público e direção desatualizados | O item 08 cita "convite para piloto, pesquisa e investimento" (`:113`). Universidades e investidores saíram do foco (`contexto.md:42-43`), mas a v2 ainda diz "Também atendemos universidades" (`index.html:404`) e `PENDENCIAS.md:215-216` ainda registra "Diário de bordo" como direção aprovada | O próximo redator pode seguir a direção errada | Atualizar `PENDENCIAS.md` e o cabeçalho do novo arquivo com a direção e o público atuais |
| 12 | média | A imagem de compartilhamento não mostra o setor | O banner Open Graph é um disco em papel creme (`:139-141`). P1 se informa por LinkedIn e WhatsApp (`personas.md:34`) | O link compartilhado não diz "frota" nem "ônibus" | B01 feito a partir de S01 ou S07, com o título renderizado por código em PT e EN |
| 13 | baixa | Falta contrato de entrega e registro | Só existe "onde salvar" (`:7-8`). Sem alt text, sem coluna de licença e atribuição (obrigatória se entrarem dados do OpenStreetMap ou do Copernicus), sem status e sem custo real | Retrabalho e risco de publicar mapa sem atribuição | Tabela de nomes no modelo de `como-entregar-midia.md` do São Jorge e campos de registro por peça (Anexo F) |

## O que manter

- **Prompts em inglês com notas em português** (`prompts-imagens.md:6`).
- **Nada de texto, logo ou marca dentro da imagem, com o motivo explicado** (`:17-18`, `:24`, `:29-30`): o texto
  entra por código nos dois idiomas. Manter a regra, mas reescrever como descrição positiva (Anexo D.5).
- **Negativos anatômicos** "deformed hands, extra fingers, plastic skin" (`:25-26`).
- **Ficha por peça com nome de arquivo, proporção e lugar no site** (`:5`). É a base do esqueleto novo.
- **Loop sem áudio, com imagem parada para movimento reduzido** (`:150-152`).
- **Pós-produção:** AVIF e WebP, versões por tela, conferência de contraste e registro no Obsidian (`:186-193`).
- **Aviso de pessoa gerada e o antídoto "weathered skin, natural wrinkles, unposed"** (`:131-132`).
- **"face out of frame" na cabine** (`:65`): protege identidade e combina com a mensagem de privacidade.
- **Reservar área vazia para texto já no prompt** (`:118`, `:140-141`), agora em todas as peças.
- **"no brand markings" e "neat cable routing" no aparelho** (`:86-88`).
- **Na v2, a curva do olho e o painel continuam em código:** interface real vale mais que tela inventada por IA.
  Nas fotos com monitor, a tela sai escura para receber a interface real (Anexo D.5).

## Recomendações para a próxima versão (em ordem de prioridade)

1. **Antes de gerar qualquer coisa:** decidir a política de IA (pergunta 1) e fechar o aparelho canônico no Blender,
   com render de frente, 3/4, lateral e noite (Anexo D.6).
2. **Reescrever `prompts-imagens.md` no esqueleto do Anexo F**, descartando as 9 peças indicadas no Anexo A.
3. **Âncora de estilo aprovada pelo Matheus antes da série:** S01 de dia, S01 à noite (Relight) e S07. Mostrar as
   3 imagens antes do resto, conforme a memória do projeto ("mostrar uma prévia concreta antes de codar visual",
   `feedback-visual-sobrio-profissional.md:15`).
4. **Gerar na ordem da venda:** S01 e S02 (topo) → S07, S08, S10, S11 (segmentos) → S05, S06 (gestão) → S12
   (instalação) → S13, S14, S04 (motorista) → B01 a B04.
5. **Mapas com dados reais, em código ou no Blender** (F01, F02, F04, F05), com atribuição. Nenhuma geografia gerada
   por IA (Anexo C).
6. **No máximo 3 vídeos gerados** (V01 no topo, V03 como sequência de rolagem da garagem, V02 opcional). V05 sai do
   Blender e V04 e V06 são código. Todos com versão parada.
7. **Captação real em paralelo:** protótipo em bancada, veículo parado com consentimento e garagem parceira. As
   imagens de IA vão sendo substituídas, como no contrato de substituição do São Jorge
   (`SITES E PROJETOS/saojorge/docs/plano-animacoes.md:143-147`).
8. **Legenda "Imagem ilustrativa"** nas cenas de uso, alt text em PT e EN e créditos de dados de mapa no rodapé.
9. **Orçamento de 20 a 30 mil créditos** (Anexo E.3). Testar movimento no MiniMax H3 Max Turbo (200 créditos por
   5 s) antes do vídeo final no Kling 2.5 (650 créditos por 10 s em 1080p, custo medido no São Jorge).

## Perguntas que só o Matheus responde

1. **Imagem gerada por IA pode ir para o site publicado**, com a legenda "Imagem ilustrativa"? Ou fica só como prévia
   até existir captação real, como no São Jorge ("release sem nenhum pixel gerado por IA",
   `plano-animacoes.md:143-147`)? Aqui não há frota real para fotografar, então a resposta muda o plano inteiro.
2. **O hardware vai ter tela, LED de status ou luz de alerta?** Hoje o alarme é só sonoro (`vision/alarm.py:1`). A
   câmera infravermelha será de 850 nm (brilho vermelho fraco visível de perto no escuro) ou de 940 nm (invisível)?
   Isso muda todas as cenas noturnas.
3. **Existe protótipo montado, transportadora ou garagem parceira** para fotografar e filmar com autorização escrita
   e sem logotipos?
4. **O que o mapa-múndi deve dizer?** A proposta é mostrar a noite real no momento da visita, com o Brasil em destaque
   e sem rotas entre continentes (F05). Existe operação fora do Brasil que valha mostrar?
5. **O topo mostra caminhão, ônibus ou o par gêmeo** que troca conforme a escolha "Carga | Passageiros"?
6. **Aprova um elenco fixo gerado?** Motorista de carga de 55 a 60 anos, motorista de ônibus urbano (mulher de 40 a
   45), gestora de 40 a 45 e técnico de 30 a 35, com diversidade de cor e tipo físico.
7. **Qual plano e saldo do Magnific** para esta série, e quem dispara as gerações? Gastar crédito é decisão do Matheus
   (erro 46 do vault, `erros-que-a-ia-comete.md:274-278`).
8. **O site continua escuro como a v2?** Isso define se as áreas de texto nas fotos devem ser escuras ou claras.

---

## Anexo A · Diagnóstico linha a linha do `prompts-imagens.md`

Das 14 peças (10 fotos e 4 vídeos): **nenhuma serve como está, 5 podem ser reescritas e 9 devem ser descartadas.**

| Trecho | Linhas | Veredito | Por quê |
|---|---|---|---|
| Título e direção "Diário de bordo" | 1-4 | Descartar | O conceito foi abandonado quando a v2 virou página de produto (`PENDENCIAS.md:198-207`) |
| Uso, idioma e onde salvar | 5-8 | Manter | Funciona. Acrescentar o contrato de nomes e o status de cada peça |
| "Enquanto as imagens não chegam" | 9-10 | Reescrever | Cita fundos em código (papel, grade do disco, faixa refletiva) que não existem na v2 |
| Bloco de estilo | 14-19 | Reescrever | Filme 35 mm com grão (`:15`) repete efeito rejeitado. A paleta "cream paper" (`:16`) é do conceito morto. O desfoque global (`:17`) deixa tudo igual e com cara de IA. "Brazilian highway trucking culture" (`:15`) só fala de carga. "not a stock photo" (`:18`) é negação vaga. Manter: "natural and practical light only", "honest and unpolished", "no logos" |
| Negativos | 23-27 | Manter e ampliar | Acrescentar placa e tela legíveis, caminhão americano, faixa central branca em pista de mão dupla, parede de monitores de CFTV, malha de pontos sobre rosto, pôr do sol e rastros de luz. A lista de modelos do Magnific só mostra `prompt` como entrada obrigatória e não mostra campo de negativo, então as exclusões também devem ir escritas como descrição |
| Nota sobre texto e logo | 29-30 | Manter | O motivo está certo: idiomas e direito de uso |
| 01 `papel-diagrama` | 36-45 | Descartar | Textura de papel é o efeito decorativo rejeitado, sem produto nem frota |
| 02 `disco-tacografo` | 47-57 | Descartar | O disco não é o produto e traz números legíveis (a própria nota admite, `:56-57`). Lembra controle de jornada, que P1 já tem (`personas.md:21`) |
| 03 `cabine-madrugada` | 59-67 | Reescrever como S01 noite | Manter o rosto fora do quadro e o brilho âmbar do painel. Tirar chuva com rastros de farol, "tired", "cinematic" e mãos no volante em destaque. Pôr o aparelho canônico e trocar a vista do banco do passageiro por um enquadramento sobre o ombro do motorista |
| 04 `olho-infravermelho` | 70-79 | Descartar | É biometria em close: estética de vigilância, contra o medo do P5 (`personas.md:105-107`) e contra a mensagem "descarta a imagem" (`index.html:353`) |
| 05 `dispositivo-painel` | 81-88 | Reescrever como S03 | A posição está errada, o computador fica exposto e há poeira no ar. A origem passa a ser o render do Blender usado como referência de produto |
| 06 `patio-frota` | 91-98 | Reescrever como F03 | A vista aérea é boa: de cima não aparecem placa, logo lateral nem rosto. Tirar grão e "sodium", pôr garagem de ônibus como variante e fazer dia e noite por Relight |
| 07 `faixa-refletiva` | 101-109 | Descartar | Ornamento temático do tipo rejeitado no "Cabine noturna" (`feedback-visual-sobrio-profissional.md:13`) |
| 08 `rodovia-amanhecer` | 111-118 | Reescrever como B03 e S07 | Manter a área vazia na metade de cima. Tirar "pesquisa e investimento" (`:113`) e o amanhecer âmbar "hopeful", que é clichê. Pôr manhã nublada e recorte de celular |
| 09 `retrato-parada` | 121-132 | Reescrever como S13 e S04 | "roadside diner" é conceito americano, o copo na mão gera artefato funcional, e "tired" com boné gasto é estereótipo. Mostrar o motorista em contexto profissional: conversa na garagem ou pausa digna |
| 10 `banner-compartilhamento` | 134-142 | Descartar e refazer como B01 | Não mostra o setor. O Open Graph precisa dizer "frota" em uma olhada |
| Regras de vídeo | 146-152 | Manter e ampliar | Acrescentar modelo, quadro inicial e final, número de quadros, tetos de peso e custo |
| V1 `video-estrada-noite` | 154-159 | Descartar | Faixa tracejada correndo para a câmera é o efeito rejeitado e o clichê de vídeo de logística |
| V2 `video-piscada` | 161-168 | Descartar | A piscada foi rejeitada (`feedback-visual-sobrio-profissional.md:15`) e o close estigmatiza |
| V3 `video-amanhecer` | 170-175 | Descartar | Timelapse de nascer do sol é clichê. Substituir por V03 (garagem do dia para a noite) ou V04 (terminador sobre a malha) |
| V4 `video-disco` | 177-182 | Descartar | Conceito morto |
| Depois de gerar | 186-193 | Manter e ampliar | Acrescentar critérios de aceite por quadro, registro de custo real e legenda "Imagem ilustrativa" |

---

## Anexo B · Cenas necessárias (shot list numerada)

Códigos: **F** fundo, **S** imagem de seção, **B** banner, **V** vídeo. As seções são prováveis e devem ser
conferidas com o mapa da Frente 4: Topo · Na cabine · O gestor fica sabendo · Carga · Passageiros · Motorista e
privacidade · Instalação e piloto · O aparelho · Perguntas · Contato.

### B.1 Regras de recorte (valem para todas as fotos)

- **Master 3:2** (cerca de 3000 × 2000 px depois de ampliar). Recortes: computador 21:9 (2560 × 1097) ou 16:9
  (2560 × 1440); celular 4:5 (1080 × 1350) ou 9:16 (1080 × 1920).
- **Zona segura, pela conta:** num master 3:2, o recorte 9:16 de altura cheia ocupa 37,5% da largura, o 4:5 ocupa
  53%, e o 21:9 de largura cheia ocupa 64% da altura (corta 18% em cima e 18% embaixo). Portanto, **o assunto inteiro
  cabe numa janela de 37,5% da largura, dentro da faixa vertical de 18% a 82%**. Essa janela pode ficar no terço onde
  está o assunto, e o texto do computador vai no lado oposto.
- **Alternativa quando o texto fica sobre a foto:** gerar o núcleo em 4:5 e usar o Expand do Magnific para chegar a
  16:9 e 21:9. A área inventada fica só na periferia (céu, parede, asfalto), que é exatamente onde entra o texto.
  Conferir se o Expand não criou objeto nem letra.
- **Texto sobre a foto só onde há tom uniforme** (céu nublado, parede, asfalto escuro), com véu de legibilidade sutil
  como nos sites do Matheus (`Obsidian/90 - Projetos/Padroes/meu-estilo-de-sites.md:77`). No celular, o texto vai
  **acima ou abaixo** da imagem, não sobre ela, exceto nos 9:16 de céu escuro.

### B.2 Imagens de seção: o que se vê e para quem

| Código · arquivo | Seção | Persona | Cena | Objetivo narrativo |
|---|---|---|---|---|
| S01 · `cabine-carga` | Topo (par A) | P1, P4 | Cabine de caminhão de cabine avançada, enquadrada por trás do ombro direito do motorista (nuca e ombro desfocados na borda direita). Painel no terço de baixo, aparelho canônico nítido sobre o painel, BR de pista dupla pelo para-brisa com uma carreta distante | "É um aparelho pequeno, na cabine, para frota" em 5 s, sem mostrar rosto |
| S02 · `cabine-onibus` | Topo (par B) | P2, P3 | O mesmo enquadramento e a mesma posição do aparelho, numa cabine de ônibus rodoviário (para-brisa panorâmico, painel largo) | Passageiros têm o mesmo produto. A troca carga ↔ passageiros não pula |
| S03 · `aparelho-painel` | Na cabine | P1, P4, P5 | Aparelho nítido no terço esquerdo, com 85 a 100 mm. Motorista desfocado ao fundo, sem olhos legíveis | Mostrar o tamanho e a discrição do aparelho, sem cara de câmera de vigilância |
| S04 · `parada-descanso-noite` | Na cabine (consequência do alarme) e Motorista | P5, P1, P2 | Caminhão estacionado num ponto de parada e descanso à noite, luzes delimitadoras âmbar acesas. O motorista, pequeno no quadro, de pé ao lado da porta aberta, bebendo água | "O alarme é para você parar em segurança" (`personas.md:111`), sem mostrar ninguém dormindo |
| S05 · `gestora-revisao` | O gestor fica sabendo | P1 | Gestora de 40 a 45 anos numa sala de operações de transportadora, de dia, vista em 3/4 por trás e à esquerda. Monitor no terço direito com **tela escura uniforme** para receber a interface real por código | Revisão humana antes de qualquer conversa com o motorista |
| S06 · `cco-urbano` | O gestor fica sabendo e Passageiros | P3 | Coordenadora com headset numa mesa de CCO com 2 monitores de tela escura, janela ampla, colegas desfocados. **Sem parede de monitores de CFTV** | Triagem calma, não "sala de vigilância" |
| S07 · `carreta-br` | Carga | P1, P4 | Cavalo mecânico de cabine avançada com carreta sider de lona lisa numa BR de pista dupla com canteiro, tele de ponto elevado à beira da estrada, carreta no terço direito vindo para a esquerda | Frota pesada em operação real no Brasil |
| S08 · `rodoviario-noite` | Passageiros (fretamento) | P2 | Ônibus rodoviário branco ou grafite, sem pintura de empresa, em 3/4 de frente numa rodovia à noite, faróis acesos, luz de corredor fraca no salão | "Funciona à noite, com passageiros a bordo" (`personas.md:49`) |
| S09 · `salao-passageiros` | Passageiros e Privacidade | P2, P3 | Vista do fundo do corredor para a frente, encostos altos escondendo as cabeças, luz de corredor baixa, cabine do motorista ao fundo com a estrada iluminada pelos faróis | Proteção dos passageiros sem rosto de ninguém. A câmera olha só o motorista (`personas.md:74`) |
| S10 · `urbano-corredor` | Passageiros (urbano) | P3 | Ônibus urbano padron sem pintura de operadora, em 3/4 de frente numa faixa exclusiva, dia nublado, pedestres e ciclista desfocados em primeiro plano, fachadas sem letreiro legível | Corredor urbano com pedestres e ciclistas (`personas.md:63`) |
| S11 · `vuc-doca` | Carga (última milha) | P4 | VUC de ré numa doca de centro de distribuição de manhã, operador de colete refletivo e botina conferindo volumes, porta aberta | Frota mista: não é só carreta |
| S12 · `instalacao-garagem` | Instalação e piloto | P2, P1, P3 | Técnico com uniforme liso, inclinado pela porta do motorista de um caminhão parado na garagem, fixando o aparelho no painel. Vista de fora em 3/4 de trás, luz do dia entrando pelo portão, mãos parcialmente escondidas | Instalação na garagem, sem tirar o veículo de rodar por muito tempo (objeções em `personas.md:30`, `:52-53`) |
| S13 · `motorista-gestora` | Motorista e privacidade | P5, P1 | Motorista de carga de 55 a 60 anos e a gestora de pé diante do caminhão na garagem, olhando juntos um tablet de tela invisível, conversa tranquila, 50 mm na altura dos olhos | "Ele autoriza e vê os próprios dados", "revisão antes de qualquer conversa" (`personas.md:112-114`) |
| S14 · `checklist-onibus` | Motorista e Passageiros | P3, P5 | Motorista de ônibus urbano (mulher de 40 a 45) fazendo checklist com prancheta ao lado do ônibus, na garagem, na hora azul, uniforme liso | Profissional competente, antes do turno |
| S15 · `aparelho-tecnico` | O aparelho (especificações) | P1, P4 | Render do Blender em fundo neutro: frente, 3/4 e lateral. As medidas entram por código | Especificação honesta. Mostrar o hardware só quando for definido (`PENDENCIAS.md:211`) |

### B.3 Imagens de seção: parâmetros técnicos

| Código | Luz e hora (Anexo D.1) | Câmera | Computador | Celular | Área livre para texto | Origem | Variações |
|---|---|---|---|---|---|---|---|
| S01 | H1 dia nublado. Noite H3 por Relight | 28-35 mm entre os bancos, na altura do ombro | 21:9, texto sobre o céu do para-brisa (terço de cima à esquerda) ou em coluna ao lado | 4:5 com aparelho e painel no centro-baixo; texto acima | Céu nublado no para-brisa, cerca de 40% × 35% em cima à esquerda | IA com referência de produto (render) | Dia, noite, par S02 |
| S02 | Igual a S01 | Igual a S01 | Igual a S01 | Igual a S01 | Igual a S01 | IA com S01 como referência de imagem | Dia, noite |
| S03 | H1 e H3 | 85-100 mm, f/4 equivalente | 16:9, texto nos 2/3 da direita desfocados | 4:5 com aparelho no terço de baixo; texto acima | 2/3 da direita | Render do Blender composto ou IA com referência de produto | Dia, noite com LED infravermelho só se for 850 nm |
| S04 | H3 noite com luz do posto | 35 mm, motorista a 15-20 m | 21:9, texto à esquerda sobre céu e pátio escuros | 9:16 com caminhão e figura nos 40% de baixo; texto no alto | 45% da esquerda | IA com elenco | Hora azul |
| S05 | H1 com luz de janela e teto | 35 mm em 3/4 por trás | 16:9, texto sobre a parede clara à esquerda | 4:5 com gestora e monitor; texto acima | 40% da esquerda | IA com elenco; interface composta por código | Nenhuma |
| S06 | H1 | 35 mm, plano médio aberto | 16:9, texto sobre a janela (em cima à esquerda) | 4:5 | Janela desfocada | IA com elenco; telas compostas | Nenhuma |
| S07 | H1. Noite H3 por Relight | 200 mm de ponto elevado, carreta a mais de 80 m (placa ilegível pela distância) | 21:9, texto sobre o céu nublado nos 40% de cima | 4:5 com a carreta na metade de baixo | Céu | IA | Dia, noite com luzes delimitadoras |
| S08 | H3 | 135 mm na beira da estrada | 21:9, texto em cima à esquerda sobre o céu escuro | 9:16 com o ônibus no terço de baixo | Céu escuro | IA | Hora azul |
| S09 | H3 | 24-28 mm no eixo do corredor | 16:9, texto em coluna ao lado (o quadro é simétrico) | 4:5 com o corredor centralizado | Nenhuma: texto ao lado | IA | Nenhuma |
| S10 | H1 | 85 mm na calçada, altura dos olhos | 16:9, texto sobre o céu e as fachadas desfocadas à direita | 4:5 | Terço de cima à direita | IA | Nenhuma |
| S11 | H1 manhã | 35 mm | 16:9, texto sobre a parede da doca à direita | 4:5 | 40% da direita | IA com elenco | Nenhuma |
| S12 | H1 com luz do portão | 35 mm por fora da porta | 16:9, texto sobre o piso e a parede da garagem à esquerda | 4:5 com porta e técnico | 45% da esquerda | IA com elenco e referência de produto; trocar por foto real assim que houver | Nenhuma |
| S13 | H1 luz de garagem aberta | 50 mm, altura dos olhos | 16:9, texto à direita sobre a frente desfocada do caminhão (grade genérica) | 4:5 com as duas pessoas | 35% da direita | IA com elenco | Nenhuma |
| S14 | H2 hora azul com LEDs da garagem | 50 mm | 16:9, texto sobre o teto e o céu em cima | 4:5 | Terço de cima | IA com elenco | Dia |
| S15 | Estúdio neutro, luz suave | Ortográfica e 50 mm | 16:9 | 4:5 | Generosa | Blender | Grafite; noite com LED infravermelho |

### B.4 Fundos, banners e vídeos

| Código · arquivo | Tipo | Seção | Persona | Cena ou peça | Computador | Celular | Origem |
|---|---|---|---|---|---|---|---|
| F01 · `malha-federal` | Fundo (mapa) | Carga e Passageiros (abertura dos segmentos) | P1, P2 | Malha rodoviária federal do Brasil, linhas finas sem rótulo, versões dia e noite | 21:9 com o Brasil deslocado para a direita e texto sobre o oceano | 9:16 recortando o Centro-Sul | Dados do DNIT (SNV) em código ou Blender (Anexo C) |
| F02 · `corredor-sul` | Fundo (mapa) | Carga | P1 | Corredor SP–PR–SC–RS (`personas.md:14`), rodovias do corredor em destaque discreto | 21:9 | 9:16 (o corredor é quase norte-sul e cabe no vertical) | Dados do DNIT; conferir no SNV quais BRs formam o corredor |
| F03 · `patio-zenital` | Fundo (foto) | O aparelho, números e especificações | P3, P4 | Pátio de centro de distribuição e garagem de ônibus vistos a 90°, fileiras formando padrão gráfico | 21:9 | 9:16 (o padrão repetido recorta fácil) | IA ou drone próprio. De cima não aparecem placa, logo lateral nem rosto |
| F04 · `serra-relevo` | Fundo (mapa) | Perguntas ("sem internet guarda e envia depois", `index.html:373`) | P2, P1 | Relevo sombreado de uma serra com o traçado real da rodovia, em tons de cinza | 21:9 | 4:5 | Copernicus DEM com traçado do DNIT ou OSM. Não afirmar falta de sinal num lugar nomeado |
| F05 · `mundo-noite-agora` | Fundo (mapa) | Versão EN ou faixa de idiomas | Todos | Mapa-múndi em projeção de áreas iguais, com a sombra da noite real no momento da visita e o Brasil destacado. **Sem arcos entre continentes** | 21:9 | 4:5 recortando as Américas | Natural Earth e cálculo do terminador em código |
| B01 · `og-pt` e `og-en` | Banner | Compartilhamento (WhatsApp, LinkedIn) | P1, P2 | Recorte de S01 ou S07 com 55% à esquerda escurecidos para o título | 1200 × 630 | Não se aplica | Foto aprovada e título por `next/og` |
| B02 · `faixa-serra` | Banner (divisor) | Entre "Na cabine" e "Carga" | P1 | Serra com rodovia sinuosa, carreta pequena, dia nublado com névoa baixa (sem pôr do sol) | 32:9 ou 4:1 | Esconder, ou 4:5 central | IA (Nano Banana 2 aceita 4:1) |
| B03 · `ponte-manha` | Banner | Passageiros ou Contato | P2 | Ponte rodoviária de concreto sobre rio largo, manhã nublada, uma carreta e um ônibus pequenos atravessando. Ponte genérica, sem marco famoso | 21:9, texto sobre o céu e a água | 4:5 | IA; conferir estrutura e apoios (artefato funcional) |
| B04 · `contato-garagem` | Banner | Contato (WhatsApp) | P2, P3 | Portão de garagem aberto na hora azul, luz interna, veículos em silhueta, pessoa pequena no portão | 21:9, texto sobre a fachada escura | 9:16 com texto em cima | IA ou captação |
| V01 · `loop-cabine-farol` | Vídeo (loop) | Topo | P1, P2 | Da S01 noite: câmera travada, o farol de um veículo em sentido contrário varre o painel e some. Início igual ao fim, 8 a 10 s | 16:9 recortado para 21:9 | 9:16 gerado da versão vertical | Kling 2.5 1080p, quadro inicial = final |
| V02 · `loop-chuva-parado` | Vídeo (loop) | Passageiros | P2 | Ônibus **parado** na garagem ou no ponto de descanso, vista de dentro para o para-brisa, gotas escorrendo, limpador parado, luz do pátio | 16:9 | 9:16 | Kling 2.5; emenda com fusão de 12 quadros |
| V03 · `seq-garagem-dia-noite` | Sequência de rolagem (120 quadros) | Instalação e piloto | P2, P3 | B04 ou F03 do dia para a noite, com a mesma geometria. Só a luz muda | 1600 px de largura | 1080 px | Relight para o quadro final + Kling 2.5 + extração com ffmpeg |
| V04 · `terminador-malha` | Animação em código | Carga, Passageiros e F05 | P1, P2 | A noite real avançando sobre F05 ou F01, lenta e de baixo contraste. Com movimento reduzido fica parada às 02:00 | Canvas ou SVG | Igual | d3-geo (exemplo "Solar Terminator") |
| V05 · `turntable-aparelho` | Sequência de arrasto (120 quadros) | O aparelho | P1, P4 | O aparelho girando 360°, controlado pelo arrasto, como o turntable de lâminas do São Jorge (`plano-animacoes.md:98-101`) | 1600 px | 1080 px | Blender, sem crédito |
| V06 · `rota-desenho` | Animação em código | Carga | P1 | Um trecho do corredor Sul se desenha **uma vez** com a rolagem, com legenda "rota ilustrativa" | SVG | SVG | Código (`stroke-dashoffset`) |

### B.5 Cobertura cruzada

| | Carga pesada | Fretamento e rodoviário | Urbano | Van e VUC | Gestão e CCO | Motorista digno | Instalação e garagem | Dia | Noite |
|---|---|---|---|---|---|---|---|---|---|
| Peças | S01, S03, S07, S12, S13, F02, B02 | S02, S08, S09, V02, B03 | S06, S10, S14 | S11 | S05, S06 | S04, S13, S14 | S12, V03, B04, F03 | S01, S03, S05-S07, S10-S13, B01-B03 | S01n, S04, S07n, S08, S09, S14, V01, V02, B04 |

---

## Anexo C · Estradas e mapas (requisito novo)

### C.1 Princípios

1. **A geografia nunca é gerada por IA.** Geradores de imagem erram contorno, forma e rótulo de mapa. Em 2026, na
   conferência AIDS 2026, no Rio, um slide do Departamento de Estado dos EUA com mapa gerado por IA pôs a Nigéria sem
   litoral no meio do Saara e Moçambique no Chifre da África (Mappr). A regra da área é usar dado geográfico real e, no
   máximo, entregar ao modelo uma silhueta geometricamente correta. Fontes de dado:
   - **DNIT, Sistema Nacional de Viação:** SHP, GeoJSON e KML pelo VGEO e pelos dados abertos.
   - **Natural Earth:** domínio público, sem atribuição obrigatória.
   - **OpenStreetMap:** licença ODbL, com o crédito "© OpenStreetMap contributors" junto do mapa.
   - **Copernicus DEM GLO-30:** relevo, com aviso de fonte obrigatório.
2. **O mapa é contexto, não o produto.** O DriveSafe não tem localização (problema 5). Nada de pino de veículo, pino de
   evento, "frota ao vivo no mapa" ou rota com hora. Um traçado de rota sempre leva a legenda "rota ilustrativa".
3. **Mapa-múndi não pode sugerir operação global.** Arcos ligando continentes são imagem de frete aéreo e marítimo,
   e o produto é rodoviário e brasileiro. O uso honesto é o **tempo**: a noite real passando pelo mundo, com o Brasil
   em destaque. Isso conversa com o fato do produto de que madrugada pesa no risco (`contexto.md:32`).
4. **Só a luz se move, nunca a câmera.** Esse é o princípio do próprio Matheus: "o que é luz cresce em opacidade e
   brilho, nunca se move em x/y" (`plano-animacoes.md:25`). Serve para o terminador e para dia e noite nas fotos.

### C.2 Peças de estrada e mapa

| Pedido do coordenador | Peça | Como fazer |
|---|---|---|
| Malha rodoviária do Brasil vista de cima | F01 | GeoJSON do SNV simplificado (tolerância perto de 200 m, por exemplo no mapshaper), linhas de 0,5 a 1 px. Dia: linhas grafite sobre fundo claro. Noite: linhas âmbar a 30% sobre grafite. Sem rótulos |
| Trechos de BR de dia e à noite | S07 (dia) e S07n (Relight), S08 | Foto com tele de ponto elevado, faixa central amarela na pista simples e branca entre faixas do mesmo sentido (Anexo D.4). À noite: luzes delimitadoras âmbar, faróis e tachas refletivas. Nos trechos rurais, nada de iluminação pública inventada |
| Rotas desenhadas sobre mapa-múndi | Substituir por F05 (noite real) e V06 (rota no Brasil) | Rota no mundo não se sustenta. No Brasil, o corredor da P1 se desenha uma vez com a rolagem. Para a P2, um círculo de 900 km de raio mostra a escala da viagem noturna (`personas.md:39`): é geometria, não rastreamento |
| Entroncamentos | F03 (variante) ou render de trevo | Melhor: geometria de um trevo do OSM extrudada no Blender, vista de cima, sem rótulo e sem nome. Com IA, só trevo genérico; rejeitar alça que não liga a nada (artefato funcional) |
| Serras | F04 e B02 | Relevo sombreado do Copernicus com o traçado real (fundo) e foto de serra com névoa baixa em dia nublado (banner) |
| Pontes | B03 | Ponte de concreto genérica, sem marco reconhecível, com veículos pequenos |

### C.3 Como virar fundo de seção

- **Contraste baixo sob o texto:** linhas da malha com 12% a 18% de contraste sobre o fundo. O acento vai só no
  trecho de que a seção fala.
- **Recorte por tela:** no computador, Brasil deslocado para a direita e texto sobre o oceano. No celular, recorte
  vertical do Centro-Sul, onde BR-116 e BR-101 correm quase de norte a sul.
- **Peso:** malha simplificada em SVG, ou AVIF pré-renderizado quando for densa demais. Atribuição no rodapé.
- **Sem textura:** nada de papel antigo, tacógrafo, grade de radar ou neon.

### C.4 Como virar vídeo ou animação em loop sem clichê

- **F05 com V04:** a noite real no momento da visita, calculada e não gerada. Pode andar em tempo real, o que é
  imperceptível, ou num ciclo lento de 30 a 40 s por 24 h com baixo contraste. Com movimento reduzido, fica parada.
- **V06:** a rota desenha uma vez quando a seção entra e para. Não é loop.
- **V03:** a garagem vai do dia para a noite pela rolagem. A geometria é idêntica e só a luz muda.
- **Proibidos:** pontos luminosos correndo pelas linhas, globo 3D girando, rede de pontos conectados, rastros de
  farol em longa exposição, hyperlapse de faixa tracejada, drone sobre estrada no pôr do sol, HUD e mira sobre veículo.

---

## Anexo D · Regras da nova série fotográfica

### D.1 Luz: três horários canônicos (e nenhum outro)

| Código | Horário | Descrição | Nunca |
|---|---|---|---|
| H1 | Dia nublado claro, 10h a 15h | Luz difusa, sombras suaves, céu branco-acinzentado e uniforme (vira área de texto) | Sol no quadro, céu azul saturado, reflexo estourado |
| H2 | Hora azul | Céu azul-escuro sem sol visível, luzes práticas começando (garagem, faróis) | Pôr do sol laranja, silhueta contra o sol |
| H3 | Noite com luz prática | Só as luzes que existem na cena: painel, faróis, delimitadoras âmbar, LED branco de pátio | Neon, luz colorida sem fonte, lens flare, névoa "cinematográfica" |

- **Interior de cabine:** a luz principal é a do para-brisa. O painel é luz prática, fraca.
- **Mesma direção de luz nas cenas da mesma locação**, para que dia e noite do Relight e as sequências de vídeo batam.

### D.2 Lente e posição de câmera

| Situação | Lente (equivalente full frame) | Posição | Profundidade de campo |
|---|---|---|---|
| Veículo na estrada | 135-200 mm | Ponto elevado à beira da estrada, veículo a mais de 80 m | Moderada (f/5.6 a f/8) |
| Interior de cabine | 28-35 mm | Entre os bancos, na altura do ombro | Moderada: painel e aparelho nítidos |
| Detalhe do aparelho | 85-100 mm | 40-60 cm do aparelho | Rasa só aqui (f/4) |
| Pessoas | 50 mm | Altura dos olhos, 2-4 m | Moderada |
| Zenital | Equivalente a 24 mm de drone | 90° exatos, 40-60 m | Tudo nítido |

- **Nada de bokeh cremoso como padrão.** Kamali et al. 2025 mostram que retrato simples com fundo desfocado engana
  mais o olho. Por isso esse recurso é o que dá "cara de banco de imagem" gerado: evitar.

### D.3 Cor e acabamento

- Balanço de branco correto: cerca de 5600 K de dia e 4000 a 4500 K nas cenas noturnas com LED.
- Saturação baixa a média, pretos com detalhe, contraste moderado.
- **Sem grão adicionado, sem vinheta, sem teal-and-orange, sem HDR.** A textura vem do mundo: poeira no pneu, tecido
  gasto do banco, plástico riscado.
- **Acento âmbar só onde ele existe no mundo** (delimitadoras e painel), o que conversa com o âmbar da interface
  (`index.html:21`). Vermelho só em luz real, como lanterna e freio.
- Referência de tom: fotografia editorial de relatório anual de empresa de transporte, não filme.
- Referência documental brasileira para o princípio (não para copiar): o livro "Vida na Boleia", de Ita Kirsch e
  Bala Blauth, 21 mil km por 16 estados acompanhando o que cada região transporta (Sul21). O que aproveitar é a
  regionalidade real e o respeito pelo trabalho.

### D.4 Contexto brasileiro (checklist)

- **Caminhão de cabine avançada ("cara chata")**, com carreta sider, baú ou graneleira. O caminhão de capô longo
  americano quase sumiu da produção nacional por causa da regra de comprimento e da influência europeia (Autopapo).
- **Direção à esquerda e circulação pela direita.** Faixa **amarela** separa fluxos opostos e faixa **branca** separa
  faixas do mesmo sentido (DETRAN-PR, sinalização horizontal). Acostamento, defensa metálica e tachas refletivas.
- **Placa Mercosul presente, mas ilegível** por distância, ângulo ou desfoque.
- **Paisagem por região**, sem nomear lugar: araucária e serra no Sul, cana e laranja no interior paulista, soja
  no Centro-Oeste, terra vermelha.
- **Ônibus sem pintura de viação ou operadora:** rodoviário com para-brisa panorâmico, urbano padron com portas à
  direita.
- **Uniforme liso** (polo ou camisa cinza ou azul-marinho, sem logo). Colete refletivo e botina em pátio de centro de
  distribuição.
- **Pessoas:** 30 a 60 anos, tipos físicos variados, cabelo grisalho, pele com textura. A distribuição de cor segue o
  Censo 2022: 45,3% pardos, 43,5% brancos, 10,2% pretos, 0,8% indígenas e 0,4% amarelos (IBGE e Agência Gov).
- **Gênero sem distorcer a realidade:** 99,5% dos caminhoneiros são homens (CNT, Pesquisa Perfil dos Caminhoneiros
  2019, via Revista Carga Pesada), então a carga pesada tem motorista homem. Mulheres aparecem na gestão e no CCO, que são mulheres nas personas P1 e P3, e ao volante
  do ônibus urbano (S14).
- **Ponto de parada e descanso** existe na lei (Lei 13.103/2015, com locais reconhecidos pelo DNIT e pela ANTT): é o
  cenário honesto para a pausa (S04).

### D.5 Sinais de IA a evitar (checklist de rejeição por quadro)

Organizado pelas cinco categorias de Kamali et al. 2025 (CHI):

| Categoria | Rejeitar o quadro se aparecer |
|---|---|
| Anatômica | Dedos no volante ou na ferramenta (número, dobra, fusão); dentes; orelhas diferentes; pescoço longo |
| Estilística | Pele cerosa ou brilhante; "cinematográfico demais"; bokeh cremoso; simetria perfeita; veículo limpo demais; HDR |
| Funcional | Volante com raios incoerentes; cinto atravessando errado; retrovisor sem suporte; porta sem maçaneta; número de parafusos de roda diferente entre rodas; carreta sem quinta roda; eixo flutuando; cabo que termina no nada; alça de trevo que não liga a nada; prancheta ou tablet segurado de forma impossível |
| Física | Sombras em direções diferentes; reflexo no para-brisa ou no retrovisor que não bate; farol aceso sem luz projetada; chuva sem reflexo no asfalto; painel iluminando o que não alcança |
| Sociocultural | Caminhão americano de capô longo; faixa central branca em pista de mão dupla; placa amarela americana; volante à direita; "diner"; placa de estrada em inglês; farda policial |
| Texto | Qualquer letra ou número legível em placa, letreiro, baú, tela, uniforme ou crachá |
| Clichê | Pôr do sol; rastro de luz; poeira no ar em contraluz; chuva com neon; motorista bocejando ou dormindo; malha de pontos ou mira sobre rosto; parede de monitores |

**Como escrever as exclusões:** o guia do Veo 3.1 recomenda descrever o que se quer ("a desolate landscape with no
buildings") em vez de negar ("no man-made structures"). Exemplos para o novo arquivo:

```
license plates too small and angled to read · signage out of focus with no readable characters ·
unbranded vehicles with plain white and graphite paint · monitors showing a uniform dark screen ·
hands relaxed and partly hidden by the steering wheel rim
```

### D.6 Aparelho canônico (descrição fixa e neutra, sem marca)

**Base nos fatos:** câmera USB ou Pi Camera, infravermelha de 850 ou 940 nm recomendada (`README.md:266-273`), de
frente para o motorista (`README.md:283-284`), alarme sonoro por buzzer ou caixa USB (`README.md:277-280`), sem tela
no código. A posição segue a prática do setor: sobre o painel, a até cerca de 20° da linha reta de visão do motorista
(manual do Seeing Machines Guardian). A detecção de celular recorta a região em volta do motorista
(`vision/phone.py:4`), então a câmera precisa ver cabeça, ombros e mãos.

Bloco para colar em toda cena com cabine (em inglês):

```
[DEVICE · canonical v1 · unbranded]
a compact driver-facing camera unit about the size of a matchbox (60 x 40 x 30 mm),
matte graphite plastic housing with softly rounded edges,
a small dark glass lens in the center with two tiny near-infrared LED dots beside it that look black in daylight,
on a short matte black articulated arm fixed to the top of the dashboard,
just to the right of the steering wheel rim, within about 20 degrees of the driver's straight-ahead line,
below the driver's view of the road, lens angled up toward the driver's face;
one thin black cable runs neatly along the dashboard seam and disappears under the trim;
the processing unit is hidden behind the dashboard and never visible;
no screen, no buttons, no status light, no text, no logo
```

- **Noite, só se a câmera for de 850 nm:** "the two LED dots show a very faint dark red glow visible only up close;
  nothing else on the unit lights up". Com 940 nm não há brilho nenhum (Axton: o de 850 nm tem brilho vermelho fraco
  na fonte; o de 940 nm, nenhum).
- **Unidade de processamento, só na cena de instalação (S12)**, marcada como hipótese até o hardware ser definido
  (`PENDENCIAS.md:211`): "a matte black fanless aluminum box about the size of a paperback book with fine cooling
  fins, no markings, being fixed behind the lower dashboard panel".
- **Regras:** a mesma posição relativa em caminhão, ônibus rodoviário e urbano. Nunca no para-brisa, no retrovisor ou
  preso por ventosa. No quadro, nunca maior que um mostrador do painel.
- **Blender primeiro:** modelar uma vez (60 × 40 × 30 mm, chanfro de 3 mm, plástico grafite fosco, lente de vidro,
  dois LEDs) e renderizar frente, 3/4, lateral e noite em 2K com fundo transparente. Esses renders viram a referência
  de produto em todas as gerações, e o turntable (V05) sai do mesmo arquivo. Quando o hardware real existir, troca-se
  só a referência. No script, lembrar do erro 70 do vault (`transform_apply` com flags explícitas,
  `erros-que-a-ia-comete.md:529-535`).

### D.7 Elenco fixo (personagens gerados e reutilizados)

| Personagem | Aparece em | Descrição base |
|---|---|---|
| Motorista de carga | S04, S13 | 55 a 60 anos, pardo, corpo robusto, cabelo grisalho curto, barba por fazer, polo cinza lisa, calça jeans, botina |
| Motorista de ônibus urbano | S14 | 40 a 45 anos, preta, cabelo preso, camisa azul-marinho lisa de manga curta |
| Gestora de segurança de frota | S05, S13 | 40 a 45 anos, branca, óculos, camisa social clara, crachá virado ou sem texto |
| Técnico instalador | S12 | 30 a 35 anos, pardo, magro, macacão ou polo cinza liso, luvas finas |
| Coordenadora de CCO | S06 | 35 a 40 anos, parda, headset, camisa escura lisa |

- **Ficha de cada personagem:** frente, 3/4 e perfil em fundo cinza. Aprovar e usar como referência de personagem.
- **Conferir semelhança com pessoa real ou famosa** antes de aprovar (D.8).

### D.8 Cuidados legais e éticos (checklist de publicação)

- **Marcas:** nenhum logotipo de montadora, nenhuma grade frontal reconhecível, nenhuma pintura de transportadora ou
  viação existente, nenhuma marca de pneu ou bandeira de posto (Lei 9.279/1996).
- **Placas:** sempre ilegíveis. Nunca inventar placa legível, porque ela pode coincidir com um veículo real. O mesmo
  vale para as placas de demonstração da interface (`index.html:307-318`), assunto da Frente 5.
- **Rostos:**
  - Pessoa gerada não pode parecer pessoa real ou famosa. O uso comercial não autorizado de imagem gera indenização
    sem prova de prejuízo (Súmula 403 do STJ; Código Civil, art. 20).
  - Na captação real: autorização de uso de imagem assinada.
  - Com o sistema rodando durante a captação, é dado pessoal do motorista, e o consentimento já é registrado no
    produto (`contexto.md:34`).
- **Motorista:** nunca dormindo, babando, bocejando de forma teatral, levando bronca ou punido (`personas.md:118`).
- **Passageiros:** sem rosto identificável (S09).
- **Referências:** proibido usar foto de terceiros (Pinterest, site de montadora ou de concorrente) como imagem de
  referência. O curso de Magnific do vault faz isso (`Formação de Magnific/04 - Composição com múltiplos elementos e consistência.md:21-23`),
  mas aqui traz risco de marca e de obra alheia. Só referências próprias: Blender, fotos próprias e imagens geradas já
  aprovadas.
- **Transparência:** legenda "Imagem ilustrativa" nas cenas de uso e instalação. O guia do CONAR de 2026 reforça que
  anunciante e agência respondem pela veracidade de conteúdo feito com IA e recomenda transparência (Meio & Mensagem).
- **Mapas:** crédito do OpenStreetMap e do Copernicus quando usados. Nenhum pino de veículo ou evento.
- **Drone próprio:** cadastro no SISANT (ANAC) e autorização de voo no SARPAS (DECEA), obrigatória para todo drone a
  partir de 1º/07/2026 (DECEA e guias de 2026).

---

## Anexo E · Magnific

### E.1 Modelos encontrados nesta sessão

Consultados só com as ferramentas de listagem (lista de modelos de imagem, lista de modelos de vídeo, modos de
ampliação de imagem e modos de ampliação de vídeo), em 11/09/2026. Nada foi gerado nem simulado. Os custos vêm da
página de preços do Magnific (acessada em 11/09/2026) e de medições do São Jorge.

**Imagem: 49 modelos.** Os que importam para esta série:

| Modelo | O que o catálogo diz | Onde encaixa | Custo |
|---|---|---|---|
| Seedream 5 Pro | Modelo padrão recomendado ("sota"); referências de estilo, personagem, produto e imagem; 21:9, 16:9, 9:16, 3:4 e 3:2 (**sem 4:5**); 1,5K e 2K | Base da série: S01 a S14, exploração da âncora | 75 créditos por imagem (1,5K) |
| Google Nano Banana Pro | Recomendado para edição guiada por referência, consistência de personagem e fidelidade de produto; 4:5 e 21:9; até 4K | Cenas com o aparelho (referência de produto) e com o elenco; núcleos 4:5 | 150 créditos por imagem (4K) |
| Google Nano Banana 2 | Proporções extremas 4:1 e 8:1; até 4K | Faixa B02; rascunhos | 75 créditos (1K ou 2K), 150 (4K) |
| Google Nano Banana 2 Lite | Recomendado para rascunho barato e volume | Testar composição antes da versão final | 60 créditos |
| Seedream 5 Lite | 2K a 4K | Fundo zenital F03 em 4K barato | 50 créditos (4K) |
| Recraft V4.1 | "sota" para texto para imagem sem referência, fotorrealismo incluído | Primeira exploração da âncora sem referência | 60 créditos |
| Krea 2 | Proporção 2,35:1 | Banners panorâmicos B02 e B03 | 80 créditos |
| MAI Image 2.5 (beta) | Único com referência do tipo "locations" | Teste para manter a mesma garagem entre S12, S13 e B04 | Não publicado |
| Flux.2 Pro, Flux.2 Max, Flux.1 Realism | Fotorrealismo; o Realism não aceita referência | Alternativa; o Realism não serve para série | 50 (Pro 1K), 130 (Max 1K) |
| GPT 2 e GPT 2.5 (beta) | "sota" para texto, infográfico e interface, **não** para foto | Não usar em foto | 400 créditos (Mid 2K) |
| Cinematic (Imagen) | 21:9, 4K e controles de câmera | Evitar como padrão: "cinematográfico demais" é sinal de IA | Não publicado |
| Ideogram 4, P-Image Ideogram | Especialistas em texto | Não usar (o texto entra por código) | 44 (P-Image 2K High) |
| Outros listados | Auto, Classic, Classic Fast, Flux.1, Flux.1 Fast, Flux.1 Kontext Pro e Max, Flux.1.1, Flux.2 Flex, Flux.2 Klein, GPT 1 HQ, GPT 1.5, Grok, Grok Imagine 2.0, Ideogram, Luma Uni-1.1, Mystic 1.0 e 2.5 (Flexible, Fluid), Qwen, Qwen Image 3.0 e 3.0 Pro, Recraft V4, Recraft V4 Pro, Runway, Seedream 4, Seedream 4 4K, Seedream 4.5, Z-Image | Sem vantagem clara aqui | Luma 140; Grok 70 |

**Vídeo: 51 modelos.** Para loop é preciso **quadro final**:

| Modelo | O que o catálogo diz | Onde encaixa | Custo |
|---|---|---|---|
| Kling 2.5 | Recomendado em custo e benefício para vídeo **sem som** de 5 a 10 s; 16:9, 9:16 e 1:1; quadro inicial e final (o final **só em 1080p**) | V01, V02 e V03 (finais) | 650 créditos por take de 10 s em 1080p (medido no São Jorge, `prompts-animacoes.md:23`) |
| Kling 3.0 Omni | Fora do beta; 3 a 15 s; até 4K; inicial e final; referências de personagem, produto e vídeo. Referência de imagem não combina com quadro final | Movimento com o aparelho idêntico, sem loop | Não publicado |
| Google Veo 3.1 | Fora do beta; 4, 6 ou 8 s; 16:9 e 9:16; até 4K; inicial e final; áudio opcional | V01 em 4K, só se o topo exigir | 2.080 créditos por 4 s em 4K com áudio |
| Seedance 2.5 (beta) | Recomendado como melhor geral; **21:9 nativo**; 4 a 30 s; inicial e final; câmera "static"; sem música. Quadros inicial e final não combinam com referências | Só para um plano 21:9 nativo com câmera parada | 3.160 créditos por 4 s em 1080p (o mais caro por segundo) |
| MiniMax H3, H3 Max, H3 Max Turbo | 21:9; inicial e final; H3 em 2K; Max Turbo em 768p | **Testar o movimento barato** antes do final; H3 2K para faixas 21:9 | 200 créditos por 5 s (Max Turbo 768p) |
| Wan 2.7, Wan 3.0, Wan 3.0 Prime (beta) | Inicial e final; até 30 s; 1080p | Alternativa ao Kling | 480 créditos por 2 s (Wan 3.0 1080p); 800 (Prime) |
| Gemini Omni 1.1 (beta) | Inicial e final; até 4K | Alternativa | 720 créditos por 3 s |
| FLUX 3 (beta) | 21:9; o quadro inicial e final encarece | Evitar | 2.750 créditos por 5 s (1080p) |
| PixVerse 5.5 e 6 (beta) | Inicial e final | Caro por segundo | 200 créditos por 1 s (PixVerse 6 1080p) |
| Kling 3.0 Turbo, Sora 2 e 2 Pro, Runway Gen 4 e 4.5, Grok, Grok Imagine 1.5, Happy Horse 1 e 1.1, Wan 2.2, 2.5 e 2.6, MiniMax Hailuo 2.3 e 2.3 Fast | **Sem quadro final** | Não servem para loop | Kling 3.0 Turbo: 780 créditos por 3 s |
| Veo 3.1 Fast e Lite, Kling 2.1, 2.1 Master e 2.6, Hailuo 02, Seedance 1.5 Pro, 2.0, 2.0 Fast e 2.0 Mini, Auto | Variantes | Rascunho, se preciso | Não publicado |
| Omni Human 1.5, Veed Fabric 1.0 e Fast, Veed Sync 2.0, Runway Act Two, Kling Motion Control 2.6 e 3.0, Wan 2.2 Animate Move, MiniMax Live Illustrations, Happy Horse Edit | Avatar, dublagem, controle por vídeo e ilustração | **Não usar:** nada de motorista falando gerado por IA | Não se aplica |

**Ampliação de imagem (modos):**
- **Precision photo:** 2x, "zero creativity", a escolha dos fotógrafos. É o **final padrão**.
- **Precision sublime:** 2x a 16x, "shines at 4x". Para o topo 21:9 em 3840 px ou mais.
- **Precision denoiser:** para foto real ruidosa.
- **Precision v1 (high HDR):** evitar, porque produz halos.
- **Creative:** "hallucinate detail". **Proibido em rosto e no aparelho**, porque inventa detalhe e se afasta do
  original em rostos reais (Run the Eval).
- Custo: Precision a 90 créditos por imagem 2K.

**Ampliação de vídeo (modos):** Topaz (com interpolação de quadros), Magnific Creative e Magnific Precision, até
3840 px. Custo não publicado.

**Outras ferramentas do catálogo (não carregadas, por regra da tarefa):**
- Relight (imagem e vídeo).
- Change Camera.
- Expand.
- Variations.
- Retouch e Skin Enhancer.
- Remove Background.
- Gerador 3D: Tripo ou Trellis 2, exporta GLB (documentação do Magnific).
- Spaces e Flows.

### E.2 Usos concretos

1. **Série consistente com imagem de referência (Spaces):**
   - Montar o Space "DriveSafe · série" com três entradas fixas: a âncora de estilo aprovada (referência de estilo),
     os renders do aparelho (referência de produto) e as fichas do elenco (referência de personagem).
   - Um nó de geração por cena, duplicado com Ctrl+D, trocando só o bloco da cena. O Space avisa o total de créditos
     antes de rodar em lote (`Formação de Magnific/08 - Produzindo dezenas de peças numa rodada só.md:26-27`, `:39`).
   - Salvar como Flow para refazer quando o hardware ou o elenco mudar.
2. **Reiluminar a mesma cena (Relight):**
   - Do quadro de dia aprovado (H1) saem a hora azul (H2) e a noite (H3), com a geometria idêntica. Isso serve para a
     alternância dia e noite no site e para os quadros inicial e final de V03.
   - O Relight aceita até 3 luzes com posição, intensidade e cor, e transfere luz de uma imagem de referência.
   - Conferir a física: farol aceso precisa projetar luz, e a luz é simulada, com falhas em casos complexos
     (Run the Eval).
3. **Mudar o ângulo (Change Camera):**
   - Para veículos e locações: a mesma garagem vista de outro ponto (S12 ↔ B04) ou o mesmo pátio em zenital (F03).
   - Serve para recompor o 9:16 quando o recorte corta o assunto.
   - **Não usar em rostos:** a pessoa muda.
4. **Expandir para recortes largos (Expand):** núcleo 4:5 para 16:9 e 21:9, ou 16:9 para 21:9, criando só céu, parede
   ou asfalto na área de texto. Rejeitar se o Expand inventar objeto ou letra.
5. **Ampliar a resolução (Upscale):**
   - Final em Precision photo 2x, com nitidez de 5 a 10 e grão de 4 a 7 para preservar a textura natural, **sem
     adicionar grão**.
   - Topo 21:9 em Precision sublime 4x.
   - Nunca o modo Creative em pessoa ou aparelho.
6. **Loop curto de movimento sutil (vídeo):**
   - O mesmo quadro aprovado como inicial **e** final no Kling 2.5 em 1080p, o que emenda sem corte (guias do Kling).
   - Um evento de luz só: o farol que passa (V01) ou a chuva no para-brisa com o **veículo parado** (V02). Câmera
     travada, sem som.
   - No prompt: "no shake, no cuts, no speed changes, faithful to the starting photograph", a linguagem que já
     funcionou no São Jorge (`prompts-animacoes.md:9-21`).
   - Testar antes no MiniMax H3 Max Turbo (768p). Se sobrar um salto, fundir 12 quadros no ffmpeg.
   - A versão parada é o próprio quadro inicial.
   - **Não fazer "luz de alerta do aparelho":** o alarme é sonoro (problema 5).
7. **Sequência de rolagem de 100 a 150 quadros (V03):**
   - Quadro inicial de dia e final de noite (Relight) no Kling 2.5 de 10 s.
   - Extrair os quadros **localmente, sem crédito**, com a receita do São Jorge:
     `ffmpeg -i take.mp4 -vf "fps=12,scale=1600:-2" frame-%04d.webp` (12 fps × 10 s = 120 quadros; o São Jorge usa
     30 fps, `como-entregar-midia.md:28-30`).
   - Tetos: 45 KB por quadro, 6 MB no computador e 2,5 MB no celular (`plano-animacoes.md:174`).
   - Curar quadro a quadro.
8. **Modelo 3D do aparelho para girar:**
   - **Blender** para o aparelho de medidas definidas, com arestas e materiais controlados. Render de 120 quadros
     para arrasto (V05), sem crédito e sem 3D rodando no navegador, a mesma escolha do São Jorge
     (`site-saojorge.md:37`).
   - O gerador 3D do Magnific (Tripo ou Trellis 2, saída GLB) só serve como rascunho a partir de **fotos do protótipo
     real**, quando ele existir.
9. **Vídeo da cena de instalação:** **não gerar.** Instalação é afirmação sobre o produto e deve ser filmada de verdade
   (pergunta 3).

### E.3 O que gasta mais crédito e orçamento da série

**Ranking por custo (página de preços do Magnific e medições do São Jorge):**

| Posição | Item | Custo aproximado |
|---|---|---|
| 1 | Vídeo Seedance 2.5 1080p | cerca de 790 créditos por segundo (3.160 por 4 s) |
| 2 | Vídeo FLUX 3 1080p | 550 por segundo |
| 3 | Vídeo Veo 3.1 4K com áudio | 520 por segundo |
| 4 | Vídeo Kling 3.0 Turbo 1080p | 260 por segundo |
| 5 | Vídeo Wan 3.0 1080p e Gemini Omni 1.1 | cerca de 240 por segundo |
| 6 | Vídeo PixVerse 6 1080p | 200 por segundo |
| 7 | Vídeo Kling 2.5 1080p | cerca de 65 por segundo (650 por 10 s, medido) |
| 8 | Vídeo MiniMax H3 Max Turbo 768p | 40 por segundo |
| 9 | Imagem GPT 2 Mid 2K | 400 por imagem |
| 10 | Imagem Nano Banana Pro 4K e Nano Banana 2 4K | 150 |
| 11 | Imagem Luma Uni-1.1 e Flux.2 Max | 140 e 130 |
| 12 | Ampliação Precision | 90 por imagem 2K |
| 13 | Imagem Krea 2, Seedream 5 Pro e Nano Banana 2 2K | 80 e 75 |
| 14 | Imagem Recraft V4.1 e Nano Banana 2 Lite | 60 |
| 15 | Imagem Seedream 5 Lite 4K e Flux.2 Pro | 50 |
| Sem preço público | Relight, Change Camera, Expand, gerador 3D e ampliação de vídeo | Conferir no aplicativo antes de rodar (a simulação de custo não foi usada, por regra da tarefa) |

**Orçamento estimado da série do Anexo B:**

| Etapa | Conta | Créditos |
|---|---|---|
| Exploração da âncora | 8 imagens Seedream 5 Pro | 600 |
| Fichas do elenco | 5 personagens × 3 imagens Nano Banana Pro (preço de 4K, pior caso) | 2.250 |
| Imagens de seção | 14 cenas (S01 a S14) × 4 tentativas × 75 a 150 | 4.200 a 8.400 |
| Fundo zenital e banners | 12 imagens × 50 a 80 | 600 a 960 |
| Ampliação final | 25 imagens × 90 | 2.250 |
| Relight e Expand | cerca de 10 e 20 usos | não publicado |
| Testes de vídeo | 10 × MiniMax H3 Max Turbo 5 s | 2.000 |
| Vídeos finais | V01, V02 e V03 × 2 takes × Kling 2.5 10 s | 3.900 |
| **Total sem Veo** | | **cerca de 16 a 20 mil + Relight e Expand** |
| Opcional: V01 em 4K | 2 takes × Veo 3.1 8 s | +8.320 |

- O plano Premium dá 20.000 créditos por mês, segundo o curso do vault (`Formação de Magnific/02 - Como o Magnific Funciona.md:22`).
- O que mais pesa é vídeo, 4K e repetição de tentativas. Por isso: rascunho barato, uma âncora aprovada antes e só
  3 vídeos gerados.

---

## Anexo F · Esqueleto do novo `prompts-imagens.md`

O redator final escreve os prompts. O esqueleto define seções, campos e blocos:

````markdown
# Mídia do site DriveSafe: fundos, imagens, banners e vídeos

## 0. Como usar este arquivo
- Direção vigente: <página de produto para frotas de carga e passageiros; data da aprovação>
- Público: P1 a P5 (link para personas.md). Fora do foco: universidades e investidores
- Política de IA: <decisão do Matheus: publicada com "Imagem ilustrativa" | só prévia até captação real>
- Status de cada peça: a gerar · gerada · aprovada · no site · substituída por captação real
- Onde salvar e contrato de nomes: <tabela pasta + nome-base + onde entra, no modelo do São Jorge>
- Orçamento: <créditos previstos> · saldo · custo real acumulado
- Registro: prompt aprovado vai para Obsidian/90 - Projetos/Prompts/prompts-de-imagem.md

## 1. Bíblia visual (vale para todas as peças)
### 1.1 Horários canônicos
| Código | Horário | Bloco de luz (EN) | Nunca |
H1 dia nublado · H2 hora azul · H3 noite com luz prática
### 1.2 Lentes e posições de câmera
| Situação | Lente | Posição | Profundidade | Bloco (EN) |
### 1.3 Bloco de estilo de foto (EN)
```
[STYLE · PHOTO · v1]
<gênero: editorial documentary photograph for a Brazilian fleet-safety company, real working conditions>
<cor: neutral white balance, low-to-medium saturation, moderate contrast, detailed blacks>
<textura: true-to-life surfaces (…) — no added grain, no vignette>
<luz: {H1|H2|H3}> <lente: {da tabela 1.2}> <profundidade: moderate depth of field>
```
### 1.4 Bloco Brasil (EN)
```
[BRAZIL · v1]
<left-hand-drive, driving on the right · cab-over trucks · yellow center line on two-way roads ·
unbranded vehicles · plain uniforms · regional landscape: {…}>
```
### 1.5 Exclusões escritas como descrição (EN) e lista de rejeição por quadro
```
[CLEAN · v1]
<plates too small and angled to read · signage out of focus without readable characters ·
monitors with a uniform dark screen · hands relaxed, partly hidden>
```
Checklist de rejeição: anatômica · estilística · funcional · física · sociocultural · texto · clichê
### 1.6 Aparelho canônico
- Bloco [DEVICE · canonical vN] (EN) · variante noite (850 nm | 940 nm) · unidade de processamento (só instalação)
- Renders do Blender: arquivos, vistas, data · regras de posição e tamanho no quadro
### 1.7 Elenco fixo
| Personagem | Peças | Bloco de descrição (EN) | Ficha aprovada (arquivo) |
### 1.8 Legal e ética (checklist de publicação)
marcas · placas · rostos e semelhança · motorista · passageiros · referências próprias · "Imagem ilustrativa" ·
atribuição de mapas · drone
### 1.9 Fluxo padrão no Magnific
| Passo | Ferramenta | Modelo e configuração | Entrada | Saída | Créditos |
1 âncora · 2 geração com referências · 3 Relight · 4 Change Camera (se preciso) · 5 Expand · 6 Upscale Precision ·
7 vídeo com quadro inicial e final · 8 extração local de quadros
### 1.10 Critérios de aceite
por foto · por vídeo (sem salto na emenda, luz constante, nada "ferve" entre quadros) · por mapa (dado e atribuição)

## 2. FUNDOS (texturas e mapas atrás do texto)
### F01 · `malha-federal` · <seção>
- Tipo: fundo (mapa) · Status · Origem: dados (DNIT SNV) + código | Blender
- Objetivo narrativo:
- Persona:
- Fonte de dados, licença e atribuição:
- Tratamento: espessura de linha · contraste máximo sob o texto · simplificação · dia e noite
- Área do texto e recorte: computador (proporção, px, onde fica o texto) · celular (proporção, px)
- Não pode aparecer: rótulos · pinos de veículo ou evento · arcos entre continentes · textura de papel
- Animação (se houver): o que se move (só luz) · duração · estado parado para movimento reduzido
- Arquivo e formatos · alt text PT · alt text EN · Registro

## 3. IMAGENS DE SEÇÃO
### S01 · `cabine-carga` · Topo (par A)
- Tipo · Status · Origem (IA | Blender | captação) · Substituir por captação quando: <condição>
- Objetivo narrativo (o que a pessoa entende em 5 s):
- Persona principal e secundária:
- Seção e posição no layout:
- Composição: assunto · posição (terço) · escala · o que ocupa cada parte do quadro
- Área livre para texto: onde (% do quadro) · tom (claro | escuro) · texto sobre | ao lado | acima
- Luz e hora: H1 | H2 | H3 (+ variações)
- Lente e câmera: distância focal · altura · distância · ângulo
- Paleta: dominante · acento que existe na cena · o que não pode ter
- Não pode aparecer (específico da peça) + [CLEAN]
- Recortes: master (proporção, px) · computador 21:9 | 16:9 (px) · celular 4:5 | 9:16 (px) · zona segura
- Variações: dia · noite (Relight) · par gêmeo · outro ângulo (Change Camera)
- Referências: estilo (âncora) · produto (render do aparelho) · personagem (ficha) · imagem (peça-mãe)
- Fluxo no Magnific: | Passo | Ferramenta | Modelo | Configuração | Créditos estimados |
- Prompt (EN): [STYLE] + [BRAZIL] + [DEVICE] + <bloco da cena> + [CLEAN]
- Critérios de aceite específicos:
- Legal: placa · marca · rosto · legenda "Imagem ilustrativa" (sim | não)
- Arquivo: nome-base · pasta · formatos de saída (AVIF, WebP, 3 larguras)
- Alt text PT · alt text EN
- Registro: data · modelo · identificação do take aprovado · custo real · o que ajustar

## 4. BANNERS
### B01 · `og-pt` / `og-en` · Compartilhamento
(os mesmos campos de imagem de seção, mais:)
- Canal e tamanho (1200 × 630) · área do título renderizado por código · leitura em miniatura de WhatsApp

## 5. VÍDEOS
### V01 · `loop-cabine-farol` · Topo
- Tipo: loop | sequência de rolagem | sequência de arrasto | animação em código
- Objetivo narrativo · Persona · Seção
- Quadro inicial (peça aprovada) · quadro final (igual | Relight | outro)
- Movimento: câmera (um só, ou travada) · evento de luz · o que não pode se mexer
- Duração · fps · número de quadros (100 a 150 para rolagem) · proporção computador e celular
- Som: desligado
- Emenda: início = fim | fusão de N quadros
- Versão parada para movimento reduzido: arquivo
- Tetos: KB por quadro · MB por sequência (computador e celular) · poster
- Fluxo no Magnific: teste (MiniMax H3 Max Turbo) · final (Kling 2.5 1080p | Veo 3.1) · ampliação de vídeo
  (se preciso) · extração local (comando ffmpeg)
- Prompt (EN): <movimento> + "faithful to the starting photograph, no shake, no cuts, no speed changes"
- Rejeitar o take se: <luz muda, textura ferve, aparelho muda de forma, aparece texto>
- Arquivo e pasta · Registro (take aprovado, custo real)

## 6. Entrega e pós-produção
formatos · larguras · posters · contraste do texto medido · créditos de dados no rodapé · legenda ilustrativa

## 7. O que foi descartado e por quê
(tabela curta do Anexo A, para ninguém ressuscitar o tacógrafo)
````

---

## Fontes

**Repositório e vault (evidência interna)**
- `site-drivesafe/prompts-imagens.md`, `site-drivesafe/previa/v2/index.html` e prints, `site-drivesafe/avaliacao/contexto.md`, `site-drivesafe/avaliacao/personas.md`
- `README.md`, `PENDENCIAS.md`, `vision/alarm.py`, `vision/phone.py`, `vision/context.py`, `backend/main.py`
- `Obsidian/DriveSafe AI - Monitoramento de Motoristas/00 - DriveSafe AI.md`
- Memória do projeto: `feedback-visual-sobrio-profissional.md`
- `Obsidian/90 - Projetos/site-saojorge.md`
- `SITES E PROJETOS/saojorge/docs/plano-animacoes.md`, `prompts-animacoes.md`, `brief-higgsfield.md`, `como-entregar-midia.md`
- `Obsidian/90 - Projetos/Padroes/erros-que-a-ia-comete.md`, `meu-estilo-de-sites.md`, `regras-de-componentes.md`, `diferenciacao-visual.md`
- `Obsidian/09 - Cursos/Viver de IA/Formação/04 - Formação de Magnific/02 - Como o Magnific Funciona.md`, `04 - Composição com múltiplos elementos e consistência.md`, `08 - Produzindo dezenas de peças numa rodada só.md`
- Catálogo do Magnific consultado nesta sessão: lista de modelos de imagem, lista de modelos de vídeo, modos de ampliação de imagem e de vídeo

**Web**
- [Kamali et al. 2025, *Characterizing Photorealism and Artifacts in Diffusion Model-Generated Images* (CHI)](https://arxiv.org/html/2502.11989)
- [Google Cloud, *Ultimate prompting guide for Veo 3.1*](https://cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-veo-3-1)
- [Kling AI, guia de quadro inicial e final](https://kling.ai/quickstart/ai-video-start-end-frames) · [Cybercorsairs, loops no Kling](https://cybercorsairs.com/kling-ai-trick-for-longer-videos-seamless-loops/)
- [Magnific, preços e créditos](https://www.magnific.com/pricing) · [Magnific Docs, Relight](https://www.magnific.com/ai/docs/relight) · [Magnific, Change Camera](https://www.magnific.com/ai/change-camera) · [Magnific Docs, 3D Generator](https://www.magnific.com/ai/docs/3d-generator) · [Magnific Blog, Flows](https://www.magnific.com/blog/introducing-flows/) · [Magnific Docs, Spaces](https://www.magnific.com/ai/docs/spaces-overview)
- [Run the Eval, *Magnific AI Review 2026*](https://runtheeval.com/magnific-ai-2026-review-upscale-relight/)
- [ManualsLib, Seeing Machines Guardian Gen 2, manual de campo](https://www.manualslib.com/manual/1504727/Seeing-Machines-Guardian-Gen-2.html)
- [Axton, 850 nm vs 940 nm](https://axtontech.com/850nm-vs-940nm-light-what-is-the-difference/)
- [Autopapo, diferenças entre caminhões americanos e brasileiros](https://autopapo.com.br/noticia/diferencas-caminhoes-americanos-brasileiros/)
- [DETRAN-PR, sinalização horizontal](https://www.detraneduca.pr.gov.br/sites/educacao-transito/arquivos_restritos/files/documento/2020-08/sinalizacao_horizontal.pdf)
- [Agência Gov, Censo 2022: cor ou raça](https://agenciagov.ebc.com.br/noticias/202312/censo-2022-mostra-que-45-da-populacao-brasileira-e-pardos-e-43-5-branca)
- [Revista Carga Pesada, perfil dos caminhoneiros (CNT 2019)](https://cargapesada.com.br/conheca-o-perfil-dos-caminhoneiros-do-brasil/)
- [DNIT, Pontos de Parada e Descanso](https://www.gov.br/dnit/pt-br/rodovias/pontos-de-parada-e-descanso)
- [Sul21, *Vida na Boleia*](https://sul21.com.br/postsrascunho/2015/06/vida-na-boleia-livro-fotografico-retrata-realidade-de-caminhoneiros-no-brasil)
- [Brazil Visible, DNIT malha rodoviária (SNV, formatos e acesso)](https://brazilvisible.org/docs/apis/infraestrutura-transportes/dnit-malha-rodoviaria/) · [Ministério dos Transportes, mapas](https://www.gov.br/transportes/pt-br/assuntos/dados-de-transportes/bit/bit-mapas)
- [Natural Earth, termos de uso](https://www.naturalearthdata.com/about/terms-of-use/) · [OSMF, orientações de atribuição](https://osmfoundation.org/wiki/Licence/Attribution_Guidelines) · [Licença do Copernicus DEM GLO-30](https://docs.sentinel-hub.com/api/latest/static/files/data/dem/resources/license/License-COPDEM-30.pdf)
- [Mappr, mapa de IA da África com erros](https://www.mappr.co/ai-generated-africa-map/) · [ResearchGate, exemplos de mapas gerados por IA](https://www.researchgate.net/figure/Example-AI-generated-maps-1-inaccuracies-2-misleading-information-3_fig1_370213379)
- [Observable, D3 Solar Terminator](https://observablehq.com/@d3/solar-terminator)
- [STJ, Súmula 403](https://www.stj.jus.br/docs_internet/revista/eletronica/stj-revista-sumulas-2014_38_capSumula403.pdf) · [Código Civil, art. 20](https://www.planalto.gov.br/ccivil_03/leis/2002/l10406compilada.htm) · [Lei 9.279/1996](https://www.planalto.gov.br/ccivil_03/leis/l9279.htm)
- [Meio & Mensagem, guia do CONAR 2026](https://www.meioemensagem.com.br/midia/conar-atualiza-guia-para-influenciadores-digitais)
- [DECEA, drones](https://www.decea.mil.br/drone/) · [Guia de regras para drones em 2026](https://irlenmenezes.com.br/regras-para-drones-2026-guia-completo/)
