"""NFC UID debounce. PC/SC grab waits for the LIFEBOOK."""

from __future__ import annotations

from store.domain.uid import normalize_uid


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
