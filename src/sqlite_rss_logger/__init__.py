"""Log to one SQLite database per application and publish the records as an RSS feed.

``SQLiteHandler`` (standard library only) is the logging side. The feed service
lives in ``sqlite_rss_logger.app`` and is started with the ``sqlite-rss-logger``
command.
"""

from sqlite_rss_logger.handler import SQLiteHandler

__all__ = ["SQLiteHandler"]
