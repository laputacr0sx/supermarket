from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint(
            "status != 'ready' OR (name IS NOT NULL AND length(trim(name)) > 0 "
            "AND price_cents IS NOT NULL)",
            name="ck_products_ready_complete",
        ),
        CheckConstraint("origin IN ('household','store')", name="ck_products_origin"),
        CheckConstraint("status IN ('draft','ready')", name="ck_products_status"),
        CheckConstraint("price_cents IS NULL OR price_cents >= 0", name="ck_products_price"),
        Index("ix_products_active", "active"),
        Index("ix_products_status", "status"),
        Index("ix_products_origin", "origin"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    barcode: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    origin: Mapped[str] = mapped_column(String(16), nullable=False, default="household")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    price_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stock: Mapped[int | None] = mapped_column(Integer, nullable=True)
    image_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)

    line_items: Mapped[list[LineItem]] = relationship(back_populates="product")


class Card(Base):
    __tablename__ = "cards"
    __table_args__ = (CheckConstraint("role IN ('child','staff')", name="ck_cards_role"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    uid: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    child_name: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="child")
    active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    account: Mapped[Account | None] = relationship(back_populates="card")
    sales: Mapped[list[Sale]] = relationship(back_populates="card")
    ledger: Mapped[list[Ledger]] = relationship(back_populates="card")


class Account(Base):
    __tablename__ = "accounts"

    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id"), primary_key=True)
    balance_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    card: Mapped[Card] = relationship(back_populates="account")


class Sale(Base):
    __tablename__ = "sales"
    __table_args__ = (Index("ix_sales_created_at", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id"), nullable=False)
    total_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    voided_at: Mapped[str | None] = mapped_column(Text, nullable=True)

    card: Mapped[Card] = relationship(back_populates="sales")
    lines: Mapped[list[LineItem]] = relationship(back_populates="sale")


class LineItem(Base):
    __tablename__ = "line_items"
    __table_args__ = (CheckConstraint("qty > 0", name="ck_line_qty"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("sales.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)

    sale: Mapped[Sale] = relationship(back_populates="lines")
    product: Mapped[Product] = relationship(back_populates="line_items")


class Ledger(Base):
    __tablename__ = "ledger"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('topup','reset','void_refund','checkout')",
            name="ck_ledger_kind",
        ),
        Index("ix_ledger_card_created", "card_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    sale_id: Mapped[int | None] = mapped_column(ForeignKey("sales.id"), nullable=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    card: Mapped[Card] = relationship(back_populates="ledger")
