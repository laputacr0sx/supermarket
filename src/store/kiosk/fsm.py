"""POS state machine. Pure: no pygame, no HTTP."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TypedDict

from store.domain.money import cents_to_yuan

RESULT_S = 3.0
FLASH_S = 2.0
STAFF_S = 30.0
TOPUP = {"F5": 500, "F6": 1000, "F7": 2000}


class Overlay(TypedDict, total=False):
    code4: str
    name: str
    total: int | None
    balance: int | None
    need: int | None


class Queue(TypedDict, total=False):
    kind: str
    amount_cents: int | None
    confirm: bool


@dataclass(frozen=True)
class Line:
    barcode: str
    name: str
    price_cents: int
    qty: int


@dataclass(frozen=True)
class ViewModel:
    header: str
    pill: str
    flash: str | None
    picture: str
    tag_yuan: int | None
    title: str
    sub: str
    count: str
    sum_label: str
    sum_yuan: int | None
    sum_style: str


@dataclass(frozen=True)
class KioskState:
    mode: str
    cart: tuple[Line, ...]
    result: str | None
    until: float | None
    last: Line | None
    overlay: Overlay
    queue: Queue


@dataclass(frozen=True)
class Effect:
    kind: str
    code: str | None = None
    uid: str | None = None
    items: tuple[Line, ...] = ()
    ledger_kind: str | None = None
    amount_cents: int | None = None


@dataclass(frozen=True)
class Barcode:
    code: str


@dataclass(frozen=True)
class Uid:
    uid: str


@dataclass(frozen=True)
class Tick:
    pass


@dataclass(frozen=True)
class Key:
    name: str


@dataclass(frozen=True)
class StaffUnlock:
    pass


@dataclass(frozen=True)
class ScanReply:
    action: str
    product: dict[str, object] | None


@dataclass(frozen=True)
class PayReply:
    kind: str
    total_cents: int | None = None
    balance_cents: int | None = None
    need_cents: int | None = None
    name: str = ""


type Event = Barcode | Uid | Tick | Key | StaffUnlock | ScanReply | PayReply


def idle() -> KioskState:
    return KioskState("idle", (), None, None, None, {}, {})


def _total(cart: tuple[Line, ...]) -> int:
    return sum(line.price_cents * line.qty for line in cart)


def _count(cart: tuple[Line, ...]) -> int:
    return sum(line.qty for line in cart)


def _add(cart: tuple[Line, ...], line: Line) -> tuple[Line, ...]:
    out: list[Line] = []
    found = False
    for existing in cart:
        if existing.barcode == line.barcode:
            out.append(replace(existing, qty=existing.qty + line.qty))
            found = True
        else:
            out.append(existing)
    if not found:
        out.append(line)
    return tuple(out)


def step(state: KioskState, event: Event, *, now: float) -> tuple[KioskState, Effect]:
    if isinstance(event, Tick) and state.until is not None and now >= state.until:
        mode = "cart" if state.cart else "idle"
        nxt = replace(state, mode=mode, result=None, until=None, overlay={}, queue={})
        return nxt, Effect("none")
    if isinstance(event, StaffUnlock):
        nxt = replace(
            state, mode="staff", result=None, until=now + STAFF_S, overlay={}, queue={}
        )
        return nxt, Effect("none")
    if isinstance(event, Key):
        return _on_key(state, event, now)
    if isinstance(event, Barcode):
        return state, Effect("scan", code=event.code)
    if isinstance(event, Uid):
        if state.mode == "staff_queued" and state.queue:
            return state, Effect(
                "ledger",
                uid=event.uid,
                ledger_kind=str(state.queue.get("kind") or "topup"),
                amount_cents=state.queue.get("amount_cents"),
            )
        if state.mode in {"staff", "staff_queued"}:
            return state, Effect("none")
        if state.cart:
            return state, Effect("checkout", uid=event.uid, items=state.cart)
        return state, Effect("card", uid=event.uid)
    if isinstance(event, ScanReply):
        return _on_scan(state, event, now)
    if isinstance(event, PayReply):
        return _on_pay(state, event, now)
    return state, Effect("none")


def _on_key(state: KioskState, event: Key, now: float) -> tuple[KioskState, Effect]:
    if state.mode not in {"staff", "staff_queued"}:
        return state, Effect("none")
    name = event.name
    if name == "Escape":
        if state.mode == "staff_queued":
            nxt = replace(state, mode="staff", queue={}, until=now + STAFF_S)
            return nxt, Effect("none")
        mode = "cart" if state.cart else "idle"
        nxt = replace(state, mode=mode, queue={}, until=None)
        return nxt, Effect("none")
    if name in TOPUP:
        queue: Queue = {"kind": "topup", "amount_cents": TOPUP[name]}
        nxt = replace(state, mode="staff_queued", queue=queue, until=now + STAFF_S)
        return nxt, Effect("none")
    if name == "F8":
        if state.queue.get("kind") == "reset" and state.queue.get("confirm"):
            return state, Effect("none")
        if state.queue.get("kind") == "reset":
            queue = Queue(kind="reset", amount_cents=None, confirm=True)
        else:
            queue = Queue(kind="reset", amount_cents=None, confirm=False)
        nxt = replace(state, mode="staff_queued", queue=queue, until=now + STAFF_S)
        return nxt, Effect("none")
    if name == "F10":
        return state, Effect("void")
    return state, Effect("none")


def _price_cents(product: dict[str, object]) -> int:
    raw = product.get("price_cents") or 0
    return raw if isinstance(raw, int) else 0


def _on_scan(state: KioskState, event: ScanReply, now: float) -> tuple[KioskState, Effect]:
    product = event.product or {}
    if event.action == "sell":
        line = Line(
            str(product.get("barcode") or ""),
            str(product.get("name") or ""),
            _price_cents(product),
            1,
        )
        cart = _add(state.cart, line)
        nxt = replace(state, mode="cart", cart=cart, last=line, result=None, until=None)
        return nxt, Effect("none")
    if event.action == "learned":
        overlay: Overlay = {"code4": str(product.get("barcode") or "")[-4:]}
        nxt = replace(state, mode="result", result="learned", until=now + FLASH_S, overlay=overlay)
        return nxt, Effect("none")
    if event.action == "pending":
        overlay = Overlay(code4=str(product.get("barcode") or "")[-4:])
        nxt = replace(state, mode="result", result="pending", until=now + FLASH_S, overlay=overlay)
        return nxt, Effect("none")
    nxt = replace(state, mode="result", result="unknown", until=now + FLASH_S, overlay={})
    return nxt, Effect("none")


def _on_pay(state: KioskState, event: PayReply, now: float) -> tuple[KioskState, Effect]:
    if event.kind == "paid":
        overlay: Overlay = {
            "name": event.name,
            "total": event.total_cents,
            "balance": event.balance_cents,
        }
        return replace(
            state,
            mode="result",
            result="paid",
            cart=(),
            last=None,
            until=now + RESULT_S,
            overlay=overlay,
            queue={},
        ), Effect("none")
    if event.kind == "need":
        overlay = Overlay(name=event.name, need=event.need_cents)
        nxt = replace(state, mode="result", result="need", until=now + RESULT_S, overlay=overlay)
        return nxt, Effect("none")
    if event.kind == "balance":
        overlay = Overlay(name=event.name, balance=event.balance_cents)
        nxt = replace(state, mode="result", result="balance", until=now + RESULT_S, overlay=overlay)
        return nxt, Effect("none")
    overlay = Overlay(name=event.name)
    nxt = replace(state, mode="result", result="unknown", until=now + FLASH_S, overlay=overlay)
    return nxt, Effect("none")


def view(state: KioskState) -> ViewModel:
    n = _count(state.cart)
    total = _total(state.cart)
    count = f"{n}件" if n else ""
    if state.result == "paid":
        return ViewModel(
            "士多", "掃 · 拍", "ok", "card",
            cents_to_yuan(state.overlay.get("total") or 0),
            "得",
            f"{state.overlay.get('name') or ''} 剩",
            "",
            "剩",
            cents_to_yuan(state.overlay.get("balance") or 0),
            "gold",
        )
    if state.result == "need":
        return ViewModel(
            "士多", "掃 · 拍", "nope", "card", None, "唔夠",
            str(state.overlay.get("name") or ""),
            count, "差",
            cents_to_yuan(state.overlay.get("need") or 0),
            "need",
        )
    if state.result == "learned":
        return ViewModel(
            "士多", "掃 · 拍", "soft", "barcode", None, "記低",
            f"叫大人 ·{state.overlay.get('code4') or ''}",
            count or "未賣",
            "共" if n else "",
            cents_to_yuan(total) if n else None,
            "hot" if n else "dim",
        )
    if state.result == "pending":
        return ViewModel(
            "士多", "掃 · 拍", "soft", "barcode", None, "問大人",
            f"·{state.overlay.get('code4') or ''}",
            count, "共" if n else "",
            cents_to_yuan(total) if n else None,
            "hot" if n else "dim",
        )
    if state.result == "balance":
        yuan = cents_to_yuan(state.overlay.get("balance") or 0)
        return ViewModel(
            "士多", "掃 · 拍", "ok", "card", yuan,
            str(state.overlay.get("name") or ""), "餘",
            "", "餘", yuan, "gold",
        )
    if state.result == "unknown":
        return ViewModel(
            "士多", "掃 · 拍", "nope", "barcode", None, "唔識", "",
            count, "共" if n else "",
            cents_to_yuan(total) if n else None,
            "hot" if n else "",
        )
    if state.last and state.cart:
        qty = next((ln.qty for ln in state.cart if ln.barcode == state.last.barcode), 1)
        return ViewModel(
            "士多", "掃 · 拍", None, "idle",
            cents_to_yuan(state.last.price_cents),
            state.last.name,
            f"×{qty}" if qty > 1 else "",
            count, "共", cents_to_yuan(total), "hot",
        )
    vm = ViewModel("士多", "掃 · 拍", None, "idle", None, "掃嘢", "拍卡", "", "共", 0, "dim")
    if state.mode in {"staff", "staff_queued"}:
        return replace(vm, header="STAFF", pill="F5–F10")
    return vm
