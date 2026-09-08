FROM node:24.20.0-alpine3.24 AS web-build
WORKDIR /build/web
COPY web/package.json web/package-lock.json ./
RUN npm ci --ignore-scripts --no-audit --no-fund
COPY web/ ./
RUN npm run build

FROM caddy:2.11.4-alpine
COPY --from=web-build /build/web/dist /srv
COPY deploy/caddy/Caddyfile /etc/caddy/Caddyfile
