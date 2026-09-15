# Spec 019 · Painel mais claro: lista e cards, janelas no centro, modo escuro, termo importado e vídeos do momento

| Campo | Valor |
|---|---|
| Status | implementada em 15/09/2026 (tela, núcleo Python, testes e roteiro de conferência com capturas em `docs/painel/capturas-2026-09-15-parte-2/`); falta usar pela ponte do Python dentro do pacote com a janela visível; as perguntas do fim continuam abertas |
| PRD | RF-40 a RF-49 (painel) e, entrados no PRD em 15/09/2026 por esta spec: RF-51 (lista e cards), RF-52 (modo escuro), RF-53 (termo importado como comprovante), RF-54 (motorista e vídeos no relatório) |
| Pedido | "o dashboard eu ainda achei que ficou um pouco confuso porém eu gostei muito, mas ainda não parece muito intuitivo; além disso onde tem lista quero que tenha tanto lista e card para melhor identificação; os modais devem abrir centralizado na tela com um blur no fundo do resto da tela; deve ter a opção de importar o termo do motorista para dentro do sistema para comprovar; quero modo escuro também; e na viagem não tem nada que indica quem foi o motorista de forma clara e não tem os campos dos vídeos capturados no momento" (15/09/2026) |
| Specs irmãs | 012 (viagem), 014 (menu e permissões), 015 (motoristas e termo), 016 (aparência e cópia), 017 (Início) |
| Código | `painel/app/` (telas) e `painel/desktop/` (preferências, termos e cópia) |

## O que deixava o painel confuso (visto nas capturas de 15/09)

1. Abrir um motorista ou um veículo já mostrava o formulário editável com "Salvar": não havia "ver" antes de "editar".
2. Cada cadastro abria de um jeito: veículo novo numa janela central; veículo existente, motorista e pessoa num painel
   lateral.
3. O Início empilhava cinco blocos do mesmo peso (Primeiros passos, caixa conectada, viagens, avisos, teste), e o que
   fazer primeiro não se destacava.
4. A caixa conectada aparecia duas vezes (cartão grande no menu e bloco no Início), com um "Abrir viagem" desligado.
5. No relatório da viagem, o motorista era uma palavra numa linha cinza, e quase todo momento dizia "Sem vídeo" sem
   explicar por quê.

## Decisões

1. **Janelas no centro.** Cadastrar, ver, editar, caixa, pessoa, momento e busca rápida abrem no centro da tela, com o
   resto da janela desfocado e escurecido. Cabeçalho com título e "Fechar", corpo que rola por dentro e rodapé sempre
   visível. Esc e clique fora fecham, e o foco volta para onde estava. O painel lateral deixa de existir.
2. **Ver antes de editar.** Abrir um motorista, um veículo ou uma pessoa mostra os dados em seções curtas; "Editar"
   troca para o formulário na mesma janela. "Cadastrar" abre direto o formulário.
3. **Lista e cards.**
   - Telas: Viagens, Momentos da viagem, Motoristas, Veículos, Caixas e Equipe, com o botão "Lista | Cards" ao lado da
     busca.
   - Card: nome grande, a identificação (placa, matrícula, caixa), a situação em frase e no máximo três informações.
     Mesmos itens, ordem e filtro da lista.
   - Padrão: cards. A escolha fica guardada por pessoa e por tela, pela ponte (nada no navegador, ENT-07).
   - O registro de atividades continua só em lista, porque é um histórico.
4. **Modo escuro.**
   - Tema "Claro", "Escuro" ou "Igual ao Windows", escolhido por pessoa. O botão fica no pé do menu para todas as
     funções; "Aparência", em Configurações, mostra o mesmo tema.
   - Cores próprias do escuro, nunca a inversão automática, com contraste conferido por teste.
   - Antes de alguém entrar, vale o último tema usado neste computador. Padrão: claro.
5. **Termo importado como comprovante.**
   - Na janela do motorista, "Importar termo assinado": arquivo PDF, PNG ou JPEG de até 10 MB, a data da assinatura
     (não pode ser futura) e a versão do termo.
   - O arquivo fica na pasta de dados do painel (`termos/`), com SHA-256 no banco, e entra na cópia de segurança.
   - Nunca é apagado: trocar o arquivo cria registro novo, e o histórico mostra todos, com quem importou e quando.
   - "Ver termo" mostra a foto dentro do painel e abre o PDF no leitor do computador. Arquivo mexido fora do painel é
     detectado e avisado.
   - Só administrador e supervisor importam e veem. Importar e abrir vão para o registro de atividades.
   - Termo registrado antes, sem arquivo, continua valendo e aparece como "sem o arquivo do termo" (pergunta 2).
6. **Motorista claro na viagem.**
   - O relatório começa com dois blocos lado a lado, **Veículo** e **Motorista**.
   - Motorista: nome completo, matrícula, CNH (categoria e validade), termo (com ou sem arquivo) e "Ver cadastro".
   - Na lista e nos cards de Viagens, o motorista aparece junto do veículo.
7. **Vídeos do momento.**
   - Todo momento tem o campo **Vídeo**, na lista e no card.
   - Clicar no momento abre a janela do momento com o vídeo e, para cada trecho gravado, os campos Início, Fim, Duração,
     Câmera, Caixa, Coletado em, Fica guardado até e Situação (disponível, trancado sem termo, apagado pelo prazo).
     Depois vêm o que a caixa registrou naquele momento e os botões de decisão.
   - Momento sem vídeo diz por quê (primeiro sinal de sono não é gravado; aviso de tempo de direção não tem câmera).
   - Enquanto a leitura da caixa não existe, os vídeos são fictícios: quadro escuro sem imagem, com os campos reais.
8. **Início mais direto.**
   - No topo, **O que fazer agora** em cards (momentos para verificar, CNH vencendo, caixa com problema, cópia
     atrasada), cada um com um botão.
   - Primeiros passos viram uma barra com o próximo passo; a lista completa abre por "Ver todos".
   - A caixa conectada sai do menu (fica uma linha curta, "Caixa conectada · 64%") e aparece só no Início.

## Contrato da ponte (acréscimos; os dois lados iguais)

```ts
type Tema = "claro" | "escuro" | "sistema";
type Visao = "lista" | "cards";
type TelaComVisao = "viagens" | "momentos" | "motoristas" | "veiculos" | "caixas" | "equipe";
interface Preferencias { tema: Tema; visao: Record<TelaComVisao, Visao> } // padrão: tema "claro", todas "cards"
interface Estado { /* ...campos atuais... */ tema: Tema; preferencias: Preferencias | null; videos_dias: number }
// tema: o da pessoa que entrou; sem sessão, o último salvo neste computador (padrão "claro").
// videos_dias: guarda.videos_dias das configurações (para "fica guardado até").
interface ArquivoTermo { nome: string; tipo: "pdf" | "imagem"; bytes: number; importado_em: string; importado_por: string }
interface Motorista { /* ... */ termo: { assinado: boolean; data: string | null; versao: string | null; arquivo: ArquivoTermo | null } }
interface TermoRegistro { id: number; assinado: boolean; data: string | null; versao: string | null;
  registrado_por: string | null; registrado_em: string; arquivo: ArquivoTermo | null }
```

| Método | Quem pode | Devolve |
|---|---|---|
| `preferencias_salvar(valores: { tema?, visao?: Partial<Record<TelaComVisao, Visao>> })` | qualquer sessão | `Preferencias` (por pessoa; o `tema` também vira o último usado neste computador) |
| `termo_importar(motorista_id, arquivo: { nome, conteudo_base64 }, dados: { data, versao? })` | administrador e supervisor | `Motorista` (registro novo de termo assinado, com o arquivo) |
| `termo_ver(motorista_id)` | administrador e supervisor | imagem: `{ tipo: "imagem", nome, conteudo: "data:image/...;base64,..." }`; PDF: abre no leitor do computador e devolve `{ tipo: "pdf", nome, aberto: true }` |
| `motorista_termos(motorista_id)` | administrador e supervisor | `TermoRegistro[]`, mais novo primeiro |

Erros: arquivo que não é PDF, PNG ou JPEG, maior que 10 MB ou com data futura → `invalido` com `campo` (`arquivo`,
`data`); motorista sem termo com arquivo em `termo_ver` → `nao_encontrado`; arquivo alterado fora do painel →
`conflito` ("O arquivo do termo foi alterado fora do painel").

## Comportamento

- **Janelas**
  - Dado Motoristas aberto, quando a pessoa clica num motorista, então abre no centro a janela com os dados e o botão
    "Editar", com o fundo desfocado.
- **Lista e cards**
  - Dado Motoristas em cards, quando a pessoa escolhe "Lista", então a tabela aparece com os mesmos motoristas, e ao
    abrir o painel de novo continua em lista.
- **Tema**
  - Dado o tema claro, quando a pessoa escolhe "Escuro" no pé do menu, então todas as telas trocam na hora, e a tela de
    entrar também abre escura na próxima vez.
- **Termo**
  - Dado Marcos Teixeira sem termo, quando o supervisor importa `termo-marcos.pdf` com a data de hoje, então o termo
    aparece assinado com o arquivo, o registro ganha "importou termo assinado" e os vídeos dele deixam de ficar
    trancados.
  - Dado um arquivo `.exe` renomeado para `.pdf`, então aparece "Use um PDF ou uma foto (PNG ou JPEG) do termo
    assinado" e nada é gravado.
- **Viagem**
  - Dado o relatório do Ônibus 2240, então o bloco Motorista mostra "Carlos Menezes", a matrícula 0412, a CNH e o termo.
  - Quando a pessoa abre o momento "Sono repetido", então a janela mostra os dois trechos gravados com início, fim,
    duração, câmera, caixa, coleta, prazo e situação.

## Critérios de aceite

| ID | Critério | Teste |
|---|---|---|
| MOD-01 | Nenhum painel lateral: cadastrar, ver, editar, caixa, pessoa, momento e busca abrem no centro com o fundo desfocado; Esc e clique fora fecham | `painel/app/scripts/testes/shell.test.mjs` e `scripts/conferir-telas.mjs` |
| MOD-02 | A janela aberta fica no centro da janela do app (não presa na tela) e rola por dentro, com o rodapé visível | `conferir-telas.mjs` |
| INT-01 | Abrir motorista, veículo ou pessoa mostra os dados antes do formulário; "Editar" troca na mesma janela | `conferir-telas.mjs` |
| INT-02 | Início começa por "O que fazer agora", com um botão em cada card; a caixa conectada não ocupa o menu | `conferir-telas.mjs` |
| VIS-01 | Viagens, Momentos, Motoristas, Veículos, Caixas e Equipe têm Lista e Cards com os mesmos itens, ordem e filtro | `shell.test.mjs` e `conferir-telas.mjs` |
| VIS-02 | A escolha de visão e o tema ficam guardados por pessoa, pela ponte | `tests/test_painel_preferencias.py` |
| PRF-01 | `preferencias_salvar` aceita só os valores do contrato, vale para qualquer função e não aparece para outra pessoa | idem |
| ESC-01 | Tema claro, escuro ou igual ao Windows, por pessoa; sem sessão, o último usado neste computador | idem e `shell.test.mjs` |
| ESC-02 | Nenhuma cor fixa nas telas fora dos tokens do `globals.css`; texto e texto secundário com contraste de 4,5:1 ou mais sobre o fundo e a superfície, nos dois temas | `shell.test.mjs` |
| ESC-03 | Telas principais conferidas em captura no tema escuro | `conferir-telas.mjs` |
| TER-01 | Importar aceita só PDF, PNG ou JPEG (conferidos pelos primeiros bytes) até 10 MB, com data não futura; o resto é recusado com frase simples e nada é gravado | `tests/test_painel_termos.py` |
| TER-02 | Arquivo guardado em `termos/` com SHA-256; conteúdo alterado fora do painel é detectado ao abrir | idem |
| TER-03 | Nada é apagado: trocar cria registro novo; o histórico mostra quem importou e quando | idem |
| TER-04 | Só administrador e supervisor importam, veem e listam; Consulta recebe `sem_permissao` | idem |
| TER-05 | Importar e abrir vão para o registro de atividades | idem |
| TER-06 | A cópia de segurança leva os arquivos dos termos | idem |
| TER-07 | O banco da versão anterior sobe para o esquema novo sem perder dados | idem |
| VIA-01 | O relatório mostra Veículo e Motorista em destaque (nome completo, matrícula, CNH e termo) | `conferir-telas.mjs` |
| VID-01 | Todo momento tem o campo Vídeo; com vídeo, a janela mostra Início, Fim, Duração, Câmera, Caixa, Coletado em, Fica guardado até e Situação; sem vídeo, diz o motivo | `shell.test.mjs` e `conferir-telas.mjs` |
| VID-02 | "Fica guardado até" = coleta + prazo das configurações; vídeo de motorista sem termo aparece trancado | `shell.test.mjs` |

## Fora de escopo agora

- Vídeo de verdade dentro do painel (depende da leitura da caixa, spec 004).
- Assinar o termo dentro do app, ler o texto do termo (OCR) e modelo do termo para imprimir.
- Tema por computador em vez de por pessoa.

## Perguntas para o Matheus

1. **Todo momento deve ter vídeo?** Em 11/09 ficou "a caixa grava só trechos curtos quando detecta algo muito
   recorrente". A prévia mostra vídeo em sono repetido e em uso de celular, e diz por que os outros momentos não têm.
2. **Sem o arquivo do termo, os vídeos daquele motorista ficam trancados?** Hoje basta o termo registrado.
3. **O modelo do termo para imprimir entra agora?**

## Riscos

- **Arquivo do termo é dado pessoal** (assinatura e nome): fica na pasta do usuário do Windows e vai cifrado na cópia de
  segurança, mas no disco é o arquivo como veio.
- **10 MB pela ponte** (em base64) podem levar alguns segundos no computador da garagem.
- **Desfoque do fundo** pesa em computador fraco: se pesar, a janela escurece sem desfocar.
