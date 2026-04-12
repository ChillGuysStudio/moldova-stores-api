from __future__ import annotations

import asyncio
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Query

from app.adapters import ADAPTERS, ProductNotResolvedError
from app.models.product import MultiStoreProductSearch, Product, ProductList, StoreSearchError
from app.search_cache import cached_native_search


router = APIRouter(prefix="/products", tags=["products"])


HOST_TO_STORE = {
    "bomba.md": "bomba",
    "www.bomba.md": "bomba",
    "www.smart.md": "smart",
    "smart.md": "smart",
    "enter.online": "enter",
    "www.enter.online": "enter",
    "darwin.md": "darwin",
    "www.darwin.md": "darwin",
    "maximum.md": "maximum",
    "www.maximum.md": "maximum",
    "xstore.md": "xstore",
    "www.xstore.md": "xstore",
}


@router.get("/search")
async def search_products(
    q: str = Query(..., min_length=1),
    stores: str | None = Query(None, description="Comma-separated store keys. Omit to search all."),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, description="Normalized number of products returned per store."),
) -> MultiStoreProductSearch:
    selected_stores = _selected_stores(stores=stores)
    results = await asyncio.gather(
        *[_search_store(store_key, q=q, page=page, page_size=page_size) for store_key in selected_stores],
        return_exceptions=True,
    )
    response = MultiStoreProductSearch(query=q, page=page, page_size=page_size, stores=selected_stores)
    for store_key, result in zip(selected_stores, results):
        if isinstance(result, ProductList):
            response.results[store_key] = result
        else:
            response.errors[store_key] = StoreSearchError(store=store_key, message=str(result))
    return response


async def _search_store(store: str, *, q: str, page: int, page_size: int) -> ProductList:
    adapter = _adapter_or_404(store)
    return await _normalized_search(adapter, q=q, page=page, page_size=page_size)


async def _normalized_search(adapter, *, q: str, page: int, page_size: int) -> ProductList:
    start = (page - 1) * page_size
    end = start + page_size
    products: list[Product] = []
    seen_native_pages: set[tuple[str | None, ...]] = set()
    total: int | None = None
    native_page = 1

    while len(products) < end:
        result = await cached_native_search(adapter, query=q, page=native_page)
        if total is None:
            total = result.total
        if not result.products:
            break

        native_signature = tuple(product.source_id for product in result.products)
        if native_signature in seen_native_pages:
            break
        seen_native_pages.add(native_signature)

        products.extend(result.products)
        if total is not None and len(products) >= total:
            break

        native_page += 1

    return ProductList(
        store=adapter.store,
        query=q,
        page=page,
        page_size=page_size,
        products=products[start:end],
        total=total,
    )


def _selected_stores(*, stores: str | None) -> list[str]:
    if stores:
        selected = [item.strip() for item in stores.split(",") if item.strip()]
    else:
        selected = list(ADAPTERS.keys())

    if not selected:
        raise HTTPException(status_code=400, detail="No stores selected")

    unsupported = [item for item in selected if item not in ADAPTERS]
    if unsupported:
        raise HTTPException(status_code=404, detail=f"Unsupported store(s): {', '.join(unsupported)}")

    return selected


@router.get("/by-url", response_model=Product)
async def get_product_by_url(url: str = Query(..., description="Absolute product URL.")) -> Product:
    store = _store_from_url(url)
    adapter = _adapter_or_404(store)
    try:
        return await adapter.get_by_url(url)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/{store}/{source_id}", response_model=Product)
async def get_product_by_id(store: str, source_id: str) -> Product:
    adapter = _adapter_or_404(store)
    try:
        return await adapter.get_by_id(source_id)
    except ProductNotResolvedError as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "product_id_not_resolved",
                "store": exc.store,
                "source_id": exc.source_id,
                "message": exc.message,
            },
        ) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


def _adapter_or_404(store: str):
    adapter = ADAPTERS.get(store)
    if adapter is None:
        raise HTTPException(status_code=404, detail=f"Unsupported store: {store}")
    return adapter


def _store_from_url(url: str) -> str:
    host = urlparse(url).netloc.lower()
    store = HOST_TO_STORE.get(host)
    if not store:
        raise HTTPException(status_code=400, detail=f"Unsupported product URL host: {host}")
    return store
