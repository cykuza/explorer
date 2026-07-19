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

Canonical nginx configs live in [`deploy/nginx/`](nginx/) (baked into the web image; see also the rate-limit / cache / SSE settings there). Build args:

```bash
cd web
NEXT_PUBLIC_NETWORKS=mainnet,testnet pnpm build
# or: docker build -f deploy/docker/web.Dockerfile --build-arg NEXT_PUBLIC_NETWORKS=mainnet,testnet .
```

Non-default networks are emitted under `/{network}/…` at build time from `NEXT_PUBLIC_NETWORKS` (first entry is the default and uses root paths). Default-network URLs under `/mainnet/…` are permanently redirected to `/…`.

## Production compose

Stack file: [`compose.prod.yml`](compose.prod.yml). Services: `cyberyend-mainnet`, `cyberyend-testnet`, `postgres`, `indexer-mainnet`, `indexer-testnet`, `api`, `nginx`.

### Env file

```bash
cp deploy/.env.prod.example deploy/.env.prod
# edit CHANGE_ME secrets (Postgres + RPC passwords)
```

Never commit `.env.prod`. Pass it explicitly so Compose interpolates `${…}` in the compose file:

```bash
docker compose --env-file deploy/.env.prod -f deploy/compose.prod.yml …
```

| Variable | Purpose |
|----------|---------|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Postgres + API/indexer DB URL |
| `CYBERYEN_RPC_USER` / `CYBERYEN_RPC_PASSWORD` | Node RPC (both networks) |
| `EXPLORER_DB_STATEMENT_TIMEOUT_MS` | API read-engine `statement_timeout` (default 5000) |
| `EXPLORER_API_LIMIT_CONCURRENCY` | uvicorn `--limit-concurrency` (default 100) |
| `EXPLORER_API_MAX_LAG` | API tip lag budget |

### Bring-up order

1. Create and edit `.env.prod` as above.
2. Start nodes + Postgres (indexed volumes, no public RPC ports):

   ```bash
   docker compose --env-file deploy/.env.prod -f deploy/compose.prod.yml \
     up -d cyberyend-mainnet cyberyend-testnet postgres
   ```

3. Apply migrations for both schemas (use the indexer services — they already
   have full `Settings` env; schema defaults to `EXPLORER_NETWORK`):

   ```bash
   docker compose --env-file deploy/.env.prod -f deploy/compose.prod.yml run --rm \
     indexer-mainnet alembic upgrade head

   docker compose --env-file deploy/.env.prod -f deploy/compose.prod.yml run --rm \
     indexer-testnet alembic upgrade head
   ```

4. Start indexers, API, and nginx:

   ```bash
   docker compose --env-file deploy/.env.prod -f deploy/compose.prod.yml up -d
   ```

Resource notes (4 vCPU / 8 GB host): mainnet node `-dbcache=1536` / `-maxmempool=300`; testnet `-dbcache=384` / `-maxmempool=100`; Postgres `shared_buffers=256MB` (+ related knobs). P2P published (`58383`, `44551`); RPC stays on the Compose network only.

### TLS bootstrap (certbot webroot)

While nginx is in HTTP-only mode (empty `certs` volume):

```bash
# Obtain cert (example for cyberyen.work); writes into the certbot-www volume
docker run --rm -it \
  -v "$(docker volume ls -q | grep certbot-www | head -1)":/var/www/certbot \
  -v "$(docker volume ls -q | grep _certs$ | head -1)":/etc/letsencrypt \
  certbot/certbot certonly --webroot -w /var/www/certbot \
  -d cyberyen.work --email you@example.com --agree-tos --no-eff-email

# Copy live certs into the nginx certs volume layout expected by entrypoint
# (fullchain.pem + privkey.pem at volume root), then recreate nginx so the
# entrypoint switches from HTTP-only to HTTPS + redirect:
docker compose --env-file deploy/.env.prod -f deploy/compose.prod.yml \
  up -d --force-recreate nginx
```

Entrypoint (`deploy/nginx/docker-entrypoint.sh`): if `/etc/nginx/certs/{fullchain.pem,privkey.pem}` exist → enable TLS + HTTP→HTTPS redirect; otherwise stay HTTP-only (`nginx -t` still passes).

Renewal cron (host), roughly monthly:

```cron
0 3 1 * * docker run --rm \
  -v explorer_certbot-www:/var/www/certbot \
  -v explorer_certs_letsencrypt:/etc/letsencrypt \
  certbot/certbot renew \
  && docker compose --env-file /opt/explorer/deploy/.env.prod \
       -f /opt/explorer/deploy/compose.prod.yml exec nginx nginx -s reload
```

(After the *first* cert install, recreate nginx once so the entrypoint enables the TLS server block; subsequent renewals only need `nginx -s reload` if the PEM paths are unchanged.)

### fail2ban (host)

Example jail watching nginx access logs for 429/404 floods (requires publishing or bind-mounting nginx logs to the host):

```ini
# /etc/fail2ban/filter.d/nginx-limiter.conf
[Definition]
failregex = ^<HOST> .* "(GET|POST|HEAD).*" (429|404)
ignoreregex =

# /etc/fail2ban/jail.d/nginx-limiter.local
[nginx-limiter]
enabled = true
port = http,https
filter = nginx-limiter
logpath = /var/log/nginx/access.log
maxretry = 60
findtime = 60
bantime = 3600
```

### Disk watch

On a ~75 GB NVMe host, chainstate (mainnet + testnet with `txindex`) and Postgres will dominate growth. Monitor with `df -h` / `docker system df` and alert before free space drops under ~15–20%. Prune unused images after upgrades; do not prune named volumes.
