"""Render log entries as an RSS 2.0 document using the Jinja template."""

from __future__ import annotations

import html
import re
from datetime import UTC, datetime
from email.utils import format_datetime
from urllib.parse import urlsplit, urlunsplit

from jinja2 import Environment, PackageLoader

from sqlite_rss_logger.reader import LogEntry

_env = Environment(
    loader=PackageLoader("sqlite_rss_logger", "templates"),
    autoescape=True,
    trim_blocks=True,
)

_INVALID_XML = re.compile("[^\x09\x0a\x0d\x20-퟿-�\U00010000-\U0010ffff]")
_TITLE_LENGTH = 80

DEFAULT_TITLE = "Application logs"
DEFAULT_DESCRIPTION = "Latest log records from all applications"


def _clean(text: str) -> str:
    """Remove characters that are not allowed in XML 1.0."""
    return _INVALID_XML.sub("", text)


def _item(entry: LogEntry, base_link: str) -> dict[str, str]:
    summary = _clean(entry.message).strip().splitlines()[0] if entry.message.strip() else ""
    if len(summary) > _TITLE_LENGTH:
        summary = summary[: _TITLE_LENGTH - 3] + "..."
    body = _clean(entry.message)
    if entry.traceback:
        body += "\n\n" + _clean(entry.traceback)
    created = datetime.fromisoformat(entry.created)
    guid = f"{entry.application}-{entry.id}"
    return {
        # Implements REQ-025: title, link, description, date and stable GUID.
        "title": f"[{entry.level}] {entry.application}: {summary}",
        # Unique per item; some readers hide or merge items without distinct links.
        "link": f"{base_link}#{guid}",
        # Escaped twice on purpose: RSS 2.0 descriptions are HTML carried as XML text.
        # html.escape() makes the log text safe HTML; Jinja autoescape then encodes that
        # HTML for the XML. Readers undo both layers. Do not mark this Markup/|safe.
        "description": f"<pre>{html.escape(body)}</pre>",
        "pub_date": format_datetime(created),
        "guid": guid,
        "level": entry.level,
    }


def render_rss(
    entries: list[LogEntry],
    link: str,
    title: str = DEFAULT_TITLE,
    description: str = DEFAULT_DESCRIPTION,
) -> str:
    """Return an RSS 2.0 document for ``entries`` (already ordered newest first).

    ``title`` and ``description`` are the channel's title and description.

    ``link`` is the URL the feed was requested at. It is used as-is for the
    ``rel="self"`` link. The channel and item links drop the query string and
    fragment, so a token in the URL never appears in them.
    """
    parts = urlsplit(link)
    base_link = urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
    return _env.get_template("rss.xml.j2").render(
        title=_clean(title),
        link=base_link,
        self_link=link,
        description=_clean(description),
        build_date=format_datetime(datetime.now(UTC)),
        items=[_item(e, base_link) for e in entries],
    )
