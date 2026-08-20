"""HID scanner: key names → barcode. grab() is Linux-only and optional."""

from __future__ import annotations

_DIGIT = {f"KEY_{d}": str(d) for d in range(1, 10)}
_DIGIT["KEY_0"] = "0"
_DIGIT["KEY_KP0"] = "0"
for d in range(1, 10):
    _DIGIT[f"KEY_KP{d}"] = str(d)


def key_to_char(name: str) -> str | None:
    if name == "KEY_ENTER" or name == "KEY_KPENTER":
        return "\n"
    return _DIGIT.get(name)


def assemble(events: list[tuple[str, int]]) -> list[str]:
    """Complete barcodes from (KEY_*, value) pairs. value 1 = down, 2 = repeat."""
    codes: list[str] = []
    buf: list[str] = []
    for name, value in events:
        if value != 1:
            continue
        ch = key_to_char(name)
        if ch is None:
            continue
        if ch == "\n":
            if buf:
                codes.append("".join(buf))
                buf = []
            continue
        buf.append(ch)
    return codes
