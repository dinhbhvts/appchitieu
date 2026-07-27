"""Asset snapshot model - the monthly net-worth "CHOT THANG" block.

Each row is one asset line for one month, e.g. ("TK vo", 776,240,000) for
July 2026. All values are entered by hand and can be edited. The total net
worth of a month is simply the sum of that month's rows, and the month-by-month
trend is the sum grouped by (year, month).

We store year and month as plain integers (not a full date) because a snapshot
belongs to a whole month, not a specific day.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AssetSnapshot(Base):
    __tablename__ = "asset_snapshots"
    __table_args__ = (
        # The real access pattern is always "this year AND this month
        # together" (see asset_service.month()/history()) - the pre-existing
        # single-column indexes on year and month separately don't match that
        # as well as this composite does.
        Index("ix_asset_snapshots_year_month", "year", "month"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # The month this value belongs to. Stored as plain (year, month) integers
    # instead of a date, because a snapshot belongs to a WHOLE MONTH, not a
    # specific day - matches how the old "CHỐT THÁNG" block worked.
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    month: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # Asset label, e.g. "TK vo", "Vang 9999", "Chung khoan chong".
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Value in VND. Numeric(18, 0) keeps whole numbers with no float rounding.
    value: Mapped[float] = mapped_column(Numeric(18, 0), nullable=False)

    # NULL for a normal, freely-edited row. One of "vo_taikhoan",
    # "chong_taikhoan", "vo_ck", "chong_ck" for the 4 pinned, auto-computed
    # rows (see app/services/asset_service.py SYSTEM_ITEMS) - identifies them
    # reliably (not by name text, which the user could otherwise rename) so
    # the service can find/update the SAME row across page loads, pin them to
    # the top in a fixed order, and block manual edit/delete on them.
    system_key: Mapped[str | None] = mapped_column(
        String(30), nullable=True, index=True,
        comment="NULL = mục thường, người dùng tự nhập/sửa/xóa. Khác NULL = "
                "mục hệ thống (Tài khoản/Chứng khoán chồng/vợ), tự động tính "
                "toán mỗi lần xem, không cho sửa/xóa thủ công.",
    )

    # Optional note, e.g. "1 cay", "gui tiet kiem", "2 chi".
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="Xóa mềm: True = người dùng đã xóa từ UI. Hàng vẫn còn trong "
                "DB, chỉ bị ẩn khỏi mọi danh sách và tổng hợp.",
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
