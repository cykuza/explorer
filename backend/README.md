# Explorer backend

Python package for the Cyberyen explorer indexer and FastAPI surface.

## Setup

Requires Python 3.14 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run pytest
```

Monorepo quick start (Compose, env, web UI): see the [repository README](../README.md).

## Layout

- `src/explorer/` — indexer, API routes, models, settings
- `migrations/` — Alembic schema migrations
- `tests/` — unit and integration tests
