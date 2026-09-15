# Spec 014 · Entrar, equipe e permissões do painel

| Campo | Valor |
|---|---|
| Status | aprovada em 14/09/2026 ("gostei, pode fazer", com o pedido de menos cara de IA e mais movimento); em construção |
| PRD | RF-40 (menu do painel), RF-41 (entrar e primeiro acesso), RF-42 (equipe e funções), RF-43 (registro de atividades), RNF-12 (senha e sessão) |
| Pedido | "ainda falta bastante coisa nesse painel: a parte de fazer login, uma parte de configuração, uma parte de coisas separadas, registro de veículos e motoristas, registros de funcionários, guia de uso de tudo etc. Falta muita, muita coisa" (14/09/2026) |
| Specs irmãs | 015 (cadastros), 016 (configurações), 017 (guia de uso); 012 (telas aprovadas), 013 (janela do app) |
| Código | `painel/app/` (telas) e `painel/desktop/` (contas, sessão e banco local) |

## Contexto

- **Como está o painel hoje:** as telas aprovadas (caixa conectada, relatório da viagem, veículos e caixas) abrem sem
  login, com dados fictícios, e as decisões somem ao fechar a janela.
- **O que já existe no servidor** (`servidor/backend/auth.py`, `database.py:196-265`):
  - login com papéis `admin`, `gestor` e `motorista`;
  - sessão em cookie, consentimentos e tabela de auditoria.
  - Ele serve de referência de regras, não de código: o painel roda no computador da garagem, sem depender de internet.
- **Conflito com o PRD:** o RF-26 diz "logins criados só pela equipe RotaGuard". Num app que funciona sem internet, a
  empresa precisa criar os logins dos próprios funcionários.
  - Proposta (decisão 2): a RotaGuard continua controlando quem **ativa** o painel, e o administrador da empresa cria a
    equipe.

## Mapa do painel depois de entrar

Menu fixo na coluna da esquerda, com nomes simples:

| Item | O que tem | Spec |
|---|---|---|
| Início | Caixa conectada agora, o que falta verificar hoje, avisos (CNH vencendo, caixa com problema) e "Primeiros passos" enquanto a instalação não termina | 012, 017 |
| Viagens | Todas as viagens, com busca e filtro por data, veículo, motorista e "falta verificar"; abre o relatório aprovado | 012 |
| Motoristas | Cadastro, CNH, termo de ciência e histórico de cada motorista | 015 |
| Veículos e caixas | Cadastro dos veículos e a caixa instalada em cada um | 015 |
| Equipe | Pessoas que usam o painel, função de cada uma e registro de atividades | esta |
| Configurações | Empresa, regras da viagem, guarda dos vídeos, cópia de segurança, acesso e sobre | 016 |
| Guia de uso | Passo a passo de tudo, com busca | 017 |

- **Rodapé do menu:** nome e função de quem entrou, e o botão "Sair".
- **Contador:** o item Viagens mostra quantos momentos faltam verificar. Os outros itens não têm contador, para não
  encher a tela.
- **Caixa conectada:** o cartão com o progresso aparece no topo do menu só enquanto há caixa conectada (como na prévia
  aprovada).
- **Mudança na prévia aprovada:** a lista de viagens sai da coluna da esquerda e vai para a tela Viagens. A coluna
  vira menu, porque agora são 7 áreas.

## Decisões

1. **Contas guardadas no próprio computador.**
   - Banco SQLite na pasta de dados do app:
     - Windows: `%LOCALAPPDATA%\RotaGuard\Painel\painel.db`;
     - Linux: `~/.local/share/rotaguard-painel/painel.db`.
   - Funciona sem internet. Contas compartilhadas entre computadores ficam como pergunta (1).
2. **Ativação, sem cadastro aberto.**
   - No primeiro uso, o painel pede o **arquivo da empresa** entregue pela RotaGuard. É o chaveiro de coleta da spec
     003, que já identifica a empresa e as caixas dela.
   - Com o arquivo válido, cria-se o primeiro administrador: nome, usuário e senha.
   - Sem o arquivo, o painel só abre o modo demonstração, com dados fictícios e aviso.
3. **Três funções**, com nomes de garagem:

   | Pode fazer | Administrador | Supervisor | Consulta |
   |---|---|---|---|
   | Ver viagens e relatórios, imprimir | sim | sim | sim |
   | Ver os vídeos curtos | sim | sim | não |
   | Conectar caixa e importar viagem | sim | sim | não |
   | Confirmar, marcar alarme falso e registrar orientação | sim | sim | não |
   | Cadastrar e editar motoristas e veículos | sim | sim | não |
   | Equipe, configurações e registro de atividades | sim | não | não |

   - O motorista não entra no painel da garagem. A área do motorista (RF-23) é outra etapa.
   - A permissão é conferida no lado Python (decisão 5), nunca só na tela.
4. **Senha:**
   - no mínimo 10 caracteres, sem exigir símbolo; senhas muito comuns são recusadas com uma lista local;
   - guardada só como hash `scrypt` da biblioteca padrão do Python, com N = 2^17, r = 8, p = 1 e sal de 16 bytes;
   - conferida com `hmac.compare_digest`;
   - quem recebe senha nova do administrador troca no primeiro acesso.
5. **Sessão sem porta de rede:**
   - login, cadastros e decisões passam pela ponte do pywebview (`js_api`), não por rotas HTTP;
   - outro programa do computador não consegue chamar essas funções pela porta local, que continua servindo só os
     arquivos da interface (spec 013);
   - a sessão existe só na memória do processo: fechar o app é sair.
6. **Tentativas erradas:**
   - depois de 5 erros seguidos, o usuário espera 30 s;
   - a espera dobra a cada novo erro, até 15 min;
   - cada erro vai para o registro de atividades.
7. **Bloqueio por tempo sem uso:**
   - padrão de 15 min, configurável de 5 a 60 min (spec 016);
   - a tela escurece e pede a senha de novo, sem perder a página aberta.
8. **Esqueci a senha**, sem e-mail porque o app é offline:
   - o administrador cria uma senha temporária para a pessoa;
   - se o único administrador esquecer, vale o **código de recuperação** mostrado uma vez na ativação, para imprimir e
     guardar;
   - o código é guardado só como hash.
9. **Ninguém é apagado.**
   - Pessoa que sai da empresa é **desativada**, e o nome continua nas revisões que ela fez.
   - O último administrador ativo não pode ser desativado.
10. **"Quem verificou"** passa a ser o nome de quem entrou. Na prévia, aparecia "Você".
11. **Registro de atividades:**
    - só acrescenta, com cada linha levando o hash da anterior (mesma ideia do registro da viagem, spec 001);
    - guarda quem, quando, o quê e em quê: entrou, errou a senha, saiu, bloqueou, abriu vídeo, confirmou, desfez,
      cadastrou, editou, desativou, mudou configuração, fez cópia de segurança e exportou;
    - o administrador vê em Equipe → Registro de atividades, filtra por pessoa e data e exporta em CSV.

## Comportamento

- **Primeiro uso**
  - Dado o painel recém-instalado, quando abre, então pede o arquivo da empresa ou oferece "Ver demonstração".
  - Dado o arquivo válido, quando a pessoa cria o administrador, então o painel mostra o código de recuperação uma vez,
    pede para imprimir ou anotar e abre o Início com os Primeiros passos.
  - Dado um arquivo de outra empresa ou alterado, então aparece "Este arquivo não é válido. Peça um novo à RotaGuard" e
    nada é criado.
- **Entrar**
  - Dado um usuário ativo, quando digita a senha certa, então entra no Início e o registro ganha "entrou".
  - Dada a 5ª senha errada seguida, então aparece "Espere 30 segundos para tentar de novo" com contagem regressiva.
  - Dado um usuário desativado, então aparece "Este acesso foi desativado. Fale com o administrador", sem dizer se a
    senha estava certa.
- **Bloqueio**
  - Dados 15 min sem mexer, então o painel bloqueia a tela e o vídeo que estava aberto para de tocar.
- **Permissão**
  - Dada uma pessoa com função Consulta, quando abre um relatório, então vê os momentos, mas não vê o botão de vídeo nem
    os botões de decisão.
  - Dada uma chamada à ponte sem a permissão certa, então o Python recusa e registra a tentativa, mesmo que a tela tenha
    sido alterada.
- **Equipe**
  - Dado o administrador, quando adiciona uma pessoa, então escolhe a função, recebe uma senha temporária para passar à
    pessoa e a criação vai para o registro.
  - Dado o último administrador ativo, quando tenta se desativar ou virar Supervisor, então o painel recusa e explica.

## Critérios de aceite

| ID | Critério | Teste |
|---|---|---|
| ENT-01 | Sem banco, o app abre a tela de ativação; sem arquivo da empresa, só a demonstração abre | `tests/test_painel_contas.py` |
| ENT-02 | Arquivo da empresa com assinatura inválida, de outra empresa ou alterado é recusado e nada é gravado | idem |
| ENT-03 | Senha guardada só como `scrypt` (N 2^17, r 8, p 1, sal de 16 bytes); nenhuma senha em texto no banco, no log ou na ponte | idem (procura a senha em todos os arquivos gerados) |
| ENT-04 | Senha com menos de 10 caracteres ou da lista de senhas comuns é recusada com mensagem simples | idem |
| ENT-05 | 5 erros seguidos → 30 s de espera, dobrando até 15 min; cada erro no registro | idem (relógio falso) |
| ENT-06 | Usuário desativado recebe a mesma resposta com senha certa ou errada | idem |
| ENT-07 | Sessão só na memória: reabrir o app pede login; nenhum token em arquivo, cookie ou `localStorage` | idem + teste da interface |
| ENT-08 | Bloqueio após o tempo configurado; desbloquear exige a senha de quem entrou | idem (relógio falso) |
| ENT-09 | Código de recuperação mostrado uma vez, guardado só como hash, e usável uma vez só | idem |
| EQP-01 | Tabela de permissões da decisão 3 conferida no Python para cada função da ponte | idem (matriz função × ação) |
| EQP-02 | Consulta não recebe vídeo nem botões de decisão na tela | teste da interface |
| EQP-03 | Ninguém é apagado; desativar mantém o nome nas revisões; o último administrador ativo não pode ser desativado nem rebaixado | `tests/test_painel_contas.py` |
| EQP-04 | Decisão de momento grava o nome e a função de quem entrou | idem |
| ATV-01 | Registro de atividades só acrescenta; cada linha leva o hash da anterior; alterar ou apagar uma linha é detectado | idem |
| ATV-02 | Todas as ações da decisão 11 geram linha com quem, quando, o quê e em quê | idem |
| ATV-03 | Exportação CSV do registro, só para o administrador, também registrada | idem |
| MEN-01 | Menu com os 7 itens na ordem do mapa; o item da tela aberta marcado; itens sem permissão não aparecem | teste da interface (`painel/app/scripts/testes/shell.test.mjs`) e roteiro `painel/app/scripts/conferir-telas.mjs` |
| MEN-02 | Ctrl+K abre a busca rápida: telas do menu da própria função, viagens, motoristas, veículos e capítulos do guia, sem acento e sem maiúscula; Enter abre (motorista e veículo no painel lateral), Esc fecha. Incluído em 15/09/2026, vindo do contrato do painel | idem |

## Fora de escopo agora

- Contas compartilhadas entre vários computadores ou pela internet.
- Entrar com a conta do Windows, Google ou Microsoft, e verificação em duas etapas.
- Login do motorista (RF-23).
- Recuperar senha por e-mail ou SMS.

## Perguntas para o Matheus

1. ~~A empresa usa o painel em **um computador só** por garagem, ou precisa ver as mesmas contas e viagens em vários
   computadores?~~ **Respondida em 14/09/2026:** "por enquanto local". Mais para frente, "tudo isso vai estar conectado a
   uma VPS": por isso cada registro já nasce com `uid`, `criado_em` e `alterado_em`.
2. As três funções (Administrador, Supervisor, Consulta) servem, ou falta alguma (por exemplo, "Instrutor", que só
   registra orientação)?
3. A função Consulta pode ver os vídeos? A proposta é não, para expor menos o rosto do motorista (LGPD).
4. O usuário do login é um nome curto (`marina.lopes`) ou o CPF? A proposta é nome curto, para não espalhar CPF.

## Riscos

- **Computador compartilhado ou roubado:** as senhas estão protegidas, mas nomes e viagens ficam no banco local.
  - Resposta: pasta do usuário do Windows, bloqueio por tempo e recomendação de disco criptografado (BitLocker) no guia.
  - Criptografar o próprio banco (SQLCipher) fica para avaliar: é mais uma dependência nativa no pacote.
- **Código de recuperação perdido** junto com a senha do único administrador: só a RotaGuard reativa, com arquivo novo
  da empresa, e as contas antigas ficam desativadas.
- **scrypt pesado em computador fraco:** cerca de 130 MB de memória por tentativa. Medir no pior computador de garagem
  que tivermos; se passar de 1 s, ajustar N e registrar aqui.
