"""users.color / avatar_preset / avatar_data / avatar_updated_at

Revision ID: b5e2c7a9d4f1
Revises: a3d8f1c6e9b4
Create Date: 2026-10-31 10:00:00.000000

Cấu hình > Người dùng: màu đại diện + avatar (chibi gợi ý hoặc ảnh tải lên).
All new columns are nullable - null = mặc định (màu mặc định theo tên Chồng/
Vợ, avatar chữ cái đầu). Also refreshes the profile_name comment: the Drive
"Tên hồ sơ" now also applies to maintenance (Bảo trì) and warranty (Bảo hành)
and can be set once while editing if it was empty. No new notebook columns.

Written defensively (existence checks), same pattern as e6b2d8f4a1c9.
IMPORTANT: run this BEFORE (or together with) deploying the new backend -
the User model selects these columns, so login fails until they exist.
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'b5e2c7a9d4f1'
down_revision: str | None = 'a3d8f1c6e9b4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_NEW_COLUMNS = [
    ("color", lambda: sa.String(length=9),
     "Màu đại diện (hex #RRGGBB, màu nền nhạt). Null = màu mặc định (Chồng "
     "#EAF2FE, Vợ #FCEAF4)."),
    ("avatar_preset", lambda: sa.String(length=30),
     "Avatar: null = chữ cái đầu tên; 'chibi:N' = chibi gợi ý thứ N; "
     "'upload' = ảnh tải lên (avatar_data)."),
    ("avatar_data", lambda: sa.LargeBinary(),
     "Ảnh avatar tải lên (JPEG vuông <= 256px) khi avatar_preset='upload'."),
    ("avatar_updated_at", lambda: sa.DateTime(),
     "Thời điểm đổi avatar gần nhất (frontend dùng làm version để tải lại ảnh)."),
]

_PROFILE_NAME_COMMENT = (
    "Chỉ áp dụng cho type=personal_info, document, purchase, maintenance, "
    "warranty: 'Tên hồ sơ' (purchase: 'Hóa đơn mua hàng') - đặt 1 lần (lúc "
    "tạo, hoặc lúc sửa nếu đang trống), dùng làm tên thư mục con trên Google "
    "Drive để chứa file đính kèm của mục này. Không cho đổi sau khi đã đặt."
)


def _has_table(conn, table_name: str) -> bool:
    return sa.inspect(conn).has_table(table_name)


def _existing_columns(conn, table_name: str) -> set[str]:
    return {c["name"] for c in sa.inspect(conn).get_columns(table_name)}


def _comment(conn, table: str, column: str, comment: str) -> None:
    if conn.dialect.name != "postgresql":
        return
    if not _has_table(conn, table) or column not in _existing_columns(conn, table):
        return
    escaped = comment.replace("'", "''")
    op.execute(f'COMMENT ON COLUMN "{table}"."{column}" IS \'{escaped}\'')


def upgrade() -> None:
    conn = op.get_bind()
    if _has_table(conn, "users"):
        existing = _existing_columns(conn, "users")
        missing = [(n, t) for n, t, _ in _NEW_COLUMNS if n not in existing]
        if missing:
            with op.batch_alter_table("users") as batch_op:
                for name, type_factory in missing:
                    batch_op.add_column(sa.Column(name, type_factory(), nullable=True))
        for name, _, comment in _NEW_COLUMNS:
            _comment(conn, "users", name, comment)
    _comment(conn, "notebook_items", "profile_name", _PROFILE_NAME_COMMENT)


def downgrade() -> None:
    conn = op.get_bind()
    if _has_table(conn, "users"):
        existing = _existing_columns(conn, "users")
        drop = [n for n, _, _ in _NEW_COLUMNS if n in existing]
        if drop:
            with op.batch_alter_table("users") as batch_op:
                for name in drop:
                    batch_op.drop_column(name)
