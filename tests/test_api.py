from fastapi.testclient import TestClient

from store.api.app import create_app
from store.config import Settings
from store.domain.barcode import ean13_check
from store.domain.money import yuan_to_cents
from store.persist.engine import create_schema, make_engine, make_session_factory
from store.seed import seed_session
from tests.conftest import CEREAL, DRAFT, MILK, UNKNOWN_OK

TOMATO_SAFE = "200184739201" + ean13_check("200184739201")


def _client() -> TestClient:
    engine = make_engine(":memory:")
    create_schema(engine)
    factory = make_session_factory(engine)
    session = factory()
    seed_session(session)
    # add the draft SKU used by checkout-404 tests
    from datetime import UTC, datetime

    from store.persist.tables import Product

    session.add(
        Product(
            barcode=DRAFT,
            origin="store",
            status="draft",
            created_at=datetime.now(UTC).replace(microsecond=0).isoformat(),
        )
    )
    session.commit()
    session.close()
    settings = Settings(database=":memory:", docs=True)
    app = create_app(settings, engine=engine)
    return TestClient(app)


def test_scan_ready_then_unknown_then_garbage() -> None:
    with _client() as client:
        ready = client.post("/pos/scan", json={"barcode": CEREAL})
        assert ready.status_code == 200
        assert ready.json()["action"] == "sell"
        assert ready.json()["product"]["name"] == "麥片"

        learned = client.post("/pos/scan", json={"barcode": UNKNOWN_OK})
        assert learned.status_code == 201
        assert learned.json()["action"] == "learned"

        pending = client.post("/pos/scan", json={"barcode": UNKNOWN_OK})
        assert pending.status_code == 200
        assert pending.json()["action"] == "pending"

        bad = client.post("/pos/scan", json={"barcode": "not-a-barcode"})
        assert bad.status_code == 422


def test_get_product_does_not_learn() -> None:
    with _client() as client:
        missing = client.get(f"/pos/products/{UNKNOWN_OK}")
        assert missing.status_code == 404


def test_checkout_and_402_and_draft() -> None:
    with _client() as client:
        draft = client.post(
            "/pos/checkout",
            json={"uid": "DEADBEEF", "items": [{"barcode": DRAFT, "qty": 1}]},
        )
        assert draft.status_code == 404

        paid = client.post(
            "/pos/checkout",
            json={"uid": "DEADBEEF", "items": [{"barcode": CEREAL, "qty": 1}]},
        )
        assert paid.status_code == 200
        assert paid.json()["total_cents"] == yuan_to_cents(12)

        poor = client.post(
            "/pos/checkout",
            json={
                "uid": "CAFEBABE",
                "items": [
                    {"barcode": CEREAL, "qty": 1},
                    {"barcode": MILK, "qty": 1},
                ],
            },
        )
        assert poor.status_code == 402
        assert poor.json()["detail"]["need_cents"] == yuan_to_cents(15)


def test_idempotency_key_replays() -> None:
    with _client() as client:
        headers = {"Idempotency-Key": "play-1"}
        first = client.post(
            "/pos/checkout",
            json={"uid": "DEADBEEF", "items": [{"barcode": TOMATO_SAFE, "qty": 1}]},
            headers=headers,
        )
        second = client.post(
            "/pos/checkout",
            json={"uid": "DEADBEEF", "items": [{"barcode": TOMATO_SAFE, "qty": 1}]},
            headers=headers,
        )
        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["sale_id"] == second.json()["sale_id"]


def test_card_and_topup() -> None:
    with _client() as client:
        card = client.get("/pos/cards/DEADBEEF")
        assert card.status_code == 200
        assert card.json()["name"] == "樂樂"
        top = client.post(
            "/pos/ledger",
            json={"uid": "CAFEBABE", "kind": "topup", "amount_cents": yuan_to_cents(10)},
        )
        assert top.status_code == 200
        assert top.json()["balance_cents"] == yuan_to_cents(15)


def test_uid_debounce_is_409() -> None:
    with _client() as client:
        first = client.post(
            "/pos/checkout",
            json={"uid": "DEADBEEF", "items": [{"barcode": CEREAL, "qty": 1}]},
        )
        second = client.post(
            "/pos/checkout",
            json={"uid": "DEADBEEF", "items": [{"barcode": MILK, "qty": 1}]},
        )
        assert first.status_code == 200
        assert second.status_code == 409
        assert second.json()["detail"] == "duplicate checkout"


def test_pos_body_validation() -> None:
    with _client() as client:
        empty_cart = client.post("/pos/checkout", json={"uid": "DEADBEEF", "items": []})
        assert empty_cart.status_code == 422

        empty_scan = client.post("/pos/scan", json={"barcode": ""})
        assert empty_scan.status_code == 422

        bad_kind = client.post(
            "/pos/ledger",
            json={"uid": "DEADBEEF", "kind": "gift", "amount_cents": 100},
        )
        assert bad_kind.status_code == 422

        topup_zero = client.post(
            "/pos/ledger",
            json={"uid": "DEADBEEF", "kind": "topup", "amount_cents": 0},
        )
        assert topup_zero.status_code == 422
