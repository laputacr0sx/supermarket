"""Enroll cards. Staff vs child is a SQLite role, not chip data."""

from __future__ import annotations

from sqlalchemy.orm import Session

from store.domain.errors import DuplicateCard, InvalidLedger, UnknownCard
from store.domain.uid import normalize_uid
from store.persist import repo
from store.persist.tables import Account, Card
from store.services import ledger


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
    label = name.strip()
    if not label:
        raise InvalidLedger("name")
    card = Card(uid=uid, child_name=label, role=role, active=1)
    session.add(card)
    session.flush()
    session.add(Account(card_id=card.id, balance_cents=0))
    session.flush()
    if opening_cents > 0:
        ledger.apply_ledger(session, uid, "topup", opening_cents)
    return card


def deactivate(session: Session, uid: str) -> Card:
    card = repo.get_card_by_uid(session, normalize_uid(uid))
    if card is None:
        raise UnknownCard(uid)
    card.active = 0
    session.flush()
    return card


def list_cards(session: Session) -> list[Card]:
    return repo.list_cards(session)
