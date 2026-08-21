from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine

from store.api.app import create_admin_app
from store.config import Settings
from store.persist.engine import create_schema, make_engine, make_session_factory
from store.seed import seed_session
from store.services import catalog, checkout
from store.services.checkout import CheckoutItem
from tests.conftest import CEREAL, UNKNOWN_OK, ean13

_TEST_USER = "admin"
_TEST_PASSWORD = "test-only-password"
_AUTH = (_TEST_USER, _TEST_PASSWORD)
_PANTRY = ean13("590123412346")


def _build(tmp_path: Path, *, password: str = _TEST_PASSWORD) -> tuple[TestClient, Engine]:
    engine = make_engine(":memory:")
    create_schema(engine)
    session = make_session_factory(engine)()
    seed_session(session)
    catalog.scan(session, UNKNOWN_OK)
    session.commit()
    session.close()
    settings = Settings(
        database=":memory:",
        docs=True,
        admin_user=_TEST_USER,
        admin_password=password,
        product_images=str(tmp_path / "images"),
    )
    return TestClient(create_admin_app(settings, engine=engine)), engine


@pytest.fixture
def admin(tmp_path: Path) -> Iterator[TestClient]:
    client, _engine = _build(tmp_path)
    with client:
        yield client


def test_admin_requires_auth(admin: TestClient) -> None:
    assert admin.get("/").status_code == 401


def test_wrong_password_rejected(admin: TestClient) -> None:
    assert admin.get("/", auth=(_TEST_USER, "nope")).status_code == 401


def test_empty_password_never_logs_in(tmp_path: Path) -> None:
    client, _engine = _build(tmp_path, password="")
    with client:
        assert client.get("/", auth=(_TEST_USER, "")).status_code == 401


def test_drafts_page_lists_learned_code(admin: TestClient) -> None:
    page = admin.get("/", auth=_AUTH)
    assert page.status_code == 200
    assert UNKNOWN_OK in page.text
    assert "未完成" in page.text


def test_finish_draft_then_gone_from_unfinished(admin: TestClient) -> None:
    posted = admin.post(
        f"/products/{UNKNOWN_OK}/finish",
        data={"name": "牙膏", "yuan": "9"},
        auth=_AUTH,
        follow_redirects=False,
    )
    assert posted.status_code in {302, 303}
    page = admin.get("/", auth=_AUTH)
    assert UNKNOWN_OK not in page.text
    shelf = admin.get("/shelf", auth=_AUTH)
    assert "牙膏" in shelf.text


def test_finish_saves_photo(tmp_path: Path) -> None:
    client, _engine = _build(tmp_path)
    with client:
        posted = client.post(
            f"/products/{UNKNOWN_OK}/finish",
            data={"name": "牙膏", "yuan": "9"},
            files={"photo": ("cam.jpg", b"\xff\xd8\xff\xd9", "image/jpeg")},
            auth=_AUTH,
            follow_redirects=False,
        )
        assert posted.status_code in {302, 303}
        photos = list((tmp_path / "images").glob("*.jpg"))
        assert len(photos) == 1
        assert photos[0].read_bytes() == b"\xff\xd8\xff\xd9"


def test_drop_draft(admin: TestClient) -> None:
    posted = admin.post(
        f"/products/{UNKNOWN_OK}/drop",
        auth=_AUTH,
        follow_redirects=False,
    )
    assert posted.status_code in {302, 303}
    assert UNKNOWN_OK not in admin.get("/", auth=_AUTH).text


def test_learn_typed_barcode(admin: TestClient) -> None:
    posted = admin.post(
        "/learn",
        data={"barcode": _PANTRY},
        auth=_AUTH,
        follow_redirects=False,
    )
    assert posted.status_code in {302, 303}
    assert _PANTRY in admin.get("/", auth=_AUTH).text


def test_label_sheet_is_pdf(admin: TestClient) -> None:
    pdf = admin.get("/sheet.pdf", auth=_AUTH)
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF")


def test_reprint_selected_is_pdf(admin: TestClient) -> None:
    pdf = admin.post("/reprint.pdf", data={"barcodes": UNKNOWN_OK}, auth=_AUTH)
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF")


def test_enroll_and_topup(admin: TestClient) -> None:
    posted = admin.post(
        "/cards",
        data={"uid": "AABBCCDD", "name": "杏", "role": "child", "yuan": "15"},
        auth=_AUTH,
        follow_redirects=False,
    )
    assert posted.status_code in {302, 303}
    page = admin.get("/cards", auth=_AUTH)
    assert "杏" in page.text
    topped = admin.post(
        "/cards/CAFEBABE/topup",
        data={"yuan": "10"},
        auth=_AUTH,
        follow_redirects=False,
    )
    assert topped.status_code in {302, 303}
    after = admin.get("/cards", auth=_AUTH)
    assert "15元" in after.text


def test_sales_today_and_void(tmp_path: Path) -> None:
    client, engine = _build(tmp_path)
    with client:
        session = make_session_factory(engine)()
        checkout.checkout(session, "DEADBEEF", [CheckoutItem(CEREAL, 1)])
        session.commit()
        session.close()
        page = client.get("/sales", auth=_AUTH)
        assert page.status_code == 200
        assert "樂樂" in page.text
        voided = client.post("/void-last", auth=_AUTH, follow_redirects=False)
        assert voided.status_code in {302, 303}
        after = client.get("/sales", auth=_AUTH)
        assert "作廢" in after.text


def test_doctor_page(admin: TestClient) -> None:
    page = admin.get("/doctor", auth=_AUTH)
    assert page.status_code == 200
    assert "API 正常" in page.text


def test_deactivate_ready_product(admin: TestClient) -> None:
    admin.post(
        f"/products/{UNKNOWN_OK}/finish",
        data={"name": "牙膏", "yuan": "9"},
        auth=_AUTH,
    )
    posted = admin.post(
        f"/products/{UNKNOWN_OK}/deactivate",
        auth=_AUTH,
        follow_redirects=False,
    )
    assert posted.status_code in {302, 303}
    assert "停用" in admin.get("/shelf", auth=_AUTH).text
