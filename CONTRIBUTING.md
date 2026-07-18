# Contributing

Thanks for your interest in the Cyberyen explorer. Contributions of all kinds are welcome — bug reports, fixes, tests, documentation, and features.

## Ways to contribute

- **Report bugs** via [GitHub Issues](https://github.com/cykuza/explorer/issues). Include steps to reproduce, expected vs actual behavior, and relevant logs or environment details (network, OS, versions).
- **Suggest improvements** in an issue before large changes so we can align on design.
- **Open a pull request** against `master`. Prefer focused PRs with a clear description of *why* the change is needed.

## Development setup

**Prerequisites:** [uv](https://docs.astral.sh/uv/) (Python 3.14), [pnpm](https://pnpm.io/) 11+, Node.js 24 LTS, Docker Compose.

```bash
cp .env.example .env
docker compose -f deploy/compose.dev.yml up -d
cd backend && uv sync
cd ../web && pnpm install
```

See `.env.example` and the [README](README.md) for configuration. Technical notes for operators and developers live under [`docs/`](docs/).

## Backend (`backend/`)

```bash
cd backend
uv run ruff check
uv run ruff format --check
uv run mypy --strict src/
uv run pytest -m "not integration"   # unit tests
uv run pytest -m integration         # needs compose stack
```

Apply database migrations with `uv run alembic upgrade head` when the schema changes.

## Web (`web/`)

```bash
cd web
pnpm exec tsc --noEmit
pnpm next build
```

## Pull request checklist

- [ ] CI would pass locally (lint, types, tests for the area you touched)
- [ ] No secrets or real credentials — use `.env.example` as the template
- [ ] New behavior covered by tests when practical
- [ ] Docs updated if you change operator-facing setup or APIs

## Code of conduct

Be respectful and constructive. Assume good intent; focus feedback on the code and the problem.
