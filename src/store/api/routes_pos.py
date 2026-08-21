from __future__ import annotations

import time
from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from sqlalchemy.orm import Session

from store.api.deps import get_session
from store.api.schemas import (
    CardOut,
    CheckoutIn,
    CheckoutOut,
    LedgerIn,
    LedgerOut,
    ProductOut,
    ScanIn,
    ScanOut,
    VoidIn,
    VoidOut,
)
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


def _raise(exc: Exception) -> NoReturn:
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
def pos_scan(
    body: ScanIn, request: Request, session: SessionDep, response: Response
) -> ScanOut:
    learn = bool(request.app.state.settings.learn_on_unknown)
    result = catalog.scan(session, body.barcode, learn=learn)
    if result.action == "reject":
        raise HTTPException(status_code=422, detail={"action": "reject"})
    payload = ScanOut(
        action=result.action,
        product=ProductOut.model_validate(result.product) if result.product else None,
    )
    if result.action == "learned":
        response.status_code = 201
    return payload


@router.get("/products/{barcode}")
def pos_product(barcode: str, session: SessionDep) -> ProductOut:
    try:
        product = catalog.lookup(session, barcode)
    except UnknownProduct as exc:
        _raise(exc)
    return ProductOut.model_validate(product)


@router.get("/cards/{uid}")
def pos_card(uid: str, session: SessionDep) -> CardOut:
    card = repo.get_card_by_uid(session, uid.upper().replace(":", "").replace(" ", ""))
    if card is None:
        raise HTTPException(status_code=404, detail="unknown card")
    account = repo.get_account(session, card.id)
    return CardOut(
        name=card.child_name,
        role=card.role,
        balance_cents=account.balance_cents if account else 0,
        active=bool(card.active),
    )


@router.post("/checkout")
def pos_checkout(
    body: CheckoutIn,
    request: Request,
    session: SessionDep,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> CheckoutOut:
    cache: dict[tuple[str, str], tuple[float, CheckoutOut]] = request.app.state.idempotency
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
    payload = CheckoutOut(
        sale_id=result.sale_id,
        total_cents=result.total_cents,
        balance_cents=result.balance_cents,
    )
    cache[("uid", uid)] = (now, payload)
    if idempotency_key:
        cache[("id", idempotency_key)] = (now, payload)
    return payload


@router.post("/ledger")
def pos_ledger(body: LedgerIn, session: SessionDep) -> LedgerOut:
    try:
        result = ledger.apply_ledger(session, body.uid, body.kind, body.amount_cents)
    except StoreError as exc:
        _raise(exc)
    return LedgerOut(
        kind=result.kind,
        amount_cents=result.amount_cents,
        balance_cents=result.balance_cents,
    )


@router.post("/void-last")
def pos_void(body: VoidIn, session: SessionDep) -> VoidOut:
    try:
        result = ledger.void_last(session, body.uid)
    except StoreError as exc:
        _raise(exc)
    return VoidOut(
        kind=result.kind,
        amount_cents=result.amount_cents,
        balance_cents=result.balance_cents,
        sale_id=result.sale_id,
    )
