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


def test_list_settled_filters_by_settled_date_not_start_date(client):
    """/savings/settled lọc theo settled_date (ngày tất toán) - KHÁC
    /savings (list_between) vốn lọc theo start_date (ngày gửi). Một khoản mở
    (gửi) ngoài khoảng tìm kiếm nhưng TẤT TOÁN trong khoảng đó vẫn phải xuất
    hiện; một khoản đang active (chưa tất toán) không bao giờ xuất hiện dù
    start_date rơi đúng khoảng."""
    chong, _ = _users(client)
    settled_in_range = client.post("/savings", json={
        "name": "Tất toán tháng 3", "start_date": "2025-09-01", "amount": 40_000_000,
        "term_value": 6, "term_unit": "month", "interest_rate": 5, "user_id": chong,
    }).json()
    client.put(f"/savings/{settled_in_range['id']}", json={
        "status": "settled", "settled_date": "2026-03-15", "actual_interest": 1_000_000,
    })
    settled_out_of_range = client.post("/savings", json={
        "name": "Tất toán tháng 2", "start_date": "2025-08-01", "amount": 20_000_000,
        "term_value": 6, "term_unit": "month", "interest_rate": 5, "user_id": chong,
    }).json()
    client.put(f"/savings/{settled_out_of_range['id']}", json={
        "status": "settled", "settled_date": "2026-02-01", "actual_interest": 500_000,
    })
    still_active = client.post("/savings", json={
        # start_date roi dung khoang tim kiem nhung chua tat toan.
        "name": "Đang gửi trong tháng 3", "start_date": "2026-03-10", "amount": 10_000_000,
        "term_value": 6, "term_unit": "month", "interest_rate": 5, "user_id": chong,
    }).json()

    rows = client.get("/savings/settled", params={"start": "2026-03-01", "end": "2026-03-31"}).json()
    names = {r["name"] for r in rows}
    assert names == {"Tất toán tháng 3"}
    assert all(r["id"] != still_active["id"] for r in rows)
    assert all(r["id"] != settled_out_of_range["id"] for r in rows)
    assert rows[0]["status"] == "settled"
    assert rows[0]["actual_interest"] == 1_000_000


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
    # Money-weighted: TK3 gửi đúng 365 ngày (2025-01-01 -> 2026-01-01) nên
    # trọng số = gốc y hệt lãi đơn 1 năm -> trùng với lãi/gốc đơn thuần:
    # 4,800,000 / (80,000,000 * 365/365) * 100 = 6.0%.
    assert combined["avg_return_rate_pct"] == 6.0
    # TK1 và TK2 đều mở trong chính 2026 nên không tính vào "đầu năm". TK3 mở
    # từ 2025 (< 2026) và còn hiệu lực tính đến 01/01/2026 (chỉ tất toán ĐÚNG
    # ngày 01/01/2026, tức chưa tất toán trước đó) nên VẪN được tính vào số
    # dư đầu năm dù sau đó tất toán ngay trong năm 2026.
    assert combined["opening_balance_this_year"] == 80_000_000
    # Đối chiếu: đang gửi hiện tại = đầu năm + gửi thêm trong năm - tất toán
    # trong năm (80M + 150M - 80M = 150M).
    assert combined["total_active_amount"] == (
        combined["opening_balance_this_year"]
        + combined["total_deposited_this_year"]
        - combined["total_settled_amount_this_year"]
    )

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


def test_summary_opening_balance_this_year_excludes_new_deposits(client):
    """Bug đã sửa: 'Số dư đầu năm' KHÔNG được lẫn với các khoản mới gửi
    trong chính năm đang xem - dù cả hai đều đang 'active'."""
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
    # Chỉ "TK cũ" (60M) tính là số dư đầu năm 2026 - "TK mới" (17M) dù đang
    # active vẫn không được tính vào đây vì nó mở trong chính năm 2026.
    assert s["opening_balance_this_year"] == 60_000_000
    assert s["total_deposited_this_year"] == 17_000_000

    # Xem báo cáo năm 2025 (trước khi "TK mới" tồn tại): ca hai khoan deu
    # duoc mo truoc hoac trong 2025? TK cu mo 2024 (< 2025) -> tinh; TK moi
    # mo 2026 (> 2025) nen khong lien quan gi toi nam 2025 (khong active tai
    # thoi diem do trong du lieu logic don gian cua app - chi xet start_date).
    s2025 = client.get("/savings/summary", params={"year": 2025}).json()
    assert s2025["opening_balance_this_year"] == 60_000_000
    assert s2025["total_deposited_this_year"] == 0


def test_summary_opening_balance_includes_deposit_settled_during_the_year(client):
    """Khoản gửi TỪ TRƯỚC năm đang chọn nhưng bị tất toán NGAY TRONG năm đó
    vẫn phải được tính vào "số dư đầu năm" (nó CÓ active vào lúc 01/01) - dù
    hiện tại (sau khi tất toán) không còn nằm trong danh sách đang gửi.
    Đây chính là phần chênh lệch từng gây ra 1 != 2+3+4 trước khi sửa."""
    chong, _ = _users(client)
    old_dep = client.post("/savings", json={
        # Gửi từ 2024, chưa tất toán tại thời điểm 01/01/2026.
        "name": "TK cũ sẽ tất toán trong năm", "start_date": "2024-06-01",
        "amount": 40_000_000, "term_value": 36, "term_unit": "month",
        "interest_rate": 5, "user_id": chong,
    }).json()
    client.post("/savings", json={
        "name": "TK mới trong năm", "start_date": "2026-04-01", "amount": 20_000_000,
        "term_value": 6, "term_unit": "month", "interest_rate": 5, "user_id": chong,
    })
    # Tất toán "TK cũ" vào giữa năm 2026.
    client.put(f"/savings/{old_dep['id']}", json={
        "status": "settled", "settled_date": "2026-06-01", "actual_interest": 2_000_000,
    })

    s = client.get("/savings/summary", params={"year": 2026}).json()
    # Chỉ còn "TK mới" đang active.
    assert s["total_active_amount"] == 20_000_000
    # "TK cũ" (40M) tuy đã tất toán trong năm nhưng VẪN active tại 01/01/2026
    # nên vẫn tính vào số dư đầu năm.
    assert s["opening_balance_this_year"] == 40_000_000
    assert s["total_deposited_this_year"] == 20_000_000
    assert s["total_settled_amount_this_year"] == 40_000_000
    # Đối chiếu đúng tuyệt đối: 40M + 20M - 40M = 20M.
    assert s["total_active_amount"] == (
        s["opening_balance_this_year"]
        + s["total_deposited_this_year"]
        - s["total_settled_amount_this_year"]
    )


def test_summary_avg_return_rate_with_multiple_settlements(client):
    """Tỉ suất lợi nhuận trung bình/năm = bình quân theo GỐC x THỜI GIAN GỬI
    (money-weighted annualized): Σ lãi thực nhận / Σ (gốc * số ngày gửi/365)
    * 100 - KHÔNG phải lãi/tổng gốc tất toán đơn thuần, vì 2 khoản dưới đây
    có kỳ hạn khác nhau (12 tháng vs 6 tháng) nên phải quy đổi về cùng đơn vị
    %/năm trước khi gộp."""
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
    # TK A: 365 ngày gửi -> trọng số = 100,000,000 * 365/365 = 100,000,000.
    # TK B: 273 ngày gửi (2025-06-01 -> 2026-03-01) -> trọng số =
    # 200,000,000 * 273/365 ≈ 149,589,041.10.
    # avg = 15,000,000 / (100,000,000 + 149,589,041.10) * 100 ≈ 6.01%
    # (khác 5.0% của công thức cũ lãi/tổng gốc đơn thuần, vì TK B kỳ hạn
    # ngắn hơn được quy đổi đúng tỉ trọng thời gian thay vì tính ngang TK A).
    assert s["avg_return_rate_pct"] == 6.01
