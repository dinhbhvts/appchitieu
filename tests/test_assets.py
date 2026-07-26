"""Tests for the asset snapshot (net worth) module."""

import pytest


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


def test_yearly_history_uses_last_month_of_each_year_as_closing(client):
    # 2024: two months of data - March and November. November (later month)
    # should be the "chốt năm" value, not the sum of both.
    client.post("/assets", json={"year": 2024, "month": 3, "name": "TK", "value": 100_000_000})
    client.post("/assets", json={"year": 2024, "month": 11, "name": "TK", "value": 150_000_000})
    # 2025: only December.
    client.post("/assets", json={"year": 2025, "month": 12, "name": "TK", "value": 200_000_000})

    yearly = client.get("/assets/yearly-history").json()
    by_year = {row["year"]: row for row in yearly}

    assert by_year[2024]["closing_month"] == 11
    assert by_year[2024]["total"] == 150_000_000
    assert by_year[2024]["change_amount"] == 0  # first year in the series -> no prior comparison
    assert by_year[2024]["change_pct"] is None

    assert by_year[2025]["closing_month"] == 12
    assert by_year[2025]["total"] == 200_000_000
    assert by_year[2025]["change_amount"] == 50_000_000
    assert by_year[2025]["change_pct"] == pytest.approx(33.3, abs=0.1)


def test_yearly_history_not_affected_by_month_data_order(client):
    # Insert out of order (later year first) - result must still be sorted
    # correctly and independent of insertion order.
    client.post("/assets", json={"year": 2023, "month": 6, "name": "A", "value": 50_000_000})
    client.post("/assets", json={"year": 2022, "month": 5, "name": "A", "value": 30_000_000})

    yearly = client.get("/assets/yearly-history").json()
    years = [row["year"] for row in yearly]
    assert years == sorted(years)
