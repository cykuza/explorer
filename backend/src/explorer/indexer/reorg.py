"""Reorg fork-point detection (pure, no I/O)."""

from __future__ import annotations


class ReorgTooDeepError(Exception):
    """Raised when the fork is deeper than the configured max rollback depth."""

    def __init__(self, depth: int, max_depth: int) -> None:
        self.depth = depth
        self.max_depth = max_depth
        super().__init__(
            f"reorg depth {depth} exceeds max_reorg_depth {max_depth}",
        )


def find_fork_height(
    *,
    db_tip_height: int,
    stored_hash_at: dict[int, str],
    node_hash_at: dict[int, str],
    max_reorg_depth: int,
) -> int:
    """Return the highest height where DB and node hashes still agree.

    Walks downward from ``db_tip_height``. Raises ``ReorgTooDeepError`` if no
    common ancestor is found within ``max_reorg_depth`` steps (or at genesis).

    For height 0 mismatch, returns ``-1`` (rewind everything) if within depth.
    """
    if db_tip_height < 0:
        return -1

    depth = 0
    for height in range(db_tip_height, -1, -1):
        depth = db_tip_height - height
        if depth > max_reorg_depth:
            raise ReorgTooDeepError(depth, max_reorg_depth)
        stored = stored_hash_at.get(height)
        node = node_hash_at.get(height)
        if stored is not None and node is not None and stored == node:
            return height

    # Exhausted without a match — treat as full rewind if still within depth.
    depth = db_tip_height + 1
    if depth > max_reorg_depth:
        raise ReorgTooDeepError(depth, max_reorg_depth)
    return -1
