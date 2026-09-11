# Rodada de referências: site DriveSafe (11/09/2026)

Feita antes de qualquer código, pela regra do vault (`referencias-de-design.md`): fontes de categorias diferentes,
o que aproveitar, o que descartar e onde cada uma encaixa. Pedido novo do Matheus nesta rodada: **o site deve ter algo
de estradas e mapa-múndi**.

> Referência não é cópia: aproveita-se o princípio (estrutura, ritmo, tratamento), nunca o layout ou a identidade.

## 1. Galeria: sites de logística premiados (Awwwards)

Página da categoria: [Awwwards · logistics](https://www.awwwards.com/inspiration_search/logistics/)

| Site | Prêmio | Aproveitar | Descartar |
|---|---|---|---|
| [Truck'N Roll](https://trucknroll.com/) · [ficha](https://www.awwwards.com/sites/truckn-roll-r) (Locomotive) | Site do dia, 03/06/2026 | Duas cores só (preto e branco), fotografia forte e tipografia de cartaz: seriedade sem enfeite | Rolagem suave de biblioteca como efeito por si só |
| [Madar](https://madarplatform.com/en) · [ficha](https://www.awwwards.com/sites/madar) (Vide Infra) | Site do dia, 19/09/2025 | Plataforma de logística contada como história, com 3D servindo à explicação | Azul-marinho com coral, o par de cores comum de startup |
| [M.V.P. Trans-Logistics](https://mvplogistics.eu/en/main-en/) · [ficha](https://www.awwwards.com/sites/m-v-p-trans-logistics) | Menção honrosa, 06/02/2026 | Foto grande de fundo e vídeo no rodapé para dar escala à operação | Frase de efeito vazia ("we deliver peace of mind") |

## 2. Movimento: rota e mapa comandados pela rolagem

| Fonte | Aproveitar |
|---|---|
| [Codrops · Scroll-driven SVG map animations with GSAP (21/05/2026)](https://tympanus.net/codrops/2026/05/21/creating-scroll-driven-svg-map-animations-with-gsap/) | Mapa em SVG com rota desenhada, pontos de partida e chegada e "câmera" que acompanha a rolagem (ScrollTrigger, DrawSVG e MotionPath). É a base técnica para uma viagem noturna como fio da página |
| [Codrops · Scroll-triggered curved path animations (17/12/2025)](https://tympanus.net/codrops/2025/12/17/building-responsive-scroll-triggered-curved-path-animations-with-gsap/) | Caminho curvo responsivo: a estrada que atravessa seções sem quebrar no celular |
| [Codrops · Cinematic 3D scroll experiences with GSAP (19/11/2025)](https://tympanus.net/codrops/2025/11/19/how-to-build-cinematic-3d-scroll-experiences-with-gsap/) | Sequência de câmera entrando na cabine até o aparelho, no estilo das sequências de quadros do site São Jorge |

## 3. Dados reais para estrada e mapa (fora do web design)

A diferença contra um site genérico: **estrada e mapa desenhados com dado público de verdade, e número com fonte**,
em vez de ilustração de estrada.

| Fonte | O que dá | Licença e uso |
|---|---|---|
| [DNIT · VGeo](http://servicos.dnit.gov.br/vgeo/) e [Sistema Nacional de Viação](https://www.gov.br/dnit/pt-br/assuntos/noticias/dnit-publica-atualizacao-do-sistema-nacional-de-viacao) | Malha real das rodovias federais (SHP, GeoJSON, KML) para desenhar as BRs em SVG | Dado público federal; citar a fonte |
| [PRF · dados abertos](https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dados-abertos-da-prf) | Acidentes nas rodovias federais de 2007 a 2026, por ocorrência, por pessoa e **por causa**. Traz "Condutor Dormindo" e tem dicionário de dados | Dado público; calcular os números e citar ano e fonte na página |
| [Natural Earth](https://www.naturalearthdata.com/about/terms-of-use/) | Mapa-múndi (países, costas, estradas em escala mundial) | **Domínio público**, sem exigência de atribuição |
| [OMS · Relatório global de segurança viária 2023](https://www.onsv.org.br/comunicacao/observatorio-analisa-o-relatorio-da-oms-sobre-a-seguranca-viaria-global-2023) (análise do ONSV) | 1,19 milhão de mortes no trânsito por ano no mundo (dados de 2021) | Número com fonte para o mapa-múndi |

> [!note] Hipótese, confirmar
> Falta baixar a base da PRF e calcular os números por BR e por ano antes de pôr qualquer valor na página.
> Também falta ver se a causa "uso de celular" aparece com esse nome no dicionário de dados.

## 4. Produto: concorrentes (rodada da noite de 10/09, na nota 08 do vault)

[Nauto](https://www.nauto.com/product) · [Samsara câmeras](https://www.samsara.com/products/cameras) ·
[Motive](https://gomotive.com/products/dashcam/) · [Seeing Machines](https://seeingmachines.com/products/fleet/) ·
[Netradyne](https://www.netradyne.com/products/fleet-camera-system) · [Lytx](https://www.lytx.com/drivecam-event-recorder).
Servem para mostrar o espaço do DriveSafe (processa no veículo e não envia vídeo), não para copiar.

## 5. Referência interna: o que já funcionou nos sites do Matheus

- [[site-saojorge]] (`90 - Projetos\site-saojorge.md`):
  - narrativa em 3 atos;
  - sequências de 100 a 150 quadros comandadas pela rolagem;
  - objeto 3D pré-renderizado no Blender;
  - mídia com shot list numerada;
  - tipografia escolhida pela identidade (Marcellus e Alegreya Sans).
- [[site-fornalha-quintal]] (`90 - Projetos\Projetos Analisados\site-fornalha-quintal.md`):
  - capa editorial, com a foto entrando depois do texto;
  - grade assimétrica 7/5;
  - nenhum card;
  - numeração tipográfica no lugar de ícone;
  - movimento só com máscara.
- Os dois diferenciais **não vêm de paleta nem de fonte**: vêm de estrutura, mídia forte e narrativa. É isso que faltou
  na v1 e na v2 do DriveSafe.
