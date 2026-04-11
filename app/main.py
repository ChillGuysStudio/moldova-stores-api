from fastapi import FastAPI

from app.routes.products import router as products_router
from app.routes.stores import router as stores_router
from app.storage.db import init_db


app = FastAPI(
    title="Moldova Stores Product API",
    description="Romanian-only read API for products from Moldovan stores.",
    version="0.1.0",
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


app.include_router(stores_router)
app.include_router(products_router)

