"""Tap a card: empty = balance; --item barcodes = checkout."""

from __future__ import annotations

import argparse
import sys
from typing import Any, Protocol

import httpx2

from store.config import get_settings
from store.domain.money import format_yuan, yuan_to_cents
from store.domain.uid import normalize_uid


class TapClient(Protocol):
    def get(self, url: str) -> Any: ...
    def post(self, url: str, json: dict) -> Any: ...


def format_balance(card: dict) -> str:
    name = card.get("name") or card.get("uid") or ""
    cents = card.get("balance_cents")
    extra = f" {format_yuan(cents)}" if isinstance(cents, int) else ""
    return f"{name}{extra}"


def format_checkout(body: dict) -> str:
    total = body.get("total_cents")
    left = body.get("balance_cents")
    bits = ["paid"]
    if isinstance(total, int):
        bits.append(format_yuan(total))
    if isinstance(left, int):
        bits.append(f"剩 {format_yuan(left)}")
    return " ".join(bits)


def tap_balance(client: TapClient, uid: str) -> str:
    uid = normalize_uid(uid)
    response = client.get(f"/pos/cards/{uid}")
    if response.status_code == 404:
        return "unknown card"
    if response.status_code != 200:
        return "error"
    return format_balance(response.json())


def tap_pay(client: TapClient, uid: str, barcodes: list[str]) -> str:
    uid = normalize_uid(uid)
    items = [{"barcode": code, "qty": 1} for code in barcodes]
    response = client.post("/pos/checkout", json={"uid": uid, "items": items})
    if response.status_code == 200:
        return format_checkout(response.json())
    if response.status_code == 402:
        detail = response.json().get("detail")
        need = detail.get("need_cents") if isinstance(detail, dict) else None
        if isinstance(need, int):
            return f"need {format_yuan(need)}"
        return "need"
    if response.status_code == 404:
        return "not found"
    return "error"


def tap_topup(client: TapClient, uid: str, amount_cents: int) -> str:
    uid = normalize_uid(uid)
    response = client.post(
        "/pos/ledger",
        json={"uid": uid, "kind": "topup", "amount_cents": amount_cents},
    )
    if response.status_code == 404:
        return "unknown card"
    if response.status_code != 200:
        return "error"
    body = response.json()
    left = body.get("balance_cents")
    extra = f" {format_yuan(left)}" if isinstance(left, int) else ""
    return f"topup{extra}"


def run() -> None:
    parser = argparse.ArgumentParser(prog="store-tap")
    parser.add_argument("uid")
    exclusive = parser.add_mutually_exclusive_group()
    exclusive.add_argument("--item", action="append", dest="items")
    exclusive.add_argument("--topup", type=int, metavar="YUAN")
    args = parser.parse_args()
    settings = get_settings()
    url = f"http://{settings.pos_host}:{settings.pos_port}"
    try:
        with httpx2.Client(base_url=url, timeout=5.0) as client:
            if args.topup is not None:
                print(tap_topup(client, args.uid, yuan_to_cents(args.topup)))
            elif args.items:
                print(tap_pay(client, args.uid, args.items))
            else:
                print(tap_balance(client, args.uid))
    except httpx2.RequestError as exc:
        print(f"store-api down ({url}): {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except ValueError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    run()
