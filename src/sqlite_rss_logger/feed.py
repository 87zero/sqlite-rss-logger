"""Render log entries as an RSS 2.0 document using the Jinja template."""

from __future__ import annotations

import html
import re
from datetime import UTC, datetime
from email.utils import format_datetime

from jinja2 import Environment, PackageLoader

from sqlite_rss_logger.reader import LogEntry

_env = Environment(
    loader=PackageLoader("sqlite_rss_logger", "templates"),
    autoescape=True,
    trim_blocks=True,
)

_INVALID_XML = re.compile("[^\x09\x0a\x0d\x20-퟿-�\U00010000-\U0010ffff]")
_TITLE_LENGTH = 80


def _clean(text: str) -> str:
    """Remove characters that are not allowed in XML 1.0."""
    return _INVALID_XML.sub("", text)


def _item(entry: LogEntry) -> dict[str, str]:
    summary = _clean(entry.message).strip().splitlines()[0] if entry.message.strip() else ""
    if len(summary) > _TITLE_LENGTH:
        summary = summary[: _TITLE_LENGTH - 3] + "..."
    body = _clean(entry.message)
    if entry.traceback:
        body += "\n\n" + _clean(entry.traceback)
    created = datetime.fromisoformat(entry.created)
    return {
        # Implements REQ-025: title, description, date and stable GUID.
        "title": f"[{entry.level}] {entry.application}: {summary}",
        "description": f"<pre>{html.escape(body)}</pre>",
        "pub_date": format_datetime(created),
        "guid": f"{entry.application}-{entry.id}",
        "level": entry.level,
    }


def render_rss(entries: list[LogEntry], link: str) -> str:
    """Return an RSS 2.0 document for ``entries`` (already ordered newest first)."""
    return _env.get_template("rss.xml.j2").render(
        title="Application logs",
        link=link,
        description="Latest log records from all applications",
        build_date=format_datetime(datetime.now(UTC)),
        items=[_item(e) for e in entries],
    )
