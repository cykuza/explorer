"""CLI entry point: ``explorer sync`` / ``explorer api`` / ``explorer --version``."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from explorer import __version__
from explorer.config import Settings
from explorer.logging_setup import configure_logging


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="explorer")
    parser.add_argument(
        "--version",
        action="version",
        version=f"explorer {__version__}",
    )
    sub = parser.add_subparsers(dest="command")
    sync_parser = sub.add_parser("sync", help="Run the block indexer")
    sync_parser.add_argument(
        "--once",
        action="store_true",
        help="Backfill to tip and exit (no ZMQ/poll loop)",
    )
    api_parser = sub.add_parser("api", help="Run the read-only REST API")
    api_parser.add_argument("--host", default=None, help="Bind host (default EXPLORER_API_HOST)")
    api_parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Bind port (default EXPLORER_API_PORT)",
    )

    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    if args.command == "sync":
        configure_logging(logging.INFO)
        settings = Settings()  # type: ignore[call-arg]
        from explorer.indexer.sync import run_sync

        try:
            asyncio.run(run_sync(settings, once=bool(args.once)))
        except KeyboardInterrupt:
            return 130
        return 0
    if args.command == "api":
        configure_logging(logging.INFO)
        from explorer.api.app import create_app
        from explorer.api.settings import ApiSettings

        api_settings = ApiSettings()  # type: ignore[call-arg]
        host = args.host if args.host is not None else api_settings.api_host
        port = args.port if args.port is not None else api_settings.api_port
        app = create_app(api_settings)
        import uvicorn

        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info",
            limit_concurrency=api_settings.api_limit_concurrency,
        )
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
