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
        if not isinstance(body, dict):
            return ScanReply("reject", None)
        action = body.get("action")
        product = body.get("product")
        if not isinstance(action, str):
            return ScanReply("reject", None)
        if not isinstance(product, dict):
            return ScanReply(action, None)
        return ScanReply(action, {str(k): v for k, v in product.items()})

    def pay(self, uid: str, items: tuple[Line, ...]) -> PayReply:
        payload: dict[str, object] = {
            "uid": uid,
            "items": [{"barcode": line.barcode, "qty": line.qty} for line in items],
        }
        response = self._client.post("/pos/checkout", json=payload)
        if response.status_code == 200:
            body = response.json()
            if not isinstance(body, dict):
                return PayReply("unknown")
            total = body.get("total_cents")
            balance = body.get("balance_cents")
            return PayReply(
                "paid",
                total_cents=total if isinstance(total, int) else None,
                balance_cents=balance if isinstance(balance, int) else None,
            )
        if response.status_code == 402:
            payload = response.json()
            detail = payload.get("detail") if isinstance(payload, dict) else None
            need = detail.get("need_cents") if isinstance(detail, dict) else None
            return PayReply("need", need_cents=need if isinstance(need, int) else None)
        return PayReply("unknown")

    def card(self, uid: str) -> PayReply:
        response = self._client.get(f"/pos/cards/{uid}")
        if response.status_code != 200:
            return PayReply("unknown")
        body = response.json()
        if not isinstance(body, dict):
            return PayReply("unknown")
        balance = body.get("balance_cents")
        return PayReply(
            "balance",
            balance_cents=balance if isinstance(balance, int) else None,
            name=str(body.get("name") or ""),
        )

    def ledger(self, uid: str, kind: str, amount_cents: int | None) -> PayReply:
        response = self._client.post(
            "/pos/ledger",
            json={"uid": uid, "kind": kind, "amount_cents": amount_cents},
        )
        if response.status_code != 200:
            return PayReply("unknown")
        body = response.json()
        if not isinstance(body, dict):
            return PayReply("unknown")
        balance = body.get("balance_cents")
        return PayReply("balance", balance_cents=balance if isinstance(balance, int) else None)

    def void_last(self) -> PayReply:
        response = self._client.post("/pos/void-last", json={})
        if response.status_code != 200:
            return PayReply("unknown")
        body = response.json()
        if not isinstance(body, dict):
            return PayReply("unknown")
        balance = body.get("balance_cents")
        return PayReply("balance", balance_cents=balance if isinstance(balance, int) else None)
