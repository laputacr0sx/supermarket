"""httpx2 client for the till. Maps HTTP to FSM replies."""

from __future__ import annotations

from typing import Literal, TypeVar

import httpx2
from pydantic import BaseModel, ValidationError

from store.api.schemas import (
    CardOut,
    CheckoutIn,
    CheckoutItemIn,
    CheckoutOut,
    LedgerIn,
    LedgerOut,
    ScanIn,
    ScanOut,
    VoidIn,
    VoidOut,
)
from store.kiosk.fsm import Line, PayReply, ScanReply

TModel = TypeVar("TModel", bound=BaseModel)


def _parse(model: type[TModel], raw: object) -> TModel | None:
    try:
        return model.model_validate(raw)
    except ValidationError:
        return None


class Api:
    def __init__(self, base_url: str) -> None:
        self._client = httpx2.Client(base_url=base_url, timeout=5.0)

    def close(self) -> None:
        self._client.close()

    def scan(self, code: str) -> ScanReply:
        response = self._client.post("/pos/scan", json=ScanIn(barcode=code).model_dump())
        if response.status_code == 422:
            return ScanReply("reject", None)
        if response.status_code not in {200, 201}:
            return ScanReply("reject", None)
        parsed = _parse(ScanOut, response.json())
        if parsed is None:
            return ScanReply("reject", None)
        product = dict(parsed.product.model_dump()) if parsed.product else None
        return ScanReply(parsed.action, product)

    def pay(self, uid: str, items: tuple[Line, ...]) -> PayReply:
        body = CheckoutIn(
            uid=uid,
            items=[CheckoutItemIn(barcode=line.barcode, qty=line.qty) for line in items],
        )
        response = self._client.post("/pos/checkout", json=body.model_dump())
        if response.status_code == 200:
            parsed = _parse(CheckoutOut, response.json())
            if parsed is None:
                return PayReply("unknown")
            return PayReply(
                "paid",
                total_cents=parsed.total_cents,
                balance_cents=parsed.balance_cents,
            )
        if response.status_code == 402:
            raw = response.json()
            detail = raw.get("detail") if isinstance(raw, dict) else None
            need = detail.get("need_cents") if isinstance(detail, dict) else None
            return PayReply("need", need_cents=need if isinstance(need, int) else None)
        return PayReply("unknown")

    def card(self, uid: str) -> PayReply:
        response = self._client.get(f"/pos/cards/{uid}")
        if response.status_code != 200:
            return PayReply("unknown")
        parsed = _parse(CardOut, response.json())
        if parsed is None:
            return PayReply("unknown")
        return PayReply("balance", balance_cents=parsed.balance_cents, name=parsed.name)

    def ledger(self, uid: str, kind: str, amount_cents: int | None) -> PayReply:
        if kind == "topup":
            ledger_kind: Literal["topup", "reset"] = "topup"
        elif kind == "reset":
            ledger_kind = "reset"
        else:
            return PayReply("unknown")
        try:
            body = LedgerIn(uid=uid, kind=ledger_kind, amount_cents=amount_cents)
        except ValidationError:
            return PayReply("unknown")
        response = self._client.post("/pos/ledger", json=body.model_dump())
        if response.status_code != 200:
            return PayReply("unknown")
        parsed = _parse(LedgerOut, response.json())
        if parsed is None:
            return PayReply("unknown")
        return PayReply("balance", balance_cents=parsed.balance_cents)

    def void_last(self) -> PayReply:
        response = self._client.post("/pos/void-last", json=VoidIn().model_dump())
        if response.status_code != 200:
            return PayReply("unknown")
        parsed = _parse(VoidOut, response.json())
        if parsed is None:
            return PayReply("unknown")
        return PayReply("balance", balance_cents=parsed.balance_cents)
