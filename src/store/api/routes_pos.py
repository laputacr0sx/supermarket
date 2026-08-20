from __future__ import annotations

import time
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from store.api.deps import get_session
from store.domain.errors import (
    DuplicateCheckout,
    InactiveCard,
    InsufficientFunds,
    InsufficientStock,
    InvalidLedger,
    NothingToVoid,
    ProductNotSellable,
    StaffCannotShop,
    StoreError,
    UnknownCard,
    UnknownProduct,
)
from store.persist import repo
from store.services import catalog, checkout, ledger

router = APIRouter(prefix="/pos", tags=["pos"])
SessionDep = Annotated[Session, Depends(get_session)]


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


def _raise(exc: Exception) -> None:
    if isinstance(exc, InsufficientFunds):
        raise HTTPException(status_code=402, detail={"need_cents": exc.need_cents}) from exc
    if isinstance(exc, (UnknownCard, UnknownProduct, ProductNotSellable, NothingToVoid)):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if isinstance(exc, (InactiveCard, StaffCannotShop, InsufficientStock, DuplicateCheckout)):
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if isinstance(exc, InvalidLedger):
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    raise exc


@router.post("/scan")
def pos_scan(body: ScanIn, request: Request, session: SessionDep) -> dict:
    learn = bool(getattr(request.app.state.settings, "learn_on_unknown", True))
    result = catalog.scan(session, body.barcode, learn=learn)
    if result.action == "reject":
        raise HTTPException(status_code=422, detail={"action": "reject"})
    payload = {
        "action": result.action,
        "product": catalog.product_to_dict(result.product) if result.product else None,
    }
    return JSONResponse(payload, status_code=201 if result.action == "learned" else 200)


@router.get("/products/{barcode}")
def pos_product(barcode: str, session: SessionDep) -> dict:
    try:
        product = catalog.lookup(session, barcode)
    except UnknownProduct as exc:
        _raise(exc)
    return catalog.product_to_dict(product)


@router.get("/cards/{uid}")
def pos_card(uid: str, session: SessionDep) -> dict:
    card = repo.get_card_by_uid(session, uid.upper().replace(":", "").replace(" ", ""))
    if card is None:
        raise HTTPException(status_code=404, detail="unknown card")
    account = repo.get_account(session, card.id)
    return {
        "name": card.child_name,
        "role": card.role,
        "balance_cents": account.balance_cents if account else 0,
        "active": bool(card.active),
    }


@router.post("/checkout")
def pos_checkout(
    body: CheckoutIn,
    request: Request,
    session: SessionDep,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> dict:
    cache: dict = request.app.state.idempotency
    now = time.monotonic()
    if idempotency_key:
        hit = cache.get(("id", idempotency_key))
        if hit and now - hit[0] < 30:
            return hit[1]
    uid = body.uid.upper().replace(":", "").replace(" ", "")
    debounce = float(request.app.state.settings.uid_debounce_s)
    last = cache.get(("uid", uid))
    if last and now - last[0] < debounce:
        raise HTTPException(status_code=409, detail="duplicate checkout")
    try:
        result = checkout.checkout(
            session,
            uid,
            [checkout.CheckoutItem(i.barcode, i.qty) for i in body.items],
        )
    except StoreError as exc:
        _raise(exc)
    payload = {
        "sale_id": result.sale_id,
        "total_cents": result.total_cents,
        "balance_cents": result.balance_cents,
    }
    cache[("uid", uid)] = (now, payload)
    if idempotency_key:
        cache[("id", idempotency_key)] = (now, payload)
    return payload


@router.post("/ledger")
def pos_ledger(body: LedgerIn, session: SessionDep) -> dict:
    try:
        result = ledger.apply_ledger(session, body.uid, body.kind, body.amount_cents)
    except StoreError as exc:
        _raise(exc)
    return {
        "kind": result.kind,
        "amount_cents": result.amount_cents,
        "balance_cents": result.balance_cents,
    }


@router.post("/void-last")
def pos_void(body: VoidIn, session: SessionDep) -> dict:
    try:
        result = ledger.void_last(session, body.uid)
    except StoreError as exc:
        _raise(exc)
    return {
        "kind": result.kind,
        "amount_cents": result.amount_cents,
        "balance_cents": result.balance_cents,
        "sale_id": result.sale_id,
    }
