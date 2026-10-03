"""Tests for the command line entry point (REQ-042, REQ-044)."""

from click.testing import CliRunner

from sqlite_rss_logger import cli


def test_help_lists_options_and_env_vars():
    result = CliRunner().invoke(cli.main, ["--help"])
    assert result.exit_code == 0
    for text in ("--log-dir", "--port", "--max-items", "--token", "SQLITE_RSS_LOGGER_LOG_DIR"):
        assert text in result.output


def test_options_reach_settings(monkeypatch, tmp_path):
    captured = {}
    monkeypatch.setattr(cli.uvicorn, "run", lambda app, **kw: captured.update(app=app, **kw))
    monkeypatch.setenv("SQLITE_RSS_LOGGER_PORT", "9123")
    result = CliRunner().invoke(cli.main, ["--log-dir", str(tmp_path), "--token", "t"])
    assert result.exit_code == 0, result.output
    assert captured["port"] == 9123
    assert captured["host"] == "127.0.0.1"
