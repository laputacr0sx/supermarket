"""Console scan: POST /pos/scan and print one line per barcode."""

from __future__ import annotations

import argparse
import sys

import httpx2

from store.config import get_settings


def format_scan(action: str, product: dict | None) -> str:
    code = (product or {}).get("barcode") or ""
    tail = code[-4:] if code else ""
    if action == "sell" and product:
        name = product.get("name") or code
        cents = product.get("price_cents")
        yuan = f" {cents // 100}元" if cents is not None else ""
        return f"{name}{yuan}"
    if action == "learned":
        return f"learned {tail}".rstrip()
    if action == "pending":
        return f"pending {tail}".rstrip()
    if action == "inactive":
        return f"inactive {tail}".rstrip()
    return action


def scan_lines(client, barcodes: list[str]) -> list[str]:
    lines: list[str] = []
    for raw in barcodes:
        response = client.post("/pos/scan", json={"barcode": raw})
        if response.status_code == 422:
            lines.append("reject")
            continue
        body = response.json()
        action = body.get("action") or body.get("detail", {}).get("action", "error")
        lines.append(format_scan(action, body.get("product")))
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
    with httpx2.Client(base_url=url, timeout=5.0) as client:
        for line in scan_lines(client, codes):
            print(line)


if __name__ == "__main__":
    run()
