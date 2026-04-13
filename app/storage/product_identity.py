from __future__ import annotations

from dataclasses import dataclass

from app.storage.db import connect_postgres, connect_sqlite, get_identity_db_backend, init_db


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
    if get_identity_db_backend() == "postgres":
        _save_identity_postgres(store=store, source_id=source_id, url=url, sku=sku, name=name)
    else:
        _save_identity_sqlite(store=store, source_id=source_id, url=url, sku=sku, name=name)


def get_identity(store: str, source_id: str | int) -> ProductIdentity | None:
    init_db()
    if get_identity_db_backend() == "postgres":
        row = _get_identity_postgres(store, source_id)
    else:
        row = _get_identity_sqlite(store, source_id)

    if row is None:
        return None
    return ProductIdentity(
        store=row["store"],
        source_id=row["source_id"],
        url=row["url"],
        sku=row["sku"],
        name=row["name"],
    )


def _save_identity_sqlite(
    *,
    store: str,
    source_id: str | int,
    url: str | None,
    sku: str | int | None,
    name: str | None,
) -> None:
    with connect_sqlite() as db:
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


def _save_identity_postgres(
    *,
    store: str,
    source_id: str | int,
    url: str | None,
    sku: str | int | None,
    name: str | None,
) -> None:
    with connect_postgres() as db:
        with db.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO product_identity (store, source_id, url, sku, name, last_seen_at)
                VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT(store, source_id) DO UPDATE SET
                    url = COALESCE(excluded.url, product_identity.url),
                    sku = COALESCE(excluded.sku, product_identity.sku),
                    name = COALESCE(excluded.name, product_identity.name),
                    last_seen_at = CURRENT_TIMESTAMP
                """,
                (store, str(source_id), url, str(sku) if sku is not None else None, name),
            )


def _get_identity_sqlite(store: str, source_id: str | int):
    with connect_sqlite() as db:
        return db.execute(
            """
            SELECT store, source_id, url, sku, name
            FROM product_identity
            WHERE store = ? AND source_id = ?
            """,
            (store, str(source_id)),
        ).fetchone()


def _get_identity_postgres(store: str, source_id: str | int):
    with connect_postgres() as db:
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT store, source_id, url, sku, name
                FROM product_identity
                WHERE store = %s AND source_id = %s
                """,
                (store, str(source_id)),
            )
            return cursor.fetchone()
