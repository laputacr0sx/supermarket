"""Save phone-camera JPEGs next to the product id."""

from __future__ import annotations

from pathlib import Path

from store.domain.errors import ProductNotSellable

_MAX_BYTES = 4 * 1024 * 1024


def save_product_photo(directory: Path, product_id: int, data: bytes) -> str:
    if not data:
        raise ProductNotSellable("photo empty")
    if len(data) > _MAX_BYTES:
        raise ProductNotSellable("photo too large")
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{product_id}.jpg"
    path.write_bytes(data)
    return str(path)