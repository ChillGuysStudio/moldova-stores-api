from __future__ import annotations

import asyncio
import httpx

from app.adapters.base import ProductNotResolvedError, StoreAdapter
from app.clients.http import DEFAULT_HEADERS, get_text
from app.models.product import Product, ProductList, ProductPrice
from app.normalizers.availability import normalize_availability
from app.normalizers.price import to_float
from app.normalizers.product import product_from_jsonld
from app.parsing.html import soup_from_html
from app.parsing.jsonld import find_product_jsonld
from app.parsing.livewire import extract_livewire_products_from_snapshot
from app.storage.product_identity import get_identity, save_identity


class DarwinAdapter(StoreAdapter):
    store = "darwin"
    base_url = "https://darwin.md"

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._csrf_token: str | None = None
        self._search_snapshot: str | None = None
        self._bootstrap_lock = asyncio.Lock()

    async def search(self, query: str, *, page: int = 1) -> ProductList:
        if page > 1:
            raise ValueError("Darwin direct Livewire search only supports page=1 in v1")

        raw_products = await self._search_livewire(query)
        products = [self._from_livewire_item(item) for item in raw_products]
        return ProductList(store=self.store, query=query, page=page, products=products)

    async def get_by_id(self, source_id: str) -> Product:
        identity = get_identity(self.store, source_id)
        if identity and identity.url:
            return await self.get_by_url(identity.url)
        raise ProductNotResolvedError(self.store, source_id)

    async def get_by_url(self, url: str) -> Product:
        html = await get_text(url)
        jsonld = find_product_jsonld(html)
        if not jsonld:
            raise LookupError(f"Darwin product URL not parseable: {url}")
        product = product_from_jsonld(self.store, jsonld, fallback_url=url)
        save_identity(
            store=self.store,
            source_id=product.source_id,
            sku=product.sku,
            url=product.url or url,
            name=product.name,
        )
        return product

    async def _search_livewire(self, query: str) -> list[dict]:
        await self._ensure_livewire_session()
        assert self._client is not None
        assert self._csrf_token is not None
        assert self._search_snapshot is not None

        response = await self._client.post(
            f"{self.base_url}/livewire/update",
            json={
                "_token": self._csrf_token,
                "components": [
                    {
                        "snapshot": self._search_snapshot,
                        "updates": {"keywords": query},
                        "calls": [],
                    }
                ],
            },
            headers={
                "accept": "application/json",
                "content-type": "application/json",
                "referer": f"{self.base_url}/",
                "x-csrf-token": self._csrf_token,
                "x-livewire": "",
            },
        )
        response.raise_for_status()
        data = response.json()
        self._search_snapshot = data["components"][0]["snapshot"]
        return extract_livewire_products_from_snapshot(self._search_snapshot)

    async def _ensure_livewire_session(self) -> None:
        if self._client and self._csrf_token and self._search_snapshot:
            return

        async with self._bootstrap_lock:
            if self._client and self._csrf_token and self._search_snapshot:
                return

            self._client = httpx.AsyncClient(follow_redirects=True, timeout=30, headers=DEFAULT_HEADERS)
            response = await self._client.get(self.base_url)
            response.raise_for_status()
            soup = soup_from_html(response.text)

            csrf = soup.select_one('meta[name="csrf-token"]')
            if not csrf or not csrf.get("content"):
                raise LookupError("Darwin CSRF token not found")

            for element in soup.find_all(attrs={"wire:snapshot": True}):
                snapshot = element.get("wire:snapshot", "")
                if '"name":"search-form"' in snapshot or '"name": "search-form"' in snapshot:
                    self._csrf_token = csrf.get("content")
                    self._search_snapshot = snapshot
                    return

            raise LookupError("Darwin search-form Livewire snapshot not found")

    async def _reset_livewire_session(self) -> None:
        if self._client:
            await self._client.aclose()
        self._client = None
        self._csrf_token = None
        self._search_snapshot = None

    def _from_livewire_item(self, item: dict) -> Product:
        product_url = f"{self.base_url}/{item.get('slug')}" if item.get("slug") else None
        image = item.get("image")
        product = Product(
            store=self.store,
            source_id=str(item.get("id")) if item.get("id") is not None else None,
            sku=str(item.get("id")) if item.get("id") is not None else None,
            name=str(item.get("name") or "Unknown product").strip(),
            brand=None,
            category=None,
            url=product_url,
            image=image,
            images=[image] if image else [],
            price=ProductPrice(
                current=to_float(item.get("final_price") or item.get("price")),
                old=to_float(item.get("pre_discount_price")),
                currency="MDL",
            ),
            availability=normalize_availability(item.get("stock") and int(item.get("stock", 0)) > 0),
            short_description=item.get("short_description"),
            source_type="livewire_snapshot",
            raw=item,
        )
        save_identity(
            store=self.store,
            source_id=product.source_id,
            sku=product.sku,
            url=product.url,
            name=product.name,
        )
        return product
