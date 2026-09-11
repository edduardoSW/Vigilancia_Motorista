---
name: avaliar-site-5-frentes
description: Avaliação criteriosa de um site ou prévia de site por 5 agentes em paralelo, cada um numa frente (mensagem e personas, direção de arte anti-genérico, imagens e prompts, estrutura e conversão, técnica e veracidade), com nota por critério, evidência e correções. Usar quando pedirem "avaliar o site", "avaliação com personas", "5 agentes" ou antes de aprovar uma nova versão do site do DriveSafe.
---

# Avaliar site em 5 frentes

Criada em 11/09/2026 para o site do DriveSafe, a pedido do Matheus ("avaliação criteriosa com personas e 5 agentes
para avaliar várias frentes, igual uma skill do Claude"). Serve para qualquer versão nova do site.

## Antes de começar

1. Garantir que existem e estão atualizados:
   - `docs/site/contexto.md` (pedido, histórico, fatos do produto, restrições);
   - `docs/site/personas.md` (P1 a P5).
2. Descobrir o que será avaliado:
   - o site avaliado agora é o projeto Next.js em `site/`: rodar `npm run dev` (ou `npm run build && npm run start`)
     e abrir a rota a avaliar;
   - prints em 1440 px e 400 px, tirados com o Chrome ou o Edge sem janela;
   - o roteiro de mídia em `docs/site/midia/` (`README.md` como índice, `00-regras-gerais.md`, `01-fundos.md`,
     `02-fotos.md`, `03-banners.md` e `04-videos.md`).
3. Criar a pasta da rodada: `docs/site/avaliacoes/<AAAA-MM-DD>-<versao>/`, com os prints em `prints-avaliados/`.

## Rodar os 5 avaliadores em paralelo

Uma mensagem com 5 chamadas de agente (tipo `general-purpose`), em segundo plano. Cada prompt leva:

- o caminho de `contexto.md`, `personas.md` e dos arquivos avaliados;
- a frente, os critérios e o formato abaixo;
- o arquivo de saída `docs/site/avaliacoes/<rodada>/0N-<frente>.md`;
- as regras: **só ler e escrever o próprio relatório** (não mexer no site), português do Brasil, toda crítica com
  evidência (`arquivo:linha`, trecho do print ou fonte com URL), nada de conselho genérico.

### Escala de notas (0 a 10)

| Faixa | Significado |
|---|---|
| 0–3 | Inaceitável: atrapalha a venda ou arrisca a marca |
| 4–5 | Fraco: existe, mas não convence |
| 6–7 | Aceitável: funciona, sem diferencial |
| 8–9 | Bom: convence a persona e tem identidade |
| 10 | Referência do mercado |

### Frente 1 · Mensagem, posicionamento e personas

- **Critérios:**
  - entende-se em 5 s o que é e para quem;
  - dores de cada persona;
  - cobertura de **carga e de passageiros**;
  - prova e credibilidade;
  - objeções (alarme falso, custo, LGPD, motorista);
  - chamada adequada a venda B2B (piloto, celular/WhatsApp);
  - tom sério, pt-BR natural, sem jargão;
  - diferença frente à videotelemetria que grava vídeo.
- **Método:** simular a leitura de cada persona (P1 a P5): o que ela entendeu em 5 s, o que a convenceu, o que a faz
  fechar a aba e a nota dela.
- Pesquisar como 3 concorrentes se posicionam (com URL), para achar o espaço do DriveSafe, sem copiar.

### Frente 2 · Direção de arte, tipografia, layout e identidade (anti-genérico)

- **Critérios:**
  - estrutura (é o esqueleto padrão de landing?);
  - tipografia (escolha com motivo e hierarquia);
  - cor e contraste (sóbrio e profissional, adequado ao setor);
  - composição e ritmo;
  - presença do mundo real (cabine, frota, garagem, gente);
  - componentes que denunciam template;
  - coerência com os sites que o Matheus já fez;
  - seriedade para transporte sem clichê.
- **Leitura obrigatória:** `meu-estilo-de-sites.md`, `diferenciacao-visual.md`, `awwwards-estudo.md`, o erro 75 de
  `erros-que-a-ia-comete.md` e pelo menos 4 notas `site-*.md` do Matheus, para dizer em concreto o que os sites dele
  fazem que este não faz.
- **Entregar:**
  - a lista de "sinais de template", com evidência;
  - **3 direções estruturais** (descrição, não código) que quebrem o esqueleto padrão.

### Frente 3 · Imagens, vídeo e prompts (com ideias para o Magnific)

- **Critérios:**
  - adequação ao objetivo de divulgação para logística e passageiros;
  - cobertura de cenas por seção e por persona (caminhão, carreta, ônibus rodoviário e urbano, van, gestor/CCO,
    motorista, instalação do aparelho, garagem, noite e dia);
  - realismo e contexto brasileiro;
  - sinais de imagem de IA a evitar;
  - consistência como série fotográfica;
  - uso no layout (espaço para texto, recortes para celular e computador, proporções);
  - cuidados legais e éticos (marcas, placas, rostos, não estigmatizar o motorista);
  - produção (modelo, consistência, ampliação) e vídeo ou animação.
- **Entregar:**
  - diagnóstico dos arquivos de `docs/site/midia/`;
  - lista de cenas necessárias por seção;
  - regras para o novo prompt;
  - ideias concretas de uso do Magnific.
- **Não gerar** imagem nem vídeo (gasta crédito). Pode só listar modelos disponíveis.

### Frente 4 · Estrutura, navegação e conversão B2B

- **Critérios:**
  - jornada e ordem das seções frente às perguntas das personas;
  - escaneabilidade;
  - caminhos para os dois segmentos (carga e passageiros);
  - demonstração de como funciona (cabine → alarme → gestor);
  - provas;
  - chamadas (pedir piloto, WhatsApp, "Já é cliente? Entrar");
  - celular (print de 400 px);
  - conteúdo de apoio à decisão (modelo de cobrança, instalação, perguntas e objeções, LGPD, especificações);
  - microcopy;
  - como medir a conversão.
- **Entregar:**
  - mapa do site proposto;
  - roteiro seção a seção, com o objetivo de cada uma e a persona que ela atende.

### Frente 5 · Técnica, acessibilidade, SEO, idiomas e veracidade

- **Critérios:**
  - acessibilidade (contraste WCAG AA, tamanho de fonte, foco, semântica, movimento reduzido);
  - desempenho (fontes externas, animação contínua, imagens futuras, LCP);
  - SEO (título, descrição, Open Graph, dados estruturados, hierarquia de títulos, `hreflang`);
  - prontidão para PT/EN;
  - alinhamento com a stack aprovada (Next.js + next-intl, versões do vault);
  - **veracidade**.
- **Veracidade:**
  - listar **cada afirmação do site** e marcar verdadeira, falsa ou não verificável, conferindo no código do
    repositório (`caixa/vision/`, `servidor/backend/`) e em fonte legal com URL (LGPD, CTB art. 67-C, Lei 13.103/2015);
  - propor o texto corrigido de cada uma.

### Formato de cada relatório

```markdown
# Frente N · <nome>
Avaliador: agente N · <data> · versão avaliada: <arquivo>

## Nota geral: X/10
<uma frase que resume por quê>

## Notas por critério
| Critério | Nota | Por quê | Evidência |

## Leitura por persona
<obrigatório nas frentes 1 e 4; nas outras, quando fizer diferença>

## Problemas, do mais grave ao menos grave
| # | Gravidade (crítica/alta/média/baixa) | Problema | Evidência | Impacto | Correção concreta |

## O que manter

## Recomendações para a próxima versão (em ordem de prioridade)

## Perguntas que só o Matheus responde
```

Ao terminar, o agente devolve só: a nota geral, os 5 problemas mais graves e o caminho do relatório.

## Consolidar

1. Ler os 5 relatórios.
2. Escrever `docs/site/avaliacoes/<rodada>/00-consolidado.md` com:
   - quadro de notas (frentes × critérios);
   - notas por persona;
   - problemas repetidos entre frentes (são os mais confiáveis);
   - conflitos entre avaliadores e como decidir;
   - decisões que dependem do Matheus;
   - o plano da próxima versão.
3. Atualizar os arquivos de `docs/site/midia/` com o que a frente 3 apontou.
4. Registrar no vault: a nota do projeto no Obsidian e, se aparecer erro novo da IA, o `erros-que-a-ia-comete.md`.
5. Antes de codar a próxima versão: rodada de referências com URL e 2 ou 3 direções que mudem a estrutura, mostradas
   ao Matheus para escolher.
