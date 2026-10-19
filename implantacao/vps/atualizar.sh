#!/usr/bin/env bash
# Troca a imagem de um serviço do RotaGuard para uma tag já construída na VPS e recria só aquele container.
# Se ele não ficar saudável em 90 s, volta sozinho para a tag anterior (spec 021, VPS-06).
#
#   ./atualizar.sh site <tag>       (em /root/rotaguard)
#   ./atualizar.sh central <tag>
set -euo pipefail
cd "$(dirname "$0")"

PARTE="${1:?informe site ou central}"
TAG="${2:?informe a tag (veja: docker images rotaguard-$PARTE)}"
case "$PARTE" in
  site) VARIAVEL=SITE_TAG ;;
  central) VARIAVEL=CENTRAL_TAG ;;
  *) echo "parte desconhecida: $PARTE (use site ou central)"; exit 2 ;;
esac
SERVICO="rotaguard_$PARTE"
docker image inspect "rotaguard-$PARTE:$TAG" > /dev/null
ANTERIOR="$(grep "^$VARIAVEL=" .env | cut -d= -f2- || true)"
PREFIXO="$(grep '^CONTAINER_PREFIXO=' .env | cut -d= -f2- || true)"
CONTAINER="${PREFIXO:-rotaguard}-$PARTE"

trocar_tag() {
  grep -v "^$VARIAVEL=" .env > .env.novo || true
  echo "$VARIAVEL=$1" >> .env.novo
  chmod 600 .env.novo
  mv .env.novo .env
  docker compose up -d "$SERVICO"
}

saudavel() {
  for _ in $(seq 1 30); do
    [ "$(docker inspect -f '{{.State.Health.Status}}' "$CONTAINER" 2>/dev/null)" = healthy ] && return 0
    sleep 3
  done
  return 1
}

echo "== $PARTE: ${ANTERIOR:-nenhuma} -> $TAG"
trocar_tag "$TAG"
if saudavel; then
  echo "OK: rotaguard-$PARTE:$TAG no ar ($CONTAINER)"
  exit 0
fi

echo "!! $TAG não ficou saudável. Últimas linhas do log:"
docker logs "$CONTAINER" --tail 40 || true
if [ -z "$ANTERIOR" ]; then
  echo "!! não havia tag anterior para voltar"
  exit 1
fi
echo "== voltando para $ANTERIOR"
trocar_tag "$ANTERIOR"
saudavel && echo "voltou para $ANTERIOR" || echo "!! $ANTERIOR também não ficou saudável: olhar os logs"
exit 1
