from __future__ import annotations

from typing import Any

from app.models.product import Product, ProductPrice
from app.normalizers.availability import normalize_availability
from app.normalizers.price import normalize_currency, to_float


def _brand_name(value: Any) -> str | None:
    if isinstance(value, dict):
        return value.get("name")
    if value:
        return str(value)
    return None


def _offers(value: Any) -> dict[str, Any]:
    if isinstance(value, list):
        return value[0] if value and isinstance(value[0], dict) else {}
    return value if isinstance(value, dict) else {}


def product_from_jsonld(store: str, data: dict[str, Any], *, fallback_url: str | None = None) -> Product:
    offers = _offers(data.get("offers"))
    images_value = data.get("image") or []
    images = images_value if isinstance(images_value, list) else [images_value]
    images = [str(image) for image in images if image]
    source_id = data.get("sku") or data.get("mpn")
    url = data.get("url") or offers.get("url") or fallback_url

    return Product(
        store=store,
        source_id=str(source_id) if source_id is not None else None,
        sku=str(data.get("sku")) if data.get("sku") is not None else None,
        name=str(data.get("name") or "Unknown product"),
        brand=_brand_name(data.get("brand")),
        category=str(data.get("category")) if data.get("category") else None,
        url=str(url) if url else None,
        image=images[0] if images else None,
        images=images,
        price=ProductPrice(
            current=to_float(offers.get("price")),
            old=None,
            currency=normalize_currency(offers.get("priceCurrency")),
        ),
        availability=normalize_availability(offers.get("availability")),
        short_description=str(data.get("description")) if data.get("description") else None,
        source_type="json_ld",
        raw=data,
    )

