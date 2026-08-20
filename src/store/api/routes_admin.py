from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from store.api.deps import get_session, require_admin
from store.domain.errors import StoreError
from store.domain.money import yuan_to_cents
from store.services import catalog, labels

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))

router = APIRouter(dependencies=[Depends(require_admin)])
SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/", response_class=HTMLResponse)
def home(request: Request, session: SessionDep) -> HTMLResponse:
    drafts = catalog.list_drafts(session)
    return TEMPLATES.TemplateResponse(
        request,
        "drafts.html",
        {"drafts": drafts, "store_name": request.app.state.settings.store_name},
    )


@router.post("/products/{barcode}/finish")
def finish(
    barcode: str,
    session: SessionDep,
    name: Annotated[str, Form()],
    yuan: Annotated[str, Form()],
) -> RedirectResponse:
    try:
        cents = yuan_to_cents(int(yuan))
        catalog.finish(session, barcode, name=name, price_cents=cents)
    except (StoreError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse("/", status_code=303)


@router.get("/sheet.pdf")
def sheet(request: Request, session: SessionDep) -> FileResponse:
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp.close()
    path = Path(tmp.name)
    labels.print_sheet(
        session,
        path,
        labels.PAGE,
        prefix_min=request.app.state.settings.store_prefix_min,
        prefix_max=request.app.state.settings.store_prefix_max,
    )
    return FileResponse(path, media_type="application/pdf", filename="labels.pdf")
