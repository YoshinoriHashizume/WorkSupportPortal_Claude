"""対応区分（S-204）の行への付与と一覧側（件数・並び・フィルタ・ペイロード・CSV）のテスト。

test-design.md TC-SRR-A-001〜005 / TC-SRR-C-001〜006。
"""

from __future__ import annotations

import csv
import io
from datetime import date

from application.inventory_order_alert.domain.value_objects.confirmation import STATUS_CHOICES
from application.inventory_order_alert.domain.value_objects.export_csv import EXPORT_COLUMNS, render_export_csv
from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    QUADRANT_DORMANT_STOCK,
    QUADRANT_LOW_FLOW_NO_INCOMING,
    QUADRANT_NORMAL_FLOW,
)
from application.inventory_order_alert.domain.value_objects.list_client_data import build_list_client_payload
from application.inventory_order_alert.domain.value_objects.list_filter import build_filter_options
from application.inventory_order_alert.domain.value_objects.list_query import parse_list_query
from application.inventory_order_alert.domain.value_objects.list_rows import filter_summary_rows, sort_summary_rows
from application.inventory_order_alert.domain.value_objects.row_counts import count_rows
from application.inventory_order_alert.domain.value_objects.row_display import row_alert_class
from application.inventory_order_alert.domain.value_objects.stockout_risk import (
    RESPONSE_DELIVERY_CHECK,
    RESPONSE_NONE,
    RESPONSE_ORDER_NEEDED,
    RESPONSE_ORDER_OVERDUE,
    RESPONSE_WATCH,
    attach_response_class,
)
from application.inventory_order_alert.domain.value_objects.table_display import (
    SORT_ONLY_COLUMNS,
    SORTABLE_COLUMNS,
    SortSpec,
    sort_rows,
)

TODAY = date(2026, 9, 18)


def _row(
    response: str | None,
    *,
    item_cd: str = "X",
    quadrant: str = QUADRANT_NORMAL_FLOW,
    qty: int = 0,
    status: str = "未確認",
    stockout_date: str = "",
    order_deadline: str = "",
    **extra,
):
    """判定済みの行（取込時に `attach_response_class` が付けた形）を作る。"""
    row: dict[str, object] = {
        "cust_code": "100",
        "cust_name": "得意先",
        "cust_chrg_psn_cd": "A01",
        "item_cd": item_cd,
        "flow_quadrant": quadrant,
        "flow_quadrant_key": "normal-flow" if quadrant == QUADRANT_NORMAL_FLOW else "low-flow-no-incoming",
        "post_shipment_total_qty": qty,
        "confirmation_status": status,
        "last_incoming_date": "",
        "last_ship_date": "2026/06/15",
    }
    if response is not None:
        row.update(
            {
                "response_class": response,
                "response_class_key": {
                    RESPONSE_ORDER_OVERDUE: "order-overdue",
                    RESPONSE_DELIVERY_CHECK: "delivery-check",
                    RESPONSE_ORDER_NEEDED: "order-needed",
                    RESPONSE_WATCH: "watch",
                    RESPONSE_NONE: "none",
                }[response],
                "response_reasons": ["在庫切れ 2026/10/10", "発注期限 2026/10/02"] if response == RESPONSE_ORDER_OVERDUE else [],
                "stockout_date": stockout_date,
                "order_deadline": order_deadline,
                "below_safety_stock": False,
                "safety_stock": 0.0,
                "overdue_order_qty": 0,
                "overdue_order_count": 0,
                "lead_time_days": 5,
                "lead_time_source": "master",
                "ordering_method": "手動発注",
            }
        )
    row.update(extra)
    return row


# --- TC-SRR-A-001〜005: 行への付与 ---


def _unit_row(item_cd: str, *, internal: str = "IN-1", daily: list[dict[str, object]] | None = None, **extra):
    row: dict[str, object] = {
        "cust_code": "100",
        "item_cd": item_cd,
        "internal_item_cd": internal,
        "level1_item_cd": "X-9065",
        "level1_vend_cd": "9065",
        "lead_time_days": 5,
        "lead_time_source": "master",
        "demand_forecast_stock_total": 100,
        "unconfirmed_order_daily": daily if daily is not None else [{"date": "2026-10-10", "qty": 160}],
        "open_purchase_orders": [],
    }
    row.update(extra)
    return row


def test_a001_one_assessment_per_reconciliation_unit():
    """照合単位（同じ内作品番 × 仕入先）の行には同じ判定が入る。"""
    rows = [_unit_row("ITEM-A"), _unit_row("ITEM-B")]

    enriched = attach_response_class(rows, TODAY)

    assert {row["response_class"] for row in enriched} == {RESPONSE_ORDER_NEEDED}
    assert {row["stockout_date"] for row in enriched} == {"2026/10/10"}


def test_a002_attached_keys():
    [enriched] = attach_response_class([_unit_row("ITEM-A")], TODAY)

    assert enriched["response_class"] == RESPONSE_ORDER_NEEDED
    assert enriched["response_class_key"] == "order-needed"
    assert enriched["response_reasons"][0] == "在庫切れ 2026/10/10"
    assert enriched["stockout_date"] == "2026/10/10"
    assert enriched["order_deadline"] == "2026/10/05"  # 在庫切れ日 − リードタイム 5 日
    assert enriched["below_safety_stock"] is False
    assert enriched["overdue_order_qty"] == 0


def test_a003_legacy_keys_are_not_attached():
    [enriched] = attach_response_class([_unit_row("ITEM-A")], TODAY)

    for key in ("stockout_risk", "stockout_risk_reasons", "days_until_stockout", "shortage_qty", "replenishment_qty"):
        assert key not in enriched


def test_a004_rows_without_materials_fall_back_to_none():
    """旧スナップショット（内示も発注残もない行）は例外にならず対象外。"""
    [enriched] = attach_response_class([{"cust_code": "100", "item_cd": "ITEM-A"}], TODAY)

    assert enriched["response_class"] == RESPONSE_NONE


def test_a005_input_rows_are_not_mutated():
    rows = [_unit_row("ITEM-A")]
    original = dict(rows[0])

    attach_response_class(rows, TODAY)

    assert rows[0] == original


# --- TC-SRR-C-001: 件数サマリ ---


def test_c001_counts_by_response_class():
    rows = [
        _row(RESPONSE_ORDER_OVERDUE),
        _row(RESPONSE_ORDER_OVERDUE),
        _row(RESPONSE_DELIVERY_CHECK),
        _row(RESPONSE_ORDER_NEEDED),
        _row(RESPONSE_WATCH),
        _row(RESPONSE_NONE),
        _row(None),  # 旧スナップショット
    ]

    counts = count_rows(rows)

    assert (counts.order_overdue, counts.delivery_check, counts.order_needed, counts.watch, counts.none_response) == (2, 1, 1, 1, 2)
    assert counts.by_response_class == {"発注遅れ": 2, "納期確認": 1, "要発注": 1, "要監視": 1, "対象外": 2}
    assert counts.total == 7


# --- TC-SRR-C-002: 既定の並び ---


def test_c002_default_sort_is_response_then_deadline_then_stockout_date():
    rows = [
        _row(RESPONSE_NONE, item_cd="none"),
        _row(RESPONSE_WATCH, item_cd="watch"),
        _row(RESPONSE_ORDER_NEEDED, item_cd="needed-far", order_deadline="2026/12/01", stockout_date="2026/12/06"),
        _row(RESPONSE_ORDER_NEEDED, item_cd="needed-near", order_deadline="2026/10/01", stockout_date="2026/10/06"),
        _row(RESPONSE_ORDER_OVERDUE, item_cd="overdue-b", order_deadline="2026/09/15", stockout_date="2026/09/25"),
        _row(RESPONSE_ORDER_OVERDUE, item_cd="overdue-a", order_deadline="2026/09/01", stockout_date="2026/09/20"),
        _row(None, item_cd="legacy"),
    ]

    ordered = [row["item_cd"] for row in sort_summary_rows(rows)]

    assert ordered[:2] == ["overdue-a", "overdue-b"]
    assert ordered[2:4] == ["needed-near", "needed-far"]
    assert ordered[4] == "watch"
    assert set(ordered[5:]) == {"none", "legacy"}


# --- TC-SRR-C-005: 一覧の列と並べ替え ---


def test_c005_sortable_columns_and_date_sorting():
    rows = [
        _row(RESPONSE_ORDER_NEEDED, item_cd="a", stockout_date=""),
        _row(RESPONSE_ORDER_OVERDUE, item_cd="b", stockout_date="2026/09/25"),
        _row(RESPONSE_ORDER_NEEDED, item_cd="c", stockout_date="2026/10/06"),
    ]

    by_response = sort_rows(rows, sort_specs=(SortSpec("response_class", "asc"),))
    assert [r["item_cd"] for r in by_response] == ["b", "c", "a"]  # 同順位は在庫切れ日、空は末尾

    by_stockout_desc = sort_rows(rows, sort_specs=(SortSpec("stockout_date", "desc"),))
    assert [r["item_cd"] for r in by_stockout_desc] == ["c", "b", "a"]  # 空は昇順・降順とも末尾

    assert SORTABLE_COLUMNS[:4] == (
        ("response_class", "対応区分"),
        ("stockout_date", "在庫切れ日"),
        ("order_deadline", "発注期限"),
        ("flow_quadrant", "流動区分"),
    )
    assert ("months_of_stock", "在庫月数") in SORT_ONLY_COLUMNS


# --- TC-SRR-C-003: フィルタ ---


def test_c003_filter_by_response_class_and_ordering_method():
    rows = [
        _row(RESPONSE_ORDER_NEEDED, item_cd="n"),
        _row(RESPONSE_DELIVERY_CHECK, item_cd="d", ordering_method="MRP 発注"),
        _row(None, item_cd="legacy"),
    ]

    query = parse_list_query({"response_class": "order-needed"}, today=TODAY)
    assert query.response_class == "order-needed"
    assert [r["item_cd"] for r in filter_summary_rows(rows, query)] == ["n"]

    query = parse_list_query({"response_class": "none"}, today=TODAY)
    assert [r["item_cd"] for r in filter_summary_rows(rows, query)] == ["legacy"]  # 旧行は対象外

    query = parse_list_query({"ordering_method": "manual"}, today=TODAY)
    assert query.ordering_method == "manual"
    assert [r["item_cd"] for r in filter_summary_rows(rows, query)] == ["n"]

    assert parse_list_query({"response_class": "foo", "ordering_method": "bar"}, today=TODAY).response_class == ""
    assert parse_list_query({"response_class": "要発注"}, today=TODAY).response_class == "order-needed"
    # 旧キー・旧称も受ける（REQ-SRR-F-008）
    assert parse_list_query({"stockout_risk": "danger"}, today=TODAY).response_class == "order-overdue"
    assert parse_list_query({"stockout_risk": "注意"}, today=TODAY).response_class == "order-needed"


# --- ペイロード ---


def test_payload_carries_response_class_fields():
    rows = [
        _row(RESPONSE_ORDER_OVERDUE, item_cd="d", stockout_date="2026/10/10", order_deadline="2026/10/02", overdue_order_qty=300, overdue_order_count=2),
        _row(None, item_cd="legacy"),
    ]
    payload = build_list_client_payload(all_rows=rows, filter_options=build_filter_options(rows), confirmation_status_choices=list(STATUS_CHOICES))

    overdue = payload["rows"][0]
    assert overdue["responseClass"] == "発注遅れ"
    assert overdue["responseClassKey"] == "order-overdue"
    assert overdue["responseReasons"] == ["在庫切れ 2026/10/10", "発注期限 2026/10/02"]
    assert overdue["stockoutDate"] == "2026/10/10"
    assert overdue["orderDeadline"] == "2026/10/02"
    assert overdue["overdueOrderQty"] == 300
    assert overdue["overdueOrderCount"] == 2
    assert overdue["belowSafetyStock"] is False
    assert overdue["leadTimeDays"] == 5
    assert overdue["orderingMethodKey"] == "manual"
    assert overdue["alertRowClass"] == "response-order-overdue"
    assert overdue["display"]["response_class"] == "発注遅れ"

    legacy = payload["rows"][1]
    assert legacy["responseClass"] == "対象外"
    assert legacy["responseClassKey"] == "none"
    assert legacy["display"]["response_class"] == ""

    assert payload["responseClassOrder"] == ["order-overdue", "delivery-check", "order-needed", "watch", "none"]
    assert payload["responseClassLabels"] == {
        "order-overdue": "発注遅れ",
        "delivery-check": "納期確認",
        "order-needed": "要発注",
        "watch": "要監視",
        "none": "対象外",
    }
    assert payload["defaultSortSpecs"][0] == {"column": "response_class", "direction": "asc"}


# --- TC-SRR-C-006: 行の色 ---


def test_c006_row_alert_class_priority():
    assert row_alert_class(_row(RESPONSE_ORDER_OVERDUE, quadrant=QUADRANT_LOW_FLOW_NO_INCOMING)) == "response-order-overdue"
    assert row_alert_class(_row(RESPONSE_DELIVERY_CHECK)) == "response-delivery-check"
    assert row_alert_class(_row(RESPONSE_ORDER_NEEDED)) == "response-order-needed"
    # 要監視・対象外は流動区分の色を使わない（行の色は対応区分のみ）
    assert row_alert_class(_row(RESPONSE_WATCH, quadrant=QUADRANT_DORMANT_STOCK)) == "response-watch"
    assert row_alert_class(_row(RESPONSE_NONE)) == "response-none"
    assert row_alert_class(_row(None, quadrant=QUADRANT_DORMANT_STOCK)) == "response-none"
    assert row_alert_class(_row(RESPONSE_ORDER_OVERDUE, status="確認済み")) == "確認済"


# --- TC-SRR-C-004: CSV ---


def test_c004_csv_appends_response_class_columns():
    columns = [column for column, _label in EXPORT_COLUMNS]
    assert columns[28:] == [
        "response_class",
        "response_reasons",
        "stockout_date",
        "order_deadline",
        "overdue_order_qty",
        "below_safety_stock",
        "safety_stock",
        "lead_time_days",
        "ordering_method",
    ]
    assert [label for _c, label in EXPORT_COLUMNS[28:]] == [
        "対応区分",
        "対応区分の理由",
        "在庫切れ日",
        "発注期限",
        "納期遅れの発注残数量",
        "安全在庫割れ",
        "安全在庫",
        "リードタイム",
        "発注方式",
    ]

    rows = [
        _row(RESPONSE_ORDER_OVERDUE, stockout_date="2026/10/10", order_deadline="2026/10/02", overdue_order_qty=300, below_safety_stock=True),
        _row(None),
    ]
    payload = render_export_csv(rows).decode("utf-8-sig")
    records = list(csv.DictReader(io.StringIO(payload)))

    assert records[0]["対応区分"] == "発注遅れ"
    assert records[0]["対応区分の理由"] == "在庫切れ 2026/10/10・発注期限 2026/10/02"
    assert records[0]["在庫切れ日"] == "2026/10/10"
    assert records[0]["発注期限"] == "2026/10/02"
    assert records[0]["納期遅れの発注残数量"] == "300"
    assert records[0]["安全在庫割れ"] == "あり"
    assert records[0]["発注方式"] == "手動発注"
    # 旧スナップショットは対象外として出る
    assert records[1]["対応区分"] == "対象外"
    assert records[1]["対応区分の理由"] == ""
    assert records[1]["安全在庫割れ"] == ""
