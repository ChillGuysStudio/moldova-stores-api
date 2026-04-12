from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass

from app.models.product import ProductList


DEFAULT_SEARCH_CACHE_TTL_SECONDS = 300
DEFAULT_SEARCH_CACHE_MAX_ENTRIES = 512


@dataclass
class SearchCacheEntry:
    expires_at: float
    result: ProductList


_cache: dict[tuple[str, str, int], SearchCacheEntry] = {}
_in_flight: dict[tuple[str, str, int], asyncio.Task[ProductList]] = {}
_lock = asyncio.Lock()


async def cached_native_search(adapter, *, query: str, page: int) -> ProductList:
    ttl = _ttl_seconds()
    if ttl <= 0:
        return await adapter.search(query, page=page)

    key = (adapter.store, query.strip().casefold(), page)
    now = time.monotonic()

    async with _lock:
        entry = _cache.get(key)
        if entry and entry.expires_at > now:
            return entry.result.model_copy(deep=True)
        if entry:
            _cache.pop(key, None)

        task = _in_flight.get(key)
        created_task = False
        if task is None:
            task = asyncio.create_task(adapter.search(query, page=page))
            _in_flight[key] = task
            created_task = True

    try:
        result = await task
    except Exception:
        if created_task:
            async with _lock:
                _in_flight.pop(key, None)
        raise

    if created_task:
        async with _lock:
            _in_flight.pop(key, None)
            _cache[key] = SearchCacheEntry(expires_at=time.monotonic() + ttl, result=result.model_copy(deep=True))
            _trim_cache()

    return result.model_copy(deep=True)


def clear_search_cache() -> None:
    _cache.clear()
    _in_flight.clear()


def _ttl_seconds() -> int:
    return _int_from_env("SEARCH_CACHE_TTL_SECONDS", DEFAULT_SEARCH_CACHE_TTL_SECONDS)


def _max_entries() -> int:
    return _int_from_env("SEARCH_CACHE_MAX_ENTRIES", DEFAULT_SEARCH_CACHE_MAX_ENTRIES)


def _int_from_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


def _trim_cache() -> None:
    max_entries = _max_entries()
    if max_entries <= 0:
        _cache.clear()
        return
    while len(_cache) > max_entries:
        oldest_key = min(_cache, key=lambda key: _cache[key].expires_at)
        _cache.pop(oldest_key, None)
