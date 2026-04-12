from app.models.store import StoreCapabilities


STORE_CAPABILITIES: dict[str, StoreCapabilities] = {
    "smart": StoreCapabilities(
        store="smart",
        name="Smart.md",
        base_url="https://www.smart.md",
        supports_search=True,
        supports_url_fetch=True,
        supports_id_fetch="direct",
        notes="Uses Visely catalog/search API.",
    ),
    "bomba": StoreCapabilities(
        store="bomba",
        name="Bomba.md",
        base_url="https://bomba.md",
        supports_search=True,
        supports_url_fetch=True,
        supports_id_fetch="direct",
        notes="Uses curl_cffi because regular HTTP clients are blocked by Cloudflare.",
    ),
    "maximum": StoreCapabilities(
        store="maximum",
        name="Maximum.md",
        base_url="https://maximum.md",
        supports_search=True,
        supports_url_fetch=True,
        supports_id_fetch="direct",
        notes="Uses the Romanian PJAX search HTML fragment for search and compare-cookie product JSON for ID lookup.",
    ),
    "xstore": StoreCapabilities(
        store="xstore",
        name="Xstore.md",
        base_url="https://xstore.md",
        supports_search=True,
        supports_url_fetch=True,
        supports_id_fetch="search_resolved",
        notes="Cold ID lookup searches by numeric ID and parses exact data-id product card.",
    ),
    "enter": StoreCapabilities(
        store="enter",
        name="Enter.online",
        base_url="https://enter.online",
        supports_search=True,
        supports_url_fetch=True,
        supports_id_fetch="cached_or_resolved",
        notes="Cold numeric ID lookup is unreliable; search/by-url fills the resolver cache.",
    ),
    "darwin": StoreCapabilities(
        store="darwin",
        name="Darwin.md",
        base_url="https://darwin.md",
        supports_search=True,
        supports_url_fetch=True,
        supports_id_fetch="cached_or_resolved",
        notes="Uses the Romanian HTML search page; cold numeric ID lookup is unreliable, search/by-url fills the resolver cache.",
    ),
}
