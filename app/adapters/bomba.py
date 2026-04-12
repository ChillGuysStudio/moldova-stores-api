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
        url = f"{self.base_url}/ro/cautare/?query={quote(query)}"
        if page > 1:
            url += f"&page={page}"
        html = await get_text(url)
        soup = soup_from_html(html)
        products = self._parse_search_cards(soup)
        return ProductList(
            store=self.store,
            query=query,
            page=page,
            products=products,
            total=self._total_from_search(soup),
        )

    def _parse_search_cards(self, soup) -> list[Product]:
        products: list[Product] = []
        seen: set[str] = set()

        for card in soup.select(".product__item"):
            link = card.select_one('a.name[href*="/ro/product/"], a[href*="/ro/product/"]')
            if not link:
                continue
            href = absolute_url(self.base_url, link.get("href"))
            if not href:
                continue
            product_id = link.get("data-ecom_id") or card.get("data-id") or self._id_from_url(href)
            name = link.get_text(" ", strip=True)
            if not product_id or not name or product_id in seen:
                continue
            seen.add(product_id)

            price = to_float(link.get("data-ecom_price") or self._text_from(card, ".product-price .price"))
            discount = to_float(link.get("data-ecom_discount"))
            old_price = None
            if price is not None and discount:
                old_price = price + discount

            image = self._image_from_card(card)
            product = Product(
                store=self.store,
                source_id=product_id,
                sku=product_id,
                name=name,
                brand=link.get("data-ecom_brand") or None,
                category=link.get("data-ecom_category") or None,
                url=href,
                image=image,
                images=[image] if image else [],
                price=ProductPrice(current=price, old=old_price),
                availability="in_stock" if card.select_one(".button-cart, .check_color_and_size") else "unknown",
                source_type="html_card",
                raw={
                    "data_articol": card.get("data-articol"),
                    "data_ecom_index": link.get("data-ecom_index"),
                },
            )
            save_identity(store=self.store, source_id=product_id, sku=product_id, url=href, name=name)
            products.append(product)

        return products

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

    def _image_from_card(self, card) -> str | None:
        image = card.select_one(".product__photo img")
        if not image:
            return None
        return absolute_url(self.base_url, image.get("data-src") or image.get("src"))

    def _text_from(self, card, selector: str) -> str | None:
        element = card.select_one(selector)
        return element.get_text(" ", strip=True) if element else None

    def _total_from_search(self, soup) -> int | None:
        element = soup.select_one(".product_count")
        if not element:
            return None
        match = re.search(r"\d+", element.get_text(" ", strip=True))
        return int(match.group(0)) if match else None
