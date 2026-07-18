"""Static check: api package must not write to the database."""

from __future__ import annotations

import ast
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1] / "src" / "explorer" / "api"

# Tokens that indicate SQLAlchemy write usage in source text.
FORBIDDEN_SUBSTRINGS = (
    ".insert(",
    ".update(",
    ".delete(",
    "pg_insert",
    "begin(",
)


def test_api_sources_contain_no_write_statements() -> None:
    offenders: list[str] = []
    for path in sorted(API_ROOT.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        # AST parse ensures files are valid Python.
        ast.parse(source, filename=str(path))
        for token in FORBIDDEN_SUBSTRINGS:
            if token in source:
                offenders.append(f"{path.relative_to(API_ROOT.parent.parent)}: {token}")
    assert not offenders, "api module must be read-only:\n" + "\n".join(offenders)
