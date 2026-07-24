"""Backup the production database to a portable, restorable file.

Uses `pg_dump -Fc` (Postgres "custom" format): a single compressed file that
`pg_restore` can load into ANY Postgres server (Neon, Supabase, Render
Postgres, RDS, a local install, ...). This is intentionally NOT tied to Neon's
own backup/branching features -- if Neon disappears, this file is still
enough to rebuild the database elsewhere.

Usage (from the backend/ directory, with DATABASE_URL set in .env or the
environment):

    python -m scripts.backup_db

Requires the `pg_dump` command-line tool to be installed and on PATH.
  - Windows: install "PostgreSQL" (the installer includes command-line tools)
    or just the standalone "psql"/client tools, and add its bin/ folder to PATH.
  - Linux/Cowork sandbox: `apt-get install -y postgresql-client`.

Old backups beyond KEEP_LAST are deleted automatically so the folder does not
grow forever.
"""

import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Where backups are written. VibeApp/backups, next to the backend/ and
# frontend/ folders, so the user can find them easily and they are NOT part
# of any git repo (nothing here gets committed).
BACKUP_DIR = Path(__file__).resolve().parents[2] / "backups"
KEEP_LAST = 8  # keep the 8 most recent backups (~2 months at weekly cadence)


def _database_url() -> str:
    """Read DATABASE_URL the same way the app does (backend/.env or env var)."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from app.core.config import get_settings  # local import: needs the path above

    url = get_settings().database_url
    if url.startswith("sqlite"):
        raise SystemExit(
            "DATABASE_URL is not set (or points at local SQLite). "
            "Put the real Neon connection string in backend/.env before "
            "running a backup."
        )
    # pg_dump doesn't understand SQLAlchemy's "+psycopg" driver suffix -
    # strip it down to a plain postgresql:// URL.
    return re.sub(r"^postgresql\+\w+://", "postgresql://", url)


def _prune_old_backups() -> None:
    files = sorted(BACKUP_DIR.glob("vibeapp_*.dump"), key=lambda p: p.name)
    for old in files[:-KEEP_LAST]:
        old.unlink()
        print(f"  Xóa bản cũ: {old.name}")


def main() -> None:
    BACKUP_DIR.mkdir(exist_ok=True)
    url = _database_url()

    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    out_file = BACKUP_DIR / f"vibeapp_{stamp}.dump"

    print(f"Đang backup DB vào {out_file} ...")
    result = subprocess.run(
        ["pg_dump", "-Fc", "-f", str(out_file), url],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        out_file.unlink(missing_ok=True)
        raise SystemExit(f"pg_dump lỗi:\n{result.stderr}")

    size_kb = out_file.stat().st_size / 1024
    print(f"Backup xong: {out_file.name} ({size_kb:.0f} KB)")

    _prune_old_backups()
    remaining = sorted(BACKUP_DIR.glob("vibeapp_*.dump"))
    print(f"Hiện có {len(remaining)} bản backup trong {BACKUP_DIR}")


if __name__ == "__main__":
    main()
