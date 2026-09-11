# Contexto para avaliar o site do RotaGuard

Base comum dos 5 avaliadores. Escrito em 11/09/2026 e atualizado no mesmo dia, depois da primeira rodada. O resultado
dessa rodada está em `docs/site/avaliacoes/2026-09-11-previa-v2/00-consolidado.md`.

- **Nome do produto:** **RotaGuard** (antes DriveSafe AI), decidido pelo Matheus em 11/09. Falta conferir no INPI.
- **No código:** os identificadores ainda usam `DRIVESAFE_*` (`README.md`, início).

## O que o Matheus pediu (palavras dele)

- "O site que foi feito está totalmente ridículo." Tem que ser **divulgação de um produto para empresas de logística e
  de transporte de pessoas**, com **imagens relacionadas a isso**.
- "O site está muito genérico, totalmente genérico, com fontes genéricas, layout genérico, tudo que eu literalmente não
  quero. Nenhum site que eu fiz tem esse genérico."
- "No prompt de imagens, faça algo pensado." Também quer ideias de uso do **Magnific** (imagens, animação, vídeo).
- Avaliação criteriosa, com **personas**, por **5 agentes** em frentes diferentes.

## Histórico que não pode se repetir

- **App "Cabine noturna" rejeitado (10/09):** "muito feio, cara de IA, paleta de cores horrenda, efeitos
  desnecessários, sem cara de algo profissional e sério".
- **Prévia v1 do site rejeitada (10/09):** "horrível, totalmente genérico", "você só colocou texto". Virou o erro 75 do
  vault: aplicar o feedback de uma peça em outra e enfraquecer o conceito até sobrar um template. Os prints estão em
  `docs/site/avaliacoes/2026-09-11-previa-v2/prints-avaliados/v1/`.
- **Prévia v2 do site (10/09, noite):**
  - era `site-drivesafe/previa/v2/index.html`, que saiu do branch porque o Matheus não quer site em HTML; continua no
    histórico do git, no commit `9e8ad60`;
  - os prints estão em `docs/site/avaliacoes/2026-09-11-previa-v2/prints-avaliados/v2/`;
  - o Matheus a chamou de ridícula e genérica, e as 5 frentes deram média de 2,6/10 em 11/09.
- **Regra do vault antes de qualquer site:** rodada de referências com URL e **2 ou 3 direções que mudem a estrutura**
  (não só paleta e fonte), mostradas para escolher antes de codar.
  - **Exceção pedida pelo Matheus em 11/09:** o site é feito direto em Next.js + Tailwind, sem rodada de prévias.
  - A direção C "Escalas" da frente 2 (mundo → Brasil → rodovia → cabine → frota) é o ponto de partida, escolhida pelo
    Claude. O Matheus pode trocar.

## O produto (fatos do código, não marketing)

As linhas marcadas como **decisão** ou **hipótese do Matheus** registram o que ele disse em 11/09 e deixam claro o que
ainda não existe no código.

| Item | Fato | Onde conferir |
|---|---|---|
| O que é | Câmera voltada para o motorista mais um computador pequeno no veículo (Raspberry Pi ou PC), com alarme sonoro local e envio dos eventos para um painel da empresa | `caixa/run_monitor.py`, `caixa/vision/` |
| Sonolência | Olhos fechados por 1 s (microssono), 3 s (sono) e 6 s (sem resposta); PERCLOS; piscadas mais longas que a calibração do próprio motorista; bocejos; cabeceio; olhos esfregados como sinal leve | `caixa/vision/drowsiness.py`, `caixa/vision/risk.py`, `caixa/vision/face_touch.py` |
| Celular | Na mão, no ouvido ou olhando para ele por mais de 2 s; celular parado no suporte não conta | `caixa/vision/phone.py` |
| Contexto | Madrugada e direção contínua acima de 5 h 30 min (CTB, art. 67-C) pesam no risco | `caixa/vision/context.py`, `caixa/vision/risk.py` |
| Outros sinais | "Sinais compatíveis com ativação atípica" (pupila só com câmera infravermelha, piscadas, olhar). **Não é diagnóstico nem exame de drogas** | `caixa/vision/activation.py`, `caixa/vision/pupil.py` |
| Privacidade (código de hoje) | O vídeo é processado no aparelho e nenhuma imagem é gravada; saem métricas, eventos e o estado ao vivo a cada 15 s. Os consentimentos do motorista são registrados com histórico, mas o recebimento de eventos não confere o consentimento de monitoramento (frente 5, C9). **Muda com os clipes curtos decididos em 11/09 (linha "Função definida em 11/09")** | `caixa/vision/driver_monitor.py`, `servidor/backend/routes/people.py`, `servidor/backend/routes/device_api.py` |
| Conexão | Funciona sem internet; eventos ficam numa fila e são enviados depois | `caixa/vision/event_queue.py`, `caixa/vision/sync.py` |
| Painel da empresa | Frota ao vivo, revisão de eventos (confirmar, alarme falso, orientado), página do motorista, relatórios CSV; várias empresas na plataforma; sem cadastro aberto (a equipe cria os logins) | `servidor/backend/`, `painel/webapp/` |
| Situação real | Protótipo com testes automatizados. **Não há frota em piloto documentada nem números de redução de acidentes.** Limiares iniciais, ainda a validar com gravações reais | `PENDENCIAS.md` |
| Função definida em 11/09 (**decisão do Matheus; não existe no código**) | Palavras dele: "nem toda hora deve ser gravada, apenas as partes que o sensor detecta algo muito recorrente, tipo sonolência frequente durante muito tempo e algum tipo de uso de anfetamina, e o principal analisado e mais importante deve ser a log, que seria o registro. A empresa, quando o motorista chegar, deve recolher o equipamento e, ao conectar, o sistema deve reconhecer o equipamento e gerar o relatório. A funcionalidade dele vai ser basicamente essa; quanto às gravações, devem ser curtas." **Consequências:** há clipes curtos, então "nenhuma imagem é gravada" passa a ser falso para o produto; o fluxo principal é registro na caixa → recolhimento na chegada → relatório ao conectar; o envio ao vivo vira secundário. **Hoje o código não grava imagem e envia os eventos pela rede** | `README.md` ("Como funciona" e "Privacidade"); consolidado, seções 5 e 6.2 |
| Hardware (**decisão provável do Matheus, 11/09**) | Caixa com Raspberry Pi e câmera acoplada. Primeiro, "provavelmente o 3". Sobre o Pi 3, depois disse "eu não sei" e pediu opinião. O provável passou a ser o **Raspberry Pi 4 de 4 GB**, que funciona como dispositivo pela USB-C (a caixa ligada por cabo é reconhecida) e tem codificador H.264 no chip para os clipes. **No código:** o Raspberry Pi é previsto (sistema de 64 bits), mas nunca foi testado nem medido; as medições são de um PC com Windows | `README.md` (seções "Raspberry Pi", "Desempenho medido" e "O que foi testado e o que falta"); consolidado, seção 6.1 |
| Pupila (**decisão do Matheus, 11/09**) | Primeiro: "leitura de pupila antes, durante e depois da rota". Depois: se vier, será no celular do motorista. **No código:** a pupila existe só na caixa, durante a viagem e só com câmera infravermelha. Foi conferida só em imagens sintéticas, nunca com câmera infravermelha real. Não existe medição no celular nem antes ou depois da rota | `caixa/vision/pupil.py`, `caixa/vision/activation.py`, `README.md` |
| Pulseira de frequência cardíaca (**hipótese do Matheus, 11/09**) | "Provavelmente iremos usar pulseiras que medem o pulso (frequência cardíaca) para identificar a questão do uso de drogas." Depois, ficou para muito depois. **Não existe no código**: aparece só como opção de melhoria nas pendências. Frequência cardíaca, sozinha, não identifica droga | `PENDENCIAS.md` (decisão da etapa 2) |
| App instalável (**decisão do Matheus, 11/09**) | Painel mais modo de teste com a câmera do próprio aparelho. Instaladores nativos para Windows, macOS, Linux e Android, gerados com Tauri 2 no GitHub Actions, e PWA no iPhone. Download no site para quem entra com o PIN. **No código:** ainda não; hoje existe o `painel/webapp/` (PWA) | `painel/webapp/`; consolidado, seção 5 |
| Em aberto | Hardware final: medidas, alimentação de 12 ou 24 V para 5 V/3 A com desligamento seguro, instalação, câmera infravermelha de 850 ou 940 nm e medição no Pi 4. Regras dos clipes: o que dispara, duração, criptografia, quem assiste e por quanto tempo ficam. Integridade e hora do registro | `PENDENCIAS.md`; consolidado, seção 7 |

## Restrições do site

- **Público principal:** **transportadoras de carga e operadores logísticos** e **empresas de transporte de
  passageiros** (fretamento, rodoviário, urbano). Universidades e investidores deixaram de ser o foco.
- **Contato:** **só por celular ou WhatsApp**, sem cadastro nem formulário de conta. O link "Já é cliente? Entrar" leva à
  área de download do app com PIN (decisão de 11/09).
- **Idiomas e stack:** português e inglês. **Stack definida pelo Matheus: Next.js + Tailwind CSS + next-intl**, com o
  site em `site/`, para ele mesmo modificar.
  - As prévias em HTML saíram do branch e não servem de base de código.
  - Versões conferidas no registro na hora. A prova é build + lint (regras e armadilhas em `stack-padrao.md` e nos erros
    30 e 52 a 55 do vault).
- **Nenhuma afirmação sem fonte ou sem base no código**, por exemplo "reduz 90% dos acidentes" ou "em piloto com X".
  - Também não: "nenhuma imagem é gravada", porque haverá clipes curtos.
  - Também não: "detecta drogas" ou "uso de anfetamina", porque o código só fala em sinais compatíveis com ativação
    atípica, sem diagnóstico.
  - Função decidida e ainda não feita só entra no site quando existir.

## Arquivos que os avaliadores devem abrir

- **Site atual:** o projeto Next em `site/`. Rodar `npm run dev`, ou `npm run build && npm run start`, e tirar prints em
  1440 px e 400 px.
- **Rodada anterior:** `docs/site/avaliacoes/2026-09-11-previa-v2/` (relatórios `01` a `05`, `00-consolidado.md`,
  `referencias.md` e `prints-avaliados/`).
- **Prévias em HTML (só histórico):** `git show 9e8ad60:site-drivesafe/previa/v2/index.html` e
  `git show 9e8ad60:site-drivesafe/previa/index.html`.
- **Roteiro de mídia:** `docs/site/midia/` (`README.md` como índice, `00-regras-gerais.md`, `01-fundos.md`,
  `02-fotos.md`, `03-banners.md` e `04-videos.md`).
- **Personas:** `docs/site/personas.md`.
- **Vault do Matheus (padrões e sites dele):**
  - `C:\Users\Matheus Corte\Desktop\Obsidian\90 - Projetos\Padroes\` (`meu-estilo-de-sites.md`, `diferenciacao-visual.md`,
    `awwwards-estudo.md`, `referencias-de-design.md`, `erros-que-a-ia-comete.md`);
  - `...\90 - Projetos\Projetos Analisados\site-*.md` e `...\90 - Projetos\site-saojorge.md`.
