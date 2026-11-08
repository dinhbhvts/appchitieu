"""Kiểm tra nhanh tình trạng database (CHỈ ĐỌC - không sửa gì).

Chạy:
    python scripts/check_db.py                 # dùng DATABASE_URL trong backend/.env
    python scripts/check_db.py "<DATABASE_URL>"  # kiểm tra 1 địa chỉ khác (vd của Render)

In ra: máy chủ/database/tài khoản đang kết nối, search_path, các schema đang
có, số bảng + số dòng của vài bảng chính. Mật khẩu không bao giờ được in ra.
"""

import sys
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> None:
    if len(sys.argv) > 1:
        url = sys.argv[1].strip()
    else:
        from app.core.config import get_settings
        url = get_settings().database_url
    u = make_url(url)
    if u.drivername == "postgresql":
        u = u.set(drivername="postgresql+psycopg")
    print("Máy chủ   :", u.host)
    print("Database  :", u.database)
    print("Tài khoản :", u.username)
    print("Tham số   :", dict(u.query) or "(không có)")

    engine = create_engine(u)
    with engine.connect() as c:
        c.execute(text("SET TRANSACTION READ ONLY"))
        q = lambda sql: c.execute(text(sql)).fetchall()  # noqa: E731
        print("Phiên bản :", q("select version()")[0][0][:60])
        print("current_user / current_database:", q("select current_user, current_database()")[0])
        print("search_path      :", q("show search_path")[0][0])
        print("current_schema() :", q("select current_schema()")[0][0])
        print("Cấu hình riêng (role/db):", q(
            "select coalesce(r.rolname,'*'), coalesce(d.datname,'*'), s.setconfig "
            "from pg_db_role_setting s left join pg_roles r on r.oid=s.setrole "
            "left join pg_database d on d.oid=s.setdatabase") or "(không có)")
        schemas = [r[0] for r in q(
            "select nspname from pg_namespace where nspname not like 'pg_%' "
            "and nspname <> 'information_schema' order by 1")]
        print("Các schema đang có:", schemas)
        for s, n in q("select table_schema, count(*) from information_schema.tables "
                      "where table_schema not in ('pg_catalog','information_schema') "
                      "group by 1 order by 1"):
            print(f"  schema {s}: {n} bảng")
        if "public" in schemas:
            for t in ("alembic_version", "users", "transactions", "asset_snapshots",
                      "notebook_items", "savings_deposits"):
                try:
                    if t == "alembic_version":
                        v = q("select version_num from public.alembic_version")
                        print(f"  public.{t}: {[r[0] for r in v]}")
                    else:
                        n = q(f"select count(*) from public.{t}")[0][0]
                        print(f"  public.{t}: {n} dòng")
                except Exception as e:  # noqa: BLE001
                    c.rollback()
                    c.execute(text("SET TRANSACTION READ ONLY"))
                    print(f"  public.{t}: LỖI {str(e).splitlines()[0]}")
        else:
            print("!!! KHÔNG CÓ schema public - dữ liệu cũ không còn ở database này.")


if __name__ == "__main__":
    main()
