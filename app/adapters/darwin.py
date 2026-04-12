from __future__ import annotations

import json
import re
from urllib.parse import quote

from app.adapters.base import ProductNotResolvedError, StoreAdapter
from app.clients.http import get_text
from app.models.product import Product, ProductList, ProductPrice
from app.normalizers.price import to_float
from app.normalizers.product import product_from_jsonld
from app.parsing.html import absolute_url, soup_from_html
from app.parsing.jsonld import find_product_jsonld
from app.storage.product_identity import get_identity, save_identity


class DarwinAdapter(StoreAdapter):
    store = "darwin"
    base_url = "https://darwin.md"

    async def search(self, query: str, *, page: int = 1) -> ProductList:
        html = await get_text(f"{self.base_url}/cautare?keywords={quote(query)}&page={page}")
        soup = soup_from_html(html)
        products = self._parse_search_cards(soup)
        return ProductList(
            store=self.store,
            query=query,
            page=page,
            products=products,
            total=self._total_from_search(soup),
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

    def _parse_search_cards(self, soup) -> list[Product]:
        products: list[Product] = []
        seen: set[str] = set()

        for card in soup.select(".product-items-5.ga-list .product-card.product-item"):
            link = self._product_link_from_card(card)
            if not link:
                continue
            url = absolute_url(self.base_url, link.get("href"))
            ga4_item = self._ga4_item_from_link(link)
            source_id = ga4_item.get("item_id")
            if not url or not source_id or source_id in seen:
                continue

            name = self._name_from_card(card, ga4_item)
            if not name:
                continue
            seen.add(source_id)

            image = self._image_from_card(card)
            product = Product(
                store=self.store,
                source_id=source_id,
                sku=source_id,
                name=name,
                brand=ga4_item.get("item_brand"),
                category=ga4_item.get("item_category"),
                url=url,
                image=image,
                images=[image] if image else [],
                price=self._price_from_card(card, ga4_item),
                availability="unknown",
                short_description=self._description_from_card(card, name),
                source_type="html_card",
                raw={"url": url, "ga4_item": ga4_item},
            )
            save_identity(store=self.store, source_id=source_id, sku=source_id, url=url, name=product.name)
            products.append(product)

        return products

    def _product_link_from_card(self, card):
        return card.select_one('a.product-link[href$=".html"], a[href$=".html"]')

    def _ga4_item_from_link(self, link) -> dict:
        raw = link.get("data-ga4")
        if not raw:
            return {}
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        ecommerce = payload.get("ecommerce") or {}
        items = ecommerce.get("items") or []
        return items[0] if items and isinstance(items[0], dict) else {}

    def _image_from_card(self, card) -> str | None:
        image = card.select_one(".product-img img, img")
        if not image:
            return None
        return absolute_url(self.base_url, image.get("data-src") or image.get("src"))

    def _name_from_card(self, card, ga4_item: dict) -> str | None:
        title = card.select_one(".title-product")
        text = title.get_text(" ", strip=True) if title else ga4_item.get("item_name")
        return text or None

    def _description_from_card(self, card, name: str) -> str | None:
        description = card.select_one(".description-product, .product-description, .color-80")
        if description:
            return self._clean_description(description.get_text(" ", strip=True))

        link = self._product_link_from_card(card)
        if not link:
            return None
        text = link.get_text(" ", strip=True)
        if text.startswith(name):
            text = text[len(name) :].strip()
        text = re.sub(r"\bCashback\s+\d+(?:[.,]\d+)?\s+lei\b", "", text, flags=re.IGNORECASE).strip()
        return self._clean_description(text)

    def _clean_description(self, text: str) -> str | None:
        text = text.strip()
        if text.lower() in {"loading", "loading..."}:
            return None
        return text or None

    def _price_from_card(self, card, ga4_item: dict) -> ProductPrice:
        current = to_float(ga4_item.get("price"))
        discount = to_float(ga4_item.get("discount"))
        old = current + discount if current is not None and discount else None
        if current is None:
            price = card.select_one(".price, .color-green")
            current = to_float(price.get_text(" ", strip=True)) if price else None
        return ProductPrice(current=current, old=old, currency="MDL")

    def _total_from_search(self, soup) -> int | None:
        text = soup.get_text(" ", strip=True)
        match = re.search(r"Produse\s+g[aă]site:\s*(\d[\d\s]*)", text, flags=re.IGNORECASE)
        if not match:
            return None
        return int(match.group(1).replace(" ", ""))
