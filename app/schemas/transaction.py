"""Pydantic schemas for Transaction, including the list-with-balance response."""

from datetime import date as date_type

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import TransactionType


class TransactionBase(BaseModel):
    # The "..." marks a field as required; Field(gt=0) enforces amount > 0.
    date: date_type
    type: TransactionType
    amount: float = Field(..., gt=0, description="So tien, phai lon hon 0")
    content: str
    user_id: int
    category_id: int | None = None
    note: str | None = None


class TransactionCreate(TransactionBase):
    """Payload to create a transaction. Defaults (today, current user, last
    category) are filled in by the app UI before sending, per the style guide's
    'under 10 seconds to enter' rule."""


class TransactionUpdate(BaseModel):
    """All fields optional so the client can send only what changed."""

    date: date_type | None = None
    type: TransactionType | None = None
    amount: float | None = Field(default=None, gt=0)
    content: str | None = None
    user_id: int | None = None
    category_id: int | None = None
    note: str | None = None


class TransactionRead(TransactionBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class TransactionWithBalance(TransactionRead):
    """A transaction plus the running balance after it.

    The old spreadsheet had a DU CUOI (closing balance) column that users
    updated by hand. Here the server computes it, so it can never be wrong.
    """

    running_balance: float
