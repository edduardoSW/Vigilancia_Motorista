# Spec 015 · Cadastro de motoristas, veículos e caixas

| Campo | Valor |
|---|---|
| Status | aprovada em 14/09/2026 ("gostei, pode fazer", com o pedido de menos cara de IA e mais movimento); em construção |
| PRD | RF-44 (motoristas), RF-45 (veículos), RF-46 (caixas), RF-12 (termo de ciência), RNF-05 (privacidade) |
| Pedido | "registro de veículos e motoristas" (14/09/2026) |
| Specs irmãs | 014 (quem pode cadastrar), 016 (guarda dos dados), 003 (caixas pareadas e arquivo da empresa), 004 (importação) |
| Código | `painel/app/` (telas) e `painel/desktop/` (banco local e regras) |

## Contexto

- **O que existe:**
  - o servidor tem motoristas, veículos e dispositivos (`servidor/backend/database.py:91-162`);
  - o painel tem só a lista "Veículos e caixas" com dados fictícios.
- **Por que o cadastro importa:**
  - o relatório precisa dizer **quem dirigiu** e **qual veículo**;
  - a regra de descanso depende do tipo de transporte (carga ou passageiros, RF-03);
  - o vídeo do rosto é dado pessoal e só pode aparecer com o termo de ciência registrado (RF-12).

## Decisões

1. **Motorista:**

   | Campo | Obrigatório | Observação |
   |---|---|---|
   | Nome completo | sim | |
   | Nome nos relatórios | sim | Sugerido a partir do nome ("Carlos Menezes" → "Carlos M."), editável |
   | Matrícula | sim | Única na empresa |
   | CNH: número, categoria e validade | sim | Número com 11 dígitos e dígito verificador; categorias C, D ou E |
   | Telefone | não | |
   | CPF | não | Pergunta 1; se informado, confere o dígito verificador e fica mascarado na lista |
   | Situação | sim | Ativo, afastado ou desligado |
   | Termo de ciência do monitoramento | sim | Assinado em (data) e versão do termo; ou "ainda não assinou" |
   | Observações | não | Texto curto |

   - **Sem foto do motorista:** foto de rosto é dado biométrico em potencial e não é necessária para o relatório.
   - O termo tem um modelo para imprimir, gerado pelo painel com o nome da empresa (texto revisado por advogado antes de
     clientes, como na spec 010).
2. **Termo ainda não assinado:**
   - a viagem chega e o relatório abre;
   - os **vídeos curtos ficam trancados** até o termo ser registrado, com o aviso "Falta registrar o termo de ciência
     deste motorista";
   - mudar o termo gera linha no registro de atividades (spec 014) e nunca apaga o histórico: revogar é registro novo,
     como no servidor (`database.py:234-250`).
3. **CNH:**
   - aviso no Início e na lista 30 dias antes de vencer;
   - vencida aparece como "CNH vencida em 10/09/2026";
   - **não impede** importar a viagem: o painel registra, e a empresa decide.
4. **Veículo:**

   | Campo | Obrigatório | Observação |
   |---|---|---|
   | Número do veículo (prefixo) | sim | Único na empresa. É o nome usado em todo o painel ("Ônibus 2240") |
   | Placa | sim | Formato Mercosul (`ABC1D23`) ou antigo (`ABC-1234`) |
   | Tipo | sim | Ônibus, micro-ônibus, caminhão ou van |
   | Transporta | sim | Passageiros ou carga. Define a regra de descanso (RF-03) |
   | Marca e modelo, ano | não | |
   | Caixa instalada | não | Escolhida entre as caixas da empresa sem veículo |
   | Situação | sim | Em uso, na oficina ou fora de uso |

5. **Caixa:**
   - **O painel não cria caixa.** As caixas vêm do arquivo da empresa (spec 003): número (`RG-0139`), geração e
     situação.
   - O painel vincula a caixa a um veículo, troca de veículo e mostra:
     - última coleta;
     - versão do programa;
     - maior temperatura na última viagem;
     - espaço livre;
     - "precisa de atenção" com o motivo em frase simples.
   - Trocar a caixa de veículo guarda o histórico: viagens antigas continuam com o veículo em que a caixa estava.
   - Caixa revogada (roubada ou perdida) aparece como "Caixa bloqueada pela RotaGuard" e não importa viagem.
6. **Quem dirigiu a viagem:**
   - na importação, o painel sugere o último motorista daquele veículo e pede confirmação: "Quem dirigiu?";
   - dá para trocar depois, com linha no registro de atividades;
   - revezamento com dois motoristas fica como pergunta (2).
7. **Planilha:**
   - "Importar planilha" aceita CSV de motoristas e de veículos, com modelo para baixar;
   - antes de gravar, mostra o que vai entrar, o que tem erro (linha e motivo) e o que já existe;
   - nada é gravado se a pessoa não confirmar.
8. **Ninguém é apagado:**
   - motorista desligado e veículo fora de uso saem das listas do dia a dia, mas continuam nas viagens antigas;
   - os dados pessoais do motorista desligado seguem o prazo de guarda da spec 016.
9. **Pedido do motorista (LGPD, direito de acesso):** "Exportar dados deste motorista" gera um arquivo com o cadastro,
   termos, viagens e momentos confirmados. A exportação vai para o registro de atividades.

## Comportamento

- **Cadastrar motorista**
  - Dado o Supervisor, quando preenche os campos obrigatórios e salva, então o motorista aparece na lista e o registro
    ganha "cadastrou motorista".
  - Dada uma matrícula ou CNH que já existe, então o campo mostra "Já existe um motorista com esta matrícula" e nada é
    gravado.
  - Dada a validade da CNH no passado, então o painel salva e mostra o aviso de CNH vencida.
- **Termo**
  - Dado um motorista sem termo, quando alguém abre a viagem dele, então os momentos aparecem e o botão de vídeo diz
    "Vídeo trancado: falta o termo".
- **Veículo e caixa**
  - Dada uma caixa sem veículo, quando o Supervisor cadastra o veículo e escolhe a caixa, então a caixa sai da lista de
    livres.
  - Dada uma caixa conectada que não está vinculada a veículo, então o passo a passo da importação pergunta "Em qual
    veículo esta caixa está?" antes de abrir a viagem.
- **Planilha**
  - Dada uma planilha com 3 linhas boas e 1 com CNH inválida, então a prévia mostra "3 prontos para entrar, 1 com erro
    na linha 4: número da CNH inválido", e confirmar grava só os 3.

## Critérios de aceite

| ID | Critério | Teste |
|---|---|---|
| MOT-01 | Campos obrigatórios da decisão 1; matrícula e CNH únicas na empresa | `tests/test_painel_cadastros.py` |
| MOT-02 | CNH com 11 dígitos e dígito verificador; CPF opcional com dígito verificador; CPF mascarado na lista | idem |
| MOT-03 | Nome nos relatórios sugerido ("Carlos Menezes" → "Carlos M.") e editável | idem |
| MOT-04 | Sem termo registrado, a ponte recusa entregar vídeo daquele motorista, mesmo com chamada direta | idem |
| MOT-05 | Termo nunca apagado: revogar ou reassinar cria registro novo com data, versão e quem registrou | idem |
| MOT-06 | Aviso de CNH 30 dias antes de vencer e de CNH vencida, sem bloquear importação | idem (relógio falso) |
| MOT-07 | "Exportar dados deste motorista" gera arquivo com cadastro, termos, viagens e momentos confirmados, e registra | idem |
| VEI-01 | Número único na empresa; placa Mercosul ou antiga; tipo e "transporta" obrigatórios | idem |
| VEI-02 | "Transporta" define a regra de descanso usada no relatório (carga 30 min a cada 6 h, passageiros 30 min a cada 4 h) | idem |
| CXA-01 | Caixas só vêm do arquivo da empresa; o painel não cria caixa | idem |
| CXA-02 | Uma caixa em um veículo por vez; trocar guarda o histórico e não muda viagens antigas | idem |
| CXA-03 | Caixa revogada não importa viagem e aparece como bloqueada | idem |
| PLA-01 | Importar planilha mostra prévia com linhas prontas, com erro (linha e motivo) e repetidas; só grava ao confirmar | idem |
| CAD-01 | Nada é apagado: desligado e fora de uso somem das listas do dia a dia e continuam nas viagens antigas | idem |
| CAD-02 | Toda criação, edição, troca de caixa e exportação gera linha no registro de atividades (spec 014) | idem |

## Fora de escopo agora

- Escala de viagens (quem sai com qual veículo e quando).
- Garagens ou filiais separadas dentro da mesma empresa (pergunta 3).
- Documentos do veículo (licenciamento, tacógrafo) e manutenção.
- Foto do motorista e reconhecimento de rosto.

## Perguntas para o Matheus

1. CPF do motorista: pedir (opcional) ou não pedir? A proposta é opcional, para não guardar sem necessidade.
2. Revezamento: uma viagem pode ter dois motoristas trocando no meio? Se sim, a caixa precisa saber a hora da troca.
3. Empresas com mais de uma garagem precisam separar motoristas e veículos por garagem?
4. A empresa já tem os motoristas numa planilha ou sistema de RH? Se tiver, qual formato, para o modelo de importação
   bater.

## Riscos

- **Termo trancando vídeo** pode parecer defeito para a garagem: o aviso precisa dizer o motivo e o que fazer, e o guia
  (spec 017) explica.
- **Dado pessoal no computador da garagem:** mesmo cuidado da spec 014 (pasta do usuário, bloqueio e disco
  criptografado recomendado).
- **Validação de CNH:** o algoritmo do dígito verificador precisa de casos reais anonimizados para teste; sem eles, os
  testes usam números gerados pelo próprio algoritmo.
