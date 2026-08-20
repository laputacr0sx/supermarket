"""Seed play-day rows. Safe to re-run (skips existing barcodes / UIDs)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select

from store.config import get_settings
from store.domain.barcode import ean13_check
from store.domain.money import yuan_to_cents
from store.persist.engine import create_schema, make_engine, make_session_factory, session_scope
from store.persist.tables import Account, Card, Product


def _ean13(body12: str) -> str:
    return body12 + ean13_check(body12)


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def seed_session(session) -> None:
    now = _now()
    products = [
        ("麥片", _ean13("489000000001"), 12, "household"),
        ("牛奶", _ean13("489000000002"), 8, "household"),
        ("番茄", _ean13("200184739201"), 3, "store"),
    ]
    for name, code, yuan, origin in products:
        existing = session.scalar(select(Product).where(Product.barcode == code))
        if existing:
            continue
        session.add(
            Product(
                barcode=code,
                origin=origin,
                status="ready",
                name=name,
                price_cents=yuan_to_cents(yuan),
                stock=None,
                active=1,
                created_at=now,
            )
        )

    cards = [
        ("DEADBEEF", "樂樂", "child", 30),
        ("CAFEBABE", "森", "child", 5),
        ("0FF1CE", "職員", "staff", 0),
    ]
    for uid, name, role, yuan in cards:
        if session.scalar(select(Card).where(Card.uid == uid)):
            continue
        card = Card(uid=uid, child_name=name, role=role, active=1)
        session.add(card)
        session.flush()
        session.add(Account(card_id=card.id, balance_cents=yuan_to_cents(yuan)))


def run() -> None:
    settings = get_settings()
    engine = make_engine(settings.database)
    create_schema(engine)
    factory = make_session_factory(engine)
    with session_scope(factory) as session:
        seed_session(session)
    print(f"seeded {settings.database}")


if __name__ == "__main__":
    run()
