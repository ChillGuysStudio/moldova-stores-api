from app.normalizers.availability import normalize_availability
from app.normalizers.price import normalize_currency, to_float


def test_to_float_parses_common_price_strings():
    assert to_float("13 369.00") == 13369.0
    assert to_float("28399,50") == 28399.5


def test_normalize_currency_maps_lei_to_mdl():
    assert normalize_currency("lei") == "MDL"
    assert normalize_currency("MDL") == "MDL"


def test_normalize_availability_schema_urls():
    assert normalize_availability("https://schema.org/InStock") == "in_stock"
    assert normalize_availability("https://schema.org/OutOfStock") == "out_of_stock"

