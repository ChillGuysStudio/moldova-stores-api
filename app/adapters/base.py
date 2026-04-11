from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.product import Product, ProductList


class ProductNotResolvedError(Exception):
    def __init__(self, store: str, source_id: str, message: str | None = None) -> None:
        self.store = store
        self.source_id = source_id
        self.message = message or (
            "This store needs URL mapping first. Use product search or by-url fetch to resolve it."
        )
        super().__init__(self.message)


class StoreAdapter(ABC):
    store: str
    base_url: str

    @abstractmethod
    async def search(self, query: str, *, page: int = 1) -> ProductList:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, source_id: str) -> Product:
        raise NotImplementedError

    @abstractmethod
    async def get_by_url(self, url: str) -> Product:
        raise NotImplementedError

