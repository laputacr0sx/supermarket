"""Write an A4 shop-label PDF. Default mints a 3x8 sheet of drafts."""

from __future__ import annotations

import argparse
from pathlib import Path

from store.config import get_settings
from store.persist.engine import create_schema, make_engine, make_session_factory, session_scope
from store.services import labels


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
    settings = get_settings()
    engine = make_engine(settings.database)
    create_schema(engine)
    factory = make_session_factory(engine)
    path = Path(args.path)
    with session_scope(factory) as session:
        if args.reprint:
            labels.reprint(session, path, args.reprint)
            codes = args.reprint
        else:
            codes = labels.print_sheet(session, path, args.count)
    print(f"{path} {len(codes)} codes")


if __name__ == "__main__":
    run()
