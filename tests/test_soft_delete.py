"""Tests for the app-wide soft-delete convention: "Xóa" from any UI/endpoint
must hide the row from lists (existing behavior tests already cover this per
module) but must NOT actually remove it from the database - it only sets
is_deleted=True + deleted_at, so the underlying data is never truly lost.

This file specifically checks the "still in the DB" half, by reading the row
straight from the database after calling the DELETE endpoint - the half that
a "does it disappear from the list" test cannot tell apart from a real hard
delete.
"""

from app.core.database import SessionLocal
from app.models.asset import AssetSnapshot
from app.models.notebook_item import NotebookItem
from app.models.stock import StockCashFlow, StockDividend, StockHolding, StockTrade
from app.models.transaction import Transaction


def test_deleted_transaction_still_exists_in_db(client):
    user_id = client.get("/users").json()[0]["id"]
    created = client.post("/transactions", json={
        "date": "2026-07-01", "type": "expense", "amount": 100000,
        "content": "Xoa thu", "user_id": user_id,
    }).json()

    assert client.delete(f"/transactions/{created['id']}").status_code == 200
    assert all(x["id"] != created["id"] for x in client.get("/transactions").json())

    with SessionLocal() as db:
        row = db.get(Transaction, created["id"])
        assert row is not None
        assert row.is_deleted is True
        assert row.deleted_at is not None


def test_deleted_asset_snapshot_still_exists_in_db(client):
    created = client.post("/assets", json={
        "year": 2026, "month": 7, "name": "Xoa thu", "value": 1000000,
    }).json()

    assert client.delete(f"/assets/{created['id']}").status_code == 200
    month = client.get("/assets/month", params={"year": 2026, "month": 7}).json()
    assert all(x["id"] != created["id"] for x in month["items"])

    with SessionLocal() as db:
        row = db.get(AssetSnapshot, created["id"])
        assert row is not None
        assert row.is_deleted is True


def test_deleted_notebook_item_still_exists_in_db(client):
    created = client.post("/notebook-items", json={
        "type": "note", "title": "Xoa thu",
    }).json()

    assert client.delete(f"/notebook-items/{created['id']}").status_code == 200

    with SessionLocal() as db:
        row = db.get(NotebookItem, created["id"])
        assert row is not None
        assert row.is_deleted is True


def test_deleted_stock_cashflow_still_exists_in_db(client):
    user_id = client.get("/users").json()[0]["id"]
    created = client.post("/stocks/cashflows", json={
        "date": "2026-07-01", "type": "deposit", "amount": 1000000,
        "user_id": user_id,
    }).json()

    assert client.delete(f"/stocks/cashflows/{created['id']}").status_code == 200
    assert all(x["id"] != created["id"] for x in client.get("/stocks/cashflows").json())

    with SessionLocal() as db:
        row = db.get(StockCashFlow, created["id"])
        assert row is not None
        assert row.is_deleted is True


def test_deleted_stock_trade_still_exists_in_db(client):
    user_id = client.get("/users").json()[0]["id"]
    created = client.post("/stocks/trades", json={
        "date": "2026-07-01", "symbol": "NKG", "side": "buy",
        "quantity": 100, "price": 20000, "user_id": user_id,
    }).json()

    assert client.delete(f"/stocks/trades/{created['id']}").status_code == 200
    assert all(x["id"] != created["id"] for x in client.get("/stocks/trades").json())

    with SessionLocal() as db:
        row = db.get(StockTrade, created["id"])
        assert row is not None
        assert row.is_deleted is True


def test_deleted_stock_holding_still_exists_in_db(client):
    user_id = client.get("/users").json()[0]["id"]
    created = client.post("/stocks/holdings", json={
        "user_id": user_id, "symbol": "NKG", "value": 1000000,
    }).json()

    assert client.delete(f"/stocks/holdings/{created['id']}").status_code == 200
    assert all(x["id"] != created["id"] for x in client.get("/stocks/holdings").json())

    with SessionLocal() as db:
        row = db.get(StockHolding, created["id"])
        assert row is not None
        assert row.is_deleted is True


def test_deleted_stock_dividend_still_exists_in_db(client):
    user_id = client.get("/users").json()[0]["id"]
    created = client.post("/stocks/dividends", json={
        "date": "2026-07-01", "symbol": "NKG", "amount": 500000,
        "user_id": user_id,
    }).json()

    assert client.delete(f"/stocks/dividends/{created['id']}").status_code == 200
    assert all(x["id"] != created["id"] for x in client.get("/stocks/dividends").json())

    with SessionLocal() as db:
        row = db.get(StockDividend, created["id"])
        assert row is not None
        assert row.is_deleted is True
