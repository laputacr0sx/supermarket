from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from store.persist.tables import Account, Card, Product, Sale


def get_product_by_barcode(session: Session, barcode: str) -> Product | None:
    return session.scalar(select(Product).where(Product.barcode == barcode))


def get_card_by_uid(session: Session, uid: str) -> Card | None:
    return session.scalar(select(Card).where(Card.uid == uid))


def get_account(session: Session, card_id: int) -> Account | None:
    return session.get(Account, card_id)


def last_open_sale(session: Session, card_id: int | None = None) -> Sale | None:
    stmt = select(Sale).where(Sale.voided_at.is_(None)).order_by(Sale.id.desc())
    if card_id is not None:
        stmt = stmt.where(Sale.card_id == card_id)
    return session.scalars(stmt).first()


def all_barcodes(session: Session) -> set[str]:
    return set(session.scalars(select(Product.barcode)).all())


def list_drafts(session: Session) -> list[Product]:
    stmt = select(Product).where(Product.status == "draft").order_by(Product.id)
    return list(session.scalars(stmt))


def list_ready(session: Session) -> list[Product]:
    stmt = (
        select(Product)
        .where(Product.status == "ready")
        .order_by(Product.name, Product.id)
    )
    return list(session.scalars(stmt))


def list_cards(session: Session) -> list[Card]:
    stmt = select(Card).options(selectinload(Card.account)).order_by(Card.id)
    return list(session.scalars(stmt))


def list_sales_on(session: Session, day: str) -> list[Sale]:
    stmt = (
        select(Sale)
        .options(selectinload(Sale.card))
        .where(Sale.created_at.startswith(day))
        .order_by(Sale.id.desc())
    )
    return list(session.scalars(stmt))
