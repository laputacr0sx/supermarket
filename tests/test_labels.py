from store.persist import repo
from store.services import labels


def test_print_sheet_mints_drafts_and_embeds_codes(seeded, tmp_path):
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


def test_reprint_does_not_mint(seeded, tmp_path):
    first = tmp_path / "a.pdf"
    codes = labels.print_sheet(seeded, first, count=2)
    before = repo.all_barcodes(seeded)
    labels.reprint(seeded, tmp_path / "b.pdf", codes)
    assert repo.all_barcodes(seeded) == before
    data = (tmp_path / "b.pdf").read_bytes()
    for code in codes:
        assert code.encode("ascii") in data


def test_reprint_rejects_unknown(seeded, tmp_path):
    import pytest

    from store.domain.errors import UnknownProduct

    with pytest.raises(UnknownProduct):
        labels.reprint(seeded, tmp_path / "x.pdf", ["0000000000000"])
