import pytest

from store.domain.errors import (
    InactiveCard,
    InsufficientFunds,
    ProductNotSellable,
    StaffCannotShop,
    UnknownCard,
    UnknownProduct,
)
from sqlalchemy.orm import Session

from store.domain.money import yuan_to_cents
from store.persist import repo
from store.persist.tables import Account
from store.services.checkout import CheckoutItem, checkout
from tests.conftest import CEREAL, DRAFT, MILK


def _account(session: Session, uid: str) -> Account:
    card = repo.get_card_by_uid(session, uid)
    assert card is not None
    account = repo.get_account(session, card.id)
    assert account is not None
    return account


def test_happy_path_debits_and_writes_sale(seeded: Session) -> None:
    result = checkout(
        seeded,
        "DEADBEEF",
        [CheckoutItem(CEREAL, 1), CheckoutItem(MILK, 1)],
    )
    assert result.total_cents == yuan_to_cents(20)
    assert result.balance_cents == yuan_to_cents(10)
    assert _account(seeded, "DEADBEEF").balance_cents == yuan_to_cents(10)
    cereal = repo.get_product_by_barcode(seeded, CEREAL)
    assert cereal is not None
    assert cereal.stock == 9


def test_insufficient_funds_leaves_balance_and_stock(seeded: Session) -> None:
    cereal = repo.get_product_by_barcode(seeded, CEREAL)
    assert cereal is not None
    before_stock = cereal.stock
    before_bal = _account(seeded, "CAFEBABE").balance_cents
    with pytest.raises(InsufficientFunds) as err:
        checkout(seeded, "CAFEBABE", [CheckoutItem(CEREAL, 1), CheckoutItem(MILK, 1)])
    assert err.value.need_cents == yuan_to_cents(15)
    seeded.rollback()
    seeded.expire_all()
    cereal = repo.get_product_by_barcode(seeded, CEREAL)
    assert cereal is not None
    assert cereal.stock == before_stock
    assert _account(seeded, "CAFEBABE").balance_cents == before_bal


def test_unknown_card(seeded: Session) -> None:
    with pytest.raises(UnknownCard):
        checkout(seeded, "NOPE", [CheckoutItem(CEREAL, 1)])


def test_unknown_sku(seeded: Session) -> None:
    with pytest.raises(UnknownProduct):
        checkout(seeded, "DEADBEEF", [CheckoutItem("0000000000000", 1)])


def test_draft_sku_is_not_sold(seeded: Session) -> None:
    with pytest.raises(ProductNotSellable):
        checkout(seeded, "DEADBEEF", [CheckoutItem(DRAFT, 1)])
    assert _account(seeded, "DEADBEEF").balance_cents == yuan_to_cents(30)


def test_staff_card_cannot_shop(seeded: Session) -> None:
    with pytest.raises(StaffCannotShop):
        checkout(seeded, "0FF1CE", [CheckoutItem(CEREAL, 1)])


def test_inactive_card_rejected(seeded: Session) -> None:
    with pytest.raises(InactiveCard):
        checkout(seeded, "00DEAD", [CheckoutItem(CEREAL, 1)])
