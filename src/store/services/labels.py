"""A4 shop labels. Mint is a catalog write; the PDF is a view of the numbers."""

from __future__ import annotations

from pathlib import Path

from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.eanbc import Ean13BarcodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas
from sqlalchemy.orm import Session

from store.domain.errors import InvalidBarcode
from store.services import catalog

COLS = 3
ROWS = 8
PAGE = COLS * ROWS


def print_sheet(
    session: Session,
    path: Path | str,
    count: int = PAGE,
    *,
    prefix_min: int = 200,
    prefix_max: int = 299,
) -> list[str]:
    if count < 1 or count > PAGE:
        raise InvalidBarcode("count")
    rows = catalog.mint_store_drafts(
        session, count, prefix_min=prefix_min, prefix_max=prefix_max
    )
    codes = [row.barcode for row in rows]
    render_sheet(path, codes)
    return codes


def resolve_codes(session: Session, barcodes: list[str]) -> list[str]:
    codes: list[str] = []
    for raw in barcodes:
        product = catalog.lookup(session, raw)
        codes.append(product.barcode)
    return codes


def reprint(session: Session, path: Path | str, barcodes: list[str]) -> None:
    render_sheet(path, resolve_codes(session, barcodes))


def render_sheet(path: Path | str, barcodes: list[str]) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    c = Canvas(str(out), pagesize=A4, pageCompression=0)
    c.setKeywords(" ".join(barcodes))
    page_w, page_h = A4
    cell_w = page_w / COLS
    cell_h = page_h / ROWS
    for i, code in enumerate(barcodes):
        if i and i % PAGE == 0:
            c.showPage()
        col = i % COLS
        row = (i % PAGE) // COLS
        x = col * cell_w
        y = page_h - (row + 1) * cell_h
        _cell(c, x, y, cell_w, cell_h, code)
    c.save()


def _cell(c: Canvas, x: float, y: float, w: float, h: float, code: str) -> None:
    c.saveState()
    c.setDash(2, 2)
    c.rect(x + 4, y + 4, w - 8, h - 8)
    c.setDash()
    if len(code) == 13 and code.isdigit():
        widget = Ean13BarcodeWidget(
            code, barHeight=52, barWidth=1.1, humanReadable=0, quiet=1
        )
        drawing = Drawing(w - 16, 64)
        drawing.add(widget)
        renderPDF.draw(drawing, c, x + 12, y + h - 78)
    c.setFont("Courier", 9)
    c.drawCentredString(x + w / 2, y + 22, code)
    c.setStrokeColorRGB(0.6, 0.6, 0.6)
    c.line(x + 16, y + 14, x + w - 16, y + 14)
    c.restoreState()
