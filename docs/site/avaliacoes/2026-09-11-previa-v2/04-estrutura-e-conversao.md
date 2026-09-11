# Frente 4 · Estrutura, navegação e conversão B2B
Avaliador: agente 4 · 11/09/2026 · versão avaliada: `site-drivesafe/previa/v2/index.html` (prints `previa-topo.png`,
`previa-desktop.png` com 1440 × 5200 px e `previa-celular.png` com 400 × 7400 px)

> Convenções deste relatório
> - Linha sem caminho = `site-drivesafe/previa/v2/index.html`.
> - Região de print em pixels reais, contando do topo (y).
> - Veracidade de cada frase é da frente 5; visual, da frente 2; imagens, da frente 3. Aqui só entra o que muda a
>   jornada, a navegação e a conversão.
> - O requisito novo do Matheus, recebido durante a avaliação ("algo referente a estradas, mapa-múndi etc."), está
>   na entrega E e nas seções S1, S2, S7 e S10 do roteiro.

## Nota geral: 3/10
A página mostra bem o que a câmera mede, mas não leva ninguém a lugar nenhum: o único caminho de conversão termina
num `href="#"`, o transporte de passageiros não existe e falta tudo o que um comitê de compra, um diretor financeiro ou
um motorista precisam para decidir.

## Notas por critério
| Critério | Nota | Por quê | Evidência |
|---|---|---|---|
| Jornada e ordem das seções | 4 | É um passeio pelo produto (demonstração → cabine → painel → privacidade → especificações → piloto). Faltam "para quem", objeções, custo, instalação e quem está por trás. O pedido de piloto é a última seção e não funciona. | 226–408; menu 211–216 sem item de piloto |
| Escaneabilidade | 5 | Títulos curtos e poucos parágrafos. Mas os h2 são frases de efeito que não dizem público nem benefício, há jargão sem tradução (PERCLOS, EAR, JSON) e rótulos mono de 0,66 a 0,8rem. Lendo só os títulos, ninguém descobre que o produto detecta celular. | h2 em 268, 297, 352, 383, 403; PERCLOS em 255, 327, 388; EAR em 454; JSON em 365–371; `.metric span` 0,66rem em 83 |
| Caminhos para carga e passageiros | 1 | Nenhuma ocorrência de ônibus, passageiro, fretamento, urbano ou van. "Caminhão" aparece 3 vezes e a chamada final é "Comece com cinco caminhões". | 268, 352, 403 |
| Demonstração de como funciona | 5 | É a melhor parte: sinal do olho → alarme na cabine → painel → o que sai do veículo. Mas não mostra onde a câmera fica, o celular, o resultado da revisão nem o que acontece sem sinal no meio da história. No celular, o painel perde a frota e as curvas. O quadro do alarme mostra "Abertura do olho 100%" junto de "Crítico". | 243–259, 276–289, 300–344, 355–375; CSS 108–109 e 151; `previa-topo.png` y≈550–620 |
| Provas | 2 | Só dados de demonstração. "Em piloto com transportadoras" não tem frota documentada e "baseados em literatura" não cita qual. Não aparece equipe, teste nem fonte com link, e o repositório tem tudo isso. | 229, 384, 412; `contexto.md:37`; `README.md:110-138` e `README.md:406-447` |
| Chamadas (piloto, WhatsApp, Entrar) | 1 | WhatsApp sem link, "Entrar" apontando para "#" e escondido no celular, idioma como texto, nenhum `tel:`, nenhuma mensagem pronta por segmento. | 406, 219, 48–49, 218, 412 |
| Celular (400 px) | 3 | Sem menu e sem botão de menu, sem "Entrar", botão do cabeçalho com 40 px, painel sem lista de veículos, rótulos do gráfico distorcidos, chamada final a ~6.030 px do topo. A favor: cabeçalho fixo com "Pedir piloto" e botão final de 48 px em largura total. | 41–50, 108–109, 151, 331 e 540; `previa-celular.png` y≈0–60, 2625–3230, 3020–3030, 6030–6077 |
| Conteúdo de apoio à decisão | 1 | Só a ficha de especificações. Não há piloto (duração, veículos, entregas), cobrança, instalação, suporte, perguntas frequentes, LGPD além de uma frase, nem quem está por trás. | 379–397, 353, 404 |
| Microcopy | 4 | Há boas frases ("Pare em local seguro", "No suporte, não conta", "Tela com dados de demonstração"). Mas "gestor avisado imediatamente" contradiz a fila sem internet, "Entrar" substitui "Já é cliente? Entrar", "Pedir piloto" vira "Falar pelo WhatsApp", universidades e editais estão fora do foco, "O que ele mede" não tem sujeito e a marca oscila entre "DriveSafe" e "DriveSafe AI". | 281, 389, 344; 273 × 373; 219; 220 × 406; 404; 383; 209 × 412 |
| Como medir a conversão | 0 | Nenhum analytics, evento, identificador nas chamadas ou UTM. E sem destino não há o que medir. | 1–572 sem script de medição; 406 |

## Leitura por persona

Simulação com os prints de 1440 px e 400 px. "Encontra" = a resposta está na página e dá para achar rolando.

### P1 · Renata (carga, 190 cavalos mecânicos, decide em comitê): 4/10
| Pergunta dela (`personas.md:24-35`) | Onde está na v2 | Resultado |
|---|---|---|
| É para frota pesada? | Só no h2 da 2ª seção: "antes de o caminhão sair da faixa" (268). O topo fala de "frota" (231) | Encontra tarde e sem certeza |
| O que detecta e como o gestor fica sabendo? | Sono: demonstração (243–259) e escada 1/3/6 s (270–274). Celular: só uma linha da ficha (389). Gestor: painel (293–346) | Encontra o sono; o celular passa despercebido |
| Não grava imagem? Por que isso reduz a resistência? | 231, 238, 352–375 | Encontra "não grava"; não encontra o argumento para sindicato e motoristas |
| Como é o piloto e quem está por trás? | 403–404: "cinco caminhões, instalação acompanhada, calibração, relatório do período" | Sem duração, custo nem critério; quem está por trás: nada |
| Convive com o rastreador? | Nada | Não encontra (o código aceita a velocidade vinda de outro programa: `vision/context.py:32-33`) |
| Objeções: alarme falso (sol, óculos, noite), custo por veículo, parar para instalar, LGPD, suporte na estrada | Óculos: "óculos escuros detectados" (391), ambíguo. O resto: nada | Objeções abertas |

- **Onde se perde:** na ficha (379–397). "Roda em Raspberry Pi, Linux, Windows e macOS" soa como projeto de bancada para
  quem compara com as videotelemetrias do mercado. E não há nada para mandar ao comitê: nem URL específica, nem PDF.
- **Próximo passo:** "Pedir piloto" (220) → seção final → "Falar pelo WhatsApp" (406) sem destino. Beco sem saída.

### P2 · Carlos (fretamento e turismo, 38 ônibus): 2/10
| Pergunta dela (`personas.md:47-53`) | Onde está na v2 | Resultado |
|---|---|---|
| É para ônibus? | Nenhuma ocorrência de ônibus ou passageiro; "caminhão" em 268, 352 e 403 | Conclui que não é para ele na 2ª seção (`previa-desktop.png` y≈975–1050) |
| Protege os passageiros e funciona à noite? | O horário 02:14 sugere noite (278, 297); passageiros: nada | Não encontra |
| Instalação simples e preço previsível? | Nada | Não encontra |
| Argumento para vender ao cliente corporativo? | Nada | Não encontra |

- **Onde se perde:** no jargão ("EAR 0,33", "PERCLOS 60 s" e o bloco JSON: 454, 255, 365–371), justamente o que ele
  desconfia (`personas.md:56`).
- **Próximo passo:** o convite é "Comece com cinco caminhões" (403). Nenhum para ele. Ele prefere falar direto, mas não
  há `tel:`.

### P3 · Juliana (CCO, 620 ônibus urbanos, 9 garagens): 3/10
| Pergunta dela (`personas.md:68-76`) | Onde está na v2 | Resultado |
|---|---|---|
| Triagem e prioridade dos eventos | Lista por risco e chip "Em risco 3" (305–314); fila "Eventos para revisar" (333–339) | Encontra no computador; no celular a lista some (108–109) |
| Revisão com decisão registrada | Só botões "Revisar" que não fazem nada (336–338) | Não vê confirmado, alarme falso e motorista orientado, que existem no produto (`backend/routes/alerts.py:23-24`) |
| Relatórios por garagem, linha e turno | Nada | Não encontra, e o backend não tem esses campos |
| Escala para centenas de veículos; convivência com câmeras e GPS | Painel de exemplo com 24 veículos (304); integração: nada | Não encontra |
| Privacidade dos passageiros | "CÂMERA DA CABINE · OLHOS DO MOTORISTA" (245) | Deduz; não está dito |
| Conexão, alarme falso no para-e-anda, sindicato | Fila sem internet (373); o resto, nada | Parcial |

- **Onde se perde:** "O gestor é avisado no painel imediatamente" (273) contra "Sem internet, fica na fila" (373). Para
  quem teme um CCO afogado ou cego, a contradição pesa.
- **Próximo passo:** o piloto proposto é "cinco caminhões" (403); o dela é "uma garagem" (`personas.md:77`).

### P4 · Marcos (diretor financeiro, 70 caminhões e 140 vans e VUCs): 2/10
| Pergunta dela (`personas.md:89-95`) | Onde está na v2 | Resultado |
|---|---|---|
| Como é cobrado (por veículo, comodato) e qual o prazo | Nada | Não encontra |
| O que o piloto mede antes e depois | "relatório do período" (404) | Vago |
| Relatório que a seguradora aceite | Nada. O produto exporta planilha com 16 colunas (`backend/routes/alerts.py:97-101`) | Não encontra |
| Custo de instalação | Nada | Não encontra |
| Riscos de LGPD e trabalhistas; agregados | "conforme a LGPD" (353), sem detalhe; a revisão jurídica está pendente (`Obsidian/DriveSafe AI - Monitoramento de Motoristas/00 - DriveSafe AI.md:85`) | Afirmação que ele não consegue checar |
| Continuidade (empresa nova) | Nada: sem equipe, CNPJ ou cidade | Não encontra |

- **Onde se perde:** em "Em piloto com transportadoras" (229). Ele pede a referência e ela não existe
  (`contexto.md:37`). O site ganha pontos por não prometer "reduz X%", mas perde tudo nessa linha.
- **Próximo passo:** nenhum feito para ele. Não há material para receber nem página para encaminhar.

### P5 · José (motorista, voz da CIPA e do sindicato): 3/10
| Pergunta dela (`personas.md:109-114`) | Onde está na v2 | Resultado |
|---|---|---|
| Não grava imagem nem som? | Imagem: 231, 238, 352, 359. Som: nada | Metade |
| O alarme é para mim? | Tela da cabine: "Pare em local seguro" (281) | Encontra. É o melhor momento da página para ele |
| Eu autorizo e posso ver os meus dados? | "com o consentimento do motorista" (353, 394). Ver os próprios dados: nada | A v1 dizia "O motorista vê os próprios dados e o que autorizou" (`site-drivesafe/previa/index.html:254`); a v2 perdeu |
| Sol e óculos escuros viram sono? | "óculos escuros detectados" (391) | Soa como mais uma coisa detectada contra ele |
| O evento é revisado antes de qualquer conversa? | Nada | Não encontra |

- **Onde se perde:** no painel, que lista nomes com "Crítico" e "o dia de cada motorista" (298, 307–312). É a visão de
  quem vigia, sem a parte que o protege.
- **Próximo passo:** nenhum. Não há página que o gestor possa mandar aos motoristas.

## Problemas, do mais grave ao menos grave
| # | Gravidade | Problema | Evidência | Impacto | Correção concreta |
|---|---|---|---|---|---|
| 1 | crítica | Caminho de conversão morto | "Falar pelo WhatsApp" com `href="#"` (406) é a única saída de "Pedir piloto" (220 e 233 → `#piloto`, 399). Nenhum `tel:` na página. `PENDENCIAS.md:210` já registrava "botão sem link" | Nenhum contato é possível: a página inteira trabalha para um clique que volta ao topo | Link `https://wa.me/55DDNNNNNNNNN?text=` com mensagem pronta por segmento (entrega H), "Ligar" com `tel:` e o número em texto no rodapé e na seção de piloto. O número é o de `DRIVESAFE_CONTATO_CELULAR` (`backend/config.py:24-27`), que só o Matheus tem |
| 2 | crítica | Transporte de passageiros não existe | Zero ocorrências de ônibus, passageiro, fretamento, urbano ou van; "caminhão" em 268, 352 e 403; chamada "Comece com cinco caminhões" (403) | P2 e P3, dois dos quatro compradores, saem na 2ª seção | Portas de segmento no topo e 3 páginas de segmento (entregas C e D). Nas seções comuns, "veículo" e "cabine" no lugar de "caminhão" |
| 3 | alta | Celular sem navegação e sem "Já é cliente? Entrar" | `.menu` some abaixo de 992 px e não há botão (44–45, 211–216); `.login` some abaixo de 640 px (48–49) e aponta para "#" (219); o texto é "Entrar", não "Já é cliente? Entrar"; "PT · EN" é `<span>` (218, 412); `previa-celular.png` y≈0–60 | No celular (onde está o WhatsApp e onde o motorista abriria o próprio painel) só dá para rolar; o cliente não entra; ninguém troca o idioma | Botão "Menu" com `aria-expanded` abrindo todos os links, "Já é cliente? Entrar", PT e EN e "Ligar" (padrão do próprio Matheus: `regras-de-componentes.md:87`). "Já é cliente? Entrar" também no rodapé. PT e EN como links para `/pt/...` e `/en/...`, com o idioma atual marcado |
| 4 | alta | Nenhum conteúdo de apoio à decisão | A página só tem especificações (379–397), o piloto em uma frase (404) e a LGPD em uma frase (353) | P1 não tem o que levar ao comitê; P4 não tem cobrança, prazo nem risco jurídico; P3 não tem escala nem integração | Páginas `/piloto`, `/perguntas-frequentes`, `/privacidade`, `/quem-somos` e ficha técnica completa (entrega G, com o que depende do Matheus) |
| 5 | alta | Prova não verificável no lugar da prova que existe | "Em piloto com transportadoras" (229) e "protótipo em piloto" (412) contra "Não há frota em piloto documentada" (`contexto.md:37`); "baseados em literatura" sem citar (384) | Na primeira pergunta de P4 ("quais?"), a credibilidade cai. A prova real (fontes dos limiares, testes, desempenho medido) fica escondida | Prova conferível: fonte de cada limiar com link (`README.md:110-138`), "protótipo com testes automáticos" (`PENDENCIAS.md:19`), "piloto aberto para as primeiras frotas" e a equipe com nome. Texto final com a frente 5 |
| 6 | alta | O uso de celular, dor central de P1 e P3, some | Única menção: linha da ficha (389). Demonstração, cabine e painel só falam de olhos | Metade do valor do produto não aparece; P3 ("celular ao volante e distração", `personas.md:62`) não se reconhece | Estado de celular na sequência da cabine: na mão, no ouvido, olhando por mais de 2 s; no suporte não conta; parado não conta quando há velocidade do veículo (`vision/engine.py:109-110`). Um evento de celular no painel de exemplo |
| 7 | média | Nada para o motorista, e regressão frente à v1 | v1: "O motorista vê os próprios dados e o que autorizou" (`site-drivesafe/previa/index.html:254`), removido. v2: nomes com "Crítico" (307) e "o dia de cada motorista" (298); revisão só como botão (336–338) | P5 derruba a adoção e P1 a P4 ficam sem argumento para o sindicato | Seção "Para o motorista" na home e página `/motoristas` para o gestor compartilhar (roteiro S5). Mostrar o resultado da revisão: confirmado, alarme falso, motorista orientado (`backend/routes/alerts.py:23-24`) |
| 8 | média | Contradição sobre o aviso ao gestor | "O gestor é avisado no painel imediatamente" (273) × "Sem internet, fica na fila" (373). No código: envio a cada 5 s com conexão e novas tentativas até 5 min sem ela (`vision/sync.py:58, 82`) | P1 e P3 leem uma promessa de tempo real que falha justamente na serra sem sinal | "Com sinal, o gestor vê em segundos. Sem sinal, o evento espera no aparelho e chega com a hora certa quando a conexão volta" (`backend/routes/device_api.py:61-69`) |
| 9 | média | Painel no celular perde o que o título promete | Lista de veículos some abaixo de 896 px (108–109); detalhe e curva somem abaixo de 768 px (151); "A frota inteira ao vivo" (297) com um veículo; rótulos do "Dia do motorista" distorcidos (texto dentro de SVG com `preserveAspectRatio="none"`, 331 e 540); `previa-celular.png` y≈2625–3230 | O argumento do painel cai no aparelho em que P2 abre o link recebido por WhatsApp | No celular: 3 veículos em lista compacta acima do veículo selecionado; eventos em cartão com tipo, duração e situação da revisão; rótulos do eixo em HTML, fora do SVG esticado |
| 10 | média | Botões falsos e janela de programa | "Revisar" (336–338, estilo em 150), chips de filtro (305, estilo em 114–115) e "— ▢ ✕" (301) parecem clicáveis e não fazem nada. A janela assume "programa de computador" com o formato do painel em aberto (`PENDENCIAS.md:7`) | Toque sem resposta no celular parece site quebrado; e o site promete um formato que não foi decidido | Tirar a aparência de botão (ou legendar "exemplo") e trocar "Revisar" pela situação da revisão. Remover os controles de janela até definir o formato |
| 11 | média | A chamada final fala com público fora do foco | "Também atendemos universidades e editais de pesquisa" (404) contra `contexto.md:42-43` | Dilui a mensagem no pedido de piloto e soa como projeto acadêmico para P4 | Remover. Se voltar, em página própria e fora do caminho do comprador |
| 12 | média | Jargão técnico sem tradução no caminho do comprador | "PERCLOS 60 s" (255), "PERCLOS 3 min" (327), "PERCLOS" (388), "EAR 0,33" (454), bloco JSON (365–371) | P2 desconfia, P4 não entende, P5 se assusta | Na home, palavras simples ("tempo de olho quase fechado nos últimos 3 min"); termo técnico entre parênteses só na ficha técnica; o JSON vira a lista "o que a empresa recebe: tipo, hora, duração, nível, veículo" |
| 13 | média | Quadro da demonstração com estado contraditório | "Abertura do olho 100%", "Olhos fechados 1,2 s" e "Crítico" ao mesmo tempo (`previa-topo.png` y≈550–620); o alarme fica ativo de 5,85 s a 8,3 s, depois de o olho reabrir (486, 499–505) | Quem escaneia lê "olho aberto e risco crítico" e desconfia do sistema | Rótulos "Último fechamento: 1,2 s" e "Alarme tocando", ou congelar o quadro no olho fechado |
| 14 | baixa | Rodapé sem saída e sem identidade da empresa | 411–413: só "DriveSafe AI · protótipo em piloto" e "PT · EN" | Venda B2B sem CNPJ, cidade, contato, política de privacidade e LinkedIn, que é onde P1 se informa (`personas.md:34`) | Rodapé com WhatsApp e número em texto, "Ligar", "Já é cliente? Entrar", privacidade, LinkedIn, CNPJ e cidade |
| 15 | baixa | Alvo de toque no limite | Botão do cabeçalho com 40 px de altura (50); `previa-celular.png` y≈10–50 | Passa no mínimo AA de 24 px ([WCAG 2.2, 2.5.8](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html)), mas fica abaixo dos 44 pt que a Apple recomenda ([HIG](https://developer.apple.com/design/human-interface-guidelines/accessibility)), no botão mais tocado | `min-height: 44px` nos botões e 48 px no principal |
| 16 | baixa | Sem medição | Nenhum script nem atributo de evento (1–572) | Não dá para saber de onde vêm as conversas nem qual segmento responde | Plano da entrega H |
| 17 | baixa | Título sugere função que o produto não tem | "O aviso chega antes de o caminhão sair da faixa." (268); o produto não mede faixa (`contexto.md:28-33`) | P1 pode entender detecção de saída de faixa e cobrar isso no piloto | "O alarme toca no primeiro segundo de olhos fechados." Validar com a frente 5 |

## O que manter
- **Mostrar o produto funcionando em vez de foto de banco:** a demonstração do sinal (243–259) com legendas honestas
  ("Simulação do sinal", 259; "Tela com dados de demonstração", 344).
- **A escada 1 s / 3 s / 6 s** (270–274): lida em 3 segundos e fiel ao código (`README.md:110`).
- **A divisão "fica no veículo / sai para a frota"** (355–375): é o melhor argumento para P5 e para o sindicato. Só
  traduzir o JSON.
- **Microcopy que respeita o motorista e antecipa objeção:** "Pare em local seguro" (281) e "No suporte, não conta" (389).
- **Cabeçalho fixo com a chamada sempre à vista** (41, 220), desde que ela tenha destino.
- **A ressalva "em validação com gravações reais"** (384): honestidade que P4 valoriza.
- **Não prometer "reduz X% dos acidentes":** é diferencial real contra Creare ("até 40%") e Seeing Machines ("mais de
  94%"), ver entrega J.
- **A fila de revisão no painel** (333–339): princípio certo para P3. Falta mostrar o resultado.

## Recomendações para a próxima versão (em ordem de prioridade)
1. **Consertar a conversão antes de qualquer visual:** número, links `wa.me` com mensagem por segmento, `tel:`, "Já é
   cliente? Entrar" com destino, PT e EN de verdade e menu no celular (problemas 1 e 3; entrega A).
2. **Separar os caminhos:** portas de segmento no topo e 3 páginas (carga e logística; fretamento e rodoviário; ônibus
   urbano) com a mesma espinha, trocando vocabulário, cena, objeções e piloto (problema 2; entregas C e D).
3. **Usar uma viagem noturna como fio da página**, em mapa desenhado com a malha real, demonstrando cabine → alarme →
   trecho sem sinal → gestor revisa. No celular, linha do tempo vertical (entregas E e F).
4. **Pôr o celular e o motorista dentro da história:** estado de celular na cabine, seção e página para o motorista e
   resultado da revisão no painel (problemas 6 e 7).
5. **Escrever o conteúdo de decisão com as respostas do Matheus:** piloto, cobrança, instalação e suporte, perguntas
   frequentes, privacidade, ficha técnica, quem somos (entrega G).
6. **Trocar prova não verificável por prova conferível:** fontes dos limiares com link (mapa-múndi das fontes), testes e
   equipe. Tirar "em piloto com transportadoras" até existir (problema 5).
7. **Limpar a microcopy:** contradição do aviso ao gestor, jargão, botões falsos, universidades, nome único da marca
   (problemas 8, 10 a 13 e 17).
8. **Medir desde o primeiro dia sem rastrear pessoas:** eventos de clique, UTM, código na mensagem do WhatsApp e
   planilha do funil (entrega H).

## Entregas da frente 4

### A. Inventário de chamadas e navegação no HTML
| # | Elemento | Linha | O que está errado | Correção |
|---|---|---|---|---|
| 1 | Botão "Falar pelo WhatsApp" | 406 | `href="#"`: volta ao topo | `https://wa.me/55DDNNNNNNNNN?text=<mensagem do segmento>` com `target="_blank"` e `rel="noopener"`. O app já monta o link assim (`backend/main.py:99`; `webapp/assets/js/views/login.js:31-33`) |
| 2 | "Pedir piloto" no cabeçalho e no topo | 220, 233 | Levam a `#piloto` (399), cuja única saída é o item 1 | Apontar direto para o WhatsApp com a mensagem de piloto, ou para `/piloto` com o botão funcionando |
| 3 | "Entrar" | 219 | `href="#"`; texto sem "Já é cliente?" | "Já é cliente? Entrar" → `/entrar` (como acessar; o acesso é criado pela equipe, `backend/config.py:24`) ou o endereço do painel |
| 4 | "Entrar" no celular | 48–49 | `display: none` abaixo de 640 px | Levar para o menu e para o rodapé |
| 5 | Menu no celular | 44–45, 211–216 | `display: none` abaixo de 992 px, sem botão | Botão "Menu" com `aria-expanded` e `aria-controls`, que fecha no Esc |
| 6 | Seletor de idioma | 218, 412 | `<span>` "PT · EN", sem idioma marcado | Links `/pt/...` e `/en/...` com `hreflang` e `aria-current` |
| 7 | Logo | 207 | `href="#"` | `/` (obrigatório quando houver mais de uma página) |
| 8 | "Revisar" | 336–338 (estilo em 150) | Parece botão e não faz nada | Mostrar a situação da revisão, sem cara de botão |
| 9 | Chips "Todos / Em risco 3 / Parados" | 305 (estilo em 114–115) | Parecem filtros | Idem |
| 10 | Controles "— ▢ ✕" | 301 | Parecem clicáveis e fixam o formato "programa de computador" | Remover |
| 11 | Menu | 211–216 | Só âncoras de produto; sem piloto, segmentos, perguntas ou contato | Ver o mapa do site (entrega D) |
| 12 | Telefone | nenhuma | Nenhum `tel:`, embora o contato seja "celular ou WhatsApp" (`contexto.md:44`) | "Ligar" com `tel:+55...` no menu, na seção de piloto e no rodapé |
| 13 | Rodapé | 411–413 | Nenhum link | Contato, "Já é cliente? Entrar", privacidade, LinkedIn, CNPJ |

### B. Celular (400 px): navegação, toque e o que some
| O quê | Computador (1440 px) | Celular (400 px) | Evidência | Efeito na venda |
|---|---|---|---|---|
| Menu de seções | 4 links no cabeçalho | Some, sem botão | 44–45; `previa-celular.png` y≈0–60 | Só rolando; ninguém pula para privacidade ou piloto |
| "Entrar" | Visível, mas `href="#"` | Some abaixo de 640 px | 48–49, 219 | Cliente e motorista sem porta no aparelho que mais usam |
| PT · EN | Texto | Texto | 218, 412 | Nenhum idioma troca |
| "Pedir piloto" do cabeçalho | 40 px | 40 px, fixo no topo | 41, 50; y≈10–50 | Bom estar fixo; pequeno para o botão mais tocado |
| Demonstração | Ao lado do título | Entra no fim da primeira tela (y≈645); métricas 2×2 com rótulos de ~10,5 px; "OLHO DIREITO · EAR 0,33" com ~6 px (13 unidades num SVG de 800 desenhado em ~360 px) | 83, 89–93, 442; y≈645–1170 e y≈836 | Leitura difícil; o rótulo técnico vira ruído |
| Lista de veículos do painel | 7 veículos | Some abaixo de 896 px | 108–109; y≈2625–3230 | "A frota inteira ao vivo" com um veículo só |
| Detalhe e curva do evento | Visíveis | Somem abaixo de 768 px | 151; y≈3060–3230 | A curva prometida em 298 não aparece |
| Rótulos 00–24 do "Dia do motorista" | Legíveis | Esticados e ilegíveis | 331, 540; y≈3020–3030 | Ruído visual |
| "Revisar" | Parece botão | Parece botão | 336–338 | Toque sem resposta |
| "Falar pelo WhatsApp" final | 48 px, à direita | 48 px, largura total, y≈6030–6077 | 53, 196–197, 406 | Tamanho certo, destino nenhum |
| Comprimento da página | ≈4.800 px (≈5 telas de 900 px) | ≈6.200 px (≈7,5 telas de 830 px) | Fim do conteúdo em `previa-desktop.png` y≈4800 e `previa-celular.png` y≈6200; o resto do print é fundo vazio | O único pedido de contato fica no fim da rolagem mais longa |

### C. Uma página ou páginas por segmento

**Resposta:** uma home que distribui por segmento, 3 páginas de segmento e páginas comuns por tema. Não um site por
segmento.

| Persona | Ciclo de compra | O que precisa receber ou encaminhar | Consequência para a estrutura |
|---|---|---|---|
| P1 · carga | Longo: comitê, compara com videotelemetrias, piloto de 5 a 10 veículos com relatório (`personas.md:32-33`). Chega por LinkedIn, WhatsApp, Fenatran e seguradora (`personas.md:34`) | Link específico para frota pesada e material de piloto para o comitê | Página própria, com URL e prévia de link próprias (título e imagem que aparecem no WhatsApp e no LinkedIn), mais `/piloto` e a ficha técnica em PDF |
| P2 · fretamento | Curto: decide sozinho ou com o filho, por indicação e vendo funcionar na garagem (`personas.md:54`) | Link que um colega manda dizendo "é para ônibus"; ligação | Página curta, sem jargão, com ônibus desde a primeira imagem, "Ligar" ao lado do WhatsApp e oferta de demonstração na garagem |
| P3 · urbano | Longo e formal: diretoria, processo interno de compra, piloto em uma garagem (`personas.md:77`) | Ficha técnica, privacidade, escala, integração, proposta | Página com triagem do CCO, escala e piloto por garagem, com links para ficha técnica e privacidade |
| P4 · financeiro | Precisa justificar o investimento com retorno e ouve a corretora (`personas.md:86, 97`) | Cobrança, prazo, o que o piloto mede, continuidade | Não é segmento, é tema: `/piloto` (com cobrança) e `/quem-somos`, com link a partir de todas as páginas |
| P5 · motorista | Não compra, mas pode derrubar a adoção (`personas.md:102`) | Uma página que o gestor mande no grupo dos motoristas ou imprima para o mural | `/motoristas`, em linguagem simples e fácil de compartilhar |

**Por que não uma página única:**
- As três operações falam línguas diferentes: "eventos por 10 mil km" (`personas.md:35`), "simples e direto"
  (`personas.md:56`), "CCO, garagem, linha, turno" (`personas.md:78`). Um texto único para as três vira o genérico que
  o Matheus rejeitou.
- Em frota, o link é o canal. Ele circula por WhatsApp e LinkedIn, e a prévia mostra o título da página, não o da âncora.
- A mensagem do WhatsApp já sai qualificada, com o segmento no texto.
- Medir por segmento vira contar visitas por página.

**Por que não um site por segmento:** o produto é o mesmo (cabine, alarme, painel, privacidade). Três sites
triplicariam tradução PT/EN e manutenção. As seções comuns viram componentes reutilizados; a página de segmento troca o
que está na tabela abaixo.

| O que muda | Carga e logística | Fretamento e rodoviário | Ônibus urbano |
|---|---|---|---|
| Para quem | P1, P4 | P2 | P3 |
| Cena | Cavalo mecânico e carreta à noite; VUC e van para frota mista | Ônibus rodoviário em viagem noturna; garagem | Ônibus no corredor; CCO; garagem |
| Palavras | Gestão de fadiga, sinistralidade, programa de segurança | Direto: segurança dos passageiros, sem complicação | CCO, garagem, linha, turno, operador, índice de ocorrências |
| Estrada e mapa | Viagem São Paulo → Curitiba pela BR-116 | Viagem noturna de ônibus de até 900 km com revezamento | Linha entre garagem e terminal, com dupla pegada |
| Objeções, em ordem | Alarme falso; custo por veículo; instalação; LGPD e agregados; suporte na estrada; rastreador | "Motorista experiente não precisa"; custo; complicação; tirar o ônibus de rodar; suporte fora da capital | Sindicato; custo em escala; manutenção; conexão; para-e-anda; CCO afogado de alertas |
| Piloto (a confirmar) | 5 a 10 veículos com relatório (`personas.md:32`) | Alguns ônibus e demonstração na garagem (`personas.md:54`) | Uma garagem (`personas.md:77`) |
| Argumento extra | Relatório para seguradora e embarcador | Frase para o contrato com o cliente corporativo | Triagem e revisão registrada |
| Mensagem pronta | "[C1] ... frota de __ caminhões" | "[F1] ... frota de __ ônibus" | "[U1] ... __ ônibus em __ garagens" |

**O que a pesquisa mostra (princípio, não layout):**
- A Samsara tem "Industries" no menu e uma página de transporte de passageiros, com subpágina para transporte escolar.
- A Creare junta todos os segmentos numa página só e usa WhatsApp.
- A Seeing Machines e a Ituran não separam segmentos.
- **Nenhum dos quatro publica como é o piloto, a instalação, o modelo de cobrança ou a privacidade do motorista.** É
  esse o espaço do DriveSafe (entrega J).

### D. Mapa do site proposto

```
/                                Início: diz o que é e distribui por segmento
├── /carga-e-logistica           P1, P4 · transportadoras e operadores logísticos
├── /fretamento-e-rodoviario     P2 · fretamento, turismo e rodoviário
├── /onibus-urbano               P3 · concessionárias urbanas e metropolitanas
├── /como-funciona               todos · a viagem noturna completa, cabine, painel, sem sinal
├── /motoristas                  P5 (e quem repassa) · linguagem simples, fácil de compartilhar
├── /piloto                      P1, P3, P4, P2 · piloto, cobrança, instalação e suporte
├── /perguntas-frequentes        todos · objeções
├── /privacidade                 P4, P3, P5 · LGPD do produto e política do site
├── /ficha-tecnica               P1, P3 · aparelho, limites, fontes (mapa-múndi), PDF
├── /quem-somos                  P4, P2 · equipe, empresa, estágio do produto
└── /entrar                      clientes · destino de "Já é cliente? Entrar"
/en/...                          espelho em inglês (slugs traduzidos, hreflang)
```

**Fases:**
- **Lançamento:** `/`, as 3 páginas de segmento, `/motoristas`, `/piloto` (com cobrança e as 6 perguntas principais),
  `/privacidade` e `/entrar`. "Como funciona", ficha técnica e quem somos entram como seções da home.
- **Depois das respostas do Matheus e do hardware:** `/como-funciona`, `/ficha-tecnica` com PDF,
  `/perguntas-frequentes` completa e `/quem-somos`.

**Navegação:**
- **Cabeçalho no computador:** marca · Segmentos (os 3) · Como funciona · Motoristas · Piloto · Perguntas · PT | EN ·
  Já é cliente? Entrar · [Falar no WhatsApp].
- **Celular:**
  - no cabeçalho, marca, [WhatsApp] e [Menu];
  - no menu, os mesmos links, "Ligar", PT | EN e "Já é cliente? Entrar";
  - barra fixa embaixo com "WhatsApp" e "Ligar" (padrão do próprio Matheus, `site-dra-jania.md:27`).
- **Rodapé:** contato em texto, Ligar, Já é cliente? Entrar, páginas, privacidade, LinkedIn, CNPJ, cidade, PT | EN.

### E. Estrada e mapa: onde vendem e onde só decoram
Pedido do Matheus nesta rodada: "algo referente a estradas, mapa-múndi etc.". Regra usada: **só entra estrada ou mapa
que responda a uma pergunta de persona ou demonstre uma regra do produto.**

| # | Onde entra | O que mostra | Por que vende (não decora) | Persona | Cuidado de veracidade | Depende de |
|---|---|---|---|---|---|---|
| 1 | Home S1: portas de segmento | Três vias: rodovia com carreta à noite, ônibus rodoviário em serra, corredor urbano com ônibus | A pessoa se reconhece em 5 s e escolhe o próprio caminho; resolve a ausência de ônibus (problema 2) | P1, P2, P3 | Dizer "feito para", sem pinos de clientes (`contexto.md:37`) | Imagens da frente 3 |
| 2 | Home S2 e páginas de segmento: viagem noturna como fio | São Paulo → Curitiba pela BR-116, desenhada com a malha real do DNIT (`referencias.md:34`), com paradas por horário: calibração, madrugada, microssono, trecho sem sinal, sinal de volta, 5 h 30 ao volante, parada, revisão | Demonstra cabine → alarme → gestor no cenário de risco que P1 conhece; cada parada responde a uma objeção | P1, P4, P5; variante de ônibus (P2) e de turno urbano (P3) | Eventos marcados pela hora, não pela posição: o produto não guarda localização (não há GPS em `vision/` nem em `backend/`). Rótulo "Viagem de demonstração. O DriveSafe não registra localização." A v2 já mostra essa rota no painel (320) como se fosse dado | Rota confirmada pelo Matheus |
| 3 | Dentro da viagem (ou na ficha técnica): trecho sem sinal | Faixa sem cobertura na serra; evento esperando no aparelho; painel com "sem contato · eventos na fila"; envio com a hora certa | Responde à objeção de conexão (`personas.md:75`) e desfaz a contradição entre 273 e 373 | P1, P3, P2 | Esquema, não mapa de cobertura de operadora. Comportamento em `vision/sync.py:58, 82`, `backend/serializers.py:54-56` e `backend/routes/device_api.py:61-69` | Capacidade da fila (Matheus) |
| 4 | Página de ônibus urbano | Uma linha entre garagem e terminal, com dupla pegada e parada no ponto final | Explica o para-e-anda: com o ônibus parado, celular não vira alerta quando o aparelho recebe a velocidade do veículo (`vision/engine.py:109-110`) | P3 | Sem a velocidade do veículo, essa regra não vale. Relatórios por garagem, linha e turno não existem no backend | Integração de velocidade (Matheus) |
| 5 | S7 e `/piloto`: onde instalamos e atendemos | Mapa do Brasil com as regiões atendidas | Responde a "suporte na estrada" e "suporte fora da capital" (`personas.md:31, 53`) | P1, P2 | Só com a área real | **Matheus** |
| 6 | S10 e `/ficha-tecnica`: mapa-múndi das fontes | Onde nasceu cada regra usada nos limiares: Euro NCAP 2026 (Europa), NHTSA (Estados Unidos), CTB art. 67-C e 252 (Brasil) e os estudos citados em `README.md:110-138` | Prova sem número inventado; diferença frente a quem promete "até 40%" ou "94%"; motivo real para o mapa-múndi na versão em inglês | P1, P3, P4, visitante em inglês | É mapa de referências, não de presença. País de cada estudo conferido na fonte. Mapa base do Natural Earth, domínio público (`referencias.md:36`) | Só a conferência |
| 7 | `/carga-e-logistica` (opcional) | Acidentes com causa "condutor dormindo" por BR, com dado da PRF e o ano | Fala a língua de P1 e P4 (sinistralidade), com fonte pública | P1, P4 | Calcular antes de publicar e citar causa e ano (`referencias.md:35, 39-41`) | Cálculo da base da PRF |

**Onde não usar (decoração):**
- tracejado de estrada animado, marcos de km e estrada em loop, já rejeitados pelo Matheus no app (`PENDENCIAS.md:8`);
- globo girando;
- mapa de calor de eventos por trecho, porque não há GPS;
- pinos de clientes, porque não há clientes;
- o número mundial de mortes no trânsito (1,19 milhão, `referencias.md:37`) como abertura, porque não fala de fadiga nem
  de frota e é o tipo de número grande que P4 descarta.

**Celular e movimento reduzido:**
- No celular, a rota vira linha do tempo vertical, com o mapa pequeno no topo da seção. Nada de prender a rolagem: o
  pedido de piloto não pode ficar atrás de uma animação presa.
- Com `prefers-reduced-motion`, o mapa fica parado, com as paradas numeradas.

### F. Roteiro seção a seção da página principal
**Ordem pensada pelas perguntas das personas:**
1. o que é e para quem (S1);
2. como funciona no mundo real (S2);
3. o que detecta (S3);
4. o que a empresa recebe (S4);
5. as objeções mais fortes: motoristas (S5) e LGPD (S6); a conexão fica resolvida dentro de S2;
6. o próximo passo (S7);
7. as outras objeções (S8);
8. quem está por trás (S9);
9. de onde vêm as regras (S10);
10. a chamada final (S11).

S8 a S10 aparecem na home em versão curta, com link para a página completa.

#### S0 · Cabeçalho fixo
- **Objetivo:** orientar e manter a chamada à vista em qualquer ponto da rolagem.
- **Persona:** todas.
- **Conteúdo:** marca; Segmentos (Carga e logística, Fretamento e rodoviário, Ônibus urbano); Como funciona;
  Motoristas; Piloto; Perguntas; PT | EN; "Já é cliente? Entrar". No celular: marca, WhatsApp e Menu.
- **Prova:** nenhuma.
- **Chamada:** "Falar no WhatsApp" (evento `whatsapp_clique`, seção = cabeçalho).

#### S1 · Abertura: o que é e para quem
- **Objetivo:** em 5 s, dizer o que é e para quem, e fazer a pessoa escolher o próprio caminho.
  - O que é: câmera na cabine que avisa o motorista quando o sono ou o celular aparecem e manda só o evento para a
    empresa, sem gravar imagem.
  - Para quem: frotas de carga e de passageiros.
- **Persona:** P1, P2, P3. P4 e P5 costumam chegar por link.
- **Conteúdo:**
  - título que nomeia o produto e os dois segmentos;
  - subtítulo com "sem gravar imagem";
  - três portas de segmento, cada uma com a sua via;
  - uma linha de estágio: "Protótipo testado, com piloto aberto para as primeiras frotas · feito por [equipe] em [cidade]".
- **Prova:** a linha de estágio, verdadeira, e o nome da equipe.
- **Chamada:** primária "Falar no WhatsApp"; secundária "Ver uma viagem com o DriveSafe" (âncora para S2). Cada porta
  leva à página do segmento (evento `segmento_escolha`).
- **Estrada e mapa:** sim, como seletor de segmento (entrega E, item 1).

#### S2 · Uma viagem noturna (o fio da página)
- **Objetivo:** demonstrar cabine → alarme → gestor no cenário de risco que o comprador conhece e responder "e sem
  sinal?" sem uma seção só para isso.
- **Persona:** P1 (madrugada, rodovia), P4 (o que vira relatório), P5 (revisão antes da conversa). Nas páginas de
  segmento, a mesma viagem com ônibus rodoviário (P2) e um turno de linha urbana (P3).
- **Conteúdo:** mapa São Paulo → Curitiba pela BR-116, com a malha do DNIT, e paradas por horário.
  1. **22:40, saída da base.** Os primeiros 5 a 10 minutos calibram o jeito de piscar do motorista, e o nível crítico
     já vale durante a calibração (`README.md:57, 126`).
  2. **00:00, começa a madrugada.** Sinais leves passam a pesar mais das 00:00 às 06:59 (`vision/context.py:22`;
     `README.md:120-121`).
  3. **02:14, olhos fechados por 1,2 s.** Alarme na cabine e "Pare em local seguro" (reaproveitar 276–289).
  4. **02:31, trecho sem sinal na serra.** O evento fica no aparelho, e o painel mostra o veículo "sem contato" com
     eventos na fila (`backend/serializers.py:54-56`; `backend/config.py:16`).
  5. **03:05, o sinal volta.** Os eventos sobem com a hora em que aconteceram (`vision/sync.py:58`;
     `backend/routes/device_api.py:61-69`).
  6. **04:10, 5 h 30 min ao volante.** Aviso de jornada, com base no CTB art. 67-C (`vision/context.py:19`). Uma
     parada de 30 min zera a contagem (`README.md:123`).
  7. **07:00, o gestor revisa.** Confirmado, alarme falso ou motorista orientado, e exporta a planilha
     (`backend/routes/alerts.py:23-24, 92-124`).
- **Prova:** cada parada traz a regra e a fonte. Rótulo fixo: "Viagem de demonstração. O DriveSafe não registra
  localização."
- **Chamada:** na chegada a Curitiba, "Quero testar numa viagem assim" (WhatsApp com a mensagem de piloto do segmento).
- **Estrada e mapa:** sim, é o fio (entrega E, itens 2 e 3).

#### S3 · Na cabine: sono e celular
- **Objetivo:** mostrar o que é detectado e que o alarme é para o motorista.
- **Persona:** P1, P3, P5.
- **Conteúdo:**
  - a escada 1 s / 3 s / 6 s (270–274);
  - sonolência: piscadas mais longas que a própria calibração, tempo de olho quase fechado, bocejos e cabeceio;
  - celular na mão, no ouvido ou olhando por mais de 2 s; no suporte não conta; com velocidade do veículo, parado não
    conta (`vision/engine.py:109-110`);
  - óculos escuros e mão no olho desligam a medida do olho em vez de virar sono (`PENDENCIAS.md:65`; `README.md:403`);
  - o que não é: diagnóstico nem exame de drogas (`contexto.md:33`).
- **Prova:** fontes dos limiares com link (Euro NCAP 2026 e NHTSA: `README.md:110, 136`) e "limiares iniciais, em
  validação com gravações reais" (384).
- **Chamada:** link "Ver a ficha técnica e as fontes".
- **Estrada e mapa:** não.

#### S4 · O que a empresa recebe
- **Objetivo:** mostrar triagem, revisão com decisão registrada e relatório.
- **Persona:** P1, P3, P4.
- **Conteúdo:**
  - frota ordenada por conexão e por risco (`backend/routes/fleet.py:98`);
  - veículo "sem contato" com eventos na fila;
  - fila de revisão com as três decisões (`backend/routes/alerts.py:23-24`);
  - planilha com as colunas reais: data e hora, tipo, nível, duração, motorista, veículo, revisão, quem revisou e nota
    (`backend/routes/alerts.py:97-101`);
  - acessos criados pela equipe, sem cadastro aberto (`backend/config.py:24`);
  - cada empresa só vê os próprios dados (`backend/database.py:70`);
  - sem janela de programa de computador enquanto o formato do painel não for decidido (`PENDENCIAS.md:7`).
- **Prova:** legenda "tela de exemplo" e a lista das colunas como estão no produto.
- **Chamada:** "Ver o painel com a gente pelo WhatsApp" (demonstração a distância), se o Matheus puder fazer.
- **Estrada e mapa:** não. Sem GPS no produto, não desenhar mapa de eventos.

#### S5 · Para o motorista
- **Objetivo:** dar ao comprador um argumento para motoristas e sindicato, e ao motorista uma leitura que o respeite.
- **Persona:** P5, e P1 a P4 como quem repassa.
- **Conteúdo:**
  - não grava imagem;
  - o alarme é para você parar em segurança;
  - você autoriza cada uso (monitoramento, perfil entre viagens, envio de sinais de ativação: `backend/database.py:25`)
    e pode revogar a autorização (`backend/database.py:235`);
  - você vê e baixa os seus dados (`backend/routes/people.py:149-170`; `PENDENCIAS.md:32`);
  - todo evento passa por revisão e o alarme falso fica marcado;
  - óculos escuros não viram sono.
- **Prova:** trechos do termo (versão 2026-09, `backend/database.py:27`), se o Matheus liberar.
- **Chamada:** "Enviar esta explicação para os motoristas" (compartilhar o link de `/motoristas` por WhatsApp; evento
  `motoristas_compartilhar`).
- **Estrada e mapa:** não.

#### S6 · Privacidade e LGPD
- **Objetivo:** tirar o risco jurídico da mesa.
- **Persona:** P4, P3, P1.
- **Conteúdo:**
  - reaproveitar "fica no veículo / sai para a empresa" (355–375), com lista em português no lugar do JSON;
  - consentimento com histórico e canal: app, termo assinado ou equipe (`backend/database.py:26`);
  - registro de quem fez o quê (`backend/database.py:254`);
  - sinais de ativação ficam só no aparelho por padrão e só são enviados com autorização (`backend/database.py:80-81`;
    `backend/routes/device_api.py:55-56`);
  - eventos já enviados são apagados do aparelho depois de 30 dias (`vision/event_queue.py:117`, chamado a cada contato
    com o servidor em `vision/sync.py:135`).
- **Prova:** a situação da revisão jurídica, dita como está (pendente em `00 - DriveSafe AI.md:85`).
- **Chamada:** "Ler a política completa" (`/privacidade`).
- **Estrada e mapa:** não.

#### S7 · Como funciona o piloto
- **Objetivo:** tornar o próximo passo concreto e pequeno.
- **Persona:** P1 (5 a 10 veículos com relatório), P3 (uma garagem), P2 (ver funcionando na garagem), P4 (o que mede,
  custo, prazo).
- **Conteúdo (quase tudo depende do Matheus):**
  - duração e número de veículos por segmento;
  - o que a empresa entrega: acesso dos gestores, lista de motoristas e consentimentos;
  - o que a equipe entrega: aparelhos, instalação, calibração e relatório;
  - o que se mede e como se compara o antes e o depois;
  - custo do piloto e o que acontece no fim (devolução ou contratação, exportação dos dados);
  - instalação: onde fica a câmera, tempo por veículo, se precisa parar;
  - suporte: canal, horário e regiões.
- **Prova:** exemplo de relatório de piloto, com dados de demonstração marcados.
- **Chamada:** "Pedir piloto pelo WhatsApp" e "Ligar", com mensagem pronta contendo segmento e tamanho da frota.
- **Estrada e mapa:** mapa do Brasil com as regiões atendidas, só com a área real (entrega E, item 5).

#### S8 · Perguntas frequentes (objeções)
- **Objetivo:** responder à objeção onde ela aparece, sem precisar de conversa.
- **Persona:** todas. A ordem muda por página de segmento.
- **Conteúdo:** as 6 perguntas mais pesadas (alarme falso, custo, instalação, LGPD e motoristas, sem sinal, rastreador),
  com link para `/perguntas-frequentes`.
- **Prova:** respostas baseadas no código onde houver (entrega G).
- **Chamada:** "Não achou a sua pergunta? Mande no WhatsApp."

#### S9 · Quem está por trás
- **Objetivo:** mostrar continuidade e dar confiança.
- **Persona:** P4, P2, P1.
- **Conteúdo:** nomes, papéis, cidade, CNPJ, estágio do produto e contato direto.
- **Prova:** LinkedIn de cada pessoa e o que já foi testado (`README.md:419-439`).
- **Chamada:** "Falar com [nome]".

#### S10 · De onde vêm os limiares (mapa-múndi das fontes)
- **Objetivo:** provar sem número inventado e marcar a diferença frente a quem promete percentual.
- **Persona:** P1 e P3 (lado técnico), P4 ("número sem fonte"), visitante em inglês.
- **Conteúdo:** mapa-múndi com as normas e os estudos que definem cada regra, cada um no país da instituição conferido
  na referência:
  - Euro NCAP 2026 (Europa);
  - NHTSA (Estados Unidos);
  - CTB art. 67-C e 252 (Brasil);
  - os estudos de `README.md:110-138`.

  Ao lado, a ficha técnica resumida.
- **Prova:** link de cada fonte.
- **Chamada:** "Baixar a ficha técnica (PDF)", quando houver os dados do aparelho.
- **Estrada e mapa:** sim, o mapa-múndi (entrega E, item 6).

#### S11 · Chamada final por segmento
- **Objetivo:** converter quem rolou até o fim.
- **Persona:** todas.
- **Conteúdo:** três botões de WhatsApp com a mensagem de cada segmento, "Ligar", quem responde e em quanto tempo, e
  "Já é cliente? Entrar".
- **Prova:** nome de quem atende.
- **Chamada:** os três botões e "Ligar".

#### S12 · Rodapé
- **Conteúdo:** WhatsApp e número em texto, "Ligar", "Já é cliente? Entrar", PT | EN, privacidade, LinkedIn, CNPJ e
  cidade.

### G. Conteúdo de apoio à decisão que falta
**Negrito** = só o Matheus pode fornecer.

| Tema | O que precisa responder | Persona | O que já dá para escrever (fonte) | Depende do Matheus |
|---|---|---|---|---|
| Como o piloto funciona | Duração; número de veículos por segmento; o que é entregue; o que se mede antes e depois; critério de sucesso; custo; o que acontece no fim | P1, P3, P4, P2 | Calibração individual de 5 a 10 min (`README.md:57`); relatório em planilha com 16 colunas (`backend/routes/alerts.py:97-101`); revisão com 3 decisões (`backend/routes/alerts.py:23-24`) | **Todo número e todo compromisso**: duração, veículos, custo, entregas e se há um período só registrando para medir o "antes" |
| Modelo de cobrança | Por veículo por mês, comodato ou venda; instalação cobrada; prazo mínimo; reajuste; cancelamento; devolução | P4, P2 | "Os dados saem com você": exportação da planilha e dos dados do motorista (`backend/routes/alerts.py:92`; `backend/routes/people.py:149`) | **Todo** |
| Instalação | Onde fica a câmera; fixação; alimentação; tempo por veículo; se precisa parar o veículo; quem instala; garagem ou pátio | P1, P2, P3 | O aparelho inicia sozinho ao ligar (`README.md:281`); o Pi 5 não tem saída de som P2 (`README.md:277`) | **Todo o físico**: o hardware está em aberto (`contexto.md:38`) |
| Suporte | Canal, horário, regiões, prazo de troca do aparelho, atualização | P1, P2, P3 | O painel mostra aparelho sem contato (`backend/config.py:16`); a regra dos sinais de ativação vai do servidor ao aparelho (`backend/routes/device_api.py:51-58`) | **Todo o operacional** e a área atendida |
| Perguntas frequentes | Lista abaixo | Todas | 11 das 18 com base no código | 7 das 18 |
| Privacidade e motoristas (LGPD) | O que é processado e onde; o que sai; retenção no aparelho e no servidor; base legal; consentimentos e revogação; direitos do titular; registro de acessos; sinais de ativação; controlador e operador; encarregado; agregados | P4, P3, P5, P1 | `backend/database.py:25-27, 80-81, 235, 254`; `backend/routes/people.py:149-170`; `backend/routes/device_api.py:55-56`; `vision/event_queue.py:117` | **Retenção no servidor, papéis de controlador e operador, encarregado, base legal, texto do termo e revisão jurídica** (`00 - DriveSafe AI.md:85`) |
| Ficha técnica | Câmera (modelo, infravermelho, fps); processador; alimentação de 12 ou 24 V; medidas; temperatura; conexão (4G, Wi-Fi); capacidade da fila; volume do alarme; certificações; sistemas testados | P1, P3 | Limite de fps (`README.md:127`); testado só no Windows (`README.md:421-423, 440-443`) | **O aparelho final**, e se a ficha diz "testado" ou "compatível" |
| Quem está por trás | Nomes, papéis, cidade, CNPJ, estágio, parceiros | P4, P2, P1 | Estágio: protótipo com testes automáticos (`PENDENCIAS.md:19`) | **Todo**. O vault registra o repositório `github.com/edduardoSW/Vigilancia_Motorista` com o Matheus como contribuidor (`00 - DriveSafe AI.md:17`): quem aparece como dono? |
| Convivência com o que já existe | Rastreador, câmeras e GPS: o que integra, como e quem faz | P1, P3 | Lê a velocidade de um arquivo escrito por outro programa (GPS, OBD-II, CAN) (`vision/context.py:32-33`) | **Quais rastreadores, quem escreve a integração, se usa câmera já instalada** |
| Relatório para seguradora e cliente corporativo | Formato, período e indicadores | P4, P2 | Planilha (`backend/routes/alerts.py:97-101`) | **Se existe modelo e se alguma corretora já viu** |

**Perguntas frequentes com as objeções:**

| # | Pergunta | Persona | Base da resposta | Situação |
|---|---|---|---|---|
| 1 | Grava vídeo ou som do motorista? | P5, P1, P3 | Nenhuma gravação de vídeo nem captura de áudio em `vision/` e `run_monitor.py` (busca por VideoWriter, imwrite, microfone, pyaudio e sounddevice sem ocorrências). A exportação diz "não grava nem envia imagens" (`backend/routes/people.py:162`) | Código. Confirmar a frase com a frente 5 e explicar à parte o modo de teste da equipe, que recebe vídeo e o apaga depois da análise (`backend/config.py:34-35`) |
| 2 | Óculos escuros ou sol no rosto viram sono? | P1, P5 | Óculos escuros ou olhos fora da imagem por 10 s geram aviso leve e a medida do olho é desligada (`README.md:403`) | Código para óculos; sol ainda não validado (`README.md:446-447`) |
| 3 | Funciona à noite? | P1, P2 | Câmera infravermelha recomendada (`README.md:271`), ainda não testada (`README.md:442`) | Código, com pendência |
| 4 | O motorista é punido por alarme falso? | P5, P3 | A revisão marca "alarme falso" e registra quem revisou (`backend/routes/alerts.py:23-24, 72-77`) | Código, mais **a recomendação que o Matheus quer fazer às empresas** |
| 5 | E sem internet? | P1, P3 | Fila no aparelho, envio a cada 5 s com conexão, hora original preservada (`vision/sync.py:58, 82`; `backend/routes/device_api.py:61-69`) | Código; **capacidade da fila** |
| 6 | Convive com o meu rastreador? | P1, P3 | Velocidade vinda de outro programa (`vision/context.py:32-33`) | Parcial; **Matheus** |
| 7 | Quanto custa e como é cobrado? | P4, P2 | Nenhuma | **Matheus** |
| 8 | Precisa parar o veículo para instalar? | P1, P2, P3 | Nenhuma | **Matheus** |
| 9 | Onde fica a câmera? Atrapalha a visão? | P5, P1 | Nenhuma | **Matheus** |
| 10 | Precisa de consentimento? E os agregados? | P4, P1 | Consentimento com histórico e canal (`backend/database.py:25-27`) | Código, mais **jurídico** |
| 11 | O motorista vê os próprios dados? | P5 | Painel do motorista e exportação (`PENDENCIAS.md:32`; `backend/routes/people.py:149-170`; `backend/routes/alerts.py:43-44`) | Código (formato do painel em aberto) |
| 12 | Detecta droga ou álcool? | P5, P4 | Não é diagnóstico nem exame (`contexto.md:33`); sinais de ativação ficam no aparelho por padrão (`backend/database.py:80-81`) | Código; **o Matheus decide se o site cita esse módulo** |
| 13 | Serve para ônibus urbano no para-e-anda? | P3 | Com a velocidade do veículo, celular com o ônibus parado não gera alerta (`vision/engine.py:109-110`) | Código parcial; limiares urbanos não validados |
| 14 | Aguenta 600 veículos? | P3 | Várias empresas e PostgreSQL (`PENDENCIAS.md:29-30`) | Escala não medida; **Matheus** |
| 15 | Quem dá suporte na estrada ou fora da capital? | P1, P2 | Nenhuma | **Matheus** |
| 16 | Se a DriveSafe parar, fico com os dados? | P4 | Exportação da planilha e dos dados do motorista (`backend/routes/alerts.py:92`; `backend/routes/people.py:149`) | Código, mais **contrato** |
| 17 | Quanto reduz de acidentes? | P4, P1 | Ainda não há piloto medido e nada se publica sem fonte (`contexto.md:37, 46`) | Resposta honesta pronta |
| 18 | Qual a diferença para a videotelemetria? | P1, P4 | Não grava nem envia vídeo; o processamento é no aparelho (`contexto.md:34`) | Código; **como tratar a falta de vídeo para defesa em sinistro** |

### H. Como medir a conversão sem rastreamento invasivo
**Princípios:**
- Medir cliques em chamadas e visitas por página, nunca a pessoa.
- Sem cookie de rastreamento, gravação de sessão, pixel de anúncio ou formulário.
- Quem se identifica é o próprio contato, ao mandar a mensagem.
- Descrever na política de privacidade do site o que é medido.

**Eventos (no máximo 2 propriedades, para caber no plano Pro da Vercel):**

| Evento | Quando | Propriedades | Pergunta que responde |
|---|---|---|---|
| `whatsapp_clique` | Clique em qualquer link `wa.me` | seção, segmento | Que seção e que segmento geram conversa |
| `ligar_clique` | Clique em `tel:` | seção, segmento | Quem prefere ligar (hipótese: P2) |
| `piloto_clique` | Clique em "Pedir piloto" | seção, segmento | Intenção de piloto contra dúvida geral |
| `segmento_escolha` | Clique numa porta de segmento da home | segmento | Mistura real de público |
| `entrar_clique` | Clique em "Já é cliente? Entrar" | origem (cabeçalho, menu, rodapé) | Quanto o site é usado como porta de cliente |
| `motoristas_compartilhar` | Compartilhar a página dos motoristas | canal | Compradores levando o argumento aos motoristas |
| `faq_abrir` | Abrir uma pergunta | id da pergunta | Quais objeções pesam |
| `ficha_baixar` | Baixar a ficha técnica | segmento | Interesse técnico e de comitê |
| `idioma_trocar` | Trocar PT/EN | idioma de destino | Demanda real pela versão em inglês |

**UTM nos links que o Matheus espalha:**
- `utm_source`: linkedin, whatsapp, fenatran, seguradora, email.
- `utm_medium`: post, grupo, qr, parceiro.
- `utm_campaign`: por exemplo, `piloto-carga-2026-10`.
- QR code em material impresso (feira, garagem) com `utm_medium=qr`.
- Uma planilha com cada link gerado.

**Código na mensagem do WhatsApp (liga o clique à conversa sem guardar dado pessoal):**
- Formato do link: `https://wa.me/55DDNNNNNNNNN?text=<texto codificado>`
  ([WhatsApp · click to chat](https://faq.whatsapp.com/5913398998672934/)).
- Exemplo de texto: "Olá! Vim pelo site do DriveSafe [C1-LI]. Quero entender o piloto para a minha frota de __
  veículos."
- Letra do segmento: C (carga), F (fretamento), U (urbano), M (página dos motoristas), S (cliente pedindo suporte).
- Origem em 2 letras, tirada do `utm_source` da própria URL no momento do clique: LI (LinkedIn), WA (WhatsApp), FE
  (Fenatran), SG (seguradora), DI (direto). Nada fica guardado no navegador.
- No WhatsApp Business, uma etiqueta por segmento.

**Funil semanal (planilha simples):**

| Etapa | Onde contar |
|---|---|
| Visitas por página de segmento | Analytics |
| Cliques em WhatsApp e Ligar, por seção | Eventos |
| Conversas recebidas, por código | WhatsApp Business (etiquetas) |
| Demonstrações marcadas | Planilha |
| Pilotos | Planilha |
| Contratos | Planilha |

**Como ler o funil:**
- Clique ÷ visita, por segmento: a página convence?
- Conversa ÷ clique: se cair, o link ou a mensagem têm problema.
- Piloto ÷ conversa: a oferta é boa?

**Ferramenta (decisão do Matheus):**

| Opção | O que cobre | Limite | Custo |
|---|---|---|---|
| Vercel Web Analytics, padrão do vault (`stack-padrao.md:68`) | Visitas sem cookie de terceiros; eventos no plano Pro | No Hobby, sem eventos e sem UTM; no Pro, eventos com 2 propriedades; UTM só com Web Analytics Plus | Hobby grátis; Plus custa US$ 10/mês por equipe, além do Pro ([limites](https://vercel.com/docs/analytics/limits-and-pricing), [eventos](https://vercel.com/docs/analytics/custom-events), [privacidade](https://vercel.com/docs/analytics/privacy-policy)) |
| Umami instalado na VPS prevista (`PENDENCIAS.md:30`) | Visitas, eventos por atributo `data-umami-event`, campanhas, sem cookies | Manter o servidor | Só a VPS ([eventos](https://docs.umami.is/docs/track-events), [repositório](https://github.com/umami-software/umami)) |
| Sem ferramenta | Só os códigos do WhatsApp e a planilha | Não mede visitas nem cliques | Zero |

**Sugestão:**
- Se a VPS sair, Umami nela.
- Senão, Vercel Pro com eventos de 2 propriedades (seção e segmento). A origem vem do código da mensagem, o que dispensa
  o Plus.

**Não usar:**
- pixel da Meta;
- remarketing do Google Ads;
- gravação de sessão e mapa de calor (Hotjar, Clarity);
- impressão digital do navegador;
- o lead-gate dos outros sites do Matheus (conflito I.1).

### I. Conflitos com o vault e com decisões anteriores
1. **Lead-gate × "sem cadastro nem formulário".**
   - `meu-estilo-de-sites.md:102` e `site-dra-jania.md:31, 160` pedem nome e telefone antes de abrir o WhatsApp.
   - `contexto.md:44` proíbe formulário.
   - Para o DriveSafe: sem lead-gate; o código na mensagem faz a atribuição. Registrar como exceção na nota do projeto.
2. **Estrada decorativa × estrada pedida.**
   - No app, o Matheus rejeitou "tracejado de estrada, marcos de km, animação de estrada" (`PENDENCIAS.md:8`). Agora pede
     estradas e mapa-múndi no site.
   - Levar a proibição do app para o site repetiria o erro de aplicar o feedback de uma peça em outra
     (`contexto.md:19`). Trazer de volta os efeitos também seria erro.
   - Proposta: no site, estrada e mapa só com informação (rota, horário, sinal, fontes). Confirmar com ele.
3. **"Diário de bordo" e públicos.**
   - `PENDENCIAS.md:215-216` registra a direção "dia de 24 h num disco de tacógrafo" e públicos que incluem investidores
     e universidades.
   - `contexto.md:42-43` tirou esses públicos do foco, e a v2 ainda cita universidades (404).
   - A viagem noturna (S2) junta o tempo do "Diário de bordo" com o espaço da estrada. Confirmar se a direção ainda vale.
4. **Formato do painel.** A v2 desenha janela de programa de computador (301) e deixa "Entrar" sem destino (219), com o
   formato em aberto (`PENDENCIAS.md:7`).
5. **Rota e localização.**
   - O painel de exemplo mostra "São Paulo → Curitiba · BR-116" (320).
   - O produto não guarda localização: não há GPS em `vision/` nem em `backend/`, só a velocidade opcional
     (`vision/context.py:32-33`).
   - Qualquer mapa de eventos por local seria promessa.
6. **Relatórios por garagem, linha e turno.** P3 pede (`personas.md:70`), mas o backend não tem campo de garagem, linha
   ou turno.
7. **Vault.** `contexto.md:19` cita o "erro 75", mas o `erros-que-a-ia-comete.md` local termina no 74 (linha 563).
   Conferir se o vault está sincronizado antes de consolidar.

### J. Referências pesquisadas
| Fonte | O que faz com segmento, prova e chamada | Princípio para o DriveSafe |
|---|---|---|
| [Samsara · Passenger Transit](https://www.samsara.com/industries/passenger-transit) | Página própria no menu "Industries", subpágina de transporte escolar, prova por estudo de caso com número de cliente, chamadas "Check our prices" e "Talk to sales" | Página por segmento, com vocabulário e prova do segmento. Não copiar a métrica de cliente, que o DriveSafe não tem |
| [Creare Sistemas · Sensor de Fadiga](https://crearesistemas.com.br/sensor-de-fadiga/) | Uma página para todos os segmentos (transporte, mineração, energia...), "Fale Conosco" (formulário) e "Chamar no WhatsApp", "até 40%" e logos; sem perguntas frequentes, preço ou piloto | WhatsApp é canal normal do setor no Brasil. Evitar segmentos misturados e percentual |
| [Seeing Machines · Guardian (frota)](https://seeingmachines.com/fleet/) | "How it works" em 5 passos (detecta, alerta na cabine, central analisa, gestor age, orientação), "Request information", "mais de 94%"; sem páginas por segmento | Fechar a sequência com o passo de orientação (o DriveSafe tem "motorista orientado", `backend/routes/alerts.py:24`) |
| [Ituran · Sensor de fadiga](https://ituran.com.br/sensor-de-fadiga/) | Texto de blog, cotação por formulário e WhatsApp; sem instalação, preço, contrato ou LGPD | Confirma o vazio que o DriveSafe pode ocupar |

- **Medição:** [Vercel · eventos](https://vercel.com/docs/analytics/custom-events) ·
  [Vercel · limites e preço](https://vercel.com/docs/analytics/limits-and-pricing) ·
  [Vercel · privacidade](https://vercel.com/docs/analytics/privacy-policy) ·
  [Umami · eventos](https://docs.umami.is/docs/track-events) ·
  [Umami · repositório](https://github.com/umami-software/umami) ·
  [WhatsApp · click to chat](https://faq.whatsapp.com/5913398998672934/).
- **Toque:** [WCAG 2.2 · 2.5.8 Target Size (Minimum)](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html) ·
  [Apple HIG · Accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility).
- **Estrada e mapa (rodada do coordenador):** DNIT, PRF e Natural Earth em `referencias.md:34-36`.

## Perguntas que só o Matheus responde
**Contato e acesso**
1. Qual número atende no WhatsApp e na ligação? Quem responde e em quanto tempo?
2. Para onde vai "Já é cliente? Entrar" enquanto o formato do painel (programa, app de celular, web) não é decidido? E o
   motorista entra onde?

**Segmentos e oferta**
3. Os três segmentos (carga e logística; fretamento e rodoviário; ônibus urbano) entram no lançamento, ou começa por um?
4. Piloto: duração, número de veículos por segmento, custo, o que vocês entregam, como medem o antes e o depois e o que
   acontece no fim?
5. Cobrança: por veículo por mês, comodato ou venda? Prazo mínimo? Instalação cobrada?
6. Dá para mostrar o produto funcionando na garagem do cliente (P2)? Em que regiões?

**Produto e hardware**
7. Onde a câmera fica, quanto tempo leva a instalação, se precisa parar o veículo, qual a alimentação e as medidas?
8. Suporte: canal, horário, regiões e troca de aparelho?
9. Integra com rastreador? Quem escreve a integração da velocidade?
10. Como funciona a troca de motorista no revezamento (um aparelho, dois motoristas)?
11. Relatório por garagem, linha e turno está nos planos? Pode aparecer como "sob consulta"?
12. O site pode citar os "sinais compatíveis com ativação atípica", ou esse módulo fica fora da divulgação?

**Prova e empresa**
13. Quem aparece em "Quem está por trás": nomes, papéis, cidade, CNPJ? O repositório pode ser citado?
14. Alguma frota testa o produto hoje? Se não, "em piloto com transportadoras" sai.
15. A revisão jurídica de LGPD já foi feita? Quem é o encarregado de dados?

**Estrada, mapa e medição**
16. Confirma que, no site, estrada e mapa entram só com informação (rota, horário, sinal, fontes) e sem os efeitos
    rejeitados no app (`PENDENCIAS.md:8`)?
17. O mapa-múndi pode ser o das fontes dos limiares, e não de presença? A versão em inglês mira algum país?
18. A viagem de exemplo pode ser São Paulo → Curitiba pela BR-116, já usada na v2? Existe rota mais real de um primeiro
    cliente?
19. Medição: Umami na VPS ou Vercel Pro (com ou sem Web Analytics Plus)? Aceita os códigos na mensagem do WhatsApp?
20. A direção "Diário de bordo" (`PENDENCIAS.md:215`) ainda vale para juntar com a viagem noturna?
