"""Tests for the stock module's average-cost profit/loss calculation."""


def test_stock_summary_and_realised_pl(client):
    user_id = client.get("/users").json()[0]["id"]

    # Deposit 10,000,000 into the brokerage account.
    client.post("/stocks/cashflows", json={
        "date": "2026-03-01", "type": "deposit", "amount": 10000000,
        "user_id": user_id,
    })

    # Buy 100 NKG @ 47,000 (fee 0), then sell 100 @ 49,000 (fee 0).
    client.post("/stocks/trades", json={
        "date": "2026-03-02", "symbol": "nkg", "side": "buy",
        "quantity": 100, "price": 47000, "fee": 0, "user_id": user_id,
    })
    client.post("/stocks/trades", json={
        "date": "2026-03-10", "symbol": "NKG", "side": "sell",
        "quantity": 100, "price": 49000, "fee": 0, "user_id": user_id,
    })

    summary = client.get("/stocks/summary").json()
    assert summary["total_deposit"] == 10000000
    assert summary["invested_capital"] == 10000000

    # Realised profit = (49,000 - 47,000) * 100 = 200,000
    assert summary["total_realised_pl"] == 200000

    # 'nkg' and 'NKG' are the same ticker; all shares sold => nothing held.
    positions = {p["symbol"]: p for p in summary["positions"]}
    assert positions["NKG"]["quantity_held"] == 0
    assert positions["NKG"]["realised_pl"] == 200000
