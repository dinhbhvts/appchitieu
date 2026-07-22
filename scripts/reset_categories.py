"""Replace the built-in default categories with the current list in seed.py.

Use this after the default income/expense categories change, to update an
existing database WITHOUT touching your transactions. Any category you created
yourself (is_default = False) is kept. Transactions that referenced a removed
default category simply lose that category (set to empty); their amount/date are
untouched.

Run (from the backend folder, virtual environment active):
    python -m scripts.reset_categories
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal  # noqa: E402
from app.core.seed import DEFAULT_CATEGORIES  # noqa: E402
from app.models.category import Category  # noqa: E402
from app.models.transaction import Transaction  # noqa: E402


def run() -> None:
    with SessionLocal() as db:
        # Ids of the current default categories we are about to remove.
        old = db.query(Category).filter(Category.is_default.is_(True)).all()
        old_ids = [c.id for c in old]

        # Detach any transactions pointing at those categories (keep the tx).
        if old_ids:
            (db.query(Transaction)
               .filter(Transaction.category_id.in_(old_ids))
               .update({Transaction.category_id: None},
                       synchronize_session=False))
            for c in old:
                db.delete(c)
            db.commit()

        # Insert the fresh default set (in seed order).
        for name, kind in DEFAULT_CATEGORIES:
            db.add(Category(name=name, kind=kind, is_default=True))
        db.commit()

    print(f"Da cap nhat danh muc: {len(DEFAULT_CATEGORIES)} danh muc moi.")


if __name__ == "__main__":
    run()
