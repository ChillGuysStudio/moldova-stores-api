from fastapi import APIRouter

from app.config import STORE_CAPABILITIES
from app.models.store import StoreCapabilities


router = APIRouter(tags=["stores"])


@router.get("/stores", response_model=list[StoreCapabilities])
async def list_stores() -> list[StoreCapabilities]:
    return list(STORE_CAPABILITIES.values())

