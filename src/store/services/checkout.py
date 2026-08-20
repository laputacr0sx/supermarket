from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from store.domain import barcode as bc
from store.domain.errors import (
    InactiveCard,
    InsufficientFunds,
    InsufficientStock,
    ProductNotSellable,
    StaffCannotShop,
    UnknownCard,
    UnknownProduct,
)
from store.persist import repo
from store.persist.tables import Ledger, LineItem, Sale


@dataclass(frozen=True)
class CheckoutItem:
    barcode: str
    qty: int


@dataclass(frozen=True)
class CheckoutResult:
    sale_id: int
    total_cents: int
    balance_cents: int


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _require_shopper(session: Session, uid: str):
    card = repo.get_card_by_uid(session, uid.upper().replace(":", "").replace(" ", ""))
    if card is None:
        raise UnknownCard(uid)
    if not card.active:
        raise InactiveCard(uid)
    if card.role != "child":
        raise StaffCannotShop(uid)
    account = repo.get_account(session, card.id)
    if account is None:
        raise UnknownCard(uid)
    return card, account


def checkout(session: Session, uid: str, items: list[CheckoutItem]) -> CheckoutResult:
    if not items:
        raise UnknownProduct("empty")
    card, account = _require_shopper(session, uid)

    merged: dict[str, int] = {}
    for item in items:
        if item.qty < 1:
            raise UnknownProduct(item.barcode)
        code = bc.normalize(item.barcode)
        merged[code] = merged.get(code, 0) + item.qty

    lines: list[tuple] = []
    total = 0
    for code, qty in merged.items():
        product = repo.get_product_by_barcode(session, code)
        if product is None:
            raise UnknownProduct(code)
        if (
            product.status != "ready"
            or not product.active
            or product.price_cents is None
            or not (product.name or "").strip()
        ):
            raise ProductNotSellable(code)
        if product.stock is not None and product.stock < qty:
            raise InsufficientStock(code)
        lines.append((product, qty, product.price_cents))
        total += product.price_cents * qty

    if account.balance_cents < total:
        raise InsufficientFunds(total - account.balance_cents)

    now = _now()
    sale = Sale(card_id=card.id, total_cents=total, created_at=now)
    session.add(sale)
    session.flush()
    for product, qty, unit in lines:
        session.add(
            LineItem(
                sale_id=sale.id,
                product_id=product.id,
                qty=qty,
                unit_price_cents=unit,
            )
        )
        if product.stock is not None:
            product.stock -= qty
    account.balance_cents -= total
    session.add(
        Ledger(
            card_id=card.id,
            kind="checkout",
            amount_cents=-total,
            sale_id=sale.id,
            created_at=now,
            note=None,
        )
    )
    session.flush()
    return CheckoutResult(sale.id, total, account.balance_cents)
