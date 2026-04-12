from app.models.product import Product, ProductList
from app.routes.products import _normalized_search
from app.search_cache import clear_search_cache

import pytest


class FakeAdapter:
    store = "fake"

    def __init__(self, native_pages: list[list[str]]) -> None:
        self.native_pages = native_pages
        self.calls: list[int] = []

    async def search(self, query: str, *, page: int = 1) -> ProductList:
        self.calls.append(page)
        names = self.native_pages[page - 1] if page <= len(self.native_pages) else []
        return ProductList(
            store=self.store,
            query=query,
            page=page,
            products=[Product(store=self.store, source_id=name, name=name) for name in names],
            total=sum(len(items) for items in self.native_pages),
        )


@pytest.mark.anyio
async def test_normalized_search_slices_native_pages() -> None:
    clear_search_cache()
    adapter = FakeAdapter(
        [
            [f"p{index}" for index in range(1, 34)],
            [f"p{index}" for index in range(34, 67)],
        ]
    )

    result = await _normalized_search(adapter, q="iphone", page=2, page_size=20)

    assert result.page == 2
    assert result.page_size == 20
    assert result.total == 66
    assert [product.source_id for product in result.products] == [f"p{index}" for index in range(21, 41)]
    assert adapter.calls == [1, 2]


@pytest.mark.anyio
async def test_normalized_search_reuses_cached_native_pages() -> None:
    clear_search_cache()
    adapter = FakeAdapter(
        [
            [f"p{index}" for index in range(1, 34)],
            [f"p{index}" for index in range(34, 67)],
        ]
    )

    first = await _normalized_search(adapter, q="iphone", page=1, page_size=20)
    second = await _normalized_search(adapter, q="iphone", page=2, page_size=20)

    assert [product.source_id for product in first.products] == [f"p{index}" for index in range(1, 21)]
    assert [product.source_id for product in second.products] == [f"p{index}" for index in range(21, 41)]
    assert adapter.calls == [1, 2]
    clear_search_cache()
