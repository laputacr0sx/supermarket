from __future__ import annotations

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from store.config import Settings, get_settings
from store.persist.engine import create_schema, make_engine, make_session_factory


def create_app(settings: Settings | None = None, *, engine=None) -> FastAPI:
    settings = settings or get_settings()
    docs = "/docs" if settings.docs else None

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        eng = engine or make_engine(settings.database)
        create_schema(eng)
        app.state.engine = eng
        app.state.session_factory = make_session_factory(eng)
        app.state.settings = settings
        app.state.idempotency = {}
        yield
        eng.dispose()

    app = FastAPI(
        title="store-api",
        lifespan=lifespan,
        docs_url=docs,
        redoc_url=None if not settings.docs else "/redoc",
    )
    from store.api.routes_pos import router as pos_router

    app.include_router(pos_router)
    return app


def run() -> None:
    settings = get_settings()
    uvicorn.run(
        "store.api.app:create_app",
        factory=True,
        host=settings.pos_host,
        port=settings.pos_port,
        reload=False,
    )
