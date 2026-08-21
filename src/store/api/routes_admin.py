from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from store.api.deps import get_session, require_admin
from store.config import Settings
from store.domain.errors import StoreError
from store.domain.money import yuan_to_cents
from store.persist.tables import Card
from store.services import cards, catalog, labels, ledger
from store.services.photos import save_product_photo

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))

router = APIRouter(dependencies=[Depends(require_admin)])
SessionDep = Annotated[Session, Depends(get_session)]


@dataclass(frozen=True)
class CardRow:
    card: Card
    balance_cents: int


def _ctx(request: Request, **extra: object) -> dict[str, object]:
    return {"store_name": request.app.state.settings.store_name, **extra}


def _settings(request: Request) -> Settings:
    settings = request.app.state.settings
    if not isinstance(settings, Settings):
        raise RuntimeError("settings missing")
    return settings


def _html(request: Request, name: str, **extra: object) -> HTMLResponse:
    return TEMPLATES.TemplateResponse(request, name, _ctx(request, **extra))


def _see(path: str) -> RedirectResponse:
    return RedirectResponse(path, status_code=303)


def _fail(exc: Exception) -> NoReturn:
    raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/", response_class=HTMLResponse)
def home(request: Request, session: SessionDep) -> HTMLResponse:
    return _html(request, "drafts.html", drafts=catalog.list_drafts(session))


@router.get("/shelf", response_class=HTMLResponse)
def shelf(request: Request, session: SessionDep) -> HTMLResponse:
    return _html(request, "shelf.html", products=catalog.list_ready(session))


@router.get("/cards", response_class=HTMLResponse)
def cards_page(request: Request, session: SessionDep) -> HTMLResponse:
    rows = [
        CardRow(card, card.account.balance_cents if card.account else 0)
        for card in cards.list_cards(session)
    ]
    return _html(request, "cards.html", cards=rows)


@router.get("/sales", response_class=HTMLResponse)
def sales_page(request: Request, session: SessionDep) -> HTMLResponse:
    return _html(request, "sales.html", sales=ledger.list_today(session))


@router.get("/doctor", response_class=HTMLResponse)
def doctor_page(request: Request) -> HTMLResponse:
    settings = _settings(request)
    db = Path(settings.database)
    journal = "n/a"
    engine = getattr(request.app.state, "engine", None)
    if engine is not None:
        with engine.connect() as conn:
            journal = str(conn.exec_driver_sql("PRAGMA journal_mode").scalar())
    backup_dir = Path("/var/backups/store")
    backup = "尚未"
    try:
        if backup_dir.is_dir():
            found = sorted(backup_dir.glob("store-*.db"))
            backup = found[-1].name if found else "尚未"
    except OSError:
        backup = "尚未"
    return _html(
        request,
        "doctor.html",
        database=settings.database,
        db_exists=db.exists() if settings.database not in {":memory:"} else False,
        journal=journal,
        images=settings.product_images or "(未設)",
        backup=backup,
    )


@router.post("/learn")
def learn(session: SessionDep, barcode: Annotated[str, Form()]) -> RedirectResponse:
    try:
        result = catalog.scan(session, barcode, learn=True)
    except StoreError as exc:
        _fail(exc)
    if result.action == "reject":
        raise HTTPException(status_code=400, detail="invalid barcode")
    return _see("/")


@router.post("/products/{barcode}/finish")
def finish(
    request: Request,
    barcode: str,
    session: SessionDep,
    name: Annotated[str, Form()],
    yuan: Annotated[str, Form()],
    photo: Annotated[UploadFile | None, File()] = None,
) -> RedirectResponse:
    try:
        cents = yuan_to_cents(int(yuan))
        product = catalog.finish(session, barcode, name=name, price_cents=cents)
        if photo is not None and photo.filename:
            data = photo.file.read()
            root = _settings(request).product_images.strip()
            if data and root:
                product.image_path = save_product_photo(Path(root), product.id, data)
                session.flush()
    except (StoreError, ValueError) as exc:
        _fail(exc)
    return _see("/")


@router.post("/products/{barcode}/drop")
def drop_draft(barcode: str, session: SessionDep) -> RedirectResponse:
    try:
        catalog.drop_draft(session, barcode)
    except StoreError as exc:
        _fail(exc)
    return _see("/")


@router.post("/products/{barcode}/deactivate")
def deactivate_product(barcode: str, session: SessionDep) -> RedirectResponse:
    try:
        catalog.deactivate(session, barcode)
    except StoreError as exc:
        _fail(exc)
    return _see("/shelf")


@router.get("/sheet.pdf")
def sheet(request: Request, session: SessionDep) -> FileResponse:
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp.close()
    path = Path(tmp.name)
    labels.print_sheet(
        session,
        path,
        labels.PAGE,
        prefix_min=_settings(request).store_prefix_min,
        prefix_max=_settings(request).store_prefix_max,
    )
    return FileResponse(path, media_type="application/pdf", filename="labels.pdf")


@router.post("/reprint.pdf")
def reprint(
    session: SessionDep,
    barcodes: Annotated[list[str] | None, Form()] = None,
) -> FileResponse:
    picked = barcodes or []
    if not picked:
        raise HTTPException(status_code=400, detail="pick barcodes")
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp.close()
    path = Path(tmp.name)
    try:
        labels.reprint(session, path, picked)
    except StoreError as exc:
        _fail(exc)
    return FileResponse(path, media_type="application/pdf", filename="reprint.pdf")


@router.post("/cards")
def enroll_card(
    session: SessionDep,
    uid: Annotated[str, Form()],
    name: Annotated[str, Form()],
    role: Annotated[str, Form()] = "child",
    yuan: Annotated[str, Form()] = "0",
) -> RedirectResponse:
    try:
        cards.enroll(
            session,
            uid,
            name,
            role=role,
            opening_cents=yuan_to_cents(int(yuan or "0")),
        )
    except (StoreError, ValueError) as exc:
        _fail(exc)
    return _see("/cards")


@router.post("/cards/{uid}/topup")
def topup_card(
    uid: str, session: SessionDep, yuan: Annotated[str, Form()]
) -> RedirectResponse:
    try:
        ledger.apply_ledger(session, uid, "topup", yuan_to_cents(int(yuan)))
    except (StoreError, ValueError) as exc:
        _fail(exc)
    return _see("/cards")


@router.post("/cards/{uid}/reset")
def reset_card(uid: str, session: SessionDep) -> RedirectResponse:
    try:
        ledger.apply_ledger(session, uid, "reset")
    except StoreError as exc:
        _fail(exc)
    return _see("/cards")


@router.post("/cards/{uid}/deactivate")
def deactivate_card(uid: str, session: SessionDep) -> RedirectResponse:
    try:
        cards.deactivate(session, uid)
    except StoreError as exc:
        _fail(exc)
    return _see("/cards")


@router.post("/void-last")
def void_last_sale(session: SessionDep) -> RedirectResponse:
    try:
        ledger.void_last(session)
    except StoreError as exc:
        _fail(exc)
    return _see("/sales")
