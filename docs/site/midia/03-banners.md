# Banners do site RotaGuard (faixas e Open Graph)

> As regras comuns (luz, lentes, blocos, legal e ética, fluxo no Magnific, aceite e entrega) estão em
> `00-regras-gerais.md`. Cada prompt abaixo traz dentro dele os blocos fixos que usa e pode ser copiado inteiro.

- **Créditos:** estimativas de 11/09/2026. **Conferir o preço no app antes de rodar.**
- **Peças:** B01 (compartilhamento, derivado de fotos aprovadas) · B02 (II→III) · B04 (III.8 contato). A B03 (ponte) ficou
  adiada (`00-regras-gerais.md`, seção 14).

---

### B01 · `og` · Compartilhamento (WhatsApp, LinkedIn)

- **Tipo · status · origem:** banner · a fazer depois das fotos aprovadas · derivado, sem geração nova. Título renderizado
  por código com `next/og`, em PT e EN.
- **Substitui:** nenhuma.
- **Objetivo (5 s, em miniatura de WhatsApp):** "frota de carga" ou "ônibus", conforme a página, e o nome RotaGuard.
- **Persona:** P1 (se informa por LinkedIn e WhatsApp, `docs/site/personas.md:34`) e P2 (recebe o link de um colega).
- **Canal e tamanho:** 1200 × 630 px (serve para LinkedIn, WhatsApp e X). Uma imagem por página e por idioma.
- **Variantes:**

| Variante | Página | Foto de origem | Recorte |
|---|---|---|---|
| `og-inicio` | `/` | S07 dia | Carreta ocupando 40% a 45% da largura da metade da foto |
| `og-carga` | `/carga-e-logistica` | S07 dia | Igual |
| `og-fretamento` | `/fretamento-e-rodoviario` | S08 hora azul (H2) | Ônibus ocupando cerca de 45% da largura da metade da foto |
| `og-urbano` | `/onibus-urbano` | S10 | Ônibus ocupando cerca de 50% da largura da metade da foto |

- **Composição (igual nas quatro):**
  - metade esquerda: painel liso na cor de concreto do site, com o título da página e "RotaGuard" em texto de código;
  - metade direita: recorte apertado da foto;
  - sem véu escuro sobre a foto, porque o título não fica em cima dela.
- **Área do título:** 600 × 630 px à esquerda, com margem de 64 px. Título com no máximo 3 linhas em corpo grande.
- **Leitura em miniatura:** conferir o arquivo reduzido a 300 px de largura (tamanho aproximado do cartão de link no
  celular). O veículo precisa ser reconhecível e o título legível. Se o veículo virar mancha, apertar mais o recorte.
- **Luz:** a da foto de origem (dia ou hora azul). Nada noturno: noite em miniatura vira retângulo preto.
- **Não pode aparecer:** logotipo de terceiro, placa legível, texto dentro da foto, selo "em piloto" (não existe piloto,
  `docs/site/contexto.md:37`).
- **Variações:** PT e EN de cada variante (8 arquivos).
- **Referências:** fotos aprovadas S07, S08 e S10.
- **Fluxo:** sem Magnific.

| Passo | Ferramenta | Configuração | Créditos |
|---|---|---|---|
| 1 | Editor ou script | Recortes de 600 × 630 px a partir dos masters aprovados | 0 |
| 2 | `next/og` (`opengraph-image.tsx` por rota) | Painel de concreto + título do next-intl + recorte | 0 |
| 3 | Conferência | Validador de Open Graph e miniatura a 300 px | 0 |

- **Prompt:** não se aplica (derivado).
- **Aceite específico:** título legível a 300 px; veículo reconhecível; peso abaixo de 300 KB (meta proposta).
- **Legal:** a foto de origem já passou pelo checklist; sem "Imagem ilustrativa" (a imagem de compartilhamento não tem
  espaço de legenda, e as fotos de origem não mostram uso do produto).
- **Arquivo:** gerado em build por rota; os recortes-fonte ficam em `midia/aprovadas/B01-og-<variante>-recorte.png`.
- **Alt PT (og:image:alt), exemplo:** "RotaGuard: sono e celular ao volante em frotas de carga". O texto final sai da
  copy de cada página.
- **Alt EN, example:** "RotaGuard: drowsiness and phone use at the wheel in freight fleets".
- **Registro:** data — · recortes aprovados — · ajustar —

### B02 · `serra-rodovia` · Transição do Ato II para o Ato III

- **Tipo · status · origem:** banner · a gerar · IA (Seedream 5 Pro em 21:9 + Expand para 32:9). Substituir por captação
  real de teleobjetiva numa serra, se houver.
- **Substitui:** foto provisória B02 `serra-rodovia`.
- **Objetivo (5 s):** "a viagem passa por serra, longe de tudo e sem sinal, e o registro continua na caixa até a chegada".
- **Persona:** P1 e P2. Secundária: P3 (conexão, `docs/site/personas.md:75`).
- **Seção e posição:** faixa sangrando entre o fim do Ato II e o começo do Ato III, com uma frase curta. No celular, some
  ou vira recorte 4:5.
- **Composição:**
  - rodovia de pista simples subindo em curvas por uma serra costeira de Mata Atlântica, em dia nublado;
  - neblina baixa nos vales, abaixo da estrada;
  - estrada atravessando o quadro da esquerda para a direita, com barreira de concreto do lado de fora das curvas e rocha
    cortada do lado de dentro;
  - uma carreta de cabine avançada pequena (cerca de 1/20 da largura) numa curva à direita do centro;
  - 40% de cima: neblina se fundindo no céu branco-acinzentado.
- **Área livre para texto:** faixa de cima (neblina e céu), clara (texto escuro).
- **Luz e hora:** H1.
- **Lente e câmera:** 200 mm, f/8, ponto elevado na encosta oposta.
- **Paleta:** verdes escuros apagados, cinza da rocha e do concreto, branco da neblina.
- **Não pode aparecer:**
  - pôr do sol ou luz dourada;
  - "god rays";
  - placa de estrada legível;
  - túnel com nome;
  - mirante turístico;
  - vários veículos;
  - céu azul.
- **Recortes:**
  - computador 32:9 (2560 × 720) a partir do 21:9 expandido;
  - celular 4:5 (1080 × 1350) recortando a curva com a carreta;
  - zona segura: a carreta e a curva entre 45% e 75% da largura e entre 45% e 80% da altura do master 21:9.
- **Variações:** Change Camera só se o recorte 4:5 cortar a curva.
- **Referências:** estilo (âncora).
- **Fluxo no Magnific** (créditos estimados; conferir no app):

| Passo | Ferramenta | Modelo e configuração | Créditos |
|---|---|---|---|
| 1 | Geração no Space | Seedream 5 Pro, 21:9, 2K, 4 tentativas. Alternativa: Nano Banana 2 em 4:1 (75) ou Krea 2 em 2,35:1 (80) | 300 a 320 |
| 2 | Expand | 21:9 → 32:9 para os dois lados. Prompt: "continue the forested slopes, the low fog in the valleys and the even white-grey sky; no new roads, no buildings" | sem preço público |
| 3 | Upscale | Precision photo 2x | 90 |
| — | Total estimado | | cerca de 410 + ferramentas sem preço |

- **Prompt (EN), montado.** Blocos: cena + `H1 v1` + `STYLE v1` + `BRAZIL VEHICLES v1` + `BRAZIL HIGHWAY v1` + `CLEAN v1`.

```
A two-lane Brazilian highway climbs through a steep coastal mountain range covered in dense Atlantic Forest on an overcast day, with low fog resting in the valleys below the road. Photographed from an elevated point on the opposite slope with a 200mm lens at f/8, the road crosses the frame from left to right as a series of curves carved into the hillside, with concrete barriers on the outer edge of each curve and a cut rock face on the inside. A single plain white cab-over truck with a sider trailer climbs a curve right of center, small, about one twentieth of the frame width. The upper 40 percent of the frame is soft fog blending into an even white-grey sky.

Light: overcast late morning, soft diffuse daylight from a uniformly bright white-grey sky, the sun fully hidden behind an even cloud layer, gentle soft-edged shadows, daylight white balance around 5600 K.

Editorial documentary photograph for the annual report of a Brazilian transport company, showing real working conditions in an honest, unglamorous and restrained way. Neutral colors with low-to-medium saturation, moderate contrast and shadows that keep visible detail. Texture comes from the real world: worn seat fabric, scratched plastic, road grime, concrete stains, creased work clothes. Clean modern digital capture with a natural finish, even sharpness and a plain, ungraded look.

Brazilian vehicles: left-hand drive with traffic on the right; European-style cab-over trucks with flat fronts; buses and coaches without company livery; all vehicles in plain white, silver or graphite paint; Mercosur license plates present but too small and angled to read.

Brazilian highway: two lanes with a yellow center line between opposing directions and white edge lines, paved shoulders, metal guardrails and reflective road studs on the center line.

Every sign, screen, label and license plate is free of legible characters: signage is distant and out of focus, plates are too small and angled to read, monitors, laptops and tablets show a uniform dark screen, uniforms and vehicles are plain and unmarked. Hands are relaxed and partly hidden. Every mechanical part is complete and connected, and all shadows and reflections agree with one consistent light direction.
```

- **Aceite específico:**
  - a estrada é contínua (nenhuma curva que não liga a nada);
  - barreiras do lado certo;
  - a carreta está na pista, no sentido plausível;
  - o Expand não criou estrada nova, casa ou antena.
- **Legal:** paisagem genérica, sem marco reconhecível. Legenda "Imagem ilustrativa": não.
- **Arquivo:** `B02-serra-rodovia-h1` → AVIF e WebP em 32:9 e 4:5.
- **Alt PT:** "Rodovia em curvas numa serra coberta de mata, com neblina nos vales e uma carreta subindo."
- **Alt EN:** "A winding highway through a forested mountain range, with fog in the valleys and a truck climbing."
- **Registro:** data — · modelo — · take aprovado — · custo real — · ajustar —

### B04 · `contato-garagem` · III.8 Contato (e quadros de V03)

- **Tipo · status · origem:** banner · a gerar · IA (Seedream 5 Pro). Substituir por captação real de uma garagem parceira.
- **Substitui:** nenhuma (peça nova).
- **Objetivo (5 s):** "no fim do dia, a garagem: é aqui que a gente instala, recolhe a caixa e conversa".
- **Persona:** P2 (ver funcionando na garagem, `docs/site/personas.md:54`) e P3 (piloto numa garagem, `:77`).
- **Seção e posição:**
  - III.8 contato, faixa sangrando em 21:9, versão H2 com os botões de WhatsApp e "Ligar" por cima, na zona escura;
  - as versões H1 e H3, sem a pessoa, são os quadros final e inicial de V03 (III.2, `04-videos.md`). A mesma garagem abre
    e fecha o Ato III.
- **Composição:**
  - portão largo e aberto de uma garagem de ônibus e caminhões, visto de frente a partir do pátio vazio;
  - dentro, sob LED frio, a frente de dois ônibus urbanos e de um caminhão de cabine avançada em sombra suave;
  - uma pessoa de camisa azul-marinho, pequena, parada no vão, olhando o pátio;
  - fachada lisa cinza-escura e céu nos 45% de cima;
  - vão do portão no meio de baixo.
- **Área livre para texto:** 45% de cima (fachada e céu). Escura em H2 e H3 (texto claro), clara em H1.
- **Luz e hora:** master H1. H2 e H3 pelo Relight.
- **Lente e câmera:** 35 mm, f/8, altura de quem está em pé, a cerca de 25 m, de frente.
- **Paleta:** cinza-escuro da fachada, azul-ardósia do céu (H2), branco-frio de dentro, branco dos veículos.
- **Não pode aparecer:**
  - letreiro na fachada;
  - número no portão;
  - logotipo de empresa;
  - letreiro de destino aceso;
  - pôr do sol;
  - poça com reflexo colorido.
- **Recortes (master 3:2, Expand para 21:9 se faltar céu):**
  - computador 21:9 com a faixa de 18% a 82%;
  - celular 9:16 com o portão nos 55% de baixo e o texto no céu;
  - zona segura: o vão do portão entre 31% e 69% da largura e entre 50% e 85% da altura.
- **Variações:**
  - H2 (banner);
  - H3 (quadro inicial de V03);
  - H1 sem pessoa (quadro final de V03);
  - H3 sem pessoa (Retouch).
- **Referências:** estilo (âncora); luz noturna (S01 noite) para o H3.
- **Fluxo no Magnific** (créditos estimados; conferir no app):

| Passo | Ferramenta | Modelo e configuração | Créditos |
|---|---|---|---|
| 1 | Geração no Space | Seedream 5 Pro, 3:2, 2K, 4 tentativas, em H1 | 300 |
| 2 | Expand (se preciso) | 3:2 → 21:9 para cima. Prompt: "continue the plain dark grey facade and the even sky; nothing new" | sem preço público |
| 3 | Relight | H1 → H2 e H1 → H3 (prompts abaixo) | sem preço público |
| 4 | Retouch | Tirar a pessoa das versões H1 e H3 usadas em V03 | sem preço público |
| 5 | Upscale | Precision photo 2x em H1, H2 e H3 | 270 |
| — | Total estimado | | cerca de 570 + ferramentas sem preço |

- **Prompt (EN), montado.** Blocos: cena + `H1 v1` + `STYLE v1` + `BRAZIL VEHICLES v1` + `BRAZIL PEOPLE v1` + `CLEAN v1`.

```
The wide open door of a Brazilian bus and truck garage seen straight on from the empty paved yard outside, photographed with a 35mm lens at f/8 at standing height from about 25 meters. Inside, under cool white LED lights, the flat fronts of two parked plain white city buses and one plain white cab-over truck stand in soft shadow, their destination displays dark. One person in a plain navy work shirt, small in the frame, stands in the doorway looking out toward the yard, relaxed. The garage's plain dark grey facade and the sky above it fill the upper 45 percent of the frame; the door opening sits in the lower middle of the frame, and the yard in front is smooth grey concrete.

Light: overcast late morning, soft diffuse daylight from a uniformly bright white-grey sky, the sun fully hidden behind an even cloud layer, gentle soft-edged shadows, daylight white balance around 5600 K.

Editorial documentary photograph for the annual report of a Brazilian transport company, showing real working conditions in an honest, unglamorous and restrained way. Neutral colors with low-to-medium saturation, moderate contrast and shadows that keep visible detail. Texture comes from the real world: worn seat fabric, scratched plastic, road grime, concrete stains, creased work clothes. Clean modern digital capture with a natural finish, even sharpness and a plain, ungraded look.

Brazilian vehicles: left-hand drive with traffic on the right; European-style cab-over trucks with flat fronts; buses and coaches without company livery; all vehicles in plain white, silver or graphite paint; Mercosur license plates present but too small and angled to read.

Brazilian working adults with real skin texture, pores and fine lines, varied body types, plain work clothes in grey, navy or white without logos or readable badges, natural unposed expressions, attention on their task and away from the photographer.

Every sign, screen, label and license plate is free of legible characters: signage is distant and out of focus, plates are too small and angled to read, monitors, laptops and tablets show a uniform dark screen, uniforms and vehicles are plain and unmarked. Hands are relaxed and partly hidden. Every mechanical part is complete and connected, and all shadows and reflections agree with one consistent light direction.
```

- **Prompt de Relight (EN), para H2:**

```
Blue hour: the sky above the garage becomes an even deep slate blue from top to horizon, the facade turns dark blue-grey, the cool white LED lights inside the garage glow brighter than the yard and spill a soft rectangle of light onto the concrete in front of the door, no warm color anywhere.
```

- **Prompt de Relight (EN), para H3:**

```
Night: the sky above the garage is dark and even, the facade is almost black, the cool white LED lights inside the garage are the main light and spill a clear rectangle of light onto the concrete yard in front of the door; the parked vehicles inside are lit from above; the yard beyond the light is dark.
```

- **Aceite específico:**
  - H1, H2 e H3 com a geometria idêntica (sobrepor a 50%);
  - luz de dentro projetada no piso em H2 e H3;
  - Retouch sem mancha onde estava a pessoa;
  - fachada sem texto.
- **Legal:** garagem genérica, sem logotipo. Legenda "Imagem ilustrativa": não.
- **Arquivo:** `B04-contato-garagem-h1`, `-h2`, `-h3`, `-h1-vazia` e `-h3-vazia` → AVIF e WebP em 21:9 e 9:16. As
  versões vazias vão para `midia/aprovadas/` como quadros de V03.
- **Alt PT:** "Portão aberto de uma garagem de ônibus e caminhões na hora azul, com uma pessoa no vão."
- **Alt EN:** "The open door of a bus and truck garage at blue hour, with a person standing in the doorway."
- **Registro:** data — · modelo — · take aprovado — · custo real — · ajustar —
