from __future__ import annotations

import threading
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from store.config import Settings, get_settings
from store.persist.engine import create_schema, make_engine, make_session_factory


def _lifespan(settings: Settings, engine):
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        eng = engine or make_engine(settings.database)
        create_schema(eng)
        app.state.engine = eng
        app.state.session_factory = make_session_factory(eng)
        app.state.settings = settings
        app.state.idempotency = {}
        yield
        if engine is None:
            eng.dispose()

    return lifespan


def create_app(settings: Settings | None = None, *, engine=None) -> FastAPI:
    settings = settings or get_settings()
    docs = "/docs" if settings.docs else None
    app = FastAPI(
        title="store-api",
        lifespan=_lifespan(settings, engine),
        docs_url=docs,
        redoc_url=None if not settings.docs else "/redoc",
    )
    from store.api.routes_pos import router as pos_router

    app.include_router(pos_router)
    return app


def create_admin_app(settings: Settings | None = None, *, engine=None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(
        title="store-admin",
        lifespan=_lifespan(settings, engine),
        docs_url=None,
        redoc_url=None,
    )
    from store.api.routes_admin import router as admin_router

    app.include_router(admin_router)
    return app


def run() -> None:
    settings = get_settings()
    engine = make_engine(settings.database)
    create_schema(engine)
    admin_app = create_admin_app(settings, engine=engine)
    pos_app = create_app(settings, engine=engine)
    threading.Thread(
        target=lambda: uvicorn.run(
            admin_app,
            host=settings.admin_host,
            port=settings.admin_port,
            reload=False,
        ),
        daemon=True,
        name="store-admin",
    ).start()
    uvicorn.run(pos_app, host=settings.pos_host, port=settings.pos_port, reload=False)
