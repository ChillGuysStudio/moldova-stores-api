from __future__ import annotations


def to_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = str(value).replace(" ", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def normalize_currency(value: object) -> str:
    if value is None:
        return "MDL"
    text = str(value).upper()
    if text in {"LEI", "MDL"}:
        return "MDL"
    return text
