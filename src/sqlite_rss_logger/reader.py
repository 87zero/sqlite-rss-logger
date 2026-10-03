"""Read the latest log records from all application databases in a directory.

Use case: the feed service needs the newest records across every
``<application>.db`` file. Databases are opened read-only and never modified.

Standard library only.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

_QUERY = (
    "SELECT id, created, level, levelno, logger, message, traceback FROM logs "
    "WHERE levelno >= ? ORDER BY created DESC, id DESC LIMIT ?"
)


@dataclass(frozen=True)
class LogEntry:
    """One log record together with the application it came from."""

    application: str
    id: int
    created: str
    level: str
    levelno: int
    logger: str
    message: str
    traceback: str | None


def _connect_readonly(db_path: Path) -> sqlite3.Connection:
    # Implements REQ-027: read-only access.
    return sqlite3.connect(f"{db_path.resolve().as_uri()}?mode=ro", uri=True, timeout=5)


def list_applications(log_dir: Path) -> list[str]:
    """Return application names (database filename stems) found in ``log_dir``."""
    # Implements REQ-022: discovery by scanning, on every call (no restart needed).
    if not log_dir.is_dir():
        return []
    return sorted(p.stem for p in log_dir.glob("*.db") if p.is_file())


def latest_entries(
    log_dir: Path,
    limit: int,
    applications: list[str] | None = None,
    min_level: int = logging.NOTSET,
) -> list[LogEntry]:
    """Return the newest ``limit`` entries across all databases, newest first.

    Args:
        log_dir: Directory holding the ``<application>.db`` files.
        limit: Maximum number of entries to return.
        applications: Only read these applications; ``None`` reads all.
        min_level: Minimum numeric level (for example ``logging.WARNING``).

    A database that is missing, locked, corrupt or has an unexpected schema is
    skipped with a warning instead of failing the whole call.
    """
    entries: list[LogEntry] = []
    for application in list_applications(log_dir):
        if applications and application not in applications:
            continue
        db_path = log_dir / f"{application}.db"
        conn = None
        try:
            conn = _connect_readonly(db_path)
            rows = conn.execute(_QUERY, (min_level, limit)).fetchall()
        except sqlite3.Error as exc:
            # Implements REQ-028: skip a bad database, keep serving the rest.
            log.warning("Skipping %s: %s", db_path.name, exc)
            continue
        finally:
            if conn is not None:
                conn.close()
        entries.extend(LogEntry(application, *row) for row in rows)
    # Implements REQ-023, REQ-024: merge, newest first, latest N.
    entries.sort(key=lambda e: (e.created, e.application, e.id), reverse=True)
    return entries[:limit]
