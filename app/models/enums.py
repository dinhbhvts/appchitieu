"""Shared enumerations used across models and schemas.

Using Python enums (instead of loose strings like "income"/"expense") means the
database, the API and the code all agree on the exact set of allowed values, so
a typo becomes an error instead of silently corrupt data.
"""

import enum


class TransactionType(str, enum.Enum):
    """What a transaction does to the shared fund.

    income/expense change the fund balance. transfer is an INTERNAL move of
    money between the two people (e.g. husband transfers part of his salary to
    the wife). A transfer does NOT change the household fund total; it only
    shifts money from one person to the other in the per-person reports.
    """

    income = "income"    # THU  - tien vao quy
    expense = "expense"  # CHI  - tien ra khoi quy
    transfer = "transfer"  # CHUYEN NOI BO - chong -> vo, khong doi so du quy


class CategoryKind(str, enum.Enum):
    """Which transaction types a category may be used for."""

    income = "income"
    expense = "expense"
    both = "both"


class CashFlowType(str, enum.Enum):
    """Money moving in/out of the brokerage account."""

    deposit = "deposit"    # NAP  - chuyen tien vao tai khoan chung khoan
    withdraw = "withdraw"  # RUT  - rut tien ra khoi tai khoan chung khoan


class TradeSide(str, enum.Enum):
    """Direction of a stock order."""

    buy = "buy"    # MUA
    sell = "sell"  # BAN


class SavingsTermUnit(str, enum.Enum):
    """Unit for a savings deposit's kỳ hạn (term)."""

    day = "day"      # NGAY
    month = "month"  # THANG


class SavingsStatus(str, enum.Enum):
    """Whether a savings deposit ("khoản gửi tiết kiệm") is still open."""

    active = "active"    # DANG GUI
    settled = "settled"  # DA TAT TOAN


# NOTE: NotebookItem's "type" used to be a fixed Python enum here. It is now
# a free string validated against the notebook_types table instead (see
# app/models/notebook_type.py), so the user can add their own custom types
# from Cấu hình > Danh mục tiện ích without a code change. The original 7
# built-in types plus "account" are seeded there (app/core/seed.py).
