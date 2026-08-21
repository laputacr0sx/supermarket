from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from store.config import Settings
from store.domain.barcode import ean13_check
from store.domain.money import yuan_to_cents
from store.persist.engine import create_schema, make_engine, make_session_factory
from store.persist.tables import Account, Card, Product


def ean13(body12: str) -> str:
    return body12 + ean13_check(body12)


CEREAL = ean13("489000000001")
MILK = ean13("489000000002")
TOMATO = ean13("200184739201")
DRAFT = ean13("271840395761")
UNKNOWN_OK = ean13("590123412345")


@pytest.fixture(autouse=True)
def isolate_store_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Host STORE_* and default.toml must not point tests at a real sqlite file."""
    for key in list(os.environ):
        if key.startswith("STORE_"):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("STORE_DATABASE", ":memory:")


@pytest.fixture
def engine() -> Iterator[Engine]:
    eng = make_engine(":memory:")
    create_schema(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    factory = make_session_factory(engine)
    sess = factory()
    yield sess
    sess.rollback()
    sess.close()


@pytest.fixture
def seeded(session: Session) -> Session:
    now = "2026-08-18T00:00:00+00:00"
    session.add_all(
        [
            Product(
                barcode=CEREAL,
                origin="household",
                status="ready",
                name="麥片",
                price_cents=yuan_to_cents(12),
                stock=10,
                active=1,
                created_at=now,
            ),
            Product(
                barcode=MILK,
                origin="household",
                status="ready",
                name="牛奶",
                price_cents=yuan_to_cents(8),
                stock=None,
                active=1,
                created_at=now,
            ),
            Product(
                barcode=TOMATO,
                origin="store",
                status="ready",
                name="蕃茄",
                price_cents=yuan_to_cents(3),
                active=1,
                created_at=now,
            ),
            Product(
                barcode=DRAFT,
                origin="store",
                status="draft",
                name=None,
                price_cents=None,
                active=1,
                created_at=now,
            ),
        ]
    )
    lele = Card(uid="DEADBEEF", child_name="樂樂", role="child", active=1)
    sam = Card(uid="CAFEBABE", child_name="森", role="child", active=1)
    staff = Card(uid="0FF1CE", child_name="職員", role="staff", active=1)
    dead = Card(uid="00DEAD", child_name="停用", role="child", active=0)
    session.add_all([lele, sam, staff, dead])
    session.flush()
    session.add_all(
        [
            Account(card_id=lele.id, balance_cents=yuan_to_cents(30)),
            Account(card_id=sam.id, balance_cents=yuan_to_cents(5)),
            Account(card_id=staff.id, balance_cents=0),
            Account(card_id=dead.id, balance_cents=yuan_to_cents(10)),
        ]
    )
    session.commit()
    return session


@pytest.fixture
def settings() -> Settings:
    return Settings(database=":memory:", docs=True, learn_on_unknown=True)
