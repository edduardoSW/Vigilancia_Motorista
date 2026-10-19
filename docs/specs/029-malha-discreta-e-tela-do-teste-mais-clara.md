# Spec 029 · Malha discreta, trechos com o rosto limpo e tela do teste mais clara

| Campo | Valor |
|---|---|
| Status | aprovada (pedido do Matheus em 19/10/2026) → em implementação |
| PRD | RF-17, RF-18, RF-65 |
| Pedido | "esta muito bom porem o script nessa parte da face esta algo muito feio esses quadrados e etc visualmente não ficou muito legal e dificulta realmente ver a face e o olho da pessoa pela camera então em investigação isso pode ser ruim, além disso no script no resumo final e naquela parte que mostra as coisas no script estão muito confusas não estão muito faceis de identificar o que é cada coisa mas eu gostei bastante" (19/10/2026, com captura da tela) |
| Muda | spec 023 (decisão 4: malha) e spec 026 (decisão 5: "o vídeo vai com a malha desenhada") |
| Código | `caixa/vision/driver_monitor.py` (desenho da malha), `caixa/vision/trechos.py`, `caixa/tela_teste/*`, `painel/app/src/components/live/camera-malha.ts` e `camera-cores.ts` (mesmo estilo na câmera do painel) |
| Testes | `tests/test_tela_teste.py`, `tests/test_trechos.py`, `painel/app/scripts/testes/camera-*.test.mjs` (MAL-01 a MAL-08, TEL-17 a TEL-24) |

## O que está ruim (captura do Matheus)

- Testa e bochechas com **polígonos preenchidos** em amarelo: tampam a pele.
- Olhos com **contorno grosso e círculo na íris**: tampam o olho, que é o que mais importa ver.
- Lábios com contorno grosso e linha no meio da boca.
- Os 478 pontos ajudam a mostrar a tecnologia, mas no conjunto a imagem fica poluída.
- Na tela do teste e no resumo final, os números aparecem sem dizer com clareza o que são, se estão bons ou ruins e
  comparados a quê.

## Decisões

1. **O rosto e os olhos nunca ficam cobertos.** Nada preenchido sobre a pele. Nada desenhado dentro do olho (sem
   círculo na íris, sem contorno sobre a pálpebra). Marcas dos olhos ficam **fora** do olho: dois cantos finos (como
   colchetes) nos cantos externos, ou um traço fino abaixo da pálpebra inferior.
2. **Novo modo padrão "Discreta":** pontos dos 478 com raio 1 e opacidade baixa (≈ 25%), só nas bordas do rosto e
   espaçados (subconjunto), contorno do rosto fino e tracejado, regiões do pulso só como **cantos** finos (sem
   preenchimento e sem contorno inteiro), boca com traço fino só no contorno externo. Lima só nas marcas que estão
   medindo; o resto em branco translúcido.
3. **Modos:** Discreta (padrão), Completa (a malha inteira, ainda sem preencher nada e sem cobrir o olho), Só o rosto
   (desligada, nada desenhado). O modo "Pontos" e "Essencial" saem (confundiam).
4. **Trechos gravados vão com o rosto limpo:** sem malha. Só uma faixa fina no **rodapé, fora do rosto**, com hora,
   tipo do alerta e "RotaGuard". Para investigação, a imagem é a prova; a malha fica só na tela ao vivo.
5. **Tela do teste reorganizada por pergunta**, em linguagem simples, cada medida com: nome claro, valor, unidade,
   **situação** (Normal, Atenção, Alto) e uma linha visível de "o que é" (não só no "?"):
   - topo: uma frase grande com o estado agora ("Tudo normal", "Olhos fechando devagar", "Celular na mão há 4 s");
   - **Sono:** olho aberto agora (%), tempo de olho fechado nos últimos 3 min (%), piscadas por minuto, duração da
     piscada, cada uma comparada com a calibração da própria pessoa ("acima do seu normal");
   - **Atenção na estrada:** para onde olha, tempo fora da estrada, celular, mãos no rosto;
   - **Cabeça e boca:** bocejos, cabeceios;
   - **Coração (estimativa):** bpm, confiança;
   - nomes técnicos (PERCLOS, EAR, KSS) só em letra pequena ao lado, nunca como título.
6. **Resumo final em formato de relatório**:
   - frase-resumo no topo ("Teste de 12 min: 2 alertas de sono e 1 de celular" ou "Nenhum alerta em 12 min");
   - linha do tempo da sessão com os alertas marcados;
   - lista de alertas com hora, o que foi, quanto durou e o vídeo (se houver);
   - tabela "Como a pessoa estava" com as médias, cada uma com a explicação em uma frase e a faixa normal;
   - detalhes técnicos (fps, latência, calibração, sinais avançados) recolhidos no fim.
7. **Mesmo estilo de malha na câmera do painel** (spec 025), para o produto ser coerente.

## Critérios de aceite

| ID | Critério |
|---|---|
| MAL-01 | Em todos os modos, nenhum pixel dentro do polígono de cada olho (pontos da pálpebra) é alterado pelo desenho |
| MAL-02 | Em nenhum modo há preenchimento: a fração de pixels alterados dentro das regiões do pulso é < 3% |
| MAL-03 | Modo Discreta altera < 1,5% dos pixels do rosto (caixa do rosto) num quadro 640×480; Completa < 6% |
| MAL-04 | Modo "Só o rosto" não altera nenhum pixel |
| MAL-05 | Trecho gravado: nenhum pixel alterado dentro da caixa do rosto em relação ao quadro original; a faixa com hora e tipo fica só no rodapé |
| MAL-06 | Desenho em < 3 ms por quadro 640×480 (melhor de 5 rodadas) |
| MAL-07 | Câmera do painel: mesmas regras MAL-01 a MAL-04 no canvas (teste com pontos sintéticos) |
| MAL-08 | Os modos antigos "Pontos" e "Essencial" não aparecem mais na tela nem no `/acao` |
| TEL-17 | Toda medida mostrada tem nome em português simples, valor com unidade, situação e uma frase de "o que é" visível |
| TEL-18 | O topo mostra uma frase de estado atual, nunca só um número |
| TEL-19 | PERCLOS, EAR e KSS não aparecem como título de cartão (só como nota técnica pequena) |
| TEL-20 | Medidas comparadas com a calibração dizem "seu normal: X" quando há calibração |
| TEL-21 | Resumo começa com uma frase-resumo que conta alertas por tipo e duração do teste |
| TEL-22 | Resumo tem lista de alertas com hora, duração e botão do vídeo quando houver trecho |
| TEL-23 | Detalhes técnicos do resumo ficam recolhidos por padrão |
| TEL-24 | Capturas novas da tela e do resumo em `docs/app-teste/capturas-2026-10-19-v2/`, conferidas |
