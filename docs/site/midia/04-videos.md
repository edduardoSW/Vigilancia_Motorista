# Vídeos, sequências, turntable e animações em código do site RotaGuard

> As regras comuns (luz, lentes, blocos, caixa canônica, legal e ética, fluxo no Magnific, aceite e entrega) estão em
> `00-regras-gerais.md`. Nos prompts de vídeo os blocos fixos não se repetem: a imagem inicial já carrega a cena e o
> prompt descreve só o movimento (`00-regras-gerais.md`, seção 4.1). Cada prompt pode ser copiado inteiro.

- **Créditos:** estimativas de 11/09/2026. **Conferir o preço no app antes de rodar.**
  - Kling 2.5 a 650 créditos por take de 10 s em 1080p, medido no São Jorge (`SITES E PROJETOS/saojorge/docs/prompts-animacoes.md:23`).
  - MiniMax H3 Max Turbo a 200 créditos por 5 s em 768p (`03-imagens-e-prompts.md:486`).

## Regras comuns de movimento

- **Quatro tipos:**
  - loop (quadro inicial igual ao final);
  - sequência de rolagem (100 a 150 quadros lidos num canvas preso à tela);
  - sequência de arrasto (turntable no Blender);
  - animação em código.
- **Um movimento só.** Ou a câmera fica travada e um único evento de luz acontece, ou há um único movimento de câmera
  extremamente lento. Nunca os dois (`prompts-animacoes.md:11-12`).
- **Só a luz se move** nas cenas de lugar: "o que é luz cresce em opacidade e brilho, nunca se move em x/y"
  (`plano-animacoes.md:25`).
- **Nada acende na caixa.** Nenhum vídeo mostra luz de alerta. O alarme é o som real (A01).
- **Nada de motorista gerado falando, rosto em close ou tela com vídeo de motorista.**
- **Sem som** em todos os vídeos gerados. O único áudio do site é A01, tocado quando a pessoa pede.
- **Teste barato primeiro:** MiniMax H3 Max Turbo, 768p, 5 s, com quadro inicial e final. Só o que passar vai para o
  Kling 2.5.
- **Extração local, sem crédito:** `ffmpeg -i take.mp4 -vf "fps=12,scale=1600:-2" -c:v libwebp -quality 78 frame-%04d.webp`.
  São 12 quadros por segundo × 10 s = 120 quadros. O São Jorge usa 30 fps (`como-entregar-midia.md:26-30`).
- **Loop para a web:**
  `ffmpeg -i take.mp4 -an -c:v libx264 -crf 23 -preset slow -pix_fmt yuv420p -movflags +faststart saida.mp4`.
  Se sobrar um salto na emenda, fundir 12 quadros entre o fim e o começo no editor (filtro `xfade` do ffmpeg).
- **Tetos:** 45 KB por quadro, 6 MB por sequência no computador, 2,5 MB no celular, pôster até 120 KB
  (`plano-animacoes.md:174`).
- **Pista da sequência presa:** 100vh × quadros ÷ 45, como no player do São Jorge (`site-saojorge.md:109-116`). Para 120
  quadros, cerca de 267vh.
- **Celular:** nenhuma sequência prende a rolagem (`04-estrutura-e-conversao.md:289-291`). No celular entra o loop ou a
  foto parada.
- **Movimento reduzido:** toda peça tem pôster ou estado final parado. Loop que toca sozinho tem botão de pausa visível.
- **Rejeitar o take** pelos critérios de `00-regras-gerais.md`, seção 12.2.

**Peças, na ordem do site:** V04 (I.1) · V06 (I.2) · V07 (I.3, opcional) · V08 (II.2) · V01 (II.2 celular) · A01 (II.4) ·
V11 (II.5) · V02 (fretamento, opcional) · V03 (III.2) · V10 (III.2) · V05 (III.7) · V09 (III.7, opcional)

---

### V04 · `terminador-noite` · I.1 Mundo · animação em código

- **Tipo:** animação em código sobre F05 · a fazer · sem crédito.
- **Substitui:** nenhuma.
- **Objetivo · persona · seção:** a noite real passando pelo mundo agora, com o Brasil em destaque · todas · primeira tela
  do Ato I.
- **Quadro inicial e final:** não se aplica. O estado é a hora real do visitante.
- **Movimento:**
  - o véu da noite fica na posição calculada para o momento e é recalculado a cada 60 s. O avanço real, de 0,25° por
    minuto, é imperceptível, e é de propósito;
  - na entrada, o véu cresce de 0 à opacidade final em 800 ms, uma vez;
  - **nada de ciclo acelerado de 24 h:** a noite correndo pela tela vira efeito.
- **Duração · fps · quadros · proporção:** contínuo; um redesenho por minuto; 21:9 no computador e 4:5 no celular.
- **Som:** nenhum.
- **Emenda:** não se aplica.
- **Versão parada:** com movimento reduzido, sem o crescimento de entrada. Sem JavaScript, a reserva de F05 (noite às
  02:00 de Brasília).
- **Tetos:** TopoJSON até 100 KB (meta proposta); nenhum `requestAnimationFrame` contínuo.
- **Fluxo (sem Magnific):**

| Passo | Ferramenta | Configuração |
|---|---|---|
| 1 | Componente de cliente | `d3-geo`: `geoEqualEarth`, ponto subsolar pela hora UTC (declinação e equação do tempo), `geoCircle` de 90° e de 84° no ponto oposto, como no exemplo "Solar Terminator" do d3 (`03-imagens-e-prompts.md:765`) |
| 2 | Temporizador | `setInterval` de 60 s, pausado quando a aba não está visível |
| 3 | Teste | Comparar a faixa com um mapa de dia e noite de referência em três horários |

- **Prompt:** não se aplica.
- **Rejeitar se:** o véu se mover visivelmente; aparecer brilho, ponto ou globo; a faixa discordar da referência.
- **Arquivo e pasta:** componente no site; dados em `public/midia/mapas/F05-mundo-110m.json`.
- **Registro:** fórmula conferida em — · ajustar —

### V06 · `rota-br116-desenho` · I.2 Brasil · animação em código

- **Tipo:** animação em código sobre F01 e F02 · a fazer · sem crédito.
- **Substitui:** nenhuma.
- **Objetivo · persona · seção:** a viagem de demonstração se desenha uma vez, e as horas aparecem ao lado · P1, P4 e P5 ·
  I.2.
- **Quadro inicial e final:** rota vazia → rota desenhada, que fica parada.
- **Movimento:**
  - `stroke-dashoffset` do caminho único de F02, disparado **uma vez** quando a seção entra (não preso ao scrub);
  - 1,6 s com curva de saída suave;
  - depois, as horas da linha do tempo acendem em sequência (opacidade), uma a cada 150 ms;
  - no máximo 3 animações na tela (`site-saojorge.md:58`).
- **Duração · fps · quadros · proporção:** 1,6 s + cerca de 1 s das horas; vetor; 21:9 no computador; no celular, o mapa
  pequeno já desenhado e a linha do tempo vertical.
- **Som:** nenhum.
- **Emenda:** não é loop.
- **Versão parada:** rota desenhada e horas visíveis.
- **Tetos:** um `<path>`; nenhum cálculo por quadro fora da animação.
- **Fluxo (sem Magnific):**

| Passo | Ferramenta | Configuração |
|---|---|---|
| 1 | GSAP + ScrollTrigger | `once: true`, `start: "top 70%"`; animar `strokeDashoffset` do comprimento total até 0 |
| 2 | `gsap.matchMedia` | Com `prefers-reduced-motion: reduce`, pular direto para o estado final |

- **Prompt:** não se aplica.
- **Rejeitar se:** um marcador andar sobre a linha; a câmera acompanhar a rota; a legenda "Viagem de demonstração. O
  RotaGuard não registra localização." sumir.
- **Arquivo e pasta:** componente no site; `public/midia/mapas/F02-rota-br116-demo.svg`.
- **Registro:** ajustar —

### V07 · `loop-rodovia-noite` · I.3 A rodovia · opcional

- **Tipo:** loop · a gerar só se a foto parada de S07 noite parecer "morta" na primeira tela do Ato I · IA (MiniMax H3 ou
  Kling 2.5).
- **Substitui:** nenhuma. É alternativa animada de S07 noite.
- **Objetivo · persona · seção:** "a estrada à noite, com a frota passando" · P1 · I.3.
- **Quadro inicial e final:** o mesmo quadro, S07 noite **sem a carreta** (tirada por Retouch). A estrada começa e termina
  vazia, então a emenda é natural.
- **Movimento:** câmera travada. Uma carreta entra pela direita perto de 1 s, faz a curva em velocidade real e sai pela
  esquerda perto de 8 s. Nada mais se move.
- **Duração · fps · quadros · proporção:** 10 s, 24 fps; 16:9 recortado para 21:9 (Kling) ou 21:9 nativo (MiniMax H3).
- **Som:** desligado.
- **Emenda:** início igual ao fim (estrada vazia).
- **Versão parada:** S07 noite com a carreta.
- **Tetos:** meta proposta de até 4 MB em 21:9 1920 px.
- **Fluxo no Magnific** (créditos estimados; conferir no app):

| Passo | Ferramenta | Modelo e configuração | Créditos |
|---|---|---|---|
| 1 | Retouch | Tirar a carreta de S07 noite (quadro vazio) | sem preço público |
| 2 | Vídeo, teste | MiniMax H3 Max Turbo, 768p, 5 s, 21:9, quadro inicial e final iguais | 200 |
| 3 | Vídeo, final | Kling 2.5, 1080p, 10 s, 16:9, quadro inicial e final iguais, 2 takes | 1.300 |
| — | Total estimado | | cerca de 1.500 + Retouch |

- **Prompt (EN):**

```
Continue this night photograph with a locked-off telephoto camera on an elevated roadside point. The camera does not move. One truck with a long sider trailer enters from the right edge at about one second, its low-beam headlights lighting the asphalt ahead and its small amber marker lamps on, drives along the curve at a steady, realistic speed and leaves through the left edge at about eight seconds. Before it enters and after it leaves, the empty road and the dark landscape stay exactly as in the photograph. No light streaks, no motion trails, no shake, no cuts, no speed changes. Faithful to the starting photograph: same road, same hills, same light.
```

- **Rejeitar se:** a carreta mudar de forma ou de tamanho no meio; aparecer rastro de luz; a faixa central "correr"; a
  paisagem ferver; o último segundo não bater com o primeiro.
- **Arquivo e pasta:** `public/midia/video/V07-loop-rodovia-noite-21x9.mp4` e pôster `V07-loop-rodovia-noite-poster.webp`.
- **Registro:** take aprovado — · custo real — · ajustar —

### V08 · `seq-cabine` (caminhão e ônibus) · II.2 Cabine · sequência de rolagem (computador)

- **Tipo:** sequência de rolagem de 120 quadros, presa na tela · a gerar · IA (Kling 2.5, quadro inicial e final). Duas
  versões com a mesma duração: `caminhao` e `onibus` (`02-direcao-de-arte.md:446-448`).
- **Substitui:** as fotos provisórias S01 e S02 na cena presa. As fotos novas S01 e S02 são o pôster.
- **Objetivo · persona · seção:** a rolagem aproxima o olhar da caixa no painel, à noite, dentro da cabine · P1 e P2 ·
  II.2.
- **Quadro inicial e final:**
  - **inicial:** S01 noite (ou S02 noite), recorte 16:9 do master aprovado, em 1920 × 1080;
  - **final:** recorte de 80% do **mesmo master**, centrado num ponto entre a caixa e o centro do para-brisa, ampliado para
    1920 × 1080 a partir do master de 4K;
  - o modelo vê a caixa idêntica nas duas pontas e só interpola a aproximação.
- **Movimento:**
  - um único avanço de câmera, extremamente lento e constante, como num trilho dentro da cabine;
  - o ombro do motorista sai pela borda esquerda;
  - luz constante; fora do para-brisa, a estrada escura e as lanternas do caminhão da frente ficam estáveis.
  - **Não pode se mexer:** forma da caixa, painel, volante.
- **Duração · fps · quadros · proporção:** take de 10 s → 120 quadros a 12 fps · 1600 × 900.
- **Som:** desligado.
- **Emenda:** não é loop.
- **Versão parada:** S01 noite (ou S02 noite) em 21:9. No celular entra V01.
- **Tetos:** 45 KB por quadro e 6 MB por sequência (quadros noturnos comprimem bem).
- **Fluxo no Magnific** (créditos estimados; conferir no app):

| Passo | Ferramenta | Modelo e configuração | Créditos |
|---|---|---|---|
| 1 | Editor | Preparar o quadro inicial (16:9) e o final (recorte de 80% ampliado) do master aprovado | 0 |
| 2 | Vídeo, teste | MiniMax H3 Max Turbo, 768p, 5 s, quadro inicial e final; 2 testes no caminhão, 1 no ônibus | 600 |
| 3 | Vídeo, final | Kling 2.5, 1080p, 10 s, quadro inicial e final, 2 takes por veículo | 2.600 |
| 4 | Extração local | ffmpeg a 12 fps, 1600 px, WebP q78 | 0 |
| 5 | Curadoria | Quadro a quadro; trocar quadro com artefato pelo vizinho | 0 |
| — | Total estimado | | cerca de 3.200 |

- **Prompt (EN), caminhão:**

```
Continue this night photograph into one single, extremely slow and constant push-in toward the camera box on the dashboard, as if the camera were gliding forward on a rail inside the cab of a truck driving on a dark highway. The driver's shoulder slowly slides out of the left edge of the frame. The dashboard, the steering wheel and the box keep their exact shapes; the box stays dark and nothing on it lights up. Outside the windshield, the dark road and the red tail lamps of the truck far ahead stay steady. The light stays constant. No shake, no cuts, no speed changes. Faithful to the starting photograph and to the ending photograph: same cab, same box, same light. Photorealistic, no text.
```

- **Prompt (EN), ônibus:**

```
Continue this night photograph into one single, extremely slow and constant push-in toward the camera box on the dashboard, as if the camera were gliding forward on a rail inside the driver's area of a coach driving on a dark highway. The driver's shoulder slowly slides out of the left edge of the frame. The wide dashboard, the large steering wheel and the box keep their exact shapes; the box stays dark and nothing on it lights up. Outside the panoramic windshield, the dark road and the red tail lamps of the truck far ahead stay steady. The light stays constant. No shake, no cuts, no speed changes. Faithful to the starting photograph and to the ending photograph: same cab, same box, same light. Photorealistic, no text.
```

- **Rejeitar se:**
  - a caixa mudar de forma, ganhar luz ou "respirar";
  - o volante deformar;
  - a velocidade variar;
  - aparecer faixa tracejada correndo;
  - o motorista virar o rosto para a câmera.
- **Arquivo e pasta:** `public/midia/seq/V08-seq-cabine-caminhao/frame-0001.webp` … e
  `public/midia/seq/V08-seq-cabine-onibus/…`, com `poster.webp` em cada pasta.
- **Registro:** take aprovado (caminhão) — · take aprovado (ônibus) — · custo real — · ajustar —

### V01 · `loop-cabine-farol` (caminhão e ônibus) · II.2 Cabine · loop (celular)

- **Tipo:** loop de 10 s em 9:16 · a gerar · IA (Kling 2.5, quadro inicial igual ao final).
- **Substitui:** S01 e S02 provisórias no celular.
- **Objetivo · persona · seção:**
  - "a caixa não tem luz: você só a vê quando o farol de outro carro passa" · P1, P2 e P5 · II.2 no celular (onde a
    sequência não prende a rolagem);
  - também serve de estado parado da cena no computador antes do scrub, se o layout pedir.
- **Quadro inicial e final:** o mesmo quadro, recorte 9:16 de S01 noite (e de S02 noite) com a caixa e o centro do
  para-brisa, a partir do master de 4K (sem o motorista).
- **Movimento:**
  - câmera travada;
  - um único evento de luz: por volta de 2 s, os faróis de um carro em sentido contrário aparecem ao longe, à esquerda do
    para-brisa, crescem devagar e passam pela esquerda perto de 6 s;
  - a luz branca varre uma vez o painel, o aro do volante e a lateral da caixa, e some;
  - a partir de 8 s, a cabine está exatamente como no começo.
  - **Não pode se mexer:** a câmera, a caixa, o painel.
- **Duração · fps · quadros · proporção:** 10 s, 24 fps, 1080 × 1920.
- **Som:** desligado.
- **Emenda:** início igual ao fim. Se sobrar salto, fundir 12 quadros.
- **Versão parada:** o próprio quadro inicial.
- **Tetos:** meta proposta de até 3 MB por arquivo.
- **Fluxo no Magnific** (créditos estimados; conferir no app):

| Passo | Ferramenta | Modelo e configuração | Créditos |
|---|---|---|---|
| 1 | Editor | Recorte 9:16 de S01 noite e S02 noite, 1080 × 1920 | 0 |
| 2 | Vídeo, teste | MiniMax H3 Max Turbo, 768p, 5 s, quadro inicial igual ao final, 1 por veículo | 400 |
| 3 | Vídeo, final | Kling 2.5, 1080p, 10 s, 9:16, quadro inicial igual ao final, 2 takes por veículo | 2.600 |
| 4 | Exportação | ffmpeg para MP4 H.264 sem áudio | 0 |
| — | Total estimado | | cerca de 3.000 |

- **Prompt (EN):**

```
Continue this night photograph with a locked-off camera inside the cab of a vehicle driving on a dark highway. The camera does not move. One single event of light happens: at about two seconds the headlights of a single oncoming car appear far ahead on the left side of the windshield, grow slowly and pass by on the left at about six seconds; their white light sweeps once across the dashboard, the steering wheel rim and the side of the camera box, then fades away. From eight seconds to the end the cab is back exactly as in the starting photograph and holds still. The box stays dark and never lights up. The road markings stay faint and steady. No shake, no cuts, no speed changes, no lens flare, no light streaks. Faithful to the starting photograph: same cab, same box, same light.
```

- **Rejeitar se:**
  - a caixa brilhar por conta própria;
  - o farol criar estouro de lente ou rastro;
  - as sombras e a mancha de luz se moverem de forma incoerente com a posição do carro que passa;
  - o último segundo não bater com o primeiro.
- **Arquivo e pasta:** `public/midia/video/V01-loop-cabine-farol-caminhao-9x16.mp4` e `…-onibus-9x16.mp4`, com
  `…-poster.webp`.
- **Registro:** take aprovado (caminhão) — · take aprovado (ônibus) — · custo real — · ajustar —

### A01 · `alarme-real` · II.4 O alarme · áudio

- **Tipo:** áudio curto · a fazer · gravação do aparelho ou síntese pelo mesmo padrão do código. Sem Magnific.
- **Substitui:** nenhuma.
- **Objetivo · persona · seção:** a pessoa ouve o alarme de verdade, uma vez, quando aperta "Ouvir o alarme" · P5, P1 e P2
  · II.4, antes de S04 ou S16.
- **Origem honesta:**
  - **Opção 1:** gravar o buzzer ou o alto-falante do protótipo, em sala silenciosa, a 50 cm.
  - **Opção 2:** sintetizar com os mesmos parâmetros do código: 5 ciclos de tons de 2000 Hz e 1000 Hz, 150 ms cada, com
    50 ms de pausa (`vision/alarm.py:18-21`).
  - **Legenda:** "som real do alarme" (opção 1) ou "som gerado com o padrão do alarme do produto" (opção 2).
- **Movimento:** nenhum. Nada pisca na página enquanto o som toca. O botão muda de estado ("tocando").
- **Duração:** cerca de 2 s (5 ciclos, cada um com dois tons de 150 ms e pausas de 50 ms; conferir no arquivo gerado).
- **Som:** é a peça. **Nunca toca sozinho;** só com clique. Volume normalizado com pico de −3 dBFS.
- **Versão parada:** o texto "O alarme é um som alto, na cabine" com a descrição dos tons.
- **Tetos:** MP3 ou OGG até 60 KB (meta proposta).
- **Fluxo:** gravação ou script em Python com os parâmetros de `vision/alarm.py`, exportando WAV → MP3 e OGG. **Nunca gerar
  por IA** (`00-regras-gerais.md`, seção 11).
- **Prompt:** não se aplica.
- **Rejeitar se:** o padrão diferir do código; houver música ou efeito por cima; tocar sem clique.
- **Arquivo e pasta:** `public/midia/audio/A01-alarme-real.mp3` e `.ogg`.
- **Registro:** origem (gravação ou síntese) — · data — · ajustar —

### V11 · `escala-1-1-trechos` · II.5 Escala 1:1 · animação em código

- **Tipo:** animação em código (SVG) · a fazer · sem crédito. **Não existe foto nem vídeo gerado nesta seção.**
- **Substitui:** nenhuma. Substitui a ideia antiga "a imagem não passa daqui".
- **Objetivo · persona · seção:** "a viagem não é filmada inteira; só trechos curtos quando um sinal se repete. O que sai
  inteiro é o registro da viagem" · P5 (medo de ser filmado, `docs/site/personas.md:105-107`), P1 e P4 · II.5, fim do Ato
  II, na escala 1:1 da régua.
- **Desenho:**
  - **escala 1:1:** a curva de abertura do olho (sinal real do produto), em linha grafite fina sobre concreto, com a marca
    do 1 s de olho fechado. Sem foto, sem rosto, sem malha de pontos, sem mira, sem vermelho;
  - **corte (não zoom) para a viagem inteira:** uma barra horizontal de 22:40 a 07:00;
  - **registro:** linha contínua fina de ponta a ponta (o registro da viagem);
  - **trechos gravados:** dois ou três tiques finos, cada um com legenda em HTML, por exemplo "trecho de 20 s: sonolência
    repetida";
  - a proporção real deixa o trecho quase invisível na barra, e é esse o argumento. A legenda soma o total, por exemplo
    "3 trechos, 1 min de 8 h 20 min de viagem".
- **Quadro inicial e final:** curva do olho → barra da viagem com os trechos.
- **Movimento:**
  - a curva se desenha uma vez;
  - corte para a barra;
  - a linha do registro cresce da esquerda para a direita uma vez (1,2 s);
  - os tiques acendem por opacidade.
  - Nada em loop.
- **Duração · fps · proporção:** cerca de 3 s no total, disparado uma vez; vetor; largura total no computador e barra
  vertical no celular.
- **Som:** nenhum (A01 é outra seção).
- **Emenda:** não é loop.
- **Versão parada:** barra completa com os trechos e as legendas.
- **Tetos:** SVG inline pequeno; nenhuma imagem.
- **Fluxo (sem Magnific):** componente com GSAP (`once: true`) e `gsap.matchMedia` para movimento reduzido.
- **Prompt:** não se aplica.

> [!note] Hipótese, confirmar
> Duração dos trechos, o que dispara a gravação ("sonolência frequente por muito tempo"; "sinais compatíveis com uso de
> estimulante") e se o motorista vê os trechos não estão definidos nem implementados. Os números da barra são **exemplo**
> e levam a legenda "exemplo". A palavra "estimulante" só entra no texto se o Matheus decidir citar o módulo
> (`04-estrutura-e-conversao.md:654`), sempre com "não é diagnóstico nem exame de drogas" (`vision/activation.py:1`).

- **Rejeitar se:** aparecer olho fotográfico, rosto ou ícone de câmera filmando; a barra sugerir gravação contínua; faltar a
  legenda "exemplo".
- **Arquivo e pasta:** componente no site; textos no next-intl.
- **Registro:** números usados — · aprovado por — · ajustar —

### V02 · `loop-chuva-parado` · `/fretamento-e-rodoviario` · opcional

- **Tipo:** loop de 10 s · a gerar só com saldo sobrando · IA (quadro novo em Nano Banana Pro + Kling 2.5).
- **Substitui:** nenhuma.
- **Objetivo · persona · seção:** "a caixa fica no ônibus parado no pátio, noite de chuva, sem acender nada" · P2 · topo ou
  meio de `/fretamento-e-rodoviario`.
- **Quadro inicial e final:** o mesmo quadro, gerado a partir de S02 noite como referência de imagem: ônibus **parado** no
  pátio da garagem, vista do posto do motorista para o para-brisa com gotas, limpadores parados, caixa no painel.
- **Movimento:** câmera travada. Um único evento contínuo: gotas caem e escorrem pelo vidro, refratando os LEDs do pátio.
  Luz constante.
- **Duração · fps · quadros · proporção:** 10 s, 24 fps, 16:9 (computador) e recorte 9:16 do mesmo take (celular).
- **Som:** desligado.
- **Emenda:** início igual ao fim; fusão de 12 quadros se preciso.
- **Versão parada:** o quadro inicial.
- **Tetos:** meta proposta de até 4 MB em 16:9.
- **Fluxo no Magnific** (créditos estimados; conferir no app):

| Passo | Ferramenta | Modelo e configuração | Créditos |
|---|---|---|---|
| 1 | Geração do quadro | Nano Banana Pro, 16:9, referência de imagem (S02 noite) e de produto (S15), 2 tentativas, prompt do quadro abaixo | 300 |
| 2 | Vídeo, teste | MiniMax H3 Max Turbo, 768p, 5 s, inicial igual ao final | 200 |
| 3 | Vídeo, final | Kling 2.5, 1080p, 10 s, inicial igual ao final, 2 takes | 1.300 |
| — | Total estimado | | cerca de 1.800 |

- **Prompt do quadro (EN), montado.** Blocos: cena + `DEVICE DASH v1` + `DEVICE NIGHT 940 v1` + `H3 v1` + `STYLE v1` +
  `CLEAN v1`.

```
Inside the driver's area of an intercity coach parked in a Brazilian garage yard on a rainy night, photographed from just behind and to the right of the empty driver's seat at shoulder height with a 32mm lens at f/5.6, looking forward. The wide dashboard fills the lower third of the frame and the camera box described below sits on top of it, just to the right of the steering wheel, near the center of the frame. Raindrops cover the large panoramic windshield; the wipers rest still at the bottom of the glass. Outside, blurred by the wet glass, tall cool white LED lamps light the yard and the flat fronts of two other parked coaches. The engine is off and the instrument cluster is dark.

The driver-facing camera box: a compact unbranded box about 110 x 72 x 40 mm, slightly larger than a deck of playing cards, with a dark graphite anodized aluminum body whose top is shaped into fine parallel cooling fins and softly rounded 3 mm edges. The face pointing at the driver is a flat dark glass window with one small round camera lens; the infrared emitters sit hidden behind the same glass and look black. The box rests in a slim matte black cradle fixed to the top of the dashboard, just to the right of the steering wheel rim, within about 20 degrees of the driver's straight-ahead line and below the driver's view of the road, tilted up toward the driver's face. One thin black cable runs from the cradle along the dashboard seam and disappears under the trim. All its surfaces are plain, with no screen, buttons, indicator light, printing or logo, and nothing on it lights up.

At night the box stays completely dark and is visible only where light from the scene touches it.

Light: night lit only by sources that exist in the scene, such as cool white LED lamps around 4000 K, vehicle headlights, small amber marker lamps and dim instrument backlight; every source casts matching light and reflections on nearby surfaces; deep shadows that still hold detail; clean, clear air.

Editorial documentary photograph for the annual report of a Brazilian transport company, showing real working conditions in an honest, unglamorous and restrained way. Neutral colors with low-to-medium saturation, moderate contrast and shadows that keep visible detail. Texture comes from the real world: worn seat fabric, scratched plastic, road grime, concrete stains, creased work clothes. Clean modern digital capture with a natural finish, even sharpness and a plain, ungraded look.

Every sign, screen, label and license plate is free of legible characters: signage is distant and out of focus, plates are too small and angled to read, monitors, laptops and tablets show a uniform dark screen, uniforms and vehicles are plain and unmarked. Hands are relaxed and partly hidden. Every mechanical part is complete and connected, and all shadows and reflections agree with one consistent light direction.
```

- **Prompt do vídeo (EN):**

```
Continue this night photograph with a locked-off camera from the driver's area of a coach parked in a garage yard. The coach does not move and the wipers stay still. Rain falls steadily: drops land on the windshield and run down the glass in slow, irregular paths, softly refracting the cool white yard lamps outside. The camera box on the dashboard stays dark and does not change. The light stays constant. The last second matches the first. No shake, no cuts, no speed changes, no lightning, no colored reflections. Faithful to the starting photograph: same dashboard, same box, same yard.
```

- **Rejeitar se:** a chuva virar "neon"; os limpadores se moverem; a caixa brilhar; as gotas subirem; a emenda saltar.
- **Arquivo e pasta:** `public/midia/video/V02-loop-chuva-parado-16x9.mp4`, `…-9x16.mp4` e pôster.
- **Registro:** take aprovado — · custo real — · ajustar —

### V03 · `seq-garagem-noite-manha` · III.2 A chegada · sequência de rolagem (computador)

- **Tipo:** sequência de rolagem de 120 quadros, presa na tela · a gerar · IA (Relight para os quadros + Kling 2.5).
- **Substitui:** nenhuma.
- **Objetivo · persona · seção:**
  - "a viagem acaba; de manhã a frota volta à garagem, e é hora de recolher a caixa";
  - abre o novo fluxo principal (chegada → recolhimento → registro);
  - P1, P2 e P3 · III.2, antes de S17.
- **Quadro inicial e final:**
  - **inicial:** B04 em H3 **sem a pessoa**;
  - **final:** B04 em H1 **sem a pessoa**;
  - mesma geometria, porque os dois saem do mesmo master pelo Relight (`03-banners.md`, B04).
- **Movimento:**
  - câmera travada; só a luz muda: o céu vai do preto ao branco-acinzentado nublado, a fachada e o pátio ganham luz de dia
    suave, e perto de 7 s os LEDs de dentro da garagem se apagam juntos;
  - veículos parados; ninguém entra no quadro;
  - **sem sol e sem cor quente,** para não virar amanhecer de cartão-postal.
- **Duração · fps · quadros · proporção:** take de 10 s → 120 quadros a 12 fps · 1600 × 900 (recorte do 16:9).
- **Som:** desligado.
- **Emenda:** não é loop.
- **Versão parada:** B04 H1 (manhã). No celular, a mesma foto parada, sem prender a rolagem.
- **Tetos:** 45 KB por quadro e 6 MB no computador.
- **Fluxo no Magnific** (créditos estimados; conferir no app):

| Passo | Ferramenta | Modelo e configuração | Créditos |
|---|---|---|---|
| 1 | Retouch | Tirar a pessoa de B04 H1 e de B04 H3 | sem preço público |
| 2 | Vídeo, teste | MiniMax H3 Max Turbo, 768p, 5 s, inicial H3 e final H1 | 200 |
| 3 | Vídeo, final | Kling 2.5, 1080p, 10 s, inicial H3 e final H1, 2 takes | 1.300 |
| 4 | Extração local | ffmpeg a 12 fps, 1600 px, WebP q78 | 0 |
| — | Total estimado | | cerca de 1.500 + Retouch |

- **Prompt (EN):**

```
Continue this photograph with a locked-off camera: the same garage and yard, seen from exactly the same point, move from night to an overcast morning. Only the light changes. The sky slowly turns from black to an even white-grey, the facade and the concrete yard gain soft, shadowless daylight, and at about seven seconds the white LED lights inside the garage switch off together. The parked buses and truck do not move and nobody enters the frame. No sun, no warm colors, no shake, no cuts, no speed changes. Faithful to the starting photograph and to the ending photograph: same buildings, same vehicles, same framing.
```

- **Rejeitar se:** qualquer veículo ou objeto mudar de lugar; aparecer sol, laranja ou rosa no céu; a fachada "respirar";
  os LEDs piscarem mais de uma vez.
- **Arquivo e pasta:** `public/midia/seq/V03-seq-garagem-noite-manha/frame-0001.webp` … e `poster.webp`.
- **Registro:** take aprovado — · custo real — · ajustar —

### V10 · `caixa-sai-do-suporte` · III.2 A chegada · sequência de rolagem (Blender)

- **Tipo:** sequência de rolagem de 90 quadros · a fazer depois de o berço ser desenhado · Blender, sem crédito.
- **Substitui:** nenhuma.
- **Objetivo · persona · seção:** "a caixa sai do suporte sem ferramenta e vai para o escritório" · P1, P2 e P3 · III.2,
  entre V03 e S17 (ou lado a lado com S17 na grade).
- **Quadro inicial e final:** caixa no berço sobre um trecho de painel simplificado → caixa erguida 6 cm acima do berço,
  com o cabo ficando no berço.
- **Movimento:**
  - um único movimento: a caixa sobe e se afasta do berço;
  - câmera parada em 3/4, 50 mm;
  - luz de estúdio neutra, fundo na cor da seção;
  - sem mão (evita mão genérica de 3D).
- **Duração · fps · quadros · proporção:** 90 quadros · 1600 × 1200 no computador · no celular, dois quadros parados (no
  berço e fora dele).
- **Som:** nenhum.
- **Emenda:** não é loop.
- **Versão parada:** o último quadro.
- **Tetos:** 45 KB por quadro e 4 MB no total (meta proposta).
- **Fluxo (Blender):** mesmo arquivo de S15; animação por keyframes com easing suave no começo e no fim; render em
  segundo plano (`blender -b caixa-v1.blend -a`, erro 70).
- **Prompt:** não se aplica.

> [!note] Hipótese, confirmar
> O jeito de encaixar e soltar (trava, ímã, trilho) e onde o cabo se conecta não estão decididos. A peça só é feita quando
> o Matheus aprovar o desenho do berço.

- **Rejeitar se:** o movimento sugerir mecanismo que não existe; aparecer luz na caixa; a caixa atravessar o berço.
- **Arquivo e pasta:** `public/midia/seq/V10-caixa-sai-do-suporte/frame-0001.webp` … e `poster.webp`.
- **Registro:** versão do modelo — · ajustar —

### V05 · `turntable-caixa` · III.7 Ficha técnica · sequência de arrasto (Blender)

- **Tipo:** sequência de arrasto de 120 quadros (3° por quadro) · a fazer depois de S15 aprovado · Blender, sem crédito.
  Mesma escolha do São Jorge: render prévio, sem 3D rodando no navegador (`site-saojorge.md:37`).
- **Substitui:** a foto provisória S15 `raspberry-pi-camera`, como mídia interativa da ficha técnica.
- **Objetivo · persona · seção:** a pessoa gira a caixa com o dedo e vê todos os lados · P1 e P4 · III.7, ao lado da lista
  com fios.
- **Quadro inicial e final:** frente em 3/4 → volta completa de 360°.
- **Movimento:**
  - a caixa gira no próprio eixo; câmera fixa a 15° de elevação, 50 mm;
  - controlado pelo arrasto (ponteiro) com inércia leve e pelas setas do teclado, como o turntable do São Jorge
    (`plano-animacoes.md:98-101`).
- **Duração · fps · quadros · proporção:** 120 quadros · 1600 × 1200 (4:3) no computador e 1080 × 1080 no celular.
- **Som:** nenhum.
- **Emenda:** o quadro 120 emenda no 1 (volta completa).
- **Versão parada:** as vistas de S15 (frente, 3/4, lateral, traseira).
- **Tetos:** 45 KB por quadro e 6 MB no computador.
- **Fluxo (Blender):**

| Passo | Ferramenta | Configuração | Créditos |
|---|---|---|---|
| 1 | Blender | Arquivo de S15; rotação de 360° em Z em 120 quadros, interpolação linear | 0 |
| 2 | Luz | Três softboxes neutras; fundo na cor exata do token da seção; sombra de contato | 0 |
| 3 | Render | Cycles com denoise, 1600 × 1200, PNG, por `blender -b caixa-v1.blend -a` | 0 |
| 4 | Conversão | `ffmpeg` ou `cwebp` para WebP q80 | 0 |

- **Prompt:** não se aplica.
- **Rejeitar se:** o reflexo da janela "piscar" entre quadros; a sombra pular; aparecer qualquer marca; as medidas não
  baterem com a ficha.
- **Arquivo e pasta:** `public/midia/seq/V05-turntable-caixa/frame-0001.webp` … e `poster.webp`.
- **Registro:** versão do modelo — · peso final — · ajustar —

### V09 · `explodida-caixa` · III.7 Ficha técnica · opcional, depende de decisão

- **Tipo:** sequência de rolagem de 100 quadros · só se o Matheus decidir mostrar a placa por dentro · Blender, sem
  crédito.
- **Substitui:** nenhuma.
- **Objetivo · persona · seção:** "é isto que tem dentro: placa, câmera infravermelha, som, conector" · P1 e P4
  (equipamento conhecido e substituível) · III.7.
- **Risco para a mensagem:** "roda em Raspberry Pi" pode soar como projeto de bancada para quem compara com
  videotelemetria (`04-estrutura-e-conversao.md:46-47`). Por isso depende de decisão.
- **Quadro inicial e final:** caixa fechada → tampa e peças afastadas em camadas, com rótulos em HTML.
- **Movimento:** um único movimento de separação, preso ao scrub; câmera fixa em 3/4.
- **Duração · fps · quadros · proporção:** 100 quadros · 1600 × 1200.
- **Som:** nenhum.
- **Emenda:** não é loop.
- **Versão parada:** o último quadro com os rótulos.
- **Tetos:** 45 KB por quadro e 5 MB no total (meta proposta).
- **Fluxo (Blender):** mesmo arquivo de S15, com as peças internas já modeladas em tamanho real (erro 71); render em segundo
  plano.
- **Prompt:** não se aplica.

> [!note] Hipótese, confirmar
> Placa (Pi 4 de 4 GB provável), módulo de câmera, iluminador e som não estão decididos. Enquanto forem hipótese, a
> legenda é "protótipo em definição" e nenhum rótulo cita modelo comercial.

- **Rejeitar se:** aparecer peça que não existe no protótipo; aparecer marca legível em chip ou conector.
- **Arquivo e pasta:** `public/midia/seq/V09-explodida-caixa/frame-0001.webp` … e `poster.webp`.
- **Registro:** decisão do Matheus — · versão do modelo — · ajustar —