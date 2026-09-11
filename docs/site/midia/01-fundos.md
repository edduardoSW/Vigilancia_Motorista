# Fundos do site RotaGuard (mapas e pátio)

> As regras comuns (luz, lentes, blocos, legal e ética, fluxo no Magnific, aceite e entrega) estão em
> `00-regras-gerais.md`. A única peça gerada por IA deste arquivo (F03) traz dentro do prompt os blocos fixos que usa e
> pode ser copiada inteira.

**Regras dos mapas (valem para F01, F02, F04 e F05):**

1. **A geografia nunca é gerada por IA.** Vem de dado real, desenhado em código no build ou no Blender
   (`03-imagens-e-prompts.md:246-253`).
2. **O mapa é contexto, não o produto.** O RotaGuard não tem GPS. Nada de pino de veículo, pino de evento, mapa de calor
   ou "frota ao vivo". Toda rota leva a legenda **"Viagem de demonstração"** (`02-direcao-de-arte.md:182-186`).
3. **O mapa-múndi não sugere operação global.** Sem arcos entre continentes. O uso honesto é o tempo: a noite real
   passando pelo mundo (`03-imagens-e-prompts.md:256-258`).
4. **Só a luz se move.** A noite avança; a rota se desenha uma vez e para. Nada de ponto correndo pela linha, globo
   girando, zoom contínuo ou câmera seguindo um ponto (`02-direcao-de-arte.md:517-518`).
5. **Sem textura:** nada de papel envelhecido, grade de radar, neon ou tracejado de estrada.
6. **Texto sempre em HTML,** pelo next-intl, nunca gravado dentro do SVG ou da imagem.
7. **Estilo:** traço grafite sobre concreto claro, com 12% a 18% de contraste sob o texto. O acento vai só no trecho de
   que a seção fala (`03-imagens-e-prompts.md:275-276`).

**Peças, na ordem do site:** F05 (I.1) · F01 (I.2) · F02 (I.2) · F04 (III.7, opcional) · F03 (III.1)

---

### F05 · `mundo-noite` · I.1 Mundo (primeira tela)

- **Tipo · status · origem:** fundo (mapa em código) · a fazer · Natural Earth + cálculo da faixa da noite no navegador.
  Sem crédito.
- **Substitui:** nenhuma.
- **Objetivo (5 s):** "agora mesmo é noite em parte do mundo, e é de madrugada que o risco pesa" (a madrugada pesa no
  cálculo do risco, `docs/site/contexto.md:32`).
- **Persona:** todas. P1 e P2 reconhecem a operação noturna.
- **Fonte de dados, licença e atribuição:**
  - Natural Earth, países em escala 1:110 milhões: domínio público, sem atribuição obrigatória
    (`03-imagens-e-prompts.md:251`);
  - posição do Sol calculada pela hora do visitante, como no exemplo "Solar Terminator" do d3
    (`03-imagens-e-prompts.md:765`).
- **Tratamento:**
  - projeção Equal Earth (`d3.geoEqualEarth`), de áreas iguais, sem graticulado;
  - terra num tom de concreto um pouco mais escuro que o oceano (o oceano é o próprio fundo da página);
  - sem fronteiras entre países, só o contorno do Brasil em traço grafite de 1 px e preenchimento um passo mais escuro;
  - **noite:** véu preto translúcido (`02-direcao-de-arte.md:478`), em dois níveis:
    - círculo de 90° em volta do ponto oposto ao Sol, com cerca de 35% de opacidade;
    - círculo de 84° (crepúsculo civil) com mais 10%, para a borda ficar macia sem gradiente decorativo;
  - sem luzes de cidade, sem estrelas, sem brilho.
- **Área do texto e recorte:**
  - **computador (21:9, largura total):** título e botão "Pedir piloto" à esquerda; Brasil no terço direito (girar a
    projeção para longitude central perto de −100°); o véu da noite pode passar por baixo do texto;
  - **contraste:** medir no pior momento, com o véu escuro inteiro sob o título;
  - **celular (4:5):** recorte das Américas e do Atlântico, com o Brasil no centro e o texto acima do mapa.
- **Não pode aparecer:**
  - arcos, rotas entre países, pinos, pontos pulsando;
  - luzes noturnas de cidades (sugerem presença);
  - globo 3D, rede de pontos conectados;
  - nomes de países na imagem;
  - âmbar.
- **Animação:** V04 `terminador-noite` (`04-videos.md`). Só o véu se move, em tempo real. Com movimento reduzido, fica
  parado na hora real.
- **Fluxo (sem Magnific):**

| Passo | Ferramenta | Configuração |
|---|---|---|
| 1 | Script de build (Node) | Baixar Natural Earth 1:110m (países), converter para TopoJSON e manter só o polígono de terra unido e o polígono do Brasil |
| 2 | Componente de cliente | `d3-geo` com `geoEqualEarth`; posição do Sol pela hora UTC; `geoCircle` de 90° e de 84° no ponto oposto ao Sol; recalcular a cada 60 s |
| 3 | Reserva estática | SVG ou AVIF gerado no build com a noite fixa às 02:00 de Brasília, para sem JavaScript e para o Open Graph da versão EN |

- **Aceite específico:** a faixa da noite bate com um serviço de referência (por exemplo, o mapa de dia e noite do
  timeanddate) na mesma hora; o Brasil está no lugar certo; nenhum rótulo dentro do SVG.
- **Arquivo e formatos:** `public/midia/mapas/F05-mundo-110m.json` (meta proposta: até 100 KB) e
  `F05-mundo-noite-reserva.avif`.
- **Alt PT:** "Mapa-múndi com a faixa da noite neste momento; o Brasil em destaque."
- **Alt EN:** "World map showing where it is night right now, with Brazil highlighted."
- **Registro:** data da versão do Natural Earth — · fórmula conferida em — · ajustar —

### F01 · `malha-federal` · I.2 Brasil

- **Tipo · status · origem:** fundo (mapa em código) · a fazer · DNIT (Sistema Nacional de Viação) + IBGE (contorno do
  país e dos estados). Sem crédito.
- **Substitui:** nenhuma.
- **Objetivo (5 s):** "a escala muda: do mundo para a malha de rodovias federais onde as frotas rodam".
- **Persona:** P1 e P2. Secundária: P3.
- **Fonte de dados, licença e atribuição:**
  - DNIT, SNV, camada de rodovias federais em SHP, GeoJSON ou KML pelo VGeo e pelos dados abertos
    (`03-imagens-e-prompts.md:250`; `docs/site/avaliacoes/2026-09-11-previa-v2/referencias.md:34`);
  - IBGE para o contorno do Brasil e das UFs;
  - crédito no rodapé: "Rodovias: DNIT, SNV (versão)" e "Limites: IBGE (versão)".
- **Tratamento:**
  - projeção cônica de áreas iguais (Albers) ajustada ao Brasil;
  - simplificação com tolerância perto de 200 m no mapshaper (`03-imagens-e-prompts.md:266`);
  - contorno do Brasil em 1 px grafite a 30%, UFs em 0,5 px a 12%;
  - rodovias federais em 0,75 a 1 px grafite a 45%;
  - **só trechos pavimentados**, para não aparecer trecho planejado desenhado tracejado;
  - trechos duplicados um pouco mais grossos (1,25 px), o que é informação real;
  - sem rótulos;
  - entrada da seção: a malha cresce em opacidade uma vez (luz, não movimento).
- **Área do texto e recorte:**
  - **computador (21:9):** Brasil inteiro nos 60% da direita, texto à esquerda sobre o fundo liso;
  - **celular (9:16):** recorte do Centro-Sul (SP, PR, SC, RS), onde BR-116 e BR-101 correm quase de norte a sul, com o
    texto acima.
- **Não pode aparecer:**
  - pinos, veículos, eventos, mapa de calor;
  - nomes de cidades dentro do SVG;
  - linhas brilhando, pontos correndo, tracejado;
  - fundo escuro de "painel de controle".
- **Animação:** só a entrada por opacidade (400 a 600 ms, uma vez). F02 e V06 desenham a rota por cima.
- **Fluxo (sem Magnific):**

| Passo | Ferramenta | Configuração |
|---|---|---|
| 1 | Download | SNV do DNIT (registrar a data da versão) e malha do IBGE |
| 2 | mapshaper | Filtrar trechos pavimentados e duplicados, simplificar (cerca de 200 m), exportar TopoJSON |
| 3 | Script de build | `d3-geo` com Albers ajustado ao Brasil; gerar SVG estático em `public/` |
| 4 | Conferência | Sobrepor o SVG ao visualizador do DNIT em três pontos (SP, Curitiba, Brasília) |

> [!note] Hipótese, confirmar
> Os nomes dos campos do SNV que marcam "pavimentada" e "duplicada" e os parâmetros da projeção Albers usados pelo IBGE
> não foram conferidos nesta sessão. Ler o dicionário do SNV e a documentação do IBGE antes do script.

- **Aceite específico:** nenhuma rodovia fora do lugar na sobreposição; SVG abaixo de 150 KB (meta proposta); crédito
  presente.
- **Arquivo e formatos:** `public/midia/mapas/F01-malha-federal.svg` e `F01-malha-federal-reserva.avif`.
- **Alt PT:** "Mapa do Brasil com a malha de rodovias federais."
- **Alt EN:** "Map of Brazil showing the federal highway network."
- **Registro:** versão do SNV — · versão do IBGE — · tolerância usada — · peso final —

### F02 · `rota-br116-demo` · I.2 Brasil (viagem de demonstração)

- **Tipo · status · origem:** fundo (mapa em código, sobre F01) · a fazer · traçado da BR-116 entre São Paulo e Curitiba,
  tirado do SNV. Sem crédito.
- **Substitui:** nenhuma.
- **Objetivo (5 s):** "uma viagem noturna de exemplo, de São Paulo a Curitiba, que o resto da página conta" (roteiro S2,
  `04-estrutura-e-conversao.md:332-354`).
- **Persona:** P1 e P4. Secundária: P5.
- **Fonte de dados, licença e atribuição:** DNIT, SNV (mesma versão de F01).
- **Tratamento:**
  - a BR-116 entre São Paulo e Curitiba em traço grafite de 2 px a 90%, sobre F01;
  - nenhuma cor de marca, nenhum âmbar;
  - início e fim marcados por círculos vazados de 6 px (não pinos);
  - nomes "São Paulo" e "Curitiba" em HTML;
  - **legenda fixa em HTML:** "Viagem de demonstração. O RotaGuard não registra localização.";
  - as horas da viagem (22:40 saída, 02:14 alarme, 07:00 chegada e relatório) ficam **numa linha do tempo ao lado do mapa,
    não sobre a linha**, porque marcar hora num ponto da estrada seria marcar posição.
- **Área do texto e recorte:**
  - **computador:** mapa nos 60% da direita, linha do tempo nas 5 colunas da esquerda;
  - **celular:** mapa pequeno no topo da seção e linha do tempo vertical embaixo, sem prender a rolagem
    (`04-estrutura-e-conversao.md:289-291`).
- **Não pode aparecer:**
  - caminhão ou ônibus andando sobre a linha;
  - pontos de evento na estrada;
  - quilometragem como se fosse medida pelo produto;
  - zoom seguindo a rota.
- **Animação:** V06 `rota-br116-desenho`, que se desenha uma vez quando a seção entra (`04-videos.md`).
- **Fluxo (sem Magnific):**

| Passo | Ferramenta | Configuração |
|---|---|---|
| 1 | mapshaper | Extrair do SNV os segmentos da BR-116 entre os limites de São Paulo e de Curitiba e unir num caminho só |
| 2 | Script de build | Mesma projeção de F01; exportar um `<path>` único para o `stroke-dashoffset` |

> [!note] Hipótese, confirmar
> - A rota de demonstração São Paulo → Curitiba pela BR-116 ainda depende do Matheus (`04-estrutura-e-conversao.md:665-666`).
> - Se no futuro o registro da viagem ganhar localização por integração com rastreador, a legenda e a regra 2 mudam.
>   Hoje não há GPS.

- **Aceite específico:** o traçado coincide com o SNV; a legenda está visível sem rolar; nenhuma marca sobre a linha.
- **Arquivo e formatos:** `public/midia/mapas/F02-rota-br116-demo.svg`.
- **Alt PT:** "Viagem de demonstração pela BR-116, de São Paulo a Curitiba, desenhada sobre a malha federal."
- **Alt EN:** "Demonstration trip along the BR-116 highway from São Paulo to Curitiba, drawn over the federal network."
- **Registro:** versão do SNV — · segmentos usados — · ajustar —

### F04 · `serra-relevo` · III.7 Ficha técnica ou `/perguntas-frequentes` ("E sem sinal?") · opcional

- **Tipo · status · origem:** fundo (mapa de relevo) · a fazer, opcional · Copernicus DEM GLO-30 + traçado do SNV, com
  sombreamento no GDAL ou no Blender. Sem crédito.
- **Substitui:** nenhuma.
- **Objetivo (5 s):** "na serra, sem sinal de celular, o registro continua na caixa e sai inteiro na chegada".
- **Persona:** P1 e P2. Secundária: P3.
- **Fonte de dados, licença e atribuição:**
  - Copernicus DEM GLO-30, com o texto de atribuição exigido pela licença
    ([licença](https://docs.sentinel-hub.com/api/latest/static/files/data/dem/resources/license/License-COPDEM-30.pdf));
  - traçado da BR-116 do SNV.
- **Tratamento:**
  - relevo sombreado em cinzas de concreto, luz de noroeste a 45° (convenção de mapa);
  - exagero vertical de no máximo 1,5x, declarado na legenda;
  - contraste de 12% a 18% sob o texto;
  - traçado da rodovia em grafite de 1,5 px;
  - sem rótulos;
  - **não afirmar falta de sinal num lugar com nome** (`03-imagens-e-prompts.md:221`).
  - **Opção Blender:** o mesmo relevo em vista oblíqua de 30°, com câmera ortográfica e sem movimento.
- **Área do texto e recorte:** computador 21:9 com o texto à esquerda sobre a parte mais plana; celular 4:5 com o texto
  acima.
- **Não pode aparecer:**
  - antenas, ícones de sinal ou círculos de cobertura;
  - neblina decorativa;
  - veículo;
  - nome da serra.
- **Animação:** nenhuma.
- **Fluxo (sem Magnific):**

| Passo | Ferramenta | Configuração |
|---|---|---|
| 1 | Download | Folhas do Copernicus DEM GLO-30 que cobrem o trecho de serra da BR-116 entre SP e PR |
| 2 | GDAL | `gdaldem hillshade` com azimute de 315°, altitude de 45° e fator z de 1,5; recorte na área do trecho |
| 3 | Composição | Sobrepor o traçado do SNV na mesma projeção; exportar AVIF |
| 4 | Opcional | Blender com o DEM como deslocamento, câmera ortográfica oblíqua, render estático |

> [!note] Hipótese, confirmar
> Qual trecho de serra a BR-116 atravessa entre São Paulo e Paraná precisa ser conferido no SNV e no relevo antes de
> recortar. A peça só entra se o Matheus aprovar o argumento "o registro não depende de sinal".

- **Aceite específico:** relevo coerente com o traçado (a estrada segue os vales); atribuição do Copernicus presente.
- **Arquivo e formatos:** `public/midia/mapas/F04-serra-relevo` em AVIF e WebP, 21:9 e 4:5.
- **Alt PT:** "Relevo sombreado de um trecho de serra com o traçado de uma rodovia federal."
- **Alt EN:** "Shaded relief of a mountain section with the route of a federal highway."
- **Registro:** folhas do DEM — · parâmetros — · ajustar —

### F03 · `patio-aereo` · III.1 A frota (faixa de abertura)

- **Tipo · status · origem:** fundo (foto) · a gerar · IA (Seedream 5 Pro). Substituir por drone próprio com cadastro no
  SISANT e autorização no SARPAS (`03-imagens-e-prompts.md:447-448`). De cima não aparecem placa, logotipo lateral nem
  rosto.
- **Substitui:** foto provisória F03 `patio-aereo`.
- **Objetivo (5 s):** "frotas inteiras, carga e passageiros, paradas na garagem: é para esta escala".
- **Persona:** P3 (620 ônibus, 9 garagens) e P1. Secundária: P4.
- **Seção e posição:** abertura do Ato III, faixa sangrando em 21:9 com o título do ato; abaixo dela, a faixa de
  segmentos (S07, S08, S10, S11).
- **Composição:**
  - vista zenital a 90° exatos de um pátio;
  - 40% da esquerda: área de manobra vazia de asfalto cinza-escuro liso, com poucas linhas-guia brancas;
  - 60% da direita: fileiras organizadas, primeiro de ônibus urbanos (com aparelhos de ar-condicionado cinza no teto),
    depois de caminhões de cabine avançada com carretas de teto branco e cinza-claro;
  - poucas pessoas pequenas andando entre as fileiras.
- **Área livre para texto:** área de manobra à esquerda, escura (texto claro).
- **Luz e hora:** H1. H3 pelo Relight (alternativa para seção escura).
- **Lente e câmera:** zenital, equivalente a 24 mm, a cerca de 50 m, tudo nítido.
- **Paleta:** cinza do asfalto, branco dos tetos, cinza dos aparelhos de ar-condicionado.
- **Não pode aparecer:**
  - números ou nomes pintados nas vagas ou nos tetos;
  - logotipo no teto;
  - carro de passeio em destaque;
  - piscina, campo ou vizinhança reconhecível;
  - sombras longas de fim de tarde.
- **Recortes (master 3:2):**
  - computador 21:9 (o padrão se repete e recorta sem perda);
  - celular 9:16 com recorte de uma coluna de fileiras e o texto acima;
  - zona segura: o padrão nos 60% da direita.
- **Variações:**
  - H3 (Relight);
  - Change Camera só para alinhar as fileiras na horizontal, se saírem tortas.
- **Referências:** estilo (âncora).
- **Fluxo no Magnific** (créditos estimados em 11/09/2026; conferir no app):

| Passo | Ferramenta | Modelo e configuração | Créditos |
|---|---|---|---|
| 1 | Geração no Space | Seedream 5 Lite, 4K, 3:2, 4 tentativas (zenital com pouco detalhe fino) | 200 |
| 2 | Retouch (se preciso) | Apagar número ou letra pintada | sem preço público |
| 3 | Change Camera (se preciso) | Girar para alinhar as fileiras | sem preço público |
| 4 | Relight | Prompt H3 abaixo | sem preço público |
| 5 | Upscale | Precision photo 2x, H1 e H3 | 180 |
| — | Total estimado | | cerca de 380 + ferramentas sem preço |

- **Prompt (EN), montado.** Blocos: cena + `H1 v1` + `STYLE v1` + `BRAZIL VEHICLES v1` + `CLEAN v1`.

```
Straight top-down aerial photograph at exactly 90 degrees from about 50 meters above a Brazilian transport garage yard in the morning, 24mm equivalent lens, everything in focus, forming a calm graphic pattern. The left 40 percent of the frame is a wide empty maneuvering area of smooth dark grey asphalt with a few plain white guide lines. The right 60 percent holds neat parallel rows of parked vehicles: first a row of plain white city buses whose roofs carry grey air-conditioning units, then several rows of plain white cab-over trucks with long trailers whose plain white and light grey roofs form long stripes. Parking bays are marked only with plain white lines. Three small figures in plain work clothes walk between the rows. Soft overcast light gives short, faint shadows under the vehicles.

Light: overcast late morning, soft diffuse daylight from a uniformly bright white-grey sky, the sun fully hidden behind an even cloud layer, gentle soft-edged shadows, daylight white balance around 5600 K.

Editorial documentary photograph for the annual report of a Brazilian transport company, showing real working conditions in an honest, unglamorous and restrained way. Neutral colors with low-to-medium saturation, moderate contrast and shadows that keep visible detail. Texture comes from the real world: worn seat fabric, scratched plastic, road grime, concrete stains, creased work clothes. Clean modern digital capture with a natural finish, even sharpness and a plain, ungraded look.

Brazilian vehicles: left-hand drive with traffic on the right; European-style cab-over trucks with flat fronts; buses and coaches without company livery; all vehicles in plain white, silver or graphite paint; Mercosur license plates present but too small and angled to read.

Every sign, screen, label and license plate is free of legible characters: signage is distant and out of focus, plates are too small and angled to read, monitors, laptops and tablets show a uniform dark screen, uniforms and vehicles are plain and unmarked. Hands are relaxed and partly hidden. Every mechanical part is complete and connected, and all shadows and reflections agree with one consistent light direction.
```

- **Prompt de Relight (EN), para H3:**

```
Night: tall LED lamps standing between the rows cast round pools of cool white light on the asphalt; the vehicle roofs catch the light at the edges of each pool and fall into darkness between them; the empty maneuvering area on the left is dark with only faint spill light.
```

- **Aceite específico:**
  - vista realmente a 90° (sem laterais de veículo aparecendo);
  - carretas acopladas aos cavalos;
  - fileiras paralelas;
  - nenhum texto no teto ou no chão.
- **Legal:** sem logotipo em teto; vizinhança genérica. Legenda "Imagem ilustrativa": não.
- **Arquivo e formatos:** `F03-patio-aereo-h1` e `F03-patio-aereo-h3` → AVIF e WebP em 21:9 e 9:16.
- **Alt PT:** "Vista aérea de um pátio com fileiras de ônibus urbanos e carretas estacionados."
- **Alt EN:** "Aerial view of a yard with rows of parked city buses and tractor-trailers."
- **Registro:** data — · modelo — · take aprovado — · custo real — · ajustar —
