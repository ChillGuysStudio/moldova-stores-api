from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


IdFetchSupport = Literal["direct", "search_resolved", "cached_or_resolved"]


class StoreCapabilities(BaseModel):
    store: str
    name: str
    base_url: str
    supports_search: bool
    supports_url_fetch: bool
    supports_id_fetch: IdFetchSupport
    notes: str | None = None
