"""One-off fix: rename the default users and categories to proper Vietnamese
(with diacritics) in an existing database.

Why this exists
---------------
Early versions seeded the users/categories without diacritics ("Chong",
"An uong"...). Those are app-provided display labels, so they should read with
diacritics ("Chồng", "Ăn uống"). This script updates the existing rows in place
- it does NOT touch any transaction you entered, and it keeps all your data
(transactions reference these rows by id, not by name).

How to run (from the backend folder, virtual environment active)
----------------------------------------------------------------
    python -m scripts.fix_diacritics

Then restart the server. Running it twice is harmless.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal  # noqa: E402
from app.models.category import Category  # noqa: E402
from app.models.user import User  # noqa: E402

# old (no diacritics) -> new (proper Vietnamese)
USER_RENAMES = {"Chong": "Chồng", "Vo": "Vợ"}
CATEGORY_RENAMES = {
    "Thu nhap": "Thu nhập",
    "An uong": "Ăn uống",
    "Di lai": "Đi lại",
    "Hoa don": "Hóa đơn",
    "Suc khoe": "Sức khỏe",
    "Mua sam": "Mua sắm",
    "Khac": "Khác",
}


def run() -> None:
    changed = 0
    with SessionLocal() as db:
        for user in db.query(User).all():
            if user.name in USER_RENAMES:
                user.name = USER_RENAMES[user.name]
                changed += 1
        for cat in db.query(Category).all():
            if cat.name in CATEGORY_RENAMES:
                cat.name = CATEGORY_RENAMES[cat.name]
                changed += 1
        db.commit()
    print(f"Da cap nhat {changed} ten (nguoi + danh muc) sang tieng Viet co dau.")


if __name__ == "__main__":
    run()
