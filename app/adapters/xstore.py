from __future__ import annotations

from urllib.parse import quote

from app.adapters.base import StoreAdapter
from app.clients.http import get_text
from app.models.product import Product, ProductList, ProductPrice
from app.normalizers.price import to_float
from app.normalizers.product import product_from_jsonld
from app.parsing.html import absolute_url, soup_from_html
from app.parsing.jsonld import find_product_jsonld
from app.storage.product_identity import get_identity, save_identity


class XstoreAdapter(StoreAdapter):
    store = "xstore"
    base_url = "https://xstore.md"

    async def search(self, query: str, *, page: int = 1) -> ProductList:
        url = f"{self.base_url}/search?search={quote(query)}"
        if page > 1:
            url += f"&page={page}"
        html = await get_text(url)
        products = self._parse_cards(html)
        return ProductList(store=self.store, query=query, page=page, products=products)

    async def get_by_id(self, source_id: str) -> Product:
        identity = get_identity(self.store, source_id)
        if identity and identity.url and "javascript:" not in identity.url:
            return await self.get_by_url(identity.url)

        results = await self.search(source_id)
        exact = next((item for item in results.products if item.source_id == str(source_id) and item.url), None)
        if not exact:
            raise LookupError(f"Xstore product {source_id} not found")
        return await self.get_by_url(exact.url)

    async def get_by_url(self, url: str) -> Product:
        html = await get_text(url)
        jsonld = find_product_jsonld(html)
        if not jsonld:
            raise LookupError(f"Xstore product URL not parseable: {url}")
        product = product_from_jsonld(self.store, jsonld, fallback_url=url)
        save_identity(
            store=self.store,
            source_id=product.source_id,
            sku=product.sku,
            url=product.url or url,
            name=product.name,
        )
        return product

    def _parse_cards(self, html: str) -> list[Product]:
        soup = soup_from_html(html)
        products: list[Product] = []
        seen: set[str] = set()
        for element in soup.select("[data-id][data-p='item']"):
            source_id = element.get("data-id")
            if not source_id or source_id in seen:
                continue
            seen.add(source_id)
            card = element.find_parent("figure", class_="card-product") or element.find_parent()
            while card and not card.select_one("a.img-wrap[href], a.xp-title[href]"):
                card = card.find_parent()
            link = card.select_one("a.img-wrap[href], a.xp-title[href]") if card else None
            url = absolute_url(self.base_url, link.get("href") if link else None)
            image_el = card.select_one("img[src]") if card else None
            image = absolute_url(self.base_url, image_el.get("src") if image_el else None)
            product = Product(
                store=self.store,
                source_id=source_id,
                sku=source_id,
                name=element.get("data-name") or (link.get_text(" ", strip=True) if link else "Unknown product"),
                brand=element.get("data-brand"),
                category=element.get("data-category"),
                url=url,
                image=image,
                images=[image] if image else [],
                price=ProductPrice(current=to_float(element.get("data-price")), currency="MDL"),
                availability="unknown",
                source_type="html_card",
                raw={key: value for key, value in element.attrs.items() if key.startswith("data-")},
            )
            save_identity(store=self.store, source_id=source_id, sku=source_id, url=url, name=product.name)
            products.append(product)
        return products
