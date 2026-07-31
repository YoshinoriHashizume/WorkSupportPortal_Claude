from __future__ import annotations

from datetime import date

from application.inventory_order_alert.domain.value_objects.list_rows import (
    filter_summary_rows,
    sort_summary_rows,
)
from application.inventory_order_alert.domain.value_objects.list_query import ListQuery, parse_list_query


def _row(
    *,
    cust_code: str = "112",
    vend_code: str = "9209",
    alert_level: str = "重点",
    confirmation_status: str = "未確認",
    qty: int = 100,
) -> dict[str, object]:
    return {
        "cust_code": cust_code,
        "level1_vend_cd": vend_code,
        "alert_level": alert_level,
        "confirmation_status": confirmation_status,
        "post_shipment_total_qty": qty,
    }


def test_parse_list_query_defaults():
    query = parse_list_query({}, today=date(2026, 6, 17))
    assert query.as_of_date == date(2026, 6, 17)
    assert query.alert_only is True
    assert query.hide_confirmed is False
    assert query.warning_shipment_months == 12
    assert query.warning_incoming_months == 12


def test_parse_list_query_warning_months():
    query = parse_list_query(
        {"warningShipmentMonths": "24", "warningIncomingMonths": "6"},
        today=date(2026, 6, 17),
    )
    assert query.warning_shipment_months == 24
    assert query.warning_incoming_months == 6


def test_parse_list_query_alert_only_false():
    query = parse_list_query({"alertOnly": "false"}, today=date(2026, 6, 17))
    assert query.alert_only is False


def test_parse_list_query_hide_confirmed():
    query = parse_list_query({"hideConfirmed": "true"}, today=date(2026, 6, 17))
    assert query.hide_confirmed is True


def test_filter_summary_rows_by_cust_and_vend_code():
    rows = [_row(cust_code="112"), _row(cust_code="999"), _row(vend_code="0001")]
    query = ListQuery(as_of_date=date(2026, 6, 17), cust_code="112", vend_code="9209")
    filtered = filter_summary_rows(rows, query)
    assert len(filtered) == 1
    assert filtered[0]["cust_code"] == "112"


def test_filter_summary_rows_alert_only():
    rows = [_row(alert_level="重点"), _row(alert_level="アラート無し")]
    query = ListQuery(as_of_date=date(2026, 6, 17), alert_only=True)
    filtered = filter_summary_rows(rows, query)
    assert len(filtered) == 1
    assert filtered[0]["alert_level"] == "重点"


def test_filter_summary_rows_hide_confirmed():
    rows = [_row(confirmation_status="確認済み"), _row(confirmation_status="未確認")]
    query = ListQuery(as_of_date=date(2026, 6, 17), hide_confirmed=True, alert_only=False)
    filtered = filter_summary_rows(rows, query)
    assert len(filtered) == 1
    assert filtered[0]["confirmation_status"] == "未確認"


def test_sort_summary_rows_orders_by_alert_then_qty():
    rows = [
        _row(alert_level="警告（出荷あり）", qty=50),
        _row(alert_level="重点", qty=10),
        _row(alert_level="重点", qty=200),
    ]
    sorted_rows = sort_summary_rows(rows)
    assert [row["alert_level"] for row in sorted_rows] == ["重点", "重点", "警告（出荷あり）"]
    assert [row["post_shipment_total_qty"] for row in sorted_rows[:2]] == [200, 10]
