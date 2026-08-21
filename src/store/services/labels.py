"""A4 shop labels. Mint is a catalog write; the PDF is a view of the numbers.

Geometry is Rayfilm 0102 (38.1 × 21.2 mm), the same die-cut as Avery L7651 /
Zweckform 3651: 5 × 13 = 65 stickers on A4. Print at 100%, do not fit-to-page.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.eanbc import Ean13BarcodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from sqlalchemy.orm import Session

from store.domain.errors import InvalidBarcode
from store.services import catalog

# Rayfilm 0102 / Avery L7651
LABEL_W = 38.1 * mm
LABEL_H = 21.2 * mm
COLS = 5
ROWS = 13
PAGE = COLS * ROWS
LEFT = 4.7 * mm
TOP = 10.7 * mm
DX = 40.6 * mm
DY = 21.2 * mm
BAR_H = 14.5 * mm
BAR_X = 0.33 * mm
DIGIT_SIZE = 6.0


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


def label_origin(index_on_page: int) -> tuple[float, float]:
    """Bottom-left of a sticker, PDF points. `index_on_page` is 0..PAGE-1."""
    col = index_on_page % COLS
    row = index_on_page // COLS
    _, page_h = A4
    x = LEFT + col * DX
    y = page_h - TOP - (row + 1) * DY
    return x, y


def render_sheet(path: Path | str, barcodes: list[str]) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    c = Canvas(str(out), pagesize=A4, pageCompression=0)
    c.setTitle("士多 labels · Rayfilm 0102")
    c.setKeywords(" ".join(barcodes))
    for i, code in enumerate(barcodes):
        if i and i % PAGE == 0:
            c.showPage()
        x, y = label_origin(i % PAGE)
        _cell(c, x, y, code)
    c.save()


def _cell(c: Canvas, x: float, y: float, code: str) -> None:
    c.saveState()
    if len(code) == 13 and code.isdigit():
        widget = Ean13BarcodeWidget(
            code, barHeight=BAR_H, barWidth=BAR_X, humanReadable=0, quiet=1
        )
        bw = float(widget.width)
        bh = float(widget.barHeight)
        drawing = Drawing(bw, bh)
        drawing.add(widget)
        bx = x + (LABEL_W - bw) / 2
        by = y + 4.2 * mm
        renderPDF.draw(drawing, c, bx, by)
    c.setFont("Courier", DIGIT_SIZE)
    c.drawCentredString(x + LABEL_W / 2, y + 1.3 * mm, code)
    c.restoreState()
