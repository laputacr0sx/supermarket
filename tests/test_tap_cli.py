from fastapi.testclient import TestClient

from store.api.app import create_app
from store.config import Settings
from store.persist.engine import create_schema, make_engine, make_session_factory
from store.seed import seed_session
from store.tap_cli import format_balance, tap_balance, tap_pay
from tests.conftest import CEREAL


def _client() -> TestClient:
    engine = make_engine(":memory:")
    create_schema(engine)
    session = make_session_factory(engine)()
    seed_session(session)
    session.commit()
    session.close()
    return TestClient(create_app(Settings(database=":memory:", docs=True), engine=engine))


def test_format_balance_shows_name_and_yuan():
    line = format_balance({"name": "樂樂", "balance_cents": 3000, "role": "child"})
    assert "樂樂" in line
    assert "30元" in line


def test_empty_tap_prints_balance():
    with _client() as client:
        line = tap_balance(client, "DEADBEEF")
    assert "樂樂" in line


def test_pay_then_402_then_unknown_card():
    with _client() as client:
        paid = tap_pay(client, "DEADBEEF", [CEREAL])
        assert paid.startswith("paid")
        need = tap_pay(client, "CAFEBABE", [CEREAL, CEREAL])
        assert need.startswith("need")
        missing = tap_balance(client, "FFFFFFFF")
        assert missing == "unknown card"
