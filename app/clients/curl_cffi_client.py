from __future__ import annotations

import asyncio
from typing import Any

from curl_cffi import requests


DEFAULT_HEADERS = {
    "accept-language": "ro-RO,ro;q=0.9,en-US;q=0.7,en;q=0.6",
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
    ),
}


def _get_text_sync(url: str, headers: dict[str, str] | None = None) -> str:
    response = requests.get(
        url,
        headers={**DEFAULT_HEADERS, **(headers or {})},
        impersonate="chrome",
        timeout=30,
    )
    response.raise_for_status()
    return response.text


def _post_json_sync(url: str, payload: dict[str, Any], headers: dict[str, str] | None = None) -> dict:
    response = requests.post(
        url,
        json=payload,
        headers={**DEFAULT_HEADERS, **(headers or {})},
        impersonate="chrome",
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


async def get_text(url: str, *, headers: dict[str, str] | None = None) -> str:
    return await asyncio.to_thread(_get_text_sync, url, headers)


async def post_json(url: str, payload: dict[str, Any], *, headers: dict[str, str] | None = None) -> dict:
    return await asyncio.to_thread(_post_json_sync, url, payload, headers)

