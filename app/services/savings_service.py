"""Business logic for savings deposits ("Gửi tiết kiệm").

maturity_date is always DERIVED (never accepted as raw input - see the
schema) from (start_date, term_value, term_unit), so it can never drift out
of sync with the term. expected_interest is a simple-interest SUGGESTION the
user can override; it is only auto-(re)computed when the request doesn't
explicitly set it, so an edit to an unrelated field (e.g. note) never
clobbers a value the user already customised.
"""

from datetime import date as date_type
from datetime import timedelta

from sqlalchemy.orm import Session

from app.models.enums import SavingsStatus, SavingsTermUnit
from app.models.savings import SavingsDeposit
from app.repositories import savings_repository as repo
from app.schemas.savings import SavingsDepositCreate, SavingsDepositUpdate, SavingsSummary

# Financial inputs that, when changed, make an existing expected_interest
# suggestion stale - see update_deposit().
_INTEREST_INPUT_FIELDS = {"amount", "interest_rate", "start_date", "term_value", "term_unit"}


def _add_months(d: date_type, months: int) -> date_type:
    """d + `months` calendar months, clamping the day to the target month's
    last day (e.g. 31/1 + 1 tháng -> 28/2, not an invalid 31/2)."""
    import calendar

    total = d.month - 1 + months
    year = d.year + total // 12
    month = total % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    return date_type(year, month, min(d.day, last_day))


def _compute_maturity_date(
    start_date: date_type, term_value: int, term_unit: SavingsTermUnit
) -> date_type:
    if term_unit == SavingsTermUnit.day:
        return start_date + timedelta(days=term_value)
    return _add_months(start_date, term_value)


def _compute_expected_interest(
    amount: float, interest_rate: float, start_date: date_type, maturity_date: date_type
) -> float:
    """Simple interest (lãi đơn), the standard Vietnamese bank convention:
    amount * rate%/năm * (số ngày gửi thực tế / 365). The user can always
    override the stored value if their bank quotes something slightly
    different (rounding, actual/360, etc.)."""
    days = (maturity_date - start_date).days
    return round(amount * (interest_rate / 100) * (days / 365), 0)


def get(db: Session, deposit_id: int) -> SavingsDeposit | None:
    return repo.get(db, deposit_id)


def list_between(
    db: Session, start: date_type | None = None, end: date_type | None = None,
    user_id: int | None = None,
) -> list[SavingsDeposit]:
    return repo.list_between(db, start=start, end=end, user_id=user_id)


def list_unsettled(db: Session, user_id: int | None = None) -> list[SavingsDeposit]:
    return repo.list_unsettled(db, user_id=user_id)


def create_deposit(
    db: Session, payload: SavingsDepositCreate, actor_id: int | None = None
) -> SavingsDeposit:
    data = payload.model_dump()
    maturity_date = _compute_maturity_date(
        data["start_date"], data["term_value"], data["term_unit"]
    )
    data["maturity_date"] = maturity_date
    if data.get("expected_interest") is None:
        data["expected_interest"] = _compute_expected_interest(
            data["amount"], data["interest_rate"], data["start_date"], maturity_date,
        )
    data["updated_by"] = actor_id
    return repo.create(db, data)


def update_deposit(
    db: Session, deposit_id: int, payload: SavingsDepositUpdate,
    actor_id: int | None = None,
) -> SavingsDeposit | None:
    row = repo.get(db, deposit_id)
    if row is None:
        return None
    changes = payload.model_dump(exclude_unset=True)

    # Settled requires a settled_date - check against the row AFTER this
    # request's changes are conceptually applied (a request might set status
    # without settled_date because settled_date was already set earlier, or
    # might set both together).
    final_status = changes.get("status", row.status)
    final_settled_date = changes.get("settled_date", row.settled_date)
    if final_status == SavingsStatus.settled and final_settled_date is None:
        raise ValueError("Đã tất toán thì cần nhập thời gian tất toán")

    # maturity_date always re-derived from the resulting (start_date,
    # term_value, term_unit), whether or not this request touched them.
    start_date = changes.get("start_date", row.start_date)
    term_value = changes.get("term_value", row.term_value)
    term_unit = changes.get("term_unit", row.term_unit)
    changes["maturity_date"] = _compute_maturity_date(start_date, term_value, term_unit)

    # Refresh the expected_interest suggestion only if this request left it
    # unset AND touched one of the inputs that feeds the calculation -
    # otherwise leave whatever the user already has/customised alone.
    if "expected_interest" not in changes and _INTEREST_INPUT_FIELDS & changes.keys():
        amount = changes.get("amount", row.amount)
        interest_rate = changes.get("interest_rate", row.interest_rate)
        changes["expected_interest"] = _compute_expected_interest(
            float(amount), float(interest_rate), start_date, changes["maturity_date"],
        )

    changes["updated_by"] = actor_id
    return repo.update(db, row, changes)


def delete_deposit(db: Session, deposit_id: int) -> bool:
    row = repo.get(db, deposit_id)
    if row is None:
        return False
    repo.delete(db, row)
    return True


def summary(db: Session, year: int, user_id: int | None = None) -> SavingsSummary:
    """Top-of-screen totals: current active total/count (not date-filtered,
    same "current state" philosophy as StockHolding) plus interest actually
    received in `year` (by settled_date), the principal tất toán in `year`,
    the principal newly gửi in `year` (by start_date), and the resulting
    average return rate - see SavingsSummary for exactly what each field
    means."""
    unsettled = repo.list_unsettled(db, user_id=user_id)
    total_active_amount = sum(float(d.amount) for d in unsettled)

    all_rows = repo.list_all(db)
    in_scope = lambda d: user_id is None or d.user_id == user_id  # noqa: E731

    interest_this_year = sum(
        float(d.actual_interest)
        for d in all_rows
        if d.status == SavingsStatus.settled
        and d.actual_interest is not None
        and d.settled_date is not None
        and d.settled_date.year == year
        and in_scope(d)
    )

    total_settled_amount_this_year = sum(
        float(d.amount)
        for d in all_rows
        if d.status == SavingsStatus.settled
        and d.settled_date is not None
        and d.settled_date.year == year
        and in_scope(d)
    )

    total_deposited_this_year = sum(
        float(d.amount)
        for d in all_rows
        if d.start_date.year == year and in_scope(d)
    )

    avg_return_rate_pct = (
        round(interest_this_year / total_settled_amount_this_year * 100, 2)
        if total_settled_amount_this_year > 0 else None
    )

    return SavingsSummary(
        total_active_amount=total_active_amount,
        active_count=len(unsettled),
        interest_received_this_year=interest_this_year,
        total_settled_amount_this_year=total_settled_amount_this_year,
        total_deposited_this_year=total_deposited_this_year,
        avg_return_rate_pct=avg_return_rate_pct,
    )


def interest_received_between(
    db: Session, user_id: int, start: date_type, end: date_type
) -> float:
    """Actual interest (đã tất toán) received by `user_id` with settled_date
    in [start, end] - feeds the Tài khoản vợ/chồng auto-formula in
    app/services/asset_service.py."""
    return sum(
        float(d.actual_interest)
        for d in repo.list_all(db)
        if d.status == SavingsStatus.settled
        and d.actual_interest is not None
        and d.settled_date is not None
        and d.user_id == user_id
        and start <= d.settled_date <= end
    )
