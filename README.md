# Cyberyen Explorer

Block explorer for the [Cyberyen](https://cyberyen.org) blockchain — indexer, API, and static web UI.

Repository: [cykuza/explorer](https://github.com/cykuza/explorer).

## Run locally

**Prerequisites:** [uv](https://docs.astral.sh/uv/) (Python 3.14), [pnpm](https://pnpm.io/) 11+, Node.js 24 LTS, Docker Compose.

```bash
cp .env.example .env
docker compose -f deploy/compose.dev.yml up -d
```

Starts a Cyberyen Core regtest node and PostgreSQL 18. Regtest RPC credentials are throwaway `dev` / `dev`.

```bash
cd backend && uv sync && uv run pytest
cd ../web && pnpm install && pnpm next build
```

See `.env.example` for configuration.

## Development

Start Postgres + regtest node, then the API (port 8080):

```bash
docker compose -f deploy/compose.dev.yml --profile api up -d
```

Run the web UI (dev server proxies `/api/*` and `/healthz` to `127.0.0.1:8080`, and pretty entity URLs to shell pages):

```bash
cd web
pnpm install
pnpm dev
```

`NEXT_PUBLIC_NETWORKS` is a comma-separated list (first entry is the default network at root paths). When unset, it defaults to `regtest`.

Regenerate TypeScript types from the live OpenAPI document (API must be up):

```bash
cd web && pnpm gen:api
```

Typecheck / production static export:

```bash
cd web && pnpm typecheck && pnpm build
```

Deploy notes (nginx rewrite map for shell pages): [`deploy/README.md`](deploy/README.md).

## Documentation

Operator and developer notes: [`docs/`](docs/).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Issues and pull requests are welcome.
