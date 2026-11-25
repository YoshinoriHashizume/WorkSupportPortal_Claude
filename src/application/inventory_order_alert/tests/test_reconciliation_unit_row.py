"""照合単位行（T-213）へのまとめ・代表得意先（V-241）・得意先別内訳（V-242）・確認記録のまとめ（spec/13）。

test-design.md TC-RUR-D-001〜037。
"""

from __future__ import annotations

import copy
from datetime import date, datetime

from application.inventory_order_alert.domain.value_objects.confirmation import (
    ConfirmationRecord,
    MemoEntryRecord,
    attach_confirmation_fields,
)
from application.inventory_order_alert.domain.value_objects.flow_quadrant import REFERENCE_FLOW_SELECTION
from application.inventory_order_alert.domain.value_objects.list_query import ListQuery
from application.inventory_order_alert.domain.value_objects.list_rows import apply_flow_quadrants_to_rows
from application.inventory_order_alert.domain.value_objects.reconciliation_unit_row import (
    build_reconciliation_unit_rows,
    merge_memo_entries,
    select_representative,
    unit_confirmation,
)

AS_OF = date(2026, 11, 25)


def _row(cust_code: str, item_cd: str, **overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "cust_code": cust_code,
        "cust_name": f"得意先{cust_code}",
        "cust_chrg_psn_cd": "22",
        "item_cd": item_cd,
        "internal_item_cd": item_cd,
        "level1_item_cd": f"{item_cd}-9028",
        "level1_vend_cd": "9028",
        "level1_vend_name": "大一螺子",
        "stock_qty": "",
        "mari_stock_qty": 0,
        "stock_location_detail": "",
        "stock_location_summary": "",
        "last_incoming_date": "",
        "last_ship_date": "",
        "post_shipment_count": 0,
        "post_shipment_total_qty": 0,
        "daily_shipment": [],
        "daily_incoming": [],
        "unconfirmed_order_daily": [],
        "unconfirmed_order_trend": [],
        "shipment_trend": [],
        "incoming_trend": [],
        "open_purchase_orders": [],
        "planned_incoming": [],
        "ordering_method": "MRP 発注",
        "response_class": "対象外",
        "response_class_key": "none",
        "stockout_date": "",
        "order_deadline": "",
        "response_reasons": [],
        "process_chain": [],
        "lead_time_days": 30,
        "lead_time_source": "master",
    }
    row.update(overrides)
    return row


def _unit_a_rows() -> list[dict[str, object]]:
    """同じ得意先品番 X を得意先 104（内示多い）と 176（内示少ない）で受ける。"""
    common = {
        "stock_qty": "11341",
        "mari_stock_qty": 11000,
        "stock_location_detail": "2E4-01-1=341@20161228;2A4-02-1=11000@20261106",
        "daily_incoming": [{"date": "2026-11-06", "qty": 36000}],
        "incoming_trend": [{"month": "2026-11", "qty": 36000}],
        "last_incoming_date": "2026/11/06",
        "response_class": "発注遅れ",
        "response_class_key": "order-overdue",
        "stockout_date": "2026/12/10",
        "order_deadline": "2026/11/10",
        "response_reasons": ["在庫切れ 2026/12/10", "発注期限 2026/11/10"],
    }
    return [
        _row(
            "104",
            "X",
            cust_name="トヨタ紡織株式会社",
            last_ship_date="2026/11/26",
            post_shipment_count=10,
            post_shipment_total_qty=1000,
            daily_shipment=[{"date": "2026-11-24", "qty": 2000}],
            shipment_trend=[{"month": "2026-11", "qty": 2000}],
            unconfirmed_order_daily=[{"date": "2026-11-26", "qty": 1428}],
            unconfirmed_order_trend=[{"month": "2026-11", "qty": 30000}],
            **common,
        ),
        _row(
            "176",
            "X",
            cust_name="秋田工業株式会社",
            last_ship_date="2026/03/02",
            post_shipment_count=2,
            post_shipment_total_qty=20,
            daily_shipment=[{"date": "2026-11-24", "qty": 10}],
            shipment_trend=[{"month": "2026-11", "qty": 10}],
            unconfirmed_order_daily=[{"date": "2026-11-26", "qty": 10}],
            unconfirmed_order_trend=[{"month": "2026-11", "qty": 300}],
            **common,
        ),
    ]


def _unit_b_rows() -> list[dict[str, object]]:
    """内作品番 IN-1 × 9065 を共有する得意先品番 P・Q を得意先 308 で受ける。"""
    shared = {"internal_item_cd": "IN-1", "level1_item_cd": "IN-1-9065", "level1_vend_cd": "9065", "level1_vend_name": "仕入先9065"}
    return [
        _row("308", "P", stock_qty="100", unconfirmed_order_trend=[{"month": "2026-12", "qty": 100}], **shared),
        _row("308", "Q", stock_qty="", unconfirmed_order_trend=[{"month": "2026-12", "qty": 500}], **shared),
    ]


def _single_s_row() -> dict[str, object]:
    return _row("150", "S", stock_qty="5")


def _by_item(unit_rows: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    return {str(row["item_cd"]): row for row in unit_rows}


# --- TC-RUR-D-001〜002: 行のまとめ ---


def test_d001_one_row_per_reconciliation_unit():
    rows = _unit_a_rows() + _unit_b_rows() + [_single_s_row()]

    assert len(build_reconciliation_unit_rows(rows)) == 3


def test_d002_rows_without_item_cd_are_not_merged():
    rows = [_row("100", ""), _row("200", "")]

    assert len(build_reconciliation_unit_rows(rows)) == 2


# --- TC-RUR-D-003〜005: 代表得意先 ---


def test_d003_representative_is_the_customer_with_the_largest_demand():
    [unit] = build_reconciliation_unit_rows(_unit_a_rows())

    assert unit["cust_code"] == "104"
    assert unit["cust_codes"] == ["104", "176"]


def test_d004_tie_goes_to_the_smaller_customer_code():
    rows = _unit_a_rows()
    for row in rows:
        row["unconfirmed_order_trend"] = []

    [unit] = build_reconciliation_unit_rows(list(reversed(rows)))

    assert unit["cust_code"] == "104"


def test_d005_representative_item_is_the_one_with_the_largest_demand():
    [unit] = build_reconciliation_unit_rows(_unit_b_rows())

    assert unit["item_cd"] == "Q"
    assert unit["item_cds"][0] == "Q"
    assert select_representative(_unit_b_rows())["item_cd"] == "Q"


# --- TC-RUR-D-006〜015: 合算 ---


def test_d006_stock_is_summed_without_counting_the_same_item_twice():
    [unit] = build_reconciliation_unit_rows(_unit_a_rows())

    assert float(unit["stock_qty"]) == 11341
    assert unit["mari_stock_qty"] == 11000


def test_d007_stock_stays_empty_when_every_item_is_empty():
    rows = _unit_b_rows()
    rows[0]["stock_qty"] = ""

    [unit] = build_reconciliation_unit_rows(rows)

    assert unit["stock_qty"] == ""


def test_d008_stock_sums_the_items_that_have_a_value():
    [unit] = build_reconciliation_unit_rows(_unit_b_rows())

    assert float(unit["stock_qty"]) == 100


def test_d009_last_dates_are_the_newest():
    [unit] = build_reconciliation_unit_rows(_unit_a_rows())

    assert unit["last_ship_date"] == "2026/11/26"
    assert unit["last_incoming_date"] == "2026/11/06"


def test_d010_shipment_counts_are_summed():
    [unit] = build_reconciliation_unit_rows(_unit_a_rows())

    assert unit["post_shipment_count"] == 12
    assert unit["post_shipment_total_qty"] == 1020


def _series(points: object) -> dict[str, int]:
    return {str(point.get("date") or point.get("month")): int(point["qty"]) for point in points}  # type: ignore[union-attr]


def test_d011_daily_shipment_is_summed_per_day():
    [unit] = build_reconciliation_unit_rows(_unit_a_rows())

    assert _series(unit["daily_shipment"])["2026-11-24"] == 2010


def test_d012_daily_incoming_is_not_counted_twice():
    [unit] = build_reconciliation_unit_rows(_unit_a_rows())

    assert _series(unit["daily_incoming"])["2026-11-06"] == 36000
    assert _series(unit["incoming_trend"])["2026-11"] == 36000


def test_d013_daily_demand_is_summed_across_customers():
    [unit] = build_reconciliation_unit_rows(_unit_a_rows())

    assert _series(unit["unconfirmed_order_daily"])["2026-11-26"] == 1438


def test_d014_monthly_demand_is_summed():
    [unit] = build_reconciliation_unit_rows(_unit_a_rows())

    assert _series(unit["unconfirmed_order_trend"])["2026-11"] == 30300


def test_d015_open_orders_are_not_counted_twice():
    order = {"order_cd": "PO-1", "item_cd": "X-9028", "vend_cd": "9028", "due_date": "2026/12/01", "remaining_qty": 300}
    rows = _unit_a_rows()
    for row in rows:
        row["open_purchase_orders"] = [dict(order)]
        row["planned_incoming"] = [{"date": "2026-12-01", "qty": 300}]

    [unit] = build_reconciliation_unit_rows(rows)

    assert len(unit["open_purchase_orders"]) == 1
    assert _series(unit["planned_incoming"])["2026-12-01"] == 300


# --- TC-RUR-D-016〜021: 代表の値・一覧・内訳 ---


def test_d016_judgement_comes_from_the_representative_row():
    [unit] = build_reconciliation_unit_rows(_unit_a_rows())

    assert unit["response_class"] == "発注遅れ"
    assert unit["stockout_date"] == "2026/12/10"
    assert unit["order_deadline"] == "2026/11/10"


def test_d017_lists_start_with_the_representative_then_customer_code_order():
    rows = _unit_a_rows()
    rows[1]["unconfirmed_order_trend"] = [{"month": "2026-11", "qty": 99999}]  # 176 が代表
    rows.append(_row("150", "X", stock_qty="11341"))

    [unit] = build_reconciliation_unit_rows(rows)

    assert unit["cust_codes"] == ["176", "104", "150"]


def test_d018_lists_drop_duplicates():
    [unit] = build_reconciliation_unit_rows(_unit_a_rows())

    assert unit["cust_chrg_psn_cds"] == ["22"]
    assert unit["item_cds"] == ["X"]
    assert unit["level1_vend_cds"] == ["9028"]


def test_d019_customer_breakdown_has_one_entry_per_customer_and_item():
    [unit] = build_reconciliation_unit_rows(_unit_a_rows())

    breakdown = unit["customer_breakdown"]
    assert [entry["cust_code"] for entry in breakdown] == ["104", "176"]
    first = breakdown[0]
    for key in (
        "cust_code",
        "cust_name",
        "item_cd",
        "cust_chrg_psn_cd",
        "unconfirmed_order_trend",
        "shipment_trend",
        "post_shipment_total_qty",
        "last_ship_date",
    ):
        assert key in first
    assert first["cust_name"] == "トヨタ紡織株式会社"


def test_d020_single_row_has_one_breakdown_entry():
    [unit] = build_reconciliation_unit_rows([_single_s_row()])

    assert unit["unit_member_count"] == 1
    assert len(unit["customer_breakdown"]) == 1


def test_d021_manual_ordering_wins_inside_the_unit():
    rows = _unit_a_rows()
    rows[1]["ordering_method"] = "手動発注"

    [unit] = build_reconciliation_unit_rows(rows)

    assert unit["ordering_method"] == "手動発注"


# --- TC-RUR-D-022: 流動区分は合算で判定する ---


def _with_flow(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return apply_flow_quadrants_to_rows(
        rows,
        as_of_date=AS_OF,
        query=ListQuery(as_of_date=AS_OF, flow_selection=REFERENCE_FLOW_SELECTION),
    )


def test_d022_flow_quadrant_is_judged_on_the_merged_values():
    rows = _unit_a_rows()
    rows[1]["last_ship_date"] = "2024/01/10"  # 176 だけ出荷が止まっている
    per_row = {row["cust_code"]: row["flow_quadrant"] for row in _with_flow(copy.deepcopy(rows))}
    assert per_row["104"] != per_row["176"]  # 得意先ごとなら区分が分かれる

    [unit] = _with_flow(build_reconciliation_unit_rows(rows))

    assert unit["flow_quadrant"] == per_row["104"]


# --- TC-RUR-D-023〜025: 入力・旧データ・壊れた値 ---


def test_d023_input_rows_are_not_modified():
    rows = _unit_a_rows()
    before = copy.deepcopy(rows)

    build_reconciliation_unit_rows(rows)

    assert rows == before


def test_d024_old_snapshot_rows_without_new_keys_are_merged():
    rows = _unit_a_rows()
    for row in rows:
        row.pop("reconciliation_unit_key", None)
        row.pop("ordering_method", None)

    assert len(build_reconciliation_unit_rows(rows)) == 1


def test_d025_broken_values_do_not_raise():
    rows = _unit_a_rows()
    rows[0]["daily_shipment"] = None
    rows[0]["stock_qty"] = "abc"
    rows[1]["unconfirmed_order_trend"] = "x"

    [unit] = build_reconciliation_unit_rows(rows)

    assert _series(unit["daily_shipment"])["2026-11-24"] == 10


# --- TC-RUR-D-030〜037: 確認状態・確認メモ ---


def _record(item_cd: str, status: str, updated: datetime, *, entries: tuple[MemoEntryRecord, ...] = ()) -> ConfirmationRecord:
    return ConfirmationRecord(
        cust_code="",
        item_cd=item_cd,
        status=status,
        memo="",
        confirmed_flow_quadrant="通常流動品",
        confirmed_at=updated,
        confirmed_by="u1",
        updated_at=updated,
        memo_entries=entries,
    )


def _memo(content: str, created: datetime, *, group: str = "", entry_id: int = 0) -> MemoEntryRecord:
    return MemoEntryRecord(created_at=created, created_by="u1", content=content, entry_group=group, entry_id=entry_id)


def test_d030_no_record_means_unconfirmed():
    assert unit_confirmation(["X"], {}) is None


def test_d031_the_newest_record_wins():
    records = {
        "P": _record("P", "confirmed", datetime(2026, 11, 20)),
        "Q": _record("Q", "in_progress", datetime(2026, 11, 24)),
    }

    assert unit_confirmation(["P", "Q"], records).status == "in_progress"


def test_d032_split_units_keep_their_own_records():
    records = {
        "P": _record("P", "confirmed", datetime(2026, 11, 20)),
        "Q": _record("Q", "confirmed", datetime(2026, 11, 20)),
    }

    assert unit_confirmation(["P"], records).status == "confirmed"
    assert unit_confirmation(["Q"], records).status == "confirmed"


def test_d033_added_item_inherits_the_existing_record():
    records = {"P": _record("P", "confirmed", datetime(2026, 11, 20))}

    assert unit_confirmation(["P", "R"], records).status == "confirmed"


def test_d034_copied_memos_are_shown_once():
    shared = _memo("仕入先に確認", datetime(2026, 11, 24), group="g-1", entry_id=1)
    copied = _memo("仕入先に確認", datetime(2026, 11, 24), group="g-1", entry_id=2)
    records = [
        _record("P", "confirmed", datetime(2026, 11, 24), entries=(shared,)),
        _record("Q", "confirmed", datetime(2026, 11, 24), entries=(copied,)),
    ]

    assert len(merge_memo_entries(records)) == 1


def test_d035_memos_before_migration_are_kept_separately():
    records = [
        _record("P", "confirmed", datetime(2026, 11, 24), entries=(_memo("同じ", datetime(2026, 11, 1), entry_id=1),)),
        _record("Q", "confirmed", datetime(2026, 11, 24), entries=(_memo("同じ", datetime(2026, 11, 1), entry_id=2),)),
    ]

    assert len(merge_memo_entries(records)) == 2


def test_d036_memos_are_newest_first():
    records = [
        _record(
            "P",
            "confirmed",
            datetime(2026, 11, 24),
            entries=(
                _memo("a", datetime(2026, 11, 20), entry_id=1),
                _memo("b", datetime(2026, 11, 24), entry_id=2),
                _memo("c", datetime(2026, 11, 22), entry_id=3),
            ),
        )
    ]

    assert [entry.content for entry in merge_memo_entries(records)] == ["b", "c", "a"]


def test_d037_unit_row_gets_the_confirmation_of_its_items():
    [unit] = build_reconciliation_unit_rows(_unit_a_rows())
    records = {"X": _record("X", "confirmed", datetime(2026, 11, 24))}

    [enriched] = attach_confirmation_fields([unit], records)

    assert enriched["confirmation_status"] == "確認済み"
