"""Tests for the transactions and reports endpoints."""


def test_seeded_users_and_categories(client):
    """A fresh install should have the two users and the default categories."""
    users = client.get("/users").json()
    assert len(users) == 2

    categories = client.get("/categories").json()
    names = {c["name"] for c in categories}
    assert "Ăn uống" in names


def test_create_and_running_balance(client):
    """Income then expense should produce the correct running balance."""
    user_id = client.get("/users").json()[0]["id"]

    # +1,000,000 income
    client.post("/transactions", json={
        "date": "2026-07-01", "type": "income", "amount": 1000000,
        "content": "Luong", "user_id": user_id,
    })
    # -200,000 expense
    client.post("/transactions", json={
        "date": "2026-07-02", "type": "expense", "amount": 200000,
        "content": "Di cho", "user_id": user_id,
    })

    rows = client.get("/transactions").json()
    assert len(rows) == 2
    # Balance after the two rows: 1,000,000 - 200,000 = 800,000
    assert rows[-1]["running_balance"] == 800000


def test_report_summary(client):
    """The period summary should total income, expense and net balance."""
    user_id = client.get("/users").json()[0]["id"]
    client.post("/transactions", json={
        "date": "2026-07-01", "type": "income", "amount": 5000000,
        "content": "Luong", "user_id": user_id,
    })
    client.post("/transactions", json={
        "date": "2026-07-10", "type": "expense", "amount": 1500000,
        "content": "Chi tieu", "user_id": user_id,
    })

    summary = client.get("/reports/summary").json()
    assert summary["total_income"] == 5000000
    assert summary["total_expense"] == 1500000
    assert summary["balance"] == 3500000


def test_transfer_does_not_change_fund_but_shows_in_person_report(client):
    users = client.get("/users").json()
    chong = users[0]["id"]
    vo = users[1]["id"]

    # Husband salary 30,500,000 into the fund.
    client.post("/transactions", json={
        "date": "2026-07-01", "type": "income", "amount": 30500000,
        "content": "Lương chồng", "user_id": chong,
    })
    # Husband transfers 26,388,888 to wife (internal move).
    client.post("/transactions", json={
        "date": "2026-07-02", "type": "transfer", "amount": 26388888,
        "content": "Chuyển cho vợ", "user_id": chong,
    })

    # Household: transfer must NOT change income/expense/balance.
    fund = client.get("/reports/summary").json()
    assert fund["total_income"] == 30500000
    assert fund["total_expense"] == 0
    assert fund["balance"] == 30500000

    # Husband: transferred_out shown; net held = 30,500,000 - 26,388,888.
    ch = client.get("/reports/summary", params={"user_id": chong}).json()
    assert ch["transferred_out"] == 26388888
    assert ch["net_held"] == 30500000 - 26388888

    # Wife: received the transfer.
    v = client.get("/reports/summary", params={"user_id": vo}).json()
    assert v["transferred_in"] == 26388888
    assert v["net_held"] == 26388888
