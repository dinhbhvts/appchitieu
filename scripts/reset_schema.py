"""Rebuild ALL tables to match the latest code, then seed defaults.

Use this after a structural change (new column / new table / new transaction
type) to bring an existing database up to date. It is the simplest, most
reliable way to apply schema changes for this app.

WARNING: this DELETES all rows (it drops and recreates the tables). That is
fine during setup because your real data lives in the Excel file and can be
re-imported with `scripts.import_excel` right afterwards.

Run (point DATABASE_URL at the database you want to rebuild):
    python -m scripts.reset_schema
    python -m scripts.import_excel --fresh
    python -m scripts.set_password "Chồng" <mat_khau>
    python -m scripts.set_password "Vợ" <mat_khau>
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app import models  # noqa: E402,F401  (registers all tables)
from app.core.seed import seed  # noqa: E402


def run() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed(db)
    print("Da tao lai toan bo bang theo cau truc moi nhat + seed mac dinh.")


if __name__ == "__main__":
    run()
