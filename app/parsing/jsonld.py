from __future__ import annotations

import json
from typing import Any

from app.parsing.html import soup_from_html


def _iter_nodes(data: Any):
    if isinstance(data, dict):
        yield data
        graph = data.get("@graph")
        if isinstance(graph, list):
            for item in graph:
                yield from _iter_nodes(item)
    elif isinstance(data, list):
        for item in data:
            yield from _iter_nodes(item)


def find_product_jsonld(html: str) -> dict[str, Any] | None:
    soup = soup_from_html(html)
    for script in soup.find_all("script", {"type": "application/ld+json"}):
        text = script.string or script.get_text(strip=True)
        if not text:
            continue
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            continue
        for node in _iter_nodes(data):
            node_type = node.get("@type")
            if node_type == "Product" or (isinstance(node_type, list) and "Product" in node_type):
                return node
    return None

