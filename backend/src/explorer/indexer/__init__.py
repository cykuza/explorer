"""Block indexer: apply blocks, handle reorgs, sync via RPC+ZMQ."""

from __future__ import annotations

from explorer.indexer.sync import Syncer, run_sync

__all__ = ["Syncer", "run_sync"]
