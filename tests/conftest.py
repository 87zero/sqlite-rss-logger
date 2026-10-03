import logging
import sqlite3
from pathlib import Path

import pytest

from sqlite_rss_logger import SQLiteHandler


def write_record(
    handler: SQLiteHandler,
    message: str,
    created: float,
    level: int = logging.INFO,
    name: str = "test",
) -> None:
    """Emit one record with a fixed timestamp through ``handler``."""
    record = logging.makeLogRecord(
        {
            "msg": message,
            "levelno": level,
            "levelname": logging.getLevelName(level),
            "name": name,
            "created": created,
        }
    )
    handler.handle(record)


@pytest.fixture
def log_dir(tmp_path: Path) -> Path:
    return tmp_path / "logs"


@pytest.fixture
def make_handler(log_dir: Path):
    handlers: list[SQLiteHandler] = []

    def _make(application: str) -> SQLiteHandler:
        handler = SQLiteHandler(application, log_dir=log_dir)
        handlers.append(handler)
        return handler

    yield _make
    for handler in handlers:
        handler.close()


def count_rows(db_path: Path) -> int:
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute("SELECT COUNT(*) FROM logs").fetchone()[0]
    finally:
        conn.close()
