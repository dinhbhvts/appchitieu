"""Tests for the stock module's totals and profit/loss.

Profit/loss = current holdings value + total withdrawn - total deposited (the
same way the source spreadsheet computes it). This is additive across people
and does not depend on the (often incomplete) buy/sell log.

Since the auto "Tiền mặt" holding was added, "current holdings value" always
includes that row (un-invested cash), so P/L now correctly reflects deposited
money that hasn't been put into a specific ticker yet - see test_cash_*
below and stock_service._cash_delta. The numbers in the pre-existing tests
here were updated accordingly (previously idle cash was invisible, so P/L
understated by exactly the un-invested amount).
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

    # Auto Tiền mặt row = 0 (base) + 10M (deposit) - 2M (withdraw) = 8,000,000.
    # total_holdings_value = NKG(5M) + Tiền mặt(8M) = 13,000,000.
    assert summary["total_holdings_value"] == 13000000
    # P/L = holdings(13M) + withdrawn(2M) - deposited(10M) = 5,000,000
    assert summary["total_realised_pl"] == 5000000


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

    # No withdrawals/trades: Tiền mặt(uid) == deposited(uid), so
    # holdings_value(uid) = val(uid) + dep(uid), and P/L(uid) collapses to
    # just val(uid) (the deposit cancels itself out via the cash row).
    # a: val=12M ; b: val=1M ; combined = 13M = a + b.
    assert pl_a == 12000000
    assert pl_b == 1000000
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


def test_dividend_does_not_double_count_via_manual_stock_holdings(client):
    """Cổ tức KHÔNG được cộng thêm một lần nữa vào các khoản "Đang giữ" nhập
    tay (StockHolding thường) - đó vẫn là con số người dùng tự gõ, không tự
    động cộng dồn cổ tức. Xem test_dividend_flows_into_cash_and_pl bên dưới
    cho kênh DUY NHẤT mà cổ tức thực sự ảnh hưởng tới Lãi/lỗ: dòng Tiền mặt
    tự động."""
    user_id = client.get("/users").json()[0]["id"]

    client.post("/stocks/holdings", json={
        "user_id": user_id, "symbol": "NKG", "quantity": 100, "value": 5000000,
    })
    before = client.get("/stocks/holdings", params={"user_id": user_id}).json()
    nkg_before = next(h for h in before if h["symbol"] == "NKG")["value"]

    client.post("/stocks/dividends", json={
        "date": "2026-04-01", "symbol": "NKG", "amount": 500000,
        "user_id": user_id,
    })
    after = client.get("/stocks/holdings", params={"user_id": user_id}).json()
    nkg_after = next(h for h in after if h["symbol"] == "NKG")["value"]

    # The manually-entered NKG row is untouched by recording a dividend.
    assert nkg_after == nkg_before == 5000000


def test_dividend_flows_into_cash_and_pl_via_auto_cash_row(client):
    """Cổ tức (số tiền thực nhận) tự động cộng vào dòng Tiền mặt - đây là
    con số tiền THẬT nhận được nên đúng ra phải tăng Lãi/lỗ, khác với trước
    đây (khi chưa có dòng Tiền mặt tự động, cổ tức hoàn toàn không ảnh
    hưởng gì tới total_realised_pl)."""
    user_id = client.get("/users").json()[0]["id"]

    # Deposit 10,000,000, no withdrawals, nothing currently held.
    client.post("/stocks/cashflows", json={
        "date": "2026-03-01", "type": "deposit", "amount": 10000000,
        "user_id": user_id,
    })
    before = client.get("/stocks/summary").json()
    # PL = Tiền mặt(10M) + 0(withdraw) - 10M(deposit) = 0
    assert before["total_realised_pl"] == 0
    assert before["total_dividend"] == 0

    client.post("/stocks/dividends", json={
        "date": "2026-04-01", "symbol": "NKG", "amount": 500000,
        "user_id": user_id,
    })
    after = client.get("/stocks/summary").json()
    # total_dividend is still surfaced for display...
    assert after["total_dividend"] == 500000
    # ...and now ALSO flows into P/L via the auto Tiền mặt row (+500,000),
    # exactly once - the money really was received.
    assert after["total_realised_pl"] == before["total_realised_pl"] + 500000


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


# --- Auto "Tiền mặt" cash holding -------------------------------------------

def test_cash_holding_auto_created_and_computed(client):
    user_id = client.get("/users").json()[0]["id"]

    # Before any activity: GET already auto-creates the row, value 0.
    holdings = client.get("/stocks/holdings", params={"user_id": user_id}).json()
    cash = next(h for h in holdings if h["is_cash"])
    assert cash["symbol"] == "Tiền mặt"
    assert cash["value"] == 0
    assert cash["cash_base_value"] == 0

    client.post("/stocks/cashflows", json={
        "date": "2026-03-01", "type": "deposit", "amount": 10000000,
        "user_id": user_id,
    })
    client.post("/stocks/trades", json={
        "date": "2026-03-05", "symbol": "NKG", "side": "buy",
        "quantity": 100, "price": 30000, "fee": 15000, "user_id": user_id,
    })
    client.post("/stocks/trades", json={
        "date": "2026-03-10", "symbol": "NKG", "side": "sell",
        "quantity": 40, "price": 32000, "fee": 8000, "user_id": user_id,
    })
    client.post("/stocks/dividends", json={
        "date": "2026-04-01", "symbol": "NKG", "amount": 120000,
        "user_id": user_id,
    })
    client.post("/stocks/cashflows", json={
        "date": "2026-04-05", "type": "withdraw", "amount": 1000000,
        "user_id": user_id,
    })

    # 10,000,000 (deposit) - (100*30000 + 15000) (buy) + (40*32000 - 8000)
    # (sell) + 120,000 (dividend) - 1,000,000 (withdraw)
    expected = 10000000 - (100 * 30000 + 15000) + (40 * 32000 - 8000) \
        + 120000 - 1000000
    holdings = client.get("/stocks/holdings", params={"user_id": user_id}).json()
    cash = next(h for h in holdings if h["is_cash"])
    assert cash["value"] == expected


def test_cash_holding_always_listed_first(client):
    user_id = client.get("/users").json()[0]["id"]
    # "AAA" sorts before "Tiền mặt" alphabetically, but the cash row must
    # still be pinned to the top of the list.
    client.post("/stocks/holdings", json={
        "user_id": user_id, "symbol": "AAA", "value": 1000000,
    })
    holdings = client.get("/stocks/holdings", params={"user_id": user_id}).json()
    assert holdings[0]["is_cash"] is True


def test_cash_holding_base_value_is_editable(client):
    user_id = client.get("/users").json()[0]["id"]
    holdings = client.get("/stocks/holdings", params={"user_id": user_id}).json()
    cash_id = next(h for h in holdings if h["is_cash"])["id"]

    r = client.put(f"/stocks/holdings/{cash_id}", json={"cash_base_value": 2000000})
    assert r.status_code == 200
    assert r.json()["cash_base_value"] == 2000000
    assert r.json()["value"] == 2000000  # no other activity yet


def test_cash_holding_locks_system_fields(client):
    user_id = client.get("/users").json()[0]["id"]
    holdings = client.get("/stocks/holdings", params={"user_id": user_id}).json()
    cash_id = next(h for h in holdings if h["is_cash"])["id"]

    for payload in (
        {"symbol": "XYZ"}, {"quantity": 5}, {"value": 999}, {"user_id": user_id},
    ):
        r = client.put(f"/stocks/holdings/{cash_id}", json=payload)
        assert r.status_code == 400

    # note is allowed alongside cash_base_value.
    r = client.put(f"/stocks/holdings/{cash_id}",
                    json={"cash_base_value": 500000, "note": "Số dư ban đầu"})
    assert r.status_code == 200


def test_cash_holding_cannot_be_deleted(client):
    user_id = client.get("/users").json()[0]["id"]
    holdings = client.get("/stocks/holdings", params={"user_id": user_id}).json()
    cash_id = next(h for h in holdings if h["is_cash"])["id"]

    r = client.delete(f"/stocks/holdings/{cash_id}")
    assert r.status_code == 400


def test_total_holdings_value_includes_cash(client):
    user_id = client.get("/users").json()[0]["id"]
    client.post("/stocks/holdings", json={
        "user_id": user_id, "symbol": "NKG", "value": 3000000,
    })
    holdings = client.get("/stocks/holdings", params={"user_id": user_id}).json()
    cash_id = next(h for h in holdings if h["is_cash"])["id"]
    client.put(f"/stocks/holdings/{cash_id}", json={"cash_base_value": 1000000})

    summary = client.get("/stocks/summary", params={"user_id": user_id}).json()
    assert summary["total_holdings_value"] == 4000000  # 3M (NKG) + 1M (cash)
