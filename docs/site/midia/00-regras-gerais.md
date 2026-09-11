# Regras gerais da mídia do site RotaGuard

> Valem para todas as peças de `01-fundos.md`, `02-fotos.md`, `03-banners.md` e `04-videos.md`. O índice, a tabela de
> peças, o orçamento e a ordem de geração estão no `README.md`. Escrito em 11/09/2026. Nada aqui manda gerar: gastar
> crédito do Magnific é decisão do Matheus (erro 46, `Obsidian/90 - Projetos/Padroes/erros-que-a-ia-comete.md:274-278`).

**Índice:** 1 Direção e fatos do produto · 2 Luz · 3 Lentes · 4 Blocos fixos · 5 Caixa canônica · 6 Elenco fixo ·
7 Recursos futuros · 8 Legal e ética · 9 Fluxo padrão no Magnific · 10 Ideias de Magnific que valem a pena ·
11 O que não fazer · 12 Critérios de aceite · 13 Entrega e pós-produção · 14 O que foi descartado e por quê · Fontes

---

## 1. Direção e fatos do produto

### 1.1 Para que serve a mídia

- **Site:** Next.js + Tailwind, direção C "Escalas" (`docs/site/avaliacoes/2026-09-11-previa-v2/02-direcao-de-arte.md:434-536`).
- **Três atos:**
  - **Ato I · A malha:** mapa-múndi com a faixa real da noite → malha rodoviária federal → rodovia à noite com carreta e ônibus.
  - **Ato II · A cabine:** escolha caminhão ou ônibus → cabine → a caixa instalada → o alarme (sonoro, mostrado pela
    consequência) → escala 1:1 com a ideia "a viagem não é filmada inteira; só trechos curtos quando um sinal se repete".
  - **Ato III · A frota:** a chegada e o recolhimento da caixa → a caixa conectada ao computador e o relatório da viagem →
    a gestora revisa o relatório → para quem dirige → piloto e instalação → ficha técnica → contato.
- **Ônibus:** o foco é o **rodoviário interestadual**, de empresas que viajam entre estados (decisão do Matheus,
  11/09/2026). Ônibus urbano, corredor, CCO urbano e motorista de ônibus urbano ficaram fora do foco (`02-fotos.md`,
  "Rebaixadas").
- **Onde a mídia entra no código:** o site está em `site/`. Cada foto é chamada pelo código da cena
  (`site/src/components/photo.tsx`) e lida de um manifesto (`site/src/data/fotos-provisorias.json`, pelo
  `site/src/lib/fotos.ts`). A troca da foto provisória pela peça nova é feita no manifesto, com o mesmo código.
- **Postura:** diretor de fotografia de relatório anual de transportadora brasileira, não gerador de banco de imagens. A
  mídia vem antes do layout, e cada peça já nasce com lugar, recorte e área de texto.
- **Método do Matheus:** shot list numerada, sequências de 100 a 150 quadros para rolagem, imagem para vídeo com curadoria
  e objeto 3D no Blender (`Obsidian/90 - Projetos/site-saojorge.md:37`, `:58`, `:60-61`).

### 1.2 Fatos que toda imagem precisa respeitar

| Fato | Consequência na imagem | Fonte |
|---|---|---|
| O nome é **RotaGuard** (antes DriveSafe AI) | O nome e qualquer marca nunca aparecem dentro da imagem. Entram por código, nos idiomas do site (pt-BR, en, es, fr e zh-CN, `docs/specs/008-site.md:20`) | Decisão do Matheus, 11/09/2026 |
| Hardware: **caixa com Raspberry Pi e câmera acoplada**. A placa provável é o Pi 4 de 4 GB (85 × 56 mm), ainda hipótese. O Pi 4 funciona como dispositivo pela USB-C, então a caixa ligada por cabo pode ser reconhecida, e tem codificador H.264 para os trechos | Uma única caixa canônica (seção 5), modelada no Blender antes de qualquer cena | Decisão do Matheus, 11/09/2026; `docs/site/contexto.md:53`; `docs/produto/PRD.md:129-133`; `README.md:259-291` |
| O alarme é **sonoro** (buzzer ou alto-falante) | Nada acende na caixa. O alarme aparece pela consequência (parar e descansar) e pelo som real (A01) | `caixa/vision/alarm.py:1`; `README.md:284-287` |
| A caixa **grava trechos curtos só quando um sinal se repete** (sonolência frequente por muito tempo; sinais compatíveis com uso de estimulante). No resto do tempo, não grava | Nenhuma peça diz ou sugere "não grava". Nenhuma tela mostra rosto de motorista. A escala 1:1 vira "a viagem não é filmada inteira" (V11) | Decisão do Matheus, 11/09/2026 |
| O mais importante é o **registro da viagem**. Na chegada, a empresa recolhe a caixa, conecta no computador ou na rede do escritório, e o sistema gera o relatório. O acompanhamento ao vivo deixa de ser o centro e o envio ao vivo fica opcional | O Ato III mostra recolhimento (S17), caixa conectada (S18) e revisão do relatório (S05). Nenhuma sala de controle acompanhando a frota ao vivo | Decisão do Matheus, 11/09/2026; `docs/produto/PRD.md:39-40`, `:83`, `:85` |
| **Sem GPS** no produto | Nenhum pino de veículo ou evento. Toda rota leva a legenda "Viagem de demonstração" | `02-direcao-de-arte.md:182-186`; `04-estrutura-e-conversao.md:273` |
| "Sinais compatíveis com ativação atípica" **não são diagnóstico nem exame de drogas** | Proibido sugerir exame toxicológico, polícia, punição ou motorista "dopado" (seção 8.2) | `caixa/vision/activation.py:1`; `docs/site/contexto.md:33` |
| É **protótipo**, sem frota em piloto | Nenhuma cena apresentada como "cliente real". Legenda "Imagem ilustrativa" nas cenas de uso | `docs/site/contexto.md:37-38` |
| Câmera **infravermelha** recomendada, de 850 ou 940 nm | Os emissores ficam escondidos atrás do vidro escuro. Brilho vermelho fraco só se a câmera for de 850 nm | `README.md:278-280` |
| **Pulseira** de frequência cardíaca e **leitura de pupila no celular** do motorista ficam "para muito depois" | Só no bloco "Futuro, não gerar agora" (S90 e S91), fora do orçamento | `PENDENCIAS.md:164`; decisão do Matheus, 11/09/2026 |

> [!note] Hipótese, confirmar
> A gravação de trechos curtos é decisão de produto de 11/09/2026 e ainda não está no código: hoje nenhuma imagem é
> gravada (`docs/site/contexto.md:48`, `:52`). O PRD propõe trechos de no máximo 20 s (10 s antes e 10 s depois), até 12
> por viagem, e ainda pede confirmação do Matheus (`docs/produto/PRD.md:54`, `:161`). Como o relatório mostra os trechos
> também está em aberto. Por isso toda tela nas fotos sai escura e uniforme, para receber a interface real por código
> quando ela existir.

### 1.3 Paleta do site e das fotos

> [!note] Hipótese, confirmar
> **Decisão pendente do Matheus:** site claro, com neutros de concreto e asfalto, a noite e o escuro só dentro das fotos e
> nenhum âmbar de marca (`02-direcao-de-arte.md:472-478`). As zonas de texto abaixo já assumem isso.

- **Seções claras (a maioria):** a foto fica ao lado do texto, em grade editorial 7/5. A zona de texto sobre a foto só
  vale quando a foto sangrar.
- **Seções fotográficas escuras** (Ato I rodovia, Ato II cabine e alarme, contato): texto claro sobre zona escura e
  uniforme (céu noturno, fachada, pátio escuro), com véu de legibilidade sutil, como nos sites do Matheus
  (`Obsidian/90 - Projetos/Padroes/meu-estilo-de-sites.md:77`).
- **Fotos de dia que sangram** (serra, rodovia de dia): texto escuro sobre céu nublado claro.
- **Cor dentro das fotos:**
  - noites neutras e frias (LED branco de 4000 a 4500 K);
  - âmbar só em pontos de luz que existem (lanternas delimitadoras) e nunca dominante, para não repetir o "escuro com âmbar"
    do app recusado (`.claude/.../memory/feedback-visual-sobrio-profissional.md:11-15`);
  - vermelho só em luz real (lanterna, freio).

### 1.4 Esquerda e direita

- **Composição:** "esquerda do quadro" e "direita do quadro".
- **Objetos no veículo:** o lado do veículo visto por quem está sentado ao volante. O motorista senta à esquerda e a caixa
  fica à direita do volante.
- **Nos prompts em inglês:** "left of the frame" para composição, "to the right of the steering wheel" para posição física.
  Nunca misturar os dois referenciais (erro 72, `erros-que-a-ia-comete.md:547-553`).

---

## 2. Luz: três horários e nenhum outro

| Código | Horário | Bloco de luz (EN), colar como está | Nunca |
|---|---|---|---|
| **H1** | Dia nublado claro | `Light: overcast late morning, soft diffuse daylight from a uniformly bright white-grey sky, the sun fully hidden behind an even cloud layer, gentle soft-edged shadows, daylight white balance around 5600 K.` | Sol no quadro, céu azul saturado, reflexo estourado |
| **H2** | Hora azul | `Light: blue hour with the sun well below the horizon, an even deep slate-blue sky from top to horizon, practical lights just switched on and balanced with the remaining skylight, neutral white balance.` | Faixa laranja no horizonte, silhueta contra o sol, pôr do sol |
| **H3** | Noite com luz prática | `Light: night lit only by sources that exist in the scene, such as cool white LED lamps around 4000 K, vehicle headlights, small amber marker lamps and dim instrument backlight; every source casts matching light and reflections on nearby surfaces; deep shadows that still hold detail; clean, clear air.` | Neon, luz colorida sem fonte, lens flare, névoa "de cinema", rastro de luz |

- **Uma direção de luz por locação.** O Relight e as sequências só batem se dia e noite da mesma cena tiverem a luz
  principal no mesmo lado.
- **Interior de cabine:** a luz principal vem do para-brisa, e o painel é luz prática fraca.
- **Farol aceso projeta luz.** Farol aceso sem mancha de luz no asfalto é erro físico e reprova o quadro.
- **Cena noturna nasce de dia sempre que possível.** Gera-se H1 e deriva-se H2 e H3 pelo Relight, com a geometria
  idêntica. Se o Relight falhar, gera-se a noite nativa com a imagem de dia como referência de composição.

---

## 3. Lentes e posições de câmera

| Situação | Lente (equivalente full frame) | Posição | Profundidade | Linha de câmera (EN) |
|---|---|---|---|---|
| Veículo na estrada | 135 a 200 mm | Ponto elevado à beira da estrada, veículo a mais de 80 m | f/5.6 a f/8 | `Photographed from an elevated roadside position with a 200mm telephoto lens at f/8, the vehicle more than 80 meters away, compressed perspective.` |
| Interior de cabine | 28 a 35 mm | Entre os bancos, na altura do ombro | f/5.6: painel e caixa nítidos | `Photographed from between the two front seats at shoulder height with a 32mm lens at f/5.6.` |
| Detalhe da caixa | 85 a 100 mm | 40 a 60 cm da caixa | f/4, a única peça com fundo bem desfocado | `Photographed with a 90mm lens at f/4 from about 50 cm.` |
| Pessoas | 50 mm | Altura dos olhos, 2 a 4 m | f/5.6 | `Photographed with a 50mm lens at f/5.6 at eye level from about 3 meters.` |
| Escritório e garagem com pessoa e objeto | 35 mm | 2,5 a 6 m, altura dos olhos | f/5.6 | `Photographed with a 35mm lens at f/5.6 at eye level.` |
| Zenital | Drone, equivalente a 24 mm | 90° exatos, 40 a 60 m | Tudo nítido | `Straight top-down aerial photograph at exactly 90 degrees from about 50 meters, 24mm equivalent lens, everything in focus.` |

- **Sem bokeh cremoso como padrão.** Retrato com fundo muito desfocado é o que mais engana o olho e dá "cara de banco de
  imagem" gerado (Kamali et al., 2025, citado em `03-imagens-e-prompts.md:316-317`).
- **Palavras que não entram em prompt nenhum:** cinematic, film, 35mm film, grain, moody, dramatic, epic, bokeh,
  hyperrealistic, 8k, golden hour, sunset, light trails, volumetric, haze, lens flare.

---

## 4. Blocos fixos de texto (EN)

Cada peça repete, dentro do próprio prompt, só os blocos que usa. **Se um bloco mudar de versão, trocar em todas as peças**:
buscar pelo nome do bloco (por exemplo, `DEVICE DASH v1`) nos quatro arquivos.

### 4.1 Ordem de montagem e limite de tamanho

1. Bloco da cena, escrito por extenso (o que se vê, onde está no quadro, câmera).
2. Blocos de personagem e da caixa, quando aparecem (`CAST`, `WARDROBE`, `DEVICE`).
3. Luz (`H1`, `H2` ou `H3`).
4. `STYLE`.
5. Contexto brasileiro (`BRAZIL VEHICLES`, `BRAZIL HIGHWAY`, `BRAZIL PEOPLE`).
6. `CLEAN`.

- **Por quê:** a cena vem primeiro porque os modelos pesam mais o começo do texto.
- **Tamanho:** o prompt montado fica entre 2.000 e 3.800 caracteres. O limite de cada modelo não foi conferido nesta
  sessão.
- **Se o app avisar limite ou cortar o texto:**
  - encurtar primeiro o `BRAZIL` (deixar só o que aparece na cena) e depois o `STYLE`;
  - nunca cortar a cena, o `DEVICE` ou o `CAST`.
- **Nos prompts de vídeo:** não repetir os blocos. A imagem inicial já carrega a cena, e o prompt descreve só o movimento.
- **Rótulos:** o nome do bloco (por exemplo, `STYLE v1`) fica fora do texto copiável. Nas peças, a linha "Blocos" acima de
  cada prompt diz quais entraram e em que versão. Assim nenhum rótulo entre colchetes vai parar dentro da imagem.
- **Luz:** os três blocos de luz da seção 2 se chamam `H1 v1`, `H2 v1` e `H3 v1`.

### 4.2 `STYLE v1`

```
Editorial documentary photograph for the annual report of a Brazilian transport company, showing real working conditions in an honest, unglamorous and restrained way. Neutral colors with low-to-medium saturation, moderate contrast and shadows that keep visible detail. Texture comes from the real world: worn seat fabric, scratched plastic, road grime, concrete stains, creased work clothes. Clean modern digital capture with a natural finish, even sharpness and a plain, ungraded look.
```

### 4.3 Blocos Brasil

**`BRAZIL VEHICLES v1`**

```
Brazilian vehicles: left-hand drive with traffic on the right; European-style cab-over trucks with flat fronts; buses and coaches without company livery; all vehicles in plain white, silver or graphite paint; Mercosur license plates present but too small and angled to read.
```

**`BRAZIL HIGHWAY v1`**

```
Brazilian highway: two lanes with a yellow center line between opposing directions and white edge lines, paved shoulders, metal guardrails and reflective road studs on the center line.
```

**`BRAZIL PEOPLE v1`**

```
Brazilian working adults with real skin texture, pores and fine lines, varied body types, plain work clothes in grey, navy or white without logos or readable badges, natural unposed expressions, attention on their task and away from the photographer.
```

- **Paisagem por região,** sem nomear lugar: araucária e serra no Sul, cana e laranja no interior paulista, soja no
  Centro-Oeste, eucalipto e barranco de terra vermelha (`03-imagens-e-prompts.md:339-340`).
- **Gênero sem distorcer a realidade:** 99,5% dos caminhoneiros são homens (CNT 2019, citado em
  `03-imagens-e-prompts.md:347-349`). Carga pesada tem motorista homem. No ônibus rodoviário interestadual, o elenco
  também usa motoristas homens: não há dado nesta pesquisa sobre a presença de mulheres no volante do rodoviário, e o
  Matheus pediu para não distorcer o setor. Mulheres aparecem na gestão (gestora) e no despacho da garagem.

> [!note] Hipótese, confirmar
> Se o Matheus quiser uma mulher ao volante do rodoviário, antes conferir a participação feminina no setor numa fonte
> (por exemplo, pesquisa da CNT ou dado da ANTT) e mostrar isso numa peça só, como parte de uma dupla de revezamento.
- **Cor da pele no elenco:** segue o Censo 2022 (45,3% pardos, 43,5% brancos, 10,2% pretos), citado em
  `03-imagens-e-prompts.md:345-346`.

### 4.4 `CLEAN v1` (exclusões escritas como descrição)

```
Every sign, screen, label and license plate is free of legible characters: signage is distant and out of focus, plates are too small and angled to read, monitors, laptops and tablets show a uniform dark screen, uniforms and vehicles are plain and unmarked. Hands are relaxed and partly hidden. Every mechanical part is complete and connected, and all shadows and reflections agree with one consistent light direction.
```

- **Por que descrever em vez de negar:** o guia do Veo 3.1 recomenda descrever o que se quer em vez de negar, e a lista de
  modelos do Magnific não mostra campo de prompt negativo (`03-imagens-e-prompts.md:132`, `:367-368`).
- **Prompts de vídeo:** mantêm as proibições curtas que já funcionaram no São Jorge ("no shake, no cuts, no speed
  changes", `SITES E PROJETOS/saojorge/docs/prompts-animacoes.md:20-21`).

### 4.5 Checklist de rejeição por quadro

Organizado pelas categorias de Kamali et al. (2025), como em `03-imagens-e-prompts.md:355-365`:

| Categoria | Rejeitar o quadro se aparecer |
|---|---|
| Anatômica | Dedos em número errado, dobrados ou fundidos; dentes; orelhas diferentes; pescoço longo |
| Estilística | Pele cerosa ou brilhante; "cinematográfico demais"; bokeh cremoso; simetria perfeita; veículo limpo demais; HDR |
| Funcional | Volante com raios incoerentes; cinto atravessado errado; retrovisor sem suporte; porta sem maçaneta; parafusos de roda diferentes entre rodas; carreta sem quinta roda; eixo flutuando; cabo que termina no nada; tablet ou prancheta seguros de forma impossível |
| Física | Sombras em direções diferentes; reflexo que não bate; farol aceso sem luz projetada; painel iluminando o que não alcança |
| Sociocultural | Caminhão americano de capô longo; faixa central branca em pista de mão dupla; placa americana; volante à direita; placa de estrada em inglês; farda policial |
| Texto | Qualquer letra ou número legível em placa, letreiro, baú, tela, uniforme, crachá, teto de ônibus ou letreiro de destino |
| Produto | Caixa com forma, proporção, aletas, janela ou suporte diferentes do render aprovado; caixa com luz, tela ou botão; caixa maior que um mostrador do painel em plano aberto; caixa no para-brisa ou presa por ventosa |
| Clichê | Pôr do sol; rastro de luz; poeira em contraluz; chuva com neon; motorista bocejando ou dormindo; malha de pontos ou mira sobre rosto; parede de monitores |

---

## 5. Caixa canônica (hipótese até existir protótipo)

### 5.1 O que se sabe e o que não se sabe

| Item | Situação | Fonte |
|---|---|---|
| Placa | **Hipótese:** Raspberry Pi 4 de 4 GB (antes se falava do Pi 3; em 11/09 o Matheus disse "eu não sei"). Placa de 85 × 56 mm, com furos de fixação a 58 × 49 mm e canto de 3 mm no desenho oficial do Pi 3 B+ | Decisão do Matheus, 11/09/2026; [desenho mecânico do Pi 3 B+](https://datasheets.raspberrypi.com/rpi3/raspberry-pi-3-b-plus-mechanical-drawing.pdf) |
| Portas altas da placa | No Pi 3 B+, as USB têm 16 mm de altura e a rede, 13,5 mm. Isso define a altura interna mínima | Desenho mecânico do Pi 3 B+ |
| Temperatura | O Pi 4 é especificado para "0 a 50 °C ambiente". Cabine parada ao sol pode passar disso, então a caixa precisa dissipar calor (aletas ou ventilação discreta) | [Especificações do Pi 4](https://www.raspberrypi.com/products/raspberry-pi-4-model-b/specifications/) |
| Alimentação | O Pi 4 pede 5 V por USB-C, mínimo de 3 A. No veículo, precisa de conversor de 12 ou 24 V, que fica fora da imagem | Especificações do Pi 4 |
| Som | O Pi 4 tem saída de áudio de 4 polos. O alarme pode ser buzzer ou alto-falante: não decidido | Especificações do Pi 4; `README.md:284-287` |
| Câmera | Módulo de cerca de 25 × 24 × 11,5 mm (Camera Module 3). A versão NoIR não tem filtro infravermelho e é usada com iluminação infravermelha. Qual módulo e qual iluminador: não decidido | [Documentação das câmeras](https://www.raspberrypi.com/documentation/accessories/camera.html) |
| Posição na cabine | Sobre o painel, à direita do volante, a até cerca de 20° da linha reta de visão, abaixo da visão da estrada, câmera de frente para o rosto | Manual do Seeing Machines Guardian, citado em `03-imagens-e-prompts.md:380-381`; `README.md:290-291` |
| Sai do veículo | **Sim:** a empresa recolhe a caixa na chegada. Como encaixa e trava no suporte: não decidido | Decisão do Matheus, 11/09/2026 |
| Ligação no escritório | Cabo no computador ou rede do escritório. Tipo de cabo e conector: não decidido | Decisão do Matheus, 11/09/2026 |
| Medidas externas | Não decididas. Estimativa: 105 a 115 × 70 a 75 × 36 a 42 mm, contando placa, paredes de 2,5 mm, folga, portas, câmera e aletas | Conta própria sobre as medidas acima |

> [!note] Hipótese, confirmar
> Medidas externas, forma, câmera no corpo ou num braço curto, aletas ou ventilação, suporte removível, tipo de cabo,
> iluminador de 850 ou 940 nm e a própria placa. **Modelar no Blender primeiro**, aprovar o render com o Matheus e só então
> gerar qualquer cena com a caixa.

### 5.2 Blender primeiro (S15)

- **Tamanho real, peça por peça.** Modelar a placa (85 × 56 mm, com as portas altas), o módulo de câmera, os dois emissores
  infravermelhos, o buzzer ou alto-falante e o conector. A caixa é desenhada em volta dessas peças, não o contrário. É o
  erro 71: caixinha genérica esconde conflito de montagem (`erros-que-a-ia-comete.md:538-545`).
- **Duas formas para comparar, na mesma cabine simplificada em escala 1:1:**
  - **A (padrão dos prompts v1):** câmera atrás de uma janela de vidro escuro na face voltada para o motorista.
  - **B:** câmera num braço curto sobre a caixa.
- **Duas soluções de calor:**
  - **A1 (padrão dos prompts v1):** corpo de alumínio com aletas finas no dorso.
  - **A2:** corpo de plástico com fendas discretas nas laterais.
- **Suporte:** berço baixo parafusado no painel, de onde a caixa sai sem ferramenta. O cabo de energia fica preso ao berço.
- **Teste de visão:**
  - pôr um ponto no olho do motorista sentado (altura típica de cabine avançada) e traçar a linha até a borda de baixo do
    para-brisa;
  - o topo da caixa precisa ficar abaixo dessa linha;
  - se não ficar, a forma B ou uma caixa mais baixa vencem.
- **Materiais de partida:** alumínio anodizado grafite fosco (rugosidade 0,5 a 0,6), vidro escuro com IOR 1,5 e suporte de
  metal preto fosco (rugosidade 0,45). Sem logotipo nem gravação.
- **Renders (2K, PNG com fundo transparente, nome `S15-caixa-render-<vista>-v1.png`):**
  - frente, 3/4 esquerda, lateral, traseira com o cabo e topo com as aletas;
  - fora do berço, sobre mesa;
  - no berço, sobre um painel simplificado;
  - **da mesma posição de câmera de S01 (32 mm, entre os bancos) e de S03 (90 mm, a 50 cm)**, com luz de dia e de noite.
  Esses dois ângulos alimentam a referência de produto e as composições.
- **Script:**
  - `transform_apply` com as flags explícitas (`location=False, rotation=False, scale=True`);
  - cortador ou união penetrando pelo menos 1 mm;
  - conferir `is_manifold`;
  - render longo por `blender -b arquivo.blend -a`, nunca pelo MCP (erro 70, `erros-que-a-ia-comete.md:529-536`).
- **Quando o protótipo existir:** fotografar a caixa real, trocar os renders e rodar de novo o Flow de pós-produção
  (seção 10, ideia 12).

### 5.3 Blocos da caixa (EN)

**`DEVICE DASH v1`** (a caixa no berço, dentro do veículo)

```
The driver-facing camera box: a compact unbranded box about 110 x 72 x 40 mm, slightly larger than a deck of playing cards, with a dark graphite anodized aluminum body whose top is shaped into fine parallel cooling fins and softly rounded 3 mm edges. The face pointing at the driver is a flat dark glass window with one small round camera lens; the infrared emitters sit hidden behind the same glass and look black. The box rests in a slim matte black cradle fixed to the top of the dashboard, just to the right of the steering wheel rim, within about 20 degrees of the driver's straight-ahead line and below the driver's view of the road, tilted up toward the driver's face. One thin black cable runs from the cradle along the dashboard seam and disappears under the trim. All its surfaces are plain, with no screen, buttons, indicator light, printing or logo, and nothing on it lights up.
```

**`DEVICE HAND v1`** (a caixa fora do veículo: balcão, mesa, mão)

```
The camera box out of its vehicle cradle: a compact unbranded box about 110 x 72 x 40 mm, slightly larger than a deck of playing cards, with a dark graphite anodized aluminum body whose top is shaped into fine parallel cooling fins and softly rounded 3 mm edges; one face is a flat dark glass window with one small round camera lens, and the back has a small recessed connector. All its surfaces are plain, with no screen, buttons, indicator light, printing or logo, and nothing on it lights up.
```

**`DEVICE NIGHT 940 v1`**

```
At night the box stays completely dark and is visible only where light from the scene touches it.
```

**`DEVICE NIGHT 850 v1`**

```
At night two very faint dark-red dots glow behind the dark glass window, visible only up close; nothing else on the box lights up.
```

- **Padrão:** `DEVICE NIGHT 940 v1`. O de 850 nm só entra se o Matheus confirmar esse iluminador. O de 850 nm tem brilho
  vermelho fraco na fonte e o de 940 nm não tem nenhum (Axton, citado em `03-imagens-e-prompts.md:399-401`).

### 5.4 Regras de uso

- **Mesma posição relativa** em caminhão, van ou VUC e ônibus rodoviário: sobre o painel, à direita do volante.
- **Nunca** no para-brisa, no retrovisor, presa por ventosa ou sobre o painel de instrumentos.
- **Em plano aberto de cabine,** nunca maior que um mostrador do painel.
- **Nada acende:** sem tela, LED, luz de status ou animação de alerta.
- **Cabo sempre organizado,** correndo pela emenda do painel.
- **Referência de produto:** toda geração com a caixa leva os renders aprovados de S15.
- **Forma diferente do render reprova o quadro,** mesmo que a imagem esteja bonita.

---

## 6. Elenco fixo (pessoas geradas e reutilizadas)

| Personagem | Peças | Ficha (arquivo) |
|---|---|---|
| Motorista de carga | S04, S13, S17 (e S91, futuro) | `elenco/motorista-carga-v1.png` |
| Motorista rodoviário interestadual | S14 e S10 (rosto legível) | `elenco/motorista-rodoviario-v1.png` |
| Gestora de segurança de frota | S05, S13 | `elenco/gestora-v1.png` |
| Sem ficha, porque o rosto nunca fica legível | Motorista rodoviário de costas ou longe (S02, S09, S16), dupla do revezamento (S16), técnico RotaGuard (S12), despachante da garagem (S17), operador de doca (S11), passageiros (S09, S10) | Só o bloco de roupa |

- **Quem instala e quem recolhe:** o técnico RotaGuard instala e pareia a caixa (`docs/produto/PRD.md:29`). Quem recolhe
  a caixa na chegada é a própria empresa (despachante da garagem), não o técnico.

**`CAST TRUCK DRIVER v1`**

```
The truck driver: a Brazilian man aged about 58 with brown (pardo) skin, a sturdy build, short grey hair, grey stubble, sun-weathered skin with deep smile lines and a calm, competent manner; plain grey polo shirt, dark jeans, black leather work boots.
```

**`CAST COACH DRIVER v1`**

```
The coach driver: a Brazilian man aged about 50 with light brown skin, a medium build, short dark hair greying at the temples, clean-shaven, with a calm and attentive manner; plain light blue short-sleeve shirt, dark trousers, black work shoes.
```

**`CAST MANAGER v1`**

```
The fleet safety manager: a Brazilian white woman aged about 44 with shoulder-length dark brown hair, thin dark-rimmed glasses and an attentive, even-tempered manner; light blue button-down shirt with the sleeves rolled once, dark trousers, a plain badge turned backward on a lanyard.
```

**`WARDROBE COACH DRIVER v1`**

```
The coach driver, seen only from behind or far away: a Brazilian man in his late forties with short dark hair, a plain light blue short-sleeve shirt and dark trousers.
```

**`WARDROBE TECHNICIAN v1`**

```
The installation technician, seen only from behind: a Brazilian man in his thirties with short black hair, a plain grey work polo shirt, dark work trousers and thin black work gloves.
```

**`WARDROBE DISPATCHER v1`**

```
The garage dispatcher, seen from the side and partly from behind with her face turned away: a Brazilian woman in her forties with dark hair tied back, a plain navy work polo shirt.
```

- **Ficha de cada personagem:**
  - frente, 3/4 e perfil;
  - fundo cinza liso, luz H1 de janela, 50 mm;
  - Nano Banana Pro com o bloco `CAST` + `STYLE v1` + `BRAZIL PEOPLE v1`.
  O Matheus aprova antes de qualquer cena com a pessoa.
- **Semelhança:** antes de aprovar, conferir se a pessoa gerada lembra alguém real ou famoso. Uso comercial de imagem sem
  autorização gera indenização sem prova de prejuízo (Súmula 403 do STJ; Código Civil, art. 20, citados em
  `03-imagens-e-prompts.md:432-434`).
- **Na cena:** a ficha entra como referência de personagem. Nunca usar Change Camera em pessoa, porque o rosto muda
  (`03-imagens-e-prompts.md:534`).

---

## 7. Recursos futuros: pulseira e leitura de pupila no celular

- **Situação:**
  - a pulseira de frequência cardíaca não existe no código e aparece só como opção de melhoria (`PENDENCIAS.md:164`);
  - a leitura de pupila, se vier, será feita no celular do motorista, que tem câmera melhor;
  - o Matheus deixou os dois "para muito depois" (11/09/2026).
- **Peças:** S90 (pulseira) e S91 (pupila no celular), no fim de `02-fotos.md`, no bloco **"Futuro, não gerar agora"**, fora
  do orçamento.
- **Saiu do roteiro principal:** a checagem de início e fim de turno com a câmera da caixa.
- **Bloco da pulseira (só para quando o recurso for confirmado):**

**`BAND v1`**

```
The work wristband: a slim, flat matte black sensor module about 35 x 25 x 9 mm on a dark grey woven fabric strap about 22 mm wide with a hook-and-loop closure, worn like a watch and looking like work safety equipment; the module's top surface is blank, with no display, digits, lights or logo.
```

- **Proibido nessas peças:**
  - cara de relógio inteligente ou de academia, número de batimentos, ícone de coração, linha de eletrocardiograma, luz
    verde do sensor aparecendo;
  - pulseira de hospital;
  - qualquer semelhança com **tornozeleira eletrônica** (nunca no tornozelo, nunca volumosa, nunca em close sobre mesa, como
    objeto apreendido);
  - close de olho, pupila dilatada, lanterna no olho, comparação "antes e depois";
  - tela do celular mostrando resultado.

---

## 8. Legal e ética (checklist de publicação)

### 8.1 Checklist

- [ ] **Marcas:** nenhum logotipo de montadora, grade reconhecível, pintura de transportadora ou viação existente, marca de
  pneu ou bandeira de posto (Lei 9.279/1996, citada em `03-imagens-e-prompts.md:428-429`).
- [ ] **Placas:** sempre ilegíveis. Nunca inventar placa legível, porque pode coincidir com veículo real.
- [ ] **Rostos:** pessoa gerada sem semelhança com pessoa real. Na captação real, autorização de uso de imagem assinada.
- [ ] **Motorista:** nunca dormindo, babando, bocejando, levando bronca ou punido (`docs/site/personas.md:116-118`).
- [ ] **Passageiros:** sem rosto identificável.
- [ ] **Telas:** escuras e uniformes. Nenhum rosto de motorista em monitor, notebook ou tablet. A interface entra por
  código. Se um dia mostrar trecho gravado, só trecho real de teste com consentimento, nunca gerado.
- [ ] **Referências só próprias:** renders do Blender, fotos próprias e imagens já aprovadas da série. Proibido usar foto de
  terceiros (Pinterest, site de montadora ou de concorrente) como referência (`03-imagens-e-prompts.md:440-443`).
- [ ] **Legenda "Imagem ilustrativa"** (EN "Illustrative image") nas cenas de uso, instalação, recolhimento e escritório.
  O guia do CONAR de 2026 reforça que anunciante e agência respondem pela veracidade de conteúdo feito com IA
  (`03-imagens-e-prompts.md:444-445`).
- [ ] **Mapas:** crédito do DNIT e do IBGE e texto de atribuição do Copernicus quando usado. Nenhum pino de veículo ou evento.
- [ ] **Drone próprio:** cadastro no SISANT e autorização de voo no SARPAS (`03-imagens-e-prompts.md:447-448`).

### 8.2 Drogas, gravação e motorista

- **O produto aponta sinais compatíveis, não diagnostica** (`caixa/vision/activation.py:1`). A validação exigiria parceria com
  universidade e aprovação em comitê de ética (`README.md:94-95`). A mídia não pode prometer detecção de droga.
- **Proibido em qualquer peça:**
  - exame toxicológico, coleta, laboratório, copo de urina, bafômetro, seringa, comprimido, pó;
  - polícia, PRF, blitz, fiscalização, algema, sala de interrogatório;
  - supervisor vigiando, fila de motoristas sendo "testados", segurança de uniforme recebendo a caixa;
  - motorista "suspeito", "dopado", suado, de olhos vermelhos ou com pupila em close;
  - selo "livre de drogas", resultado positivo ou negativo;
  - saco de evidência, luva de perícia, cadeado ou cofre na hora de recolher a caixa.
- **Recolhimento da caixa:** é rotina de fim de viagem, como entregar a chave e a papeleta, nunca apreensão.
- **Gravação de trechos:** o motorista não aparece sendo filmado, e ninguém aparece assistindo a vídeo de motorista.

---

## 9. Fluxo padrão no Magnific

Créditos: preços da página do Magnific acessada em 11/09/2026 e medições do São Jorge (`03-imagens-e-prompts.md:456-603`;
`SITES E PROJETOS/saojorge/docs/prompts-animacoes.md:23`). **Conferir o preço no app antes de rodar**, pela simulação de
custo do Space, porque os preços mudam e Relight, Change Camera, Expand e Retouch não têm preço público.

| Passo | Ferramenta | Modelo e configuração | Entrada | Saída | Créditos |
|---|---|---|---|---|---|
| 0 | Blender (fora do Magnific) | Caixa v1 em tamanho real; renders 2K com fundo transparente | Seção 5 | Renders de S15 | 0 |
| 1 | Geração de rascunho | Nano Banana 2 Lite, proporção final | Prompt montado | 3 composições para escolher | 60 cada |
| 2 | Geração no Space "RotaGuard · série v1" | **Seedream 5 Pro** (3:2 ou 21:9, 2K) quando não há caixa nem rosto legível. **Nano Banana Pro** (4K, 16:9 ou 4:5) quando há caixa ou elenco. Referências de estilo, produto e personagem | Prompt montado + referências | Até 4 tentativas por peça | 75 (Seedream 5 Pro 1,5K) · 150 (Nano Banana Pro 4K, pior caso) |
| 3 | Retouch | Apagar letra, placa, logotipo ou objeto que escapou, ou tirar um veículo ou pessoa para quadro de vídeo | Take escolhido | Take limpo | Sem preço público |
| 4 | Relight | H1 → H2 ou H3 com o prompt de luz da peça, ou transferência da luz de uma imagem aprovada | Take limpo | Variação de horário com a mesma geometria | Sem preço público |
| 5 | Change Camera | Só locação ou veículo, nunca rosto ou caixa | Take aprovado | Outro ângulo | Sem preço público |
| 6 | Expand | Núcleo 4:5 → 16:9; 3:2 → 21:9; 21:9 → 32:9. O prompt descreve só a periferia (céu, parede, piso, asfalto) | Take aprovado | Recorte largo | Sem preço público |
| 7 | Upscale | **Precision photo 2x** (padrão, "zero creativity"). Precision sublime 4x só para 21:9 que sangra. **Nunca Creative em rosto ou na caixa** | Final | Master | 90 por imagem 2K |
| 8 | Vídeo, teste | MiniMax H3 Max Turbo, 768p, 5 s, quadro inicial e final | Master aprovado | Teste de movimento, emenda e estabilidade da caixa | 200 |
| 9 | Vídeo, final | Kling 2.5, 1080p, 10 s, quadro inicial e final (o final só existe em 1080p), sem som | Master aprovado | Take final | 650 por take |
| 10 | **Baixar para o projeto** | Baixar em resolução original **toda** imagem e todo vídeo que for aprovado ou que ainda possa servir de quadro, referência ou reserva, para `site/midia-fonte/<código>/` (nomes na seção 5 do `README.md`). Conferir que o arquivo abre e tem o tamanho certo. **Depois, apagar do Magnific.** Nada fica guardado só lá | Take ou imagem | Arquivo no projeto | 0 |
| 11 | Extração local | ffmpeg na máquina, sem crédito | Arquivo baixado | Quadros WebP ou MP4 em `site/public/midia/` | 0 |
| 12 | Registro | Campo "Registro" da peça (com o nome do arquivo baixado) e status no `README.md` | — | — | 0 |

- **Regra de guarda (decisão do Matheus, 11/09/2026):** vídeos e imagens gerados no Magnific são baixados para a pasta do
  site e não ficam guardados no Magnific. As referências fixas do Space (âncora, renders da caixa, fichas do elenco) também
  têm cópia em `site/midia-fonte/`, para refazer o Space do zero se preciso.
- **Take descartado:** não precisa ser baixado. Apagar do Magnific depois de registrar no campo "Registro" o que deu
  errado.

---

## 10. Ideias de Magnific que valem a pena neste site

1. **Space com referências fixas.**
   - **Montagem:** Space "RotaGuard · série v1" com três grupos de entrada:
     - estilo: S01 dia, S01 noite e S07 dia aprovados;
     - caixa: renders de S15;
     - elenco: as quatro fichas.
   - **Cenas:** um nó de geração por peça, duplicado com Ctrl+D, trocando só o prompt. O Space mostra o total de créditos
     antes de rodar em lote (`Formação de Magnific/08 - Produzindo dezenas de peças numa rodada só.md:26-27`, `:39`, citado
     em `03-imagens-e-prompts.md:522-523`).
   - **Resultado:** a série inteira parece da mesma câmera.
2. **Relight de dia para noite na mesma cena:** S01, S02, S03, S07 e F03 nascem em H1 e ganham H3 pelo Relight; S08 ganha
   H2; S14 (garagem do rodoviário) ganha H1. O site usa o dia e a noite da mesma foto em lugares diferentes (S07 dia no Open Graph de carga, S07
   noite no Ato I) sem gerar duas vezes.
3. **Relight para a sequência de rolagem da garagem (V03).** B04 é gerada em H1, e o Relight cria o H3 com a geometria
   idêntica. H3 vira o quadro inicial e H1 o final no Kling 2.5. O modelo só precisa mudar a luz, que é o princípio do São
   Jorge: "o que é luz cresce em opacidade e brilho, nunca se move em x/y" (`plano-animacoes.md:25`).
4. **Relight com imagem de referência para unificar as noites:** a luz noturna aprovada de S01 é transferida para S04,
   S16 e S08. Todas as noites ficam com o mesmo LED frio e a mesma densidade de sombra.
5. **Change Camera só onde não há rosto nem caixa:**
   - recompor S07 e B02 quando o recorte de celular corta a curva da estrada;
   - alinhar as fileiras de F03 na horizontal.
6. **Expand de 4:5 para 16:9 e 21:9:**
   - **Quais peças:** as fotos com elenco (S05, S12, S13, S14 e S17) nascem em 4:5, que é o recorte exato do cartão de
     celular (`Obsidian/90 - Projetos/Padroes/regras-de-componentes.md:67`). O Expand abre para 16:9 criando só parede, piso
     ou céu, onde entra o texto. B04 vai para 21:9 e B02 para 32:9 do mesmo jeito.
   - **Conferir:** se o Expand criou objeto, letra ou logotipo.
7. **Upscale Precision:**
   - **Padrão:** photo 2x, com nitidez de 5 a 10 e o controle de grão só para preservar a textura, sem adicionar grão.
     Conferir o nome dos controles no app.
   - **Sublime 4x:** só em S07 noite e S08, que sangram em 21:9 em telas de 2560 px.
   - **Creative:** nunca em S01, S02, S03, S17, S18 nem em rosto, porque inventa detalhe (Run the Eval, citado em
     `03-imagens-e-prompts.md:500-501`).
8. **Loops de 8 a 10 s com câmera travada e um único evento de luz:**
   - V01: o farol de um carro em sentido contrário varre a cabine uma vez e some;
   - V02: chuva no para-brisa com o ônibus parado.
   Quadro inicial igual ao final no Kling 2.5 em 1080p, o que emenda sem corte.
9. **Push-in com o quadro final recortado do próprio master (V08).**
   - O quadro final é um recorte de 80% do mesmo master.
   - O modelo vê a caixa idêntica nas duas pontas e só interpola a aproximação.
   - Isso reduz a chance de a caixa "derreter" no meio.
10. **Teste barato antes do vídeo final:** MiniMax H3 Max Turbo em 768p, 5 s, 200 créditos. Confere movimento, emenda e
    estabilidade da caixa. Só o que passar vai para o Kling 2.5 (650). Cada ideia descartada no teste economiza cerca de
    1.100 créditos (dois takes finais menos o teste).
11. **Retouch para limpar em vez de gerar de novo:**
    - apagar letra, placa legível ou emblema na grade;
    - tirar a carreta de S07 noite para criar o quadro vazio de V07;
    - tirar a pessoa de B04 para os quadros de V03.
12. **Flow "pós RotaGuard":**
    - **O que faz:** Relight → Expand → Upscale Precision, salvo como Flow.
    - **Quando rodar de novo:** quando o protótipo real trocar os renders da caixa. Troca-se a referência e roda-se o Flow
      nas peças com a caixa, sem refazer composição.
13. **Gerador 3D (Tripo ou Trellis 2, saída GLB) só a partir de fotos do protótipo real.**
    - Fotografar a caixa real girando, gerar o GLB, limpar e conferir as medidas no Blender.
    - O modelo limpo substitui S15, V05, V09 e V10.
    - Nunca a partir de imagem gerada, porque isso transformaria em "produto" uma forma que ninguém fabricou.
14. **Rascunho de composição no Nano Banana 2 Lite (60 créditos)** antes do Nano Banana Pro (150) na âncora. Escolhe-se o
    enquadramento barato e paga-se a fidelidade da caixa só uma vez.
15. **Teste de locação fixa (beta):** MAI Image 2.5 é o único modelo listado com referência do tipo "locations"
    (`03-imagens-e-prompts.md:471`). Vale um teste para manter a mesma garagem em S12, S13, S14, S17 e B04. É beta: se
    falhar, a garagem é descrita por texto e aceita-se variação.

---

## 11. O que não fazer

- **Motorista falando gerado por IA:** avatar, dublagem, sincronia labial (Omni Human, Veed Fabric e Sync, Runway Act Two,
  Kling Motion Control e as ferramentas de fala do Magnific).
- **Luz de alerta inventada:** LED, tela, luz piscando ou brilho na caixa. O alarme é som.
- **Mapa gerado:** mapa, malha, rota, relevo, globo ou contorno de país. Mapa gerado por IA erra geografia de forma
  grosseira (caso da AIDS 2026, citado em `03-imagens-e-prompts.md:246-249`).
- **Som do alarme gerado por IA:** o site usa o som real (A01).
- **Rosto de motorista ou "trecho gravado" gerado por IA** dentro de qualquer tela.
- **Upscale Creative ou Skin Enhancer** em pessoa ou na caixa. O Skin Enhancer alisa a pele, e o elenco precisa de textura.
- **Variations como imagem final,** porque a caixa muda de forma.
- **Change Camera em rosto ou na caixa.**
- **Vídeo de instalação ou de recolhimento gerado.** É afirmação sobre o produto e deve ser filmado de verdade
  (`03-imagens-e-prompts.md:564-565`).
- **Modelo "Cinematic" (Imagen) e vídeo 4K (Veo 3.1, Seedance 2.5) como padrão:** puxam o "cinematográfico demais" e são
  os mais caros por segundo (`03-imagens-e-prompts.md:571-579`).
- **Referência de terceiros:** Pinterest, montadora, concorrente.
- **Peças do bloco "Futuro, não gerar agora"** (S90, S91).
- **Qualquer geração sem o Matheus aprovar o gasto** e sem a âncora de estilo aprovada.

---

## 12. Critérios de aceite

### 12.1 Foto

- Passa no checklist de rejeição (4.5) inteiro.
- A caixa bate com o render aprovado: proporção, aletas, janela, berço, cabo, nada aceso e tamanho no quadro.
- O assunto cabe na zona segura dos dois recortes (13.2), e a zona de texto é uniforme e sem objeto.
- A cena respeita o motorista (8.2) e não parece "cliente real" sem legenda.
- A luz bate com o horário (H1, H2 ou H3) e com a outra variação da mesma cena.

### 12.2 Vídeo

- Emenda sem salto no loop (último quadro igual ao primeiro).
- Luz constante, fora o evento previsto.
- Textura não "ferve" entre quadros.
- A caixa não muda de forma e não acende.
- Nenhum texto aparece.
- A câmera travada não deriva.
- Curadoria quadro a quadro antes de subir, como no São Jorge (`como-entregar-midia.md:32-33`).

### 12.3 Mapa

- Dado de fonte pública, com data da versão e licença registradas.
- Projeção declarada.
- Conferido contra a fonte: nenhuma rodovia inventada ou fora do lugar.
- Nenhum pino, veículo ou evento.
- Legenda "Viagem de demonstração" em toda rota.
- Crédito no rodapé.

### 12.4 Render do Blender

- Medidas conferidas no modelo (bounding box) contra a tabela 5.1.
- Nenhum logotipo.
- Malha fechada (`is_manifold`), sem corpos soltos.
- Marcado como "protótipo em definição" no site enquanto for hipótese.

---

## 13. Entrega e pós-produção

### 13.1 Onde salvar e contrato de nomes

Ver `README.md`, seção 5. Resumo: a peça nova usa o **mesmo código** da foto provisória que substitui.

### 13.2 Recortes e zona segura

| Master | Recorte 9:16 de altura cheia | 4:5 de altura cheia | 21:9 de largura cheia | Janela segura do assunto |
|---|---|---|---|---|
| 3:2 (Seedream 5 Pro 2K, ampliado 2x para cerca de 4000 × 2667 px) | 37,5% da largura | 53% da largura | 64% da altura (corta 18% em cima e 18% embaixo) | 37,5% da largura, entre 18% e 82% da altura |
| 16:9 (Nano Banana Pro 4K, 3840 × 2160 px) | 31,6% da largura | 45% da largura | 76% da altura (corta 12% em cima e 12% embaixo) | 31,6% da largura, entre 12% e 88% da altura |

- **Tamanhos de saída:** computador 2560 × 1097 (21:9) ou 2560 × 1440 (16:9); celular 1080 × 1350 (4:5) ou 1080 × 1920
  (9:16) (`03-imagens-e-prompts.md:161-162`).
- **A janela segura pode ficar no terço do assunto;** o texto do computador vai no lado oposto.
- **No celular,** o texto vai acima ou abaixo da imagem, nunca sobre ela, exceto nos 9:16 de céu escuro.

### 13.3 Formatos e pesos

| Tipo | Formato | Larguras | Teto |
|---|---|---|---|
| Foto | AVIF e WebP | 640, 1080, 1600 e 2560 px | Meta proposta: até 250 KB na maior largura em AVIF |
| Sequência de rolagem | WebP q78, 1600 × 900 px (celular 1080 px) | — | 45 KB por quadro, 6 MB por sequência no computador, 2,5 MB no celular, pôster até 120 KB (`plano-animacoes.md:174`) |
| Loop | MP4 H.264 sem áudio, `+faststart`, e pôster | 1080 × 1920 (9:16) ou 1920 × 1080 (16:9) | Meta proposta: até 3 MB por 10 s |
| Mapa | TopoJSON ou SVG gerado no build, e AVIF de reserva | — | Meta proposta: até 150 KB por mapa |
| Render do Blender | PNG com fundo transparente (original) → WebP ou AVIF sobre a cor do fundo da seção | 1600 px | Igual à foto |

- **Movimento reduzido:** todo vídeo e toda sequência têm pôster e, com `prefers-reduced-motion`, viram imagem parada. Loop
  que toca sozinho por mais de 5 s tem botão de pausa visível (WCAG 2.2.2).
- **Contraste do texto sobre foto:** medido sobre os pixels reais da zona, no pior ponto. Mínimo de 4,5:1 para texto
  pequeno e 3:1 para texto grande. No mapa-múndi, medir com o véu da noite passando por baixo do texto.
- **Legenda "Imagem ilustrativa"** em canto discreto e legível, e crédito de dados de mapa no rodapé.
- **Texto alternativo:** cada peça traz PT e EN como base. As outras línguas do site (es, fr, zh-CN) saem da tradução no
  next-intl. O manifesto de fotos do site hoje só tem `altPt` e `altEn` (`site/src/lib/fotos.ts:13-14`).
- **Crédito no manifesto:** a peça gerada entra no `site/src/data/fotos-provisorias.json` com o mesmo `codigo`, o `arquivo`
  em `site/public/midia/`, autor "RotaGuard (imagem ilustrativa gerada)" e licença "própria". O componente mostra esse
  crédito no canto da foto (`site/src/components/photo.tsx:48`, `:65-68`).
- **Registro:** o prompt aprovado vai para `Obsidian/90 - Projetos/Prompts/prompts-de-imagem.md` só depois de ver o
  resultado, no formato daquela nota. O custo real vai no campo "Registro" da peça e no `README.md`.
- **Substituição por captação real:** quando existir protótipo, garagem parceira ou frota com autorização, a foto real
  entra no lugar da gerada com o mesmo código, e a peça passa a "substituída por captação real". Mesmo contrato do São
  Jorge (`plano-animacoes.md:143-147`).

---

## 14. O que foi descartado e por quê

| O que era | Onde estava | Por que saiu |
|---|---|---|
| Conceito "Diário de bordo": o site como 24 h num disco de tacógrafo | `docs/site/prompts-imagens.md:1-4` (apagado) | Abandonado quando o site virou página de produto. Ordena pelo relógio, não pelas perguntas de quem compra (`02-direcao-de-arte.md:146-166`) |
| Bloco de estilo com filme 35 mm, grão, "cream paper" e desfoque em tudo | antigo `:14-19` | Grão e textura de papel repetem o app recusado. Desfoque global dá cara de IA |
| 01 papel de diagrama, 02 disco de tacógrafo, 10 banner com disco | antigo `:36-57`, `:134-142` | Ornamento sem produto nem frota. Lembra controle de jornada, que a P1 já tem |
| 04 olho infravermelho em close | antigo `:70-79` | Biometria em close é estética de vigilância, contra o medo do P5 |
| 07 faixa refletiva | antigo `:101-109` | Ornamento temático do tipo rejeitado no "Cabine noturna" |
| 03 cabine de madrugada com chuva, rastros de farol, "tired" e "cinematic" | antigo `:59-67` | Clichê e sinais de IA. Virou S01 noite, sem chuva em movimento e sem cansaço |
| 05 computador exposto com câmera "high near the windshield" e poeira no ar | antigo `:81-88` | Posição errada e implausível. Virou S03 com a caixa canônica |
| 06 pátio no crepúsculo com lâmpada de sódio e grão | antigo `:91-98` | Virou F03, com dia e noite por Relight e LED |
| 08 rodovia no amanhecer âmbar "hopeful" | antigo `:111-118` | Amanhecer é clichê. Virou S07 em dia nublado e B02 |
| 09 retrato "tired" em "roadside diner" com copo na mão | antigo `:121-132` | Conceito americano, estereótipo e artefato de objeto na mão. Virou S13 e S04 |
| V1 estrada com faixa tracejada correndo, V2 piscada, V3 timelapse de amanhecer, V4 disco | antigo `:154-182` | Efeitos rejeitados pelo Matheus (tracejado, piscada) e clichês. Viraram V01, V03, V04 e V08 |
| Aparelho "caixa de fósforo" com unidade de processamento escondida atrás do painel | `03-imagens-e-prompts.md:376-411` (Anexo D.6) | Em 11/09 o Matheus definiu uma caixa com Raspberry Pi dentro e câmera acoplada, que sai do veículo na chegada |
| Promessa "nenhuma imagem é gravada" e fronteira "a imagem não passa daqui" | `02-direcao-de-arte.md:458-459` | Em 11/09 a caixa passou a gravar trechos curtos quando um sinal se repete. A escala 1:1 virou "a viagem não é filmada inteira" |
| CCO acompanhando a frota ao vivo como centro do Ato III | `02-direcao-de-arte.md:450-452` | Em 11/09 o centro virou o registro da viagem gerado na chegada |
| Ônibus urbano, corredor, CCO urbano e motorista de ônibus urbano (S06, antiga S10 e antiga S14) | Primeira versão deste roteiro (11/09) | Em 11/09 o foco de ônibus passou a ser o rodoviário interestadual. Resumo das cenas em `02-fotos.md`, "Rebaixadas", caso o urbano volte |
| Técnico de garagem que instala e também recolhe a caixa | Primeira versão deste roteiro (11/09) | O PRD separa os papéis: o técnico RotaGuard instala; a empresa recolhe (`docs/produto/PRD.md:29`, `:39-40`) |
| Checagem de pupila no início e no fim do turno com a câmera da caixa | Pedido de 11/09 (primeira versão deste roteiro) | Em 11/09 a pupila, se vier, passou para o celular do motorista, e ficou "para muito depois" |
| "Rota ilustrativa" e corredor SP–PR–SC–RS inteiro | `03-imagens-e-prompts.md:232`, `:219` | Trocados por "Viagem de demonstração" na BR-116 São Paulo → Curitiba (F02, V06) |
| B03 ponte de concreto | `03-imagens-e-prompts.md:225` | Adiada: a direção "Escalas" não tem lugar para ela nesta rodada |
| Âmbar como cor que "conversa com a interface" | `03-imagens-e-prompts.md:325-326` | O site não tem âmbar de marca. Nas fotos, âmbar só como ponto de luz real |

---

## Fontes

**Repositório e vault**
- `docs/site/avaliacoes/2026-09-11-previa-v2/03-imagens-e-prompts.md` (Anexos A a F), `02-direcao-de-arte.md`,
  `04-estrutura-e-conversao.md`, `05-tecnica-e-veracidade.md`
- `docs/site/personas.md`, `docs/site/contexto.md`, `docs/site/dados-mapas.md`, `docs/produto/PRD.md`,
  `docs/specs/008-site.md`, `README.md`, `PENDENCIAS.md`, `caixa/vision/alarm.py`, `caixa/vision/activation.py`,
  `caixa/vision/pupil.py`
- Site em código: `site/src/app/[locale]/page.tsx`, `site/src/components/photo.tsx`, `site/src/lib/fotos.ts`,
  `site/src/components/sections/*.tsx`
- Memória do projeto: `feedback-visual-sobrio-profissional.md`
- `Obsidian/90 - Projetos/site-saojorge.md`; `SITES E PROJETOS/saojorge/docs/plano-animacoes.md`,
  `prompts-animacoes.md`, `como-entregar-midia.md`
- `Obsidian/90 - Projetos/Padroes/erros-que-a-ia-comete.md` (erros 46, 70, 71 e 72), `meu-estilo-de-sites.md`,
  `regras-de-componentes.md`; `Obsidian/90 - Projetos/Prompts/prompts-de-imagem.md`

**Web (conferidas em 11/09/2026)**
- [Raspberry Pi 3 B+, desenho mecânico](https://datasheets.raspberrypi.com/rpi3/raspberry-pi-3-b-plus-mechanical-drawing.pdf)
- [Raspberry Pi 4 Model B, especificações](https://www.raspberrypi.com/products/raspberry-pi-4-model-b/specifications/)
- [Raspberry Pi, documentação das câmeras](https://www.raspberrypi.com/documentation/accessories/camera.html) ·
  [Camera Module 3](https://www.raspberrypi.com/products/camera-module-3/)
- Demais fontes externas (Kamali et al. 2025, guia do Veo 3.1, Kling, preços e documentação do Magnific, Seeing Machines,
  Axton, DETRAN-PR, IBGE, CNT, DNIT, Natural Earth, Copernicus, STJ, CONAR, DECEA): lista completa em
  `03-imagens-e-prompts.md:735-768`
