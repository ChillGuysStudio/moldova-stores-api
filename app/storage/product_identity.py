from __future__ import annotations

from dataclasses import dataclass

from app.storage.db import connect, init_db


@dataclass(frozen=True)
class ProductIdentity:
    store: str
    source_id: str
    url: str | None
    sku: str | None
    name: str | None


def save_identity(
    *,
    store: str,
    source_id: str | int | None,
    url: str | None = None,
    sku: str | int | None = None,
    name: str | None = None,
) -> None:
    if source_id is None:
        return
    init_db()
    with connect() as db:
        db.execute(
            """
            INSERT INTO product_identity (store, source_id, url, sku, name, last_seen_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(store, source_id) DO UPDATE SET
                url = COALESCE(excluded.url, product_identity.url),
                sku = COALESCE(excluded.sku, product_identity.sku),
                name = COALESCE(excluded.name, product_identity.name),
                last_seen_at = CURRENT_TIMESTAMP
            """,
            (store, str(source_id), url, str(sku) if sku is not None else None, name),
        )


def get_identity(store: str, source_id: str | int) -> ProductIdentity | None:
    init_db()
    with connect() as db:
        row = db.execute(
            """
            SELECT store, source_id, url, sku, name
            FROM product_identity
            WHERE store = ? AND source_id = ?
            """,
            (store, str(source_id)),
        ).fetchone()
    if row is None:
        return None
    return ProductIdentity(
        store=row["store"],
        source_id=row["source_id"],
        url=row["url"],
        sku=row["sku"],
        name=row["name"],
    )

