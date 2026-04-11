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
venv/bin/uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

## Endpoints

```http
GET /stores
GET /products/search?store={store}&q={query}&page={page}
GET /products/{store}/{id}
GET /products/by-url?url={product_url}
```

Examples:

```http
GET /products/search?store=smart&q=iphone&page=1
GET /products/bomba/1154205
GET /products/xstore/21351
GET /products/by-url?url=https://xstore.md/apple/iphone/apple-iphone-15-128gb-pink
```

## ID Lookup Rules

Direct or cold ID lookup:

- `smart`: Visely API lookup by SKU/id.
- `bomba`: `curl_cffi` + `POST /product/find_one/`.
- `maximum`: compare-cookie product JSON endpoint.
- `xstore`: search by numeric ID, parse exact `data-id`, then fetch the product URL.

Resolver-cache ID lookup:

- `enter`
- `darwin`

For Enter and Darwin, `GET /products/{store}/{id}` first checks the local SQLite resolver cache. The cache is populated by:

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

The SQLite database is created at:

```text
data/product_identity.sqlite3
```

Override it with:

```bash
PRODUCT_IDENTITY_DB=/path/to/product_identity.sqlite3 venv/bin/uvicorn app.main:app --reload
```

## Notes

Bomba uses `curl_cffi` from the start because normal HTTP clients were already confirmed to be blocked by Cloudflare in this environment.
