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


def test_dividend_create_list_update(client):
    user_id = client.get("/users").json()[0]["id"]

    created = client.post("/stocks/dividends", json={
        "date": "2026-06-01", "symbol": "nkg", "amount": 300000,
        "user_id": user_id, "note": "Cổ tức Q2",
    }).json()
    # Symbol normalised to upper-case, same as trades.
    assert created["symbol"] == "NKG"

    rows = client.get("/stocks/dividends").json()
    assert any(r["id"] == created["id"] for r in rows)

    updated = client.put(f"/stocks/dividends/{created['id']}", json={
        "amount": 350000,
    }).json()
    assert updated["amount"] == 350000


def test_dividend_is_record_keeping_only_not_counted_in_pl(client):
    """Cổ tức chỉ để lưu trữ - KHÔNG cộng vào Lãi/lỗ, vì người dùng tự điều
    chỉnh "Đang giữ" hàng tháng đã bao gồm hiệu ứng cổ tức trong đó rồi."""
    user_id = client.get("/users").json()[0]["id"]

    # Deposit 10,000,000, no withdrawals, nothing currently held.
    client.post("/stocks/cashflows", json={
        "date": "2026-03-01", "type": "deposit", "amount": 10000000,
        "user_id": user_id,
    })
    before = client.get("/stocks/summary").json()
    # PL = 0(holdings) + 0(withdraw) - 10M(deposit) = -10M
    assert before["total_realised_pl"] == -10000000
    assert before["total_dividend"] == 0

    client.post("/stocks/dividends", json={
        "date": "2026-04-01", "symbol": "NKG", "amount": 500000,
        "user_id": user_id,
    })
    after = client.get("/stocks/summary").json()
    # total_dividend is surfaced for display...
    assert after["total_dividend"] == 500000
    # ...but does NOT change total_realised_pl.
    assert after["total_realised_pl"] == before["total_realised_pl"]


def test_dividend_accepts_quantity_only_or_amount_only(client):
    user_id = client.get("/users").json()[0]["id"]

    qty_only = client.post("/stocks/dividends", json={
        "date": "2026-05-01", "symbol": "NKG", "quantity": 100,
        "user_id": user_id,
    })
    assert qty_only.status_code == 201
    assert qty_only.json()["quantity"] == 100
    assert qty_only.json()["amount"] is None

    amount_only = client.post("/stocks/dividends", json={
        "date": "2026-05-01", "symbol": "NKG", "amount": 200000,
        "user_id": user_id,
    })
    assert amount_only.status_code == 201
    assert amount_only.json()["amount"] == 200000

    both = client.post("/stocks/dividends", json={
        "date": "2026-05-01", "symbol": "NKG", "quantity": 50,
        "amount": 100000, "user_id": user_id,
    })
    assert both.status_code == 201
    assert both.json()["quantity"] == 50
    assert both.json()["amount"] == 100000


def test_dividend_requires_quantity_or_amount(client):
    user_id = client.get("/users").json()[0]["id"]
    r = client.post("/stocks/dividends", json={
        "date": "2026-05-01", "symbol": "NKG", "user_id": user_id,
    })
    assert r.status_code == 422
