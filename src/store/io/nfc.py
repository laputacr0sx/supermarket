"""NFC UID normalize and 2s debounce. PC/SC grab waits for the LIFEBOOK."""

from __future__ import annotations

import re

_HEX = re.compile(r"^[0-9A-F]+$")


def normalize_uid(raw: str) -> str:
    uid = raw.upper().replace(":", "").replace(" ", "")
    if not uid or not _HEX.fullmatch(uid):
        raise ValueError("uid")
    return uid


def accept_tap(
    last_uid: str | None,
    last_at: float,
    raw: str,
    *,
    now: float,
    window_s: float = 2.0,
) -> str | None:
    uid = normalize_uid(raw)
    if last_uid == uid and now - last_at < window_s:
        return None
    return uid
