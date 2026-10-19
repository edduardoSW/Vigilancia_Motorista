# Spec 024 · Painel da empresa no navegador (VPS), sem deixar de ser local

| Campo | Valor |
|---|---|
| Status | implementada e testada em 19/10/2026 (21 verificações WEB-01 a WEB-14, fluxo real no Edge headless) e **não publicada**: no mesmo dia o Matheus pediu "mas o painel eu quero que seja executavel" (spec 026). Liga com o `implantacao/vps/Dockerfile.painel` se um dia for preciso |
| PRD | RF-61, RNF-14, RNF-15 |
| Pedido | "eu quero que o site e o painel de app funcionem" (na VPS); "algo muito completo para eu e os integrantes da minha equipe usarem na entrega de pitch"; "mesmo que a vps caia eu quero que o projeto continue caso tenha os arquivos do painel e script baixados no dispositivo para rodalos localmente" (19/10/2026) |
| Muda | A decisão de 14/09 ("esse dashboard não deve ser web") continua valendo para o produto instalado; a versão web é um acesso a mais, para a equipe e para o pitch |
| Specs irmãs | 013 (app do painel), 014 (entrar e permissões), 021 (VPS), 025 (câmera no navegador) |
| Código | `painel/web/` (servidor HTTP da ponte), `painel/app/src/lib/bridge.ts`, `painel/app/next.config.ts`, `implantacao/vps/Dockerfile.painel` |
| Testes | `tests/test_painel_web.py` (WEB-01 a WEB-14), `painel/app/scripts/testes/transporte.test.mjs` |

## Contexto

- As telas do painel só falam com `bridge` (`painel/app/src/lib/bridge.ts`). Hoje há dois transportes: a janela do app
  (`window.pywebview.api`, Python) e a demonstração em memória. O comentário do próprio arquivo já prevê trocar a ponte
  local por um servidor sem mudar as telas.
- Toda regra (contas, cadastros, permissões, atividades, cópia) está em módulos Python puros em `painel/desktop/`, com
  testes. A classe `Ponte` guarda a sessão de uma pessoa na memória.

## Decisões

1. **Terceiro transporte, `servidor`:** `POST {base}/api/ponte/{metodo}` com os argumentos em JSON. Escolhido só no
   build web (`NEXT_PUBLIC_PAINEL_TRANSPORTE=servidor`). O build do app instalado não muda: continua janela →
   demonstração.
2. **Servidor `painel/web/servidor_web.py`** (Starlette + Uvicorn, versões conferidas no PyPI na hora):
   - uma `Ponte` por sessão do navegador, todas sobre a mesma pasta de dados. Sem WAL: com WAL a cópia de segurança
     (`serialize`) não abre com `deserialize`; no diário padrão as várias conexões funcionaram (WEB-04);
   - cookie `rg_painel` aleatório, `HttpOnly`, `Secure`, `SameSite=Strict`, `Path=/painel`; sessão some depois do
     tempo de bloqueio das configurações (padrão da spec 014) e no máximo 12 h;
   - só métodos da lista `NOMES` do contrato; qualquer outro nome responde 404;
   - `POST` exige o cabeçalho `X-RotaGuard: 1` e `Origin` igual ao endereço do painel (CSRF);
   - corpo de até 16 MB (termo de até 10 MB em base64);
   - limite de tentativas por IP em `entrar` e `recuperar_acesso`, além da espera crescente que já existe em `contas`.
3. **Ativação na web protegida:** em endereço público, quem abrisse primeiro viraria administrador. Na web, ativar exige
   o código de ativação do `.env` da VPS (`PAINEL_CODIGO_ATIVACAO`), entregue ao Matheus fora do repositório.
4. **O que era do computador vira download:** exportações e cópia de segurança gravam num arquivo temporário e o servidor
   devolve o arquivo para o navegador baixar; "ver termo" devolve o arquivo para abrir em outra aba.
5. **Script local na web:** não existe processo local no servidor. `script_estado` responde "indisponível na web" e a
   tela Ao vivo oferece o teste com a câmera do próprio aparelho (spec 025).
6. **Endereço `/painel/`:** o build web usa `basePath: "/painel"`; o Caddy manda `/painel*` para o container do painel.
7. **Local primeiro (RNF-15):** o painel instalado continua lendo e gravando só no computador. Nenhuma tela do painel
   instalado depende da VPS. Sincronizar o painel instalado com a VPS fica para depois (spec própria).

## Critérios de aceite

| ID | Critério |
|---|---|
| WEB-01 | `estado` responde pelo HTTP o mesmo formato da ponte local |
| WEB-02 | Método fora da lista responde 404; nome com `_` no começo responde 404 |
| WEB-03 | `POST` sem `X-RotaGuard` ou com `Origin` de outro site responde 403 |
| WEB-04 | Duas sessões (dois cookies) entram com pessoas diferentes e cada uma vê só o próprio `estado.usuario` |
| WEB-05 | Sair numa sessão não derruba a outra |
| WEB-06 | `ativar_demonstracao` sem o código responde erro `sem_permissao`; com o código certo ativa uma vez só |
| WEB-07 | Cookie com `HttpOnly`, `Secure`, `SameSite=Strict` e `Path=/painel` |
| WEB-08 | `motorista_exportar` e `atividades_exportar` devolvem arquivo para download, sem gravar fora da pasta temporária |
| WEB-09 | `termo_ver` devolve o arquivo do termo com o tipo certo (PDF, PNG ou JPEG) |
| WEB-10 | Sessão expira depois do tempo sem uso e responde `sem_sessao` |
| WEB-11 | Corpo acima de 16 MB responde 413 |
| WEB-12 | Mais de 10 tentativas de `entrar` por minuto do mesmo IP respondem 429 |
| WEB-13 | O build do app instalado (sem a variável) não inclui o transporte `servidor` como escolha e continua abrindo a demonstração fora da janela |
| WEB-14 | Os testes antigos do painel (`tests/test_painel_*.py`) continuam passando |
