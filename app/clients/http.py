from __future__ import annotations

import httpx


DEFAULT_HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.7",
    "accept-language": "ro-RO,ro;q=0.9,en-US;q=0.7,en;q=0.6",
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
    ),
}


async def get_text(url: str, *, headers: dict[str, str] | None = None) -> str:
    merged_headers = {**DEFAULT_HEADERS, **(headers or {})}
    async with httpx.AsyncClient(follow_redirects=True, timeout=30, headers=merged_headers) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text


async def get_json(url: str, *, headers: dict[str, str] | None = None) -> dict:
    merged_headers = {
        **DEFAULT_HEADERS,
        "accept": "application/json",
        "x-requested-with": "XMLHttpRequest",
        **(headers or {}),
    }
    async with httpx.AsyncClient(follow_redirects=True, timeout=30, headers=merged_headers) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


async def post_json(url: str, payload: dict, *, headers: dict[str, str] | None = None) -> dict:
    merged_headers = {**DEFAULT_HEADERS, "accept": "application/json", **(headers or {})}
    async with httpx.AsyncClient(follow_redirects=True, timeout=30, headers=merged_headers) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()

