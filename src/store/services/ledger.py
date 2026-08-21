from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from store.domain.errors import InactiveCard, InvalidLedger, NothingToVoid, UnknownCard
from store.persist import repo
from store.persist.tables import Account, Card, Ledger, Sale


@dataclass(frozen=True)
class LedgerResult:
    kind: str
    amount_cents: int
    balance_cents: int
    sale_id: int | None = None


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def list_today(session: Session) -> list[Sale]:
    return repo.list_sales_on(session, datetime.now(UTC).date().isoformat())


def _live_account(session: Session, uid: str) -> tuple[Card, Account]:
    card = repo.get_card_by_uid(session, uid.upper().replace(":", "").replace(" ", ""))
    if card is None:
        raise UnknownCard(uid)
    if not card.active:
        raise InactiveCard(uid)
    account = repo.get_account(session, card.id)
    if account is None:
        raise UnknownCard(uid)
    return card, account


def apply_ledger(
    session: Session,
    uid: str,
    kind: str,
    amount_cents: int | None = None,
) -> LedgerResult:
    card, account = _live_account(session, uid)
    now = _now()
    if kind == "topup":
        if amount_cents is None or amount_cents <= 0:
            raise InvalidLedger("topup requires amount_cents > 0")
        account.balance_cents += amount_cents
        delta = amount_cents
    elif kind == "reset":
        delta = -account.balance_cents
        account.balance_cents = 0
    else:
        raise InvalidLedger(kind)
    session.add(
        Ledger(
            card_id=card.id,
            kind=kind,
            amount_cents=delta,
            created_at=now,
        )
    )
    session.flush()
    return LedgerResult(kind, delta, account.balance_cents)


def void_last(session: Session, uid: str | None = None) -> LedgerResult:
    card = None
    card_id = None
    if uid:
        card, _ = _live_account(session, uid)
        card_id = card.id
    sale = repo.last_open_sale(session, card_id)
    if sale is None:
        raise NothingToVoid()
    account = repo.get_account(session, sale.card_id)
    if account is None:
        raise UnknownCard(str(sale.card_id))
    now = _now()
    sale.voided_at = now
    account.balance_cents += sale.total_cents
    session.add(
        Ledger(
            card_id=sale.card_id,
            kind="void_refund",
            amount_cents=sale.total_cents,
            sale_id=sale.id,
            created_at=now,
        )
    )
    session.flush()
    return LedgerResult("void_refund", sale.total_cents, account.balance_cents, sale.id)
