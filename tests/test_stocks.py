"""Tests for the stock module's totals and profit/loss.

Profit/loss = current holdings value + total withdrawn - total deposited (the
same way the source spreadsheet computes it). This is additive across people
and does not depend on the (often incomplete) buy/sell log.
"""


def test_stock_summary_and_pl(client):
    user_id = client.get("/users").json()[0]["id"]

    # Deposit 10,000,000 and later withdraw 2,000,000.
    client.post("/stocks/cashflows", json={
        "date": "2026-03-01", "type": "deposit", "amount": 10000000,
        "user_id": user_id,
    })
    client.post("/stocks/cashflows", json={
        "date": "2026-04-01", "type": "withdraw", "amount": 2000000,
        "user_id": user_id,
    })

    # Currently holding NKG worth 5,000,000.
    client.post("/stocks/holdings", json={
        "user_id": user_id, "symbol": "NKG", "quantity": 100, "value": 5000000,
    })

    summary = client.get("/stocks/summary").json()
    assert summary["cum_deposit"] == 10000000
    assert summary["cum_withdraw"] == 2000000
    assert summary["invested_capital"] == 8000000  # 10M - 2M

    # P/L = holdings(5M) + withdrawn(2M) - deposited(10M) = -3,000,000
    assert summary["total_realised_pl"] == -3000000


def test_stock_pl_is_additive_across_people(client):
    users = client.get("/users").json()
    a, b = users[0]["id"], users[1]["id"]

    for uid, dep, val in [(a, 10000000, 12000000), (b, 5000000, 1000000)]:
        client.post("/stocks/cashflows", json={
            "date": "2026-03-01", "type": "deposit", "amount": dep,
            "user_id": uid,
        })
        client.post("/stocks/holdings", json={
            "user_id": uid, "symbol": "AAA", "value": val,
        })

    pl_a = client.get("/stocks/summary", params={"user_id": a}).json()[
        "total_realised_pl"]
    pl_b = client.get("/stocks/summary", params={"user_id": b}).json()[
        "total_realised_pl"]
    pl_all = client.get("/stocks/summary").json()["total_realised_pl"]

    # a: 12M - 10M = +2M ; b: 1M - 5M = -4M ; combined = -2M = a + b.
    assert pl_a == 2000000
    assert pl_b == -4000000
    assert pl_all == pl_a + pl_b
