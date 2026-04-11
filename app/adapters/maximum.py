from __future__ import annotations

from urllib.parse import quote

from app.adapters.base import StoreAdapter
from app.clients.http import get_json, get_text
from app.models.product import Product, ProductList, ProductPrice
from app.normalizers.price import normalize_currency, to_float
from app.normalizers.product import product_from_jsonld
from app.parsing.jsonld import find_product_jsonld
from app.storage.product_identity import save_identity


class MaximumAdapter(StoreAdapter):
    store = "maximum"
    base_url = "https://maximum.md"

    async def search(self, query: str, *, page: int = 1) -> ProductList:
        data = await get_json(f"{self.base_url}/ro/products/search/suggestions?query={quote(query)}")
        products = [self._from_search_item(item) for item in data.get("products", [])]
        return ProductList(
            store=self.store,
            query=query,
            page=page,
            products=products,
            total=(data.get("total_products") or {}).get("value"),
        )

    async def get_by_id(self, source_id: str) -> Product:
        data = await get_json(
            f"{self.base_url}/ro/get_compare_products",
            headers={"cookie": f"compare_products={source_id}"},
        )
        products = data.get("products") or []
        if not products:
            raise LookupError(f"Maximum product {source_id} not found")
        return self._from_compare_item(products[0])

    async def get_by_url(self, url: str) -> Product:
        html = await get_text(url)
        jsonld = find_product_jsonld(html)
        if jsonld:
            product = product_from_jsonld(self.store, jsonld, fallback_url=url)
            save_identity(
                store=self.store,
                source_id=product.source_id,
                sku=product.sku,
                url=product.url or url,
                name=product.name,
            )
            return product
        raise LookupError(f"Maximum product URL not parseable: {url}")

    def _from_search_item(self, item: dict) -> Product:
        image = item.get("image")
        price = item.get("price") or {}
        old_price = item.get("old_price") or {}
        product = Product(
            store=self.store,
            source_id=str(item.get("_id")) if item.get("_id") is not None else None,
            sku=str(item.get("_id")) if item.get("_id") is not None else None,
            name=str(item.get("title") or "Unknown product"),
            image=image,
            images=[image] if image else [],
            price=ProductPrice(
                current=to_float(price.get("value")),
                old=to_float(old_price.get("value")),
                currency=normalize_currency(price.get("unit")),
            ),
            source_type="json_api",
            raw=item,
        )
        save_identity(store=self.store, source_id=product.source_id, sku=product.sku, name=product.name)
        return product

    def _from_compare_item(self, item: dict) -> Product:
        features = item.get("features") or {}
        title = item.get("title")
        if isinstance(title, dict):
            title = title.get("ro") or next(iter(title.values()), None)
        product = Product(
            store=self.store,
            source_id=str(item.get("_id")) if item.get("_id") is not None else None,
            sku=str(item.get("_id")) if item.get("_id") is not None else None,
            name=str(title or "Unknown product"),
            image=item.get("image"),
            images=[item["image"]] if item.get("image") else [],
            price=ProductPrice(
                current=to_float(item.get("price")),
                old=to_float((features.get("2") or {}).get("value")),
                currency=normalize_currency(item.get("currency")),
            ),
            availability="unknown",
            source_type="cookie_based_json",
            raw=item,
        )
        save_identity(store=self.store, source_id=product.source_id, sku=product.sku, name=product.name)
        return product
