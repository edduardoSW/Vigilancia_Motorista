# Spec 021 · RotaGuard na VPS (site + painel web)

| Campo | Valor |
|---|---|
| Status | implementada em 19/10/2026: site e central no ar em `https://rotaguard.acexpartners.com.br` (Let's Encrypt), containers `morro-alto-os-rotaguard-site` e `morro-alto-os-rotaguard-central` saudáveis, os outros 9 containers da VPS sem mudança |
| PRD | RF-60, RF-61, RNF-14, RNF-15 |
| Pedido | "quero colocar esse projeto na vps quero colocar tudo o site vai estar em um subdominio rotaguard.acexpartners.com.br"; "na vps o nome do container docker deve estar com o nome morro alto os somente na vps"; "eu quero que o site e o painel de app funcionem"; "mesmo que a vps caia eu quero que o projeto continue caso tenha os arquivos do painel e script baixados no dispositivo para rodalos localmente" (19/10/2026) |
| Specs irmãs | 008 e 020 (site), 013 e 014 (painel), 024 (painel web) |
| Código | `implantacao/vps/`, `site/next.config.ts`, `site/Dockerfile`, `painel/web/` |

## Contexto (conferido na VPS em 19/10/2026)

- VPS `187.127.41.22` (Hostinger, Ubuntu 24.04.4, 1 vCPU, 3,8 GB de RAM, 18 GB livres), Docker 29.6.1, Compose 5.2.0.
- Já rodam lá: Brasigran, Hana Decor, links da Jania e o site Morro Alto (`morro-alto-site`, `morro-alto-site-db`).
- Um Caddy de borda próprio (`/root/edge`, container `edge-caddy`, rede `edge`) termina o TLS de todos os sites. Cada
  site é um arquivo em `/root/edge/conf/sites/*.caddy`. Firewall: só 22, 80 e 443.
- DNS de `acexpartners.com.br` na Hostinger (`dns-parking.com`). O domínio raiz está na Vercel: **não mexer**.

## Decisões

1. **Endereço:** `https://rotaguard.acexpartners.com.br`.
   - `/` e demais rotas: site (Next.js em modo `standalone`).
   - `/api/`: central de dados (spec 026): o script envia, o painel executável busca. O painel no navegador (spec
     024) ficou pronto mas não é publicado ("mas o painel eu quero que seja executavel", 19/10/2026).
2. **Containers só com o nome da VPS:** o compose usa `${CONTAINER_PREFIXO:-rotaguard}`; o `.env` da VPS define
   `CONTAINER_PREFIXO=morro-alto-os-rotaguard`. No ar: `morro-alto-os-rotaguard-site` e `morro-alto-os-rotaguard-central`.
   O nome "morro alto" não aparece no repositório além desta linha de spec.
3. **Nomes únicos na VPS** (erro 25 da vault: dois composes com serviço `app` confundiram o proxy): projeto `rotaguard`,
   serviços `rotaguard_site` e `rotaguard_central`, volume `rotaguard_central_dados`, pasta `/root/rotaguard`.
4. **Proxy:** reaproveita o `edge-caddy` e aponta para o nome do serviço (único), não do container. Novo arquivo
   `rotaguard.caddy`, validado (`caddy validate`) antes do
   `caddy reload`. Nenhum outro arquivo do Caddy é alterado.
5. **Imagens com tag do commit**, construídas na VPS a partir do código enviado por `rsync`/`tar`, e `atualizar.sh`
   que troca a tag e volta sozinho para a anterior se o container não ficar saudável em 90 s (mesmo padrão do site
   Morro Alto).
6. **Limites:** `mem_limit` 384 MB no site e 384 MB no painel; logs `json-file` 10 MB × 3.
7. **Downloads** (`site/public/downloads/`, fora do git, 155 MB) vão para um volume montado no site, não para dentro da
   imagem.
8. **A VPS nunca é dependência** (RNF-15): o painel instalado e o RotaGuard Teste não chamam a VPS para nada. A versão
   web é o mesmo código do painel com outro transporte da ponte.
9. **DNS (feito pelo Matheus):** registro A `rotaguard` → `187.127.41.22`, TTL 300, sem AAAA. O `rotaguard.caddy` só é
   ativado depois de o nome resolver, para o Caddy não entrar em espera crescente de certificado.

## Critérios de aceite

| ID | Critério |
|---|---|
| VPS-01 | `docker compose config` com `CONTAINER_PREFIXO=morro-alto-os-rotaguard` gera exatamente os containers `morro-alto-os-rotaguard-site` e `morro-alto-os-rotaguard-central`; sem a variável, `rotaguard-site` e `rotaguard-central` |
| VPS-02 | Os dois containers ficam `healthy` na VPS e nenhum outro container muda de estado ou de imagem |
| VPS-03 | `https://rotaguard.acexpartners.com.br/` responde 200 com certificado válido; `/` redireciona para `/pt-BR` e mostra o site |
| VPS-04 | `https://rotaguard.acexpartners.com.br/api/health` responde 200 pela central; `/painel/` não é publicado |
| VPS-05 | `caddy validate` passa antes do reload; os outros sites seguem respondendo 200 depois do reload |
| VPS-06 | `atualizar.sh` com uma tag que não sobe volta para a anterior |
| VPS-07 | O `.env` da VPS tem `chmod 600` e não entra no git |

## Fora de escopo

- Backup automático do volume do painel para fora da VPS (pergunta aberta abaixo).

## Perguntas abertas

- Q21-1: copiar o banco do painel web para fora da VPS todo dia (Object Storage)? Padrão até decidir: não.
