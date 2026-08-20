"""Card UID: uppercase hex, no colons."""

from __future__ import annotations

import re

_HEX = re.compile(r"^[0-9A-F]+$")


def normalize_uid(raw: str) -> str:
    uid = raw.upper().replace(":", "").replace(" ", "")
    if not uid or not _HEX.fullmatch(uid):
        raise ValueError("uid")
    return uid
