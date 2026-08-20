"""httpx2 client for the till. Maps HTTP to FSM replies."""

from __future__ import annotations

import httpx2

from store.kiosk.fsm import Line, PayReply, ScanReply


class Api:
    def __init__(self, base_url: str) -> None:
        self._client = httpx2.Client(base_url=base_url, timeout=5.0)

    def close(self) -> None:
        self._client.close()

    def scan(self, code: str) -> ScanReply:
        response = self._client.post("/pos/scan", json={"barcode": code})
        if response.status_code == 422:
            return ScanReply("reject", None)
        if response.status_code not in {200, 201}:
            return ScanReply("reject", None)
        body = response.json()
        action = body.get("action") if isinstance(body, dict) else None
        product = body.get("product") if isinstance(body, dict) else None
        if not isinstance(action, str):
            return ScanReply("reject", None)
        return ScanReply(action, product if isinstance(product, dict) else None)

    def pay(self, uid: str, items: tuple[Line, ...]) -> PayReply:
        payload = {
            "uid": uid,
            "items": [{"barcode": line.barcode, "qty": line.qty} for line in items],
        }
        response = self._client.post("/pos/checkout", json=payload)
        if response.status_code == 200:
            body = response.json()
            return PayReply(
                "paid",
                total_cents=body.get("total_cents"),
                balance_cents=body.get("balance_cents"),
            )
        if response.status_code == 402:
            detail = response.json().get("detail")
            need = detail.get("need_cents") if isinstance(detail, dict) else None
            return PayReply("need", need_cents=need if isinstance(need, int) else None)
        return PayReply("unknown")

    def card(self, uid: str) -> PayReply:
        response = self._client.get(f"/pos/cards/{uid}")
        if response.status_code != 200:
            return PayReply("unknown")
        body = response.json()
        return PayReply(
            "balance",
            balance_cents=body.get("balance_cents"),
            name=str(body.get("name") or ""),
        )
