from __future__ import annotations

import asyncio
import os

import httpx


DEFAULT_SELF_PING_INTERVAL_SECONDS = 13 * 60


def get_self_ping_url() -> str | None:
    base_url = os.environ.get("RENDER_EXTERNAL_URL", "").strip().rstrip("/")
    if not base_url:
        return None
    return f"{base_url}/ping"


def get_self_ping_interval_seconds() -> int:
    try:
        return max(1, int(os.environ.get("SELF_PING_INTERVAL_SECONDS", DEFAULT_SELF_PING_INTERVAL_SECONDS)))
    except ValueError:
        return DEFAULT_SELF_PING_INTERVAL_SECONDS


async def self_ping_loop() -> None:
    ping_url = get_self_ping_url()
    if not ping_url:
        return

    interval = get_self_ping_interval_seconds()
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        while True:
            await asyncio.sleep(interval)
            try:
                await client.get(ping_url)
            except Exception:
                # Best-effort keepalive only.
                continue
