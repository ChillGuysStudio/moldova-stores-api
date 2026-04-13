# Moldova Stores Product API

Romanian-only read API for product data from Moldovan stores, excluding `999.md`.

## Scope

Supported stores:

- `bomba`
- `smart`
- `enter`
- `darwin`
- `maximum`
- `xstore`

V1 intentionally does not include language selection, autocomplete suggestions, credit/installment data, cart, wishlist, checkout, preorder, or lead endpoints.

## Install

```bash
python3 -m venv venv
venv/bin/pip install wheel
venv/bin/pip install --no-build-isolation -e ".[dev]"
```

## Run

```bash
IDENTITY_DB_BACKEND=sqlite venv/bin/uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

## Render Deploy

Use these commands for a Render Python web service:

```bash
pip install -r requirements.txt
```

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Set these environment variables:

```bash
IDENTITY_DB_BACKEND=postgres
DATABASE_URL=postgresql://user:password@host:5432/dbname
SEARCH_CACHE_TTL_SECONDS=300
SEARCH_CACHE_MAX_ENTRIES=512
SELF_PING_BASE_URL=https://your-api.onrender.com
```

Optional self-ping settings:

```bash
SELF_PING_BASE_URL=https://your-api.onrender.com
SELF_PING_INTERVAL_SECONDS=780
```

When `SELF_PING_BASE_URL` is set, the app sends a best-effort request to `/ping` every 13 minutes.

## Endpoints

```http
GET /stores
GET /products/search?q={query}&page={page}&page_size={page_size}
GET /products/search?stores={store1},{store2}&q={query}&page={page}&page_size={page_size}
GET /products/{store}/{id}
GET /products/by-url?url={product_url}
```

Examples:

```http
GET /products/search?stores=smart&q=iphone&page=1
GET /products/search?stores=smart,xstore&q=iphone&page=1
GET /products/search?q=iphone&page=1&page_size=20
GET /products/bomba/1154205
GET /products/xstore/21351
GET /products/by-url?url=https://xstore.md/apple/iphone/apple-iphone-15-128gb-pink
```

Search behavior:

- `stores=smart` searches one store and returns a grouped multi-store response.
- `stores=smart,xstore` searches selected stores in parallel and groups results by store.
- Omitting `stores` searches all supported stores in parallel.
- `page` and `page_size` are normalized by this API. `page=1&page_size=20` returns up to 20 products per store, even if a store's native page has 20, 33, 40, or 64 products.
- Native store search pages are cached in memory for a short time, so normalized pagination can reuse page data instead of refetching the same upstream pages.
- Multi-store search isolates errors per store, so one failing upstream does not break the whole response.

Search cache settings:

```bash
SEARCH_CACHE_TTL_SECONDS=300
SEARCH_CACHE_MAX_ENTRIES=512
```

Set `SEARCH_CACHE_TTL_SECONDS=0` to disable the temporary search cache.

## ID Lookup Rules

Direct or cold ID lookup:

- `smart`: Visely API lookup by SKU/id.
- `bomba`: `curl_cffi` + `POST /product/find_one/`.
- `maximum`: compare-cookie product JSON endpoint.
- `xstore`: search by numeric ID, parse exact `data-id`, then fetch the product URL.

Resolver-cache ID lookup:

- `enter`
- `darwin`

For Enter and Darwin, `GET /products/{store}/{id}` first checks the resolver cache. The cache is populated by:

- `GET /products/search?...`
- `GET /products/by-url?...`

If an Enter or Darwin product ID has not been resolved yet, the API returns:

```json
{
  "error": "product_id_not_resolved",
  "store": "enter",
  "source_id": "263",
  "message": "This store needs URL mapping first. Use product search or by-url fetch to resolve it."
}
```

## Resolver Cache

Choose the resolver-cache backend explicitly. `IDENTITY_DB_BACKEND` is required:

```bash
IDENTITY_DB_BACKEND=sqlite
```

or:

```bash
IDENTITY_DB_BACKEND=postgres
DATABASE_URL=postgresql://user:password@host:5432/dbname
```

The SQLite profile creates its database at:

```text
data/product_identity.sqlite3
```

Override it with:

```bash
PRODUCT_IDENTITY_DB=/path/to/product_identity.sqlite3 venv/bin/uvicorn app.main:app --reload
```

When `IDENTITY_DB_BACKEND=postgres`, `DATABASE_URL` is required and the app will fail clearly if it is missing.

## Notes

Bomba uses `curl_cffi` from the start because normal HTTP clients were already confirmed to be blocked by Cloudflare in this environment.
