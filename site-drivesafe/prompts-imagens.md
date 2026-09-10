# Prompts de imagem e vídeo: site DriveSafe AI ("Diário de bordo")

- **Direção:** o site conta 24 horas na estrada. Começa de dia, em papel de diagrama de tacógrafo, escurece na
  madrugada e amanhece no contato.
- **Uso:** cada imagem abaixo tem nome de arquivo, proporção, onde entra no site e o prompt pronto.
- **Idioma dos prompts:** inglês, porque os geradores respondem melhor. As notas estão em português.
- **Onde salvar:** em `site-drivesafe/public/midia/originais/`, com o nome indicado (qualquer extensão). Eu comprimo,
  recorto e coloco no lugar.
- **Enquanto as imagens não chegam:** o site mostra fundos desenhados em código (papel, grade do disco, faixa
  refletiva), então nada fica quebrado.

## Bloco de estilo (colar no fim de todo prompt de foto)

```
documentary photography, Brazilian highway trucking culture, shot on 35mm film, visible film grain,
natural and practical light only, warm muted palette of cream paper, graphite and signal amber,
honest and unpolished, shallow depth of field, no text, no letters, no numbers, no logos,
no watermarks, no brand names, not a stock photo, not glossy CGI, not illustration
```

**Evitar em todas** (campo "negative prompt", se a ferramenta tiver):

```
text, typography, logo, watermark, signature, stock photo smile, people looking at camera, glossy 3D render,
plastic skin, oversaturated colors, neon purple, blue tech gradient, lens flare overload, cartoon, illustration,
deformed hands, extra fingers, blurry face, frame border
```

> Os pedidos de "sem texto" e "sem logo" são de propósito: todo texto do site entra por código, nos dois idiomas,
> e marca de terceiro na imagem cria problema de direito de uso.

---

## Fotos

### 01 · `papel-diagrama` (fundo de todas as seções diurnas)
- **Proporção:** quadrada, 2048 × 2048 px, **sem emenda** (seamless)
- **Onde:** fundo do site inteiro nas horas de dia, bem clarinho, atrás do texto
- **Prompt:**
```
seamless tileable texture of aged tachograph diagram paper, cream off-white stock, faint printed radial
hour grid in light warm grey, subtle fiber texture, tiny ink specks and one very faint coffee ring,
flat even lighting from above, top-down scan, extremely subtle, low contrast, no text, no numbers
```
- **Nota:** se sair com números ou letras, peça de novo com "blank paper, no printed numbers".

### 02 · `disco-tacografo` (detalhe do topo)
- **Proporção:** quadrada, 2400 × 2400 px
- **Onde:** atrás do disco animado do topo, com baixa opacidade, para dar material real
- **Prompt:**
```
top-down macro photograph of a used paper tachograph disc from a truck, circular 24-hour chart, dark stylus
ink traces showing driving and resting periods, slightly wrinkled paper, thumb smudge, resting on a worn
graphite dashboard surface, soft morning window light from the left, documentary macro, film grain
```
- **Nota:** o disco real costuma ter números impressos. Tudo bem se aparecerem pequenos e fora de foco; se ficarem
  nítidos e legíveis, peça "numbers out of focus".

### 03 · `cabine-madrugada` (capa do capítulo 02:14)
- **Proporção:** 16:9, 2400 × 1350 px
- **Onde:** capa da seção em que a página escurece e a tela "pisca" (microssono)
- **Prompt:**
```
inside the cab of a Brazilian cargo truck at 2 in the morning, view from the passenger seat toward the
windshield, driver's hands on the steering wheel only, face out of frame, dim amber dashboard glow, light rain
on the windshield, blurred streaks of oncoming headlights on a two-lane highway, deep shadows, tired quiet
atmosphere, cinematic documentary, 35mm film grain
```

### 04 · `olho-infravermelho` (seção "O que ele percebe")
- **Proporção:** 4:5, 1600 × 2000 px
- **Onde:** imagem vertical ao lado do texto sobre pupila, piscadas e câmera infravermelha
- **Prompt:**
```
extreme close-up of a human eye photographed with a near-infrared camera, black and white, sharp iris texture,
clearly visible dark pupil, small reflection of a ring of infrared LEDs on the cornea, eyelashes in focus,
clinical yet warm grain, soft vignetting, scientific documentary photograph
```
- **Nota:** foto monocromática de propósito, porque é assim que a câmera IR enxerga.

### 05 · `dispositivo-painel` (seção "Como funciona")
- **Proporção:** 3:2, 2400 × 1600 px
- **Onde:** mostra o aparelho instalado no veículo
- **Prompt:**
```
a small unbranded single-board computer in a matte black case with a tiny camera module mounted high on the
dashboard of a truck near the windshield, facing the driver's seat, neat cable routing, soft early morning
light, dust particles in the air, product documentary photography, realistic, no brand markings, film grain
```

### 06 · `patio-frota` (seção "Para a transportadora")
- **Proporção:** 16:9, 2400 × 1350 px
- **Onde:** abre a parte do painel da empresa
- **Prompt:**
```
aerial drone photograph at dusk of a Brazilian truck yard, rows of parked cargo trucks and trailers seen from
above, red and white reflective tape along the trailer edges catching the last light, long shadows, wet asphalt,
sodium street lamps turning on, calm and orderly, documentary aerial photography, film grain
```

### 07 · `faixa-refletiva` (faixa do capítulo da madrugada)
- **Proporção:** faixa larga, 3000 × 600 px
- **Onde:** faixa horizontal que atravessa a tela na passagem para a noite
- **Prompt:**
```
macro photograph of red and white retroreflective safety tape on the rear bumper of a truck at night,
illuminated by car headlights, glass bead texture visible, alternating red and white segments, slightly dirty
and scratched, deep black background, high contrast, documentary macro
```

### 08 · `rodovia-amanhecer` (capa do contato, 06:00)
- **Proporção:** ultrawide 21:9, 3000 × 1286 px
- **Onde:** fundo do fechamento do site, junto do convite para piloto, pesquisa e investimento
- **Prompt:**
```
wide landscape of a two-lane Brazilian federal highway at dawn, low mist over red earth and pasture, one truck
far away with headlights still on, amber and pale blue sky, reflective road studs glowing on the center line,
quiet hopeful mood, empty space in the upper half, documentary landscape photography, 35mm film grain
```

### 09 · `retrato-parada` (seção "Por quem fazemos isso")
- **Proporção:** 4:5, 1600 × 2000 px
- **Onde:** traz a pessoa por trás da estatística, sem virar foto de banco de imagem
- **Prompt:**
```
candid documentary portrait of a Brazilian truck driver in his fifties at a roadside diner stop at dawn,
holding a small glass of black coffee, looking toward the road and not at the camera, tired but calm
expression, worn cap, truck softly out of focus behind him, warm window light, 35mm film grain, respectful
and real
```
- **Nota:** é pessoa gerada, sem identidade real. Se sair com cara de modelo de propaganda, acrescente
  "weathered skin, natural wrinkles, unposed".

### 10 · `banner-compartilhamento` (imagem que aparece no WhatsApp e no LinkedIn)
- **Proporção:** 1200 × 630 px
- **Onde:** Open Graph; o título entra por código no lado esquerdo
- **Prompt:**
```
minimal composition on cream diagram paper, a single tachograph-style circular chart placed on the right third,
thin graphite radial lines, one continuous amber ink trace spiraling around the disc, generous empty space on
the left two thirds, flat top-down light, subtle paper grain, no text, no numbers
```

---

## Fundos em vídeo (loops curtos)

Para geradores de vídeo como Veo, Kling, Runway ou Sora:
- **Formato:** 1920 × 1080, 24 fps, 6 a 10 segundos.
- **Loop:** o último quadro precisa emendar no primeiro.
- **Áudio:** sem áudio.
- **Uso:** eu comprimo e deixo mudo, com uma imagem parada para quem prefere menos movimento.

### V1 · `video-estrada-noite` (fundo do capítulo da madrugada)
```
seamless loop, dashcam point of view from a truck driving on a dark two-lane highway at night, dashed lane
markings streaming toward the camera, occasional soft bloom of oncoming headlights, gentle road vibration,
reflective road studs passing, deep blacks, subtle film grain, no text, no dashboard overlay, no people
```

### V2 · `video-piscada` (transição do microssono)
```
seamless loop, extreme slow motion close-up of a human eye blinking once, eyelid closing slowly and staying
closed a moment too long before opening again, near-infrared black and white look, fine grain, clinical and
quiet, centered composition, no text
```
- **Nota:** o tempo com o olho fechado é o que conta a história; se ficar rápido demais, peça "eyelid stays closed
  for one full second".

### V3 · `video-amanhecer` (fundo do contato)
```
seamless loop, timelapse of the sky over an empty Brazilian highway changing from deep blue to warm amber at
sunrise, thin mist drifting over the fields, a single distant truck headlight, calm and hopeful, static
tripod shot, subtle film grain, no text
```

### V4 · `video-disco` (alternativa ao disco do topo)
```
seamless loop, macro top-down shot of a paper tachograph disc rotating very slowly while a thin stylus draws a
continuous dark ink line, cream paper, soft morning side light, shallow depth of field, calm mechanical rhythm,
no text, numbers out of focus
```

---

## Depois de gerar

- **O que me mandar:** os arquivos com os nomes acima e, se puder, o nome da ferramenta usada.
- **O que eu faço:**
  - converto para AVIF e WebP, com versões para celular e computador;
  - crio a imagem parada de cada vídeo;
  - confiro o contraste do texto por cima;
  - registro no seu Obsidian (`prompts-de-imagem.md`) os prompts que funcionaram.
