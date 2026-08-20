"""Enroll a card UID. Role lives in SQLite, not on the chip."""

from __future__ import annotations

import argparse
import sys

from store.config import get_settings
from store.domain.errors import StoreError
from store.domain.money import yuan_to_cents
from store.persist.engine import create_schema, make_engine, make_session_factory, session_scope
from store.services import cards


def run() -> None:
    parser = argparse.ArgumentParser(prog="store-enroll")
    parser.add_argument("uid")
    parser.add_argument("name")
    parser.add_argument("--role", choices=("child", "staff"), default="child")
    parser.add_argument("--yuan", type=int, default=0)
    args = parser.parse_args()
    settings = get_settings()
    engine = make_engine(settings.database)
    create_schema(engine)
    factory = make_session_factory(engine)
    try:
        with session_scope(factory) as session:
            card = cards.enroll(
                session,
                args.uid,
                args.name,
                role=args.role,
                opening_cents=yuan_to_cents(args.yuan),
            )
            print(f"{card.uid} {card.role} {card.child_name}")
    except (StoreError, ValueError) as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    run()
