"""Enroll cards. Staff vs child is a SQLite role, not chip data."""

from __future__ import annotations

from sqlalchemy.orm import Session

from store.domain.errors import DuplicateCard, InvalidLedger
from store.io.nfc import normalize_uid
from store.persist import repo
from store.persist.tables import Account, Card


def enroll(
    session: Session,
    uid: str,
    name: str,
    *,
    role: str = "child",
    opening_cents: int = 0,
) -> Card:
    uid = normalize_uid(uid)
    if role not in {"child", "staff"}:
        raise InvalidLedger(role)
    if opening_cents < 0:
        raise InvalidLedger("opening")
    if repo.get_card_by_uid(session, uid) is not None:
        raise DuplicateCard(uid)
    card = Card(uid=uid, child_name=name.strip() or uid, role=role, active=1)
    session.add(card)
    session.flush()
    session.add(Account(card_id=card.id, balance_cents=opening_cents))
    session.flush()
    return card
