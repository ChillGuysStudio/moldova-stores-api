from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Literal


DEFAULT_DB_PATH = Path("data/product_identity.sqlite3")
IdentityDbBackend = Literal["sqlite", "postgres"]


def get_identity_db_backend() -> IdentityDbBackend:
    backend = os.environ.get("IDENTITY_DB_BACKEND")
    if backend is None:
        raise RuntimeError("IDENTITY_DB_BACKEND is required and must be either 'sqlite' or 'postgres'")
    backend = backend.strip().lower()
    if backend not in {"sqlite", "postgres"}:
        raise ValueError("IDENTITY_DB_BACKEND must be either 'sqlite' or 'postgres'")
    return backend  # type: ignore[return-value]


def get_db_path() -> Path:
    return Path(os.environ.get("PRODUCT_IDENTITY_DB", DEFAULT_DB_PATH))


def get_database_url() -> str:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required when IDENTITY_DB_BACKEND=postgres")
    return database_url


def connect_sqlite() -> sqlite3.Connection:
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def connect_postgres():
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise RuntimeError("Install psycopg to use IDENTITY_DB_BACKEND=postgres") from exc

    return psycopg.connect(get_database_url(), row_factory=dict_row)


def init_db() -> None:
    if get_identity_db_backend() == "postgres":
        _init_postgres()
    else:
        _init_sqlite()


def _init_sqlite() -> None:
    with connect_sqlite() as db:
        db.execute(_create_identity_table_sql())


def _init_postgres() -> None:
    with connect_postgres() as db:
        with db.cursor() as cursor:
            cursor.execute(_create_identity_table_sql())


def _create_identity_table_sql() -> str:
    return """
    CREATE TABLE IF NOT EXISTS product_identity (
        store TEXT NOT NULL,
        source_id TEXT NOT NULL,
        url TEXT,
        sku TEXT,
        name TEXT,
        last_seen_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (store, source_id)
    )
    """
