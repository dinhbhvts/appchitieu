"""Diagnostic: print every stock trade in a given month, grouped by owner.

Used to debug the "Lệnh mua/bán trong tháng" screen showing too many rows.
Prints the raw rows straight from the database (no client-side filtering),
so we can see exactly what's really stored - including any bad/duplicate
rows from the Excel import.

Run (from the backend folder, virtual environment active, DATABASE_URL set
to the real database in .env):
    python -m scripts.diag_stock_trades 2026 7
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal  # noqa: E402
from app.models.stock import StockTrade  # noqa: E402
from app.models.user import User  # noqa: E402


def run(year: int, month: int) -> None:
    with SessionLocal() as db:
        users = {u.id: u.name for u in db.query(User).all()}
        all_trades = db.query(StockTrade).order_by(StockTrade.date).all()

        print(f"Tong so dong trong bang stock_trades (moi thoi diem): {len(all_trades)}")
        print()

        in_month = [t for t in all_trades if t.date.year == year and t.date.month == month]
        print(f"So dong co ngay thuoc thang {month}/{year}: {len(in_month)}")
        for t in in_month:
            owner = users.get(t.user_id, f"user_id={t.user_id}")
            print(f"  id={t.id:<5} date={t.date} owner={owner:<8} "
                  f"{t.side.value:<4} {t.symbol:<8} qty={t.quantity:<6} "
                  f"price={t.price} fee={t.fee}")
        print()

        # Breakdown by owner, so we can compare against what each tab shows.
        for uid, name in users.items():
            count = sum(1 for t in in_month if t.user_id == uid)
            print(f"  -> {name}: {count} giao dich trong thang {month}/{year}")

        # Also show a few rows OUTSIDE this month per owner, to check whether
        # the date field itself looks correct (e.g. not all dumped onto one
        # date, not from the wrong year, etc).
        print()
        print("5 dong gan thang nay nhat (de doi chieu ngay thang co hop ly khong):")
        others = sorted(all_trades, key=lambda t: abs((t.date.year - year) * 12 + (t.date.month - month)))
        for t in others[:5]:
            owner = users.get(t.user_id, f"user_id={t.user_id}")
            print(f"  id={t.id:<5} date={t.date} owner={owner:<8} {t.side.value} {t.symbol}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Dung: python -m scripts.diag_stock_trades <nam> <thang>")
        print("Vi du: python -m scripts.diag_stock_trades 2026 7")
        sys.exit(1)
    run(int(sys.argv[1]), int(sys.argv[2]))
