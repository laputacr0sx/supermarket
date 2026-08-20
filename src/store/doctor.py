"""Phase 1 doctor: no USB. Prints Python, DB path, and a ping."""

from __future__ import annotations

import platform
import sys
from pathlib import Path

from store.config import get_settings
from store.persist.engine import make_engine


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
    print("phase    1 (Windows-safe; hardware checks wait for the LIFEBOOK)")


if __name__ == "__main__":
    run()
