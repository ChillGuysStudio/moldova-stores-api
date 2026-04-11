from __future__ import annotations

from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Query

from app.adapters import ADAPTERS, ProductNotResolvedError
from app.models.product import Product, ProductList


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


@router.get("/search", response_model=ProductList)
async def search_products(
    store: str = Query(..., description="Store key, e.g. smart, bomba, enter."),
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
) -> ProductList:
    adapter = _adapter_or_404(store)
    try:
        return await adapter.search(q, page=page)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


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

