from __future__ import annotations

from bs4 import BeautifulSoup


def soup_from_html(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def absolute_url(base_url: str, href: str | None) -> str | None:
    if not href:
        return None
    if href.startswith("http://") or href.startswith("https://"):
        return href
    return base_url.rstrip("/") + "/" + href.lstrip("/")

