"""在庫切れリスクの一覧側（件数・ソート・フィルタ・ペイロード・CSV）のテスト（TC-SOR-D-060〜064）。"""

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
    RISK_CAUTION,
    RISK_DANGER,
    RISK_NONE,
    RISK_WATCH,
)
from application.inventory_order_alert.domain.value_objects.table_display import (
    SORT_ONLY_COLUMNS,
    SORTABLE_COLUMNS,
    SortSpec,
    sort_rows,
)

TODAY = date(2026, 9, 17)


def _row(risk: str | None, *, item_cd: str = "X", days: int | None = 10, quadrant: str = QUADRANT_NORMAL_FLOW, qty: int = 0, status: str = "未確認", **extra):
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
    if risk is not None:
        row.update(
            {
                "stockout_risk": risk,
                "stockout_risk_reasons": ["発注忘れの可能性", "リードタイム内"] if risk == RISK_DANGER else [],
                "days_until_stockout": days,
                "shortage_qty": 200,
                "replenishment_qty": 0,
                "replenishment_later_qty": 30,
                "replenishment_earliest_due": "",
                "replenishment_has_overdue": False,
                "replenishment_unknown": False,
                "lead_time_days": 5,
                "lead_time_source": "master",
                "ordering_method": "手動発注",
            }
        )
    row.update(extra)
    return row


# --- TC-SOR-D-060: 件数サマリ ---


def test_d060_counts_by_stockout_risk():
    rows = [_row(RISK_DANGER), _row(RISK_DANGER), _row(RISK_CAUTION), _row(RISK_WATCH), _row(RISK_NONE), _row(None)]

    counts = count_rows(rows)

    assert (counts.danger, counts.caution, counts.watch, counts.none_risk) == (2, 1, 2, 1)
    assert counts.by_stockout_risk == {"危険": 2, "注意": 1, "監視": 2, "対象外": 1}
    assert counts.total == 6


# --- TC-SOR-D-061: 既定ソート ---


def test_d061_default_sort_is_risk_then_days_then_flow_quadrant():
    rows = [
        _row(RISK_NONE, item_cd="none"),
        _row(RISK_WATCH, item_cd="watch", days=None),
        _row(RISK_CAUTION, item_cd="caution-far", days=90),
        _row(RISK_CAUTION, item_cd="caution-near", days=20),
        _row(RISK_DANGER, item_cd="danger-normal", days=0, quadrant=QUADRANT_NORMAL_FLOW),
        _row(RISK_DANGER, item_cd="danger-no-incoming", days=0, quadrant=QUADRANT_LOW_FLOW_NO_INCOMING),
        _row(None, item_cd="legacy"),
    ]

    ordered = [row["item_cd"] for row in sort_summary_rows(rows)]

    assert ordered[:2] == ["danger-no-incoming", "danger-normal"]
    assert ordered[2:4] == ["caution-near", "caution-far"]
    assert set(ordered[4:6]) == {"watch", "legacy"}
    assert ordered[-1] == "none"


def test_d061_table_display_sorts_by_stockout_risk_and_days():
    rows = [_row(RISK_CAUTION, item_cd="a", days=None), _row(RISK_DANGER, item_cd="b", days=5), _row(RISK_CAUTION, item_cd="c", days=1)]

    by_risk = sort_rows(rows, sort_specs=(SortSpec("stockout_risk", "asc"),))
    assert [r["item_cd"] for r in by_risk] == ["b", "c", "a"]

    by_days_desc = sort_rows(rows, sort_specs=(SortSpec("days_until_stockout", "desc"),))
    assert [r["item_cd"] for r in by_days_desc] == ["b", "c", "a"]  # 空は末尾

    assert SORTABLE_COLUMNS[0] == ("stockout_risk", "在庫切れリスク")
    assert SORTABLE_COLUMNS[1] == ("flow_quadrant", "流動区分")
    assert ("days_until_stockout", "猶予日数") in SORT_ONLY_COLUMNS


# --- TC-SOR-D-062: フィルタ ---


def test_d062_filter_by_stockout_risk_and_ordering_method():
    rows = [_row(RISK_DANGER, item_cd="d"), _row(RISK_CAUTION, item_cd="c", ordering_method="MRP 発注"), _row(None, item_cd="legacy")]

    query = parse_list_query({"stockout_risk": "danger"}, today=TODAY)
    assert query.stockout_risk == "danger"
    assert [r["item_cd"] for r in filter_summary_rows(rows, query)] == ["d"]

    query = parse_list_query({"stockout_risk": "watch"}, today=TODAY)
    assert [r["item_cd"] for r in filter_summary_rows(rows, query)] == ["legacy"]  # 旧行は監視

    query = parse_list_query({"ordering_method": "manual"}, today=TODAY)
    assert query.ordering_method == "manual"
    assert [r["item_cd"] for r in filter_summary_rows(rows, query)] == ["d"]

    assert parse_list_query({"stockout_risk": "foo", "ordering_method": "bar"}, today=TODAY).stockout_risk == ""
    assert parse_list_query({"stockout_risk": "危険"}, today=TODAY).stockout_risk == "danger"


# --- TC-SOR-D-063: ペイロード ---


def test_d063_payload_carries_stockout_risk_fields():
    rows = [_row(RISK_DANGER, item_cd="d", days=0), _row(None, item_cd="legacy")]
    payload = build_list_client_payload(all_rows=rows, filter_options=build_filter_options(rows), confirmation_status_choices=list(STATUS_CHOICES))

    danger = payload["rows"][0]
    assert danger["stockoutRisk"] == "危険"
    assert danger["stockoutRiskKey"] == "danger"
    assert danger["stockoutRiskReasons"] == ["発注忘れの可能性", "リードタイム内"]
    assert danger["daysUntilStockout"] == 0
    assert danger["shortageQty"] == 200
    assert danger["replenishment"] == {"qty": 0, "laterQty": 30, "staleQty": 0, "earliestDue": "", "hasOverdue": False, "unknown": False}
    assert danger["leadTimeDays"] == 5
    assert danger["leadTimeSource"] == "master"
    assert danger["orderingMethod"] == "手動発注"
    assert danger["orderingMethodKey"] == "manual"
    assert danger["alertRowClass"] == "stockout-danger"
    assert danger["display"]["stockout_risk"] == "危険"

    legacy = payload["rows"][1]
    assert legacy["stockoutRisk"] == "監視"
    assert legacy["stockoutRiskKey"] == "watch"
    assert legacy["daysUntilStockout"] is None
    assert legacy["display"]["stockout_risk"] == ""

    assert payload["stockoutRiskOrder"] == ["danger", "caution", "watch", "none"]
    assert payload["stockoutRiskLabels"] == {"danger": "危険", "caution": "注意", "watch": "監視", "none": "対象外"}
    assert {"key": "days_until_stockout", "label": "猶予日数"} in payload["sortOnlyColumns"]
    assert payload["defaultSortSpecs"][0] == {"column": "stockout_risk", "direction": "asc"}


def test_d063_row_alert_class_priority():
    assert row_alert_class(_row(RISK_DANGER, quadrant=QUADRANT_LOW_FLOW_NO_INCOMING)) == "stockout-danger"
    assert row_alert_class(_row(RISK_CAUTION)) == "stockout-caution"
    # 監視・対象外は流動区分の色を使わない（2026/09/18 改訂: 行の色は在庫切れリスクのみ）
    assert row_alert_class(_row(RISK_WATCH, quadrant=QUADRANT_DORMANT_STOCK)) == "stockout-watch"
    assert row_alert_class(_row(RISK_NONE)) == "stockout-none"
    assert row_alert_class(_row(None, quadrant=QUADRANT_DORMANT_STOCK)) == "stockout-watch"
    assert row_alert_class(_row(RISK_DANGER, status="確認済み")) == "確認済"


# --- TC-SOR-D-064: CSV ---


def test_d064_csv_appends_stockout_columns_after_existing_28():
    columns = [column for column, _label in EXPORT_COLUMNS]
    assert len(columns) == 39
    assert columns[28:] == [
        "stockout_risk",
        "stockout_risk_reasons",
        "days_until_stockout",
        "replenishment_qty",
        "replenishment_earliest_due",
        "replenishment_has_overdue",
        "shortage_qty",
        "lead_time_days",
        "ordering_method",
        "upstream_order_qty",
        "upstream_order_overdue",
    ]
    assert [label for _c, label in EXPORT_COLUMNS[28:]] == [
        "在庫切れリスク",
        "在庫切れリスクの理由",
        "猶予日数",
        "補充見込み",
        "補充見込みの最早納期",
        "納期超過",
        "不足数量",
        "リードタイム",
        "発注方式",
        "上流工程の発注残",
        "上流工程の納期超過",
    ]

    payload = render_export_csv([_row(RISK_DANGER, days=0, replenishment_has_overdue=True), _row(None)]).decode("utf-8-sig")
    records = list(csv.DictReader(io.StringIO(payload)))
    assert records[0]["在庫切れリスク"] == "危険"
    assert records[0]["在庫切れリスクの理由"] == "発注忘れの可能性・リードタイム内"
    assert records[0]["猶予日数"] == "0"
    assert records[0]["納期超過"] == "あり"
    assert records[0]["発注方式"] == "手動発注"
    assert records[1]["在庫切れリスク"] == ""
    assert records[1]["在庫切れリスクの理由"] == ""
    assert records[1]["納期超過"] == ""
