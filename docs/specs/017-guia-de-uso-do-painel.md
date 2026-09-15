# Spec 017 · Guia de uso do painel

| Campo | Valor |
|---|---|
| Status | aprovada em 14/09/2026 ("gostei, pode fazer", com o pedido de menos cara de IA e mais movimento); em construção |
| PRD | RF-49 (guia de uso e ajuda em cada tela) |
| Pedido | "guia de uso de tudo" (14/09/2026) |
| Specs irmãs | 012 (telas da viagem), 014 (entrar e equipe), 015 (cadastros), 016 (configurações) |
| Código | `painel/app/src/content/guide.ts` (texto), `painel/app/src/app/guia/` (tela), `painel/app/scripts/` (imagens do guia) |

## Contexto

- Quem usa o painel é gente da garagem, que não vai ler manual em PDF à parte.
- O guia fica **dentro do app**, abre sem internet e explica cada tela com a própria tela.

## Decisões

1. **Item "Guia de uso"** no rodapé do menu, para todas as funções, inclusive Consulta.
2. **Capítulos:**

   | # | Capítulo | O que ensina |
   |---|---|---|
   | 1 | Primeiros passos | Ativar com o arquivo da empresa, guardar o código de recuperação, cadastrar veículos, vincular caixas, cadastrar motoristas, registrar termos, adicionar a equipe |
   | 2 | Quando o veículo chega | Conectar a caixa, esperar a leitura, dizer quem dirigiu, abrir a viagem |
   | 3 | Verificar os momentos | O que é um momento, ver o vídeo, confirmar, alarme falso, orientar o motorista, desfazer |
   | 4 | O que cada alerta quer dizer | Cada tipo de alerta em frase simples, com "ajuda a avaliação e não é diagnóstico" |
   | 5 | Motoristas e termo de ciência | Por que o termo existe, modelo para imprimir, vídeo trancado sem termo, CNH vencendo |
   | 6 | Veículos e caixas | Cadastrar veículo, trocar caixa de veículo, caixa que precisa de atenção, caixa bloqueada |
   | 7 | Equipe e acessos | Funções, adicionar pessoa, senha esquecida, desativar, registro de atividades |
   | 8 | Cópia de segurança | Fazer cópia, guardar em pen drive, restaurar |
   | 9 | Quando algo dá errado | Caixa não reconhecida, registro alterado, vídeo apagado pelo prazo, tela bloqueada, esqueci a senha |
   | 10 | Privacidade e LGPD | O que o painel guarda, por quanto tempo, quem vê, pedido do motorista, disco criptografado |

3. **Formato de cada capítulo:**
   - passos numerados, uma ação por passo, frases curtas;
   - imagem da tela real do painel, gerada no build a partir dos dados fictícios (script de captura sem janela), para o
     guia nunca mostrar tela antiga;
   - no fim, "Se der errado", com o problema mais comum daquele passo.
4. **Busca:** campo "O que você quer fazer?" que procura nos títulos e no texto, sem diferenciar acento e maiúscula,
   sem biblioteca.
5. **Ajuda no lugar:** cada tela tem o link "Como funciona?" ao lado do título, que abre o capítulo certo do guia.
6. **Primeiros passos no Início:**
   - lista com o que falta para a instalação ficar pronta: cadastrar veículos, vincular caixas, cadastrar motoristas,
     registrar termos, adicionar a equipe e fazer a primeira cópia de segurança;
   - cada item marca sozinho quando é feito;
   - some quando tudo estiver feito, ou quando o administrador escolhe "Esconder".
7. **Alertas explicados da mesma fonte:** o capítulo 4 sai de `tipos-de-evento.json` (igual ao servidor), para nenhum
   alerta ficar sem explicação ou com nome diferente.
8. **Imprimir:** cada capítulo e o guia inteiro podem ser impressos ou salvos em PDF pela impressão do sistema.
9. **Linguagem de garagem:** o texto não usa palavras técnicas como hash, bloco, PERCLOS, token, sessão, API, banco de
   dados ou criptografia sem explicar. Um teste procura essas palavras.

## Comportamento

- **Busca**
  - Dado o guia aberto, quando alguém digita "senha", então aparecem "Esqueci a senha" (capítulo 9) e "Adicionar pessoa"
    (capítulo 7), com o trecho onde a palavra aparece.
  - Dada uma busca sem resultado, então aparece "Não achamos nada com 'x'. Tente outra palavra ou veja a lista de
    capítulos".
- **Ajuda no lugar**
  - Dado o relatório de uma viagem, quando alguém clica em "Como funciona?", então abre o capítulo 3 no passo de
    verificar momentos.
- **Primeiros passos**
  - Dada uma instalação sem veículos, então o Início mostra "Cadastre os veículos da empresa" como próximo passo, com o
    botão que leva ao cadastro.

## Critérios de aceite

| ID | Critério | Teste |
|---|---|---|
| GUI-01 | Os 10 capítulos existem, em ordem, cada um com passos numerados e "Se der errado" | `painel/app/scripts/testes/guia.test.mjs` |
| GUI-02 | Toda tela do painel tem "Como funciona?" apontando para um capítulo e passo que existem | idem |
| GUI-03 | Todo tipo de alerta de `tipos-de-evento.json` tem explicação no capítulo 4, com o mesmo nome | idem |
| GUI-04 | Busca sem acento e sem maiúscula acha "Esqueci a senha" com "SENHA" e "senha" | idem |
| GUI-05 | Nenhuma palavra técnica da lista da decisão 9 no texto do guia sem explicação | idem |
| GUI-06 | Imagens do guia geradas pelo build a partir das telas com dados fictícios; imagem faltando quebra o build | idem |
| GUI-07 | Primeiros passos marcam cada item pelo estado real (veículos, caixas, motoristas, termos, equipe, cópia) e somem quando completos | teste da interface |
| GUI-08 | O guia abre sem internet e sem login de administrador (qualquer função) | teste da interface |
| INI-01 | `inicio_resumo()` devolve a última cópia, os dias desde ela e se os Primeiros passos foram escondidos; exige sessão. Incluído em 15/09/2026 | `tests/test_painel_contas.py` |
| INI-02 | `primeiros_passos_esconder(esconder)` só para o administrador, com linha no registro de atividades. Incluído em 15/09/2026 | idem |

## Fora de escopo agora

- Vídeos de tutorial.
- Chat de suporte dentro do app.
- Guia publicado no site.

## Perguntas para o Matheus

1. Quer vídeos curtos de tutorial junto do guia no futuro?
2. O guia deve ter o contato de suporte da RotaGuard (WhatsApp e telefone)? Hoje o número não está definido (PRD, Q6).

## Riscos

- **Guia desatualizado:** mitigado pelas imagens geradas no build (GUI-06) e pelos testes de links e alertas (GUI-02,
  GUI-03).
- **Texto longo demais:** cada passo com uma ação; revisão do texto com a mesma régua de linguagem simples das telas.
