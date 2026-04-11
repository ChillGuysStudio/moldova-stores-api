from __future__ import annotations

import json
from typing import Any

from app.parsing.html import soup_from_html


def _hydrate_livewire_value(value: Any) -> Any:
    if isinstance(value, list) and len(value) == 2 and isinstance(value[1], dict):
        marker = value[1].get("s")
        if marker == "arr":
            payload = value[0]
            if isinstance(payload, dict):
                return _hydrate_livewire_value(payload)
            return [_hydrate_livewire_value(item) for item in payload]
        if marker == "mdl":
            return value[1].get("key")
    if isinstance(value, dict):
        return {key: _hydrate_livewire_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_hydrate_livewire_value(item) for item in value]
    return value


def extract_livewire_search_products(page_html: str) -> list[dict[str, Any]]:
    soup = soup_from_html(page_html)
    for element in soup.find_all(attrs={"wire:snapshot": True}):
        snapshot = element.get("wire:snapshot", "")
        if '"name":"search-form"' not in snapshot and '"name": "search-form"' not in snapshot:
            continue
        try:
            data = json.loads(snapshot)
        except json.JSONDecodeError:
            continue
        products = data.get("data", {}).get("products")
        hydrated = _hydrate_livewire_value(products)
        if isinstance(hydrated, list):
            return [item for item in hydrated if isinstance(item, dict) and item.get("id")]
    return []


def extract_livewire_products_from_snapshot(snapshot: str) -> list[dict[str, Any]]:
    data = json.loads(snapshot)
    products = data.get("data", {}).get("products")
    hydrated = _hydrate_livewire_value(products)
    if isinstance(hydrated, list):
        return [item for item in hydrated if isinstance(item, dict) and item.get("id")]
    return []
