# PRD · RotaGuard

| Campo | Valor |
|---|---|
| Produto | RotaGuard (nome anterior: DriveSafe AI) |
| Dono das decisões | Matheus Cortes |
| Repositório | `edduardoSW/Vigilancia_Motorista`, branch `app-instalavel-em-andamento` |
| Versão deste PRD | 1.0, 11/09/2026 |
| Método | SDD: este PRD → specs em `docs/specs/` → TDD (regra global 2b) |

> [!note] Como ler
> `RF-xx` = requisito funcional; `RNF-xx` = não funcional. **Existe** = já está no código e testado; **Parcial** = existe
> com lacuna; **Novo** = a fazer. Hipóteses ficam marcadas e só viram fato com medição ou decisão do Matheus.

## 1. Problema

- Frotas de carga e de passageiros rodam de madrugada. A jornada já é controlada por lei (Lei 13.103/2015; CTB,
  art. 67-C), mas a **fadiga e o celular ao volante continuam** e ninguém da empresa vê o que acontece na cabine.
- As videotelemetrias do mercado **gravam a viagem inteira**. Isso gera atrito com motoristas e sindicato, horas de
  revisão manual de vídeo e mais dado pessoal guardado.
- Quando algo acontece, a empresa precisa de um **registro confiável da viagem**, e não de horas de vídeo.

## 2. Para quem

| Quem | Papel | Detalhe |
|---|---|---|
| Gestor(a) de segurança e frota (P1), dono de fretamento (P2), CCO urbano (P3), financeiro (P4) | Compra e lê o relatório | `docs/site/personas.md` |
| Motorista (P5) | Usa, autoriza e vê os próprios dados | Não pode ser tratado como suspeito |
| Técnico RotaGuard | Instala, pareia a caixa e cadastra | Acesso de equipe |
| Equipe RotaGuard (admin) | Cria empresas e logins | Sem cadastro aberto |

## 3. O que o produto é

1. **A caixa** no veículo: Raspberry Pi com câmera voltada para o motorista.
   - Detecta sinais de sono e uso de celular e toca um **alarme sonoro** na hora, sem depender de internet.
   - Escreve o **registro da viagem** (log), que é a peça principal do produto.
   - Grava **trechos curtos de vídeo só quando um sinal se repete muito**: sonolência frequente por muito tempo, ou sinais
     compatíveis com uso de estimulante. Nunca grava a viagem inteira.
2. **A coleta**: quando o motorista chega, a empresa recolhe a caixa e a conecta. O sistema **reconhece o equipamento**,
   importa o registro e os trechos e **gera o relatório da viagem**.
3. **O app instalável**, com painel da empresa e do motorista (relatórios, revisão, autorizações) e um modo de teste
   que usa a câmera do próprio aparelho com as mesmas regras da caixa.
   - Distribuição: instaladores para Windows, Linux e Android; PWA no iPhone. Sem Mac (14/09/2026). Windows no
     futuro pela Microsoft Store (pacote MSIX).
4. **O site** de divulgação. Quem entra com o PIN vê as opções de download do app.

## 4. Objetivos e métricas de sucesso

| ID | Objetivo | Métrica | Situação |
|---|---|---|---|
| O1 | Motorista avisado na hora | Alarme em até 1,5 s depois de 1 s de olhos fechados, medido na caixa | Hipótese: medir no Pi 4 |
| O2 | Registro completo e íntegro | 100% dos eventos da viagem no relatório; qualquer alteração ou remoção no registro é detectada | Novo |
| O3 | Relatório rápido | Relatório pronto em até 2 min depois de conectar a caixa, numa viagem de 12 h | Hipótese |
| O4 | Poucos alarmes falsos | Meta definida com as gravações da etapa de validação | Aberto |
| O5 | Pouca imagem guardada | Nenhum vídeo fora dos gatilhos de recorrência; cada trecho com no máximo 20 s; trechos criptografados na caixa | Novo |
| O6 | Site que converte | Cliques em WhatsApp por segmento e por página | Novo |

## 5. Fora de escopo agora

- **Diagnóstico** de droga, álcool ou doença. O produto aponta "sinais compatíveis com ativação atípica", nunca
  "uso de droga".
- **Pulseira de frequência cardíaca** e **leitura de pupila no celular do motorista**: ficam "para muito depois",
  segundo o Matheus em 11/09/2026.
- Localização e GPS; mapa de eventos por posição.
- Vídeo ao vivo e gravação contínua.
- Saída de faixa (ADAS) e colisão.
- Substituir o controle legal de jornada.
- App nativo de iPhone (fica o PWA até existir conta de desenvolvedor Apple).
- Versão para Mac: "deixe download apenas para Windows e Linux, pois não terá para Mac" (14/09/2026).

## 6. Requisitos funcionais

### 6.1 Caixa

| ID | Requisito | Situação | Spec |
|---|---|---|---|
| RF-01 | Sonolência: olhos fechados por 1 s (microssono), 3 s (sono) e 6 s (sem resposta); PERCLOS; piscadas mais longas que a calibração individual; bocejo; cabeceio; olhos esfregados como sinal leve | Existe (`caixa/vision/drowsiness.py`, `face_touch.py`) | 009 |
| RF-02 | Celular na mão, no ouvido ou olhando por mais de 2 s; no suporte não conta como na mão | Existe, com limiares a validar (`caixa/vision/phone.py`); mão vazia na orelha corrigida em 14/09 (CEL-01), falta calibrar com gravações | 009 |
| RF-03 | Contexto: madrugada (00:00 a 06:59); direção contínua acima de 5 h 30; descanso por tipo de veículo (carga: 30 min a cada 6 h; passageiros: 30 min a cada 4 h) | Parcial: falta a regra de passageiros (`caixa/vision/context.py`) | 006 |
| RF-04 | Alarme sonoro local sem internet, com autoteste de saída de som ao ligar e aviso claro se não houver som | Parcial (`caixa/vision/alarm.py`) | 005 |
| RF-05 | Sinais compatíveis com ativação atípica (piscadas, olhar; pupila só com câmera infravermelha), sempre como "não é diagnóstico" | Existe (`caixa/vision/activation.py`) | 002 |
| RF-06 | **Registro da viagem**: só acrescenta; encadeado por hash; início e fim de viagem, calibração, cada evento, resumo a cada minuto, estado do aparelho e referência de cada trecho gravado; sobrevive a corte de energia | Novo | 001 |
| RF-07 | **Trechos curtos por recorrência**: buffer circular em memória; grava N s antes e M s depois quando um critério de recorrência dispara; limite por viagem e intervalo mínimo entre trechos; criptografado; fora dos gatilhos, nada é gravado | Novo | 002 |
| RF-08 | **Identidade da caixa**: ID único e chave própria, pareada com uma empresa | Parcial: hoje é um token de dispositivo no servidor | 003 |
| RF-09 | **Coleta ao conectar**: a caixa oferece o registro e os trechos a quem estiver autorizado, por rede (cabo USB-C do Pi 4 como rede ou rede do escritório) ou por exportação num pen drive; manifesto assinado; marca a viagem como coletada e só apaga depois da confirmação do app | Novo | 003 |
| RF-10 | **Perfil Raspberry Pi 4 (4 GB)**: resolução, taxa de quadros e intervalos de detecção ajustados; janela de vídeo desligada; desligamento seguro; temperatura no registro | Novo | 005 |
| RF-11 | Envio ao vivo para o servidor continua **opcional** e desligado por padrão | Existe (`caixa/vision/sync.py`) | 006 |
| RF-12 | Sem consentimento de monitoramento registrado, a caixa não registra dado identificado do motorista, e o servidor recusa eventos | Novo: hoje o servidor não confere (`servidor/backend/routes/device_api.py`) | 006 |

### 6.2 App instalável

| ID | Requisito | Situação | Spec |
|---|---|---|---|
| RF-20 | Reconhecer a caixa conectada (descoberta automática), confirmar que é da empresa e importar registro e trechos, verificando a integridade | Novo | 004 |
| RF-21 | Relatório da viagem: linha do tempo, contagem por tipo, episódios recorrentes com trecho, direção contínua e madrugada, saúde da caixa e integridade do registro; exportar PDF e CSV | Novo | 004 |
| RF-22 | Revisão de eventos e trechos (confirmado, alarme falso, motorista orientado), com quem revisou e quando | Existe no servidor (`servidor/backend/routes/alerts.py`) | 004 |
| RF-23 | Área do motorista: os próprios dados, autorizações e exportação | Existe (`painel/webapp`) | 007 |
| RF-24 | Modo de teste com a câmera do aparelho, com as mesmas regras de detecção da caixa | Novo | 007 |
| RF-25 | Instaladores para Windows, Linux e Android gerados no GitHub Actions (Tauri 2) e PWA no iPhone; sem Mac; Windows no futuro pela Microsoft Store (MSIX) | Novo | 007 |
| RF-26 | Logins criados só pela equipe; modo local de demonstração com PIN e dados fictícios | Existe | 007 |
| RF-27 | **App de teste do script**: o script da caixa empacotado para Windows e Linux, baixado na área do PIN do site, que roda a detecção e o alarme com a câmera do computador, sem servidor e sem instalar Python; com seção de privacidade, LGPD e termos, sem aceite obrigatório | Novo (14/09/2026) | 010 |

### 6.3 Site

| ID | Requisito | Situação | Spec |
|---|---|---|---|
| RF-30 | Site Next.js + Tailwind + next-intl em português, inglês, espanhol, francês e chinês, com seletor de idioma em dropdown com bandeira e nome do país | Em construção (`site/`) | 008 |
| RF-31 | Contato só por WhatsApp e telefone, com mensagem pronta por segmento; nenhum formulário de cadastro | Novo | 008 |
| RF-32 | "Já é cliente? Entrar": PIN conferido no servidor → página de download do app por plataforma | Novo | 008 |
| RF-33 | Nenhuma afirmação sem fonte ou sem base no código | Regra | 008 |
| RF-34 | Estradas e mapa-múndi com dado real (Natural Earth, IBGE, DNIT); nunca pino de veículo ou evento | Em construção | 008 |

## 7. Requisitos não funcionais

| ID | Requisito | Situação |
|---|---|---|
| RNF-01 | Latência do alarme de até 1,5 s no Pi 4 | Hipótese: medir |
| RNF-02 | Rosto medido a pelo menos 10 quadros por segundo no Pi 4; mãos e celular cerca de 4 vezes por segundo | Hipótese: medir |
| RNF-03 | Integridade: cada linha do registro leva o hash da anterior; fechamento assinado com a chave da caixa (HMAC-SHA256); o importador aponta a primeira linha adulterada ou faltando | Novo |
| RNF-04 | Energia: gravação só por acréscimo com `fsync`; após corte, a viagem é retomada ou fechada como "interrompida" sem perder o que já foi escrito | Novo |
| RNF-05 | Privacidade: trechos criptografados com AES-GCM; chave por caixa; retenção configurável; só perfis autorizados veem trechos; auditoria de acesso; RIPD e base legal com advogado | Novo (parecer pendente) |
| RNF-06 | Segurança da coleta: sem porta aberta sem autenticação; pareamento caixa-empresa; nada trafega sem autenticação e integridade | Novo |
| RNF-07 | Disco: teto para trechos (por exemplo, 2 GB) com rotação que nunca apaga trecho ainda não coletado sem registrar | Novo |
| RNF-08 | Calor: temperatura da CPU registrada; aviso no registro se houver estrangulamento térmico | Novo |
| RNF-09 | Site: contraste AA, `prefers-reduced-motion`, LCP de até 2,5 s | Em construção |
| RNF-10 | Licenças: nada AGPL no produto (o `yolov8n.pt` fica só em `ferramentas/`); MediaPipe Apache-2.0 | Existe |
| RNF-11 | Qualidade: toda regra com teste automatizado; prova com testes, build e lint | Regra |

## 8. Restrições

- Trabalho no branch `app-instalavel-em-andamento`, nunca na `main`.
- **Hardware recomendado: Raspberry Pi 4 com 4 GB.** O Matheus pediu opinião e não tinha certeza do Pi 3.
  - **Processamento:** CPU Cortex-A72 cerca de 3 vezes mais rápida que a Cortex-A53 do Pi 3, e 4 vezes a memória.
  - **Cabo USB:** a porta USB-C funciona como dispositivo (modo gadget), então a caixa pode ser ligada por cabo no
    computador. O Pi 3 não tem esse modo.
  - **Vídeo:** codificador H.264 no chip, útil para os trechos. O Pi 5 não tem.

  > [!note] Hipótese, confirmar
  > Taxa de quadros e latência reais só com a placa em mãos.
- Fonte veicular de 5 V e 3 A a partir de 12 ou 24 V, com desligamento seguro.
- Sem GPS; operação no Brasil; LGPD.
- Stack do site: Next.js 16.3.4, React 19.3.0, Tailwind 4.3.3, next-intl 4.14.4, TypeScript 6.0.3 (travado: o
  typescript-eslint aceita só `<6.1`), ESLint 9.39.5 (travado: `eslint-plugin-react` do `eslint-config-next`).

## 9. Riscos

| Risco | Impacto | Resposta |
|---|---|---|
| Vídeo do rosto é dado pessoal e possivelmente biométrico ou de saúde (LGPD, art. 5º, II, e art. 11) | Alto | Trechos curtos só por recorrência, criptografia, retenção curta, acesso restrito, RIPD e parecer jurídico antes de piloto com motoristas reais |
| "Anfetamina" virar promessa | Alto (jurídico e reputação) | Texto sempre "sinais compatíveis com ativação atípica, não é diagnóstico"; exame toxicológico continua sendo o da Lei 13.103 |
| Registro contestado como prova | Alto | Hash encadeado, assinatura da caixa, relógio registrado e verificação no importador |
| Alarme falso (sol, óculos, para-e-anda) | Médio | Validação com gravações (etapa 2) antes de ampliar |
| Pi 4 lento ou quente na cabine | Médio | Perfil Pi 4, medição, dissipação, registro de temperatura |
| Corte de energia corrompe o cartão | Médio | Gravação só por acréscimo, `fsync`, desligamento seguro, cartão de alta resistência |
| Nome "RotaGuard" já registrado | Médio | Conferir no INPI |

## 10. Perguntas abertas (decisão do Matheus)

Cada spec usa o valor padrão abaixo até ele decidir.

| # | Pergunta | Padrão usado até a decisão |
|---|---|---|
| Q1 | O que é "muito recorrente" para gravar? | Sonolência: 3 ou mais eventos de microssono em 30 min, **ou** 15 min seguidos em nível de sonolência. Ativação atípica: sinais persistentes por 10 min acima da linha de base do motorista |
| Q2 | Duração do trecho | 10 s antes + 10 s depois (20 s); no máximo 12 trechos por viagem; intervalo mínimo de 10 min entre trechos do mesmo tipo |
| Q3 | Como a caixa é conectada na chegada? | Implementar rede (USB-C do Pi 4 ou rede do escritório) **e** exportação para pen drive |
| Q4 | Por quanto tempo os trechos ficam guardados depois da coleta, e quem pode vê-los? | 30 dias; só gestor e admin da empresa; motorista vê os próprios |
| Q5 | Tipo de veículo por caixa (carga ou passageiros) | Configurado no pareamento; padrão "carga" |
| Q6 | Número de WhatsApp, oferta de piloto e preço | Sem valor inventado: o site mostra "a configurar" |

## 11. Histórico de decisões (11/09/2026)

- Nome do projeto: **RotaGuard**.
- Site em **Next.js + Tailwind**, nunca HTML estático. O Matheus modifica essa versão. Idiomas: pt, en, es, fr, zh,
  com bandeira e país no dropdown.
- Pastas reorganizadas: `caixa/`, `servidor/`, `painel/`, `site/`, `ferramentas/`, `implantacao/`, `tests/`, `docs/`.
- Hardware: "uma caixa com um Raspberry dentro, provavelmente o 3, com uma câmera acoplada". Depois: "caso seja
  necessário ou seria melhor usar um Raspberry Pi 4 de 4 GB, pode dar a opinião" → recomendado Pi 4 4 GB (seção 8).
- Funcionamento: "nem toda hora deve ser gravada, apenas as partes que o sensor detecta algo muito recorrente, tipo
  sonolência frequente durante muito tempo e algum tipo de uso de anfetamina, e o principal analisado e mais importante
  deve ser a log, que seria o registro. A empresa, quando o motorista chegar, deve recolher o equipamento e, ao
  conectar, o sistema deve reconhecer o equipamento e gerar o relatório. […] As gravações devem ser curtas."
- Pupila no celular do motorista e pulseira cardíaca: "isso é para muito depois".
- App: "Painel + teste de câmera"; "Instaladores + PWA".
- Método: SDD, PRD, specs, TDD e hooks de guardrail (regra global).

### 14/09/2026

- Site "Boa chegada" pronto para revisão ("o site já está pronto").
- Prioridade: "quero que faça a questão de download agora para eu poder testar em outros computadores; a parte do
  dashboard da empresa e a conexão com esse script faça depois" → RF-27 e spec 010. O painel (spec 007) e a conexão
  com o script vêm depois.
- **Teste do app no computador:**
  - "quando eu selecionei uma câmera e abri o app fechou, isso não tem lógica"; "a câmera deve ser reconhecida
    automaticamente" → câmera automática, aviso claro sem câmera e X da janela encerrando o teste (spec 010, APT-13 a
    APT-18).
  - "o celular no ouvido ainda não está 100 por cento funcional, pois quando eu coloco a mão no ouvido reconhece como
    celular ainda" → spec 009 (CEL-01).
  - "seria legal reconhecer bocejo e um pouco mais das olheiras e expressões próximas do olho, pois pode ser um
    indicativo também; se a pessoa movimenta muito a cabeça etc., tudo isso ajuda" → spec 011 (rascunho).
- **Download e nome:**
  - "coloque o download desse RotaGuard Teste dentro do site da RotaGuard" → arquivos servidos pelo site em
    `/downloads` (spec 010, decisão 11).
  - "como propriedade coloque RotaGuard, não quero que deixe o nome do meu desktop" → propriedades RotaGuard no
    executável e registro sem o nome do computador (spec 010, decisão 10).
- **Plataformas:** "futuramente irei fazer esse Microsoft Store (pacote MSIX); deixe download apenas para Windows e
  Linux, pois não terá para Mac" → sem macOS nos downloads (app de teste e instaladores do painel); Windows pela
  Microsoft Store no futuro.
- **Privacidade:** "coloque política de privacidade, LGPD e os termos dentro do script RotaGuard para ficar dentro da
  lei, porém não quero ter que aprovar nada para que comece a usar; apenas deixe lá em uma seção" → seção no app de
  teste, sem aceite obrigatório (spec 010, decisão 13). Os textos precisam de revisão de advogado antes de clientes.

## 12. Specs

| Spec | Cobre |
|---|---|
| `docs/specs/001-registro-da-viagem.md` | RF-06, RNF-03, RNF-04 |
| `docs/specs/002-trechos-por-recorrencia.md` | RF-05, RF-07, RNF-05, RNF-07 |
| `docs/specs/003-identidade-e-coleta.md` | RF-08, RF-09, RNF-06 |
| `docs/specs/004-importacao-e-relatorio.md` | RF-20, RF-21, RF-22 |
| `docs/specs/005-perfil-raspberry-pi-4.md` | RF-04, RF-10, RNF-01, RNF-02, RNF-08 |
| `docs/specs/006-contexto-consentimento-envio.md` | RF-03, RF-11, RF-12 |
| `docs/specs/007-app-instalavel.md` | RF-23 a RF-26 |
| `docs/specs/008-site.md` | RF-30 a RF-34, RNF-09 |
| `docs/specs/009-pendencias-da-deteccao.md` | RF-01, RF-02 (pendências da etapa 1 que dão para fechar sem gravação) |
| `docs/specs/010-app-de-teste-do-script.md` | RF-27 (download do script empacotado para testar em outros computadores) |
| `docs/specs/011-sinais-complementares-de-fadiga.md` | RF-13 a RF-15 propostos (bocejo visível, sinais ao redor dos olhos, movimento da cabeça); rascunho de 14/09/2026 |
