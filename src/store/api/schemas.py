"""Pydantic models for POS HTTP JSON."""

from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ScanIn(BaseModel):
    barcode: str = Field(min_length=1)


class CheckoutItemIn(BaseModel):
    barcode: str = Field(min_length=1)
    qty: int = Field(ge=1)


class CheckoutIn(BaseModel):
    uid: str = Field(min_length=1)
    items: list[CheckoutItemIn] = Field(min_length=1)


class LedgerIn(BaseModel):
    uid: str = Field(min_length=1)
    kind: Literal["topup", "reset"]
    amount_cents: int | None = None

    @model_validator(mode="after")
    def topup_needs_positive_amount(self) -> Self:
        if self.kind == "topup" and (self.amount_cents is None or self.amount_cents <= 0):
            raise ValueError("topup requires amount_cents > 0")
        return self


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
    action: Literal["sell", "inactive", "pending", "learned"]
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
