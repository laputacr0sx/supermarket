from pathlib import Path

import pytest
from reportlab.lib.pagesizes import A4
from sqlalchemy.orm import Session

from store.domain.errors import InvalidBarcode, UnknownProduct
from store.persist import repo
from store.services import labels


def test_print_sheet_mints_drafts_and_embeds_codes(seeded: Session, tmp_path: Path) -> None:
    path = tmp_path / "sheet.pdf"
    codes = labels.print_sheet(seeded, path, count=3)
    assert len(codes) == 3
    assert len(set(codes)) == 3
    data = path.read_bytes()
    assert data.startswith(b"%PDF")
    for code in codes:
        product = repo.get_product_by_barcode(seeded, code)
        assert product is not None
        assert product.origin == "store"
        assert product.status == "draft"
        assert code.encode("ascii") in data


def test_reprint_does_not_mint(seeded: Session, tmp_path: Path) -> None:
    first = tmp_path / "a.pdf"
    codes = labels.print_sheet(seeded, first, count=2)
    before = repo.all_barcodes(seeded)
    labels.reprint(seeded, tmp_path / "b.pdf", codes)
    assert repo.all_barcodes(seeded) == before
    data = (tmp_path / "b.pdf").read_bytes()
    for code in codes:
        assert code.encode("ascii") in data


def test_reprint_rejects_unknown(seeded: Session, tmp_path: Path) -> None:
    with pytest.raises(UnknownProduct):
        labels.reprint(seeded, tmp_path / "x.pdf", ["0000000000000"])


def test_reprint_normalizes_spaces(seeded: Session, tmp_path: Path) -> None:
    codes = labels.print_sheet(seeded, tmp_path / "a.pdf", count=1)
    spaced = f" {codes[0][:6]} {codes[0][6:]} "
    labels.reprint(seeded, tmp_path / "b.pdf", [spaced])
    assert codes[0].encode("ascii") in (tmp_path / "b.pdf").read_bytes()


def test_print_sheet_rejects_bad_count(seeded: Session, tmp_path: Path) -> None:
    with pytest.raises(InvalidBarcode):
        labels.print_sheet(seeded, tmp_path / "x.pdf", count=0)
    with pytest.raises(InvalidBarcode):
        labels.print_sheet(seeded, tmp_path / "x.pdf", count=labels.PAGE + 1)


def test_sheet_geometry_is_rayfilm_0102() -> None:
    assert labels.COLS == 5
    assert labels.ROWS == 13
    assert labels.PAGE == 65
    page_w, page_h = A4
    x, y = labels.label_origin(0)
    assert x == pytest.approx(labels.LEFT)
    assert y + labels.LABEL_H == pytest.approx(page_h - labels.TOP)
    last_x, last_y = labels.label_origin(labels.PAGE - 1)
    assert last_x + labels.LABEL_W <= page_w
    assert last_y >= 0


def test_full_sheet_embeds_every_code(seeded: Session, tmp_path: Path) -> None:
    path = tmp_path / "full.pdf"
    codes = labels.print_sheet(seeded, path, count=labels.PAGE)
    assert len(codes) == labels.PAGE
    data = path.read_bytes()
    for code in codes:
        assert code.encode("ascii") in data
