import pytest

from store.domain.errors import ProductNotSellable
from store.services import catalog
from tests.conftest import CEREAL, DRAFT, UNKNOWN_OK


def test_valid_unknown_becomes_one_draft(seeded):
    first = catalog.scan(seeded, UNKNOWN_OK)
    assert first.action == "learned"
    assert first.product is not None
    assert first.product.status == "draft"
    assert first.product.origin == "household"
    second = catalog.scan(seeded, UNKNOWN_OK)
    assert second.action == "pending"
    assert second.product.id == first.product.id


def test_invalid_inserts_nothing(seeded):
    before = catalog.scan(seeded, "not-a-code")
    assert before.action == "reject"
    assert before.product is None
    again = catalog.scan(seeded, "http://box")
    assert again.action == "reject"


def test_finish_without_name_stays_unready(seeded):
    product = catalog.lookup(seeded, DRAFT)
    assert product.status == "draft"
    with pytest.raises(ProductNotSellable):
        catalog.finish(seeded, DRAFT, name="   ", price_cents=300)
    seeded.refresh(product)
    assert product.status == "draft"


def test_ready_scan_is_sell(seeded):
    result = catalog.scan(seeded, CEREAL)
    assert result.action == "sell"
    assert result.product.name == "麥片"


def test_learn_off_rejects_unknown(seeded):
    result = catalog.scan(seeded, UNKNOWN_OK, learn=False)
    assert result.action == "reject"


def test_mint_store_drafts_are_random_valid(seeded):
    rows = catalog.mint_store_drafts(seeded, 5)
    codes = [r.barcode for r in rows]
    assert len(set(codes)) == 5
    assert all(r.origin == "store" and r.status == "draft" for r in rows)
    assert all(c.startswith("2") for c in codes)
