"""Import every model here so SQLAlchemy's Base registry sees all tables.

Alembic and Base.metadata.create_all() only know about models that have been
imported at least once. Importing them in this package __init__ guarantees that
happens as soon as `app.models` is imported anywhere.
"""

from app.models.asset import AssetSnapshot
from app.models.category import Category
from app.models.notebook_item import NotebookItem
from app.models.stock import (
    StockCashFlow,
    StockHolding,
    StockMonthSummary,
    StockTrade,
)
from app.models.transaction import Transaction
from app.models.user import User

__all__ = [
    "AssetSnapshot",
    "Category",
    "NotebookItem",
    "StockCashFlow",
    "StockHolding",
    "StockMonthSummary",
    "StockTrade",
    "Transaction",
    "User",
]
