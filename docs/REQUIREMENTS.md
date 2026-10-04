# Requirements: RSS Logging

Source: CONCEPT.md. Priorities use MoSCoW (Must / Should / Could / Won't).

## Overview

A Python logger writes log records to an SQLite database. Each application has
its own log database. A FastAPI web service reads the latest records from all
of the log databases and publishes them as an RSS feed.

## Logger

| ID | Requirement | Priority |
|---|---|---|
| REQ-001 | The logger is a `logging.Handler` subclass that applications attach to the standard Python `logging` module. | Must |
| REQ-002 | Each application writes to its own SQLite database file. Applications never share a database file. | Must |
| REQ-003 | The application name is supplied when the handler is created and determines the database filename (`<application>.db`) in the log directory. | Must |
| REQ-004 | The log directory is configurable. | Must |
| REQ-005 | The handler creates the database file and schema automatically if they do not exist. | Must |
| REQ-006 | Each record stores: timestamp (UTC, ISO 8601), level, logger name, message, and exception traceback (if any). | Must |
| REQ-007 | Records are stored as they are emitted; a crash in the application must not lose already-emitted records. | Must |
| REQ-008 | A failure to write to the database must not raise an exception into the application; the failure is reported through the standard `logging` error handling (`Handler.handleError`). | Must |
| REQ-009 | Multiple threads and processes of the same application can write to the same database safely (SQLite WAL mode, busy timeout). | Should |
| REQ-010 | The timestamp column is indexed so the latest records can be read efficiently. | Should |

## Web service

| ID | Requirement | Priority |
|---|---|---|
| REQ-020 | The service is implemented with FastAPI. | Must |
| REQ-021 | The service exposes an RSS 2.0 feed endpoint (`GET /rss`) containing the latest records from all log databases. | Must |
| REQ-022 | The service discovers log databases by scanning the configured log directory for `*.db` files. The filename (without extension) is the application name. Databases added after start-up are picked up without a restart. | Must |
| REQ-023 | Feed items are merged across all databases and ordered newest first. | Must |
| REQ-024 | The number of items in the feed is limited to the latest N records; N has a configured default and can be overridden by a query parameter up to a configured maximum. | Must |
| REQ-025 | Each feed item contains: title (application name, level and a short message summary), link, description (full message and traceback), publication date (record timestamp), and a stable unique GUID (application name plus record id). The item link is the feed URL without query string plus `#<guid>`, so it is unique per item and never contains an access token (some feed readers hide or merge items that lack distinct links). The channel link also omits the query string; only the `rel="self"` link keeps the exact requested URL. | Must |
| REQ-026 | The feed can be filtered by query parameters: `app` (one or more application names) and `level` (minimum level). | Should |
| REQ-027 | The service opens log databases read-only and never modifies them. | Must |
| REQ-028 | A database that is missing, locked, corrupt or has an unexpected schema is skipped and reported in the service log; it does not make the feed fail. | Must |
| REQ-029 | The feed endpoint is read-only (`GET` only). | Must |
| REQ-030 | The feed endpoint can optionally be protected by a static token set in configuration; when no token is configured, the feed is open. | Could |
| REQ-031 | The log directory, default item count, maximum item count and listen address are configurable, not hard-coded. | Must |

## Packaging and distribution

The project is a public showcase in the 87zero GitHub organisation, repository
`87zero/sqlite-rss-logger`, Python package `sqlite_rss_logger`.

| ID | Requirement | Priority |
|---|---|---|
| REQ-040 | The repository is a standard installable Python package defined by `pyproject.toml` (src layout, `uv` build-compatible), with logger and web service in the same package. | Must |
| REQ-041 | It can be added to an application with `uv add git+https://github.com/87zero/sqlite-rss-logger` and imported as `sqlite_rss_logger`. | Must |
| REQ-042 | It can be installed as a command-line tool with `uv tool install git+https://github.com/87zero/sqlite-rss-logger`, providing a command that starts the feed service. | Must |
| REQ-043 | It can be run without installing, with `uvx --from git+https://github.com/87zero/sqlite-rss-logger <command>`. | Should |
| REQ-044 | The feed service command is a Click CLI; options (log directory, host, port, item limits, token) can also be set by environment variables. | Must |
| REQ-045 | The logger library has minimal dependencies (standard library only); web service dependencies (FastAPI, uvicorn, Click) are installed with the package but the handler module imports none of them. | Should |
| REQ-046 | Installation from the GitHub URL is verified from a clean environment, and the README shows the exact commands. | Must |
| REQ-047 | A version number is defined in `pyproject.toml` and releases are marked with git tags, so users can pin an install with `@<tag>`. | Should |

## Showcase repository

| ID | Requirement | Priority |
|---|---|---|
| REQ-050 | The repository is licensed under the MIT licence (`LICENSE` file, licence declared in `pyproject.toml`). | Must |
| REQ-051 | The README explains what the project does, the architecture (handler, per-application databases, feed service), installation, a quick start, configuration, and shows sample feed output. | Must |
| REQ-052 | An example application under `examples/` logs to its own database so the full flow can be tried in a few commands. | Must |
| REQ-053 | Automated tests under `tests/` (pytest) cover the handler and the web service, using temporary databases only. | Must |
| REQ-054 | A GitHub Actions workflow runs the tests and lint (ruff) on pull requests and pushes, and runs a clean-install check of the uv Git URL install path. | Should |
| REQ-055 | The repository contains no personal data: no hard-coded home-folder paths, no secrets, no real log data. | Must |
| REQ-056 | A screenshot of the feed in a feed reader is included in the README, stored in the repository (not hotlinked). | Could |

## Constraints and assumptions

- [ASSUMPTION] Python 3.11 or later; `uv` is the supported installer (no pip instructions).
- [ASSUMPTION] The GitHub repository `87zero/sqlite-rss-logger` is public, so the uv Git URL needs no credentials.
- [ASSUMPTION] Log retention (deleting or rotating old records) is out of scope for the first version (Won't, for now).
- [ASSUMPTION] The feed is intended for a trusted network; transport security (HTTPS) is handled outside the service, for example by a reverse proxy.
- [OPEN QUESTION] Should the service also provide a per-application feed (for example `/rss/<application>`)? The `app` filter in REQ-026 currently covers this.
- [OPEN QUESTION] Is feed authentication (REQ-030) wanted at all? It is recorded as Could until confirmed.

## Out of scope

- A web UI for browsing logs.
- Writing to log databases from the web service.
- Log shipping from remote machines.
