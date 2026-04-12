from __future__ import annotations

import re
from urllib.parse import quote

from app.adapters.base import StoreAdapter
from app.clients.http import get_json, get_text
from app.models.product import Product, ProductList, ProductPrice
from app.normalizers.price import normalize_currency, to_float
from app.normalizers.product import product_from_jsonld
from app.parsing.html import absolute_url, soup_from_html
from app.parsing.jsonld import find_product_jsonld
from app.storage.product_identity import save_identity


class MaximumAdapter(StoreAdapter):
    store = "maximum"
    base_url = "https://maximum.md"

    async def search(self, query: str, *, page: int = 1) -> ProductList:
        html = await get_text(
            f"{self.base_url}/ro/search/{page}?query={quote(query)}",
            headers={
                "accept": "text/html, */*; q=0.01",
                "x-requested-with": "XMLHttpRequest",
                "x-pjax": "true",
                "x-pjax-container": "#js-pjax-container",
            },
        )
        products = self._parse_search_cards(html)
        return ProductList(
            store=self.store,
            query=query,
            page=page,
            products=products,
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

    def _parse_search_cards(self, html: str) -> list[Product]:
        soup = soup_from_html(html)
        products: list[Product] = []
        seen: set[str] = set()

        for card in soup.select(".js-content.product__item"):
            title = card.select_one(".product__item__title a")
            source_id = self._id_from_card(card, title.get("href") if title else None)
            if not source_id or source_id in seen:
                continue
            seen.add(source_id)

            image_el = card.select_one(".product__item__image img")
            image = None
            if image_el:
                image = image_el.get("data-src") or image_el.get("src")
                image = absolute_url(self.base_url, image)

            url = absolute_url(self.base_url, title.get("href") if title else None)
            product = Product(
                store=self.store,
                source_id=source_id,
                sku=source_id,
                name=title.get_text(" ", strip=True) if title else "Unknown product",
                url=url,
                image=image,
                images=[image] if image else [],
                price=ProductPrice(
                    current=self._price_from_text(card.select_one(".product__item__price-current")),
                    old=self._price_from_text(card.select_one(".product__item__price-old")),
                    currency="MDL",
                ),
                availability="out_of_stock" if card.select_one(".product_not_in_shop, .not_in_shops") else "unknown",
                short_description=self._description_from_card(card),
                source_type="html_card",
                raw={"url": url},
            )
            save_identity(store=self.store, source_id=source_id, sku=source_id, url=url, name=product.name)
            products.append(product)

        return products

    def _id_from_card(self, card, href: str | None) -> str | None:
        element = card.select_one("[data-product], [data-id]")
        if element:
            product_id = element.get("data-product") or element.get("data-id")
            if product_id:
                return str(product_id)
        if href:
            match = re.search(r"/(\d+)/?$", href)
            if match:
                return match.group(1)
        return None

    def _price_from_text(self, element) -> float | None:
        if element is None:
            return None
        match = re.search(r"\d[\d\s.,]*", element.get_text(" ", strip=True))
        return to_float(match.group(0)) if match else None

    def _description_from_card(self, card) -> str | None:
        element = card.select_one(".product-item-description")
        if not element:
            return None
        code = element.select_one(".product-item-description-code")
        if code:
            code.decompose()
        text = element.get_text(" ", strip=True)
        return text or None

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
