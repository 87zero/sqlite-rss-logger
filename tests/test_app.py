"""Tests for the RSS feed service (REQ-020 to REQ-031)."""

import logging
import xml.etree.ElementTree as ET

import pytest
from fastapi.testclient import TestClient

from conftest import write_record
from sqlite_rss_logger.app import Settings, create_app


def make_client(log_dir, **kwargs) -> TestClient:
    return TestClient(create_app(Settings(log_dir=log_dir, **kwargs)))


def items(response):
    return ET.fromstring(response.text).findall("./channel/item")


def test_feed_is_rss_with_expected_item_fields(log_dir, make_handler):
    """REQ-021, REQ-025."""
    write_record(make_handler("web"), "hello", 1_700_000_000.0, logging.WARNING)
    response = make_client(log_dir).get("/rss")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/rss+xml")
    root = ET.fromstring(response.text)
    assert root.tag == "rss" and root.get("version") == "2.0"
    (item,) = root.findall("./channel/item")
    assert item.findtext("title") == "[WARNING] web: hello"
    assert "hello" in item.findtext("description")
    assert item.findtext("pubDate") == "Tue, 14 Nov 2023 22:13:20 +0000"
    assert item.findtext("guid") == "web-1"


def test_items_merged_newest_first(log_dir, make_handler):
    """REQ-023."""
    write_record(make_handler("a"), "first", 1.0)
    write_record(make_handler("b"), "second", 2.0)
    titles = [i.findtext("title") for i in items(make_client(log_dir).get("/rss"))]
    assert titles == ["[INFO] b: second", "[INFO] a: first"]


def test_limit_default_and_clamped_to_max(log_dir, make_handler):
    """REQ-024."""
    handler = make_handler("web")
    for i in range(10):
        write_record(handler, str(i), float(i))
    client = make_client(log_dir, default_items=4, max_items=6)
    assert len(items(client.get("/rss"))) == 4
    assert len(items(client.get("/rss?limit=2"))) == 2
    assert len(items(client.get("/rss?limit=100"))) == 6
    assert client.get("/rss?limit=0").status_code == 422


def test_filters(log_dir, make_handler):
    """REQ-026."""
    write_record(make_handler("a"), "info", 1.0, logging.INFO)
    write_record(make_handler("b"), "error", 2.0, logging.ERROR)
    client = make_client(log_dir)
    assert len(items(client.get("/rss?app=a"))) == 1
    assert len(items(client.get("/rss?app=a&app=b"))) == 2
    assert len(items(client.get("/rss?level=error"))) == 1
    assert client.get("/rss?level=nonsense").status_code == 400


def test_new_database_appears_without_restart(log_dir, make_handler):
    """REQ-022."""
    client = make_client(log_dir)
    assert items(client.get("/rss")) == []
    write_record(make_handler("late"), "x", 1.0)
    assert len(items(client.get("/rss"))) == 1


def test_bad_database_does_not_break_feed(log_dir, make_handler):
    """REQ-028."""
    write_record(make_handler("good"), "ok", 1.0)
    (log_dir / "corrupt.db").write_bytes(b"garbage" * 100)
    assert len(items(make_client(log_dir).get("/rss"))) == 1


def test_get_only(log_dir):
    """REQ-029."""
    assert make_client(log_dir).post("/rss").status_code == 405


def test_markup_and_invalid_xml_characters_are_safe(log_dir, make_handler):
    handler = make_handler("web")
    write_record(handler, "<b>bold</b> & \x00\x0b bad", 1.0)
    (item,) = items(make_client(log_dir).get("/rss"))
    assert "&lt;b&gt;bold&lt;/b&gt;" in item.findtext("description")


def test_traceback_included(log_dir, make_handler):
    handler = make_handler("web")
    logger = logging.getLogger("feed-tb")
    logger.propagate = False
    logger.addHandler(handler)
    try:
        raise RuntimeError("kaboom")
    except RuntimeError:
        logger.exception("failed")
    finally:
        logger.removeHandler(handler)
    (item,) = items(make_client(log_dir).get("/rss"))
    assert "RuntimeError: kaboom" in item.findtext("description")


class TestToken:
    """REQ-030."""

    @pytest.fixture
    def client(self, log_dir, make_handler):
        write_record(make_handler("web"), "x", 1.0)
        return make_client(log_dir, token="s3cret")

    def test_rejected_without_or_with_wrong_token(self, client):
        assert client.get("/rss").status_code == 401
        assert client.get("/rss?token=wrong").status_code == 401

    def test_accepted_by_query_or_header(self, client):
        assert client.get("/rss?token=s3cret").status_code == 200
        assert client.get("/rss", headers={"Authorization": "Bearer s3cret"}).status_code == 200

    def test_open_when_no_token_configured(self, log_dir):
        assert make_client(log_dir).get("/rss").status_code == 200
