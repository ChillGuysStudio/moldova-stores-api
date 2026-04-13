from app.storage.db import get_database_url, get_identity_db_backend
from app.storage.product_identity import get_identity, save_identity

import pytest


def test_sqlite_identity_profile_persists_mapping(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("IDENTITY_DB_BACKEND", "sqlite")
    monkeypatch.setenv("PRODUCT_IDENTITY_DB", str(tmp_path / "identity.sqlite3"))

    save_identity(store="enter", source_id=263, sku=263, url="https://enter.online/old", name="Old")
    save_identity(store="enter", source_id=263, sku=263, url="https://enter.online/new", name="New")

    identity = get_identity("enter", 263)

    assert identity is not None
    assert identity.store == "enter"
    assert identity.source_id == "263"
    assert identity.sku == "263"
    assert identity.url == "https://enter.online/new"
    assert identity.name == "New"


def test_sqlite_identity_profile_does_not_overwrite_with_nulls(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("IDENTITY_DB_BACKEND", "sqlite")
    monkeypatch.setenv("PRODUCT_IDENTITY_DB", str(tmp_path / "identity.sqlite3"))

    save_identity(store="darwin", source_id="sku-1", sku="sku-1", url="https://darwin.md/product", name="Product")
    save_identity(store="darwin", source_id="sku-1", sku=None, url=None, name=None)

    identity = get_identity("darwin", "sku-1")

    assert identity is not None
    assert identity.sku == "sku-1"
    assert identity.url == "https://darwin.md/product"
    assert identity.name == "Product"


def test_postgres_profile_requires_database_url(monkeypatch) -> None:
    monkeypatch.setenv("IDENTITY_DB_BACKEND", "postgres")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    assert get_identity_db_backend() == "postgres"
    with pytest.raises(RuntimeError, match="DATABASE_URL is required"):
        get_database_url()


def test_missing_identity_profile_fails_clearly(monkeypatch) -> None:
    monkeypatch.delenv("IDENTITY_DB_BACKEND", raising=False)

    with pytest.raises(RuntimeError, match="IDENTITY_DB_BACKEND is required"):
        get_identity_db_backend()


def test_invalid_identity_profile_fails_clearly(monkeypatch) -> None:
    monkeypatch.setenv("IDENTITY_DB_BACKEND", "redis")

    with pytest.raises(ValueError, match="IDENTITY_DB_BACKEND"):
        get_identity_db_backend()
