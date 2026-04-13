import asyncio

from fastapi import FastAPI

from app.routes.products import router as products_router
from app.routes.stores import router as stores_router
from app.self_ping import get_self_ping_url, self_ping_loop
from app.storage.db import init_db


app = FastAPI(
    title="Moldova Stores Product API",
    description="Romanian-only read API for products from Moldovan stores.",
    version="0.1.0",
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    if get_self_ping_url():
        app.state.self_ping_task = asyncio.create_task(self_ping_loop())


@app.on_event("shutdown")
async def on_shutdown() -> None:
    task = getattr(app.state, "self_ping_task", None)
    if task is None:
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app.include_router(stores_router)
app.include_router(products_router)


@app.get("/ping")
async def ping() -> dict[str, str]:
    return {"status": "ok"}
