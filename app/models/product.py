from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl


Availability = Literal["in_stock", "out_of_stock", "preorder", "unknown"]
SourceType = Literal[
    "json_api",
    "json_ld",
    "html_card",
    "livewire_snapshot",
    "cookie_based_json",
    "mixed",
]


class ProductPrice(BaseModel):
    current: float | None = None
    old: float | None = None
    currency: str = "MDL"


class Product(BaseModel):
    store: str
    source_id: str | None = None
    sku: str | None = None
    name: str
    brand: str | None = None
    category: str | None = None
    url: str | None = None
    image: str | None = None
    images: list[str] = Field(default_factory=list)
    price: ProductPrice = Field(default_factory=ProductPrice)
    availability: Availability = "unknown"
    short_description: str | None = None
    source_type: SourceType = "mixed"
    raw: dict[str, Any] = Field(default_factory=dict)


class ProductList(BaseModel):
    store: str
    query: str
    page: int = 1
    products: list[Product]
    total: int | None = None


class ProductLookupError(BaseModel):
    error: str
    store: str | None = None
    source_id: str | None = None
    message: str
