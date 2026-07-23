"""Set (or change) a user's login password.

Run once after setting up the app to give each person a password:
    python -m scripts.set_password "Chồng" matkhau_cua_chong
    python -m scripts.set_password "Vợ" matkhau_cua_vo

Point DATABASE_URL at the live database to set passwords on the deployed app.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.user import User  # noqa: E402


def run(name: str, password: str) -> None:
    with SessionLocal() as db:
        user = db.query(User).filter(User.name == name).one_or_none()
        if user is None:
            names = [u.name for u in db.query(User).all()]
            print(f"Khong tim thay nguoi ten '{name}'. Cac ten hien co: {names}")
            sys.exit(1)
        user.password_hash = hash_password(password)
        db.commit()
        print(f"Da dat mat khau cho '{name}'.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print('Cach dung: python -m scripts.set_password "<Ten>" <mat_khau>')
        sys.exit(1)
    run(sys.argv[1], sys.argv[2])
