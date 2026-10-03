"""Command line entry point: start the RSS feed service."""

from __future__ import annotations

import logging
from pathlib import Path

import click
import uvicorn
from rich.logging import RichHandler

from sqlite_rss_logger.app import Settings, create_app

ENV = "SQLITE_RSS_LOGGER_"


# Implements REQ-042, REQ-044: tool command, Click options, environment variables.
@click.command()
@click.option(
    "--log-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default="logs",
    show_default=True,
    envvar=ENV + "LOG_DIR",
    show_envvar=True,
    help="Directory containing the <application>.db files.",
)
@click.option(
    "--host", default="127.0.0.1", show_default=True, envvar=ENV + "HOST", show_envvar=True
)
@click.option("--port", default=8000, show_default=True, envvar=ENV + "PORT", show_envvar=True)
@click.option(
    "--default-items",
    default=50,
    show_default=True,
    envvar=ENV + "DEFAULT_ITEMS",
    show_envvar=True,
    help="Items in the feed when no limit is requested.",
)
@click.option(
    "--max-items",
    default=500,
    show_default=True,
    envvar=ENV + "MAX_ITEMS",
    show_envvar=True,
    help="Largest limit a request may ask for.",
)
@click.option(
    "--token",
    default=None,
    envvar=ENV + "TOKEN",
    show_envvar=True,
    help="Require this token (?token=... or 'Authorization: Bearer ...'). Open if unset.",
)
@click.version_option(package_name="sqlite-rss-logger")
def main(
    log_dir: Path, host: str, port: int, default_items: int, max_items: int, token: str | None
) -> None:
    """Serve the latest log records from all application databases as an RSS feed."""
    logging.basicConfig(level=logging.INFO, format="%(message)s", handlers=[RichHandler()])
    if not log_dir.is_dir():
        logging.getLogger(__name__).warning("Log directory %s does not exist yet", log_dir)
    settings = Settings(
        log_dir=log_dir, default_items=default_items, max_items=max_items, token=token or None
    )
    uvicorn.run(create_app(settings), host=host, port=port, log_config=None)
