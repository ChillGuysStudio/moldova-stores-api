from app.adapters.base import StoreAdapter, ProductNotResolvedError
from app.adapters.bomba import BombaAdapter
from app.adapters.darwin import DarwinAdapter
from app.adapters.enter import EnterAdapter
from app.adapters.maximum import MaximumAdapter
from app.adapters.smart import SmartAdapter
from app.adapters.xstore import XstoreAdapter


ADAPTERS: dict[str, StoreAdapter] = {
    "bomba": BombaAdapter(),
    "darwin": DarwinAdapter(),
    "enter": EnterAdapter(),
    "maximum": MaximumAdapter(),
    "smart": SmartAdapter(),
    "xstore": XstoreAdapter(),
}

__all__ = ["ADAPTERS", "StoreAdapter", "ProductNotResolvedError"]

