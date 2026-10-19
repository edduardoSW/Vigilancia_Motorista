# Site RotaGuard na VPS (spec 021). Contexto de build: esta pasta (site/).
#   docker build -t rotaguard-site:<commit> --build-arg NEXT_PUBLIC_ROTAGUARD_DOMINIO=https://rotaguard.acexpartners.com.br .
# Node 26.12.0: última estável conferida em nodejs.org em 19/10/2026, a mesma major usada no desenvolvimento (26.2.0).
FROM node:26.12.0-trixie-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

FROM node:26.12.0-trixie-slim AS build
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
ARG NEXT_PUBLIC_ROTAGUARD_DOMINIO=https://rotaguard.acexpartners.com.br
ARG NEXT_PUBLIC_ROTAGUARD_INDEXAR=0
ARG NEXT_PUBLIC_ROTAGUARD_WHATSAPP=
ARG NEXT_PUBLIC_ROTAGUARD_TELEFONE=
ENV NEXT_PUBLIC_ROTAGUARD_DOMINIO=$NEXT_PUBLIC_ROTAGUARD_DOMINIO \
    NEXT_PUBLIC_ROTAGUARD_INDEXAR=$NEXT_PUBLIC_ROTAGUARD_INDEXAR \
    NEXT_PUBLIC_ROTAGUARD_WHATSAPP=$NEXT_PUBLIC_ROTAGUARD_WHATSAPP \
    NEXT_PUBLIC_ROTAGUARD_TELEFONE=$NEXT_PUBLIC_ROTAGUARD_TELEFONE
COPY --from=deps /app/node_modules ./node_modules
# Os pacotes de download (155 MB) não entram no build: vão numa camada própria no fim.
COPY . .
RUN rm -rf public/downloads && npm run build

FROM node:26.12.0-trixie-slim AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000
COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static
COPY --from=build --chown=node:node /app/public ./public
# Por último: trocar só um .zip não refaz as camadas do site.
COPY --chown=node:node public/downloads ./public/downloads
USER node
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD node -e "fetch('http://127.0.0.1:3000/').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"
CMD ["node", "server.js"]
