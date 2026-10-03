#!/usr/bin/env python3
"""Seed demonstration / benchmark data. Labels data as demo — not NCMRWF operational archives."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps" / "api"))
sys.path.insert(0, str(ROOT / "packages" / "schemas"))
sys.path.insert(0, str(ROOT / "packages" / "shared"))

os.environ.setdefault("DATABASE_URL", os.environ.get("DATABASE_URL", "sqlite:///../../data/demo/aeris.db"))


def main() -> None:
    os.chdir(ROOT / "apps" / "api")
    from app.db import Base, SessionLocal, engine
    from app.pipeline import seed_universe

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        info = seed_universe(db)
        print("Seeded demonstration benchmark:", info)
    finally:
        db.close()


if __name__ == "__main__":
    main()
