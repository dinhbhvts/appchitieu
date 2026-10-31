"""User model.

In this first version there are exactly two fixed users (e.g. Chong / Vo).
Each transaction and stock record points back to the user who entered it, which
is how we produce per-person reports as well as combined totals.
"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, LargeBinary, String, func
from sqlalchemy.orm import Mapped, deferred, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    # Primary key: a unique auto-incrementing integer for every user.
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Display name shown in the app UI (e.g. "Chong", "Vo").
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    # Salted password hash for login. Nullable so a freshly-seeded user has no
    # password until one is set (via scripts/set_password.py). Never store the
    # raw password - only the hash produced by app.core.security.
    password_hash: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
        comment="Hash MỘT CHIỀU (PBKDF2, app.core.security) của mật khẩu "
                "đăng nhập app - không thể giải mã ngược, chỉ dùng để so "
                "khớp lúc đăng nhập. KHÁC với NotebookItem.password_encrypted "
                "(mã hóa 2 chiều, dùng cho mật khẩu tài khoản ngoài đã lưu).",
    )

    # -- Cấu hình > Người dùng: màu đại diện + avatar --
    # Màu nền nhạt đại diện cho người này (hex "#RRGGBB"), dùng tô các dòng
    # giao dịch / mục Tài sản của họ. Null = màu mặc định của app (Chồng
    # xanh nhạt #EAF2FE, Vợ hồng nhạt #FCEAF4) - frontend tự áp.
    color: Mapped[str | None] = mapped_column(
        String(9), nullable=True,
        comment="Màu đại diện (hex #RRGGBB, màu nền nhạt). Null = màu mặc "
                "định (Chồng #EAF2FE, Vợ #FCEAF4).",
    )
    # Avatar: null = chữ cái đầu tên; "chibi:N" = ảnh chibi gợi ý thứ N
    # (danh sách CHIBI_SVGS / bootChibiEmojis ở frontend); "upload" = ảnh
    # người dùng tải lên, lưu ở avatar_data.
    avatar_preset: Mapped[str | None] = mapped_column(
        String(30), nullable=True,
        comment="Avatar: null = chữ cái đầu tên; 'chibi:N' = chibi gợi ý thứ "
                "N; 'upload' = ảnh tải lên (avatar_data).",
    )
    # Ảnh avatar đã cắt vuông + thu nhỏ (JPEG <= 256px, vài chục KB) - lưu
    # thẳng trong DB giống album_photos. deferred: không tải khi đọc user.
    avatar_data: Mapped[bytes | None] = deferred(mapped_column(
        LargeBinary, nullable=True,
        comment="Ảnh avatar tải lên (JPEG vuông <= 256px) khi avatar_preset='upload'.",
    ))
    # Thời điểm đổi avatar gần nhất - frontend dùng làm "version" để tải lại ảnh.
    avatar_updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # When the row was created; the database fills this in automatically.
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    # Convenience back-references so we can do user.transactions in Python.
    # These do NOT create extra columns; they are virtual links.
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="user", foreign_keys="Transaction.user_id"
    )
