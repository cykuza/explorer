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

## Documentation

Operator and developer notes: [`docs/`](docs/).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Issues and pull requests are welcome.
