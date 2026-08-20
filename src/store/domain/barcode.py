"""Normalize, check, mint EAN-13 / EAN-8. No I/O."""

from __future__ import annotations

import secrets
from enum import Enum


class BarcodeKind(Enum):
    VALID_EAN13 = "valid_ean13"
    VALID_EAN8 = "valid_ean8"
    INVALID = "invalid"


def normalize(raw: str) -> str:
    digits = "".join(ch for ch in raw.strip() if ch.isdigit() or ch in " -")
    digits = "".join(ch for ch in digits if ch.isdigit())
    if len(digits) == 12:
        return "0" + digits
    return digits


def ean13_check(body12: str) -> str:
    if len(body12) != 12 or not body12.isdigit():
        raise ValueError("ean13 body must be 12 digits")
    total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(body12))
    return str((10 - (total % 10)) % 10)


def ean8_check(body7: str) -> str:
    if len(body7) != 7 or not body7.isdigit():
        raise ValueError("ean8 body must be 7 digits")
    total = sum(int(d) * (3 if i % 2 == 0 else 1) for i, d in enumerate(body7))
    return str((10 - (total % 10)) % 10)


def classify(normalized: str) -> BarcodeKind:
    if (
        len(normalized) == 13
        and normalized.isdigit()
        and ean13_check(normalized[:12]) == normalized[12]
    ):
        return BarcodeKind.VALID_EAN13
    if (
        len(normalized) == 8
        and normalized.isdigit()
        and ean8_check(normalized[:7]) == normalized[7]
    ):
        return BarcodeKind.VALID_EAN8
    return BarcodeKind.INVALID


def is_valid(normalized: str) -> bool:
    return classify(normalized) is not BarcodeKind.INVALID


def mint_store_ean13(
    existing: set[str],
    prefix_min: int = 200,
    prefix_max: int = 299,
) -> str:
    if prefix_min < 200 or prefix_max > 299 or prefix_min > prefix_max:
        raise ValueError("shop prefixes must sit in 200–299")
    span = prefix_max - prefix_min + 1
    for _ in range(64):
        prefix = prefix_min + secrets.randbelow(span)
        item = secrets.randbelow(1_000_000_000)
        body = f"{prefix:03d}{item:09d}"
        code = body + ean13_check(body)
        if code not in existing:
            return code
    raise RuntimeError("could not mint a unique shop EAN-13")
