#!/usr/bin/env bash
# Roda NESTE computador (Git Bash): empacota o código, envia para a VPS e constrói a imagem lá, com prioridade baixa
# para não pesar nos outros sites. Depois, na VPS: ./atualizar.sh <parte> <tag>.
#
#   implantacao/vps/enviar.sh site          # site/ (inclui public/downloads, fora do git)
#   implantacao/vps/enviar.sh central       # servidor/ (central de dados, spec 026)
#   VPS=root@187.127.41.22 implantacao/vps/enviar.sh site
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$RAIZ"

PARTE="${1:?informe site ou central}"
VPS="${VPS:-root@187.127.41.22}"
# Código sem commit leva "-local-<mês dia hora minuto>": tags iguais impediriam o atualizar.sh de voltar à anterior.
MUDANCAS="$(git status --porcelain -- site servidor implantacao)"
TAG="$(git rev-parse --short HEAD)$( [ -z "$MUDANCAS" ] || date +-local-%m%d%H%M)"
DESTINO="/root/rotaguard/fonte-$PARTE"

case "$PARTE" in
  site)
    tar -czf - --exclude=node_modules --exclude=.next --exclude=out --exclude='*.log' --exclude='*.tsbuildinfo' \
      --exclude='.env*' site \
      | ssh "$VPS" "rm -rf '$DESTINO' && mkdir -p '$DESTINO' && tar -xzf - -C '$DESTINO'"
    ssh "$VPS" "cd '$DESTINO/site' && nice -n 15 docker build -t 'rotaguard-site:$TAG' ." ;;
  central)
    tar -czf - --exclude=__pycache__ servidor painel/webapp implantacao/Dockerfile.servidor \
      | ssh "$VPS" "rm -rf '$DESTINO' && mkdir -p '$DESTINO' && tar -xzf - -C '$DESTINO'"
    ssh "$VPS" "cd '$DESTINO' && nice -n 15 docker build -f implantacao/Dockerfile.servidor -t 'rotaguard-central:$TAG' ." ;;
  *) echo "parte desconhecida: $PARTE"; exit 2 ;;
esac
# A cópia do código só serve ao build (o site leva 363 MB por causa dos downloads): o disco da VPS é dividido com
# outros sites.
ssh "$VPS" "rm -rf '$DESTINO'"
echo "Imagem rotaguard-$PARTE:$TAG pronta na VPS. Para pôr no ar: ssh $VPS 'cd /root/rotaguard && ./atualizar.sh $PARTE $TAG'"
