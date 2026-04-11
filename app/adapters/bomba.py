from __future__ import annotations

import re
from urllib.parse import quote

from app.adapters.base import StoreAdapter
from app.clients.curl_cffi_client import get_text, post_json
from app.models.product import Product, ProductList, ProductPrice
from app.normalizers.price import to_float
from app.normalizers.product import product_from_jsonld
from app.parsing.html import absolute_url, soup_from_html
from app.parsing.jsonld import find_product_jsonld
from app.storage.product_identity import save_identity


class BombaAdapter(StoreAdapter):
    store = "bomba"
    base_url = "https://bomba.md"

    async def search(self, query: str, *, page: int = 1) -> ProductList:
        url = f"{self.base_url}/ro/cautare/?search={quote(query)}"
        if page > 1:
            url += f"&page={page}"
        html = await get_text(url)
        soup = soup_from_html(html)
        products: list[Product] = []
        for link in soup.select('a[href*="/ro/product/"]'):
            href = absolute_url(self.base_url, link.get("href"))
            if not href:
                continue
            product_id = self._id_from_url(href)
            name = link.get_text(" ", strip=True)
            if not product_id or not name:
                continue
            product = Product(
                store=self.store,
                source_id=product_id,
                sku=product_id,
                name=name,
                url=href,
                source_type="html_card",
            )
            save_identity(store=self.store, source_id=product_id, sku=product_id, url=href, name=name)
            products.append(product)
        return ProductList(store=self.store, query=query, page=page, products=products)

    async def get_by_id(self, source_id: str) -> Product:
        data = await post_json(f"{self.base_url}/product/find_one/", {"lang": "ro", "id": source_id})
        product = Product(
            store=self.store,
            source_id=str(data.get("id") or source_id),
            sku=str(data.get("id") or source_id),
            name=str(data.get("name") or "Unknown product"),
            brand=data.get("brand"),
            category=data.get("category"),
            price=ProductPrice(current=to_float(data.get("price")), old=to_float(data.get("discount"))),
            availability="unknown",
            source_type="json_api",
            raw=data,
        )
        save_identity(store=self.store, source_id=product.source_id, sku=product.sku, name=product.name)
        return product

    async def get_by_url(self, url: str) -> Product:
        html = await get_text(url)
        jsonld = find_product_jsonld(html)
        if not jsonld:
            raise LookupError(f"Bomba product URL not parseable: {url}")
        product = product_from_jsonld(self.store, jsonld, fallback_url=url)
        product.source_type = "json_ld"
        url_id = self._id_from_url(url)
        product.source_id = product.source_id or url_id
        product.sku = product.sku or product.source_id
        save_identity(
            store=self.store,
            source_id=product.source_id,
            sku=product.sku,
            url=product.url or url,
            name=product.name,
        )
        return product

    def _id_from_url(self, url: str) -> str | None:
        match = re.search(r"-(\d+)/?$", url)
        return match.group(1) if match else None

