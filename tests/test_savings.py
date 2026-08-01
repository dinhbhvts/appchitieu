"""Tests for savings deposits ("Gửi tiết kiệm")."""

import pytest


def _users(client):
    users = client.get("/users").json()
    return users[0]["id"], users[1]["id"]  # (chong, vo) - see seed.DEFAULT_USERS order


def test_create_deposit_computes_maturity_date_for_month_term(client):
    chong, _ = _users(client)
    r = client.post("/savings", json={
        "name": "Tiết kiệm 6 tháng", "start_date": "2026-01-15",
        "amount": 100_000_000, "term_value": 6, "term_unit": "month",
        "interest_rate": 5.5, "bank": "Vietcombank", "user_id": chong,
    })
    assert r.status_code == 201
    data = r.json()
    assert data["maturity_date"] == "2026-07-15"
    assert data["status"] == "active"
    # expected_interest auto-suggested (simple interest, ~181 days).
    assert data["expected_interest"] > 0


def test_create_deposit_computes_maturity_date_for_day_term(client):
    chong, _ = _users(client)
    r = client.post("/savings", json={
        "name": "Tiết kiệm 30 ngày", "start_date": "2026-01-01",
        "amount": 50_000_000, "term_value": 30, "term_unit": "day",
        "interest_rate": 3.0, "user_id": chong,
    })
    assert r.json()["maturity_date"] == "2026-01-31"


def test_expected_interest_can_be_overridden(client):
    chong, _ = _users(client)
    r = client.post("/savings", json={
        "name": "TK", "start_date": "2026-01-01", "amount": 100_000_000,
        "term_value": 12, "term_unit": "month", "interest_rate": 6,
        "expected_interest": 6_500_000, "user_id": chong,
    })
    assert r.json()["expected_interest"] == 6_500_000


def test_create_settled_without_settled_date_rejected(client):
    chong, _ = _users(client)
    r = client.post("/savings", json={
        "name": "TK", "start_date": "2026-01-01", "amount": 100_000_000,
        "term_value": 6, "term_unit": "month", "interest_rate": 5,
        "status": "settled", "user_id": chong,
    })
    assert r.status_code == 422


def test_update_to_settled_without_settled_date_rejected(client):
    chong, _ = _users(client)
    dep = client.post("/savings", json={
        "name": "TK", "start_date": "2026-01-01", "amount": 100_000_000,
        "term_value": 6, "term_unit": "month", "interest_rate": 5,
        "user_id": chong,
    }).json()
    r = client.put(f"/savings/{dep['id']}", json={"status": "settled"})
    assert r.status_code == 400


def test_settle_deposit_with_actual_interest(client):
    chong, _ = _users(client)
    dep = client.post("/savings", json={
        "name": "TK", "start_date": "2026-01-01", "amount": 100_000_000,
        "term_value": 6, "term_unit": "month", "interest_rate": 5,
        "user_id": chong,
    }).json()
    r = client.put(f"/savings/{dep['id']}", json={
        "status": "settled", "settled_date": "2026-07-01",
        "actual_interest": 2_500_000,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "settled"
    assert data["actual_interest"] == 2_500_000
    assert data["settled_date"] == "2026-07-01"


def test_edit_unrelated_field_does_not_clobber_custom_expected_interest(client):
    """Editing e.g. the note must not silently overwrite an expected_interest
    the user already customised, even though it's normally a suggestion."""
    chong, _ = _users(client)
    dep = client.post("/savings", json={
        "name": "TK", "start_date": "2026-01-01", "amount": 100_000_000,
        "term_value": 6, "term_unit": "month", "interest_rate": 5,
        "expected_interest": 9_999_000, "user_id": chong,
    }).json()
    r = client.put(f"/savings/{dep['id']}", json={"note": "cập nhật ghi chú"})
    assert r.json()["expected_interest"] == 9_999_000


def test_edit_amount_refreshes_expected_interest_when_not_explicitly_set(client):
    chong, _ = _users(client)
    dep = client.post("/savings", json={
        "name": "TK", "start_date": "2026-01-01", "amount": 100_000_000,
        "term_value": 12, "term_unit": "month", "interest_rate": 6,
        "user_id": chong,
    }).json()
    original = dep["expected_interest"]
    r = client.put(f"/savings/{dep['id']}", json={"amount": 200_000_000})
    assert r.json()["expected_interest"] == pytest.approx(original * 2, rel=0.01)


def test_maturity_date_recomputed_when_term_changes(client):
    chong, _ = _users(client)
    dep = client.post("/savings", json={
        "name": "TK", "start_date": "2026-01-01", "amount": 100_000_000,
        "term_value": 6, "term_unit": "month", "interest_rate": 5,
        "user_id": chong,
    }).json()
    assert dep["maturity_date"] == "2026-07-01"
    r = client.put(f"/savings/{dep['id']}", json={"term_value": 12})
    assert r.json()["maturity_date"] == "2027-01-01"


def test_delete_removes_from_lists(client):
    chong, _ = _users(client)
    dep = client.post("/savings", json={
        "name": "TK", "start_date": "2026-01-01", "amount": 100_000_000,
        "term_value": 6, "term_unit": "month", "interest_rate": 5,
        "user_id": chong,
    }).json()
    r = client.delete(f"/savings/{dep['id']}")
    assert r.status_code == 200

    unsettled = client.get("/savings/unsettled").json()
    assert all(d["id"] != dep["id"] for d in unsettled)
    rows = client.get("/savings", params={"start": "2026-01-01", "end": "2026-01-31"}).json()
    assert all(d["id"] != dep["id"] for d in rows)

    # Deleting a nonexistent id is a clean 404.
    r = client.delete(f"/savings/{dep['id'] + 9999}")
    assert r.status_code == 404


def test_list_unsettled_ignores_date_range(client):
    chong, _ = _users(client)
    client.post("/savings", json={
        "name": "TK cũ", "start_date": "2020-01-01", "amount": 100_000_000,
        "term_value": 60, "term_unit": "month", "interest_rate": 5,
        "user_id": chong,
    })
    unsettled = client.get("/savings/unsettled").json()
    assert any(d["name"] == "TK cũ" for d in unsettled)


def test_list_between_includes_active_and_settled(client):
    chong, _ = _users(client)
    active = client.post("/savings", json={
        "name": "Đang gửi", "start_date": "2026-03-01", "amount": 50_000_000,
        "term_value": 6, "term_unit": "month", "interest_rate": 5, "user_id": chong,
    }).json()
    settled = client.post("/savings", json={
        "name": "Đã tất toán", "start_date": "2026-03-05", "amount": 30_000_000,
        "term_value": 3, "term_unit": "month", "interest_rate": 4, "user_id": chong,
    }).json()
    client.put(f"/savings/{settled['id']}", json={
        "status": "settled", "settled_date": "2026-06-05", "actual_interest": 300_000,
    })

    rows = client.get("/savings", params={"start": "2026-03-01", "end": "2026-03-31"}).json()
    names = {r["name"] for r in rows}
    assert names == {"Đang gửi", "Đã tất toán"}
    statuses = {r["name"]: r["status"] for r in rows}
    assert statuses["Đang gửi"] == "active"
    assert statuses["Đã tất toán"] == "settled"


def test_summary_totals(client):
    chong, vo = _users(client)
    client.post("/savings", json={
        "name": "TK1", "start_date": "2026-01-01", "amount": 100_000_000,
        "term_value": 6, "term_unit": "month", "interest_rate": 5, "user_id": chong,
    })
    client.post("/savings", json={
        "name": "TK2", "start_date": "2026-02-01", "amount": 50_000_000,
        "term_value": 6, "term_unit": "month", "interest_rate": 5, "user_id": vo,
    })
    settled = client.post("/savings", json={
        "name": "TK3", "start_date": "2025-01-01", "amount": 80_000_000,
        "term_value": 12, "term_unit": "month", "interest_rate": 6, "user_id": chong,
    }).json()
    client.put(f"/savings/{settled['id']}", json={
        "status": "settled", "settled_date": "2026-01-01", "actual_interest": 4_800_000,
    })

    combined = client.get("/savings/summary", params={"year": 2026}).json()
    assert combined["total_active_amount"] == 150_000_000
    assert combined["active_count"] == 2
    assert combined["interest_received_this_year"] == 4_800_000
    # TK3 (80M, tất toán 2026) là khoản duy nhất tất toán trong 2026.
    assert combined["total_settled_amount_this_year"] == 80_000_000
    # TK1 + TK2 mở mới trong 2026 (100M + 50M); TK3 mở từ 2025 nên không tính.
    assert combined["total_deposited_this_year"] == 150_000_000
    # 4,800,000 / 80,000,000 * 100 = 6.0%
    assert combined["avg_return_rate_pct"] == 6.0
    # TK1 và TK2 đều mở trong chính 2026 (không phải "gửi từ trước"); TK3 tuy
    # mở từ 2025 nhưng đã tất toán nên không còn active - vậy "gửi từ trước
    # năm 2026 mà vẫn đang gửi" = 0.
    assert combined["active_amount_before_this_year"] == 0

    only_vo = client.get("/savings/summary", params={"year": 2026, "user_id": vo}).json()
    assert only_vo["total_active_amount"] == 50_000_000
    assert only_vo["active_count"] == 1
    assert only_vo["interest_received_this_year"] == 0
    assert only_vo["total_settled_amount_this_year"] == 0
    assert only_vo["total_deposited_this_year"] == 50_000_000
    # Vợ chưa tất toán khoản nào trong 2026 -> tránh chia 0, trả về None.
    assert only_vo["avg_return_rate_pct"] is None

    other_year = client.get("/savings/summary", params={"year": 2025}).json()
    assert other_year["interest_received_this_year"] == 0
    assert other_year["total_settled_amount_this_year"] == 0
    # TK3 mở trong 2025.
    assert other_year["total_deposited_this_year"] == 80_000_000
    assert other_year["avg_return_rate_pct"] is None


def test_summary_active_amount_before_this_year_excludes_new_deposits(client):
    """Bug đã sửa: 'Tổng số tiền gửi từ trước' KHÔNG được lẫn với các khoản
    mới gửi trong chính năm đang xem - dù cả hai đều đang 'active'."""
    chong, _ = _users(client)
    client.post("/savings", json={
        # Gửi từ 2024, vẫn đang gửi (chưa tất toán) khi xem báo cáo 2026.
        "name": "TK cũ", "start_date": "2024-05-01", "amount": 60_000_000,
        "term_value": 36, "term_unit": "month", "interest_rate": 5, "user_id": chong,
    })
    client.post("/savings", json={
        # Gửi mới trong chính năm 2026.
        "name": "TK mới", "start_date": "2026-03-01", "amount": 17_000_000,
        "term_value": 6, "term_unit": "month", "interest_rate": 5, "user_id": chong,
    })

    s = client.get("/savings/summary", params={"year": 2026}).json()
    assert s["total_active_amount"] == 77_000_000
    # Chỉ "TK cũ" (60M) tính là gửi từ trước 2026 - "TK mới" (17M) dù đang
    # active vẫn không được tính vào đây vì nó mở trong chính năm 2026.
    assert s["active_amount_before_this_year"] == 60_000_000
    assert s["total_deposited_this_year"] == 17_000_000

    # Xem báo cáo năm 2025 (trước khi "TK mới" tồn tại): ca hai khoan deu
    # duoc mo truoc hoac trong 2025? TK cu mo 2024 (< 2025) -> tinh; TK moi
    # mo 2026 (> 2025) nen khong lien quan gi toi nam 2025 (khong active tai
    # thoi diem do trong du lieu logic don gian cua app - chi xet start_date).
    s2025 = client.get("/savings/summary", params={"year": 2025}).json()
    assert s2025["active_amount_before_this_year"] == 60_000_000
    assert s2025["total_deposited_this_year"] == 0


def test_summary_avg_return_rate_with_multiple_settlements(client):
    """Tỉ suất lợi nhuận trung bình = tổng lãi thực nhận / tổng tiền gốc tất
    toán trong năm * 100, gộp nhiều khoản tất toán cùng năm."""
    chong, _ = _users(client)
    d1 = client.post("/savings", json={
        "name": "TK A", "start_date": "2025-01-01", "amount": 100_000_000,
        "term_value": 12, "term_unit": "month", "interest_rate": 5, "user_id": chong,
    }).json()
    d2 = client.post("/savings", json={
        "name": "TK B", "start_date": "2025-06-01", "amount": 200_000_000,
        "term_value": 6, "term_unit": "month", "interest_rate": 5, "user_id": chong,
    }).json()
    client.put(f"/savings/{d1['id']}", json={
        "status": "settled", "settled_date": "2026-01-01", "actual_interest": 5_000_000,
    })
    client.put(f"/savings/{d2['id']}", json={
        "status": "settled", "settled_date": "2026-03-01", "actual_interest": 10_000_000,
    })

    s = client.get("/savings/summary", params={"year": 2026}).json()
    assert s["total_settled_amount_this_year"] == 300_000_000
    assert s["interest_received_this_year"] == 15_000_000
    # 15,000,000 / 300,000,000 * 100 = 5.0%
    assert s["avg_return_rate_pct"] == 5.0
