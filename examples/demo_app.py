"""Example: two applications, each logging to its own SQLite database.

Run from the repository root:

    uv run examples/demo_app.py
    uv run sqlite-rss-logger --log-dir logs
    curl http://127.0.0.1:8000/rss
"""

import logging
import time

from sqlite_rss_logger import SQLiteHandler


def make_logger(application: str) -> logging.Logger:
    logger = logging.getLogger(application)
    logger.setLevel(logging.INFO)
    logger.addHandler(SQLiteHandler(application, log_dir="logs"))
    return logger


def main() -> None:
    web = make_logger("demo-web")
    worker = make_logger("demo-worker")

    web.info("Server started on port 8080")
    worker.info("Picked up job %d", 42)
    time.sleep(0.01)
    web.warning("Slow request: %s took %.1fs", "/search", 2.4)
    try:
        {}["missing"]
    except KeyError:
        worker.exception("Job %d failed", 42)
    print("Wrote records to logs/demo-web.db and logs/demo-worker.db")


if __name__ == "__main__":
    main()
