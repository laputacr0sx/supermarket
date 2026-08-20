from fastapi.testclient import TestClient

from store.api.app import create_admin_app
from store.config import Settings
from store.persist.engine import create_schema, make_engine, make_session_factory
from store.seed import seed_session
from store.services import catalog
from tests.conftest import UNKNOWN_OK

AUTH = ("admin", "play")


def _client() -> TestClient:
    engine = make_engine(":memory:")
    create_schema(engine)
    session = make_session_factory(engine)()
    seed_session(session)
    catalog.scan(session, UNKNOWN_OK)
    session.commit()
    session.close()
    settings = Settings(database=":memory:", docs=True, admin_password="play")
    return TestClient(create_admin_app(settings, engine=engine))


def test_admin_requires_auth():
    with _client() as client:
        assert client.get("/").status_code == 401


def test_drafts_page_lists_learned_code():
    with _client() as client:
        page = client.get("/", auth=AUTH)
        assert page.status_code == 200
        assert UNKNOWN_OK in page.text
        assert "未完成" in page.text


def test_finish_draft_then_gone_from_unfinished():
    with _client() as client:
        posted = client.post(
            f"/products/{UNKNOWN_OK}/finish",
            data={"name": "牙膏", "yuan": "9"},
            auth=AUTH,
            follow_redirects=False,
        )
        assert posted.status_code in {302, 303}
        page = client.get("/", auth=AUTH)
        assert UNKNOWN_OK not in page.text


def test_label_sheet_is_pdf():
    with _client() as client:
        pdf = client.get("/sheet.pdf", auth=AUTH)
        assert pdf.status_code == 200
        assert pdf.content.startswith(b"%PDF")
