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
    # Tỉ suất lợi nhuận trung bình/năm (%) - bình quân theo GỐC x THỜI GIAN
    # GỬI (money-weighted annualized): Σ actual_interest / Σ (amount * số
    # ngày gửi thực tế / 365) * 100, tính trên các khoản tất toán trong năm
    # đang chọn. Không dùng "lãi / tổng gốc tất toán" đơn thuần vì cách đó bị
    # lệch khi các khoản có kỳ hạn (thời gian gửi) khác nhau - một khoản gửi
    # 3 tháng và một khoản gửi 12 tháng cùng lãi suất niêm yết sẽ cho ra lãi
    # tuyệt đối rất khác nhau, chia thẳng sẽ ra con số không phản ánh đúng
    # lãi suất %/năm thực tế. None khi năm đó chưa có khoản nào tất toán
    # (tránh chia 0).
    avg_return_rate_pct: float | None = None
    # Số dư ĐẦU NĂM đang chọn (tính tại thời điểm 01/01 năm đó): tổng gốc của
    # các khoản mở TRƯỚC năm đang chọn (start_date.year < year) và còn hiệu
    # lực (chưa tất toán) tính đến 01/01 năm đó - tức GỒM CẢ các khoản sau đó
    # bị tất toán ngay trong năm đang chọn (khác active_amount kiểu "còn
    # active tính đến HIỆN TẠI", vốn sẽ loại các khoản đã lỡ tất toán trong
    # năm). Nhờ vậy đối chiếu được: total_active_amount = opening_balance_
    # this_year + total_deposited_this_year - total_settled_amount_this_year
    # (số dư đầu năm + gửi thêm trong năm - tất toán trong năm = đang gửi
    # hiện tại). Dùng cho card "Thông tin gửi tiết kiệm" trên màn Báo cáo.
    opening_balance_this_year: float = 0
