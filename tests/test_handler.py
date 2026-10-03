"""Tests for SQLiteHandler (REQ-001 to REQ-010)."""

import logging
import sqlite3
import threading

import pytest

from conftest import count_rows, write_record
from sqlite_rss_logger import SQLiteHandler


def test_is_logging_handler():
    """REQ-001."""
    assert issubclass(SQLiteHandler, logging.Handler)


def test_creates_database_and_schema(log_dir, make_handler):
    """REQ-003, REQ-004, REQ-005, REQ-010."""
    handler = make_handler("web")
    assert handler.db_path == log_dir / "web.db"
    conn = sqlite3.connect(handler.db_path)
    indexes = [r[1] for r in conn.execute("PRAGMA index_list(logs)")]
    conn.close()
    assert "idx_logs_created" in indexes


def test_separate_database_per_application(log_dir, make_handler):
    """REQ-002."""
    write_record(make_handler("a"), "one", 1.0)
    write_record(make_handler("b"), "two", 2.0)
    assert count_rows(log_dir / "a.db") == 1
    assert count_rows(log_dir / "b.db") == 1


def test_record_fields(log_dir, make_handler):
    """REQ-006."""
    handler = make_handler("web")
    logger = logging.getLogger("record-fields")
    logger.propagate = False
    logger.addHandler(handler)
    try:
        try:
            raise ValueError("boom")
        except ValueError:
            logger.exception("failed %s", "badly")
    finally:
        logger.removeHandler(handler)
    conn = sqlite3.connect(handler.db_path)
    created, level, levelno, name, message, tb = conn.execute(
        "SELECT created, level, levelno, logger, message, traceback FROM logs"
    ).fetchone()
    conn.close()
    assert created.endswith("+00:00")
    assert (level, levelno, name) == ("ERROR", logging.ERROR, "record-fields")
    assert message == "failed badly"
    assert "ValueError: boom" in tb


def test_record_without_exception_has_no_traceback(log_dir, make_handler):
    handler = make_handler("web")
    write_record(handler, "fine", 1.0)
    conn = sqlite3.connect(handler.db_path)
    assert conn.execute("SELECT traceback FROM logs").fetchone()[0] is None
    conn.close()


def test_record_is_durable_without_close(log_dir, make_handler):
    """REQ-007: a second connection sees the record before the handler closes."""
    handler = make_handler("web")
    write_record(handler, "kept", 1.0)
    assert count_rows(handler.db_path) == 1


def test_write_failure_does_not_raise(make_handler):
    """REQ-008."""
    handler = make_handler("web")
    errors = []
    handler.handleError = errors.append
    handler.close()
    write_record(handler, "lost", 1.0)
    assert len(errors) == 1


@pytest.mark.parametrize("name", ["", "../evil", "a/b", ".hidden", "with space"])
def test_invalid_application_name(log_dir, name):
    with pytest.raises(ValueError):
        SQLiteHandler(name, log_dir=log_dir)


def test_threads_write_safely(log_dir, make_handler):
    """REQ-009."""
    handler = make_handler("web")

    def work(n):
        for i in range(25):
            write_record(handler, f"{n}-{i}", float(n * 100 + i))

    threads = [threading.Thread(target=work, args=(n,)) for n in range(4)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert count_rows(handler.db_path) == 100


def test_two_handlers_same_database(log_dir, make_handler):
    """REQ-009: two writers (as two processes would be) share one file."""
    first, second = make_handler("web"), make_handler("web")
    write_record(first, "a", 1.0)
    write_record(second, "b", 2.0)
    assert count_rows(first.db_path) == 2
