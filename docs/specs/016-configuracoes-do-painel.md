# Spec 016 · Configurações do painel

| Campo | Valor |
|---|---|
| Status | aprovada em 14/09/2026 ("gostei, pode fazer", com o pedido de menos cara de IA e mais movimento); em construção |
| PRD | RF-47 (configurações), RF-48 (cópia de segurança), RNF-05 (retenção), RNF-13 (dados do painel no computador) |
| Pedido | "uma parte de configuração" (14/09/2026) |
| Specs irmãs | 014 (só o administrador mexe; registro de atividades), 015 (cadastros), 017 (guia) |
| Código | `painel/app/` (telas) e `painel/desktop/` (valores, banco e cópia) |

## Contexto

- Hoje, valores como o limite de direção contínua, a madrugada e o prazo dos vídeos estão fixos no código ou em
  perguntas abertas do PRD (Q4, Q5).
- A empresa precisa ajustar o que é dela (nome, logo, prazos, cópia de segurança) sem chamar a RotaGuard.
- O que é regra de lei ou de segurança não pode ser afrouxado pela tela.

## Decisões

1. **Só o administrador** abre Configurações. Toda mudança gera linha no registro de atividades com o valor antigo e o
   novo (spec 014).
2. **Seções**, cada uma numa página, com uma lista à esquerda:

   | Seção | O que tem |
   |---|---|
   | Empresa | Nome, razão social, CNPJ, telefone, endereço e logo para os relatórios impressos |
   | Regras da viagem | Limite de direção contínua, horário da madrugada e descanso por tipo de transporte |
   | Vídeos e guarda dos dados | Por quanto tempo guardar vídeos, registros de viagem e dados de motorista desligado |
   | Cópia de segurança | Onde ficam os dados, fazer cópia agora, restaurar e lembrete |
   | Acesso | Tempo sem uso para bloquear a tela |
   | Impressão | Cabeçalho do relatório e o que sai no papel |
   | Sobre o RotaGuard | Versão, novidades, licenças, privacidade e termos, contato de suporte |

3. **Regras da viagem**, com trava de lei:
   - direção contínua: padrão 5 h 30 (CTB, art. 67-C); a empresa pode **diminuir**, nunca aumentar acima da lei;
   - madrugada: 00:00 a 06:59 (RF-03), só leitura nesta versão;
   - descanso: carga 30 min a cada 6 h, passageiros 30 min a cada 4 h (RF-03), só leitura;
   - mudança vale para viagens importadas **depois** dela; viagens antigas guardam a regra com que foram lidas.
4. **Guarda dos dados** (LGPD, RNF-05):

   | Dado | Padrão | Opções |
   |---|---|---|
   | Vídeos curtos, depois da coleta | 30 dias (PRD, Q4) | 7, 15, 30, 60 ou 90 dias |
   | Registro das viagens e decisões | 5 anos | 1, 2 ou 5 anos |
   | Dados pessoais de motorista desligado | 5 anos depois do desligamento | 1, 2 ou 5 anos |

   - Vencido o prazo, o painel apaga sozinho na abertura seguinte e registra quantos itens apagou.
   - Motorista desligado: vencido o prazo, saem nome, CNH, telefone e CPF; as viagens antigas continuam, com
     "Motorista desligado" no lugar do nome.
   - Vídeo ligado a momento marcado como "em apuração" não é apagado até alguém tirar a marca (pergunta 2).
   - O registro da viagem continua depois que o vídeo é apagado: o relatório diz "Vídeo apagado em 14/10/2026 (prazo de
     30 dias)".
5. **Cópia de segurança:**
   - arquivo único `.rotaguard-copia`, com banco, vídeos ainda no prazo e configurações;
   - protegido por uma senha escolhida na hora (AES-GCM com chave derivada por `scrypt`); sem a senha, não abre;
   - o painel sugere pen drive ou pasta de rede e **lembra toda semana** se a última cópia tiver mais de 7 dias;
   - restaurar mostra a data e o conteúdo da cópia, pede a senha e troca os dados atuais só depois de confirmar, guardando
     os atuais numa cópia automática antes.
6. **Pasta dos dados:** mostrada em Cópia de segurança, com botão "Abrir pasta". Mudar de pasta fica fora desta versão.
7. **Sobre o RotaGuard:**
   - versão e data do pacote;
   - "Ver se há versão nova" abre a página de downloads do site, sem baixar sozinho;
   - licenças de terceiros e textos de privacidade, LGPD e termos, sem aceite obrigatório (mesma decisão da spec 010).
8. **Aparência:** tema claro, como a prévia aprovada. Opção de **texto maior** (115%) para quem lê pior na tela. Tema
   escuro fica como pergunta da spec 012.

## Comportamento

- **Direção contínua**
  - Dado o administrador, quando tenta pôr 6 h, então o campo mostra "O máximo é 5 h 30, pela lei (CTB, art. 67-C)" e
    não salva.
  - Quando põe 5 h, então as viagens importadas a partir de agora usam 5 h e o registro guarda "5 h 30 → 5 h".
- **Guarda**
  - Dado vídeo de 31 dias com prazo de 30, quando o painel abre, então o vídeo é apagado e o relatório mostra quando e
    por quê.
- **Cópia**
  - Dada a última cópia com 8 dias, quando o administrador entra, então o Início mostra "A última cópia de segurança
    foi há 8 dias" com o botão "Fazer cópia agora".
  - Dada uma cópia com senha errada, quando alguém tenta restaurar, então aparece "Senha da cópia errada" e nada muda.
- **Permissão**
  - Dado um Supervisor, então o item Configurações não aparece no menu, e a ponte recusa mudanças chamadas direto.

## Critérios de aceite

| ID | Critério | Teste |
|---|---|---|
| CFG-01 | Só o administrador lê e muda configurações; a ponte recusa as outras funções | `tests/test_painel_configuracoes.py` |
| CFG-02 | Toda mudança registra valor antigo, valor novo, quem e quando | idem |
| CFG-03 | Direção contínua aceita de 1 h até 5 h 30; acima disso é recusada com a mensagem da lei | idem |
| CFG-04 | Viagem guarda a regra com que foi lida; mudar a regra não muda relatório antigo | idem |
| CFG-05 | Prazos de guarda só com as opções da decisão 4; padrões 30 dias, 5 anos e 5 anos | idem |
| CFG-06 | Vencido o prazo, o vídeo é apagado na abertura, o relatório diz quando e por quê, e o registro conta os apagados | idem (relógio falso) |
| CFG-07 | Vídeo "em apuração" não é apagado pelo prazo | idem |
| BKP-01 | Cópia é um arquivo só, cifrado com AES-GCM e chave de `scrypt`; sem a senha certa não abre e nada muda | idem |
| BKP-02 | Restaurar guarda os dados atuais antes e só troca depois de confirmar | idem |
| BKP-03 | Aviso no Início quando a última cópia tem mais de 7 dias | idem (relógio falso) |
| CFG-08 | Sobre mostra a versão do pacote, licenças e os textos legais, sem aceite obrigatório | teste da interface |
| CFG-09 | Texto maior aumenta o tamanho sem quebrar as telas em 1200 × 760 (tamanho mínimo da janela) | conferência visual |

## Fora de escopo agora

- Ajustar a sensibilidade da detecção na caixa pelo painel (vai para a caixa, com teste de campo).
- Mudar a pasta dos dados, cópia automática para a nuvem e atualização automática.
- Tema escuro e idiomas além do português.

## Perguntas para o Matheus

1. Os prazos padrão (vídeos 30 dias; registros e dados de desligado 5 anos) servem até o parecer do advogado?
2. Precisa da marca "em apuração", que segura o vídeo além do prazo quando há processo ou reclamação?
3. A cópia de segurança pode ficar só com o administrador, ou o Supervisor também faz?

## Riscos

- **Senha da cópia esquecida:** a cópia fica inútil. O painel avisa isso na hora de criar e sugere anotar junto com o
  código de recuperação (spec 014).
- **Prazo de 5 anos** é proposta sem parecer jurídico; o advogado pode mudar.
- **Apagar na abertura** depende de o painel ser aberto; se ficar meses fechado, apaga tudo de uma vez na próxima vez, e
  o registro mostra.
