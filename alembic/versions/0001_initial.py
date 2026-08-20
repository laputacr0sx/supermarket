"""initial play-store schema

Revision ID: 0001
Revises:
Create Date: 2026-08-18
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE products (
          id            INTEGER PRIMARY KEY,
          barcode       TEXT NOT NULL UNIQUE,
          origin        TEXT NOT NULL DEFAULT 'household'
                        CHECK (origin IN ('household','store')),
          status        TEXT NOT NULL DEFAULT 'draft'
                        CHECK (status IN ('draft','ready')),
          name          TEXT,
          price_cents   INTEGER CHECK (price_cents IS NULL OR price_cents >= 0),
          stock         INTEGER,
          image_path    TEXT,
          active        INTEGER NOT NULL DEFAULT 1,
          created_at    TEXT NOT NULL,
          CHECK (
            status != 'ready'
            OR (name IS NOT NULL AND length(trim(name)) > 0 AND price_cents IS NOT NULL)
          )
        )
        """
    )
    op.execute(
        """
        CREATE TABLE cards (
          id            INTEGER PRIMARY KEY,
          uid           TEXT NOT NULL UNIQUE,
          child_name    TEXT NOT NULL,
          role          TEXT NOT NULL DEFAULT 'child'
                        CHECK (role IN ('child','staff')),
          active        INTEGER NOT NULL DEFAULT 1
        )
        """
    )
    op.execute(
        """
        CREATE TABLE accounts (
          card_id       INTEGER PRIMARY KEY REFERENCES cards(id),
          balance_cents INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    op.execute(
        """
        CREATE TABLE sales (
          id            INTEGER PRIMARY KEY,
          card_id       INTEGER NOT NULL REFERENCES cards(id),
          total_cents   INTEGER NOT NULL,
          created_at    TEXT NOT NULL,
          voided_at     TEXT
        )
        """
    )
    op.execute(
        """
        CREATE TABLE line_items (
          id            INTEGER PRIMARY KEY,
          sale_id       INTEGER NOT NULL REFERENCES sales(id),
          product_id    INTEGER NOT NULL REFERENCES products(id),
          qty           INTEGER NOT NULL CHECK (qty > 0),
          unit_price_cents INTEGER NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE TABLE ledger (
          id            INTEGER PRIMARY KEY,
          card_id       INTEGER NOT NULL REFERENCES cards(id),
          kind          TEXT NOT NULL CHECK (kind IN ('topup','reset','void_refund','checkout')),
          amount_cents  INTEGER NOT NULL,
          sale_id       INTEGER REFERENCES sales(id),
          created_at    TEXT NOT NULL,
          note          TEXT
        )
        """
    )
    op.execute("CREATE INDEX ix_sales_created_at ON sales (created_at)")
    op.execute("CREATE INDEX ix_ledger_card_created ON ledger (card_id, created_at)")
    op.execute("CREATE INDEX ix_products_active ON products (active)")
    op.execute("CREATE INDEX ix_products_status ON products (status)")
    op.execute("CREATE INDEX ix_products_origin ON products (origin)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ledger")
    op.execute("DROP TABLE IF EXISTS line_items")
    op.execute("DROP TABLE IF EXISTS sales")
    op.execute("DROP TABLE IF EXISTS accounts")
    op.execute("DROP TABLE IF EXISTS cards")
    op.execute("DROP TABLE IF EXISTS products")
