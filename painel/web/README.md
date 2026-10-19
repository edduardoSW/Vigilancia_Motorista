# Painel da empresa no navegador (spec 024)

O mesmo painel do app instalado, servido pela VPS em `https://rotaguard.acexpartners.com.br/painel/`. As telas são o
build web do Next (`painel/app/out-web/`) e a ponte é este servidor: `POST /painel/api/ponte/{metodo}` chama o método
de mesmo nome da `Ponte` (`painel/desktop/ponte.py`), com as mesmas regras, permissões e respostas.

**O app instalado não depende deste servidor (RNF-15).** O build normal (`npm run build`, pasta `out/`) não leva o
transporte "servidor" e continua janela do app → transporte vazio (spec 030: sem dados fictícios). Se a VPS cair, quem tem o painel e o script baixados
segue usando tudo localmente.

## Como rodar

```bash
# 1. interface (build web, sai em painel/app/out-web/)
cd painel/app
PAINEL_BASE_PATH=/painel NEXT_PUBLIC_PAINEL_TRANSPORTE=servidor npm run build

# 2. servidor (na raiz do repositório)
python -m pip install -r painel/web/requirements.txt
PAINEL_DADOS=/dados PAINEL_ESTATICO=painel/app/out-web PAINEL_ORIGEM=https://rotaguard.acexpartners.com.br \
PAINEL_CODIGO_ATIVACAO=... \
python -m uvicorn servidor_web:app --app-dir painel/web --host 0.0.0.0 --port 8000 --workers 1 \
  --no-proxy-headers --no-server-header
```

- **Um processo só (`--workers 1`)**: sessões, limite de tentativas e travas ficam na memória.
- `--no-proxy-headers`: quem lê `X-Forwarded-For`/`X-Forwarded-Proto` é o próprio servidor, só quando a conexão vem de
  um proxy confiável (`PAINEL_PROXIES`).
- No Git Bash do Windows, use `MSYS_NO_PATHCONV=1` antes das variáveis com `/painel` (senão viram `C:/Program Files/Git/painel`).
- Teste local em http: `PAINEL_COOKIE_SEGURO=0` e `PAINEL_ORIGEM=http://127.0.0.1:8000`.
- Saúde (healthcheck do Docker): `GET /painel/api/saude` → `{"ok": true}`.

## Variáveis

| Variável | Padrão | Para quê |
|---|---|---|
| `PAINEL_DADOS` | `/dados` | Pasta do `painel.db` e dos termos importados (volume do Docker). |
| `PAINEL_ESTATICO` | (nenhum) | Pasta do build web (`out-web`). Sem ela, só a API responde. |
| `PAINEL_BASE` | `/painel` | Endereço base da interface e da API (igual ao `PAINEL_BASE_PATH` do build). |
| `PAINEL_CODIGO_ATIVACAO` | (nenhum) | Código para ativar pela web. Sem ele (ou com menos de 12 caracteres), a ativação pela web fica desligada. Gerar com `python -c "import secrets; print(secrets.token_urlsafe(24))"` e guardar só no `.env` da VPS. |
| `PAINEL_ORIGEM` | (nenhum) | Endereço do site, ex.: `https://rotaguard.acexpartners.com.br`. O POST só passa com `Origin` igual. Sem ela, vale o mesmo host do pedido (avisa no log). |
| `PAINEL_COOKIE_SEGURO` | `1` | `0` tira o `Secure` do cookie (só para teste local em http). |
| `PAINEL_PROXIES` | redes privadas e loopback | De onde `X-Forwarded-For` é aceito (lista de CIDR separada por vírgula; `nenhum` desliga). O primeiro IP da lista vira o IP do limite de tentativas. |
| `PAINEL_TEMP` | temporária do sistema | Onde ficam, por alguns instantes, os arquivos das exportações (subpasta `rg-painel-web`, limpa ao subir). |
| `PAINEL_CSP` | política padrão | Troca o `Content-Security-Policy` (vazio desliga). A padrão só aceita o próprio endereço; WebAssembly e `blob:` liberados para a câmera (spec 025). |
| `PAINEL_SCRYPT_SIMULTANEOS` | `1` | Quantos cálculos de senha (scrypt, 128 MB cada) ao mesmo tempo. |
| `PAINEL_NUCLEO` | `../desktop` | Pasta do núcleo Python (`ponte.py` e cia.), se a imagem usar outro layout. |
| `ROTAGUARD_VERSAO` | `package.json` do painel | Versão mostrada nas telas (a `Ponte` lê `painel/app/package.json` se a variável não existir). |

## Contrato HTTP

- `POST {base}/api/ponte/{metodo}` com `{"args": [...]}` → o mesmo `{"ok": true, "dados"}` ou
  `{"ok": false, "erro", "codigo", "campo"?, "esperar_s"?}` da ponte local. Só os nomes da lista `NOMES` (iguais aos de
  `bridge.ts`); o resto responde 404.
- Exige `X-RotaGuard: 1` e `Origin` certo (403). Corpo até 16 MB (413). Respostas da API com `Cache-Control: no-store`.
- Ativação: `{"args": [...], "ativacao": "<código>"}`. O código vai no corpo, não em cabeçalho, porque proxies costumam
  registrar cabeçalhos. Sem o código certo: `codigo: "sem_permissao"`, `campo: "codigo_ativacao"`.
- **Arquivos**: `atividades_exportar`, `motorista_exportar`, `copia_fazer` e `termo_ver` (PDF) devolvem também
  `"arquivo": {"nome", "tipo" (MIME), "base64"}`. O `bridge.ts` baixa o arquivo no navegador (o PDF do termo abre em
  outra aba) e entrega às telas a resposta de sempre. Escolhido por ser o mais simples no navegador: uma chamada só, sem
  estado no servidor. Limite de 32 MB por arquivo. Foto do termo continua em `dados.conteudo` (`data:image/...`).
- `script_estado`/`script_eventos`: sem erro; `aberto: false` com `indisponivel: "..."` e lista vazia.

## Sessões e segurança

- Cookie `rg_painel` (32 bytes aleatórios), `HttpOnly; Secure; SameSite=Strict; Path=/painel`, sem validade (some ao
  fechar o navegador). A id troca a cada `entrar`. Sair apaga o cookie e a sessão.
- Sessão some depois do tempo de bloqueio das Configurações sem nenhum pedido (padrão 15 min) e, mesmo em uso, depois
  de 12 h. No máximo 200 sessões (a de uso mais antigo sai).
- Quem ainda não entrou não ganha sessão: `estado` e `recuperar_acesso` usam uma Ponte comum. `entrar` e a ativação
  abrem uma Ponte nova e só guardam a sessão se derem certo.
- A espera crescente das contas (5 erros: 30 s, dobrando até 15 min) vale para todas as sessões, e há também o limite
  de 10 tentativas por minuto por IP em `entrar`, `recuperar_acesso`, `desbloquear` e ativação (429 com `Retry-After`).
- Cada sessão tem a sua conexão SQLite na mesma pasta. **O banco fica no diário padrão, sem WAL**: com WAL, a imagem
  gravada na cópia de segurança (`serialize`) não abre com `deserialize` (testado). As escritas se revezam pelo
  `BEGIN IMMEDIATE` com espera de 5 s.
- Nunca registra senha, código, cookie nem corpo da requisição; falha interna aparece só como `método: TipoDoErro`.
- Cabeçalhos em toda resposta: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: same-origin`,
  `Permissions-Policy` (só câmera, só do próprio endereço) e a CSP.

## Testes

```bash
python -m pip install -r painel/web/requirements-teste.txt
python tests/test_painel_web.py            # WEB-01 a WEB-14 (o WEB-14 roda de novo tests/test_painel_*.py)
cd painel/app && npm test                  # transporte.test.mjs: transporte servidor e WEB-13 nos dois builds
```
