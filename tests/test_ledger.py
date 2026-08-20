import pytest

from store.domain.errors import InactiveCard, InvalidLedger
from store.domain.money import yuan_to_cents
from store.persist import repo
from store.services.checkout import CheckoutItem, checkout
from store.services.ledger import apply_ledger, void_last
from tests.conftest import CEREAL


def test_topup(seeded):
    result = apply_ledger(seeded, "CAFEBABE", "topup", yuan_to_cents(10))
    assert result.balance_cents == yuan_to_cents(15)
    assert result.amount_cents == yuan_to_cents(10)


def test_reset_writes_negative_delta(seeded):
    result = apply_ledger(seeded, "DEADBEEF", "reset")
    assert result.balance_cents == 0
    assert result.amount_cents == -yuan_to_cents(30)


def test_inactive_card_rejected(seeded):
    with pytest.raises(InactiveCard):
        apply_ledger(seeded, "00DEAD", "topup", 100)


def test_topup_requires_positive(seeded):
    with pytest.raises(InvalidLedger):
        apply_ledger(seeded, "DEADBEEF", "topup", 0)


def test_void_last_refunds(seeded):
    checkout(seeded, "DEADBEEF", [CheckoutItem(CEREAL, 1)])
    result = void_last(seeded, "DEADBEEF")
    assert result.kind == "void_refund"
    assert result.amount_cents == yuan_to_cents(12)
    account = repo.get_account(seeded, repo.get_card_by_uid(seeded, "DEADBEEF").id)
    assert account.balance_cents == yuan_to_cents(30)
    cereal = repo.get_product_by_barcode(seeded, CEREAL)
    # stock stays consumed; void is money-only in v1
    assert cereal.stock == 9
