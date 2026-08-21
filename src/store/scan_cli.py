"""Console scan: POST /pos/scan and print one line per barcode."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping
from typing import Protocol

import httpx2

from store.config import get_settings
from store.domain.money import format_yuan


class HttpResponse(Protocol):
    status_code: int

    def json(self) -> object: ...


class ScanClient(Protocol):
    def post(self, url: str, *, json: Mapping[str, str]) -> HttpResponse: ...


def format_scan(action: str, product: Mapping[str, object] | None) -> str:
    raw_code = (product or {}).get("barcode") or ""
    code = raw_code if isinstance(raw_code, str) else ""
    tail = code[-4:] if code else ""
    if action == "sell" and product:
        raw_name = product.get("name")
        name = raw_name if isinstance(raw_name, str) else code
        cents = product.get("price_cents")
        extra = f" {format_yuan(cents)}" if isinstance(cents, int) else ""
        return f"{name}{extra}"
    if action == "learned":
        return f"learned {tail}".rstrip()
    if action == "pending":
        return f"pending {tail}".rstrip()
    if action == "inactive":
        return f"inactive {tail}".rstrip()
    return action


def _action_from_body(body: object) -> str:
    if not isinstance(body, dict):
        return "error"
    action = body.get("action")
    if isinstance(action, str):
        return action
    detail = body.get("detail")
    if isinstance(detail, dict):
        nested = detail.get("action")
        if isinstance(nested, str):
            return nested
    return "error"


def scan_lines(client: ScanClient, barcodes: list[str]) -> list[str]:
    lines: list[str] = []
    for raw in barcodes:
        response = client.post("/pos/scan", json={"barcode": raw})
        if response.status_code == 422:
            lines.append("reject")
            continue
        if response.status_code not in {200, 201}:
            lines.append("error")
            continue
        body = response.json()
        product = body.get("product") if isinstance(body, dict) else None
        if not isinstance(product, dict):
            product = None
        lines.append(format_scan(_action_from_body(body), product))
    return lines


def run() -> None:
    parser = argparse.ArgumentParser(prog="store-scan")
    parser.add_argument("barcodes", nargs="*", help="omit to read stdin, one code per line")
    args = parser.parse_args()
    codes = list(args.barcodes)
    if not codes:
        codes = [line.strip() for line in sys.stdin if line.strip()]
    settings = get_settings()
    url = f"http://{settings.pos_host}:{settings.pos_port}"
    try:
        with httpx2.Client(base_url=url, timeout=5.0) as client:
            for line in scan_lines(client, codes):
                print(line)
    except httpx2.RequestError as exc:
        print(f"store-api down ({url}): {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    run()
