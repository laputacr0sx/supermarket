"""Toolkit-free 士多 till: catalog, cart, tap, ViewModel.

No pygame / DOM. The HTML demo and the pygame-ce kiosk both
project this ViewModel. Production `src/store/ui` paints the same object.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Literal

Flash = Literal["ok", "nope", "soft"] | None
Picture = Literal["idle", "card", "barcode"] | str
MoneyStyle = Literal["hot", "gold", "need", "dim", ""]


@dataclass(frozen=True)
class Sku:
    id: str
    name: str | None
    price: int | None  # integer 港元
    status: Literal["ready", "draft", "unknown", "invalid"]
    origin: Literal["household", "store"]
    image: str | None
    code: str
    valid: bool = True


@dataclass
class Line:
    sku_id: str
    name: str
    price: int
    qty: int
    image: str | None


@dataclass
class Card:
    name: str
    balance: int


@dataclass(frozen=True)
class ViewModel:
    header: str
    pill: str
    flash: Flash
    picture: Picture
    tag_yuan: int | None
    title: str
    sub: str
    count: str
    sum_label: str
    sum_yuan: int | None
    sum_style: MoneyStyle


@dataclass
class Result:
    kind: Literal["paid", "need", "learned", "pending", "unknown", "balance"]
    until_ms: int
    name: str = ""
    total: int = 0
    balance: int = 0
    need: int = 0
    code4: str = ""


def seed_catalog() -> dict[str, Sku]:
    return {
        "cereal": Sku("cereal", "麥片", 12, "ready", "household", "cereal", "5412345123451"),
        "milk": Sku("milk", "牛奶", 8, "ready", "household", "milk", "4006381333931"),
        "tomato": Sku("tomato", "番茄", 3, "ready", "store", "tomato", "2847193058264"),
        "toothpaste": Sku(
            "toothpaste", None, None, "unknown", "household", None, "5901234123457", True
        ),
        "apple": Sku("apple", None, None, "draft", "store", None, "2718403957618", True),
        "junk": Sku("junk", None, None, "invalid", "household", None, "http://box", False),
    }


class Shop:
    """In-memory till. Same rules as the HTML 士多 demo."""

    RESULT_MS = 6000
    UNKNOWN_MS = 4000

    def __init__(self) -> None:
        self.catalog = seed_catalog()
        self.cards = {
            "alex": Card("樂樂", 30),
            "sam": Card("森", 5),
        }
        self.cart: list[Line] = []
        self.last_id: str | None = None
        self.result: Result | None = None
        self.drafts: list[dict] = [
            {"id": "apple", "code": "2718403957618", "origin": "store", "name": "", "price": ""}
        ]

    def cart_total(self) -> int:
        return sum(line.price * line.qty for line in self.cart)

    def cart_count(self) -> int:
        return sum(line.qty for line in self.cart)

    def tick(self, now_ms: int) -> bool:
        if self.result and now_ms >= self.result.until_ms:
            self.result = None
            return True
        return False

    def scan(self, sku_id: str, now_ms: int = 0) -> str:
        sku = self.catalog.get(sku_id)
        if sku is None:
            return ""
        if sku.status == "ready" and sku.name is not None and sku.price is not None:
            for line in self.cart:
                if line.sku_id == sku.id:
                    line.qty += 1
                    break
            else:
                self.cart.append(Line(sku.id, sku.name, sku.price, 1, sku.image))
            self.last_id = sku.id
            self.result = None
            return "sell"
        if sku.status == "unknown" and sku.valid:
            self.catalog[sku.id] = replace(sku, status="draft")
            if not any(d["code"] == sku.code for d in self.drafts):
                self.drafts.append(
                    {"id": sku.id, "code": sku.code, "origin": sku.origin, "name": "", "price": ""}
                )
            self.result = Result("learned", now_ms + self.RESULT_MS, code4=sku.code[-4:])
            return "saved"
        if sku.status == "draft":
            self.result = Result("pending", now_ms + self.RESULT_MS, code4=sku.code[-4:])
            return "saved"
        self.result = Result("unknown", now_ms + self.UNKNOWN_MS)
        return "nope"

    def tap(self, card_id: str, now_ms: int = 0) -> str:
        card = self.cards.get(card_id)
        if card is None:
            return ""
        if not self.cart:
            self.result = Result(
                "balance", now_ms + self.RESULT_MS, name=card.name, balance=card.balance
            )
            return "saved"
        total = self.cart_total()
        if card.balance < total:
            self.result = Result(
                "need",
                now_ms + self.RESULT_MS,
                name=card.name,
                need=total - card.balance,
            )
            return "nope"
        card.balance -= total
        self.result = Result(
            "paid",
            now_ms + self.RESULT_MS,
            name=card.name,
            total=total,
            balance=card.balance,
        )
        self.cart = []
        self.last_id = None
        return "paid"

    def clear(self) -> None:
        self.cart = []
        self.last_id = None
        self.result = None

    def finish_draft(self, code: str, name: str, yuan: int) -> bool:
        if not name or yuan < 0:
            return False
        draft = next((d for d in self.drafts if d["code"] == code), None)
        if draft is None:
            return False
        draft["name"] = name
        draft["price"] = str(yuan)
        for sku in self.catalog.values():
            if sku.code == code:
                self.catalog[sku.id] = replace(sku, status="ready", name=name, price=yuan)
                return True
        return False

    def view(self) -> ViewModel:
        n = self.cart_count()
        total = self.cart_total()
        if self.result:
            r = self.result
            if r.kind == "paid":
                return ViewModel(
                    "士多", "掃 · 拍", "ok", "card", r.total, "得", f"{r.name} 剩",
                    "", "剩", r.balance, "gold",
                )
            if r.kind == "need":
                return ViewModel(
                    "士多", "掃 · 拍", "nope", "card", None, "唔夠", r.name,
                    f"{n}件" if n else "", "差", r.need, "need",
                )
            if r.kind == "learned":
                return ViewModel(
                    "士多", "掃 · 拍", "soft", "barcode", None, "記低",
                    f"叫大人 ·{r.code4}",
                    f"{n}件" if n else "未賣",
                    "共" if n else "", total if n else None, "hot" if n else "dim",
                )
            if r.kind == "pending":
                return ViewModel(
                    "士多", "掃 · 拍", "soft", "barcode", None, "問大人",
                    f"·{r.code4}",
                    f"{n}件" if n else "",
                    "共" if n else "", total if n else None, "hot" if n else "dim",
                )
            if r.kind == "unknown":
                return ViewModel(
                    "士多", "掃 · 拍", "nope", "barcode", None, "唔識", "",
                    f"{n}件" if n else "",
                    "共" if n else "", total if n else None, "hot" if n else "",
                )
            return ViewModel(
                "士多", "掃 · 拍", "ok", "card", r.balance, r.name, "餘",
                "", "餘", r.balance, "gold",
            )

        last = self.catalog.get(self.last_id) if self.last_id else None
        if last and last.status == "ready" and self.cart:
            qty = next((ln.qty for ln in self.cart if ln.sku_id == last.id), 1)
            return ViewModel(
                "士多", "掃 · 拍", None,
                last.image or "idle",
                last.price, last.name or "",
                f"×{qty}" if qty > 1 else "",
                f"{n}件", "共", total, "hot",
            )
        return ViewModel(
            "士多", "掃 · 拍", None, "idle", None, "掃嘢", "拍卡",
            "", "共", 0, "dim",
        )
