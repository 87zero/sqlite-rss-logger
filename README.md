# sqlite-rss-logger

A Python `logging` handler that writes to SQLite, and a small FastAPI service that
turns the latest records into an RSS feed you can read in any feed reader.

- Each application logs to its own database: `<log_dir>/<application>.db`.
- One feed merges the newest records from every database in the directory.
- The handler uses only the standard library; the feed service is FastAPI.

## Architecture

```
 app A --SQLiteHandler--> logs/app-a.db --+
 app B --SQLiteHandler--> logs/app-b.db --+--> sqlite-rss-logger (FastAPI) --> GET /rss --> feed reader
 app C --SQLiteHandler--> logs/app-c.db --+        (read-only, scans the directory on every request)
```

| Module | Purpose |
|---|---|
| `sqlite_rss_logger.handler` | `SQLiteHandler`, the `logging.Handler`; owns the schema |
| `sqlite_rss_logger.reader` | Reads the latest records across all databases, read-only |
| `sqlite_rss_logger.feed` | Renders RSS 2.0 from `templates/rss.xml.j2` (Jinja) |
| `sqlite_rss_logger.app` | FastAPI app with `GET /rss` |
| `sqlite_rss_logger.cli` | The `sqlite-rss-logger` command (Click) |

## Install

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

Use the handler in your project:

```
uv add git+https://github.com/87zero/sqlite-rss-logger
```

Install the feed service as a command:

```
uv tool install git+https://github.com/87zero/sqlite-rss-logger
```

Or run it once without installing:

```
uvx --from git+https://github.com/87zero/sqlite-rss-logger sqlite-rss-logger --log-dir logs
```

Pin a release by adding a tag: `git+https://github.com/87zero/sqlite-rss-logger@v0.1.0`.

## Quick start

In your application:

```python
import logging
from sqlite_rss_logger import SQLiteHandler

logging.getLogger().addHandler(SQLiteHandler("my-app", log_dir="logs"))
logging.getLogger().setLevel(logging.INFO)
logging.warning("Disk is %d%% full", 91)
```

Start the feed service (it reads the same directory):

```
sqlite-rss-logger --log-dir logs
```

Subscribe your feed reader to `http://127.0.0.1:8000/rss`.

To try it without writing any code, clone the repository and run:

```
uv run examples/demo_app.py
uv run sqlite-rss-logger --log-dir logs
curl "http://127.0.0.1:8000/rss?level=warning"
```

### Sample output

```xml
<item>
  <title>[WARNING] demo-web: Slow request: /search took 2.4s</title>
  <link>http://127.0.0.1:8000/rss#demo-web-2</link>
  <description>&lt;pre&gt;Slow request: /search took 2.4s&lt;/pre&gt;</description>
  <pubDate>Sat, 03 Oct 2026 08:55:12 +0000</pubDate>
  <guid isPermaLink="false">demo-web-2</guid>
  <category>WARNING</category>
</item>
```

## The handler

`SQLiteHandler(application, log_dir="logs", level=logging.NOTSET)`

- The application name becomes the filename, so it may contain only letters, digits,
  `.`, `_` and `-`.
- The directory, database and schema are created if missing.
- Every record is committed immediately. A database failure never raises into your
  application; it goes through the standard `Handler.handleError`.
- Records store UTC timestamp (ISO 8601), level, logger name, message and traceback.
- Threads share one connection. Several processes can write to the same database
  (WAL mode, 30 second busy timeout), but each process needs its own handler.

## The feed service

`GET /rss` query parameters:

| Parameter | Meaning |
|---|---|
| `app` | Only this application; repeat for several (`?app=a&app=b`) |
| `level` | Minimum level name, for example `warning` |
| `limit` | Number of items, capped at `--max-items` |
| `token` | Access token, only if one is configured |

Options (each also has an environment variable):

| Option | Environment variable | Default |
|---|---|---|
| `--log-dir` | `SQLITE_RSS_LOGGER_LOG_DIR` | `logs` |
| `--host` | `SQLITE_RSS_LOGGER_HOST` | `127.0.0.1` |
| `--port` | `SQLITE_RSS_LOGGER_PORT` | `8000` |
| `--default-items` | `SQLITE_RSS_LOGGER_DEFAULT_ITEMS` | `50` |
| `--max-items` | `SQLITE_RSS_LOGGER_MAX_ITEMS` | `500` |
| `--token` | `SQLITE_RSS_LOGGER_TOKEN` | none (feed is open) |
| `--title` | `SQLITE_RSS_LOGGER_TITLE` | `Application logs` |
| `--description` | `SQLITE_RSS_LOGGER_DESCRIPTION` | `Latest log records from all applications` |

If you call `render_rss()` yourself, pass `title=` and `description=` instead.

Notes:

- Databases are opened read-only. A missing, locked, corrupt or unexpected database
  is skipped with a warning and the rest of the feed is still served.
- New databases are picked up without restarting the service.
- When a token is set, send it as `?token=...` or `Authorization: Bearer ...`.
- The service has no HTTPS. Keep it on a trusted network or put a reverse proxy in
  front of it. Log messages can contain sensitive data; treat the feed accordingly.

## Development

```
uv sync
uv run pytest
uv run ruff check .
```

Requirements are in [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md); tests cite the
requirement IDs they cover. Open work is in [docs/TODO.md](docs/TODO.md).

## Licence

MIT. See [LICENSE](LICENSE).
