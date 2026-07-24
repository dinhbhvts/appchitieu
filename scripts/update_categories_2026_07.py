"""One-off, safe update to an EXISTING database's category list (2026-07):
  - Rename "Học phí" -> "Giáo dục" (keeps the same row id, so every
    transaction that already points at it stays correctly categorised).
  - Add two new expense categories: "Dịch vụ", "Sửa chữa".

Unlike `reset_categories.py`, this script does NOT delete/replace all
default categories, so it never detaches existing transactions.  Safe to run
more than once (each step checks before acting).

Run (from the backend folder, virtual environment active, DATABASE_URL set
to the real database in .env):
    python -m scripts.update_categories_2026_07
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal  # noqa: E402
from app.models.category import Category  # noqa: E402
from app.models.enums import CategoryKind  # noqa: E402

NEW_EXPENSE_CATEGORIES = ["Dịch vụ", "Sửa chữa"]


def run() -> None:
    with SessionLocal() as db:
        # 1) Rename "Học phí" -> "Giáo dục" (only if "Giáo dục" doesn't
        #    already exist as a separate category, and "Học phí" is present).
        old = db.query(Category).filter(Category.name == "Học phí").first()
        already_new = db.query(Category).filter(Category.name == "Giáo dục").first()
        if old is not None and already_new is None:
            old.name = "Giáo dục"
            print("Đã đổi 'Học phí' -> 'Giáo dục' (giữ nguyên id, không ảnh hưởng giao dịch cũ).")
        elif old is not None and already_new is not None:
            print("Cả 'Học phí' và 'Giáo dục' đều tồn tại - bỏ qua đổi tên, kiểm tra thủ công.")
        else:
            print("Không tìm thấy 'Học phí' (có thể đã đổi tên trước đó) - bỏ qua.")

        # 2) Add the two new categories if missing.
        for name in NEW_EXPENSE_CATEGORIES:
            exists = db.query(Category).filter(Category.name == name).first()
            if exists is None:
                db.add(Category(name=name, kind=CategoryKind.expense, is_default=True))
                print(f"Đã thêm danh mục mới: {name}")
            else:
                print(f"Danh mục '{name}' đã tồn tại - bỏ qua.")

        db.commit()
    print("Xong.")


if __name__ == "__main__":
    run()
