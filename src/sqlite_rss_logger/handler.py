"""A logging handler that writes records to a per-application SQLite database.

Use case: attach ``SQLiteHandler`` to the standard ``logging`` module so each
application keeps its own log database (``<log_dir>/<application>.db``).

Standard library only. The feed service reads these databases; the schema is
defined here and shared with ``reader.py``.

Example:
    >>> import logging
    >>> from sqlite_rss_logger import SQLiteHandler
    >>> logging.getLogger().addHandler(SQLiteHandler("my-app", log_dir="logs"))
"""

from __future__ import annotations

import logging
import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS logs (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    created   TEXT    NOT NULL,
    level     TEXT    NOT NULL,
    levelno   INTEGER NOT NULL,
    logger    TEXT    NOT NULL,
    message   TEXT    NOT NULL,
    traceback TEXT
);
CREATE INDEX IF NOT EXISTS idx_logs_created ON logs (created);
"""

INSERT = (
    "INSERT INTO logs (created, level, levelno, logger, message, traceback) "
    "VALUES (?, ?, ?, ?, ?, ?)"
)

_APPLICATION_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")

# Implements REQ-001: standard logging.Handler subclass.
class SQLiteHandler(logging.Handler):
    """Write log records to ``<log_dir>/<application>.db``.

    Args:
        application: Application name; becomes the database filename. Letters,
            digits, ``.``, ``_`` and ``-`` only, starting with a letter or digit.
        log_dir: Directory for the database file. Created if missing.
        level: Minimum level handled by this handler.

    Threads share one connection under the handler lock. Several processes may
    write to the same database (WAL mode with a busy timeout), but each process
    must create its own handler; do not share one across ``fork``.
    """

    def __init__(
        self,
        application: str,
        log_dir: str | Path = "logs",
        level: int = logging.NOTSET,
    ) -> None:
        super().__init__(level)
        if not _APPLICATION_NAME.fullmatch(application):
            raise ValueError(f"Invalid application name: {application!r}")
        self.application = application
        # Implements REQ-002, REQ-003, REQ-004: one DB per application in a configurable dir.
        self.db_path = Path(log_dir) / f"{application}.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = sqlite3.connect(
            self.db_path, timeout=30, check_same_thread=False
        )
        # Implements REQ-009: safe concurrent writers.
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA busy_timeout=30000")
        # Implements REQ-005, REQ-010: create schema and timestamp index.
        self._conn.executescript(SCHEMA)
        self._conn.commit()
        self._formatter = logging.Formatter()

    def emit(self, record: logging.LogRecord) -> None:
        # Implements REQ-007, REQ-008: commit each record; never raise into the app.
        try:
            if self._conn is None:
                raise sqlite3.ProgrammingError("handler is closed")
            traceback = None
            if record.exc_info:
                traceback = self._formatter.formatException(record.exc_info)
            elif record.exc_text:
                traceback = record.exc_text
            created = datetime.fromtimestamp(record.created, UTC).isoformat(timespec="microseconds")
            self._conn.execute(
                INSERT,
                (
                    created,
                    record.levelname,
                    record.levelno,
                    record.name,
                    record.getMessage(),
                    traceback,
                ),
            )
            self._conn.commit()
        except Exception:
            self.handleError(record)

    def close(self) -> None:
        self.acquire()
        try:
            if self._conn is not None:
                self._conn.close()
                self._conn = None
        finally:
            self.release()
        super().close()
