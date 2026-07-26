"""notebook types (danh mục tiện ích) + account fields + column comments

Revision ID: e9bf8b627c97
Revises: a1c9f3d84e21
Create Date: 2026-07-26 10:25:24.697498

Written defensively (checks before every add/create) rather than from a
blind autogenerate diff: this project's migration chain has historically
lagged behind the ORM models (some tables/columns only ever got created via
Base.metadata.create_all on a fresh database, never through a migration -
see the "categories.icon does not exist" production incident this predates).
Guarding every operation means this migration is safe to run regardless of
exactly which of those older columns a given database already has.
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'e9bf8b627c97'
down_revision: str | None = 'a1c9f3d84e21'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# (key, name, icon) - must match app/core/seed.py DEFAULT_NOTEBOOK_TYPES.
_DEFAULT_NOTEBOOK_TYPES = [
    ("address", "Địa chỉ", "📍"),
    ("birthday", "Sinh nhật", "🎂"),
    ("anniversary", "Ngày giỗ", "🕯️"),
    ("service", "Dịch vụ", "🌐"),
    ("maintenance", "Bảo trì", "🔧"),
    ("account", "Tài khoản", "🔑"),
    ("note", "Ghi chú", "📝"),
    ("child_milestone", "Mốc của con", "👶"),
]


def _existing_columns(conn, table_name: str) -> set[str]:
    return {c["name"] for c in sa.inspect(conn).get_columns(table_name)}


def _has_table(conn, table_name: str) -> bool:
    return sa.inspect(conn).has_table(table_name)


def _comment_if_exists(conn, table: str, column: str, comment: str) -> None:
    """Set a column comment - Postgres only (production); SQLite has no
    COMMENT ON COLUMN, so this is a silent no-op there. Skips cleanly if the
    table/column doesn't exist yet on this particular database.

    COMMENT ON COLUMN is DDL, and Postgres does not allow bind parameters
    ($1) inside DDL statements (it isn't just a psycopg quirk - the same
    fails from psql itself). So the comment text - which is always one of
    our own fixed strings above, never user input - is escaped and inlined
    as a literal instead of being passed as a bound parameter.
    """
    if conn.dialect.name != "postgresql":
        return
    if not _has_table(conn, table) or column not in _existing_columns(conn, table):
        return
    escaped = comment.replace("'", "''")
    op.execute(f'COMMENT ON COLUMN "{table}"."{column}" IS \'{escaped}\'')


def upgrade() -> None:
    conn = op.get_bind()

    # --- notebook_types: brand new table (danh mục tiện ích) ---
    if not _has_table(conn, "notebook_types"):
        op.create_table(
            "notebook_types",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("key", sa.String(length=30), nullable=False,
                      comment="Mã định danh loại, dùng làm giá trị notebook_items.type. "
                              "Không đổi sau khi tạo (đổi sẽ làm sai lệch các mục đã lưu)."),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("icon", sa.String(length=8), nullable=True),
            sa.Column("is_default", sa.Boolean(), nullable=False,
                      comment="True = loại có sẵn trong app (8 loại gốc, seed lúc khởi tạo). "
                              "False = do người dùng tự thêm."),
            sa.Column("is_active", sa.Boolean(), nullable=False,
                      comment="False = đã ẩn khỏi danh sách chọn loại khi thêm mới, "
                              "nhưng KHÔNG xóa để các mục sổ tay cũ vẫn hiển thị đúng."),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("updated_by", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("key"),
        )

    # Seed the 8 built-in types (idempotent - only if the table is empty;
    # app/core/seed.py does the same seeding for a fresh create_all database,
    # this covers the "table just created by this migration" path too).
    if not conn.execute(sa.text("SELECT COUNT(*) FROM notebook_types")).scalar():
        notebook_types_tbl = sa.table(
            "notebook_types",
            sa.column("key", sa.String),
            sa.column("name", sa.String),
            sa.column("icon", sa.String),
            sa.column("is_default", sa.Boolean),
            sa.column("is_active", sa.Boolean),
        )
        op.bulk_insert(
            notebook_types_tbl,
            [
                {"key": k, "name": n, "icon": i, "is_default": True, "is_active": True}
                for k, n, i in _DEFAULT_NOTEBOOK_TYPES
            ],
        )

    # --- notebook_items: new columns + widen `type` ---
    ni_cols = _existing_columns(conn, "notebook_items")
    with op.batch_alter_table("notebook_items") as batch_op:
        if "system" not in ni_cols:
            batch_op.add_column(sa.Column("system", sa.String(length=150), nullable=True))
        if "username" not in ni_cols:
            batch_op.add_column(sa.Column("username", sa.String(length=150), nullable=True))
        if "password_encrypted" not in ni_cols:
            batch_op.add_column(sa.Column(
                "password_encrypted", sa.Text(), nullable=True,
                comment="Mật khẩu đã MÃ HÓA 2 CHIỀU (không phải hash) bằng app.core.crypto - "
                        "vì người dùng cần xem lại được. Không bao giờ trả nguyên giá trị cột "
                        "này qua API, luôn giải mã trước.",
            ))
        if "info" not in ni_cols:
            batch_op.add_column(sa.Column("info", sa.Text(), nullable=True))
        if "type" in ni_cols:
            batch_op.alter_column(
                "type", existing_type=sa.String(length=20), type_=sa.String(length=30),
                existing_nullable=False,
            )

    # FK notebook_items.type -> notebook_types.key, added separately so
    # notebook_types definitely exists (and is populated) by the time this
    # constraint is checked.
    existing_fks = {fk["name"] for fk in sa.inspect(conn).get_foreign_keys("notebook_items")}
    if "fk_notebook_items_type_notebook_types" not in existing_fks:
        with op.batch_alter_table("notebook_items") as batch_op:
            batch_op.create_foreign_key(
                "fk_notebook_items_type_notebook_types", "notebook_types",
                ["type"], ["key"],
            )

    # --- Column comments on pre-existing columns (Postgres only, metadata-only,
    # each guarded to skip cleanly if that column isn't there yet). ---
    _comment_if_exists(conn, "transactions", "date",
        "Ngày phát sinh giao dịch. Tháng/năm cho báo cáo được tính từ cột "
        "này, KHÔNG có bảng riêng theo tháng.")
    _comment_if_exists(conn, "transactions", "type",
        "income = thu (tăng quỹ), expense = chi (giảm quỹ), transfer = "
        "chuyển nội bộ chồng->vợ (KHÔNG đổi tổng quỹ, chỉ dịch chuyển giữa "
        "2 người trong báo cáo riêng).")
    _comment_if_exists(conn, "categories", "kind",
        "income = chỉ dùng cho giao dịch Thu, expense = chỉ dùng cho Chi, "
        "both = dùng được cho cả hai. Không đổi được sau khi đã có giao "
        "dịch dùng danh mục này (tránh sai lệch báo cáo cũ).")
    _comment_if_exists(conn, "categories", "is_default",
        "True = danh mục có sẵn (seed lúc khởi tạo). False = do người dùng "
        "tự thêm. Cả hai loại đều KHÔNG xóa được.")
    _comment_if_exists(conn, "categories", "is_active",
        "False = ẩn khỏi màn chọn danh mục khi nhập giao dịch mới, nhưng "
        "KHÔNG xóa - giao dịch cũ dùng danh mục này vẫn hiển thị đúng "
        "trong lịch sử/báo cáo.")
    _comment_if_exists(conn, "stock_cashflows", "type",
        "deposit = nạp tiền vào tài khoản chứng khoán, withdraw = rút "
        "tiền ra. Không liên quan Transaction.type.")
    _comment_if_exists(conn, "stock_trades", "side",
        "buy = lệnh mua, sell = lệnh bán. Vị thế đang nắm giữ theo mã "
        "(SymbolPosition) được TÍNH từ các dòng buy/sell này, không lưu "
        "trực tiếp.")
    _comment_if_exists(conn, "stock_holdings", "quantity",
        "Số lượng cổ phiếu đang nắm giữ - người dùng TỰ NHẬP TAY, không "
        "tự tính từ StockTrade (mã này có thể mua từ trước khi dùng app, "
        "hoặc muốn nhập giá trị chốt tay).")
    _comment_if_exists(conn, "stock_holdings", "value",
        "Giá trị hiện tại (VNĐ) của phần đang giữ - người dùng tự nhập "
        "tay theo giá thị trường, KHÔNG tự động cập nhật.")
    _comment_if_exists(conn, "stock_month_summaries", "cum_deposit",
        "Tổng đã nạp LŨY KẾ tính đến hết tháng này (không phải số nạp "
        "riêng trong tháng) - lấy từ dữ liệu Excel gốc hoặc nối tiếp từ "
        "snapshot gần nhất.")
    _comment_if_exists(conn, "stock_month_summaries", "cum_withdraw",
        "Tổng đã rút LŨY KẾ tính đến hết tháng này (không phải số rút "
        "riêng trong tháng).")
    _comment_if_exists(conn, "asset_snapshots", "year",
        "Năm của snapshot (chốt theo THÁNG, không phải theo ngày cụ thể).")
    _comment_if_exists(conn, "asset_snapshots", "month",
        "Tháng của snapshot - snapshot thuộc về CẢ THÁNG, không phải một "
        "ngày cụ thể, giống khối CHỐT THÁNG trong file Excel gốc.")
    _comment_if_exists(conn, "users", "password_hash",
        "Hash MỘT CHIỀU (PBKDF2, app.core.security) của mật khẩu đăng "
        "nhập app - không thể giải mã ngược, chỉ dùng để so khớp lúc "
        "đăng nhập. KHÁC với NotebookItem.password_encrypted (mã hóa 2 "
        "chiều, dùng cho mật khẩu tài khoản ngoài đã lưu).")
    _comment_if_exists(conn, "notebook_items", "date1",
        "Ngày chính, ý nghĩa tùy loại: birthday=ngày sinh, "
        "anniversary=ngày mất, service=ngày bắt đầu/lắp đặt, "
        "maintenance=lần bảo trì gần nhất, child_milestone=ngày mốc.")
    _comment_if_exists(conn, "notebook_items", "date2",
        "Ngày phụ, chỉ dùng cho service/maintenance: ngày hết hạn hoặc "
        "đến hạn kế tiếp (dùng để nhắc nhở sắp đến hạn).")
    _comment_if_exists(conn, "notebook_items", "type",
        "Loại mục sổ tay, tham chiếu notebook_types.key. Quyết định "
        "những trường nào có ý nghĩa cho dòng này.")


def downgrade() -> None:
    conn = op.get_bind()
    ni_cols = _existing_columns(conn, "notebook_items")
    existing_fks = {fk["name"] for fk in sa.inspect(conn).get_foreign_keys("notebook_items")}

    with op.batch_alter_table("notebook_items") as batch_op:
        if "fk_notebook_items_type_notebook_types" in existing_fks:
            batch_op.drop_constraint("fk_notebook_items_type_notebook_types", type_="foreignkey")
        if "type" in ni_cols:
            batch_op.alter_column(
                "type", existing_type=sa.String(length=30), type_=sa.String(length=20),
                existing_nullable=False,
            )
        for col in ("info", "password_encrypted", "username", "system"):
            if col in ni_cols:
                batch_op.drop_column(col)

    if _has_table(conn, "notebook_types"):
        op.drop_table("notebook_types")
