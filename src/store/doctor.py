"""Print Python, DB, and input devices. USB grab waits for the LIFEBOOK."""

from __future__ import annotations

import platform
import sys
from pathlib import Path

from store.config import get_settings
from store.persist.engine import make_engine

_BY_ID = Path("/dev/input/by-id")


def run() -> None:
    settings = get_settings()
    print(f"python   {sys.version.split()[0]} ({platform.system()})")
    print(f"store    {settings.store_name}")
    print(f"database {settings.database}")
    db = Path(settings.database)
    if settings.database not in {":memory:"}:
        print(f"exists   {db.exists()}")
    engine = make_engine(settings.database)
    with engine.connect() as conn:
        mode = conn.exec_driver_sql("PRAGMA journal_mode").scalar()
        print(f"journal  {mode}")
    engine.dispose()
    if _BY_ID.is_dir():
        try:
            names = sorted(p.name for p in _BY_ID.iterdir())
            print("by-id    " + (" ".join(names) if names else "(empty)"))
        except OSError:
            print("by-id    (unreadable)")
    else:
        print("by-id    (none — fill config/devices.example.toml on the LIFEBOOK)")
    print("phase    2 (console scan + A4 labels; grab() needs Linux + gun)")


if __name__ == "__main__":
    run()
