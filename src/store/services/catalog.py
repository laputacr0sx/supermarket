from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy.orm import Session

from store.domain import barcode as bc
from store.domain.errors import InvalidBarcode, ProductNotSellable, UnknownProduct
from store.persist import repo
from store.persist.tables import Product


type ScanAction = Literal["sell", "inactive", "pending", "learned", "reject"]


@dataclass(frozen=True)
class ScanResult:
    action: ScanAction
    product: Product | None


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def lookup(session: Session, raw: str) -> Product:
    code = bc.normalize(raw)
    product = repo.get_product_by_barcode(session, code)
    if product is None:
        raise UnknownProduct(code)
    return product


def scan(session: Session, raw: str, *, learn: bool = True) -> ScanResult:
    code = bc.normalize(raw)
    product = repo.get_product_by_barcode(session, code)
    if product is not None:
        if product.status == "draft":
            return ScanResult("pending", product)
        if not product.active:
            return ScanResult("inactive", product)
        return ScanResult("sell", product)

    if not bc.is_valid(code):
        return ScanResult("reject", None)
    if not learn:
        return ScanResult("reject", None)

    product = Product(
        barcode=code,
        origin="household",
        status="draft",
        name=None,
        price_cents=None,
        stock=None,
        image_path=None,
        active=1,
        created_at=_now(),
    )
    session.add(product)
    session.flush()
    return ScanResult("learned", product)


def finish(
    session: Session,
    barcode: str,
    *,
    name: str,
    price_cents: int,
    image_path: str | None = None,
) -> Product:
    product = lookup(session, barcode)
    if not name.strip():
        raise ProductNotSellable("name required")
    if price_cents < 0:
        raise ProductNotSellable("price")
    product.name = name.strip()
    product.price_cents = price_cents
    if image_path is not None:
        product.image_path = image_path
    product.status = "ready"
    session.flush()
    return product


def list_drafts(session: Session) -> list[Product]:
    return repo.list_drafts(session)


def list_ready(session: Session) -> list[Product]:
    return repo.list_ready(session)


def drop_draft(session: Session, barcode: str) -> None:
    product = lookup(session, barcode)
    if product.status != "draft":
        raise ProductNotSellable(product.barcode)
    session.delete(product)
    session.flush()


def deactivate(session: Session, barcode: str) -> Product:
    product = lookup(session, barcode)
    product.active = 0
    session.flush()
    return product


def mint_store_drafts(
    session: Session,
    count: int,
    *,
    prefix_min: int = 200,
    prefix_max: int = 299,
) -> list[Product]:
    if count < 1:
        raise InvalidBarcode("count")
    existing = repo.all_barcodes(session)
    created: list[Product] = []
    now = _now()
    for _ in range(count):
        code = bc.mint_store_ean13(existing, prefix_min, prefix_max)
        existing.add(code)
        row = Product(
            barcode=code,
            origin="store",
            status="draft",
            name=None,
            price_cents=None,
            created_at=now,
        )
        session.add(row)
        created.append(row)
    session.flush()
    return created
