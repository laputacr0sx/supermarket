"""Write an A4 shop-label PDF. Default mints a Rayfilm 0102 sheet (5x13)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from store.config import get_settings
from store.domain.errors import StoreError
from store.persist.engine import create_schema, make_engine, make_session_factory, session_scope
from store.services import catalog, labels


def run() -> None:
    parser = argparse.ArgumentParser(prog="store-labels")
    parser.add_argument("path", nargs="?", default="data/labels.pdf")
    parser.add_argument("--count", type=int, default=labels.PAGE)
    parser.add_argument(
        "--reprint",
        nargs="+",
        metavar="CODE",
        help="existing barcodes; does not mint",
    )
    args = parser.parse_args()
    if args.reprint is None and not 1 <= args.count <= labels.PAGE:
        parser.error(f"--count must be 1..{labels.PAGE}")
    settings = get_settings()
    engine = make_engine(settings.database)
    create_schema(engine)
    factory = make_session_factory(engine)
    path = Path(args.path)
    try:
        with session_scope(factory) as session:
            if args.reprint:
                codes = labels.resolve_codes(session, args.reprint)
            else:
                rows = catalog.mint_store_drafts(
                    session,
                    args.count,
                    prefix_min=settings.store_prefix_min,
                    prefix_max=settings.store_prefix_max,
                )
                codes = [row.barcode for row in rows]
        labels.render_sheet(path, codes)
    except StoreError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc
    print(f"{path} {len(codes)} codes")


if __name__ == "__main__":
    run()
