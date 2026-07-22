"""Tests for the asset snapshot (net worth) module."""


def test_add_month_total_and_history(client):
    # Two asset lines in July 2026.
    client.post("/assets", json={
        "year": 2026, "month": 7, "name": "TK vo", "value": 776240000,
    })
    client.post("/assets", json={
        "year": 2026, "month": 7, "name": "Vang 9999", "value": 54000000,
        "note": "1 cay",
    })

    month = client.get("/assets/month", params={"year": 2026, "month": 7}).json()
    assert month["total"] == 830240000
    assert len(month["items"]) == 2

    history = client.get("/assets/history").json()
    assert history[-1]["total"] == 830240000


def test_copy_previous_month(client):
    client.post("/assets", json={
        "year": 2026, "month": 6, "name": "TK vo", "value": 700000000,
    })
    # Copy June's list into July, then edit the value.
    july = client.post(
        "/assets/copy-previous", params={"year": 2026, "month": 7}
    ).json()
    assert july["total"] == 700000000
    assert july["items"][0]["name"] == "TK vo"

    item_id = july["items"][0]["id"]
    client.put(f"/assets/{item_id}", json={"value": 776240000})
    updated = client.get(
        "/assets/month", params={"year": 2026, "month": 7}
    ).json()
    assert updated["total"] == 776240000
