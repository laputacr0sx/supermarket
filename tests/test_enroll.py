import pytest
from sqlalchemy import select

from store.domain.errors import DuplicateCard
from store.persist import repo
from store.persist.tables import Ledger
from store.services import cards


def test_enroll_child_with_opening_balance(session):
    card = cards.enroll(session, "aa:bb:cc:dd", "杏", role="child", opening_cents=1500)
    assert card.uid == "AABBCCDD"
    assert card.role == "child"
    account = repo.get_account(session, card.id)
    assert account is not None
    assert account.balance_cents == 1500
    rows = list(session.scalars(select(Ledger).where(Ledger.card_id == card.id)))
    assert len(rows) == 1
    assert rows[0].kind == "topup"
    assert rows[0].amount_cents == 1500


def test_enroll_duplicate_uid_rejected(seeded):
    with pytest.raises(DuplicateCard):
        cards.enroll(seeded, "DEADBEEF", "twin")


def test_enroll_staff_has_zero_shop_balance(session):
    card = cards.enroll(session, "0FF1CE00", "職員二", role="staff", opening_cents=0)
    assert card.role == "staff"
    account = repo.get_account(session, card.id)
    assert account is not None
    assert account.balance_cents == 0
