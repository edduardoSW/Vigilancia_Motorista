# Frente 5 · Técnica, acessibilidade, SEO, idiomas e veracidade
Avaliador: agente 5 · 11/09/2026 · versão avaliada: `site-drivesafe/previa/v2/index.html` (prints `previa-topo.png`, `previa-desktop.png`, `previa-celular.png`)

> Escopo: a prévia é HTML estático. A versão final será **Next.js 16 + Tailwind CSS 4 + next-intl (PT e EN)**, então a
> parte técnica avalia a prévia pensando nessa migração. Cada afirmação do site foi conferida no código do repositório
> em 11/09/2026 (`vision/`, `backend/`, `run_monitor.py`, `README.md`, `PENDENCIAS.md`). As versões foram conferidas no
> registro npm no mesmo dia. Linhas citadas como `:NNN` são de `site-drivesafe/previa/v2/index.html`.

## Nota geral: 3/10
Das **60 afirmações de fato** da página, **12 são falsas, 13 exageradas e 7 não verificáveis**. As falsas estão nos
lugares mais vistos: o selo "em piloto", o título, a promessa de privacidade e as telas. Na parte técnica, a prévia
reprova em contraste, menu no celular, SEO e idiomas. A base técnica do produto é verdadeira (escada de 1 s, 3 s e 6 s,
fila sem internet), o que torna a correção rápida. A tabela completa está no Anexo B.

## Notas por critério
| Critério | Nota | Por quê | Evidência |
|---|---|---|---|
| Veracidade | 2 | 25 de 60 afirmações falsas ou exageradas, e mais 7 sem prova. As falsas estão no selo, no h1, na privacidade e nas telas | Anexo B; Anexo C |
| Acessibilidade | 4 | Todo texto auxiliar reprova no AA (3,08 a 3,87:1) com 10,6 a 12,8 px. O texto branco do alarme fica em 3,06:1. No celular não há menu nem "Entrar". A animação é infinita e não tem pausa. Há `aria-label` em `div` sem papel | `:44-49, 76-79, 83, 88, 165, 243, 300, 516-532` |
| Desempenho | 6 | Página leve (37 KB) e sem imagens. Mas o CSS de fonte vem de terceiro e bloqueia, e o `requestAnimationFrame` faz cerca de 50 escritas no DOM por quadro, até fora da tela. Não há plano para fotos e vídeo | `:8-10, 447-456, 495-532` |
| SEO | 2 | O título ainda é de prévia. Faltam description, Open Graph, canonical, hreflang, dados estruturados e favicon. O h1 não tem as palavras que o comprador busca, e o nome "DriveSafe" já é usado na mesma categoria | `:6, 230`; Anexo D |
| Prontidão PT/EN | 2 | "PT · EN" é texto solto e não existe versão EN. Os textos da demonstração estão presos no JavaScript, com a vírgula decimal trocada à mão | `:218, 412, 418, 442, 454, 499-505` |
| Alinhamento com a stack (Next 16 + Tailwind 4 + next-intl) | 5 | Os tokens já existem e nenhum nome de classe colide com utilitário. Mas os resets e primitivos estão sem camada (quebrariam no Tailwind 4, erro 53), a fonte vem de fora em vez de `next/font` e a demonstração é imperativa. O vault ainda cita `middleware.ts` | `:12-38, 50-53`; `stack-padrao.md:83-92, 104, 112`; `erros-que-a-ia-comete.md:320-343` |

## Leitura por persona
Nesta frente, a leitura mostra onde a veracidade falha para cada pessoa.

| Persona | O que ela confere primeiro | Onde a veracidade falha para ela | Efeito provável |
|---|---|---|---|
| P1 Renata (segurança de frota) | Referência de piloto, óculos escuros, noite, alarme falso | "Em piloto com transportadoras" (`:229`) sem nenhum piloto. "Óculos escuros detectados" (`:391`), mas, de óculos escuros e com câmera comum, o sono pelos olhos deixa de ser medido (`vision/engine.py:101`, `vision/visibility.py:3-4`) | Pede o nome da transportadora e não recebe. No piloto, descobre a limitação dos óculos. O comitê descarta |
| P2 Carlos (fretamento) | Ônibus, noite, instalação simples | O texto fala só de "caminhão" (`:268, 352, 403`). O risco não usa o descanso de 4 h do transporte de passageiros, só o limite de 5 h 30 min (`vision/context.py:3-4, 19`). "Roda em Raspberry Pi" nunca foi testado (`README.md:417, 441`) | Sente que o produto não é para ele e desconfia da promessa grande |
| P3 Juliana (CCO) | Como o alerta chega e em quanto tempo | "Gestor avisado imediatamente" (`:273`): o envio acontece a cada 5 s, pode esperar até 5 min depois de uma falha e só aparece com o painel aberto, sem notificação (`vision/sync.py:59, 82`; `backend/routes/device_api.py:136-141`) | O CCO espera um alerta ativo e recebe um painel que precisa estar aberto |
| P4 Marcos (financeiro) | Risco jurídico, contrato, custo | "Conforme a LGPD" sem parecer nem RIPD (`README.md:170, 457`). O consentimento não bloqueia eventos (`backend/routes/device_api.py:51-58`). "Cinco caminhões" e "relatório do período" não são oferta definida | A compra trava no jurídico, ou ele exige uma garantia contratual que não existe |
| P5 José (motorista) | Se é filmado e o que a empresa recebe | "A imagem fica no caminhão" (`:352`) soa como imagem guardada. "Só o evento sai" é falso: o estado sai a cada 15 s (`vision/driver_monitor.py:182-207`). O modo teste transmite vídeo (`backend/routes/test_mode.py:119-124`) | O sindicato encontra uma frase falsa e usa contra a adoção |

## Problemas, do mais grave ao menos grave
| # | Gravidade | Problema | Evidência | Impacto | Correção concreta |
|---|---|---|---|---|---|
| 1 | crítica | O selo e o rodapé dizem que o produto está "em piloto", e não há piloto | `:229, 412`; `site-drivesafe/avaliacao/contexto.md:37`; `PENDENCIAS.md:41, 93, 210-212` | P1 e P4 pedem referência e não há. A confiança na página inteira cai. Há risco de publicidade enganosa (interpretação, confirmar com advogado: CDC, art. 37, com aplicação discutível em compra entre empresas) | Selo: "Protótipo em testes · vagas para o primeiro piloto". Rodapé: "DriveSafe AI · protótipo em testes" |
| 2 | crítica | A promessa de privacidade é falsa ou sem base: "Só o evento sai dele", "vai apenas o registro do evento", "com o consentimento do motorista", "conforme a LGPD" | `:352-353`. Estado a cada 15 s: `vision/driver_monitor.py:182-207`, `vision/sync.py:125-129`, `backend/routes/device_api.py:41-48, 82-98`. Consentimento não checado: `backend/routes/device_api.py:51-58, 107-144`. Sem RIPD: `README.md:168, 457` | É o argumento que convence P5 e o sindicato. Uma frase falsa aqui derruba a adoção e expõe a empresa | Texto: "A imagem é processada no aparelho e descartada. Para a empresa vão só números: eventos e o estado do aparelho. O motorista registra as autorizações e pode baixar os próprios dados." Tirar "conforme a LGPD" até existir parecer e RIPD. No produto, checar o consentimento de monitoramento antes de aceitar eventos |
| 3 | crítica | O título é falso na leitura literal, e o h2 promete um resultado sem prova | `:230, 268`. Sirene de 2 s que se repete: `vision/alarm.py:18-21, 100-107`. Nada validado com motoristas: `README.md:446`. Model card: `THIRD_PARTY_NOTICES.md:21` | O título é a frase mais lida. "Antes de sair da faixa" promete evitar acidente sem nenhum dado | H1: "Olhos fechados por 1 segundo. Alarme na cabine." H2: "O alarme toca no primeiro segundo de olhos fechados." |
| 4 | alta | As telas mostram recursos que não existem: alarme na tela da cabine, rota, direção do dia, faixa de pausas, "21 rodando", curva do olho por evento, PERCLOS ao vivo | `:276-288, 298, 304, 320, 324, 327, 330-339, 543-545`; `vision/driver_monitor.py:68-127, 189-203`; `backend/database.py:153`; `backend/queries.py:103-104`; `vision/context.py:32-33` | Na demonstração ao vivo, P1 e P3 procuram o que viram no site e não encontram | Mostrar só o que o código entrega (risco por veículo, direção contínua, dia hora a hora, evento com medidas) ou rotular cada tela como "conceito" |
| 5 | alta | Especificações exageradas: "12 pontos por olho", óculos escuros, câmera infravermelha, plataformas, celular no suporte, "em validação com gravações reais" | `:359, 384, 389, 391, 392`; `vision/face.py:35-42`; `vision/visibility.py:3-6`; `vision/engine.py:101`; `README.md:153, 417, 434, 440-447`; `vision/phone.py:64-67, 300-302`; `PENDENCIAS.md:41, 93` | O piloto revela o exagero, e o comprador passa a duvidar do resto | Textos corrigidos no Anexo B (V35, V41, V45, V48, V49, V50) |
| 6 | alta | "6 s: o gestor é avisado no painel imediatamente" | `:273`; `vision/sync.py:59, 80-83, 107-111`; `backend/routes/device_api.py:136-141`; nenhuma notificação push, SMS ou ligação em `backend/` nem em `webapp/` | P3 conta com um alerta ativo. Num motorista sem resposta de verdade, o gestor pode não ver | "O evento mais grave chega ao painel em segundos, com sinal de celular. Sem sinal, assim que ele voltar." |
| 7 | alta | O contraste AA reprova em todo texto auxiliar e no texto do alarme | `#6f6f69` em `:47, 66, 83, 88, 112, 122-123, 128, 133, 138, 146, 152, 199` (3,08 a 3,87:1); branco sobre `#ff5b4f` em `:79, 165` (3,06:1) | P1, P2 e P4 têm de 44 a 56 anos. Rótulos de 10,6 a 12,8 px ficam ilegíveis no sol e no celular | Token `--c-fg-dim: #8a8982` (5,57 / 5,26 / 4,92:1). Alarme com texto `#0b0c0e` sobre `#ff5b4f` (6,39:1) ou branco sobre `#cf3a2f` (4,88:1). Rótulo com no mínimo 12 px |
| 8 | alta | No celular não há menu nem "Entrar" | `:44-45, 48-49`; print `previa-celular.png` (o topo só tem o logo e "Pedir piloto"); requisito em `contexto.md:44` | O cliente não acha o login, e as seções só são alcançadas rolando | Botão de menu com `aria-expanded` e "Já é cliente? Entrar" visível em todas as larguras |
| 9 | média | O seletor "PT · EN" é falso, e os textos estão presos no JavaScript | `:218, 412, 418, 442, 454, 499-505`; `PENDENCIAS.md:210` | Promete uma versão que não existe e encarece a migração para next-intl | Tirar o seletor até existir EN. Na versão Next, strings em `messages/*.json` e números com o formatador do next-intl |
| 10 | média | SEO inexistente e nome disputado | `:6` (título de prévia). Sem `meta description`, Open Graph, canonical, hreflang, JSON-LD e favicon. "DriveSafe" já é usado pela Embitel e por um app de sonolência no Google Play (Anexo D) | A página não aparece na busca e compartilha mal no WhatsApp e no LinkedIn | Metadata por idioma, imagem OG de 1200×630, `alternates.languages` com `x-default`, JSON-LD `Organization`. Conferir o nome no INPI |
| 11 | média | A animação é infinita, não tem pausa e roda fora da tela. O movimento reduzido só é lido ao carregar | `:516-532`; cerca de 50 escritas no DOM por quadro (`:447-456, 495-507`) e a curva de 270 pontos refeita 30 vezes por segundo (`:509-514, 526-527`) | Descumpre o WCAG 2.2.2 (pausar, parar, ocultar) e gasta bateria no celular | Botão "Pausar", `IntersectionObserver` e `visibilitychange`, e ouvir a mudança de `prefers-reduced-motion`. No React, `ref` em vez de estado a cada quadro |
| 12 | média | As promessas de privacidade esbarram em brechas do servidor de testes | Vídeo ao vivo por MJPEG: `backend/routes/test_mode.py:119-124`, `backend/test_session.py:259-277`. Vídeo enviado fica guardado com `DRIVESAFE_MANTER_VIDEOS=1`: `backend/config.py:34-35`, `backend/test_session.py:411-412`. Vídeo órfão se o servidor reiniciar durante a análise: `backend/test_session.py:330-332`. HTTP no exemplo: `deploy/raspberry-pi/device.env.example:4` | Um auditor ou o sindicato encontra vídeo onde o site diz "0 imagens" | Limitar a frase ao aparelho do veículo. Apagar o vídeo órfão no `_load`, avisar claramente sobre a variável e exigir HTTPS |
| 13 | média | A demonstração contradiz o produto | O risco volta a "Normal" cerca de 2 s depois do alarme (`:486, 505`), mas o código segura o "Crítico" por 10 s (`vision/risk.py:14, 24, 153-161`). O status mostra "1,2 s" quando o fechamento ainda está em 1,0 s (`:486, 499`) | Quem compara com o produto vê outra lógica | Manter "Crítico" por 10 s e depois "Alto". Mostrar o tempo real no status |
| 14 | média | O alarme pode ficar mudo no Raspberry Pi | Sem player de áudio, o sistema só grava um aviso no log e manda `\a` (`vision/alarm.py:94-98, 120-122`). O Pi 5 não tem saída P2 (`README.md:277`). Som e buzzer não foram testados (`README.md:442-443`) | A promessa central ("1 s = alarme") falha em campo | Antes de publicar a promessa, testar som e buzzer no hardware do piloto |
| 15 | média | Os resets e primitivos da prévia estão sem camada e quebrariam no Tailwind 4 | `:33-36` (resets), `:50-53` (`.btn`); `erros-que-a-ia-comete.md:329-337` (erro 53); `stack-padrao.md:83-89` | O botão aparece onde deveria sumir, a cor do link sai errada e as seções colam | Não copiar `:33-36`, porque o Preflight já faz isso em `@layer base`. Primitivos em `@layer components`. Tokens e seus overrides fora de camada (erro 54) |
| 16 | baixa | Semântica e detalhes | `aria-label` em `div` sem papel (`:243, 300`); tabela sem cabeçalho (`:335-339`); rótulo SVG com 5,8 px no celular (`:442`); texto esticado por `preserveAspectRatio="none"` (`:331, 540`); links `href="#"` (`:219, 406`); sem favicon nem link para pular ao conteúdo | O leitor de tela não anuncia a demonstração, e os rótulos ficam ilegíveis | `role="img"` com descrição fixa e a parte animada em `aria-hidden`; `th scope="col"`; rótulos em HTML, fora do SVG |
| 17 | baixa | A fonte do Google é carregada de fora | `:8-10`; `stack-padrao.md:104` (a trilha A usa `next/font`) | Requisição de terceiro que bloqueia a página e envia o IP do visitante ao Google | `next/font`, que baixa a fonte no build e a serve do próprio site |
| 18 | baixa | O vault está desatualizado para o Next 16 | `stack-padrao.md:112` cita `middleware.ts`, e o Next 16 renomeou para `proxy.ts` (Anexo D). O `erros-que-a-ia-comete.md:35` já usa `proxy.ts` | Quem seguir a nota cria um arquivo depreciado | Atualizar a árvore da trilha A para `src/proxy.ts` |

## O que manter
- A demonstração é rotulada como simulação (`:246, 259`). As métricas são as mesmas da janela real do produto
  (`vision/driver_monitor.py:85-94`): abertura do olho, tempo fechado, PERCLOS de 60 s e nível de risco.
- A escada de 1 s, 3 s e 6 s é verdadeira e tem base: `vision/drowsiness.py:28-30, 71-75` e o protocolo Euro NCAP
  (Anexo D).
- "Sem internet, fica na fila e é enviado depois" é verdadeiro (`vision/event_queue.py:1`, `vision/sync.py:107-111`).
- As especificações ficam numa lista `dl`, sem superlativo, e reconhecem que os limiares são iniciais (`:384-395`). Só
  falta ajustar o tempo verbal.
- Não há número inventado de redução de acidentes nem logo de cliente.
- O site não fala de "sinais de ativação atípica" (drogas). Isso é bom para P5. Se o tema entrar, só com a ressalva de
  que não é diagnóstico (`README.md:16-17`).
- Contrastes que já passam: texto principal 16,27:1, âmbar 10,85:1, botão primário 10,22:1, texto secundário
  (`--muted`) de 6,67 a 7,55:1 e seção de especificações 5,89:1.
- Semântica de base: `lang="pt-BR"`, `header`, `nav` com rótulo, `main`, `footer`, `ol` na escada, `dl` nas
  especificações e `role="img"` na tela da cabine (`:2, 205-223, 270, 276, 386`).
- O movimento reduzido já foi pensado (`:516-520`).
- Nenhuma classe da prévia colide com utilitário do Tailwind 4 (conferido classe a classe: `shell`, `kicker`, `tag`,
  `proof`, `chip`, `pill`, `kpi`, `spec`, `card`, `flow`, `caption` e outras).

## Recomendações para a próxima versão (em ordem de prioridade)
1. **Corrigir as 25 afirmações falsas ou exageradas** com os textos do Anexo B e tirar as 7 não verificáveis até haver
   prova. Na versão Next, cada frase de fato vira uma chave em `messages`, com a fonte registrada em
   `src/content/claims.ts` (chave → `arquivo:linha` ou URL). Assim a próxima rodada confere sem reler o código.
2. **Decidir com o Matheus as brechas de produto que sustentam a privacidade**, antes de publicar essa seção:
   - checar o consentimento de monitoramento em `backend/routes/device_api.py`;
   - apagar o vídeo órfão em `backend/test_session.py:322-333`;
   - exigir HTTPS entre aparelho e servidor;
   - deixar a janela de vídeo desligada por padrão no veículo (`run_monitor.py:100-104`);
   - rever o que vai no estado ao vivo e no evento `calibracao_concluida` (`vision/drowsiness.py:521, 530`).
3. **Parecer jurídico e RIPD** sobre dado biométrico e base legal (Anexo C9). Até lá, nada de "conforme a LGPD".
4. **Telas:** definir o formato do painel (`PENDENCIAS.md:7`) e mostrar só o que existe. A tela da cabine só entra
   rotulada como "conceito".
5. **Acessibilidade:** tokens com contraste calculado pela WCAG (erro 50 do vault), rótulo com no mínimo 12 px, menu no
   celular, pausa na demonstração e `aria` corrigido (Anexo A).
6. **Migração** (Anexo A7 e A8): Next 16.3.4, React 19.3.0, Tailwind 4.3.3 e next-intl 4.14.4, com TypeScript 6.0.3 e
   ESLint 9.39.5 travados e justificados. Usar `src/proxy.ts` e `next/font`. A prova é `npm run build` **e**
   `npm run lint`.
7. **SEO:** metadata por idioma, Open Graph, canonical, `alternates.languages` com `x-default`, `sitemap.ts` com
   alternates e JSON-LD `Organization`. `Product` só quando houver oferta real: o Google exige `offers`, `review` ou
   `aggregateRating`, e avaliação não se inventa.
8. **Mídia:** fazer o plano de fotos e vídeo antes de gerar (Anexo A4). Nenhuma imagem de IA pode parecer o aparelho
   real (`PENDENCIAS.md:211` pede foto real, com consentimento).
9. **Para o consolidado:**
   - sugerir registrar no vault um erro novo: "afirmar fato do produto no site sem conferir o código ('em piloto',
     '12 pontos', 'conforme a LGPD')";
   - sugerir atualizar `stack-padrao.md`: `proxy.ts`, `priority` → `preload` e React 19.3.0 ainda a provar.

## Perguntas que só o Matheus responde
1. Existe conversa real com alguma transportadora ou empresa de ônibus? Se existe, com quem, e ela autoriza ser citada?
2. Qual é a oferta do piloto: quantos veículos, prazo, preço, quem instala, qual aparelho e qual câmera?
3. Posso recomendar mexer no backend antes de publicar a privacidade (consentimento que bloqueia eventos, vídeo órfão,
   HTTPS)?
4. Vai contratar parecer jurídico e RIPD? A transportadora será a controladora e o DriveSafe, o operador?
5. A versão EN serve a quem (investidor, parceiro de fora, fornecedor de câmera)? Precisa estar pronta no lançamento?
6. O painel será programa de computador ou app? Qual tela o site deve mostrar?
7. O kit do piloto terá câmera infravermelha? A resposta muda as frases sobre óculos escuros e noite.
8. O nome "DriveSafe" foi conferido no INPI? Já existem produtos com esse nome na mesma categoria.
9. Qual é o domínio definitivo (para canonical, Open Graph e JSON-LD)?
10. Qual número de WhatsApp vai no botão? Hoje ele está sem link (`:406`).

---

## Anexo A · Técnica em detalhe

### A1. Contraste WCAG, calculado com as cores do CSS
Cálculo pela fórmula de luminância relativa da WCAG 2.x. O AA exige 4,5:1 para texto normal e 3:1 para texto grande
(24 px, ou 18,66 px em negrito).

| Texto / fundo | Onde | Tamanho | Contraste | AA |
|---|---|---|---|---|
| `#6f6f69` / `#0b0c0e` | provas `:66`, "PT · EN" `:47`, legenda `:152`, rodapé `:199` | 12,5 a 12,8 px | 3,87:1 | reprova |
| `#6f6f69` / `#121417` | métricas da demo `:83`, nota da demo `:88`, rota `:128` | 10,6 a 12,8 px | 3,65:1 | reprova |
| `#6f6f69` / `#0f1114` | lateral do painel `:112, 122-123` | 11,2 a 11,5 px | 3,74:1 | reprova |
| `#6f6f69` / `#181b1f` | KPIs `:133`, título de painel `:138`, detalhe do evento `:146` | 11,2 a 12,8 px | 3,42:1 | reprova |
| `#6f6f69` / `#20242a` | rótulos do olho no SVG `:442` | 10,7 px no desktop, 5,8 px em 400 px | 3,08:1 | reprova |
| `#ffffff` / `#ff5b4f` | status do alarme `:79`, topo da tela da cabine `:165` | 12 a 12,5 px | 3,06:1 | reprova |
| `#a2a19a` / `#0b0c0e` a `#181b1f` | texto secundário | — | 6,67 a 7,55:1 | passa |
| `#eceae4` / `#0b0c0e` | texto principal | — | 16,27:1 | passa |
| `#ffb224` / `#0b0c0e` | kicker, destaque do h1 | — | 10,85:1 | passa |
| `#1b1300` / `#ffb224` | botão primário `:51` | 14,8 a 16 px | 10,22:1 | passa |
| `#ff5b4f` / `#181b1f` | evento crítico `:145` | 12,8 px | 5,65:1 | passa |
| `#ff5b4f` / vermelho a 14% sobre `#181b1f` | etiqueta "Risco crítico" `:129` | 12 px | 4,74:1 | passa por pouco |
| `#46c17f` / verde a 10% sobre `#121417` | status normal `:77` | 12 px | 6,95:1 | passa |
| `#5c5c57` / `#f1f0eb` | texto das especificações `:188` | — | 5,89:1 | passa |
| `#9a5b00` / `#f1f0eb` | kicker das especificações `:187` | 12,5 px | 4,75:1 | passa por pouco |
| `#3b4047` / `#20242a` | pontos do rosto `:463` | não é texto | 1,49:1 | decorativo (ok se `aria-hidden`) |

Correções calculadas:
- `#8a8982` como texto apagado: 5,57:1 sobre o fundo, 5,26:1 sobre `surface` e 4,92:1 sobre `surface-2`. Nos rótulos
  do SVG, `#908f88` dá 4,80:1.
- Alarme: texto `#0b0c0e` sobre `#ff5b4f` dá 6,39:1. Se quiser texto branco, o vermelho precisa ir para `#cf3a2f`
  (4,88:1).

### A2. Fonte, foco, semântica, menu e SVG
- **Tamanhos pequenos:**
  - 0,66rem = 10,56 px, em maiúsculas espaçadas (`:83`);
  - 0,7rem = 11,2 px (`:71, 112, 114, 123, 133`);
  - 0,72rem = 11,52 px (`:88, 122, 150, 169, 177`);
  - 0,75rem = 12 px;
  - 0,78rem = 12,48 px;
  - 0,8rem = 12,8 px.

  A WCAG não fixa tamanho mínimo. Mas, somado ao contraste baixo e à fonte mono estreita, o print de 400 px mostra
  rótulos ilegíveis. Proposta: 12 px para rótulo em maiúsculas, 14 px para texto de leitura, e nada menor no celular.
- **SVG com texto:**
  - "OLHO DIREITO · EAR 0,33" tem `font-size` 13 num `viewBox` de 800 de largura (`:249, 442`). Isso dá 10,7 px no
    desktop (demonstração com cerca de 658 px) e **5,8 px** no celular (cerca de 358 px).
  - O "Dia do motorista" usa `preserveAspectRatio="none"` com texto (`:331, 540`). No celular, a escala horizontal cai
    para cerca de 0,37, e as horas ficam espremidas.
- **Foco:**
  - Nenhum `outline: none`: o foco padrão do navegador continua visível.
  - Não há estilo próprio de `:focus-visible` nem link "Pular para o conteúdo".
  - Os botões têm 40 px de altura (`:50`), acima do mínimo de 24 px do WCAG 2.5.8.
- **Semântica:**
  - A hierarquia está certa: um h1 (`:230`), um h2 por seção e um h3 só dentro da tela simulada ("João Pereira",
    `:319`). Esse h3 põe um nome fictício no sumário da página e deve virar `p`.
  - `aria-label` em `div` sem `role` (`:243, 300`) é ignorado, porque o papel `generic` não aceita nome (WAI-ARIA 1.2).
  - O `svg` tem `aria-label` sem `role="img"` (`:358`).
  - A tabela de eventos não tem `th` nem `caption` (`:335-339`).
  - "Revisar" e os chips são `span` com cara de botão dentro de uma tela simulada. Tratar a tela inteira como imagem
    (`role="img"` com `aria-label`) evita que o leitor anuncie botões falsos.
- **Menu no celular:**
  - `.menu` some abaixo de 62rem (`:44-45`), e **não há botão para abrir**.
  - "Entrar" some abaixo de 40rem (`:48-49`).
  - Em qualquer tela menor que 992 px, a navegação some. No celular, também some o acesso de cliente pedido em
    `contexto.md:44`.
- **Demonstração com rótulo:**
  - O SVG está em `aria-hidden` (`:249, 258`), e o bloco não tem nome efetivo (`:243`).
  - As métricas mudam a cada quadro sem `aria-live`. É bom que não sejam anunciadas, mas quem navega com leitor ouve
    números mudando.
  - Proposta: `<figure>` com `<figcaption>` fixo ("Simulação: duas piscadas normais e um fechamento de 1,2 s que
    dispara o alarme") e a parte animada em `aria-hidden`.

### A3. Movimento reduzido e animação contínua
- `prefers-reduced-motion` é lido uma vez, com `matchMedia(...).matches` (`:516`). Se a pessoa mudar a preferência com
  a página aberta, nada muda. Não há `@media (prefers-reduced-motion)` no CSS (a transição da borda em `:69` é curta e
  aceitável).
- Com movimento liberado, a animação começa sozinha, **nunca termina** e não tem controle (`:521-532`). Isso descumpre
  o WCAG 2.2.2 (pausar, parar, ocultar).
- A borda vermelha pisca uma vez a cada 9 s, bem abaixo do limite de 3 flashes por segundo do WCAG 2.3.1.
- O `requestAnimationFrame` continua enquanto a aba estiver visível, **mesmo com a demonstração fora da tela**. Não há
  `IntersectionObserver` nem `visibilitychange`.
- O modo reduzido congela no quadro do alarme (`:518`). É aceitável, mas deixa uma caixa vermelha "MICROSSONO" parada
  para sempre. Um quadro final "Risco normal · alarme registrado" assusta menos.

### A4. Desempenho hoje e quando entrarem fotos e vídeos
**Hoje:**
- HTML de 37 KB, com CSS e JS embutidos e nenhuma imagem. O maior elemento do topo é o h1 (LCP provável; não medido
  nesta rodada).
- A fonte vem de um CSS do Google que bloqueia a renderização: 2 famílias e 6 pesos (`:8-10`). Com `display=swap`, a
  fonte troca depois de carregar, e o h1 de até 76 px pode pular (CLS).
- A animação faz cerca de 50 escritas no DOM por quadro, a 60 quadros por segundo:
  - 2 olhos, cada um com contorno, recorte, 6 pontos de 3 atributos e rótulo;
  - status e 4 métricas;
  - além disso, a curva de 270 pontos é refeita 30 vezes por segundo (`:447-456, 495-514, 524-529`).

**Na versão Next:**
- Usar `next/font`, que baixa a fonte no build, serve do próprio domínio e ajusta a fonte reserva para evitar o pulo.
  Nenhum pedido vai ao Google.
- A animação vira componente cliente que escreve por `ref` e para fora da tela.

**Quando entrarem fotos e vídeos:**
- **Foto do topo:** vira o LCP. Usar `next/image` com `preload` (o Next 16 depreciou `priority`) ou
  `fetchPriority="high"`, com `sizes` correto e `width`/`height` (ou `fill` num contêiner de proporção fixa) para não
  pular.
- **Formatos:** `images.formats: ['image/avif', 'image/webp']`. O padrão é só WebP. No Next 16, o padrão de `qualities`
  virou `[75]` e o de `minimumCacheTTL`, 4 h.
- **Abaixo da dobra:** `loading="lazy"`, que já é o padrão do `next/image`.
- **Recortes:** um para 1440 px e outro para 400 px, porque cenas de cabine têm o rosto no centro e o texto precisa de
  espaço.
- **Vídeo:**
  - nunca como LCP sem `poster`;
  - usar `muted`, `playsInline`, `loop` e `preload="none"` (ou `metadata`);
  - começar só quando estiver visível e não começar com movimento reduzido;
  - arquivos MP4 H.264 e WebM;
  - nada de iframe de YouTube ou Vimeo sem fachada;
  - legenda se houver fala (WCAG 1.2.2).
- **Metas no percentil 75:** LCP até 2,5 s, INP até 200 ms e CLS até 0,1 (web.dev).
- **Veracidade da mídia:** imagem gerada não pode mostrar o "aparelho DriveSafe" como se ele existisse. O hardware
  está em aberto (`contexto.md:38`; `PENDENCIAS.md:211`).

### A5. SEO
| Item | Hoje | Proposta |
|---|---|---|
| `title` | "DriveSafe — prévia v2 (página de produto)" (`:6`) | PT: "DriveSafe · Alarme de sono e celular para motoristas de frota". EN: "DriveSafe · Drowsiness and phone-use alarm for fleet drivers". Palavras são hipótese; validar com dados de busca |
| `meta description` | ausente | 150 a 160 caracteres: o que é, para quem, e "sem gravar imagem" |
| Open Graph e Twitter | ausentes | `openGraph` com `locale` `pt_BR` ou `en_US` e imagem de 1200×630 (`opengraph-image.tsx` por idioma) |
| canonical | ausente | `alternates.canonical` por idioma |
| hreflang | ausente | `alternates.languages` com `pt-BR`, `en` e `x-default`. O proxy do next-intl envia o cabeçalho `Link` por padrão, e o `sitemap.ts` leva os alternates |
| Dados estruturados | ausentes | `Organization` na home (name, url, logo, contactPoint com telefone ou WhatsApp, areaServed BR). `Product` só com `offers` real, nunca com `review` inventado |
| Títulos | h1 único (`:230`), h2 por seção, h3 dentro da tela simulada (`:319`) | Manter a ordem. O h1 deve dizer o que o comprador procura. Tirar o h3 da tela |
| Favicon e robots | ausentes | `icon.png` e `apple-icon.png`. Prévias publicadas com `noindex` |
| Nome | "DriveSafe" já usado na mesma categoria (Embitel; app no Google Play, Anexo D) | Conferir no INPI. Usar "DriveSafe AI" de forma consistente, ou outro nome |

### A6. Idiomas: o "PT · EN" é falso e o que o next-intl precisa
"PT · EN" é um `span` sem link, e não existe versão EN (`:218, 412`; `PENDENCIAS.md:210`). Para o next-intl
(4.14.4 hoje):
1. `src/i18n/routing.ts` com `defineRouting({ locales: ['pt-BR', 'en'], defaultLocale: 'pt-BR', localePrefix: 'always' })`.
   O prefixo sempre visível é o padrão do vault (`stack-padrao.md:69`).
2. `src/proxy.ts`, porque no Next 16 o `middleware.ts` virou `proxy.ts`. A documentação do next-intl já usa esse nome.
3. `src/i18n/request.ts`, que carrega `messages/${locale}.json`, e `src/i18n/navigation.ts` (`Link`, `redirect`,
   `usePathname`).
4. `src/app/[locale]/layout.tsx` com:
   - `<html lang={locale}>`;
   - `generateStaticParams`;
   - `generateMetadata` por idioma.

   Para a renderização estática, a documentação atual aponta `next/root-params` e trata `setRequestLocale` como API
   legada (conferir na hora de implementar).
5. `messages/pt-BR.json` e `messages/en.json` com **todo** texto visível, inclusive o que hoje está no JS da
   demonstração (`:442, 454, 499-505`), os rótulos do SVG, as linhas de especificação e os dados de demonstração.
6. Números, durações e horas com o formatador do next-intl (`useFormatter`), nunca com `toFixed().replace(".", ",")`
   (`:418`).
7. O seletor de idioma deve ter links reais, que mantêm a mesma rota, com `hreflang` e `lang` no próprio link.
8. Termos jurídicos em EN precisam de contexto: "Brazilian Traffic Code (CTB), art. 67-C" e "LGPD, Brazil's data
   protection law".
9. Prova: o build pré-renderiza os dois idiomas. Conferir o `<html lang>` e o cabeçalho `Link` em `/pt-BR` e em `/en`.

### A7. Migração para Next.js 16 + Tailwind 4: o que vira token, primitivo, componente e conteúdo tipado
Armadilhas do vault que valem aqui:
- regra sem camada vence qualquer camada (erro 53);
- override de token dentro de `@layer` quebra (erro 54);
- nome de classe que já é utilitário (`overline`, `col-7`, `table`) colide (erro 52);
- no `@theme inline`, o nome do utilitário deve ser diferente do nome do token (`stack-padrao.md:90-92`);
- a fonte vem de `next/font` (`stack-padrao.md:104`).

**Tokens** (`src/app/globals.css`, em `:root`, **fora de camada**, junto com os overrides), mapeados no `@theme inline`
com outro nome:

| Prévia (`:12-32`) | Token em `:root` | `@theme inline` | Nota |
|---|---|---|---|
| `--bg` | `--c-bg` | `--color-bg: var(--c-bg)` → `bg-bg` | Mesmo padrão do ACEX (`stack-padrao.md:75`) |
| `--surface`, `--surface-2` | `--c-surface`, `--c-surface-2` | `--color-surface`, `--color-surface-2` | |
| `--line`, `--line-soft` | `--c-line`, `--c-line-soft` | `--color-line`, `--color-line-soft` | |
| `--text`, `--muted`, `--dim` | `--c-fg`, `--c-fg-muted`, `--c-fg-dim` | `--color-fg`, `--color-fg-muted`, `--color-fg-dim` | `--c-fg-dim` passa a ser `#8a8982` (AA). Evitar `text-text` |
| `--amber`, `--red`, `--green` | `--c-signal`, `--c-alarm`, `--c-ok` | `--color-signal`, `--color-alarm`, `--color-ok` | Nomes de papel, não `red` e `green`, que ficam ao lado da paleta padrão (`red-500`) |
| (novo) | `--c-on-signal: #1b1300`, `--c-on-alarm: #0b0c0e` | `--color-on-signal`, `--color-on-alarm` | Calculados pela WCAG (erro 50, `erros-que-a-ia-comete.md:302-306`) |
| `--paper`, `--ink`, `--ink-muted`, `--paper-line` | `--c-paper`, `--c-ink`, `--c-ink-muted`, `--c-paper-line` | Trocados no escopo da seção clara: `[data-tone="paper"] { --c-bg: var(--c-paper); ... }`, fora de camada | Hoje estão fixos em `.specs` (`:186-193`) |
| `--sans`, `--mono` | variáveis do `next/font` | `--font-sans: var(--font-geist-sans)`, `--font-mono: var(--font-geist-mono)` | Ver a nota sobre a Geist abaixo |
| `--max: 80rem` | — | `--container-shell: 80rem` → `max-w-shell` | |
| `--pad` | `--c-gutter: clamp(1.25rem, 4vw, 3rem)` | usado pelo primitivo `.shell` | |

**Primitivos** (`@layer components`) e regras de elemento (`@layer base`):

| Prévia | Destino | Nota |
|---|---|---|
| `* { box-sizing }`, `a { color: inherit }`, `h1, h2, h3, p { margin: 0 }` (`:33-36`) | **Não copiar** | O Preflight do Tailwind 4 já faz isso em `@layer base`. Copiado sem camada, repete o erro 53 (texto da cor do fundo no botão, seções coladas) |
| `.btn`, `.btn-primary`, `.btn-ghost`, `.btn-lg` (`:50-53`) | `@layer components` | Com `display: inline-flex` dentro da camada, o `hidden` volta a funcionar |
| `.shell` (`:37`) | `@layer components` | `max-width` e `padding-inline` pelos tokens |
| `.kicker` (`:98`) | `@layer components` (ou `eyebrow`, o nome da casa) | Nunca `overline`, que é utilitário (erro 52) |
| `.tag` (`:60-61`), `.section` (`:96`) | `@layer components` | |
| `.mono` (`:38`) | Utilitário `font-mono` | Não criar classe |
| Consultas de contêiner com `cqi` (`:59, 62, 97, 99, 166-168`) | `@container` e variantes do Tailwind 4, ou valor arbitrário `text-[clamp(2.5rem,12cqi,4.75rem)]` | |

**Componentes** (`src/components/`, arquivos em kebab-case, exportação nomeada, `regras-de-componentes.md:14`):

| Parte da prévia | Componente | Servidor ou cliente | Nota |
|---|---|---|---|
| Topo `:205-223` | `site-header.tsx`, `mobile-menu.tsx`, `language-switcher.tsx` | Topo no servidor; menu e seletor com `'use client'` | O menu de celular hoje não existe |
| Texto do topo `:228-241` | `sections/hero.tsx` | servidor | As provas vêm de `src/content/proofs.ts` |
| Demonstração `:243-260, 416-533` | Pasta `eye-monitor-demo/`: `eye-monitor-demo.tsx` (`'use client'`), `eye-geometry.ts` (funções puras `bez`, `eyeShape`, `openness`) e `use-demo-clock.ts` (rAF, `IntersectionObserver`, movimento reduzido, pausa) | cliente | Escrever no DOM por `ref`, não com `setState` a cada quadro. A geometria fica testável |
| Na cabine `:264-291` | `sections/cabin.tsx`, `alert-ladder.tsx`, `cabin-alarm-screen.tsx` (só se virar "conceito") | servidor | A escada vem de `src/content/alert-ladder.ts` |
| Painel `:293-346` | `sections/fleet-panel.tsx` e pasta `fleet-panel-mock/`: `vehicle-list.tsx`, `kpi-grid.tsx`, `driver-day-strip.tsx`, `event-table.tsx` | servidor (SVG estático) | Só recursos que existem. Dados de `src/content/demo-fleet.ts` |
| Privacidade `:348-377` | `sections/privacy.tsx`, `data-flow.tsx`, `eye-points.tsx`, `event-payload.tsx` | servidor | `eye-points` reaproveita `eye-geometry.ts` |
| Especificações `:379-397` | `sections/specs.tsx` | servidor | Vem de `src/content/specs.ts` |
| Chamada final `:399-408` | `sections/pilot-cta.tsx`, `whatsapp-link.tsx` | servidor | O número vem de `src/content/site.ts` |
| Rodapé `:411-413` | `site-footer.tsx` | servidor | |

**Conteúdo tipado** (`src/content/*.ts`, com `interface` nomeada, `regras-de-componentes.md:32-41`). O texto visível
fica em `messages`; o `content` guarda estrutura, números e fonte:

| Arquivo | Tipo | Conteúdo | Fonte a registrar |
|---|---|---|---|
| `alert-ladder.ts` | `AlertStage { seconds; eventType; eventRisk; messageKey }` | 3 degraus: 1 s `microssono` (3), 3 s `sono` (4), 6 s `nao_responsivo` (5) | `vision/drowsiness.py:71-75` |
| `proofs.ts` | `Proof { value; messageKey; source }` | 3 provas do topo | `vision/drowsiness.py:28`; `vision/event_queue.py:1` |
| `specs.ts` | `SpecItem { id; messageKey; status; source }`, com `status` "testado" ou "em teste" | 8 linhas de especificação | Anexo B |
| `demo-signal.ts` | `DemoSignal { cycleS; blinksS; closure; alarmOnS; holdCriticalS }` | Tempos da animação, com o "Crítico" segurado por 10 s | `vision/risk.py:24` |
| `demo-fleet.ts` | `DemoVehicle`, `DemoEvent`, `DemoDriverHour`, todos com `demo: true` | Frota fictícia, sem rota nem curva do olho | `backend/routes/fleet.py:78-79`; `backend/queries.py:103-104` |
| `event-example.ts` | `DeviceEvent`, espelhando `backend/schemas.py:73-82` | O JSON do card de privacidade, resumido e honesto | `vision/event_queue.py:85-97` |
| `site.ts` | `SiteConfig { whatsapp; loginUrl; domain; legalLinks }` | Contato, login e links legais | `contexto.md:44` |
| `claims.ts` | `Claim { messageKey; source }` | Toda frase de fato aprovada, com a fonte | Anexo B |

> [!note] Hipótese, confirmar com a frente 2
> Geist e Geist Mono são exatamente as fontes do modelo do `create-next-app` (URL no Anexo D). Isso reforça a leitura de
> "genérico" do Matheus. A escolha da fonte é da frente 2. Aqui fica só a regra: seja qual for, entra por `next/font`.

### A8. Versões conferidas no registro npm (11/09/2026) e travas
| Pacote | `latest` hoje | Usar | Justificativa |
|---|---|---|---|
| `next` | 16.3.4 | 16.3.4 | Última estável |
| `react`, `react-dom` | 19.3.0 | 19.3.0, provar | Mais nova que a 19.2.8 validada no vault (`stack-padrao.md:44`). Só build e lint provam |
| `next-intl` | 4.14.4 | 4.14.4 | Aceita `next` ^16 (peerDependencies) |
| `tailwindcss`, `@tailwindcss/postcss` | 4.3.3 | 4.3.3 | Última estável |
| `eslint-config-next` | 16.3.4 | 16.3.4 | Mesma versão do Next |
| `typescript` | 7.0.2 | **6.0.3 (travado)** | `typescript-eslint@8.70.0` aceita `typescript >=4.8.4 <6.1.0`; 6.0.3 é a última 6.0.x (erro 30) |
| `eslint` | 10.10.0 | **9.39.5 (travado, tag `maintenance`)** | `eslint-plugin-react@7.37.5` (usado pelo `eslint-config-next`) aceita `eslint` só até `^9.7` e não é publicado desde 03/04/2025 (erro 30) |
| `geist` | 1.7.2 | só se não usar `next/font/google` | — |
| Node | — | 20.9.0 ou maior | Mínimo do Next 16 |

Mudanças do Next 16 que afetam este site:
- `middleware.ts` virou `src/proxy.ts`;
- a prop `priority` do `next/image` foi depreciada em favor de `preload`;
- `next lint` foi removido: o script passa a ser `"lint": "eslint ."`, com `eslint.config.mjs` em flat config;
- `images.qualities` passou a ter `[75]` como padrão.

A prova é `npm run build` **e** `npm run lint` (`stack-padrao.md:43-51`).

---

## Anexo B · Tabela de veracidade completa
Veredito: **VERDADEIRA**, **FALSA**, **EXAGERADA** ou **NÃO VERIFICÁVEL**. A coluna "Linha" é de `index.html`.

| # | Seção | Afirmação | Linha | Veredito | Evidência | Texto corrigido |
|---|---|---|---|---|---|---|
| V01 | Topo e rodapé | "PT · EN" | 218, 412 | FALSA | `span` sem link; a versão EN não existe (`PENDENCIAS.md:210`) | Tirar até existir EN. Depois, links reais para `/pt-BR` e `/en` |
| V02 | Selo do topo | "Em piloto com transportadoras" | 229 | FALSA | `contexto.md:37`; `PENDENCIAS.md:41, 93, 210-212`; `README.md:440-447` (Anexo C5) | "Protótipo em testes · vagas para o primeiro piloto" |
| V03 | H1 | "Microssono dura 1 segundo." | 230 | EXAGERADA | O Euro NCAP define microssono como fechamento de 1 a 2 s. A literatura fala de 1 a 15 s (Skorucak et al., 2020). No código, 1 s é o gatilho (`vision/drowsiness.py:4, 28`) | "Olhos fechados por 1 segundo." |
| V04 | H1 | "O alarme também." | 230 | FALSA (leitura literal) | A sirene dura 2,0 s e se repete enquanto o olho continua fechado (`vision/alarm.py:18-21, 100-107`; `vision/drowsiness.py:366-368`) (Anexo C2) | "Alarme na cabine." (h1 inteiro: "Olhos fechados por 1 segundo. Alarme na cabine.") |
| V05 | Subtítulo | "Uma câmera na cabine mede os olhos do motorista a cada quadro" | 231 | VERDADEIRA | `vision/face.py:232-313`; `vision/driver_monitor.py:213-233` | Manter ("mede o rosto e os olhos") |
| V06 | Subtítulo | "dispara o alarme quando eles fecham" | 231 | EXAGERADA | Só com o olho fechado por 1 s ou mais (`vision/drowsiness.py:28, 366-368`) ou com padrão de sonolência (`:310-311`). Piscada não dispara. Olho não visível não é medido (`vision/engine.py:101`) | "dispara o alarme quando eles ficam fechados por 1 segundo" |
| V07 | Subtítulo | "e envia o evento para a frota" | 231 | VERDADEIRA | `vision/event_queue.py:61-74`; `vision/sync.py:139-165`; `backend/routes/device_api.py:107-144` | "e registra o evento para o gestor da frota" |
| V08 | Subtítulo e prova | "Nenhuma imagem é gravada." e "0 imagens gravadas" | 231, 238 | VERDADEIRA (no aparelho do veículo) | Nenhuma gravação de quadro em `vision/`; `README.md:161`. Ressalvas: o modo teste transmite vídeo, e o vídeo enviado para análise pode ficar guardado (Anexo C1) | "O aparelho do veículo não grava nem envia imagem." |
| V09 | Prova | "1 s olhos fechados = alarme" | 237 | VERDADEIRA | `vision/drowsiness.py:28, 72, 366-368`; `vision/risk.py:131-132`. Ressalvas: exige olho visível e som configurado (`vision/alarm.py:94-98`) | "1 s de olhos fechados = alarme" |
| V10 | Prova | "offline guarda e envia depois" | 239 | VERDADEIRA | `vision/event_queue.py:1, 32-74`; `vision/sync.py:80-83, 107-111` | "sem sinal: guarda e envia depois" |
| V11 | Demonstração | "DEMONSTRAÇÃO" e "Simulação do sinal que o sistema mede" | 246, 259 | VERDADEIRA | As métricas são as da janela real (`vision/driver_monitor.py:85-94`) | Manter |
| V12 | Demonstração | O risco volta a "Normal" cerca de 2 s depois do alarme | 486, 501, 505 | FALSA | O "Crítico" fica 10 s e desce um nível por vez (`vision/risk.py:14, 24, 153-161`) | Manter "Crítico" por 10 s na animação e depois "Alto" |
| V13 | Na cabine, H2 | "O aviso chega antes de o caminhão sair da faixa." | 268 | NÃO VERIFICÁVEL | Nenhum dado de faixa nem validação com motoristas (`README.md:446`; `PENDENCIAS.md:41`). A 80 km/h, 1 s são 22 m. O model card diz que não serve para decisão crítica à vida (`THIRD_PARTY_NOTICES.md:21`) | "O alarme toca no primeiro segundo de olhos fechados." |
| V14 | Na cabine | "O motorista não precisa tocar em nada." | 269 | VERDADEIRA | Calibração e detecção automáticas (`run_monitor.py:168-185`; `vision/calibration.py:58-92`) | Manter |
| V15 | Na cabine | "Cada motorista é comparado com ele mesmo descansado" | 269 | EXAGERADA | "Descansado" é suposição. Sem perfil anterior, uma calibração suspeita vira referência (`vision/drowsiness.py:522-523, 534-537`). Os alarmes de 1, 3 e 6 s não dependem da calibração (`README.md:126`) (Anexo C6) | "Cada motorista é comparado com o próprio começo de viagem. Se ele já começar cansado, o sistema marca a calibração como suspeita." |
| V16 | Na cabine | "os primeiros minutos da viagem calibram o jeito de piscar de cada pessoa" | 269 | VERDADEIRA | De 5 a 10 min com o rosto visível (`run_monitor.py:75-78`; `vision/calibration.py:59, 89-92`). O modo YuNet não calibra (`vision/face.py:324`) | "os primeiros 5 a 10 minutos da viagem calibram o jeito de piscar de cada pessoa" |
| V17 | Escada, 1 s | "Olhos fechados por 1 segundo: alarme na hora." | 271 | VERDADEIRA | `vision/drowsiness.py:72, 366-368`. A latência no Raspberry Pi não foi medida (`README.md:417`) | Manter |
| V18 | Escada, 3 s | "O alarme continua e o evento sobe como crítico." | 272 | VERDADEIRA (imprecisa) | A sirene se repete (`vision/alarm.py:100-107`) e nasce um novo evento `sono`, com risco 4 (`vision/drowsiness.py:73`). Mas o nível já era crítico desde 1 s (`:366-368`) | "O alarme continua, e um segundo evento, mais grave, é registrado." |
| V19 | Escada, 6 s | "O gestor é avisado no painel imediatamente." | 273 | EXAGERADA | Envio a cada 5 s; depois de falha, espera de 10 s a 5 min; sem internet, só quando voltar; aparece só com o painel aberto; não há push, SMS nem ligação (Anexo C3) | "O evento mais grave chega ao painel em segundos, com sinal de celular. Sem sinal, assim que ele voltar." |
| V20 | Tela da cabine | "RISCO CRÍTICO · Microssono · Pare em local seguro · ALARME SONORO ATIVO" | 276-288 | FALSA | Não existe tela de cabine. O aparelho roda sem janela ou abre a janela de teste do OpenCV, com a imagem da câmera e texto sem acento (`vision/driver_monitor.py:21-22, 68-127`). "Pare em local seguro" não existe no repositório. Hardware em aberto (`contexto.md:38`) | Tirar, ou rotular "Conceito de tela, em desenvolvimento". Mostrar o que existe: sirene e evento |
| V21 | Painel, H2 | "A frota inteira ao vivo." | 297 | VERDADEIRA (na API) | `/api/fleet` (`backend/routes/fleet.py:78-79`); estado a cada 15 s (`backend/config.py:18-19`; `run_monitor.py:208`). As telas nunca foram abertas num navegador (`PENDENCIAS.md:173`) | "Todos os veículos, com o risco atualizado a cada 15 segundos." |
| V22 | Painel | "o risco de cada veículo agora, o dia de cada motorista e a fila de eventos para revisar" | 298 | VERDADEIRA (na API) | `backend/routes/fleet.py:78`; `backend/routes/people.py:119-127` (pior risco por hora, `backend/queries.py:103-104`); revisão em `backend/routes/alerts.py:65-81` | "...o dia de cada motorista, hora a hora, e a fila de eventos para revisar" |
| V23 | Painel | "com a curva do olho de cada um" (curvas na tabela) | 298, 334-339 | FALSA | O evento leva medidas resumidas, sem a série de abertura do olho (`vision/drowsiness.py:414-448`; `vision/event_queue.py:85-97`). O `webapp/` não tem nenhuma curva | "com as medidas de cada evento: tempo de olho fechado, PERCLOS e piscadas" |
| V24 | Tela do painel | Rota "São Paulo → Curitiba · BR-116" | 320 | FALSA (recurso inexistente) | Não há GPS nem rota, só um arquivo opcional de velocidade (`vision/context.py:32-33, 79-94`) | Tirar |
| V25 | Tela do painel | "Direção hoje 7 h 48 min", faixa de direção e pausa, "21 rodando" | 304, 324, 330-331, 543-545 | FALSA (recursos inexistentes) | Só existe a direção contínua estimada (`vision/context.py:40-62`). O servidor guarda só o último estado (`backend/database.py:153`). "Parado" exige telemetria (`vision/context.py:64-66`) | Mostrar "Direção contínua" e o dia hora a hora por risco |
| V26 | Tela do painel | KPI "PERCLOS 3 min 14 %" do veículo, ao vivo | 327 | EXAGERADA | O PERCLOS de 3 min só vai dentro dos eventos (`vision/drowsiness.py:438-439`), não no estado ao vivo (`vision/driver_monitor.py:189-203`) | "PERCLOS no último evento" |
| V27 | Legenda | "Tela com dados de demonstração." | 344 | VERDADEIRA (incompleta) | Os dados são fictícios, mas a tela também mostra recursos que não existem (V23 a V26) | "Tela conceitual com dados de demonstração." |
| V28 | Privacidade, H2 | "A imagem fica no caminhão." | 352 | EXAGERADA | A imagem não fica: é processada em memória e descartada (`vision/driver_monitor.py:169-180`). "Caminhão" deixa o ônibus de fora | "A imagem não é guardada nem sai do aparelho." |
| V29 | Privacidade, H2 | "Só o evento sai dele." | 352 | FALSA | A cada 15 s também sai o estado ao vivo: nível e motivos do risco, rosto visto, olhos visíveis, celular, horas de direção, fps, nome e sistema do aparelho, IP (`vision/driver_monitor.py:182-207`; `vision/sync.py:87-93, 125-129`; `backend/routes/device_api.py:41-48, 82-98`) | "Saem só números: eventos e o estado do aparelho. Nenhuma imagem." |
| V30 | Privacidade | "A câmera transforma cada quadro em pontos do olho e descarta a imagem." | 353 | EXAGERADA | Mede 478 pontos do rosto, pose da cabeça, boca e mãos (21 pontos cada), procura celular e recorta os olhos para um classificador (`vision/face.py:3, 217-227, 247-313`; `vision/phone.py:3-5, 170-189`; `vision/eye_state.py:45-70`). O descarte da imagem é verdadeiro | "A cada quadro, o aparelho mede o rosto, as mãos e o celular e descarta a imagem." |
| V31 | Privacidade | "Para a empresa vai apenas o registro do evento" | 353 | FALSA | Igual à V29. Além disso, os detalhes de cada evento trazem várias medidas, e o resumo da calibração do motorista também vai (`vision/drowsiness.py:356-363, 414-448, 521, 530`; `vision/engine.py:223-235`) | "Para a empresa vão eventos e medidas, nunca imagem." |
| V32 | Privacidade | "com o consentimento do motorista" | 353 | EXAGERADA | O consentimento é registrado com histórico (`backend/routes/people.py:130-146`; `backend/database.py:25-27`), mas o servidor aceita eventos sem checar o de "monitoramento" (`backend/routes/device_api.py:51-58, 107-144`). Só o perfil entre viagens e o envio de sinais de ativação dependem dele (`backend/routes/device_api.py:54-57`; `vision/remote_policy.py:66-76`) | "O motorista registra as autorizações e pode baixar os próprios dados." (`backend/routes/people.py:149-170`) |
| V33 | Privacidade | "conforme a LGPD" | 353 | NÃO VERIFICÁVEL (e arriscada) | Sem parecer e sem RIPD (`README.md:170, 457`); possível dado sensível; HTTP no exemplo de instalação (`deploy/raspberry-pi/device.env.example:4`) (Anexo C9) | Tirar. Usar fatos verificáveis (V08, V32) |
| V34 | Card | "NO VEÍCULO · A CADA QUADRO · descartado" | 357 | VERDADEIRA | Processamento em memória (`vision/driver_monitor.py:169-180`) | Manter |
| V35 | Card | "12 pontos por olho" | 359 | FALSA | São 6 pontos por olho para medir a abertura (`vision/face.py:35-37`) e mais 5 da íris (`:38-42`). O próprio código da prévia desenha 6 (`:420, 440`) | "6 pontos por olho, mais a íris" |
| V36 | Card | "abertura e direção do olhar" | 359 | VERDADEIRA | `vision/eyes.py:135-186`; `vision/face.py:95-97, 183-184` | Manter |
| V37 | Card | "Nenhum pixel é salvo." | 359 | VERDADEIRA (no aparelho) | Igual à V08 | "Nenhuma imagem é salva no aparelho." |
| V38 | JSON | Exemplo com 5 campos, "ENVIADO PARA A FROTA · 1 evento" | 363-371 | EXAGERADA | O evento real tem `event_uid`, `alert_type`, `risk_level`, `duration`, `occurred_at`, `age_seconds` e `details` com várias medidas (`vision/event_queue.py:85-97`; `vision/drowsiness.py:356-363`). A placa não sai do aparelho: o servidor liga o evento ao veículo pelo token (`backend/routes/device_api.py:120-122`) | Mostrar o evento real, resumido, com `"details": {…}` e a legenda "resumido" |
| V39 | Card | "Sem internet, fica na fila do aparelho e é enviado quando o sinal volta." | 373 | VERDADEIRA | `vision/event_queue.py:1`; `vision/sync.py:107-111`. Nova tentativa em até 5 min (`vision/sync.py:82`) | "...e é enviado quando o sinal volta, em poucos minutos." |
| V40 | Especificações | "Limiares iniciais baseados em literatura e em calibração individual" | 384 | VERDADEIRA | `vision/drowsiness.py:3-13`; `vision/calibration.py:3-8` | Manter |
| V41 | Especificações | "em validação com gravações reais" | 384 | EXAGERADA | As ferramentas estão prontas, mas as gravações não existem (`PENDENCIAS.md:41, 93`; `README.md:446`) | "a validar com gravações reais" |
| V42 | Críticos | "1 s (microssono), 3 s (sono) e 6 s (sem resposta)" | 387 | VERDADEIRA | `vision/drowsiness.py:28-30, 71-75`; Euro NCAP, p. 16 | Manter, citando o Euro NCAP |
| V43 | Sonolência | "PERCLOS, piscadas mais longas que a calibração, bocejos e cabeceios" | 388 | VERDADEIRA | `vision/drowsiness.py:33-44, 450-508`. O bocejo é só sinal leve (`:10`), e tudo depende da calibração (`:452-453`) | Manter |
| V44 | Celular | "Na mão, no ouvido ou olhando para ele." | 389 | VERDADEIRA | `vision/phone.py:95, 296-308, 341-346`. Os limiares "ainda são chute" (`PENDENCIAS.md:145`) | Manter e acrescentar "limiares a validar" |
| V45 | Celular | "No suporte, não conta" | 389 | EXAGERADA | É hipótese (`vision/phone.py:64-67`) e não foi testada (`README.md:446-447`). Olhar para o celular no suporte conta como "olhando o celular" (`vision/phone.py:300-302`) | "Celular parado no suporte não conta como celular na mão. Olhar para ele por mais de 2 s conta." |
| V46 | Contexto | "Madrugada e mais de 5 h 30 min ao volante pesam no risco" | 390 | VERDADEIRA (com ressalvas) | `vision/context.py:19-22`; `vision/risk.py:77-92`. Sem telemetria, "ao volante" é o rosto na câmera (`vision/context.py:55`) (Anexo C7) | "De madrugada ou depois de 5 h 30 min seguidas ao volante (CTB, art. 67-C), sinais leves de sono viram risco alto mais cedo." |
| V47 | Câmera | "Comum" | 391 | VERDADEIRA | Testado com webcam no Windows (`README.md:421-438`) | Manter |
| V48 | Câmera | "ou infravermelha" | 391 | NÃO VERIFICÁVEL | Previsto no código (`vision/pupil.py:31-65`; `run_monitor.py:66-67`), nunca testado (`README.md:442`) | "Câmera infravermelha: suporte em teste" |
| V49 | Câmera | "óculos escuros detectados" | 391 | EXAGERADA | Conferido só em 2 fotos com óculos pintados (`README.md:153, 434`; `vision/visibility.py:5-6`). Quando detecta, desliga as medidas do olho, então não detecta sono pelos olhos (`vision/visibility.py:3-4`; `vision/engine.py:101`) e só avisa depois de 10 s (`vision/engine.py:36, 212-221`) | "Com óculos escuros, o sistema percebe que não vê os olhos, não dispara alarme falso e avisa. Medir de óculos exige câmera infravermelha (em teste)." |
| V50 | Roda em | "Raspberry Pi, Linux, Windows e macOS" | 392 | EXAGERADA | Testado só no Windows 11 (`README.md:421-423, 440-441`). O Raspberry Pi nunca foi medido (`README.md:417`). No macOS Intel, cai no modo YuNet, sem calibração, pose da cabeça e bocejo (`vision/face.py:5, 320-324, 411-412`) | "Testado em computador com Windows. Raspberry Pi, Linux e macOS: em preparação." |
| V51 | Conexão | "Funciona sem internet; fila de eventos enviada depois" | 393 | VERDADEIRA | Alarme local (`vision/alarm.py`); fila (`vision/event_queue.py`; `vision/sync.py:107-111`) | Manter |
| V52 | Dados | "Sem imagens" | 394 | VERDADEIRA (no aparelho) | `README.md:161`; `backend/schemas.py:32` | "Nenhuma imagem sai do veículo" |
| V53 | Dados | "consentimento do motorista registrado" | 394 | VERDADEIRA | `backend/routes/people.py:130-146`; `backend/database.py:25-27` (ver a ressalva da V32) | Manter |
| V54 | Piloto, H2 | "Comece com cinco caminhões." | 403 | NÃO VERIFICÁVEL | Nenhuma oferta definida no repositório; hardware em aberto (Anexo C8) | Depois de definida: "Comece com um piloto em poucos veículos." |
| V55 | Piloto | "Instalação acompanhada" | 404 | NÃO VERIFICÁVEL | Não há processo nem hardware definido (`PENDENCIAS.md:210-212`; `contexto.md:38`) | Só depois de definida |
| V56 | Piloto | "calibração com os seus motoristas" | 404 | VERDADEIRA | Calibração automática (`vision/calibration.py:58-92`) | Manter |
| V57 | Piloto | "relatório do período" | 404 | NÃO VERIFICÁVEL | Existe exportação dos alertas em planilha (`backend/routes/alerts.py:92-122`), mas nenhum modelo de relatório de piloto | "exportação dos eventos do período em planilha" |
| V58 | Piloto | "Também atendemos universidades e editais de pesquisa." | 404 | NÃO VERIFICÁVEL | Nenhum atendimento registrado; esse público saiu do foco (`contexto.md:42-43`) | Tirar |
| V59 | Rodapé | "protótipo" | 412 | VERDADEIRA | `contexto.md:37` | Manter |
| V60 | Rodapé | "em piloto" | 412 | FALSA | Igual à V02 | "DriveSafe AI · protótipo em testes" |

**Contagem:** 28 verdadeiras (várias com ressalva), **12 falsas**, **13 exageradas** e **7 não verificáveis**, em 60
afirmações.

---

## Anexo C · Casos investigados a fundo

### C1. "Nenhuma imagem é gravada" e "0 imagens gravadas"
- **Aparelho no veículo:**
  - Não há `imwrite`, `VideoWriter` nem gravação de quadro em `vision/` (busca no repositório).
  - O quadro fica em memória (`vision/driver_monitor.py:169-180`). A detecção de celular copia o quadro, também em
    memória (`vision/phone.py:404-409`).
  - Ficam no aparelho: a fila de eventos, a sirene e, com consentimento, o perfil e a linha de base
    (`README.md:172-177`).
  - **Verdadeiro para o veículo.**
- **Janela de vídeo:**
  - Com tela ligada, o modo "auto" abre uma janela com a imagem da câmera e os pontos. Ela não grava. No Windows e no
    macOS, a janela abre sempre (`run_monitor.py:43-46, 100-104`; `vision/driver_monitor.py:265-267`).
  - Recomendação: `--no-window` como padrão no veículo.
- **Modo teste (só administrador):**
  - Transmite o vídeo ao vivo, com sobreposição, como JPEG em memória a cada 0,1 s, por `/api/test-mode/video.mjpg`
    (`backend/test_session.py:32-34, 259-277`; `backend/routes/test_mode.py:119-124`).
  - Não grava, mas transmite vídeo.
- **Análise de vídeo (só administrador):**
  - O vídeo enviado é gravado em `data/analises/<id>/` (`backend/routes/test_mode.py:136-141`).
  - É apagado no fim da análise, **a menos que** `DRIVESAFE_MANTER_VIDEOS=1` esteja ligado (`backend/config.py:34-35`;
    `backend/test_session.py:411-412`).
  - Se o servidor reiniciar no meio, o `_load` marca a análise como falha e **não apaga o vídeo**
    (`backend/test_session.py:330-332`). Hoje `data/analises/` está vazia.
- **Conclusão:** "Nenhuma imagem é gravada" é verdadeira para o aparelho do veículo. Para dizer "0 imagens" sobre a
  plataforma, é preciso fechar as duas brechas. Texto seguro: "O aparelho do veículo não grava nem envia imagem."

### C2. "O alarme também" (dura 1 segundo?) e como o alarme funciona
- **Som:** 5 ciclos de 2000 Hz e 1000 Hz, 150 ms cada, com 50 ms de pausa, somam **2,0 s** (`vision/alarm.py:18-21, 31-46`).
  O buzzer segue o mesmo padrão (`:112`).
- **Disparo:**
  1. A sonolência marca alarme em todo quadro com o olho fechado há 1 s ou mais (`vision/drowsiness.py:366-368`).
  2. A fusão de risco repassa o alarme (`vision/risk.py:131-132`).
  3. O monitor chama `trigger()` (`vision/driver_monitor.py:178-179`).
  4. O `trigger()` ignora a chamada se a sirene já estiver tocando (`vision/alarm.py:100-107`).

  Resultado: **blocos de 2 s que se repetem enquanto o olho continua fechado**. Quando o olho abre, o bloco atual vai
  até o fim.
- **Outros alarmes:**
  - sonolência de nível 2 (`vision/drowsiness.py:310-311`);
  - celular no ouvido ou olhando o celular, com intervalo mínimo de 30 s (`vision/phone.py:78, 367-369`);
  - subida para risco alto, com intervalo mínimo de 60 s (`vision/risk.py:32, 131`).
- **Falhas possíveis:**
  - `--mute` desliga o som (`vision/alarm.py:60-62`);
  - no Linux sem player de áudio, o sistema só grava um aviso no log e manda `\a` (`:94-98, 120-122`), e num Raspberry
    Pi sem tela isso não faz barulho;
  - o Pi 5 não tem saída P2 (`README.md:277`);
  - som e buzzer não foram testados (`README.md:442-443`);
  - olho não visível não é medido (`vision/engine.py:101`).
- **Latência:** 11 ms por quadro no PC de testes (`README.md:412`). No Raspberry Pi, não medida (`README.md:417`).
- **Conclusão:** lida ao pé da letra, "O alarme também [dura 1 segundo]" é **falsa**. O que o código garante é "o
  alarme dispara quando o olho completa 1 s fechado".

### C3. "6 s: o gestor é avisado no painel imediatamente"
- **No aparelho:**
  - O evento `nao_responsivo`, com risco 5, nasce no quadro em que o fechamento chega a 6 s
    (`vision/drowsiness.py:74, 353-364`).
  - Ele é gravado na fila local (`vision/driver_monitor.py:176-177`; `vision/event_queue.py:61-74`).
  - O aparelho não faz nada diferente aos 6 s: a sirene é a mesma.
- **Envio:**
  - Com sucesso, a thread de sincronização acorda a cada 5 s (`vision/sync.py:59, 80-83`). Ela não é acordada por
    evento novo.
  - Depois de uma falha, espera 10, 20, 40, 80 e 160 s, e depois 300 s (`vision/sync.py:82`), mesmo que o sinal já
    tenha voltado.
- **No servidor:**
  - O evento é gravado e publicado por WebSocket para a empresa (`backend/routes/device_api.py:120-141`). Só vê quem
    está com o painel aberto.
  - Não há notificação push, SMS, e-mail nem ligação em `backend/` nem em `webapp/`. Busca por `PushManager`,
    `showNotification`, `sms` e `twilio`: só o painel antigo usa notificação do navegador
    (`dashboard/static/js/app.js:228`).
- **Conclusão:** **EXAGERADA**. Texto seguro: "O evento mais grave chega ao painel em segundos, com sinal de celular.
  Sem sinal, assim que ele voltar."

### C4. "12 pontos por olho"
- O código usa **6 pontos por olho** para medir a abertura: 2 cantos, 2 em cima e 2 embaixo (`vision/face.py:35-37`).
  A íris soma mais 5 pontos: um anel de 4 e o centro (`:38-42`). O rosto inteiro tem 478 pontos (`:3`).
- A própria prévia desenha 6 pontos, com o comentário "6 pontos por olho, como no Face Landmarker" (`:420, 440`),
  enquanto o card diz 12 (`:359`).
- **FALSA.**

### C5. "Em piloto com transportadoras"
- Não há nenhuma evidência:
  - "Não há frota em piloto documentada" (`contexto.md:37`);
  - validação com gravações: "faltam gravar e anotar" (`PENDENCIAS.md:41`); "faltam as gravações" (`:93`);
  - "números só de piloto com fonte" continua pendente (`:210-212`);
  - Raspberry Pi e limiares com motoristas reais não foram testados (`README.md:440-447`).
- A busca por "piloto" só encontra o site, as pendências e as personas.
- **FALSA**, e no rodapé também (V60).

### C6. Calibração: "os primeiros minutos da viagem calibram"
- **Duração:** no mínimo 5 min e no máximo 10 min com o rosto visível. Termina aos 5 min se contar 100 piscadas
  completas; senão, segue até 10 min (`run_monitor.py:75-78`; `vision/calibration.py:59-62, 89-92`).
- **Durante a calibração:** o microssono já é detectado (`run_monitor.py:181-182`; `README.md:126`). Os níveis de
  sonolência só começam depois do perfil (`vision/drowsiness.py:452-453`).
- **"Descansado" é suposição:**
  - no fim, PERCLOS acima de 10% ou fechamento de 1 s marcam a calibração como suspeita
    (`vision/calibration.py:37-38, 168`);
  - sem perfil anterior, o perfil suspeito é usado mesmo assim (`vision/drowsiness.py:522-523, 534-537`).
- **Limites:** o perfil entre viagens só é guardado com consentimento (`run_monitor.py:157-166`), e o modo YuNet não
  calibra (`vision/face.py:324`).

### C7. Óculos escuros, câmera IR, plataformas, contexto e sem internet
- **Óculos escuros:**
  - A regra compara a luz do olho com a da bochecha e o contraste (`vision/visibility.py:12-18`). Foi conferida em 2
    fotos com óculos pintados (`README.md:153, 434`).
  - Quando detecta, desliga as medidas do olho (`vision/engine.py:101`) e só avisa depois de 10 s
    (`vision/engine.py:36, 212-221`).
  - **Não detecta sono pelos olhos de quem usa óculos escuros com câmera comum.** Com câmera infravermelha, muitos
    óculos deixam ver os olhos (`vision/visibility.py:6`), mas isso não foi testado.
- **Câmera infravermelha:** o código detecta sozinho a imagem sem cor (`vision/pupil.py:31-65`) e aceita a opção
  `--camera-ir` (`run_monitor.py:66-67`). Nunca foi testada (`README.md:442`).
- **Plataformas:**
  - o código prevê Raspberry Pi, Linux, macOS e Windows (`run_monitor.py:1`; `vision/alarm.py:1`);
  - só foi testado no Windows 11 (`README.md:421-423`);
  - Raspberry Pi, macOS e Linux não foram testados (`README.md:441`), e o Pi nunca foi medido (`README.md:417`);
  - no macOS Intel, sem MediaPipe, o sistema cai no YuNet, sem calibração, pose da cabeça e bocejo
    (`vision/face.py:5, 320-324, 411-412`).
- **Madrugada e 5 h 30 min:**
  - madrugada vai de 00:00 a 06:59 (`vision/context.py:22`) e é ignorada se o relógio marcar ano anterior a 2024
    (`:27-28, 70`);
  - o limite é de 5 h 30 min (`:19`);
  - sem telemetria, o tempo ao volante é o tempo com rosto na câmera (`:55`), e só uma pausa inteira de 30 min zera a
    contagem (`:20-21, 60-62`);
  - a madrugada só antecipa sinais leves (5 min em vez de 10), e passar de 5 h 30 min sobe o risco para "atenção" e
    gera evento (`vision/risk.py:77-92`);
  - no transporte de passageiros, o descanso é a cada 4 h (`vision/context.py:3-4`), e o risco não usa isso.
- **Sem internet:** o alarme é local e os eventos esperam na fila (`vision/alarm.py`; `vision/event_queue.py:1`;
  `vision/sync.py:107-111`). **Verdadeiro.**
- **Celular no suporte:** é hipótese (`vision/phone.py:64-67`) e não foi testado (`README.md:446-447`). Olhar para o
  celular no suporte conta como "olhando o celular" (`vision/phone.py:300-302`).

### C8. "Comece com cinco caminhões" e "Instalação acompanhada, calibração com os seus motoristas e relatório do período"
- Nenhuma oferta está definida no repositório. A busca por "piloto", "instalação" e "cinco" só encontra o site, as
  pendências e as personas.
- As personas citam piloto de 5 a 10 veículos, mas como hipótese de mercado (`personas.md:6-8, 32`).
- Hardware e instalação estão em aberto (`contexto.md:38`; `PENDENCIAS.md:210-212`).
- Existe exportação dos alertas em planilha (`backend/routes/alerts.py:92-122`), não um relatório de piloto.
- A calibração é automática (`vision/calibration.py:58-92`): essa parte é verdadeira.
- **Veredito:** "cinco caminhões", "instalação acompanhada" e "relatório do período" são **NÃO VERIFICÁVEIS**. Não
  publicar como oferta até o Matheus definir.

### C9. "Com o consentimento do motorista, conforme a LGPD"
**Fatos do código:**
- A cada quadro, o MediaPipe mede 478 pontos do rosto, a pontuação de piscada e a pose da cabeça
  (`vision/face.py:3, 217-227, 247-266`). Com câmera infravermelha, mede também a razão pupila/íris
  (`vision/pupil.py:1-10`).
- O aparelho aprende o **padrão individual do olho e da piscada** e, com consentimento, guarda esse perfil: abertura
  com o olho aberto e fechado, duração mediana da piscada, frequência, PERCLOS de base, abertura da boca e pose
  (`vision/eyes.py:65-90`; `vision/drowsiness.py:524-525`; `run_monitor.py:155-166`).
- O resumo desse perfil vai ao servidor no evento `calibracao_concluida` (`vision/drowsiness.py:521, 530`;
  `vision/engine.py:223-235`). Lá, fica ligado ao motorista identificado por nome e CNH
  (`backend/routes/device_api.py:120-122`; `backend/routes/people.py:68-69`).
- Os "sinais compatíveis com ativação atípica" o próprio código já trata como dado sensível (`run_monitor.py:28-29`;
  `README.md:164-168`).
- O consentimento de "monitoramento" é registrado, mas **não é checado** antes de aceitar eventos
  (`backend/routes/device_api.py:51-58, 107-144`).

**O que diz a lei e a ANPD** (URLs no Anexo D):
- **LGPD, art. 5º, II:** dado pessoal sensível inclui "dado genético ou biométrico, quando vinculado a uma pessoa
  natural". A ANPD transcreve o inciso no Radar Tecnológico nº 2, p. 16.
- **Definição:** a LGPD não define "dado biométrico". A ANPD descreve a biometria como "a análise técnica, realizada por
  meios matemáticos e estatísticos, das características fisiológicas (tais como impressão digital, face, íris [...]) ou
  comportamentais (voz, expressão facial [...])" e afirma que "os dados biométricos são dados pessoais sensíveis"
  (Radar Tecnológico nº 2, 2024, p. 6).
- **Art. 11, I:** o dado sensível pode ser tratado com consentimento "de forma específica e destacada, para finalidades
  específicas".
- **Art. 11, II:** traz hipóteses sem consentimento, entre elas a proteção da vida ou da incolumidade física do titular
  ou de terceiro (alínea "e").
- **Art. 11, §1º:** vale para qualquer tratamento que "revele dados pessoais sensíveis e que possa causar dano ao
  titular".
- **Art. 5º, XII:** o consentimento precisa ser manifestação "livre, informada e inequívoca". Pode ser revogado a
  qualquer momento (art. 8º, §5º).
- **Deveres:**
  - relatório de impacto, inclusive para dado sensível (art. 38);
  - medidas de segurança (art. 46);
  - direitos do titular (art. 18), com exportação já feita em `backend/routes/people.py:149-170`;
  - revisão de decisão automatizada (art. 20), com revisão humana dos eventos já feita em
    `backend/routes/alerts.py:65-81`.
- **ANPD sobre consentimento:** coleta sem transparência invalida o consentimento do art. 11, I, e sem consentimento o
  controlador precisa de uma hipótese do art. 11, II (Radar, p. 21-22).
- **Caso ViaQuatro:** o TJSP condenou a concessionária do metrô em R$ 500 mil por detectar emoção, gênero e faixa etária
  pelo rosto sem autorização, **sem identificar as pessoas** (Radar, p. 32-33).

> [!warning] Interpretação, confirmar com advogado
> 1. É plausível que as medidas faciais contínuas e o perfil individual de piscadas de um motorista identificado sejam
>    tratados como **dado biométrico** e, portanto, **sensível**, mesmo sem a finalidade de identificar a pessoa. Isso
>    segue a descrição ampla da ANPD. Há leitura contrária: no GDPR (art. 4º, 14), dado biométrico é o que permite ou
>    confirma a identificação única, e a LGPD não traz essa definição.
> 2. Mesmo que não seja biométrico, cansaço, sono e sinais de ativação podem **revelar dado de saúde** (art. 11, §1º).
> 3. Na relação de emprego, o consentimento pode ser questionado por falta de liberdade, por causa da subordinação
>    (art. 5º, XII). A base mais defensável pode ser outra hipótese do art. 11, II, como a proteção da vida e da
>    incolumidade física (alínea "e"), sempre com RIPD, transparência e minimização.
> 4. Com frota de agregados (P4), o contrato precisa definir quem é controlador (a transportadora) e quem é operador (o
>    DriveSafe).

**Conclusão:** "conforme a LGPD" **não é afirmação segura para o site**. Hoje:
- não há parecer nem RIPD (`README.md:168, 457`);
- o sistema não bloqueia eventos sem o consentimento de monitoramento;
- o exemplo de instalação usa HTTP (`deploy/raspberry-pi/device.env.example:4`);
- há dois caminhos de vídeo no servidor de testes (C1).

Texto seguro, só com fatos verificáveis: "O aparelho do veículo não grava nem envia imagem. O motorista registra as
autorizações, com histórico, e pode baixar os próprios dados." Nada de selo de conformidade.

### C10. Jornada: CTB, art. 67-C, e Lei 13.103/2015
- **CTB, art. 67-C (incluído pela Lei 13.103/2015):**
  - o caput proíbe o motorista profissional de dirigir mais de 5 h 30 min ininterruptas em transporte rodoviário
    coletivo de passageiros ou de cargas;
  - §1º: 30 min de descanso a cada 6 h no transporte de cargas, com fracionamento permitido;
  - §1º-A: 30 min a cada 4 h no transporte de passageiros.

  O resumo do próprio código confere com isso (`vision/context.py:3-4`).
- **ADI 5322 (STF, julgamento concluído em 30/06/2023):** derrubou, entre outros pontos, o fracionamento do intervalo
  de 11 h (CLT, art. 235-C, §3º, e CTB, art. 67-C, §3º). **O limite de 5 h 30 min do caput continua valendo**, e o
  fracionamento dos 30 min também (análise da NTC&Logística, Anexo D).
- **O que isso muda no site:**
  - "Mais de 5 h 30 min ao volante pesam no risco" é fiel ao caput.
  - Mas o DriveSafe **não é controle de jornada**: sem telemetria, o tempo é o rosto na câmera
    (`vision/context.py:55`), não soma pausas fracionadas (`:20-21`) e não usa a regra de 4 h dos passageiros (`:19`).
    O site não deve sugerir que ele substitui esse controle, que tem regras próprias na Lei 13.103/2015 e na CLT
    (arts. 235-A a 235-H) (interpretação, confirmar com advogado).
  - A aplicação do art. 67-C a ônibus urbano (P3) é interpretação, confirmar com advogado.

---

## Anexo D · Fontes
> [!note] Sobre as leis
> O site do Planalto recusou a conexão (ECONNRESET) em todas as tentativas desta sessão. Os textos de lei foram
> conferidos por fontes secundárias (ANPD, NTC&Logística) e pelos comentários do código. **Conferir no Planalto antes
> de publicar qualquer referência legal.**

**Leis, decisões e autoridade:**
- LGPD, Lei 13.709/2018 (compilada): https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709compilado.htm
- CTB, Lei 9.503/1997 (compilado), art. 67-C: https://www.planalto.gov.br/ccivil_03/leis/l9503compilado.htm
- Lei 13.103/2015 (lei do motorista): https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2015/lei/l13103.htm
- CDC, Lei 8.078/1990, art. 37 (interpretação, problema 1): https://www.planalto.gov.br/ccivil_03/leis/l8078compilado.htm
- ADI 5322, análise da NTC&Logística: https://www.portalntc.org.br/a-decisao-do-stf-na-adi-5322-e-as-alteracoes-na-lei-do-motorista/
- ANPD, Radar Tecnológico nº 2, Biometria e Reconhecimento Facial (2024), p. 6, 7, 16, 21-22, 32-33:
  https://www.gov.br/anpd/pt-br/centrais-de-conteudo/documentos-tecnicos-orientativos/radar-tecnologico-biometria-anpd-1.pdf
  (notícia: https://www.gov.br/anpd/pt-br/assuntos/noticias/biometria-e-tema-do-segundo-volume-da-serie-radar-tecnologico)
- GDPR, art. 4º, 14 (contraponto): https://eur-lex.europa.eu/eli/reg/2016/679/oj
- Consentimento na relação de emprego (doutrina, fonte secundária): https://www.migalhas.com.br/depeso/348072/o-consentimento-nos-contratos-e-na-relacao-de-emprego-com-a-lgpd

**Ciência e protocolo:**
- Euro NCAP, Safe Driving Driver Engagement Protocol v1.1 (out/2025), §1.3.3 a 1.3.5, p. 16: microssono é fechamento
  de 1 a 2 s, sono é 3 s ou mais, sem resposta é 6 s ou mais.
  https://cdn.euroncap.com/cars/assets/euro_ncap_protocol_safe_driving_driver_engagement_v11_a30e874152.pdf
- Skorucak et al. (2020), *Automatically Detected Microsleep Episodes in the Fitness-to-Drive Assessment*, Frontiers in
  Neuroscience: "microsleep episodes (MSEs) are short fragments of sleep (1–15 s)".
  https://www.frontiersin.org/journals/neuroscience/articles/10.3389/fnins.2020.00008/full

**Técnica:**
- Next.js 16, guia de atualização (`proxy.ts`, `next lint` removido, padrões do `next/image`): https://nextjs.org/docs/app/guides/upgrading/version-16
- `next/image` (`preload`, `priority` depreciada, `formats` AVIF): https://nextjs.org/docs/app/api-reference/components/image
- next-intl, configuração com `src/proxy.ts`: https://next-intl.dev/docs/routing/setup
- next-intl, alternate links e `localePrefix`: https://next-intl.dev/docs/routing/configuration
- Modelo do `create-next-app` com Geist e Geist Mono: https://github.com/vercel/next.js/blob/canary/packages/create-next-app/templates/app-tw/ts/app/layout.tsx
- Google, dados estruturados de produto (exige `offers`, `review` ou `aggregateRating`): https://developers.google.com/search/docs/appearance/structured-data/product-snippet
- Google, dados estruturados de organização: https://developers.google.com/search/docs/appearance/structured-data/organization
- WCAG 2.2, contraste mínimo: https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html
- WCAG 2.2, pausar, parar, ocultar: https://www.w3.org/WAI/WCAG22/Understanding/pause-stop-hide.html
- WAI-ARIA 1.2, papel `generic` (nome proibido): https://www.w3.org/TR/wai-aria-1.2/#generic
- Core Web Vitals (limites de LCP, INP e CLS): https://web.dev/articles/vitals
- Registro npm, consultado em 11/09/2026 com `npm view <pacote> dist-tags` e `peerDependencies` (Anexo A8).

**Nome "DriveSafe" já usado na mesma categoria:**
- Embitel, DriveSafe (detecção de sonolência e distração): https://www.embitel.com/iot-insights/driver-distraction-detection-app-powered-by-machine-learning
- App "Drive Safe" (Google Play), monitoramento dos olhos com alarme: https://play.google.com/store/apps/details?id=io.github.chayanforyou.drivesafe
