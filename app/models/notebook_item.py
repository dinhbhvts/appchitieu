"""NotebookItem model - the "Sổ tay gia đình" (family notebook).

One flexible table backs every lookup-info screen (addresses, birthdays,
death anniversaries, long-running services, maintenance schedules, saved
account logins, free notes, a child's milestones, and any custom type the
user adds) instead of a separate table per kind. Each row is tagged with
`type` (a key from notebook_types - see that model) and only fills in the
columns that make sense for that type; the rest stay null. This keeps the
architecture simple and lets a brand-new kind be added later - either a
built-in one (edit the seed list) or a user-added custom one (via Cấu hình >
Danh mục tiện ích, no code change needed at all) - without a new
table/migration/API.

Which columns a given `type` actually uses (for the ADD/EDIT form):
  - address:          title, relation, phone, address
  - birthday:          title, relation, date1
  - anniversary:        title, relation, date1 (+ date1_is_lunar),
  - service:            title, date1, date2, recurrence_days, amount
  - maintenance:        title, date1, date2, recurrence_days
  - child_milestone:    title, date1
  - account:            title, system, relation (as "Người dùng"), username,
                         password_encrypted
  - personal_info:      title (Tên thường gọi), full_name, date1 (Ngày sinh)
                         + remind_birthday, phone, id_number, id_issued_date,
                         id_issued_place, date2 (Ngày hết hạn CCCD),
                         birth_cert_no, health_insurance_no,
                         address (Địa chỉ thường trú), hometown,
                         profile_name (Tên hồ sơ - chỉ đặt lúc tạo) - plus
                         file attachments (NotebookAttachment), tự động lưu
                         vào thư mục riêng trên Drive (drive_folder_id) nếu
                         có profile_name
  - task:                title, info (Công việc), date2 (Ngày cần hoàn
                         thành - drives the Tổng quan reminder)
  - note / any custom
    type the user adds:  title, tags, info, note
This mapping is a UI concern (which fields to show), not enforced here.
"""

from datetime import date as date_type
from datetime import datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class NotebookItem(Base):
    __tablename__ = "notebook_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Which kind of notebook entry this is - a key from notebook_types
    # (e.g. "address", "account", or a custom type the user added).
    type: Mapped[str] = mapped_column(
        String(30), ForeignKey("notebook_types.key"), nullable=False, index=True,
        comment="Loại mục sổ tay, tham chiếu notebook_types.key. Quyết định "
                "những trường nào có ý nghĩa cho dòng này (xem docstring model).",
    )

    # Main label shown in the list, e.g. "Bố", "Internet VNPT", "Xe Vision",
    # "Wifi nhà".
    title: Mapped[str] = mapped_column(String(255), nullable=False)

    # "Quan hệ" - relationship to the family (Bố, Mẹ, Ông nội...) for
    # address/birthday/anniversary; reused as "Người dùng" (whose account it
    # is: chồng, vợ, con, bố vợ...) for type=account.
    relation: Mapped[str | None] = mapped_column(String(80), nullable=True)

    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Primary date: birth date, death date, service start date, last
    # maintenance date, milestone date - meaning depends on `type`.
    date1: Mapped[date_type | None] = mapped_column(
        Date, nullable=True,
        comment="Ngày chính, ý nghĩa tùy loại: birthday=ngày sinh, "
                "anniversary=ngày mất, service=ngày bắt đầu/lắp đặt, "
                "maintenance=lần bảo trì gần nhất, child_milestone=ngày mốc.",
    )
    # True when date1 is a LUNAR calendar date (âm lịch) - death anniversaries
    # in Vietnam are tracked by the lunar calendar. The /lunar utility converts
    # it to the correct solar date each year (for reminders).
    date1_is_lunar: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Secondary date: expiry date / next-due date (service, maintenance).
    date2: Mapped[date_type | None] = mapped_column(
        Date, nullable=True,
        comment="Ngày phụ, chỉ dùng cho service/maintenance: ngày hết hạn "
                "hoặc đến hạn kế tiếp (dùng để nhắc nhở sắp đến hạn).",
    )

    # How often this repeats, in days (e.g. 180 for "6 tháng"), for the
    # upcoming-reminders calculation. Null = one-off / no fixed cycle.
    recurrence_days: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Optional money amount (service price, loan amount...).
    amount: Mapped[float | None] = mapped_column(Numeric(18, 0), nullable=True)

    # -- type=account fields (Tài khoản: lưu thông tin đăng nhập) --
    # "Hệ thống" - which website/app/service this login is for.
    system: Mapped[str | None] = mapped_column(String(150), nullable=True)
    username: Mapped[str | None] = mapped_column(String(150), nullable=True)
    # Encrypted (reversible, NOT hashed) - the app needs to show the real
    # password again later. See app/core/crypto.py. Never expose this raw
    # column value to the API; always encrypt/decrypt through that module.
    password_encrypted: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Mật khẩu đã MÃ HÓA 2 CHIỀU (không phải hash) bằng "
                "app.core.crypto - vì người dùng cần xem lại được. Không bao "
                "giờ trả nguyên giá trị cột này qua API, luôn giải mã trước.",
    )

    # -- type=personal_info fields (Thông tin cá nhân: CCCD, BHYT, ...) --
    # "Họ tên" (legal full name) - distinct from `title` ("Tên thường gọi").
    full_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    # "Số CCCD" (citizen ID number).
    id_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    id_issued_date: Mapped[date_type | None] = mapped_column(Date, nullable=True)
    # "Nơi cấp" CCCD.
    id_issued_place: Mapped[str | None] = mapped_column(String(150), nullable=True)
    # "Số giấy khai sinh".
    birth_cert_no: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # "Số thẻ BHYT" (health insurance card number).
    health_insurance_no: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # "Quê quán" (ancestral hometown - distinct from `address`, which is used
    # here as "Địa chỉ thường trú").
    hometown: Mapped[str | None] = mapped_column(String(150), nullable=True)
    # Whether date1 (Ngày sinh) for this personal_info row should also show
    # up in the Dashboard's upcoming-reminders list, the same way a
    # dedicated type=birthday row does. Defaults to True (checked); the user
    # unticks it if they already keep this person's birthday as a separate
    # type=birthday entry, to avoid a duplicate reminder. Ignored for every
    # other type - only meaningful when type=personal_info.
    remind_birthday: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False,
        comment="Chỉ áp dụng cho type=personal_info: True = Ngày sinh của "
                "mục này cũng hiện trong danh sách nhắc nhở ở Tổng quan, "
                "giống type=birthday. Mặc định True - bỏ tích nếu đã có "
                "bản ghi 'Sinh nhật' riêng cho người này để tránh nhắc trùng.",
    )

    # -- custom (non-default) type fields --
    # "Thông tin" - generic free-text content field for custom notebook
    # types (distinct from `note`, which is for supplementary remarks). Also
    # reused as "Công việc" for type=task.
    info: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Simple free-text tags, space or comma separated (e.g. "#xe #gia_dinh").
    # Deliberately not a separate tags table - a personal notebook for two
    # people does not need that much structure.
    tags: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Free-text content: general notes, or extra detail for any type.
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # -- type=personal_info attachment-folder fields --
    # "Tên hồ sơ" - set once at creation, used as the name of this person's
    # own subfolder in Google Drive. Locked after creation (not in
    # NotebookItemUpdate) so it can never drift out of sync with the actual
    # Drive folder name - see app/services/notebook_item_service.py.
    profile_name: Mapped[str | None] = mapped_column(
        String(150), nullable=True,
        comment="Chỉ áp dụng cho type=personal_info: 'Tên hồ sơ' - đặt 1 lần "
                "lúc tạo, dùng làm tên thư mục con trên Google Drive để chứa "
                "file đính kèm của người này. Không cho đổi sau khi tạo "
                "(tránh lệch tên thư mục đã tạo trên Drive).",
    )
    # Google Drive folder id of that subfolder, created automatically the
    # first time this row is saved with a profile_name (see
    # notebook_item_service.create_item). Null if Drive wasn't configured at
    # creation time, or profile_name wasn't given - attachments then fall
    # back to the shared root folder, same as before this feature existed.
    drive_folder_id: Mapped[str | None] = mapped_column(String(120), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    # -- soft delete (see app-wide convention in app/models/soft_delete.md
    # docstring below / the migration comment) --
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="Xóa mềm: True = người dùng đã xóa từ UI. Hàng vẫn còn "
                "trong DB (không mất dữ liệu), chỉ bị ẩn khỏi mọi danh sách "
                "và tổng hợp. Không có chức năng khôi phục qua UI hiện tại.",
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    @property
    def password(self) -> str | None:
        """Decrypted password, for API responses (NotebookItemRead reads
        this via from_attributes). Read-only on purpose - writing a new
        password goes through the service layer, which encrypts it into
        password_encrypted instead (see notebook_item_service._prepare_data)."""
        from app.core.crypto import decrypt_text

        return decrypt_text(self.password_encrypted)
