from __future__ import annotations

from urllib.parse import quote

from app.adapters.base import StoreAdapter
from app.clients.http import get_json, get_text
from app.models.product import Product, ProductList, ProductPrice
from app.normalizers.availability import normalize_availability
from app.normalizers.price import to_float
from app.normalizers.product import product_from_jsonld
from app.parsing.jsonld import find_product_jsonld
from app.storage.product_identity import save_identity


class SmartAdapter(StoreAdapter):
    store = "smart"
    base_url = "https://www.smart.md"
    tenant = "74mosv2covp1tqieoh6lu8edqd"
    api_base = f"https://smartmdnew.visely.io/prometheus/api/v3/{tenant}"

    async def search(self, query: str, *, page: int = 1) -> ProductList:
        offset = max(page - 1, 0) * 40
        url = (
            f"{self.api_base}/search?q={quote(query)}&offset={offset}&count=40"
            "&includeOutOfStock=false"
            "&extraFields=variants,brand,model,sku,categories,category_names_ro,additional_attributes,tags"
        )
        data = await get_json(url)
        products = [self._from_visely(item) for item in data.get("products", [])]
        return ProductList(
            store=self.store,
            query=query,
            page=page,
            products=products,
            total=data.get("meta", {}).get("total"),
        )

    async def get_by_id(self, source_id: str) -> Product:
        url = (
            f"{self.api_base}/search?q={quote(source_id)}&count=1"
            "&extraFields=variants,brand,model,sku,categories,category_names_ro,additional_attributes,tags"
        )
        data = await get_json(url)
        for item in data.get("products", []):
            if str(item.get("sku")) == str(source_id) or str(item.get("id")) == str(source_id):
                return self._from_visely(item)
        raise LookupError(f"Smart product {source_id} not found")

    async def get_by_url(self, url: str) -> Product:
        html = await get_text(url)
        jsonld = find_product_jsonld(html)
        if jsonld:
            product = product_from_jsonld(self.store, jsonld, fallback_url=url)
            save_identity(
                store=self.store,
                source_id=product.source_id,
                sku=product.sku,
                url=product.url,
                name=product.name,
            )
            return product
        raise LookupError(f"Smart product URL not parseable: {url}")

    def _from_visely(self, item: dict) -> Product:
        name_value = item.get("name")
        name = name_value.get("ro") if isinstance(name_value, dict) else name_value
        prices = item.get("prices", [])
        regular = next((price for price in prices if price.get("priceType") == "REGULAR"), None)
        sale = next((price for price in prices if price.get("priceType") == "SALE"), None)
        active = sale or regular or {}
        category_names = item.get("categoryNames") or {}
        category_ro = category_names.get("ro") if isinstance(category_names, dict) else None
        media = item.get("media") or []
        image = media[0].get("url") if media and isinstance(media[0], dict) else None

        product = Product(
            store=self.store,
            source_id=str(item.get("sku") or item.get("id")),
            sku=str(item.get("sku")) if item.get("sku") is not None else None,
            name=str(name or item.get("model") or "Unknown product"),
            brand=item.get("brand"),
            category=category_ro[-1] if isinstance(category_ro, list) and category_ro else None,
            url=item.get("absoluteUrl"),
            image=image,
            images=[image] if image else [],
            price=ProductPrice(
                current=to_float(active.get("value")),
                old=to_float(regular.get("value")) if sale and regular else None,
                currency=active.get("currency", "MDL"),
            ),
            availability=normalize_availability(item.get("inStock")),
            short_description=item.get("model"),
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
