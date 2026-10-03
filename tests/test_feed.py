"""Tests for RSS rendering (REQ-025).

The description is escaped twice on purpose: html.escape() makes the log text safe
HTML, then Jinja autoescape encodes that HTML for the XML (see issue #1).
"""

import html
import xml.etree.ElementTree as ET

from sqlite_rss_logger.feed import render_rss
from sqlite_rss_logger.reader import LogEntry

MESSAGE = 'He said "hi" to <b>everyone</b> & left'
TRACEBACK = 'Traceback (most recent call last):\n  File "demo.py", line 1, in <module>'


def render(message: str = MESSAGE, traceback: str | None = TRACEBACK) -> str:
    entry = LogEntry(
        application="demo",
        id=1,
        created="2026-10-03T08:55:12.000000+00:00",
        level="ERROR",
        levelno=40,
        logger="demo",
        message=message,
        traceback=traceback,
    )
    return render_rss([entry], link="http://example/rss")


def test_description_is_escaped_twice_in_raw_xml():
    xml_text = render()
    assert "&lt;pre&gt;" in xml_text
    assert "&amp;quot;hi&amp;quot;" in xml_text
    assert "&amp;lt;b&amp;gt;everyone" in xml_text
    assert "&amp;amp; left" in xml_text


def test_xml_parser_yields_one_level_of_escaping_as_html():
    root = ET.fromstring(render())
    description = root.findtext("./channel/item/description")
    assert description.startswith("<pre>") and description.endswith("</pre>")
    assert "&quot;hi&quot;" in description
    assert "&lt;b&gt;everyone&lt;/b&gt;" in description
    assert "<b>" not in description


def test_html_rendering_restores_original_text():
    root = ET.fromstring(render())
    description = root.findtext("./channel/item/description")
    body = html.unescape(description.removeprefix("<pre>").removesuffix("</pre>"))
    assert body == f"{MESSAGE}\n\n{TRACEBACK}"


def test_description_is_text_not_child_elements():
    """A raw <pre> element inside <description> would mean the escaping was removed."""
    root = ET.fromstring(render())
    description = root.find("./channel/item/description")
    assert len(description) == 0
    assert root.find(".//pre") is None
