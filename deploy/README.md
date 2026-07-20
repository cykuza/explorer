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
NEXT_PUBLIC_NETWORKS=mainnet,testnet \
NEXT_PUBLIC_SITE_URL=https://cyberyen.work \
  pnpm build
# or: docker build -f deploy/docker/web.Dockerfile \
#       --build-arg NEXT_PUBLIC_NETWORKS=mainnet,testnet \
#       --build-arg NEXT_PUBLIC_SITE_URL=https://cyberyen.work .
```

`NEXT_PUBLIC_SITE_URL` sets the canonical origin for Open Graph / Twitter cards and JSON-LD (defaults to `https://cyberyen.work`).

Non-default networks are emitted under `/{network}/…` at build time from `NEXT_PUBLIC_NETWORKS` (first entry is the default and uses root paths). Default-network URLs under `/mainnet/…` are permanently redirected to `/…`.

## Production compose

Stack file: [`compose.prod.yml`](compose.prod.yml). Services: `cyberyend-mainnet`, `cyberyend-testnet`, `postgres`, `indexer-mainnet`, `indexer-testnet`, `miner-testnet`, `api`, `nginx`.

Images are pulled from GHCR (no local `build:`):

| Service | Image |
|---------|--------|
| `api`, `indexer-*`, `miner-testnet` | `ghcr.io/cykuza/explorer-backend:${EXPLORER_TAG:-latest}` |
| `nginx` | `ghcr.io/cykuza/explorer-web:${EXPLORER_TAG:-latest}` |
| `cyberyend-*` | `ghcr.io/cykuza/cyberyend:${CYBERYEND_TAG:-0.21.6.1}` |

### Env file

On the server the compose file and `.env.prod` live under `/opt/explorer/` (CD copies compose + nginx configs there over SSH). Locally:

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
| `EXPLORER_TAG` | Explorer backend/web image tag (default `latest`) |
| `CYBERYEND_TAG` | Cyberyend image tag (default `0.21.6.1`) |
| `EXPLORER_DB_STATEMENT_TIMEOUT_MS` | API read-engine `statement_timeout` (default 5000) |
| `EXPLORER_API_LIMIT_CONCURRENCY` | uvicorn `--limit-concurrency` (default 100) |
| `EXPLORER_API_MAX_LAG` | API tip lag budget |

### Bring-up order

1. Create and edit `.env.prod` as above (on the server: `/opt/explorer/.env.prod`).
2. Pull images and start the stack:

   ```bash
   cd /opt/explorer   # or from the repo: -f deploy/compose.prod.yml
   docker compose -f compose.prod.yml --env-file .env.prod pull
   docker compose -f compose.prod.yml --env-file .env.prod up -d
   ```

Each indexer runs `alembic upgrade head` for its schema (`EXPLORER_NETWORK` → schema name, unless `EXPLORER_DB_SCHEMA` is set) before `explorer sync`. The API process never migrates.

Resource notes (4 vCPU / 8 GB host): mainnet node `-dbcache=1536` / `-maxmempool=300`; testnet `-dbcache=384` / `-maxmempool=100`; Postgres `shared_buffers=256MB` (+ related knobs). P2P published (`58383`, `44551`); RPC stays on the Compose network only.

### Testnet miner

`miner-testnet` runs `explorer miner` against the testnet node RPC only (no Postgres). It refuses `EXPLORER_NETWORK=mainnet`.

Cyberyen testnet MWEB activates BIP8 height-based at **2880** (`3 × nMinerConfirmationWindow`, `960`). Consensus requires the first post-activation block to include ≥1 MWEB peg-in; without a peg-in in the mempool at the boundary, `generatetoaddress` fails with `bad-txns-vin-empty` (empty HogEx vin) and the chain stalls until a peg-in appears. A peg-in confirmed *before* tip `2879` is wasted.

The miner automates this:

1. **Bootstrap** while tip &lt; `activation + 100` (2980): mine in batches of 25 with `EXPLORER_MINER_BOOTSTRAP_SLEEP_SEC` (default 5s) between batches.
2. At tip `activation − 1`: submit an MWEB peg-in, verify it in `getrawmempool`, then mine the activation block. If mining fails with `bad-txns-vin-empty` (or the peg-in never lands in the mempool), it logs `miner_activation_stall`, submits a fresh peg-in, and retries with backoff — never exits.
3. **Steady** afterwards: one block per `EXPLORER_MINER_INTERVAL_SEC` (default 600s).

From genesis at defaults, bootstrap is roughly **10–15 minutes** of wall time (mostly sleep between ~120 batches to height 2980, plus CPU mining).

Testnet P2P **44551** is published; external peers are welcome, and external miners may join later. Our miner always follows whatever tip the node reports, so competing blocks are fine.

### Continuous deploy

On every push to `master`, CI runs the usual gates, then:

1. **`publish`** — buildx build+push `explorer-backend` and `explorer-web` to GHCR (`latest` + `${{ github.sha }}`). `cyberyend:0.21.6.1` is rebuilt only when `deploy/docker/cyberyend.Dockerfile` changes.
2. **`deploy`** — on master after publish: if required SSH secrets are set, `scp` compose/nginx/README to `/opt/explorer/`, then `pull` + `up -d` with `EXPLORER_TAG=<sha>`, then `docker image prune -af` and `docker builder prune -af` (unused artifacts only; volumes untouched), then `curl -fsS localhost/healthz` (10 attempts with backoff). If secrets are absent, the job still runs but skips deploy steps and succeeds. The host needs OpenSSH only (no `rsync` package).

### Server bootstrap (once)

Do this **before** enabling CD — avoid discovering blockers via Actions failures.

As root on the VPS (replace `deploy` with your SSH user if different):

```bash
# 1) Layout + ownership
sudo mkdir -p /opt/explorer
sudo chown -R deploy:deploy /opt/explorer

# 2) Secrets file (never commit; CD will not overwrite it)
sudo -u deploy cp /path/to/.env.prod.example /opt/explorer/.env.prod
sudo -u deploy nano /opt/explorer/.env.prod   # replace every CHANGE_ME
sudo -u deploy chmod 600 /opt/explorer/.env.prod

# 3) Docker access for the deploy user
sudo usermod -aG docker deploy   # then re-login

# 4) Free host ports this stack publishes (P2P + HTTP)
#    mainnet P2P 58383, testnet P2P 44551, nginx 80/443
ss -tlnp | grep -E ':58383|:44551|:80|:443'
# Stop any host Cyberyen / other stack using those ports before first deploy.
```

Checklist CD expects:

| Check | Why |
|-------|-----|
| `/opt/explorer` owned + writable by `DEPLOY_SSH_USER` | `scp` target |
| `/opt/explorer/.env.prod` exists, no `CHANGE_ME` | compose secrets |
| `docker` + Compose plugin; user in `docker` group | pull/up |
| Host ports **58383**, **44551**, **80**, **443** free (or already this stack) | cyberyend P2P + nginx bind |
| OpenSSH only (no `rsync` needed) | file copy |
| First deploy: use `skip_healthcheck` until IBD finishes and indexers catch tip | `/healthz` is **503** while `initialblockdownload` is true or lag exceeds budget |

Local check of preflight helpers (no Docker):

```bash
bash deploy/scripts/test_host_preflight.sh
# On the VPS (after files are present):
bash /opt/explorer/scripts/host-preflight.sh /opt/explorer
```

Required repository secrets (Settings → Secrets and variables → Actions):

| Secret | Purpose |
|--------|---------|
| `DEPLOY_SSH_HOST` | Server hostname or IP |
| `DEPLOY_SSH_USER` | SSH user (e.g. `deploy`) |
| `DEPLOY_SSH_KEY` | Private key for that user |
| `DEPLOY_SSH_PORT` | Optional. SSH port (default `22` when unset). Threaded into `scp -P`, `ssh -p`, and keyscan. |
| `DEPLOY_SSH_HOST_KEY` | Optional. Server’s `ssh-ed25519` public host key line (pinned into `known_hosts`). If unset, CD falls back to `ssh-keyscan` at deploy time. |

Pin the host key once (preferred): on a trusted machine run `ssh-keyscan -p <port> -t ed25519 <host>` (omit `-p` when using port 22), verify the fingerprint out-of-band against the server, then store that single line as `DEPLOY_SSH_HOST_KEY`. For a non-standard port, keyscan emits a **bracketed** line (`[host]:port ssh-ed25519 …`) — store that form verbatim; OpenSSH will not match a bare `host ssh-ed25519 …` entry when connecting on a non-22 port.

Images on GHCR may default to **private** on first publish. CD authenticates `docker pull` on the VPS with the job’s `GITHUB_TOKEN`. Optionally make packages public once (Package settings → Change visibility → Public) for each of `explorer-backend`, `explorer-web`, and `cyberyend` so anonymous pulls also work. The publish job attempts to set public via API when GitHub allows it.

**Tag scheme:** explorer images get `latest` and the git SHA. CD sets `EXPLORER_TAG=<sha>` on the compose command line without rewriting `.env.prod`. Cyberyend stays on `0.21.6.1` (`CYBERYEND_TAG`).

**Manual rollback** (CD prunes unused local images after a successful `up`; pull the prior SHA from GHCR):

```bash
cd /opt/explorer
EXPLORER_TAG=<previous_sha> docker compose -f compose.prod.yml --env-file .env.prod pull
EXPLORER_TAG=<previous_sha> docker compose -f compose.prod.yml --env-file .env.prod up -d
```

**First boot:** initial mainnet IBD and indexer backfill take hours. `/healthz` returns **503** while the node reports `initialblockdownload=true` **or** tip lag exceeds `EXPLORER_API_MAX_LAG`, so the deploy job’s healthcheck would fail. For the very first deploy, re-run the workflow via **Actions → CI → Run workflow** with **skip_healthcheck** enabled (or wait until IBD completes and lag is healthy, then re-run without skipping).

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
docker compose --env-file .env.prod -f compose.prod.yml \
  up -d --force-recreate nginx
```

Entrypoint (`deploy/nginx/docker-entrypoint.sh`): if `/etc/nginx/certs/{fullchain.pem,privkey.pem}` exist → enable TLS + HTTP→HTTPS redirect; otherwise stay HTTP-only (`nginx -t` still passes).

Renewal cron (host), roughly monthly:

```cron
0 3 1 * * docker run --rm \
  -v explorer_certbot-www:/var/www/certbot \
  -v explorer_certs_letsencrypt:/etc/letsencrypt \
  certbot/certbot renew \
  && docker compose --env-file /opt/explorer/.env.prod \
       -f /opt/explorer/compose.prod.yml exec nginx nginx -s reload
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

On a ~75 GB NVMe host, chainstate (mainnet + testnet with `txindex`) and Postgres will dominate growth. Monitor with `df -h` / `docker system df` and alert before free space drops under ~15–20%. CD already runs `docker image prune -af` / `docker builder prune -af` after each deploy; do not prune named volumes. Optional host-side Builder GC: `/etc/docker/daemon.json` → `builder.gc`.
