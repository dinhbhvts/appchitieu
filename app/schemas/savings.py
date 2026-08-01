"""Pydantic schemas for savings deposits ("Gửi tiết kiệm")."""

from datetime import date as date_type

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import SavingsStatus, SavingsTermUnit


class SavingsDepositCreate(BaseModel):
    name: str
    content: str | None = None
    start_date: date_type
    amount: float = Field(..., gt=0)
    term_value: int = Field(..., gt=0)
    term_unit: SavingsTermUnit = SavingsTermUnit.month
    interest_rate: float = Field(..., ge=0)
    # Optional - if omitted, the service fills in a suggested simple-interest
    # value (see savings_service._compute_expected_interest).
    expected_interest: float | None = Field(default=None, ge=0)
    bank: str | None = None
    status: SavingsStatus = SavingsStatus.active
    actual_interest: float | None = Field(default=None, ge=0)
    settled_date: date_type | None = None
    user_id: int
    note: str | None = None

    @model_validator(mode="after")
    def _settled_requires_date(self) -> "SavingsDepositCreate":
        if self.status == SavingsStatus.settled and self.settled_date is None:
            raise ValueError("Đã tất toán thì cần nhập thời gian tất toán")
        return self


class SavingsDepositUpdate(BaseModel):
    """Edit a deposit. All fields optional (partial update). maturity_date is
    never accepted here - it is always re-derived server-side from
    start_date/term_value/term_unit."""

    name: str | None = None
    content: str | None = None
    start_date: date_type | None = None
    amount: float | None = Field(default=None, gt=0)
    term_value: int | None = Field(default=None, gt=0)
    term_unit: SavingsTermUnit | None = None
    interest_rate: float | None = Field(default=None, ge=0)
    expected_interest: float | None = Field(default=None, ge=0)
    bank: str | None = None
    status: SavingsStatus | None = None
    actual_interest: float | None = Field(default=None, ge=0)
    settled_date: date_type | None = None
    user_id: int | None = None
    note: str | None = None


class SavingsDepositRead(BaseModel):
    id: int
    name: str
    content: str | None = None
    start_date: date_type
    amount: float
    term_value: int
    term_unit: SavingsTermUnit
    maturity_date: date_type
    interest_rate: float
    expected_interest: float
    bank: str | None = None
    status: SavingsStatus
    actual_interest: float | None = None
    settled_date: date_type | None = None
    user_id: int
    note: str | None = None

    model_config = ConfigDict(from_attributes=True)


class SavingsSummary(BaseModel):
    """Top-of-screen totals for the "Gửi tiết kiệm" tab, and the "Thông tin
    gửi tiết kiệm" card trên màn Báo cáo."""

    total_active_amount: float   # tổng số tiền đang gửi (không phụ thuộc bộ lọc ngày)
    active_count: int            # số khoản đang gửi
    interest_received_this_year: float  # tổng lãi thực nhận trong năm đang chọn
    # Tổng số tiền GỐC của các khoản đã tất toán trong năm đang chọn (theo
    # settled_date) - dùng cho card "Tổng hợp khoản đã tất toán" và card Báo
    # cáo. Không phải lãi - đây là số tiền gửi ban đầu được rút ra.
    total_settled_amount_this_year: float = 0
    # Tổng số tiền các khoản MỞ MỚI trong năm đang chọn (theo start_date),
    # bất kể đã tất toán hay còn đang gửi - "gửi thêm trong năm".
    total_deposited_this_year: float = 0
    # Tỉ suất lợi nhuận trung bình (%) = lãi đã nhận / tổng tất toán trong
    # năm * 100. None khi năm đó chưa có khoản nào tất toán (tránh chia 0).
    avg_return_rate_pct: float | None = None
