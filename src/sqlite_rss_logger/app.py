"""FastAPI application that publishes the latest log records as an RSS feed."""

from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request, Response

from sqlite_rss_logger.feed import DEFAULT_DESCRIPTION, DEFAULT_TITLE, render_rss
from sqlite_rss_logger.reader import latest_entries


# Implements REQ-031: all service settings are configuration.
@dataclass(frozen=True)
class Settings:
    log_dir: Path
    default_items: int = 50
    max_items: int = 500
    token: str | None = None
    title: str = DEFAULT_TITLE
    description: str = DEFAULT_DESCRIPTION


def _min_level(name: str) -> int:
    levels = logging.getLevelNamesMapping()
    try:
        return levels[name.upper()]
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Unknown level: {name}") from None


def _check_token(request: Request, query_token: str | None, expected: str) -> None:
    supplied = query_token
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        supplied = auth[7:].strip()
    if supplied is None or not secrets.compare_digest(supplied, expected):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def create_app(settings: Settings) -> FastAPI:
    """Build the feed service for the given settings."""
    app = FastAPI(title="sqlite-rss-logger")  # Implements REQ-020.

    # Implements REQ-021, REQ-029: read-only GET feed endpoint.
    @app.get("/rss")
    def rss(
        request: Request,
        apps: list[str] | None = Query(None, alias="app"),
        level: str = "NOTSET",
        limit: int | None = Query(None, ge=1),
        token: str | None = None,
    ) -> Response:
        if settings.token:  # Implements REQ-030: optional static token.
            _check_token(request, token, settings.token)
        count = min(limit or settings.default_items, settings.max_items)
        entries = latest_entries(
            settings.log_dir, count, applications=apps, min_level=_min_level(level)
        )
        return Response(
            render_rss(
                entries,
                link=str(request.url),
                title=settings.title,
                description=settings.description,
            ),
            media_type="application/rss+xml",
        )

    return app
