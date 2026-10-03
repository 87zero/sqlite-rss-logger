"""Tests for the multi-database reader (REQ-022 to REQ-028)."""

import logging
import sqlite3

import pytest

from conftest import write_record
from sqlite_rss_logger.reader import _connect_readonly, latest_entries, list_applications


def test_merges_newest_first(log_dir, make_handler):
    """REQ-023."""
    web, worker = make_handler("web"), make_handler("worker")
    write_record(web, "w1", 1.0)
    write_record(worker, "k2", 2.0)
    write_record(web, "w3", 3.0)
    entries = latest_entries(log_dir, 10)
    assert [e.message for e in entries] == ["w3", "k2", "w1"]
    assert [e.application for e in entries] == ["web", "worker", "web"]


def test_limit(log_dir, make_handler):
    """REQ-024."""
    handler = make_handler("web")
    for i in range(10):
        write_record(handler, str(i), float(i))
    assert [e.message for e in latest_entries(log_dir, 3)] == ["9", "8", "7"]


def test_filter_application_and_level(log_dir, make_handler):
    """REQ-026."""
    web, worker = make_handler("web"), make_handler("worker")
    write_record(web, "info", 1.0, logging.INFO)
    write_record(web, "error", 2.0, logging.ERROR)
    write_record(worker, "warn", 3.0, logging.WARNING)
    only_web = latest_entries(log_dir, 10, applications=["web"])
    assert {e.application for e in only_web} == {"web"}
    warnings_up = latest_entries(log_dir, 10, min_level=logging.WARNING)
    assert [e.message for e in warnings_up] == ["warn", "error"]


def test_discovers_new_database_without_restart(log_dir, make_handler):
    """REQ-022."""
    assert list_applications(log_dir) == []
    write_record(make_handler("late"), "x", 1.0)
    assert list_applications(log_dir) == ["late"]


def test_missing_directory_is_empty(tmp_path):
    assert latest_entries(tmp_path / "nope", 10) == []


def test_bad_databases_are_skipped(log_dir, make_handler, caplog):
    """REQ-028."""
    write_record(make_handler("good"), "ok", 1.0)
    (log_dir / "corrupt.db").write_bytes(b"this is not a database" * 50)
    (log_dir / "empty.db").touch()
    other = sqlite3.connect(log_dir / "wrongschema.db")
    other.execute("CREATE TABLE logs (x INTEGER)")
    other.commit()
    other.close()
    with caplog.at_level(logging.WARNING):
        entries = latest_entries(log_dir, 10)
    assert [e.message for e in entries] == ["ok"]
    assert "Skipping corrupt.db" in caplog.text


def test_connection_is_read_only(log_dir, make_handler):
    """REQ-027."""
    handler = make_handler("web")
    conn = _connect_readonly(handler.db_path)
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("DELETE FROM logs")
    conn.close()
