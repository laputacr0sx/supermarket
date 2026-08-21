"""Pydantic models for POS HTTP JSON."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ScanIn(BaseModel):
    barcode: str


class CheckoutItemIn(BaseModel):
    barcode: str
    qty: int = Field(ge=1)


class CheckoutIn(BaseModel):
    uid: str
    items: list[CheckoutItemIn]


class LedgerIn(BaseModel):
    uid: str
    kind: str
    amount_cents: int | None = None


class VoidIn(BaseModel):
    uid: str | None = None


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    barcode: str
    origin: str
    status: str
    name: str | None
    price_cents: int | None
    stock: int | None
    image_path: str | None
    active: bool


class ScanOut(BaseModel):
    action: str
    product: ProductOut | None = None


class CardOut(BaseModel):
    name: str
    role: str
    balance_cents: int
    active: bool


class CheckoutOut(BaseModel):
    sale_id: int
    total_cents: int
    balance_cents: int


class LedgerOut(BaseModel):
    kind: str
    amount_cents: int
    balance_cents: int


class VoidOut(LedgerOut):
    sale_id: int | None
