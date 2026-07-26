"""Tests for the solar<->lunar (âm lịch) conversion utility."""


def test_solar_to_lunar_and_back(client):
    r = client.get("/lunar/to-lunar", params={"date": "2024-02-10"})
    assert r.status_code == 200
    lunar = r.json()
    # Feb 10, 2024 is Tet (mùng 1 Tết) - lunar new year's day.
    assert lunar["month"] == 1
    assert lunar["day"] == 1

    back = client.get("/lunar/to-solar", params={
        "year": lunar["year"], "month": lunar["month"], "day": lunar["day"],
        "is_leap": lunar["is_leap"],
    })
    assert back.status_code == 200
    assert back.json()["date"] == "2024-02-10"


def test_lunar_to_solar_falls_back_when_day_does_not_exist(client):
    # Lunar month 2, 2026 only has 29 days (verified via app.core.lunar) -
    # day 30 should fall back to day 29 instead of erroring.
    r = client.get("/lunar/to-solar", params={"year": 2026, "month": 2, "day": 30})
    assert r.status_code == 200
    assert r.json()["date"]  # got some valid date back, did not 400


def test_lunar_month_returns_one_row_per_day(client):
    r = client.get("/lunar/month", params={"year": 2026, "month": 2})
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 28  # Feb 2026 is not a leap solar year
    assert rows[0]["date"] == "2026-02-01"
    assert rows[-1]["date"] == "2026-02-28"
    for row in rows:
        assert 1 <= row["lunar_day"] <= 30
        assert 1 <= row["lunar_month"] <= 12
