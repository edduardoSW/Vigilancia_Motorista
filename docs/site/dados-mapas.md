# Dados de mapa do site RotaGuard

Escrito em 11/09/2026. Arquivos finais em `site/src/data/mapas/`, gerados pelos scripts de `site/scripts/mapas/`.
Nenhuma geometria foi desenhada à mão nem gerada por IA: tudo sai de dado público baixado da fonte, e cada
simplificação está descrita abaixo.

> **Regra de honestidade.** O RotaGuard não registra localização (não tem GPS). Os mapas são contexto. A rota é uma
> viagem de demonstração e aparece sempre com a legenda "Rota ilustrativa" (EN: "Illustrative route"). Nada de pino de
> veículo, pino de evento ou "frota ao vivo no mapa". O próprio arquivo da rota traz esse aviso em `metadados.conteudo`.

## Resumo

| Arquivo | Conteúdo | Fonte e data do dado | Licença | Tamanho |
|---|---|---|---|---|
| `mundo.topo.json` | 177 países (objeto `paises`) | Natural Earth 1:110m, versão 5.1.1 (maio de 2022) | Domínio público | 113.963 bytes (111,3 KB) |
| `brasil-ufs.topo.json` | 27 UFs (`ufs`) e contorno do Brasil (`brasil`) | IBGE, malha territorial 2022, API de malhas v3 | Dado aberto federal, creditando a fonte | 147.817 bytes (144,4 KB) |
| `rodovias-federais.topo.json` | Malha federal existente, 147 BRs (`rodovias`) | DNIT, Sistema Nacional de Viação, versão 202607A (julho de 2026) | Dado público federal, creditando a fonte (ver ressalva) | 296.888 bytes (289,9 KB) |
| `rota-br116-sp-curitiba.json` | BR-116 de São Paulo a Curitiba e 5 pontos de referência | DNIT, SNV 202607A; posições conferidas com a malha municipal do IBGE 2022 | Igual à linha acima | 19.669 bytes (19,2 KB) |

- Data de acesso de todas as fontes: **11/09/2026**.
- Coordenadas em `[longitude, latitude]`. O IBGE e o DNIT publicam em SIRGAS 2000; segundo a nota técnica do IBGE sobre o
  fim da transição para o SIRGAS2000 (item 2.2), "WGS 84 e SIRGAS2000 são considerados idênticos para fins práticos, não
  existindo parâmetros de transformação entre eles". Por isso não houve transformação de datum.
- Anéis de polígono no sentido que o `d3-geo` espera (conferido com `d3.geoArea` no `d3-geo` 3.1.1 instalado no site).
- Cada arquivo leva um membro `metadados` com fonte, URL, versão, licença, atribuição e processamento. `topojson-client`
  e `d3-geo` ignoram esse membro.

**Números que o site pode citar, com fonte:**

- Malha rodoviária federal existente: **74.829,3 km**, dos quais **67.140,3 km pavimentados** (DNIT, SNV 202607A,
  julho de 2026; soma da extensão do SNV sem trechos planejados, sem travessias e contando uma vez os trechos
  coincidentes). Ver a comparação com a série oficial do DNIT na seção 3 antes de publicar.
- Rota de demonstração: **405,4 km** pela BR-116, da divisa de São Paulo com Taboão da Serra até a BR-116 dentro de
  Curitiba (medido na geometria do SNV 202607A).

## Atribuição (texto exato para o rodapé)

IBGE e DNIT: creditar a fonte (Decreto 8.777/2016, art. 2º, III). Natural Earth: crédito não exigido, incluído por
transparência.

**Português**

> Mapas: Natural Earth. Divisas estaduais: IBGE, malha territorial 2022. Rodovias federais e rota: DNIT, Sistema Nacional de Viação (SNV 202607A). Geometrias simplificadas.

**English**

> Maps: Natural Earth. State boundaries: IBGE, 2022 territorial mesh. Federal highways and route: DNIT, Brazilian National Road System (SNV 202607A). Simplified geometry.

**Junto da rota** (legenda da peça, não só no rodapé):

> Rota ilustrativa · BR-116, dados do DNIT (SNV 202607A)
>
> Illustrative route · BR-116, DNIT data (SNV 202607A)

Nenhum dado do OpenStreetMap foi usado, então o crédito "© OpenStreetMap contributors" não se aplica. Se um dia a fonte
for trocada por OSM, esse crédito passa a ser obrigatório (licença ODbL).

## Como gerar de novo

Na pasta `site/`:

```bash
npm run mapas                              # o mesmo que: node scripts/mapas/gerar-mapas.mjs
node scripts/mapas/conferir-mapas.mjs      # checagens e teste visual
```

Opções do gerador:

- `--atualizar`: baixa tudo de novo, ignorando o cache.
- `--so=mundo,brasil,rodovias,rota`: roda só os passos listados.

Requisitos e comportamento:

- Node 20.9 ou mais novo (o mesmo do site) e internet na primeira execução. Baixa cerca de 70 MB para
  `site/scripts/mapas/.cache/`, que não vai para o git (`site/scripts/mapas/.gitignore`) e já é ignorado pelo ESLint do
  site. Leva cerca de 30 s com o cache vazio.
- O mapshaper roda por `npx --yes mapshaper@0.7.61` (última estável no npm em 11/09/2026; `npm view mapshaper dist-tags`
  deu `latest: 0.7.61`). Nada foi instalado globalmente e nada foi acrescentado ao `site/package.json`.
- `acessado_em` nos metadados é a data em que o arquivo entrou no cache.
- A saída é determinística: duas execuções em pastas diferentes geraram arquivos idênticos byte a byte (11/09/2026).
- O gerador para com erro se algo mudar na fonte: contagem de UFs, versão do SNV, nome dos nós de início e fim da rota,
  buraco de mais de 1 m entre trechos, autointerseção, ou ponto de referência fora do município esperado.
- Para trocar a versão do SNV: mudar `SNV_VERSAO` em `gerar-mapas.mjs` para o nome de um arquivo existente na pasta
  "SNV Bases Geométricas (2013-Atual) (SHP)" do compartilhamento do DNIT e rodar com `--atualizar`.

| Script | Função |
|---|---|
| `gerar-mapas.mjs` | Baixa, filtra, simplifica e grava os quatro arquivos; grava `.cache/relatorio.json` com contagens e extensões |
| `conferir-mapas.mjs` | Contagens, bbox, propriedades, tamanhos, sentido dos anéis, continuidade da rota; desenha `.cache/teste.svg` e `.cache/teste.png` |
| `lib/arquivos.mjs` | Leitura de ZIP, `.shp` de linhas e `.dbf`, sem dependências |
| `lib/geodesia.mjs` | Distância de Vincenty no elipsoide WGS 84, Douglas-Peucker em metros, ponto em polígono, autointerseção |
| `lib/topojson.mjs` | Decodificador mínimo de TopoJSON usado na conferência |
| `lib/util.mjs` | Download com cache e novas tentativas; chamada do mapshaper por `npx` sem shell |

O PNG do teste sai pelo ImageMagick quando ele está no PATH (aqui, 7.1.2 com librsvg 2.40). O `@resvg/resvg-js` 2.6.2
aborta com erro interno do Rust neste SVG, por isso só é tentado depois, num processo separado.

## 1. `mundo.topo.json`

| Item | Valor |
|---|---|
| Fonte | Natural Earth, Admin 0 – Countries, escala 1:110m |
| Página | https://www.naturalearthdata.com/downloads/110m-cultural-vectors/110m-admin-0-countries/ |
| Download | https://naciscdn.org/naturalearth/110m/cultural/ne_110m_admin_0_countries.zip (214.976 bytes) |
| Data do dado | Versão 5.1.1, segundo o `VERSION.txt` do pacote; arquivos de maio de 2022. A última release no GitHub é a v5.1.2, de 13/05/2022 |
| Licença | Domínio público. Termos (https://www.naturalearthdata.com/about/terms-of-use/): "All versions of Natural Earth raster + vector map data found on this website are in the public domain." "No permission is needed to use Natural Earth." "Crediting the authors is unnecessary." Crédito sugerido por eles: "Made with Natural Earth." |
| Fronteiras | Visão padrão do Natural Earth: "Natural Earth shows de facto boundaries by default according to who controls the territory, versus de jure" (página de download) |
| Simplificação | Nenhuma além da própria escala 1:110m |
| Processamento | `NAME_PT` → `nome`, `NAME` → `nome_en`, `ADM0_A3` → `codigo`, `ISO_N3_EH` → `id` da geometria; TopoJSON com quantização 100.000 (grade de 0,0036° × 0,0017°, cerca de 400 m × 190 m no equador) |
| Resultado | 177 feições, 598 arcos, 8.294 vértices; bbox −180, −90, 180, 83,645 |

- `id` é o código ISO 3166-1 numérico em texto de 3 dígitos (`"076"` = Brasil), a mesma convenção do pacote
  `world-atlas`. Vem de `ISO_N3_EH` porque `ISO_N3` é `-99` para França e Noruega. Kosovo, Chipre do Norte e
  Somalilândia não têm código ISO e ficam sem `id` (174 de 177 têm).
- `codigo` usa `ADM0_A3` pelo mesmo motivo (`ISO_A3` é `-99` para França e Noruega). Para quase todos os países coincide
  com o ISO 3166-1 alfa-3; Kosovo (`KOS`), Chipre do Norte (`CYN`) e Somalilândia (`SOL`) têm códigos próprios do
  Natural Earth.

## 2. `brasil-ufs.topo.json`

| Item | Valor |
|---|---|
| Fonte | IBGE, API de malhas v3 (documentação: https://servicodados.ibge.gov.br/api/docs/malhas?versao=3) |
| Download | https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR?formato=application/vnd.geo%2Bjson&qualidade=maxima&intrarregiao=UF&periodo=2022 (1.001.279 bytes) |
| Siglas e nomes | https://servicodados.ibge.gov.br/api/v1/localidades/estados (a API de malhas só traz o código `codarea`) |
| Data do dado | Malha territorial **2022**. É o que a API devolve sem `periodo`; com `periodo=2023` a `2026` ela respondeu HTTP 500 em 11/09/2026. O período ficou fixado em 2022 no script para a saída não mudar sozinha |
| Licença | Dado aberto federal. O Decreto 8.777/2016, art. 2º, III, define dados abertos como "disponibilizados sob licença aberta que permita sua livre utilização, consumo ou cruzamento, limitando-se a creditar a autoria ou a fonte". Não achei termo de uso específico da API de malhas (a página "Termos de Uso" do IBGE só lista termos de serviços como certidões e sala de dados restritos) |
| Simplificação | Douglas-Peucker com tolerância de **500 m** (`-simplify dp interval=500m keep-shapes`, mapshaper 0.7.61, cálculo esférico). De 51.987 para 16.510 vértices. O contorno `brasil` foi feito por dissolve das UFs e usa só arcos das UFs, então divisa e contorno coincidem |
| Quantização | 50.000 (grade de 0,00089° × 0,00078°, cerca de 99 m × 87 m) |
| Propriedades de `ufs` | `sigla` ("SP"), `nome` ("São Paulo"), `codigo_ibge` (35), `regiao` ("Sudeste") |
| Resultado | 27 UFs e 1 contorno (MultiPolygon), 148 arcos; bbox −73,990, −33,748, −29,299, 5,272 |

Ilhas oceânicas: o arquivo mantém Fernando de Noronha (PE, perto de −32,43; −3,86) e Trindade (ES, perto de −29,32;
−20,51). Por isso o bbox vai até −29,3 de longitude. Sem essas ilhas, o limite leste é −34,793 (Ponta do Seixas). Se
um `fitExtent` com o contorno inteiro deixar oceano demais à direita, ajuste a projeção a esse recorte continental. O
arquivo da API não traz o arquipélago de São Pedro e São Paulo nem Martim Vaz.

A qualidade "máxima" da API já é uma malha generalizada pelo IBGE (51.987 vértices para o país inteiro); a
documentação da API não informa a tolerância dessa generalização.

> [!note] Hipótese, confirmar
> A malha de UFs de 2025 existe no FTP do IBGE (`BR_UF_2025.zip`, 14.814.182 bytes, de 26/02/2026:
> https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_municipais/municipio_2025/Brasil/BR_UF_2025.zip).
> Não foi usada porque a preferência era a API. Com 500 m de simplificação, não espero diferença visível entre 2022 e
> 2025, mas não comparei.

> [!note] Hipótese, confirmar
> Que a malha da API de malhas está coberta pela política de dados abertos com exigência só de crédito. Não há licença
> escrita na API. Para ter certeza, perguntar ao IBGE pelo Fala.BR.

## 3. `rodovias-federais.topo.json`

| Item | Valor |
|---|---|
| Fonte | DNIT, Sistema Nacional de Viação (SNV), base geométrica em shapefile |
| Página | https://www.gov.br/dnit/pt-br/assuntos/atlas-e-mapas/pnv-e-snv |
| Onde está o arquivo | Compartilhamento público do DNIT https://servicos.dnit.gov.br/dnitcloud/index.php/s/oTpPRmYs5AAdiNr, pasta "SNV Bases Geométricas (2013-Atual) (SHP)", arquivo `202607A.zip` (68.515.469 bytes, modificado em 27/07/2026) |
| Download direto | https://servicos.dnit.gov.br/dnitcloud/index.php/s/oTpPRmYs5AAdiNr/download?path=%2FSNV%20Bases%20Geom%C3%A9tricas%20(2013-Atual)%20(SHP)&files=202607A.zip |
| Data do dado | SNV versão **202607A** (campo `versao_snv` de todos os registros). A página "PNV e SNV" do DNIT informava atualização em 28/07/2026 |
| Dicionário de dados | https://servicos.dnit.gov.br/dadosabertos/dataset/fb78d7a5-3883-4ce8-a29e-7bcc8cf1c8c7/resource/51661b5f-f1ee-41a7-8dac-fa093a27a321/download/dicionario-de-dados-snv.pdf |
| Licença | Ver ressalva abaixo |

**Troca de fonte:** não houve. O DNIT respondeu e a base oficial foi usada. O VGeo não foi necessário, porque o mesmo
SNV completo está no compartilhamento acima.

**Filtro** (campo `ds_sup_fed`, "situação física" no dicionário do DNIT):

| Situação no SNV | Entra? | Registros | Extensão SNV (km) |
|---|---|---|---|
| `PLA` planejada | Não | 2.317 | 48.871,7 |
| `TRV` travessia (trechos sobre rios e lagoas, como "INÍCIO TRAVESSIA RIO ARAGUAIA → FIM TRAVESSIA") | Não | 27 | 153,9 |
| `DUP`, `PAV`, `IMP`, `LEN` | Sim | 5.329 (com coincidentes) | ver tabela de extensão |

Dos 2.317 registros planejados, 719 (21.426,0 km) não têm rodovia estadual coincidente, e 1.464 (24.150,8 km) coincidem
com rodovia estadual, municipal ou distrital pavimentada ou duplicada: a estrada existe, mas não como BR. Todos saem,
porque o SNV não os trata como rodovia federal existente. Todos os registros incluídos, coincidentes ou não, têm
jurisdição federal (`ds_jurisdi`).

**Propriedades:** `br` com três dígitos, como no SNV ("116", "010"), e `situacao`:

| `situacao` | Código SNV | Registros | Extensão SNV (km) | Medida na geometria (km) |
|---|---|---|---|---|
| `duplicada` | DUP | 956 | 7.522,7 | 7.485,1 |
| `pavimentada` | PAV | 3.332 | 59.617,6 | 59.511,3 |
| `implantada` | IMP | 253 | 5.774,5 | 5.721,5 |
| `leito_natural` | LEN | 57 | 1.914,5 | 1.979,1 |
| **Total incluído** | | **4.598** | **74.829,3** | **74.697,0** |

- Pavimentada (DUP + PAV): **67.140,3 km**. Não pavimentada (IMP + LEN): **7.689,0 km**.
- "Extensão SNV" é a soma do campo `vl_extensa`. "Medida na geometria" é o comprimento geodésico (Vincenty, WGS 84) da
  geometria original, antes da simplificação.
- Data do dado: SNV 202607A. Data do cálculo: 11/09/2026.

**Trechos coincidentes.** Quando duas BRs usam a mesma estrada, o SNV repete o trecho em cada uma e marca a cópia com
`desc_coinc = "Coinc"`. A geometria das duas cópias é idêntica (conferido, por exemplo, em `116BSP2590` e
`101BSP3645`). No arquivo, o trecho aparece nas duas BRs e as duas usam os mesmos arcos TopoJSON; na soma de extensão ele
conta uma vez só, pelo registro principal (`desc_coinc = "-"`). São 731 registros coincidentes (7.835,8 km) desenhados
sem somar.

**Simplificação e junção** (mapshaper 0.7.61):

```text
-filter "ds_sup_fed != 'PLA' && ds_sup_fed != 'TRV'"
-each   "br = vl_br, situacao = ..."        (tabela acima)
-simplify dp interval=200m
-dissolve br,situacao
-o format=topojson quantization=50000
```

- Douglas-Peucker com tolerância de **200 m**, cálculo esférico: 99,2% das 5.237.435 coordenadas únicas removidas;
  deslocamento médio de 79,6 m e máximo de 199,99 m (estatística do próprio mapshaper). O mapshaper reparou 16
  cruzamentos criados pela simplificação e avisou 42 que não conseguiu reparar; são cruzamentos entre linhas, invisíveis
  nesta escala.
- Os 5.329 registros viraram 303 feições (uma por BR e situação) e 1.131 linhas contínuas: os segmentos da mesma BR e
  situação que se tocam foram unidos. Final: 1.771 arcos e 29.345 vértices.
- Quantização 50.000 (grade de 0,00081° × 0,00076°, cerca de 90 m × 85 m).
- bbox −72,719, −33,693, −32,400, 4,483. O ponto mais a leste é a BR-363 em Fernando de Noronha.
- Conferência: a soma dos arcos únicos do arquivo dá 73.871 km, 1,1% abaixo dos 74.697 km medidos antes de simplificar.
  Isso confirma que os trechos coincidentes compartilham arcos e que a simplificação encurta a malha em cerca de 1%.

**Comparação com a série oficial do DNIT.** O PDF "Evolução da malha rodoviária pavimentada sob jurisdição federal
(Patrimônio)" (https://www.gov.br/dnit/pt-br/assuntos/atlas-e-mapas/pnv-e-snv/evolucaomalhapav-patrimonio.pdf) dá
**66.611,18 km em 2025**, "excluindo-se os trechos sobrepostos/coincidentes", usando "a última versão disponível do SNV
publicada naquele ano". O mesmo filtro deste script (DUP + PAV, sem coincidentes) dá:

| Versão do SNV | Pavimentada, sem coincidentes (km) | Diferença para 66.611,18 |
|---|---|---|
| 202507A | 66.699,95 | +0,13% |
| 202511A | 66.927,70 | +0,48% |
| 202607A (usada) | 67.140,30 | +0,79% |

> [!note] Hipótese, confirmar
> Não consegui reproduzir exatamente o número do DNIT, nem descobrir qual versão ou critério ele usa. A ordem de grandeza
> confere. Para o site, há duas formas seguras de citar:
> 1. o número oficial, com a fonte do PDF: "66.611 km de rodovias federais pavimentadas em 2025 (DNIT)";
> 2. o cálculo deste arquivo, dizendo que é cálculo: "cerca de 75 mil km de rodovias federais existentes, 67 mil
>    pavimentados (cálculo sobre o SNV 202607A do DNIT, julho de 2026)".

**Ressalva de licença do SNV:**

- O Decreto 8.777/2016 (art. 2º, III) define dados abertos como de livre utilização, "limitando-se a creditar a autoria
  ou a fonte".
- O portal de dados abertos do próprio DNIT publica as planilhas do SNV ("Jurisdição de Vias",
  https://servicos.dnit.gov.br/dadosabertos/dataset/jurisdicao-de-vias) com licença "Other (Open)".
- A base geométrica baixada (compartilhamento do DNIT) não traz licença escrita. O registro do SNV na INDE
  (https://metadados.inde.gov.br/geonetwork/srv/api/records/ce3899b3-91aa-4f32-84b1-b50b851d6716) também não.
- O rodapé do portal gov.br do DNIT declara Creative Commons Atribuição-SemDerivações 3.0 (CC BY-ND 3.0) para o conteúdo
  do site. Se isso valesse para a base geométrica, simplificar a geometria seria uma derivação.

> [!note] Hipótese, confirmar
> Que a base geométrica do SNV pode ser simplificada e publicada com crédito, pela política de dados abertos, e que o
> CC BY-ND do rodapé do gov.br vale para os textos do portal e não para a base de dados. Para ter certeza antes de
> publicar, perguntar ao DNIT pelo Fala.BR.

## 4. `rota-br116-sp-curitiba.json`

`FeatureCollection` com uma `LineString` e cinco `Point`.

| Item | Valor |
|---|---|
| Fonte | DNIT, SNV 202607A: mesmo arquivo da seção 3, eixo principal da BR-116 (`sg_tipo_tr = "B"`) |
| Conferência de posição | IBGE, API de malhas v3, municípios de 2022 (São Paulo 3550308, Juquitiba 3526209, Registro 3542602, Curitiba 4106902) e a malha de UFs da seção 2 |
| Trechos do SNV | 24: `116BSP2560` a `116BSP2700` (SP) e `116BPR2710` a `116BPR2770` (PR); lista completa em `metadados.trechos_snv` |
| Propriedades da linha | `nome` ("BR-116, Rodovia Régis Bittencourt: São Paulo → Curitiba"), `comprimento_km` (405,4) |
| Propriedades dos pontos | `nome`, `km_desde_inicio`, `referencia_snv` |
| Simplificação | Douglas-Peucker com tolerância de **20 m**, trecho a trecho, mantendo os nós entre trechos; de 25.665 para 760 vértices; coordenadas com 5 casas decimais (cerca de 1 m) |
| bbox | −49,303, −25,572, −46,752, −23,607 |

**Início: divisa municipal São Paulo/Taboão da Serra (BR-116/SP km 263,9).** É o nó do SNV onde a BR-116 existente
sai da capital rumo ao sul. Antes dele, dentro da cidade de São Paulo, o SNV só tem o trecho `116BSP2555` (km 257 a
263,9), uma reta de 2 vértices marcada como planejada, que não representa estrada nenhuma. O primeiro trecho da rota,
`116BSP2560` (km 263,9 a 270,1, 6,2 km, em Taboão da Serra), foi municipalizado: a Arteris informou em 22/02/2024 que
o trecho do "km 268,9 ao km 275,4" (numeração da concessão) passou ao município de Taboão da Serra
(https://www.arteris.com.br/fique-por-dentro/noticias-e-releases/trecho-da-rodovia-regis-bittencourt-br-116-e-municipalizado-em-taboao-da-serrasp/).
No SNV esse trecho aparece como planejado (`PLA`), com jurisdição municipal, `est_coinc = "Alienado"`, pista
duplicada (`sup_est_co = "DUP"`) e geometria detalhada (507 vértices). Ele **entra na rota**, porque é a estrada real
na saída de São Paulo, mas **não entra** em `rodovias-federais.topo.json`, que exclui planejados. Na tela, os primeiros
6,2 km da rota não têm malha federal por baixo, e isso está certo.

**Fim: `ENTR BR-116/277/376/476` (BR-116/PR km 119,2).** É o primeiro nó do SNV dentro do município de Curitiba,
conferido com a malha municipal do IBGE (3,9 km dentro da divisa). Entre os km 96,9 e 119,2 do PR, a BR-116 coincide
com a BR-277 e depois com a BR-277 e a BR-376 (campo `ds_coinc`).

**Pontos de referência.** Cada ponto é um nó do SNV sobre a linha, e não o centro da cidade. "Registro", por exemplo,
marca onde a BR-116 cruza a entrada da SP-139 em Registro.

| `nome` | `km_desde_inicio` | `referencia_snv` | Coordenada | Conferência no IBGE |
|---|---|---|---|---|
| São Paulo | 0 | DIV MUNICIPAL SÃO PAULO/TABOÃO DA SERRA · BR-116/SP km 263,9 | −46,75221; −23,60741 | A 67 m da divisa do município de São Paulo |
| Juquitiba | 65,4 | INÍCIO DA SERRA DO CAFEZAL (JUQUITIBA) · BR-116/SP km 329,2 | −47,14473; −23,97932 | Dentro de Juquitiba, a 2,9 km da divisa |
| Registro | 171,8 | ENTR SP-139 (REGISTRO) · BR-116/SP km 439,5 | −47,84914; −24,50878 | Dentro de Registro, a 7,1 km da divisa |
| Divisa SP/PR | 290,0 | DIV SP/PR (INÍCIO PONTE S/RIO PARDINHO) · BR-116/PR km 0 (= SP km 562,1) | −48,56072; −25,05958 | A 91 m da divisa do Paraná |
| Curitiba | 405,4 | ENTR BR-116/277/376/476 · BR-116/PR km 119,2 | −49,30341; −25,54417 | Dentro de Curitiba, a 3,9 km da divisa |

Juquitiba entrou por marcar o início da Serra do Cafezal e dividir o trecho de 172 km entre São Paulo e Registro.

**Comprimento.**

- `comprimento_km` = **405,4 km**: geodésico (Vincenty, elipsoide WGS 84) na geometria original do SNV, com 25.665
  vértices. `km_desde_inicio` usa a mesma medida.
- A linha entregue, simplificada, mede 404,4 km (−0,25%). Se o site posicionar pontos por fração da linha
  (`km_desde_inicio / comprimento_km`), o erro fica abaixo de 0,3%.
- A soma da extensão oficial dos 24 trechos no SNV (`vl_extensa`) dá **417,4 km**, 12 km a mais. A diferença se
  concentra em poucos trechos:

| Trecho | Local | Extensão SNV (km) | Medida na geometria (km) | Diferença (km) |
|---|---|---|---|---|
| 116BPR2750 | Contorno Leste (Quatro Barras) → entrada da PR-415 (Piraquara) | 19,0 | 14,67 | −4,33 |
| 116BSP2685 | Jacupiranga → acesso a Barra do Turvo | 74,7 | 72,99 | −1,71 |
| 116BSP2630 | Acesso sul de Juquiá → Registro | 32,5 | 31,06 | −1,44 |
| 116BSP2700 | Acesso a Barra do Turvo → divisa SP/PR | 17,9 | 16,55 | −1,35 |
| 116BSP2650 | Registro → acesso a Pariquera-Açu | 18,9 | 17,88 | −1,02 |
| 116BSP2565 | Entrada da SP-234 → entrada da SP-228 | 4,0 | 4,80 | +0,80 |

No Brasil inteiro, a razão entre a medida da geometria e a extensão do SNV tem mediana 0,999 (percentis 5 e 95: 0,936 e
1,051), então a geometria é coerente com o SNV no geral.

> [!note] Hipótese, confirmar
> A extensão do SNV segue a quilometragem de referência da rodovia, que pode não ter sido remedida depois de mudanças de
> traçado (duplicações, variantes, contornos). No trecho 116BPR2750, 19,0 km para uma distância em linha reta de cerca de
> 13,6 km é improvável numa pista duplicada, e a geometria (961 vértices) mede 14,7 km. Por isso o arquivo usa a medida
> da geometria.

**Checagens da rota:** os rótulos de fim e início de trechos vizinhos coincidem; os km encadeiam sem salto; não há buraco
de mais de 1 m entre trechos; não há autointerseção nem na geometria original nem na simplificada; todos os pontos
estão a 0,0 m da linha; a linha começa no ponto "São Paulo" e termina no ponto "Curitiba".

## 5. Faixa da noite (terminador)

Não há arquivo: o site calcula a faixa da noite com `d3-geo`, desenhando um círculo de 90° centrado no antípoda do
ponto subsolar.

Referência: NOAA Global Monitoring Laboratory, "General Solar Position Calculations",
https://gml.noaa.gov/grad/solcalc/solareqns.PDF (para conferir valores: https://gml.noaa.gov/grad/solcalc/).

**Fórmulas (NOAA).** Com `dia_do_ano` (1 em 1º de janeiro) e `hora` em UTC decimal:

```text
γ       = 2π / 365 × (dia_do_ano − 1 + (hora − 12) / 24)        [rad; em ano bissexto, 366]

eqtime  = 229,18 × (0,000075 + 0,001868 cos γ − 0,032077 sen γ
                    − 0,014615 cos 2γ − 0,040849 sen 2γ)          [minutos]

decl    = 0,006918 − 0,399912 cos γ + 0,070257 sen γ − 0,006758 cos 2γ
          + 0,000907 sen 2γ − 0,002697 cos 3γ + 0,00148 sen 3γ    [rad]
```

**Ponto subsolar.** A NOAA dá o meio-dia solar em minutos UTC como `snoon = 720 − 4 × longitude − eqtime`. No ponto
subsolar é meio-dia solar agora, então, com `minutos_utc = hora × 60`:

```text
longitude_subsolar = (720 − minutos_utc − eqtime) / 4     [graus; normalizar para −180..180]
latitude_subsolar  = decl                                 [converter para graus]
```

**Com d3-geo** (a lógica abaixo foi conferida em Node e deu os valores de exemplo da tabela):

```ts
import { geoCircle } from "d3-geo";

export function pontoSubsolar(data: Date): [number, number] {
  const ano = data.getUTCFullYear();
  const bissexto = (ano % 4 === 0 && ano % 100 !== 0) || ano % 400 === 0;
  const diaDoAno = Math.floor((data.getTime() - Date.UTC(ano, 0, 1)) / 86_400_000) + 1;
  const hora = data.getUTCHours() + data.getUTCMinutes() / 60 + data.getUTCSeconds() / 3600;
  const g = ((2 * Math.PI) / (bissexto ? 366 : 365)) * (diaDoAno - 1 + (hora - 12) / 24);
  const eqtime = 229.18 * (0.000075 + 0.001868 * Math.cos(g) - 0.032077 * Math.sin(g)
    - 0.014615 * Math.cos(2 * g) - 0.040849 * Math.sin(2 * g));
  const decl = 0.006918 - 0.399912 * Math.cos(g) + 0.070257 * Math.sin(g) - 0.006758 * Math.cos(2 * g)
    + 0.000907 * Math.sin(2 * g) - 0.002697 * Math.cos(3 * g) + 0.00148 * Math.sin(3 * g);
  const lon = (720 - hora * 60 - eqtime) / 4;
  return [((lon + 540) % 360) - 180, (decl * 180) / Math.PI];
}

const [lon, lat] = pontoSubsolar(new Date());
const noite = geoCircle().center([lon + 180, -lat]).radius(90)(); // Polygon GeoJSON da noite
```

| Instante (UTC) | Dia do ano | eqtime (min) | Declinação | Ponto subsolar (lon, lat) |
|---|---|---|---|---|
| 11/09/2026 12:00 | 254 | 3,152 | 4,868° | −0,788; 4,868 |
| 11/09/2026 05:00 | 254 | 3,044 | 4,978° | 104,239; 4,978 |
| 21/12/2026 15:00 | 355 | 2,112 | −23,421° | −45,528; −23,421 |

O raio de 90° é o terminador geométrico. Para crepúsculos, a mesma ideia com raios maiores (90,833° é o valor que a NOAA
usa para nascer e pôr do sol, com refração e tamanho do disco solar).

> [!note] Hipótese, confirmar
> A NOAA não informa a precisão dessas séries no PDF. Espero erro de fração de grau na posição do Sol, suficiente para
> uma faixa de noite num mapa de site. Conferir alguns instantes contra a calculadora da NOAA antes de afirmar precisão.

## Uso no site

Os dados são estáticos: importe só em componentes de servidor, para os JSON não irem para o pacote do navegador. As
chamadas abaixo foram conferidas com o `topojson-client` 3.1.0 instalado no site; os tipos TypeScript não foram
conferidos no build.

```ts
import { feature, mesh } from "topojson-client";
import brasil from "@/data/mapas/brasil-ufs.topo.json";
import rodovias from "@/data/mapas/rodovias-federais.topo.json";

const ufs = feature(brasil, brasil.objects.ufs);                          // 27 feições
const contorno = feature(brasil, brasil.objects.brasil);                  // 1 feição
const divisas = mesh(brasil, brasil.objects.ufs, (a, b) => a !== b);      // 26 linhas internas
const malha = mesh(rodovias, rodovias.objects.rodovias);                  // cada arco uma vez: 817 linhas
const br116 = mesh(rodovias, {
  type: "GeometryCollection",
  geometries: rodovias.objects.rodovias.geometries.filter((g) => g.properties.br === "116"),
});                                                                       // 51 linhas
```

- No mundo, o Brasil é a feição com `id === "076"` (ou `properties.codigo === "BRA"`). Não há propriedades `name`,
  `NAME`, `ADM0_A3` nem `iso_a3`.
- Para a malha inteira, use `mesh`: com `feature`, os trechos coincidentes seriam desenhados duas vezes e apareceriam
  mais fortes com transparência (a menos que a opacidade esteja no `<g>` que agrupa as linhas).
- **Não some o comprimento das feições para citar a extensão da malha.** Somar `geoLength` das 303 feições
  (raio 6.371,0088 km) dá **81.789 km**, porque os 7,8 mil km de trechos coincidentes entram duas vezes e a geometria
  está simplificada. O `mesh` dá 73.990 km, ainda simplificado. Para texto, use `metadados.extensao_km.total_snv`
  (74.829,3 km) ou os números da seção 3.
- `fitExtent` com o objeto `ufs` ou `brasil` inclui Trindade e Fernando de Noronha; ver seção 2.
- A BR-116 filtrada ainda sai em 51 linhas por causa de acessos, contornos, variantes e trechos planejados excluídos.
  Para animar o traçado São Paulo → Curitiba, use `rota-br116-sp-curitiba.json`, que é uma linha única e ordenada.

## Checagem feita em 11/09/2026

`node scripts/mapas/conferir-mapas.mjs`, com o `d3-geo` 3.1.1 do site: todas as checagens passaram.

- `mundo.topo.json`: 177 países, 174 com `id` ISO numérico único, Brasil com `id` "076", `nome` "Brasil" e `codigo`
  "BRA", bbox −180 a 180 e −90 a 83,645, nenhum anel invertido para o d3-geo.
- `brasil-ufs.topo.json`: 27 siglas únicas, contorno com 1 feição, bbox −73,990, −33,748, −29,299, 5,272 (continental até
  −34,793), 0 arcos exclusivos no contorno, nenhum anel invertido.
- `rodovias-federais.topo.json`: 303 feições, 147 BRs, só `duplicada`, `pavimentada`, `implantada` e `leito_natural`,
  bbox −72,719, −33,693, −32,400, 4,483, arcos únicos (73.871 km) a −1,11% da extensão medida; somando as feições, com
  coincidentes repetidos, 81.658 km.
- `rota-br116-sp-curitiba.json`: 1 linha e 5 pontos, 760 vértices, sem autointerseção, pontos sobre a linha e em ordem
  de km, bbox −49,303, −25,572, −46,752, −23,607.

Teste visual em `site/scripts/mapas/.cache/teste.png`, olhado de fato: mundo em Equal Earth com o Brasil destacado;
Brasil em Mercator com UFs, malha federal e rota; e o corredor SP–PR com a rota por cima da malha do SNV, os contornos
municipais do IBGE e as divisas. A rota corre sobre a BR-116 da malha em todo o trajeto (exceto nos 6,2 km iniciais
municipalizados, como esperado). O início fica na divisa oeste de São Paulo, Juquitiba e Registro ficam dentro dos
contornos, o ponto da divisa fica sobre a linha SP/PR e o fim fica dentro de Curitiba. O ESLint do site
(`eslint scripts/mapas`) não acusou nada.

## O que não consegui ou ficou em aberto

1. **Licença escrita** para a base geométrica do SNV e para a API de malhas do IBGE: não encontrei. Ficaram as hipóteses
   das seções 2 e 3; confirmar com os órgãos antes de publicar.
2. **Número oficial de extensão pavimentada:** o método reproduz a série do DNIT com diferença de 0,13% a 0,79%
   conforme a versão, mas não exatamente.
3. **Malha do IBGE posterior a 2022 pela API:** os períodos de 2023 a 2026 responderam HTTP 500. A de 2025 existe no FTP
   e não foi usada.
4. **Tolerância da qualidade "máxima" do IBGE:** não é publicada na documentação da API.
5. **Diferença entre a extensão do SNV e a medida da rota** (417,4 km contra 405,4 km): causa não confirmada.
6. **Portal dados.gov.br:** não consultado a fundo; a API dele exige chave. O portal de dados abertos do DNIT não lista a
   base geométrica, só as planilhas "Jurisdição de Vias". O VGeo não foi usado, porque o compartilhamento do DNIT tem a
   base completa.
7. **PNG pelo `@resvg/resvg-js` 2.6.2:** aborta neste SVG; a conversão depende do ImageMagick. Sem nenhum dos dois, a
   conferência gera só o SVG.

## Fontes consultadas (11/09/2026)

- DNIT, PNV e SNV: https://www.gov.br/dnit/pt-br/assuntos/atlas-e-mapas/pnv-e-snv
- DNIT, compartilhamento do SNV: https://servicos.dnit.gov.br/dnitcloud/index.php/s/oTpPRmYs5AAdiNr
- DNIT, dados abertos, "Jurisdição de Vias": https://servicos.dnit.gov.br/dadosabertos/dataset/jurisdicao-de-vias
- DNIT, evolução da malha pavimentada: https://www.gov.br/dnit/pt-br/assuntos/atlas-e-mapas/pnv-e-snv/evolucaomalhapav-patrimonio.pdf
- DNIT, VGeo (não usado): https://servicos.dnit.gov.br/vgeo/
- INDE, metadados do SNV: https://metadados.inde.gov.br/geonetwork/srv/api/records/ce3899b3-91aa-4f32-84b1-b50b851d6716
- IBGE, API de malhas v3: https://servicodados.ibge.gov.br/api/docs/malhas?versao=3
- IBGE, API de localidades: https://servicodados.ibge.gov.br/api/v1/localidades/estados
- IBGE, nota técnica sobre o SIRGAS2000: https://geoftp.ibge.gov.br/metodos_e_outros_documentos_de_referencia/normas/nota_tecnica_termino_periodo_transicao_sirgas2000.pdf
- Decreto 8.777/2016: https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2016/decreto/d8777.htm
- Natural Earth, termos de uso: https://www.naturalearthdata.com/about/terms-of-use/
- Natural Earth, releases: https://github.com/nvkelso/natural-earth-vector/releases
- Arteris, municipalização em Taboão da Serra: https://www.arteris.com.br/fique-por-dentro/noticias-e-releases/trecho-da-rodovia-regis-bittencourt-br-116-e-municipalizado-em-taboao-da-serrasp/
- NOAA, General Solar Position Calculations: https://gml.noaa.gov/grad/solcalc/solareqns.PDF
- mapshaper no npm: https://www.npmjs.com/package/mapshaper
