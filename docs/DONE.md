# Done

## Version 0.2.0

- Item `<link>` on every feed item: feed URL without query string plus `#<guid>`, so
  links are unique and never carry the access token (issue #2, REQ-025).
- Channel link also omits the query string; only `rel="self"` keeps the exact URL.
- Configurable feed title and description: `render_rss()` parameters, `Settings`,
  `--title`, `--description` and environment variables (issue #3, REQ-032).
- Unique GUIDs across recreated databases: `<application>-<id>-<creation time in base 36>`
  (REQ-025). Existing GUIDs change once.
- Code comment and tests documenting that the description is escaped twice on purpose
  (issue #1, closed as working as intended).

## Version 0.1.0

- SQLiteHandler: one database per application, WAL, schema auto-creation (REQ-001 to REQ-010).
- Feed service: GET /rss, merged newest-first, filters, limits, optional token,
  read-only, bad databases skipped (REQ-020 to REQ-031).
- Packaging: pyproject.toml, `sqlite-rss-logger` command, installable from the GitHub URL
  with `uv add`, `uv tool install` and `uvx` (REQ-040 to REQ-046).
- Showcase: public repository 87zero/sqlite-rss-logger, MIT licence, README, example
  app, pytest suite, GitHub Actions workflow including a Git URL install check
  (REQ-050 to REQ-055).
