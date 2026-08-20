from store.domain.barcode import (
    BarcodeKind,
    classify,
    ean13_check,
    mint_store_ean13,
    normalize,
)


def test_upc_a_pads_to_ean13():
    assert normalize("012345678905") == "0012345678905"


def test_spaces_and_dashes_stripped():
    assert normalize(" 489-0000 00001 ") == "0489000000001"


def test_ean13_check_vector():
    # 590123412345 + 7 is a known-valid GTIN
    assert ean13_check("590123412345") == "7"
    assert classify("5901234123457") is BarcodeKind.VALID_EAN13


def test_isbn13_is_ean13():
    body = "978014103614"
    code = body + ean13_check(body)
    assert classify(code) is BarcodeKind.VALID_EAN13


def test_bad_check_digit_is_invalid():
    assert classify("5901234123450") is BarcodeKind.INVALID


def test_url_is_invalid():
    assert classify(normalize("http://box.example/x")) is BarcodeKind.INVALID


def test_mint_stays_in_200_299_and_is_valid():
    codes = {mint_store_ean13(set()) for _ in range(20)}
    assert len(codes) == 20
    for code in codes:
        assert classify(code) is BarcodeKind.VALID_EAN13
        assert 200 <= int(code[:3]) <= 299


def test_mint_is_not_sequential():
    codes = [mint_store_ean13(set()) for _ in range(8)]
    bodies = [int(c[:12]) for c in codes]
    sequential = all(b == bodies[0] + i for i, b in enumerate(bodies))
    assert not sequential


def test_mint_respects_existing():
    first = mint_store_ean13(set())
    second = mint_store_ean13({first})
    assert first != second


def test_same_raw_forms_normalize_equal():
    assert normalize("012345678905") == normalize("0012345678905")
