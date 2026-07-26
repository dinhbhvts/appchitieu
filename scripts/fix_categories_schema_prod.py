"""One-off, SAFE fix for a production database that crashed on startup with:
    sqlalchemy.exc.ProgrammingError: column categories.icon does not exist

Root cause: the app creates brand-new tables automatically on startup
(Base.metadata.create_all), but it does NOT add new columns to a table that
already exists. "categories" already existed in production before the
Danh mục / Sổ tay upgrade, so the 5 new columns (icon, is_active, created_at,
updated_at, updated_by) never got added there - only new tables like
notebook_items were created automatically.

This script does the safe, non-destructive fix:
  1. Add the 5 missing columns to "categories" (idempotent - checks first,
     never touches existing rows/columns/data).
  2. Add the missing foreign key (updated_by -> users.id), if not already
     present.
  3. Mark Alembic's version table as being at the latest migration ("stamp"),
     WITHOUT re-running any CREATE TABLE statements - so it won't try to
     recreate tables that already exist (categories, notebook_items, etc).

Unlike scripts/reset_schema.py, this NEVER deletes or reloads data. Safe to
run more than once (every step checks before acting).

Run (from the backend folder, DATABASE_URL pointed at the PRODUCTION database):
    $env:DATABASE_URL="postgresql+psycopg://...prod-connection-string..."
    python -m scripts.fix_categories_schema_prod
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import inspect, text  # noqa: E402

from app.core.database import engine  # noqa: E402

# (column_name, DDL type + default) - matches app/models/category.py exactly.
NEW_COLUMNS = [
    ("icon", "VARCHAR(8)"),
    ("is_active", "BOOLEAN NOT NULL DEFAULT TRUE"),
    ("created_at", "TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP"),
    ("updated_at", "TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP"),
    ("updated_by", "INTEGER"),
]


def add_missing_columns() -> None:
    inspector = inspect(engine)
    existing_cols = {c["name"] for c in inspector.get_columns("categories")}

    with engine.begin() as conn:
        for name, ddl_type in NEW_COLUMNS:
            if name in existing_cols:
                print(f"Cột '{name}' đã tồn tại - bỏ qua.")
                continue
            conn.execute(text(f"ALTER TABLE categories ADD COLUMN {name} {ddl_type}"))
            print(f"Đã thêm cột '{name}' vào bảng categories.")


def add_missing_foreign_key() -> None:
    inspector = inspect(engine)
    fks = inspector.get_foreign_keys("categories")
    has_fk = any(
        fk.get("constrained_columns") == ["updated_by"] for fk in fks
    )
    if has_fk:
        print("Ràng buộc khóa ngoại updated_by -> users.id đã tồn tại - bỏ qua.")
        return
    with engine.begin() as conn:
        conn.execute(text(
            "ALTER TABLE categories "
            "ADD CONSTRAINT fk_categories_updated_by_users "
            "FOREIGN KEY (updated_by) REFERENCES users(id)"
        ))
    print("Đã thêm ràng buộc khóa ngoại fk_categories_updated_by_users.")


def stamp_alembic_head() -> None:
    """Mark the DB as being at the latest migration, without running any
    CREATE TABLE (which would fail since those tables already exist)."""
    from alembic import command
    from alembic.config import Config

    backend_dir = Path(__file__).resolve().parents[1]
    cfg = Config(str(backend_dir / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    command.stamp(cfg, "head")
    print("Đã đánh dấu Alembic ở phiên bản mới nhất (head).")


def run() -> None:
    print("Bước 1/3: Thêm các cột còn thiếu vào bảng categories...")
    add_missing_columns()
    print("\nBước 2/3: Thêm ràng buộc khóa ngoại còn thiếu...")
    add_missing_foreign_key()
    print("\nBước 3/3: Đánh dấu Alembic đã ở bản mới nhất...")
    stamp_alembic_head()
    print("\nXong! Database production giờ đã khớp với code mới nhất. "
          "Không dữ liệu nào bị xóa hoặc thay đổi.")


if __name__ == "__main__":
    run()
