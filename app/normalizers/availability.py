from app.models.product import Availability


def normalize_availability(value: object) -> Availability:
    if value is None:
        return "unknown"

    text = str(value).lower()
    if "instock" in text or text in {"1", "true", "in_stock"}:
        return "in_stock"
    if "outofstock" in text or "out_of_stock" in text or text in {"0", "false"}:
        return "out_of_stock"
    if "preorder" in text or "precomanda" in text:
        return "preorder"
    return "unknown"

