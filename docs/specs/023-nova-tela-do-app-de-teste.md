# Spec 023 · Nova tela do RotaGuard Teste (completa e bonita)

| Campo | Valor |
|---|---|
| Status | implementada em 19/10/2026 (`tests/test_tela_teste.py` 31, `tests/test_app_teste.py` 18; pacote PyInstaller com teste de fumaça; capturas em `docs/app-teste/capturas-2026-10-19/`); não verificado com webcam real em Linux nem o instalador .exe (sem Inno Setup) |
| PRD | RF-27, RF-16, RF-17, RF-18, RNF-15 |
| Pedido | "eu ainda não tenho o raspberry pi e etc então é necessário que deixe o script mais completo e bonito possível assim como o painel"; "quero que na face tenha bolinhas para captação de tudo" (19/10/2026) |
| Substitui | spec 010, decisão 2 (tela de início em Tkinter e janela do OpenCV com texto sem acento) |
| Specs irmãs | 010 (pacote e download), 018 (painel reconhece o script aberto), 022 (cardio e pontos) |
| Código | `caixa/app_teste.py`, `caixa/tela_teste/` (servidor local + `web/`), `caixa/run_monitor.py`, `caixa/vision/driver_monitor.py`, `implantacao/app-teste/` |
| Testes | `tests/test_tela_teste.py` (TEL-01 a TEL-16), `tests/test_app_teste.py` (continua passando) |

## Contexto

Hoje o RotaGuard Teste abre uma janela Tkinter simples e depois uma janela do OpenCV com o texto em fonte Hershey (sem
acento) por cima da imagem. Funciona, mas não mostra metade do que o script mede e não serve para apresentar.

## Decisões

1. **Uma janela só, em HTML**, aberta pelo pywebview (WebView2 no Windows, o mesmo do painel). Sem pywebview (Linux sem
   as bibliotecas), abre no navegador padrão. A janela do OpenCV continua existindo com `--janela-opencv` e na caixa.
2. **Servidor local só em `127.0.0.1`**, porta livre escolhida na hora e um token aleatório por sessão em todas as
   rotas (nenhum outro programa ou aparelho da rede lê a câmera):
   - `GET /` e arquivos de `web/` (HTML, CSS e JS sem build e sem nada da internet: funciona offline);
   - `GET /video.mjpg` com o quadro **já com a malha desenhada pelo Python** (pontos e imagem sincronizados);
   - `GET /estado` JSON com tudo que o motor mede no último quadro;
   - `POST /acao` (`iniciar`, `parar`, `recalibrar`, `malha`, `som`, `opcoes`) com o token e conferência de `Origin`.
3. **O monitoramento roda numa thread** do mesmo processo (`run_monitor` dividido em montar e rodar). O anúncio
   `em_execucao.json` da spec 018 continua sendo gravado, para o painel instalado reconhecer o teste.
4. **Malha ("bolinhas")** desenhada com antisserrilhado: os 478 pontos pequenos; olhos, íris e boca em destaque;
   ROIs do pulso (testa e bochechas) com contorno; caixa do celular e mãos quando detectados. Modos: `completa`,
   `pontos`, `essencial` (só olhos, boca e ROIs) e `desligada`. Tecla M alterna.
5. **Tela de início:** câmera (automática por padrão, lista das encontradas e vídeo gravado), opções (celular, som,
   calibração rápida, câmera infravermelha, cardio), privacidade e termos em seção (sem aceite obrigatório, spec 010
   decisão 13), pasta de dados e "apagar dados".
6. **Tela do teste** (escura, o vídeo é o centro):
   - vídeo grande com a malha, faixa de calibração e o nível de risco em destaque;
   - cartões: **Olhos** (abertura, fechado há, PERCLOS 60 s, piscadas por minuto, duração média), **Cabeça**
     (inclinação, giro, cabeceios), **Boca** (bocejos), **Coração** (bpm grande, onda ao vivo, confiança, respiração,
     tendência, variabilidade experimental), **Celular e mãos** (estado, tempo, olhos esfregados, mão no rosto),
     **Atenção** (direção do olhar), **Desempenho** (quadros por segundo e latência);
   - linha do tempo dos eventos da sessão, com hora e tipo;
   - atalhos: Q ou Esc encerra, C recalibra, M malha, S som, F tela cheia.
7. **Resumo ao encerrar:** duração, eventos por tipo, PERCLOS médio, piscadas por minuto, frequência cardíaca média,
   mínima e máxima, e botão para salvar o resumo em JSON e CSV na pasta de dados.
8. **Visual:** paleta do RotaGuard (verde `#103e31`, lima `#d5f669`, papel `#fafcf7`), fonte do sistema, números
   tabulares, movimento curto e respeito a `prefers-reduced-motion`. Sem gradiente roxo, sem emoji, sem cara de IA.
   Textos em português com acento.
9. **Privacidade:** nada sai do computador; o cardio aparece com "estimativa pela câmera, não é medida médica".

## Critérios de aceite

| ID | Critério |
|---|---|
| TEL-01 | O servidor só escuta em `127.0.0.1` |
| TEL-02 | Rota sem token ou com token errado responde 403 |
| TEL-03 | `POST /acao` com `Origin` de outro endereço responde 403 |
| TEL-04 | `/estado` antes de iniciar responde `{"fase": "inicio", ...}` com a lista de câmeras |
| TEL-05 | Com um vídeo de teste (quadros sintéticos), `iniciar` leva a fase a `rodando` e `/estado` traz risco, olhos, cabeça, cardio e desempenho |
| TEL-06 | `/video.mjpg` entrega quadros JPEG válidos (`multipart/x-mixed-replace`) |
| TEL-07 | `parar` encerra a thread, libera a câmera e leva a fase a `resumo` com o resumo da sessão |
| TEL-08 | O resumo soma os eventos por tipo e calcula média, mínimo e máximo do bpm só com leituras `pronto` |
| TEL-09 | Salvar o resumo grava JSON e CSV na pasta de dados e nada fora dela |
| TEL-10 | Desenho da malha: nos modos `completa`, `pontos` e `essencial` altera pixels do quadro; em `desligada` não altera |
| TEL-11 | Desenhar a malha custa menos de 4 ms por quadro 640×480 nesta máquina |
| TEL-12 | `em_execucao.json` é gravado ao iniciar e apagado ao parar (spec 018 continua valendo) |
| TEL-13 | Sem câmera: a fase vira `erro` com a mensagem de câmera ocupada ou ausente, sem fechar o app |
| TEL-14 | Os arquivos de `web/` não citam nenhum endereço `http(s)://` externo (funciona offline) |
| TEL-15 | `app_teste.py` sem argumentos abre a tela nova; `--monitor` e os argumentos antigos continuam funcionando |
| TEL-16 | O pacote do PyInstaller leva `tela_teste/web` e roda o teste de fumaça do `build.py` |

## Fora de escopo

- Gravar vídeo no app de teste.
- Enviar qualquer dado para a VPS.
