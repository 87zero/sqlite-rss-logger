# Done

Version 0.1.0 (local, not yet pushed):

- SQLiteHandler: one database per application, WAL, schema auto-creation (REQ-001 to REQ-010).
- Feed service: GET /rss, merged newest-first, filters, limits, optional token,
  read-only, bad databases skipped (REQ-020 to REQ-031).
- Packaging: pyproject.toml, `sqlite-rss-logger` command (REQ-040, REQ-042, REQ-044, REQ-045).
- Showcase: MIT licence, README, example app, pytest suite, GitHub Actions workflow
  (REQ-050 to REQ-055).
