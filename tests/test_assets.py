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


def test_plain_items_carry_forward_automatically_without_manual_copy(client):
    """Just viewing a new month (GET /assets/month) must auto-carry the
    previous month's plain lines - no explicit "Chép từ tháng trước" call
    needed anymore."""
    client.post("/assets", json={
        "year": 2026, "month": 6, "name": "TK vo", "value": 700_000_000,
    })
    july = client.get("/assets/month", params={"year": 2026, "month": 7}).json()
    assert july["total"] == 700_000_000
    assert [i["name"] for i in july["items"]] == ["TK vo"]

    # Still fully editable/deletable, like a normal manually-entered row.
    item_id = july["items"][0]["id"]
    r = client.put(f"/assets/{item_id}", json={"value": 1})
    assert r.status_code == 200
    r = client.delete(f"/assets/{item_id}")
    assert r.status_code == 200


def test_carry_forward_does_not_duplicate_on_repeated_views(client):
    client.post("/assets", json={
        "year": 2026, "month": 6, "name": "TK vo", "value": 700_000_000,
    })
    client.get("/assets/month", params={"year": 2026, "month": 7})
    client.get("/assets/month", params={"year": 2026, "month": 7})
    july = client.get("/assets/month", params={"year": 2026, "month": 7}).json()
    assert len(july["items"]) == 1


def test_carry_forward_coexists_with_system_items_from_cutover(client):
    """From 8/2026 onward, a month always has the 4 pinned system rows -
    plain rows must still carry forward alongside them without being
    blocked by the system rows' mere presence."""
    client.post("/assets", json={
        "year": 2026, "month": 7, "name": "Tài khoản vợ", "value": 700_000_000,
    })
    client.post("/assets", json={
        "year": 2026, "month": 7, "name": "Vàng 9999", "value": 54_000_000,
    })

    aug = client.get("/assets/month", params={"year": 2026, "month": 8}).json()
    names = [i["name"] for i in aug["items"]]
    assert "Vàng 9999" in names
    # 4 system rows + the 1 carried-forward plain row.
    assert len(aug["items"]) == 5

    # Viewing again must not duplicate the carried-forward row.
    aug2 = client.get("/assets/month", params={"year": 2026, "month": 8}).json()
    assert len(aug2["items"]) == 5


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


# --- 4 mục hệ thống (Tài khoản/Chứng khoán vợ/chồng) từ 8/2026 -------------

SYSTEM_NAMES = ["Tài khoản vợ", "Tài khoản chồng", "Chứng khoán vợ", "Chứng khoán chồng"]


def _users(client):
    users = client.get("/users").json()
    return users[0]["id"], users[1]["id"]  # (chong, vo) - see seed.DEFAULT_USERS order


def test_months_before_cutover_are_untouched_plain_rows(client):
    """7/2026 (the anchor month) must stay exactly as a normal, user-entered
    row - no pinning, no lock, even if its name matches a system label."""
    client.post("/assets", json={
        "year": 2026, "month": 7, "name": "Tài khoản vợ", "value": 776240000,
    })
    month = client.get("/assets/month", params={"year": 2026, "month": 7}).json()
    assert len(month["items"]) == 1
    item = month["items"][0]
    assert item["system_key"] is None

    # Fully editable/deletable, unlike a real system row.
    r = client.put(f"/assets/{item['id']}", json={"value": 800000000})
    assert r.status_code == 200
    r = client.delete(f"/assets/{item['id']}")
    assert r.status_code == 200


def test_system_items_pinned_first_in_fixed_order_from_cutover(client):
    month = client.get("/assets/month", params={"year": 2026, "month": 8}).json()
    names = [i["name"] for i in month["items"]]
    assert names[:4] == SYSTEM_NAMES
    keys = [i["system_key"] for i in month["items"][:4]]
    assert keys == ["vo_taikhoan", "chong_taikhoan", "vo_ck", "chong_ck"]

    # A plain row added afterwards must sort after the 4 pinned rows.
    client.post("/assets", json={"year": 2026, "month": 8, "name": "Vàng", "value": 1})
    month2 = client.get("/assets/month", params={"year": 2026, "month": 8}).json()
    assert [i["name"] for i in month2["items"][:4]] == SYSTEM_NAMES
    assert month2["items"][-1]["name"] == "Vàng"


def test_system_items_cannot_be_edited_or_deleted(client):
    month = client.get("/assets/month", params={"year": 2026, "month": 8}).json()
    system_row = month["items"][0]
    assert system_row["system_key"] == "vo_taikhoan"

    r = client.put(f"/assets/{system_row['id']}", json={"value": 999})
    assert r.status_code == 400

    r = client.delete(f"/assets/{system_row['id']}")
    assert r.status_code == 400


def test_account_formula_uses_prev_closing_plus_net_held(client):
    chong, vo = _users(client)

    # Anchor month (7/2026): historical, hand-entered closing balances.
    client.post("/assets", json={
        "year": 2026, "month": 7, "name": "Tài khoản vợ", "value": 700_000_000,
    })
    client.post("/assets", json={
        "year": 2026, "month": 7, "name": "Tài khoản chồng", "value": 300_000_000,
    })

    # 8/2026 flows: husband earns 30,500,000 and transfers 26,388,888 to wife.
    client.post("/transactions", json={
        "date": "2026-08-01", "type": "income", "amount": 30_500_000,
        "content": "Lương chồng", "user_id": chong,
    })
    client.post("/transactions", json={
        "date": "2026-08-02", "type": "transfer", "amount": 26_388_888,
        "content": "Chuyển cho vợ", "user_id": chong,
    })
    # Wife spends 5,000,000 in August.
    client.post("/transactions", json={
        "date": "2026-08-03", "type": "expense", "amount": 5_000_000,
        "content": "Chi tiêu", "user_id": vo,
    })

    month = client.get("/assets/month", params={"year": 2026, "month": 8}).json()
    by_name = {i["name"]: i["value"] for i in month["items"]}

    # Vợ: prev(700M) + (nhận 26,388,888 - chi 5,000,000)
    assert by_name["Tài khoản vợ"] == 700_000_000 + 26_388_888 - 5_000_000
    # Chồng: prev(300M) + (thu 30,500,000 - chuyển 26,388,888)
    assert by_name["Tài khoản chồng"] == 300_000_000 + 30_500_000 - 26_388_888


def test_stock_items_auto_fill_from_holdings(client):
    chong, vo = _users(client)
    client.post("/stocks/holdings", json={
        "user_id": vo, "symbol": "NKG", "value": 5_000_000,
    })
    client.post("/stocks/holdings", json={
        "user_id": chong, "symbol": "AAA", "value": 12_000_000,
    })

    month = client.get("/assets/month", params={"year": 2026, "month": 8}).json()
    by_name = {i["name"]: i["value"] for i in month["items"]}
    assert by_name["Chứng khoán vợ"] == 5_000_000
    assert by_name["Chứng khoán chồng"] == 12_000_000


def test_system_items_recompute_month_over_month(client):
    """9/2026's account values should build on 8/2026's computed closing
    balance, even if 9/2026 is viewed before 8/2026 ever was."""
    chong, vo = _users(client)
    client.post("/assets", json={
        "year": 2026, "month": 7, "name": "Tài khoản vợ", "value": 100_000_000,
    })
    client.post("/transactions", json={
        "date": "2026-08-05", "type": "income", "amount": 10_000_000,
        "content": "Thu nhập vợ", "user_id": vo,
    })
    client.post("/transactions", json={
        "date": "2026-09-05", "type": "income", "amount": 2_000_000,
        "content": "Thu nhập vợ", "user_id": vo,
    })

    # Skip straight to September - August must be computed as a side effect.
    sep = client.get("/assets/month", params={"year": 2026, "month": 9}).json()
    vo_sep = next(i["value"] for i in sep["items"] if i["name"] == "Tài khoản vợ")
    assert vo_sep == 100_000_000 + 10_000_000 + 2_000_000

    aug = client.get("/assets/month", params={"year": 2026, "month": 8}).json()
    vo_aug = next(i["value"] for i in aug["items"] if i["name"] == "Tài khoản vợ")
    assert vo_aug == 100_000_000 + 10_000_000


def test_copy_previous_month_does_not_duplicate_system_items(client):
    """copy-previous into a system-era month must not create a second,
    unlocked row with the same name as a pinned system row."""
    client.get("/assets/month", params={"year": 2026, "month": 8})  # materialize system rows
    client.post("/assets/copy-previous", params={"year": 2026, "month": 9})

    sep = client.get("/assets/month", params={"year": 2026, "month": 9}).json()
    names = [i["name"] for i in sep["items"]]
    for n in SYSTEM_NAMES:
        assert names.count(n) == 1


def test_account_formula_includes_settled_savings_interest(client):
    """Tài khoản vợ/chồng = công thức cũ (prev_closing + net_held) CỘNG THÊM
    tiền lãi thực nhận (actual_interest) của các khoản tiết kiệm tất toán
    trong tháng đó - xem asset_service._ensure_system_items."""
    chong, vo = _users(client)
    client.post("/assets", json={
        "year": 2026, "month": 7, "name": "Tài khoản vợ", "value": 700_000_000,
    })

    dep = client.post("/savings", json={
        "name": "TK vợ", "start_date": "2026-01-01", "amount": 100_000_000,
        "term_value": 6, "term_unit": "month", "interest_rate": 5, "user_id": vo,
    }).json()
    client.put(f"/savings/{dep['id']}", json={
        "status": "settled", "settled_date": "2026-08-10", "actual_interest": 2_500_000,
    })

    month = client.get("/assets/month", params={"year": 2026, "month": 8}).json()
    by_name = {i["name"]: i["value"] for i in month["items"]}
    assert by_name["Tài khoản vợ"] == 700_000_000 + 2_500_000


def test_account_formula_ignores_interest_settled_outside_the_month(client):
    """A deposit's actual_interest only counts toward the month its
    settled_date actually falls in - not the month it was created/started."""
    chong, vo = _users(client)
    client.post("/assets", json={
        "year": 2026, "month": 7, "name": "Tài khoản vợ", "value": 700_000_000,
    })

    dep = client.post("/savings", json={
        "name": "TK vợ", "start_date": "2026-01-01", "amount": 100_000_000,
        "term_value": 6, "term_unit": "month", "interest_rate": 5, "user_id": vo,
    }).json()
    # Settled in September, not August.
    client.put(f"/savings/{dep['id']}", json={
        "status": "settled", "settled_date": "2026-09-05", "actual_interest": 2_500_000,
    })

    aug = client.get("/assets/month", params={"year": 2026, "month": 8}).json()
    by_name_aug = {i["name"]: i["value"] for i in aug["items"]}
    assert by_name_aug["Tài khoản vợ"] == 700_000_000

    sep = client.get("/assets/month", params={"year": 2026, "month": 9}).json()
    by_name_sep = {i["name"]: i["value"] for i in sep["items"]}
    assert by_name_sep["Tài khoản vợ"] == 700_000_000 + 2_500_000


def test_editing_past_month_transaction_cascades_to_later_month(client):
    """Trả lời câu hỏi của người dùng: sửa số liệu ở tháng trước (giao dịch
    hoặc lãi tiết kiệm) có tự động cập nhật cho các tháng sau không - CÓ, vì
    _ensure_system_items luôn tính lại (không skip-if-exists) và đệ quy lùi
    về tháng trước mỗi khi bất kỳ tháng nào được xem."""
    chong, vo = _users(client)
    client.post("/assets", json={
        "year": 2026, "month": 7, "name": "Tài khoản vợ", "value": 100_000_000,
    })
    tx = client.post("/transactions", json={
        "date": "2026-08-05", "type": "income", "amount": 10_000_000,
        "content": "Thu nhập vợ", "user_id": vo,
    }).json()

    # Materialize + cache both August and September with the original figure.
    sep_before = client.get("/assets/month", params={"year": 2026, "month": 9}).json()
    vo_sep_before = next(i["value"] for i in sep_before["items"] if i["name"] == "Tài khoản vợ")
    assert vo_sep_before == 100_000_000 + 10_000_000

    # Retroactively edit August's transaction (a value already "chốt" before).
    client.put(f"/transactions/{tx['id']}", json={"amount": 25_000_000})

    # September must reflect the edit automatically on next view - no manual
    # recompute step, no stale cached value.
    sep_after = client.get("/assets/month", params={"year": 2026, "month": 9}).json()
    vo_sep_after = next(i["value"] for i in sep_after["items"] if i["name"] == "Tài khoản vợ")
    assert vo_sep_after == 100_000_000 + 25_000_000

    aug = client.get("/assets/month", params={"year": 2026, "month": 8}).json()
    vo_aug = next(i["value"] for i in aug["items"] if i["name"] == "Tài khoản vợ")
    assert vo_aug == 100_000_000 + 25_000_000


def test_editing_past_settled_savings_interest_cascades_to_later_month(client):
    """Same cascade guarantee, but for a retroactive edit to a savings
    deposit's actual_interest (instead of a plain transaction)."""
    chong, vo = _users(client)
    client.post("/assets", json={
        "year": 2026, "month": 7, "name": "Tài khoản chồng", "value": 200_000_000,
    })
    dep = client.post("/savings", json={
        "name": "TK chồng", "start_date": "2026-01-01", "amount": 50_000_000,
        "term_value": 6, "term_unit": "month", "interest_rate": 5, "user_id": chong,
    }).json()
    client.put(f"/savings/{dep['id']}", json={
        "status": "settled", "settled_date": "2026-08-15", "actual_interest": 1_000_000,
    })

    sep_before = client.get("/assets/month", params={"year": 2026, "month": 9}).json()
    v_before = next(i["value"] for i in sep_before["items"] if i["name"] == "Tài khoản chồng")
    assert v_before == 200_000_000 + 1_000_000

    # Correct the actual_interest figure after the fact.
    client.put(f"/savings/{dep['id']}", json={"actual_interest": 1_800_000})

    sep_after = client.get("/assets/month", params={"year": 2026, "month": 9}).json()
    v_after = next(i["value"] for i in sep_after["items"] if i["name"] == "Tài khoản chồng")
    assert v_after == 200_000_000 + 1_800_000


def test_recompute_all_refreshes_stale_later_months_without_viewing_them(client):
    """"Tổng hợp lại tài sản" button: editing an earlier month's data, then
    calling /assets/recompute WITHOUT re-viewing every later month by hand,
    must still refresh every already-materialized later month in one shot."""
    chong, vo = _users(client)
    client.post("/assets", json={
        "year": 2026, "month": 7, "name": "Tài khoản vợ", "value": 100_000_000,
    })
    tx = client.post("/transactions", json={
        "date": "2026-08-05", "type": "income", "amount": 10_000_000,
        "content": "Thu nhập vợ", "user_id": vo,
    }).json()

    # Materialize August AND September by viewing September once.
    sep_before = client.get("/assets/month", params={"year": 2026, "month": 9}).json()
    vo_sep_before = next(i["value"] for i in sep_before["items"] if i["name"] == "Tài khoản vợ")
    assert vo_sep_before == 100_000_000 + 10_000_000

    # Retroactively edit August's transaction - no manual re-view of any
    # later month happens after this.
    client.put(f"/transactions/{tx['id']}", json={"amount": 40_000_000})

    r = client.post("/assets/recompute")
    assert r.status_code == 200

    # A plain GET of September afterwards confirms the recompute endpoint
    # actually persisted the refresh, not just returned a one-off value.
    sep_after = client.get("/assets/month", params={"year": 2026, "month": 9}).json()
    vo_sep_after = next(i["value"] for i in sep_after["items"] if i["name"] == "Tài khoản vợ")
    assert vo_sep_after == 100_000_000 + 40_000_000


def test_recompute_all_works_before_any_month_has_ever_been_viewed(client):
    """Calling the button as the very first action (no system month
    materialized yet) must not crash - falls back to computing "today"."""
    r = client.post("/assets/recompute")
    assert r.status_code == 200
    data = r.json()
    assert data["year"] >= 2026
