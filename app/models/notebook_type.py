"""NotebookType model - the list of "loại" (kinds) a Sổ tay entry can be.

Mirrors Category exactly (see its docstring): a fixed set of built-in types
is seeded on first run (address, birthday, anniversary, service,
maintenance, note, child_milestone, account), and the user can add their own
custom types from Cấu hình > Danh mục tiện ích. Just like Category, a
NotebookType can never be deleted - only renamed or hidden (is_active =
False) - so a notebook_items row never points at a type that no longer
exists.

Custom (non-default) types always use the same short field set when adding
an entry: Tiêu đề (title), Tag (tags), Thông tin (info), Ghi chú (note). The
built-in types use whichever extra columns make sense for them (see
NotebookItem's docstring) - that mapping lives in the frontend, not here,
since it is purely a "which fields to show in the form" concern.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class NotebookType(Base):
    __tablename__ = "notebook_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Machine key stored in notebook_items.type (e.g. "address", "account").
    # Never changes after creation - notebook_items rows reference this.
    key: Mapped[str] = mapped_column(
        String(30), nullable=False, unique=True,
        comment="Mã định danh loại, dùng làm giá trị notebook_items.type. "
                "Không đổi sau khi tạo (đổi sẽ làm sai lệch các mục đã lưu).",
    )

    # Vietnamese display name, e.g. "Địa chỉ", "Tài khoản".
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    icon: Mapped[str | None] = mapped_column(String(8), nullable=True)

    # True for the 8 built-in types seeded on first run; False for types the
    # user added themselves via Cấu hình > Danh mục tiện ích.
    is_default: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="True = loại có sẵn trong app (8 loại gốc, seed lúc khởi tạo). "
                "False = do người dùng tự thêm.",
    )

    # False = hidden from the "thêm mục sổ tay" type picker, but existing
    # items of this type are kept and still display correctly (never delete
    # - same "no delete" philosophy as Category).
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False,
        comment="False = đã ẩn khỏi danh sách chọn loại khi thêm mới, "
                "nhưng KHÔNG xóa để các mục sổ tay cũ vẫn hiển thị đúng.",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
