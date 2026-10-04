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


def entries(count: int) -> list[LogEntry]:
    return [
        LogEntry("demo", i, f"2026-10-03T08:55:{i:02d}.000000+00:00", "INFO", 20, "demo", "m", None)
        for i in range(1, count + 1)
    ]


def test_each_item_has_a_unique_link_with_guid_fragment():
    """REQ-025: some readers hide or merge items without distinct links (issue #2)."""
    root = ET.fromstring(render_rss(entries(3), link="http://example/rss"))
    items = root.findall("./channel/item")
    links = [i.findtext("link") for i in items]
    assert links == [f"http://example/rss#{i.findtext('guid')}" for i in items]
    assert len(set(links)) == 3


def test_links_drop_query_string_but_self_link_keeps_it():
    url = "http://example/rss?app=demo&level=warning&token=SECRET"
    xml_text = render_rss(entries(2), link=url)
    root = ET.fromstring(xml_text)
    assert root.findtext("./channel/link") == "http://example/rss"
    for item in root.findall("./channel/item"):
        assert "SECRET" not in item.findtext("link")
        assert "?" not in item.findtext("link")
    self_link = root.find("./channel/{http://www.w3.org/2005/Atom}link")
    assert self_link.get("href") == url
    assert xml_text.count("SECRET") == 1


def test_channel_title_and_description_default():
    """REQ-032."""
    root = ET.fromstring(render_rss(entries(1), link="http://example/rss"))
    assert root.findtext("./channel/title") == "Application logs"
    assert root.findtext("./channel/description") == "Latest log records from all applications"


def test_channel_title_and_description_can_be_set():
    """REQ-032 (issue #3)."""
    root = ET.fromstring(
        render_rss(entries(1), link="http://example/rss", title="Shop logs", description="Prod")
    )
    assert root.findtext("./channel/title") == "Shop logs"
    assert root.findtext("./channel/description") == "Prod"


def test_custom_title_is_escaped_and_cleaned():
    """Special characters stay valid XML and read back unchanged."""
    xml_text = render_rss(
        entries(1), link="http://example/rss", title="R&D <logs> \x00", description="a & b"
    )
    root = ET.fromstring(xml_text)
    assert root.findtext("./channel/title") == "R&D <logs> "
    assert root.findtext("./channel/description") == "a & b"


def guid_of(entry: LogEntry) -> str:
    root = ET.fromstring(render_rss([entry], link="http://example/rss"))
    return root.findtext("./channel/item/guid")


def test_guid_is_application_id_and_base36_creation_time():
    """REQ-025: 2026-10-03T08:55:12.123456Z is 1791017712123456 microseconds."""
    entry = LogEntry(
        "demo", 2, "2026-10-03T08:55:12.123456+00:00", "INFO", 20, "demo", "m", None
    )
    guid = guid_of(entry)
    assert guid == "demo-2-hmv26f3adc"
    assert int(guid.rsplit("-", 1)[1], 36) == 1_791_017_712_123_456


def test_guid_is_stable_across_renders():
    entry = entries(1)[0]
    assert guid_of(entry) == guid_of(entry)


def test_recreated_database_does_not_reuse_guids():
    """Ids restart at 1 in a recreated database; readers must still see new GUIDs."""
    old = LogEntry("web", 1, "2026-10-03T08:00:00.000000+00:00", "INFO", 20, "web", "m", None)
    new = LogEntry("web", 1, "2026-10-04T09:30:00.000000+00:00", "INFO", 20, "web", "m", None)
    assert guid_of(old) != guid_of(new)


def test_guid_is_lowercase_letters_and_digits_only_after_the_id():
    suffix = guid_of(entries(1)[0]).rsplit("-", 1)[1]
    assert suffix.isalnum() and suffix == suffix.lower()
