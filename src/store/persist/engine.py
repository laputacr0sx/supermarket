from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Protocol

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from store.persist.tables import Base


def sqlite_url(database: str) -> str:
    if database in {":memory:", "sqlite:///:memory:", "sqlite+pysqlite:///:memory:"}:
        return "sqlite+pysqlite:///:memory:"
    path = Path(database)
    if not path.is_absolute() and database.startswith("sqlite"):
        return database
    path.parent.mkdir(parents=True, exist_ok=True)
    return "sqlite+pysqlite:///" + path.resolve().as_posix()


class _DbapiCursor(Protocol):
    def execute(self, statement: str) -> object: ...
    def close(self) -> None: ...


class _DbapiConnection(Protocol):
    isolation_level: str | None

    def cursor(self) -> _DbapiCursor: ...


def _apply_pragmas(dbapi_conn: _DbapiConnection, _connection_record: object) -> None:
    # SQLAlchemy emits BEGIN; stop sqlite3 from emitting its own.
    dbapi_conn.isolation_level = None
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


def _begin_immediate(conn: Connection) -> None:
    conn.exec_driver_sql("BEGIN IMMEDIATE")


def make_engine(database: str) -> Engine:
    url = sqlite_url(database)
    memory = ":memory:" in url
    connect_args = {"check_same_thread": False}
    if memory:
        engine = create_engine(
            url, future=True, connect_args=connect_args, poolclass=StaticPool
        )
    else:
        engine = create_engine(url, future=True, connect_args=connect_args)
    event.listen(engine, "connect", _apply_pragmas)
    event.listen(engine, "begin", _begin_immediate)
    return engine


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_schema(engine: Engine) -> None:
    Base.metadata.create_all(engine)
