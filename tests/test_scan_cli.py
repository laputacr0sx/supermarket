from fastapi.testclient import TestClient

from store.api.app import create_app
from store.config import Settings
from store.persist.engine import create_schema, make_engine, make_session_factory
from store.scan_cli import format_scan, scan_lines
from store.seed import seed_session
from tests.conftest import CEREAL, UNKNOWN_OK


def _client() -> TestClient:
    engine = make_engine(":memory:")
    create_schema(engine)
    session = make_session_factory(engine)()
    seed_session(session)
    session.commit()
    session.close()
    app = create_app(Settings(database=":memory:", docs=True), engine=engine)
    return TestClient(app)


def test_format_sell_prints_name_and_yuan():
    line = format_scan("sell", {"name": "麥片", "barcode": CEREAL, "price_cents": 1200})
    assert "麥片" in line
    assert "12元" in line


def test_scan_lines_ready_learn_pending_reject():
    with _client() as client:
        lines = scan_lines(client, [CEREAL, UNKNOWN_OK, UNKNOWN_OK, "not-a-code"])
    assert "麥片" in lines[0]
    assert lines[1].startswith("learned")
    assert lines[2].startswith("pending")
    assert lines[3] == "reject"
