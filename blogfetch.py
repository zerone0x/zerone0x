#!/usr/bin/env python3

from datetime import timezone, timedelta
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET


BLOG_FEED_URL = "https://blog.trine.dev/rss.xml"
POST_LIMIT = 5
README_PATH = Path(__file__).with_name("README.md")
START_MARKER = "<!--START_SECTION:blog-->"
END_MARKER = "<!--END_SECTION:blog-->"
SHANGHAI_TZ = timezone(timedelta(hours=8))


def fetch_feed(url):
    request = Request(url, headers={"User-Agent": "zerone0x-profile-blogfetch"})
    with urlopen(request, timeout=20) as response:
        return response.read()


def escape_markdown(text):
    return text.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")


def format_post(item):
    title = escape_markdown(unescape(item.findtext("title", "")).strip())
    link = unescape(item.findtext("link", "")).strip()
    pub_date = item.findtext("pubDate", "").strip()

    if not title or not link or not pub_date:
        return None

    published_at = parsedate_to_datetime(pub_date).astimezone(SHANGHAI_TZ)
    return f"- [{title}]({link}) - {published_at:%Y-%m-%d}"


def build_posts_markdown(feed_xml):
    root = ET.fromstring(feed_xml)
    items = root.findall("./channel/item")
    posts = []

    for item in items:
        post = format_post(item)
        if post:
            posts.append(post)
        if len(posts) == POST_LIMIT:
            break

    return "\n".join(posts) if posts else "- No recent posts available"


def replace_section(readme_content, replacement):
    start_index = readme_content.find(START_MARKER)
    end_index = readme_content.find(END_MARKER)

    if start_index == -1 or end_index == -1 or end_index < start_index:
        raise RuntimeError("Blog section markers are missing or malformed.")

    section = f"{START_MARKER}\n{replacement}\n{END_MARKER}"
    return (
        readme_content[:start_index]
        + section
        + readme_content[end_index + len(END_MARKER):]
    )


def main():
    feed_xml = fetch_feed(BLOG_FEED_URL)
    posts_markdown = build_posts_markdown(feed_xml)
    readme_content = README_PATH.read_text()
    README_PATH.write_text(replace_section(readme_content, posts_markdown))


if __name__ == "__main__":
    main()
