# Frente 1 · Mensagem, posicionamento e personas
Avaliador: agente 1 · 11/09/2026 · versão avaliada: `site-drivesafe/previa/v2/index.html` (prints `previa-topo.png`,
`previa-desktop.png` e `previa-celular.png`)

> Convenções deste relatório
> - `index.html:N` = `site-drivesafe/previa/v2/index.html`, linha N.
> - `v1:N` = `site-drivesafe/previa/index.html`, linha N (versão anterior, só histórico).
> - Caminhos de código a partir da raiz do repositório.
> - Coordenadas de print em pixels do arquivo original (x, y).

## Nota geral: 3/10
A v2 explica bem o mecanismo (olho fecha, alarme toca, evento sobe), mas não vende para ninguém. Ela:
- fala só de caminhão e ignora o transporte de passageiros;
- abre com uma afirmação falsa de piloto;
- trata o comprador como engenheiro;
- não responde nenhuma objeção além de "não grava imagem".

## Notas por critério

| Critério | Nota | Por quê | Evidência |
|---|---|---|---|
| Entende-se em 5 s o que é e para quem | 4 | "O que é" passa: alarme de sono na cabine. "Para quem" não passa: não há veículo nem segmento, e o único indício ("transportadoras") está numa etiqueta mono de 0,75 rem. O título é ambíguo e afirma um fato errado (problema 3). | `index.html:60, 229-231`; `previa-topo.png`: texto em x 128–585, y 175–525, e à direita só um rosto em pontos (x 655–1310); `previa-celular.png`, primeira tela (y 0–860): sem veículo e sem segmento |
| Dores de cada persona | 3 | Das dores das personas, só uma aparece, e parcial: madrugada e vídeo com sindicato, da P1. Faltam sinistro, seguro, contrato com cliente, indicador do poder concedente, celular no corredor urbano e o medo do motorista. | Seções em `index.html:226-408`: 5 das 6 explicam como mede; dores em `personas.md:17-23, 41-46, 61-67, 84-88, 104-108` |
| Cobertura de carga e de passageiros | 1 | "ônibus", "passageiro", "fretamento", "urbano", "rodoviário" e "logística": **0 ocorrências**. "Caminhão" aparece em 2 títulos de seção e na chamada final. | `index.html:268, 352, 403` |
| Prova e credibilidade | 2 | O site afirma um piloto que não existe, não diz quem faz o produto e tem incoerência técnica visível. A favor: é honesto sobre dados de demonstração e limiares em validação. | `index.html:229, 412` contra `contexto.md:37`; `index.html:359` contra `vision/face.py:36-37`; a favor, `index.html:259, 344, 384` |
| Objeções (alarme falso, custo, LGPD, motorista) | 3 | Responde privacidade e falta de sinal. O resto fica sem resposta boa: alarme falso vira uma linha de ficha técnica; custo, instalação, suporte, rastreador e motorista não aparecem; a LGPD é uma afirmação de conformidade sem base. | `index.html:231, 373, 391, 353` |
| Chamada adequada a venda B2B | 4 | "Pedir piloto" é a ação certa, mas: leva a um botão de WhatsApp sem link; não diz o que o piloto inclui; "cinco caminhões" exclui passageiros. "Já é cliente? Entrar" virou "Entrar" e some no celular. | `index.html:220, 233, 403-406, 219, 48-49`; regra em `contexto.md:44` |
| Tom sério, pt-BR natural, sem jargão | 5 | Frases curtas e sóbrias, sem exagero. Mas PERCLOS, EAR, JSON, "a cada quadro", "curva do olho" e "Raspberry Pi, Linux, Windows e macOS" falam com desenvolvedor, não com dono de fretamento. | `index.html:255, 327, 388, 454, 365-371, 231, 298, 392` |
| Diferença frente à videotelemetria que grava vídeo | 5 | O fato está lá e é verdadeiro ("Nenhuma imagem é gravada"), mas como detalhe técnico. O site não nomeia a alternativa, não diz por que isso importa (sindicato, LGPD, passageiros, revisão manual de vídeo) e não assume a troca: sem vídeo, não há clipe de prova. | `index.html:231, 238, 352-359`; comparação na seção de posicionamento, abaixo |

A média simples é 3,4, arredondada para 3.

## Leitura por persona

| Persona | Nota | Resumo |
|---|---|---|
| P1 Renata · segurança viária, carga | 5 | É a única para quem o site foi escrito, mas perde no comitê: "piloto com quais transportadoras?" |
| P2 Carlos · fretamento e turismo | 2 | "Comece com cinco caminhões" e PERCLOS: "isso não é para mim" |
| P3 Juliana · CCO de ônibus urbano | 3 | Vê uma fila de eventos, mas não vê ônibus, celular, triagem nem escala |
| P4 Marcos · diretor financeiro | 2 | Não acha número de negócio, modelo de cobrança nem empresa por trás |
| P5 José · motorista | 4 | "Nenhuma imagem é gravada" acalma; o painel com "João Pereira · Crítico" assusta |

### P1 · Renata (carga, 190 cavalos mecânicos, SP–PR–SC–RS)
- **Em 5 s:** entende "câmera que toca alarme quando o motorista fecha o olho". Só descobre que é para frota pesada ao
  rolar até "caminhão sair da faixa" (`index.html:268`). No topo, o único sinal de segmento é a etiqueta "Em piloto com
  transportadoras" (`index.html:229`).
- **O que a convence:**
  - a escada 1 s, 3 s e 6 s (`index.html:271-273`), que confere com `vision/drowsiness.py:28-30`;
  - a rota "São Paulo → Curitiba · BR-116" e o evento às 02:14 (`index.html:320, 337`): é o mundo dela;
  - "Nenhuma imagem é gravada" (`index.html:231`), que toca no atrito com o sindicato (`personas.md:23`);
  - a fila que funciona sem sinal (`index.html:373`) e o celular no suporte que não conta (`index.html:389`).
- **O que a faz fechar a aba (ou perder no comitê):**
  - No comitê, alguém pergunta qual transportadora está no piloto, e a resposta é nenhuma (`contexto.md:37`). A partir
    daí, nada do site vale.
  - Sobre alarme falso com sol, óculos e noite, só há "óculos escuros detectados" (`index.html:391`), que não diz que
    óculos não viram sono.
  - Não fala de rastreador, custo por veículo, parar o caminhão para instalar nem suporte na estrada
    (`personas.md:29-31`).
  - Não diz quem está por trás: o rodapé tem só "DriveSafe AI · protótipo em piloto" (`index.html:412`).
- **Nota: 5/10.**

### P2 · Carlos (38 ônibus rodoviários, fretamento corporativo)
- **Em 5 s:** vê um diagrama de olhos com "EAR 0,33" e "PERCLOS 60 s" (`index.html:255, 454`; `previa-topo.png`,
  x 655–1310). Parece produto de laboratório. Não vê ônibus, que é a primeira coisa de que ele precisa
  (`personas.md:48`).
- **O que o convence:** "O motorista não precisa tocar em nada" (`index.html:269`) e "Pare em local seguro"
  (`index.html:281`). É simples, e o alarme fala com o motorista.
- **O que o faz fechar a aba:**
  - São três títulos com caminhão (`index.html:268, 352, 403`), e a chamada final, "Comece com cinco caminhões", diz
    literalmente que o produto não é para ele.
  - Faltam passageiros, responsabilidade civil, argumento para o cliente corporativo, preço previsível e instalação sem
    tirar o ônibus de rodar (`personas.md:41-53`).
  - "Roda em Raspberry Pi, Linux, Windows e macOS" (`index.html:392`) e o bloco JSON (`index.html:365-371`) confirmam o
    medo de "tecnologia complicada".
  - "Também atendemos universidades e editais de pesquisa" (`index.html:404`) soa como projeto acadêmico, não como
    fornecedor.
- **Nota: 2/10.**

### P3 · Juliana (CCO, 620 ônibus urbanos em 9 garagens)
- **Em 5 s:** entende "alarme de sono para viagem longa de madrugada". A dor principal dela, celular e distração nos
  corredores (`personas.md:62`), só aparece na linha 389, dentro da ficha técnica.
- **O que a convence:** "Eventos para revisar", com botão "Revisar" e o filtro "Em risco 3" (`index.html:305, 334-338`),
  e a fila que funciona sem sinal (`index.html:373`).
- **O que a faz fechar a aba:**
  - O painel tem 24 veículos (`index.html:304`) e nenhuma pista de escala.
  - O site não responde o medo dela de afogar o CCO em alertas (`personas.md:66`), embora o produto já faça essa
    triagem: só eventos de risco 2 ou mais entram na fila, e avisos de sistema e de risco 1 ficam de fora
    (`backend/alert_types.py:40-42, 57-58`).
  - Não mostra a decisão registrada na revisão (confirmado, alarme falso, motorista orientado), que já existe no banco
    (`backend/database.py:24`).
  - "Antes de o caminhão sair da faixa" (`index.html:268`) não tem nada a ver com o para-e-anda urbano.
  - Não fala do sindicato dos rodoviários nem da privacidade dos passageiros (`personas.md:74-75`).
- **Nota: 3/10.**

### P4 · Marcos (diretor financeiro, 70 caminhões e 140 vans e VUCs)
- **Em 5 s:** entende "tecnologia de câmera". Não há nenhuma frase de valor para o negócio: sinistro, prêmio de seguro,
  custo total.
- **O que o convence:** a ausência de percentual inventado, que ele rejeita (`personas.md:95`), e o "relatório do
  período" do piloto (`index.html:404`).
- **O que o faz fechar a aba:**
  - Faltam o modelo de cobrança, o prazo de contrato, o custo de instalação, o que o piloto mede antes e depois e o
    relatório para a seguradora (`personas.md:90-94`).
  - "Protótipo" e "Raspberry Pi" (`index.html:392, 412`), sem empresa, CNPJ ou equipe, significam risco de continuidade
    (`personas.md:95`).
  - "Conforme a LGPD" (`index.html:353`), sem parecer, é exatamente o tipo de frase que o jurídico dele devolve.
  - A frota mista (vans, VUCs, agregados) não aparece, e a chamada fala em "cinco caminhões".
- **Nota: 2/10.**

### P5 · José (carreteiro há 31 anos, voz na CIPA)
- **Em 5 s:** vê o rosto de alguém virando pontos, com a faixa vermelha do alarme (`previa-topo.png`, x 670–950,
  y 197–228). "Nenhuma imagem é gravada" (`index.html:231`) segura a leitura.
- **O que o convence:**
  - "0 imagens gravadas" (`index.html:238`);
  - "comparado com ele mesmo descansado" (`index.html:269`);
  - "Pare em local seguro" (`index.html:281`): o alarme fala com ele.
- **O que o faz resistir:**
  - O site é narrado do lado do gestor; o motorista é sempre "ele".
  - O painel mostra nomes com "Crítico" (`index.html:307`) e botões "Revisar" (`index.html:336-338`). A escada diz "O
    gestor é avisado no painel imediatamente" (`index.html:273`). Para ele, isso é ser dedurado.
  - O site não diz nada do que o protege e já existe no produto:
    - o evento pode ser marcado como alarme falso (`backend/database.py:24`);
    - ele vê e exporta os próprios dados (`backend/routes/people.py:150`; `PENDENCIAS.md:32`);
    - não há gravação de som (nenhuma captura de áudio no código).
  - A v1 dizia "O motorista vê os próprios dados e o que autorizou" (`v1:254`). A v2 apagou essa frase.
- **Nota: 4/10.**

## Problemas, do mais grave ao menos grave

| # | Gravidade | Problema | Evidência | Impacto | Correção concreta |
|---|---|---|---|---|---|
| 1 | crítica | Afirma um piloto que não existe | "Em piloto com transportadoras" (`index.html:229`), com ponto verde de "ao vivo" (`index.html:61`; `previa-topo.png` x 128–372, y 175–205), e "protótipo em piloto" (`index.html:412`). `contexto.md:37`: "Não há frota em piloto documentada". O erro já estava na v1 (`v1:164`). | A primeira pergunta de P1 e P4 derruba a confiança em todo o resto, inclusive no que é verdade. Fere a regra "nenhuma afirmação sem base" (`contexto.md:46`). | Trocar por um status verdadeiro, como "Protótipo funcionando. Selecionando as primeiras frotas para piloto." (texto final depende da pergunta 1). Tirar o ponto verde. No rodapé, "DriveSafe · protótipo". |
| 2 | crítica | O transporte de passageiros não existe no site | Zero ocorrências de ônibus, passageiro, fretamento, urbano, rodoviário e logística; "caminhão" em `index.html:268, 352, 403`. Pedido do dono: `contexto.md:7-8, 42-43`. | P2 e P3, metade do público pedido, fecham a aba. P4, com vans e VUCs, também não se vê. | Nos trechos comuns, trocar "caminhão" por "veículo" ou "cabine". Criar duas entradas, **Carga** e **Passageiros**, cada uma com título, dores e chamada próprios (hierarquia abaixo). Chamadas: "Piloto com 5 a 10 veículos" e, no urbano, "Piloto em uma garagem". |
| 3 | alta | O título afirma um fato errado e pode ser lido de dois jeitos | "Microssono dura 1 segundo. O alarme também." (`index.html:230`). Microssono dura de 1 a 15 s (Hertig-Godeschalk et al., *SLEEP* 43(1), 2020: https://academic.oup.com/sleep/article-abstract/43/1/zsz163/5536744). Lido ao pé da letra, "o alarme também" dura 1 s, mas a sirene toca 5 ciclos de 400 ms, cerca de 2 s (`vision/alarm.py:18-21`). O título também não diz para quem nem para quê. | O primeiro contato é uma frase que um médico do trabalho ou um gerente de segurança corrige. P2 e P4 não entendem o jogo de palavras. | Usar um dos títulos propostos abaixo. Para manter a ideia do segundo, dizer o que é verdade: "O alarme toca no primeiro segundo de olho fechado." |
| 4 | alta | O site vende o mecanismo, não resolve a dor de quem compra | 5 das 6 seções explicam como o produto mede (`index.html:243-259, 264-291, 293-346, 348-377, 379-397`). Nenhuma frase sobre sinistro, seguro, contrato com cliente, indicador do poder concedente ou programa de segurança. | P1 fica sem argumento pronto para o comitê, P2 sem argumento para o cliente corporativo, e P4 não acha motivo para gastar. | Abrir cada entrada de segmento com a dor, nas palavras da persona ("gestão de fadiga", "sinistralidade", "requisito do contrato", "índice de ocorrências"), e só depois mostrar o mecanismo. O detalhe técnico desce para "Como funciona". |
| 5 | alta | O celular, dor número 1 do urbano e dor da P1, só aparece na ficha técnica | A única menção está em `index.html:389`. Topo, demonstração, painel e eventos só mostram sono (`index.html:230-259, 336-338`). O produto detecta celular na mão, no ouvido e olhando por mais de 2 s (`backend/alert_types.py:22-24`). | P3 conclui que o produto é só para viagem noturna. P1 enxerga metade do valor. | Pôr "sono e celular" já no topo. No painel de demonstração, colocar um evento "Celular na mão" ao lado do microssono. Na entrada Passageiros, falar do celular primeiro. |
| 6 | alta | Nenhuma resposta às objeções que decidem a compra | Alarme falso: só "óculos escuros detectados" (`index.html:391`). Ausentes: custo, instalação, veículo parado, suporte fora da capital, convivência com rastreador e câmeras, "motorista experiente não precisa" (`personas.md:30-31, 52-53, 75-76, 95-96`). | Quem visita sai sem a resposta que o faria chamar no WhatsApp, e procura quem responde. Cobli e Creare falam de sinistro e custo logo no primeiro bloco. | Criar o bloco "Perguntas de quem decide", com as respostas curtas deste relatório (só as verdadeiras). Onde o dado ainda não existe, "definido no piloto", se o Matheus aprovar a formulação. |
| 7 | alta | O motorista não tem voz e aparece como suspeito | Não há seção para quem dirige. "João Pereira · Crítico" (`index.html:307`), botões "Revisar" (`index.html:336-338`) e "O gestor é avisado no painel imediatamente" (`index.html:273`). A v1 dizia "O motorista vê os próprios dados e o que autorizou" (`v1:254`), e a v2 tirou. O produto tem revisão com "alarme falso" e "motorista orientado" (`backend/database.py:24`) e exportação dos dados do motorista (`backend/routes/people.py:150`). | P5 derruba a adoção. P1 a P4 ficam sem argumento para a conversa com motoristas e sindicato (`personas.md:119`). | Criar a seção "Para quem dirige", em segunda pessoa: não grava imagem nem som; o alarme é para você; você autoriza e vê seus dados; todo evento passa por uma pessoa que pode marcar alarme falso. No painel de demonstração, mostrar um evento já decidido como "Alarme falso" e outro como "Motorista orientado". |
| 8 | alta | Não há ninguém por trás do produto | O rodapé tem só "DriveSafe AI · protótipo em piloto" (`index.html:412`). Sem equipe, cidade ou CNPJ. Botão de WhatsApp com `href="#"` (`index.html:406`). | P1 (comitê), P2 (compra por indicação e confiança) e P4 (continuidade) não avançam. | Criar um bloco curto "Quem faz" (nomes, papel, cidade, CNPJ quando houver) e mostrar o número de WhatsApp. Junto, "Como é o piloto": quantos veículos, quanto tempo, o que entra no relatório (pergunta 2). |
| 9 | média | A diferença frente à videotelemetria aparece como detalhe técnico, sem escolha nem troca assumida | `index.html:231, 238, 352-359` dizem que não grava, mas não comparam com câmeras que gravam o motorista, não dizem por que isso importa e não assumem que sem vídeo não há clipe de prova. No Brasil, a Cobli vende o vídeo como prova jurídica (https://www.cobli.co/camera-de-fadiga/) e a Creare, central 24 h com playback (https://crearesistemas.com.br/sensor-de-fadiga/). Lá fora, Motive e Samsara já oferecem "modo privacidade" como opção (https://gomotive.com/blog/advanced-driver-privacy-controls/). | O comprador não percebe que é outra categoria. Quem já tem câmera acha que é "mais uma câmera". Quem precisa de vídeo de acidente só descobre a falta depois. | Posicionar como "gestão de fadiga e celular sem vídeo do motorista, por projeto e não por configuração" e responder de frente: "Precisa de vídeo de acidente? Mantenha a sua câmera de estrada; o DriveSafe é um aparelho separado." (depende da pergunta 5) |
| 10 | média | Jargão e artefatos de desenvolvedor | PERCLOS (`index.html:255, 327, 388`), EAR (`index.html:454`), JSON (`index.html:365-371`), "a cada quadro" (`index.html:231, 357`), "curva do olho" (`index.html:298, 334`) e "Roda em Raspberry Pi, Linux, Windows e macOS" (`index.html:392`). | P2 desconfia de jargão (`personas.md:55`), P4 lê "caseiro" e o texto fica frio para P5. | Traduzir: PERCLOS vira "tempo de olho fechado nos últimos 3 minutos"; o JSON vira "o que sai do veículo: tipo, hora, duração e placa". Tirar os sistemas operacionais do site de vendas e deixá-los numa ficha técnica para a TI. Se o Raspberry Pi continuar, virar argumento para P4: "hardware de mercado, sem equipamento proprietário" (pergunta 6). |
| 11 | média | Promessa implícita de resultado e de uma função que não existe | "O aviso chega antes de o caminhão sair da faixa." (`index.html:268`). O produto só tem a câmera voltada para o motorista (`contexto.md:28`): não vê a estrada, não detecta faixa e não garante tempo de reação. A 90 km/h, limite de ônibus e caminhão em rodovia de pista dupla (CTB art. 61: https://ctbdigital.com.br/artigo/art61/), 1 s são 25 m. | É uma promessa que o primeiro acidente real desmente, e confunde o produto com o ADAS vendido pelos concorrentes. | "O alarme toca no primeiro segundo de olho fechado. A 90 km/h, esse segundo são 25 metros." |
| 12 | média | "Imediatamente" contradiz "funciona sem internet" | "O gestor é avisado no painel imediatamente" (`index.html:273`) contra "Sem internet, fica na fila" (`index.html:373`). Com sinal, o envio acontece a cada 5 s, com espera crescente quando falha (`vision/sync.py:58, 82`). | P3, para quem conexão é objeção (`personas.md:75`), percebe a incoerência. | "Com sinal, o evento chega à empresa em segundos. Sem sinal, assim que a conexão volta." |
| 13 | média | Afirma conformidade legal sem base e perdeu o aviso de limite do produto | "com o consentimento do motorista, conforme a LGPD" (`index.html:353`). Na relação de emprego, o consentimento é base frágil por causa da subordinação (https://www.conjur.com.br/2021-ago-28/rodrigues-lgpd-consentimento-relacoes-trabalhistas/). A v1 dizia "Não faz diagnóstico médico e não substitui descanso e pausas" (`v1:197`); a v2 perdeu a frase. | O jurídico de P4 e de P3 barra, e a marca fica exposta se alguém questionar. | "O motorista registra a autorização, com histórico, e pode exportar os próprios dados." Tirar "conforme a LGPD" até haver parecer (pergunta 10). Voltar a frase de limite: "Indica nível de risco. Não faz diagnóstico e não substitui descanso e pausas." |
| 14 | média | Público antigo na chamada final | "Também atendemos universidades e editais de pesquisa." (`index.html:404`), contra o foco atual (`contexto.md:42-43`). | Enfraquece a imagem de fornecedor justo na hora da decisão. | Apagar. Se houver parceria acadêmica, ela vira credencial em "Quem faz", não público. |
| 15 | baixa | Número técnico incoerente | "12 pontos por olho" (`index.html:359`), mas o cálculo usa 6 pontos por olho (`vision/face.py:36-37`) e o desenho mostra 6 (`index.html:420, 440`). | Quem conferir perde a confiança no resto. | "6 pontos em cada olho", ou tirar o número. |
| 16 | baixa | O painel de demonstração só representa carga em frota pequena e mostra um formato de painel ainda não decidido | "24 veículos" (`index.html:304`), "BR-116" (`index.html:320`) e janela de programa com "— ▢ ✕" (`index.html:301`). O formato do painel está em aberto (`contexto.md:38`; `PENDENCIAS.md:7`). | P3 não vê escala, e o site promete um formato que pode mudar. | Dois estados de demonstração, rodovia de carga e ônibus, com o tipo de veículo na lista (o banco já guarda `type`: `backend/database.py:115`). Mostrar a informação, não a moldura de janela. |
| 17 | baixa | "Já é cliente? Entrar" virou "Entrar" e some no celular | `index.html:219` e `index.html:48-49` (`display:none` abaixo de 40 rem). Em `previa-celular.png` (y 0–60) só aparecem logo, idioma e "Pedir piloto". Regra em `contexto.md:44`. | O cliente atual não acha o acesso pelo celular. | Usar "Já é cliente? Entrar", visível em todas as larguras (detalhe na Frente 4). |

## O que manter
- **"Nenhuma imagem é gravada" como promessa central** (`index.html:231, 238, 352`). É verdade no aparelho do veículo
  (`contexto.md:34`). Nenhum dos concorrentes brasileiros pesquisados ocupa esse espaço.
- **A escada 1 s, 3 s e 6 s** (`index.html:271-273`). É concreta, confere com o código
  (`vision/drowsiness.py:28-30, 71-75`) e é fácil de repetir numa reunião.
- **"Cada motorista é comparado com ele mesmo descansado"** (`index.html:269`). Responde ao alarme falso e respeita o
  motorista ao mesmo tempo.
- **"Pare em local seguro."** (`index.html:281`). O alarme fala com quem dirige, não sobre ele.
- **As frases de honestidade:**
  - "Simulação do sinal" (`index.html:259`);
  - "Tela com dados de demonstração" (`index.html:344`);
  - "Limiares iniciais [...] em validação com gravações reais" (`index.html:384`).

  A Creare põe "Reduza até 40%" no título e a Cobli usa percentuais de um estudo genérico de 2020. Não inventar número
  é diferencial para P4, desde que dito de forma positiva: "o piloto mede na sua frota".
- **A fila sem internet** (`index.html:239, 373`). Importa nas rodovias brasileiras sem sinal.
- **"No suporte, não conta"** (`index.html:389`). Responde ao motorista que usa GPS no celular.
- **A fila "Eventos para revisar"** (`index.html:334-339`). É o que P1 e P3 querem ver; falta mostrar a decisão.
- **"Pedir piloto" como ação principal** (`index.html:220, 233`) e o contato sem cadastro.
- **O evento das 02:14 como fio da história** (`index.html:278, 297, 337, 367`). Dá concretude; só precisa acontecer
  também num ônibus.

## Posicionamento: como os concorrentes se apresentam

| Empresa | Título ou promessa principal | Vídeo e motorista | Prova que usa | Fala com passageiros? | Fonte |
|---|---|---|---|---|---|
| Nauto | "AI Fleet Safety Platform That Prevents Collisions"; "Safety that doesn't feel like spying" | Processa no aparelho. Envia vídeo só em incidente crítico, e gravar é opcional ("AI still works [...] without video"). Não grava áudio. | Caso BPX Energy (62% menos colisões com culpa); cita validação do VTTI | Sim: setor "Passenger Transit" e caso FlixBus | https://www.nauto.com/ · https://venturebeat.com/ai/nauto-aims-to-protect-distracted-drivers-with-in-vehicle-ai-cameras-pointing-inside · https://www.nauto.com/resources/customer-success-story-flixbus |
| Samsara | "Protect drivers, improve coaching, and lower costs." | Vídeo HD e envio automático do clipe do incidente. O "Privacy Mode" desliga a gravação da câmera interna e mantém a detecção, como configuração da frota. | "35–40% de redução agregada de colisões"; 4.800 avaliações | Sim, página de setor | https://www.samsara.com/products/safety/dash-cam · https://www.samsara.com/industries/passenger-transit · https://kb.samsara.com/hc/en-us/articles/32441582990221-Privacy-Mode-Camera-Recording (a página recusou a leitura direta, erro 403; descrição tirada do resumo da busca) |
| Motive | Drowsiness AI com alerta na cabine | "Driver Privacy Mode" detecta sono e celular "without any storage of driver-facing video". A frota escolhe se liga, e um LED verde avisa o motorista. | — | — | https://gomotive.com/blog/advanced-driver-privacy-controls/ |
| Seeing Machines (Guardian) | "Next-generation driver fatigue and distraction solution for fleets" | Alerta sonoro, luz e vibração no banco. Dados e imagens do evento vão para uma central 24 h, cujos analistas avisam o gestor "within minutes". Tem página própria para o motorista ("There is no microphone", "No one can [...] monitor you while you drive"). | "reduz eventos de fadiga em mais de 94%"; 1.200 organizações | Ônibus e caminhão | https://seeingmachines.com/products/fleet/ · https://guardian.seeingmachines.com/driver-info-anz |
| Lytx | "Video Safety and Telematics for Fleets" | O vídeo é o produto | "US$ 1,9 bilhão economizado em sinistros" (amostragem própria) | Sim (transit) | https://www.lytx.com/ |
| Cobli (BR) | "Câmera de fadiga para frotas" | "Os vídeos gravados podem servir como prova em questões jurídicas". Nada sobre LGPD. | "60% de redução no número de colisões", citando estudo de 2020 da Frost & Sullivan | Não cita segmento | https://www.cobli.co/camera-de-fadiga/ |
| Creare (BR) | "Reduza até 40% dos acidentes em sua frota com Sensor de Fadiga" | Central 24/7 que valida os alertas, playback e streaming. No transporte de colaboradores, câmeras de salão e contador de passageiros por crachá. | "até 40%" por relato de clientes; nomes de clientes (JSL, Vale, CPFL) | Sim: "Transporte de colaboradores" | https://crearesistemas.com.br/sensor-de-fadiga/ · https://crearesistemas.com.br/monitoramento-transporte-colaboradores/ |
| Buser (caso brasileiro de passageiros) | Câmera de fadiga em cerca de 200 ônibus, meta de 800. Calibra o rosto nos primeiros 5 minutos. | Vídeo e central que pode substituir o motorista | "80% menos alertas de celular" | Rodoviário | https://mobilidadesampa.com.br/2022/05/buser-cameras-sensor-de-fadiga-onibus/ |

### O que a pesquisa mostra
1. **"Não grava", sozinho, não é exclusivo.**
   - A Nauto processa no aparelho e deixa o vídeo opcional; Motive e Samsara têm modo privacidade.
   - A diferença do DriveSafe é outra: nesses produtos, a privacidade é uma chave que a empresa liga e desliga. No
     DriveSafe, pelo código de hoje, não existe vídeo do motorista para ligar (`contexto.md:34`).
   - Para o sindicato e para o motorista, só a segunda é uma promessa em que dá para acreditar.
2. **No Brasil, o discurso padrão é o oposto do DriveSafe:** vídeo como prova, central 24 h assistindo e percentual de
   redução no título (Cobli, Creare). Nas páginas lidas, ninguém fala com o motorista nem da LGPD. Esse é o espaço.
3. **Passageiros já compram isso no Brasil.** A Buser instalou câmeras em ônibus, e a Creare vende o pacote para quem
   contrata fretamento de colaboradores. Isso sustenta o argumento de P2 ("o cliente corporativo vai pedir"), mas ele
   continua sendo hipótese a confirmar nas conversas pedidas em `personas.md:6-8`. Não pode virar "exigido por lei".
4. **Onde o DriveSafe perde, e o site não deve brigar:** não tem central 24 h, vídeo de acidente, câmera de estrada,
   base instalada nem número. O site deve dizer o que não faz e o que o cliente mantém, sem imitar.

### O espaço do DriveSafe (sem copiar ninguém)
> Gestão de fadiga e celular para frotas de carga e de passageiros, **sem vídeo do motorista**. O alarme acorda quem
> dirige no primeiro segundo; a empresa recebe só o evento e decide na revisão; o motorista sabe exatamente o que sai da
> cabine.

Três diferenças que o código sustenta:
- **Sem vídeo por projeto, não por configuração:** o aparelho transforma a imagem em medidas e envia só eventos
  (`contexto.md:34`).
- **A própria empresa revisa, com decisão registrada.** Não é uma central de terceiros assistindo
  (`backend/database.py:24`; `backend/alert_types.py:40-42`).
- **Funciona sem sinal e calibra com o próprio motorista** (`vision/event_queue.py`; `index.html:269`).

O que não copiar:
- percentual no título (Creare, Seeing Machines);
- "prevents collisions" (Nauto);
- percentual de estudo genérico (Cobli);
- a página do motorista da Seeing Machines, palavra por palavra. Aproveitar só o princípio: falar com o motorista em
  segunda pessoa e listar o que é e o que não é captado.

## Hierarquia de mensagem proposta

### 1. Linha de identificação
Serve para o topo da página inicial, a descrição para buscadores e a apresentação no WhatsApp:

> **Gestão de fadiga e celular ao volante para frotas de carga e de passageiros. Sem vídeo do motorista.**

Passa no teste dos 5 s: diz o que é, para quem, e a diferença. Mas depende da pergunta 5: "sem vídeo" precisa ser regra
permanente do produto.

### 2. Títulos por segmento

**Carga** (P1 e P4)

| Opção | Título | Subtítulo | Por que funciona |
|---|---|---|---|
| C1 | A jornada já está sob controle. A fadiga da madrugada, ainda não. | Um aparelho na cabine acompanha os olhos de quem dirige, toca o alarme no primeiro segundo de olho fechado ou com o celular na mão e manda para a sua equipe só o evento. Nenhuma imagem sai do caminhão. | Usa a dor literal da P1 ("a jornada é controlada, mas a fadiga continua", `personas.md:21`), não promete resultado e cita as duas detecções |
| C2 | O rastreador mostra a velocidade. O DriveSafe mostra o motorista, sem filmar. | Olhos fechando, cabeceio e celular na mão viram alarme na cabine e evento para revisão. Sem sinal na estrada, o aparelho guarda e envia depois. | Posiciona o DriveSafe como complemento do que ela já tem (`personas.md:22, 29`), não como troca; "sem filmar" separa da videotelemetria |

**Passageiros** (P2 e P3)

| Opção | Título | Subtítulo | Por que funciona |
|---|---|---|---|
| T1 (fretamento e rodoviário) | Os passageiros dormem na viagem. O alarme fica acordado com o motorista. | No primeiro segundo de olho fechado, o alarme toca na cabine e a empresa recebe o evento. Sem vídeo do motorista e sem imagem dos passageiros. | Fala de passageiros e de noite (`personas.md:47-49`), com linguagem simples para P2, e põe o alarme ao lado do motorista, não contra ele (P5) |
| T2 (urbano e CCO) | Celular e sono ao volante, avisados na cabine. No CCO, só o que merece revisão. | O operador é alertado na hora. O CCO recebe o evento com nível de risco, e os avisos leves ficam fora da fila. Nenhuma imagem sai do ônibus: nem do motorista, nem de quem está atrás dele. | Usa as palavras dela ("CCO", "operador", `personas.md:78`) e responde o medo de afogar o CCO (`personas.md:66`) com o que o código já faz (`backend/alert_types.py:40-42, 57-58`) |

Linha de apoio para os dois segmentos (é conta, não promessa): **"A 90 km/h, um segundo de olho fechado são 25
metros."** Base: CTB art. 61 e 90 km/h = 25 m/s.

> [!note] Hipótese, confirmar
> Testar as opções C1/C2 e T1/T2 nas 3 a 5 conversas reais previstas em `personas.md:6-8`. Mostrar o topo por 5 s e
> perguntar "o que é e para quem?".

### 3. Três pilares de valor

| Pilar | O que dizer | Base no produto | Persona que convence |
|---|---|---|---|
| **1. Avisa quem dirige, na hora** | O alarme toca na cabine com 1 s de olho fechado (microssono), 3 s (sono) e 6 s (sem resposta). Também com celular na mão, no ouvido ou olhando para ele por mais de 2 s; celular no suporte não conta. Funciona sem internet. | `vision/drowsiness.py:28-30`; `vision/risk.py:124, 131`; `backend/alert_types.py:22-24`; `contexto.md:31, 35` | P2, P3, P5 |
| **2. A empresa recebe o evento, não a imagem** | A imagem vira medidas dentro do aparelho e é descartada. Saem só o evento e as medidas (tipo, hora, duração, nível de risco). Sem som. O motorista registra a autorização, com histórico, e pode exportar os próprios dados. | `contexto.md:34`; `backend/routes/people.py:131-150`; nenhuma captura de áudio no código | P1, P3, P4, P5 |
| **3. Revisão que separa risco de ruído** | Cada motorista é comparado com ele mesmo descansado. Óculos escuros que escondem os olhos geram o aviso "olhos não visíveis", que não conta como sono. Madrugada e mais de 5 h 30 min ao volante pesam no risco. Só eventos de risco 2 ou mais vão para revisão, e cada decisão fica registrada: confirmado, alarme falso ou motorista orientado. | `index.html:269`; `backend/alert_types.py:21, 36, 40-42, 57-58`; `vision/context.py:22`; `backend/database.py:24`; `PENDENCIAS.md:65-66` (limiares de óculos conferidos só em fotos: `vision/visibility.py:5`) | P1, P3, P5 |

### 4. Respostas curtas às objeções
"Pode publicar?" diz se o texto já tem base no produto ou se depende de uma decisão do Matheus (número da pergunta no
fim do relatório).

| Persona | Objeção | Resposta curta (texto para o site) | Base | Pode publicar? |
|---|---|---|---|---|
| P1 | Alarme falso com sol, óculos e noite | "Cada motorista é comparado com ele mesmo descansado. Óculos escuros que escondem os olhos geram o aviso 'olhos não visíveis', que não conta como sono. Para a noite, o sistema aceita câmera infravermelha. Os limiares estão em validação com gravações reais, e o piloto mede o alarme falso na sua frota." | `index.html:269, 384, 391`; `backend/alert_types.py:21`; `vision/visibility.py:5-6` | Sim |
| P1 | Custo por veículo por mês | [modelo de cobrança] | — | Não: pergunta 3 |
| P1 | Parar o caminhão para instalar | [tempo e forma de instalação com o hardware final] | `contexto.md:38` | Não: pergunta 6 |
| P1 | LGPD e consentimento | "Nenhuma imagem sai do veículo e não há gravação de som. O motorista registra a autorização, com o histórico de cada mudança, e pode exportar os próprios dados." | `contexto.md:34`; `backend/routes/people.py:131-150` | Sim, sem "conforme a LGPD" até haver parecer (pergunta 10) |
| P1 | Suporte na estrada | "Sem sinal, o aparelho continua avisando o motorista e guarda os eventos para enviar depois." [suporte técnico: como e em quanto tempo] | `vision/event_queue.py`; `vision/sync.py:58, 82` | Primeira frase sim; o resto, pergunta 7 |
| P1 | Convive com o rastreador | "É um aparelho separado: não depende do rastreador nem da câmera que você já tem." | Aparelho próprio (`contexto.md:28`) | Sim. Não dizer "integra com o seu rastreador": o código só lê um arquivo de velocidade que outro programa precisa escrever (`vision/context.py:32-33`) |
| P2 | "Motorista experiente não precisa disso" | "Microssono não é falta de experiência: são trechos de sono de 1 a 15 segundos, com os olhos fechando. A 90 km/h, cada segundo são 25 metros." | *SLEEP* 2020 (URL no problema 3); CTB art. 61 | Sim |
| P2 | Custo | [preço previsível por veículo] | — | Não: pergunta 3 |
| P2 | Tecnologia complicada | "O motorista não toca em nada: o aparelho se calibra sozinho nos primeiros minutos da viagem. A empresa recebe só o que precisa revisar." | `index.html:269`; `backend/alert_types.py:57-58` | Sim |
| P2 | Tirar o ônibus de rodar para instalar | [instalação] | `contexto.md:38` | Não: pergunta 6 |
| P2 | Suporte fora da capital | [suporte] | — | Não: pergunta 7 |
| P3 | Sindicato dos rodoviários | "Não existe vídeo do motorista para assistir, vazar ou usar como punição. Sai só o evento, que uma pessoa revisa e pode marcar como alarme falso. O motorista autoriza e vê os próprios dados." | `contexto.md:34`; `backend/database.py:24`; `backend/routes/people.py:150` | Sim, se a pergunta 5 confirmar que "sem vídeo" é permanente |
| P3 | Manutenção em 600 veículos | "O painel mostra, para cada aparelho, se a câmera está funcionando, quantos eventos esperam na fila e quando ele se comunicou pela última vez." | `backend/database.py:146-148` | Sim, como função que existe. Não prometer escala testada |
| P3 | Custo em escala | [modelo de cobrança para frota grande] | — | Não: pergunta 3 |
| P3 | Conexão | "Sem sinal, o alarme continua funcionando na cabine e os eventos esperam na fila do aparelho." | `vision/event_queue.py`; `index.html:373` | Sim |
| P3 | Alarme falso no para-e-anda urbano | "Os limiares ainda serão validados com gravações reais. O piloto numa garagem mede quantos alarmes falsos aparecem e ajusta antes de ampliar." | `index.html:384`; `PENDENCIAS.md:145` | Sim. Não dizer que o alarme não toca com o ônibus parado: o alarme não usa velocidade (`vision/risk.py:131`; a velocidade só conta no tempo de direção, `vision/context.py:55`) |
| P4 | Número sem fonte | "Não publicamos percentual de redução de acidentes: ainda não há piloto concluído. O piloto mede na sua frota, antes e depois." [métricas] | `contexto.md:37` | Sim; as métricas dependem da pergunta 2 |
| P4 | Relatório para a seguradora | "Relatório em planilha com os eventos do período e as decisões da revisão." | `contexto.md:36` | Sim. Não dizer "aceito pela seguradora" |
| P4 | Contrato longo | [prazo] | — | Não: pergunta 3 |
| P4 | Depender de empresa nova e de equipamento proprietário caro | "Quem faz" [pergunta 4] + "Roda em hardware de mercado (Raspberry Pi ou computador comum)." | `README.md:3` | Depende das perguntas 4 e 6 (hardware final em aberto) |
| P4 | Riscos jurídicos | "Sem vídeo e sem som, a empresa guarda muito menos dado pessoal do motorista do que numa videotelemetria." [parecer] | `contexto.md:34` | Primeira frase sim; parecer, pergunta 10 |
| P5 | Ser filmado | "Não grava imagem nem som. A câmera vira medidas dentro do aparelho, e a imagem é descartada na hora." | `contexto.md:34`; nenhuma captura de áudio no código | Sim |
| P5 | Ser punido por alarme errado | "Todo evento que chega à empresa passa por uma pessoa, que pode marcar 'alarme falso'. A decisão fica registrada." | `backend/database.py:24`; `backend/alert_types.py:57-58` | Sim. Não prometer "ninguém será punido": isso é política da empresa cliente |
| P5 | "A empresa quer me vigiar" | "Ninguém assiste você dirigindo: o aparelho não transmite vídeo. O alarme existe para te acordar e fazer você parar em segurança." | O aparelho envia só estado e nível de risco em texto (`backend/database.py:153-157`) | Sim |
| P5 | Imagem vazando | "Não existe imagem guardada para vazar." | `contexto.md:34` | Sim |
| P5 | Alarme que atrapalha a direção | "O alarme toca com o olho fechado por 1 segundo, com o celular em uso ou quando o risco sobe. Alarmes repetidos têm intervalo mínimo." | `vision/drowsiness.py:28`; `vision/risk.py:32, 124, 131` | Sim |

### 5. O que NÃO pode ser prometido

| Não dizer | Por quê | Dizer no lugar |
|---|---|---|
| "Em piloto com transportadoras", "usado por", logos, depoimentos | Não há frota em piloto documentada (`contexto.md:37`) | "Protótipo funcionando. Selecionando as primeiras frotas para piloto." |
| Qualquer percentual de redução de acidentes, sinistros, prêmio ou custo; "retorno em X meses" | Não há dado de piloto (`PENDENCIAS.md:212`) | "O piloto mede na sua frota, antes e depois." Se quiser número, usar dado público com fonte (PRF, causa "condutor dormindo"), calculado antes de publicar (`referencias.md:35, 39-41` desta rodada) |
| "Evita acidentes", "salva vidas", "antes de sair da faixa"; detecção de faixa, colisão ou pedestre | O produto avisa o motorista; não vê a estrada nem controla o veículo (`contexto.md:28`) | "Avisa quem dirige no primeiro segundo de olho fechado." |
| "Sem alarme falso", "funciona com qualquer óculos, sol e noite", "precisão de X%" | Limiares iniciais, a validar (`index.html:384`; `vision/visibility.py:5`; `PENDENCIAS.md:145`) | "Limiares em validação com gravações reais; o piloto mede o alarme falso." |
| Detecção de droga, álcool, doença ou "estado alterado" | "Não é diagnóstico nem exame de drogas" (`contexto.md:33`; `backend/alert_types.py:19`) | Não citar no site de vendas. Se citar: "sinais compatíveis com ativação atípica, sem diagnóstico". |
| "Conforme a LGPD", "100% LGPD", "aprovado pelo sindicato" | Não há parecer, e o consentimento na relação de emprego é base frágil (URL no problema 13) | "Autorização do motorista registrada, com histórico; ele exporta os próprios dados." |
| Relatórios por garagem, linha ou turno | O banco não tem esses campos (`backend/database.py:91-116`), e os filtros de relatório ainda estão pendentes (`PENDENCIAS.md:191`) | "Relatório em planilha com os eventos e as decisões da revisão." |
| "Integra com o seu rastreador", "relatório aceito pela seguradora", "desconto no seguro" | O código só lê um arquivo de velocidade escrito por outro programa (`vision/context.py:32-33`); nenhuma seguradora avaliou | "Aparelho separado, que convive com o rastreador que você já tem." |
| Central 24 h, "nossa equipe acompanha sua frota", "ligamos para o motorista" | Não existe. É o que Creare e Seeing Machines vendem | Deixar claro que a revisão é da empresa. |
| "O gestor é avisado imediatamente", sem ressalva | Com sinal, o envio acontece a cada 5 s; sem sinal, o evento espera na fila (`vision/sync.py:58, 82`) | "Em segundos com sinal; sem sinal, quando ele voltar." |
| "Não toca com o veículo parado" | O alarme não usa velocidade (`vision/risk.py:131`; `vision/context.py:55`) | Não citar. |
| Preço, comodato, prazo de contrato, tempo de instalação, suporte nacional, garantia | Hardware e modelo comercial em aberto (`contexto.md:38`) | Só depois das perguntas 3, 6 e 7. |
| Formato do painel ("acesse pelo navegador", "baixe o app") | Formato em aberto; o Matheus não quer web (`PENDENCIAS.md:7`) | "Painel da empresa", sem dizer onde roda. |
| Homologação, certificação, "padrão Euro NCAP" | Não há. O código cita o protocolo Euro NCAP 2026 só como origem dos tempos (`vision/drowsiness.py:4`), e esse protocolo é feito para carros (https://www.euroncap.com/media/85854/euro-ncap-protocol-safe-driving-driver-engagement-v10.pdf) | No máximo, em ficha técnica: "tempos de partida baseados no protocolo de monitoramento do motorista do Euro NCAP, em validação para cabine de caminhão e ônibus" (conferir com a Frente 5). |
| "Escala para centenas de veículos", como fato testado | Não há teste de carga na lista de testes (`PENDENCIAS.md:19`) | "Plataforma para várias empresas e frotas" (`contexto.md:36`). |
| "Nunca processamos vídeo" | A ferramenta interna de teste da equipe analisa vídeos enviados e os apaga ao terminar (`backend/test_session.py:3-4`) | "Nenhuma imagem sai do veículo." |

## Recomendações para a próxima versão (em ordem de prioridade)
1. **Apagar hoje as afirmações falsas e o público antigo** (`index.html:229, 404, 412`), antes de qualquer redesenho.
2. **Decidir com o Matheus a entrada por segmento** (Carga e Passageiros; se o urbano entra no primeiro ano) e escrever
   título, subtítulo e chamada de cada um a partir da hierarquia acima.
   - Cada título precisa de uma cena real do segmento (detalhe na Frente 3).
   - O rosto em pontos do topo não diz segmento nenhum (`previa-topo.png`, x 655–1310).
3. **Pôr "sono e celular" juntos** desde o topo e no painel de demonstração.
4. **Escrever a seção "Para quem dirige"** e mostrar decisões de revisão no painel ("Alarme falso", "Motorista
   orientado").
5. **Montar o bloco de perguntas** com as respostas verdadeiras da tabela acima. O que depende do Matheus só entra
   depois da resposta dele.
6. **Reescrever a diferença frente à videotelemetria como escolha:** "sem vídeo do motorista, por projeto", com a troca
   assumida ("para vídeo de acidente, mantenha a sua câmera de estrada").
7. **Traduzir o jargão** (PERCLOS, EAR, JSON, sistemas operacionais) e levar a ficha técnica para uma página própria ou
   um bloco recolhido.
8. **Criar os blocos "Quem faz" e "Como é o piloto"**, com o número real de WhatsApp.
9. **Corrigir as frases imprecisas:** título do topo, "imediatamente", "12 pontos", "sair da faixa" e "conforme a
   LGPD". Voltar o aviso "não faz diagnóstico e não substitui descanso e pausas".
10. **Cuidado com o mapa-múndi pedido nesta rodada** (`referencias.md:4-5`): ele não pode sugerir presença
    internacional que o produto não tem. O mapa que vende para P1, P2 e P3 é o das rodovias e cidades onde elas rodam;
    o mundo, se entrar, é contexto com fonte (`referencias.md:37`), não promessa de alcance.
11. **Antes de fechar o texto, validar** as opções de título e as respostas às objeções nas 3 a 5 conversas reais de
    `personas.md:6-8`.

## Perguntas que só o Matheus responde
1. **Status real:** existe alguma frota usando o DriveSafe hoje, mesmo informalmente? Se não, qual texto de status você
   aceita ("protótipo funcionando", "selecionando frotas para piloto")?
2. **Piloto:** é pago ou gratuito? Quantos veículos, por quanto tempo, e o que o relatório mede antes e depois?
3. **Cobrança:** o modelo é por veículo por mês, comodato ou compra? Qual o prazo de contrato? Isso pode aparecer no site
   (ao menos o modelo, sem valor)?
4. **Quem aparece como responsável:** nomes, cidade, CNPJ? Existe parceria (universidade, incubadora) que possa entrar
   como credencial?
5. **Vídeo:** "sem vídeo do motorista" é regra permanente do produto, mesmo se um cliente pedir clipe de evento? A
   resposta define se isso vira promessa de marca.
6. **Hardware e instalação:** quem instala, quanto tempo leva, precisa parar o veículo? Dá para dizer "hardware de
   mercado"?
7. **Suporte:** como funciona fora da capital, e em quanto tempo um aparelho é trocado?
8. **Segmentos:** carga e passageiros têm o mesmo peso? O urbano (P3, centenas de ônibus) é público do primeiro ano ou só
   fretamento e rodoviário? Vans e última milha (P4) entram?
9. **Contato:** qual é o número de WhatsApp comercial e o horário de atendimento?
10. **Jurídico:** há parecer sobre a base legal na LGPD e sobre o uso na relação de trabalho? Até lá, pode-se citar a LGPD
    no site?
11. **Motorista:** você aceita uma seção falando direto com o motorista, em segunda pessoa, num site de venda para
    empresas?
12. **Rastreador:** integrar com o rastreador que o cliente já usa é algo que você quer oferecer no piloto?
