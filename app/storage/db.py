from __future__ import annotations

import os
import sqlite3
from pathlib import Path


DEFAULT_DB_PATH = Path("data/product_identity.sqlite3")


def get_db_path() -> Path:
    return Path(os.environ.get("PRODUCT_IDENTITY_DB", DEFAULT_DB_PATH))


def connect() -> sqlite3.Connection:
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with connect() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS product_identity (
                store TEXT NOT NULL,
                source_id TEXT NOT NULL,
                url TEXT,
                sku TEXT,
                name TEXT,
                last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (store, source_id)
            )
            """
        )

