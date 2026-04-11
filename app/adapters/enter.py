from __future__ import annotations

from urllib.parse import quote

from app.adapters.base import ProductNotResolvedError, StoreAdapter
from app.clients.http import get_json, get_text
from app.models.product import Product, ProductList, ProductPrice
from app.normalizers.price import normalize_currency, to_float
from app.normalizers.product import product_from_jsonld
from app.parsing.jsonld import find_product_jsonld
from app.storage.product_identity import get_identity, save_identity


class EnterAdapter(StoreAdapter):
    store = "enter"
    base_url = "https://enter.online"

    async def search(self, query: str, *, page: int = 1) -> ProductList:
        url = f"{self.base_url}/search-fetch?q={quote(query)}&page={page}"
        data = await get_json(url)
        payload = data.get("data") or {}
        products = [self._from_search_item(item) for item in payload.get("products", [])]
        return ProductList(
            store=self.store,
            query=query,
            page=page,
            products=products,
            total=payload.get("total"),
        )

    async def get_by_id(self, source_id: str) -> Product:
        identity = get_identity(self.store, source_id)
        if identity and identity.url:
            return await self.get_by_url(identity.url)
        raise ProductNotResolvedError(self.store, source_id)

    async def get_by_url(self, url: str) -> Product:
        html = await get_text(url)
        jsonld = find_product_jsonld(html)
        if not jsonld:
            raise LookupError(f"Enter product URL not parseable: {url}")
        product = product_from_jsonld(self.store, jsonld, fallback_url=url)
        save_identity(
            store=self.store,
            source_id=product.source_id,
            sku=product.sku,
            url=product.url or url,
            name=product.name,
        )
        return product

    def _from_search_item(self, item: dict) -> Product:
        image = item.get("image")
        price = item.get("price") or {}
        product = Product(
            store=self.store,
            source_id=str(item.get("id")) if item.get("id") is not None else None,
            sku=str(item.get("id")) if item.get("id") is not None else None,
            name=str(item.get("name") or "Unknown product"),
            brand=item.get("brand"),
            category=None,
            url=item.get("url"),
            image=image,
            images=[image] if image else [],
            price=ProductPrice(
                current=to_float(price.get("current_price")),
                old=to_float(price.get("old")),
                currency=normalize_currency(price.get("currency")),
            ),
            availability="unknown",
            short_description=item.get("short_description"),
            source_type="json_api",
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

