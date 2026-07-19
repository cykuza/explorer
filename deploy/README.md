# Deploy

## Local compose

Start the Cyberyen regtest node and PostgreSQL:

```bash
docker compose -f deploy/compose.dev.yml up -d
```

Start the API as well (profile `api`, host port **8080**):

```bash
docker compose -f deploy/compose.dev.yml --profile api up -d
```

## Production static web + nginx

The web UI is a Next.js static export (`web/out`). Entity pages are shell HTML files (`block.html`, `tx.html`, `address.html`) that read the entity id from `location.pathname`. Pretty URLs must be rewritten to those shells.

Same-origin API: proxy `/api/` and `/healthz` to the explorer API process.

Example nginx map (adapt `root` and upstream):

```nginx
upstream explorer_api {
    server 127.0.0.1:8080;
}

server {
    listen 80;
    server_name explorer.example;
    root /var/www/explorer;
    index index.html;

    # Pretty entity URLs → static shell pages (default network)
    location ~ ^/(block|tx|address)/[^/]+/?$ {
        rewrite ^/(block|tx|address)/[^/]+/?$ /$1.html last;
    }

    # Network-prefixed pretty entity URLs → /{network}/{entity}.html
    location ~ ^/(mainnet|testnet|regtest)/(block|tx|address)/[^/]+/?$ {
        rewrite ^/(mainnet|testnet|regtest)/(block|tx|address)/[^/]+/?$ /$1/$2.html last;
    }

    location /api/ {
        proxy_pass http://explorer_api;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location = /healthz {
        proxy_pass http://explorer_api;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }

    location / {
        try_files $uri $uri.html $uri/index.html =404;
    }
}
```

Build the web bundle with the production network list, e.g.:

```bash
cd web
NEXT_PUBLIC_NETWORKS=mainnet,testnet pnpm build
# publish web/out to the nginx root
```

Non-default networks are emitted under `/{network}/…` at build time from `NEXT_PUBLIC_NETWORKS` (first entry is the default and uses root paths).
