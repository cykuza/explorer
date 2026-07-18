# Explorer API / indexer image (Python 3.14 + uv)
# Build from repo root: docker build -f deploy/docker/explorer.Dockerfile .
FROM python:3.14-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# hatchling resolves readme relative to pyproject.toml → ../README.md
COPY README.md /README.md

WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
COPY backend/src ./src
COPY backend/migrations ./migrations
COPY backend/alembic.ini ./

RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8080
CMD ["explorer", "api"]
