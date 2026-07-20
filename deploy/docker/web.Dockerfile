# Production web (Next.js static export) + nginx front door.
# Build from repo root:
#   docker build -f deploy/docker/web.Dockerfile \
#     --build-arg NEXT_PUBLIC_NETWORKS=mainnet,testnet \
#     --build-arg NEXT_PUBLIC_SITE_URL=https://cyberyen.work .

# Node 24 (multi-arch index digest)
FROM node@sha256:5711a0d445a1af54af9589066c646df387d1831a608226f4cd694fc59e745059 AS build

WORKDIR /app
RUN corepack enable

COPY web/package.json web/pnpm-lock.yaml web/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

COPY web/ ./

ARG NEXT_PUBLIC_NETWORKS=mainnet,testnet
ENV NEXT_PUBLIC_NETWORKS=${NEXT_PUBLIC_NETWORKS}
ARG NEXT_PUBLIC_SITE_URL=https://cyberyen.work
ENV NEXT_PUBLIC_SITE_URL=${NEXT_PUBLIC_SITE_URL}
RUN pnpm build

# nginx:stable-alpine (multi-arch index digest)
FROM nginx@sha256:97d490c12ba55b4946b01546d1c3ed324e8d41ab1c9fcb2a616aa470620e5b46

COPY deploy/nginx/nginx.conf /etc/nginx/nginx.conf
COPY deploy/nginx/includes /etc/nginx/includes
COPY deploy/nginx/templates /etc/nginx/templates
COPY deploy/nginx/docker-entrypoint.sh /docker-entrypoint-explorer.sh

COPY --from=build /app/out /usr/share/nginx/html

RUN chmod +x /docker-entrypoint-explorer.sh \
    && mkdir -p /var/cache/nginx/api /var/www/certbot /etc/nginx/certs \
    && rm -f /etc/nginx/conf.d/default.conf

EXPOSE 80 443
ENTRYPOINT ["/docker-entrypoint-explorer.sh"]
CMD ["nginx", "-g", "daemon off;"]
