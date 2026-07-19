"""Run Alembic migrations for the indexer schema (EXPLORER_DB_SCHEMA / network)."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

_ALEMBIC_INI_NAMES = ("alembic.ini",)


def _find_alembic_ini(start: Path | None = None) -> Path:
    """Resolve alembic.ini from cwd (Docker /app, local backend/)."""
    cwd = (start or Path.cwd()).resolve()
    for name in _ALEMBIC_INI_NAMES:
        candidate = cwd / name
        if candidate.is_file():
            return candidate
    msg = f"alembic.ini not found in {cwd}"
    raise FileNotFoundError(msg)


def upgrade_head(*, ini_path: Path | None = None) -> None:
    """Apply pending migrations to head for the current Settings schema."""
    path = ini_path if ini_path is not None else _find_alembic_ini()
    cfg = Config(str(path))
    command.upgrade(cfg, "head")
