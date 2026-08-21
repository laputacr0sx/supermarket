"""Kid-till chrome in written Traditional Chinese.

Edit the `Copy` fields below. `fsm.view()` and the pygame prototype both
read `COPY`. Product names (麥片, 蕃茄, …) live on catalog rows, not here.

Strings stay inside 常用字字形表 so Free HK Kai 4700 can draw every glyph.
No spoken-Cantonese particles (嘢、咗、唔、啦、仲、撳、畀、睇).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Copy:
    store: str = "士多"
    pill: str = "請拍卡"
    yuan: str = "元"
    idle_title: str = "請掃"
    idle_sub: str = "拍卡"
    idle_glyph: str = "掃"
    paid: str = "完成"
    paid_sub: str = "{name} 餘額"
    remain: str = "餘額"
    need: str = "不足"
    short: str = "差"
    learned: str = "記下"
    call_adult: str = "請找大人 ·{code4}"
    ask_adult: str = "問大人"
    unknown: str = "不識"
    still_have: str = "餘額"
    total: str = "合計"
    empty_cart: str = "未掃"
    pieces: str = "{n}件"
    staff_header: str = "STAFF"
    staff_pill: str = "F5–F10"

    def cart_count(self, n: int, *, empty: str = "") -> str:
        if n <= 0:
            return empty
        return self.pieces.format(n=n)

    def leftover_of(self, name: str) -> str:
        return self.paid_sub.format(name=name)

    def call_adult_for(self, code4: str) -> str:
        return self.call_adult.format(code4=code4)

    def ask_code(self, code4: str) -> str:
        return f"·{code4}"

    def qty_mark(self, qty: int) -> str:
        return f"×{qty}" if qty > 1 else ""


COPY = Copy()
