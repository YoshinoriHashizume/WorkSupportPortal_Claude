"""照合単位行（T-213）の CSV・配信データ・件数（spec/13 test-design TC-RUR-D-050〜056）。"""

from __future__ import annotations

import csv
import io
from datetime import date, timedelta

from application.inventory_order_alert.domain.value_objects.export_csv import EXPORT_COLUMNS, render_export_csv
from application.inventory_order_alert.domain.value_objects.list_client_data import row_to_client_dict
from application.inventory_order_alert.domain.value_objects.reconciliation_unit_row import build_reconciliation_unit_rows
from application.inventory_order_alert.domain.value_objects.row_counts import count_rows
from application.inventory_order_alert.tests.test_reconciliation_unit_row import (
    _row,
    _single_s_row,
    _unit_a_rows,
    _unit_b_rows,
)

AS_OF = date(2026, 11, 25)

EXPECTED_HEADERS = [
    "担当者コード", "得意先コード", "得意先名", "得意先品番", "仕入先コード", "仕入先名", "仕入先品番",
    "最終入荷日", "最終出荷日", "最終入荷日以降の出荷回数", "最終入荷日以降の出荷数合計",
    "在庫数(SLIMS)", "在庫数(MARI)", "在庫時点", "流動区分", "判定軸", "判定期間", "入荷実績なし",
    "責任部署", "確認状態", "確認日時", "確認者", "最新メモ", "メモ履歴", "在庫月数", "在庫切れ予測月",
    "需要予測の算出根拠", "推奨アクション", "対応区分", "対応区分の理由", "在庫切れ日", "発注期限",
    "納期遅れの発注残数量", "安全在庫割れ", "安全在庫", "リードタイム", "発注方式", "滞留発注残件数", "滞留発注残数量",
]


def _csv_rows(rows):
    text = render_export_csv(rows).decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text)))


def _all_units():
    return build_reconciliation_unit_rows(_unit_a_rows() + _unit_b_rows() + [_single_s_row()])


def test_d050_csv_has_one_line_per_unit_row():
    assert len(_csv_rows(_all_units())) == 3


def test_d051_multiple_values_are_joined():
    [line] = _csv_rows(build_reconciliation_unit_rows(_unit_a_rows()))

    assert line["得意先コード"] == "104、176"
    assert line["得意先名"] == "トヨタ紡織株式会社、秋田工業株式会社"
    assert line["得意先品番"] == "X"


def test_d052_csv_columns_do_not_change():
    assert [label for _column, label in EXPORT_COLUMNS] == EXPECTED_HEADERS


def test_d053_payload_carries_lists_breakdown_and_member_count():
    [unit] = build_reconciliation_unit_rows(_unit_a_rows())

    client = row_to_client_dict(unit, AS_OF)

    assert client["cust_codes"] == ["104", "176"]
    assert client["cust_chrg_psn_cds"] == ["22"]
    assert client["item_cds"] == ["X"]
    assert client["level1_vend_cds"] == ["9028"]
    assert len(client["customer_breakdown"]) == 2
    assert client["unit_member_count"] == 2
    # 行キーは代表の（得意先, 得意先品番）のまま（design §1）
    assert client["rowKey"].startswith("104")


def test_d054_chart_materials_are_unit_totals():
    [unit] = build_reconciliation_unit_rows(_unit_a_rows())

    client = row_to_client_dict(unit, AS_OF)

    assert {p["date"]: p["qty"] for p in client["unconfirmedOrderDaily"]}["2026-11-26"] == 1438


def _business_days(start: date, end: date) -> list[date]:
    days = []
    day = start
    while day <= end:
        if day.weekday() < 5:
            days.append(day)
        day += timedelta(days=1)
    return days


def _demand(daily_qty_by_month: dict[int, int]) -> list[dict[str, object]]:
    return [
        {"date": day.isoformat(), "qty": daily_qty_by_month[day.month]}
        for day in _business_days(date(2026, 11, 26), date(2026, 12, 31))
    ]


def test_d055_chart_goes_below_zero_on_the_stockout_date():
    """`90361-18001` 相当: 在庫 11,341、トヨタ紡織 1 日 1,428→967、秋田工業 1 日 10→12。"""
    rows = _unit_a_rows()
    rows[0]["unconfirmed_order_daily"] = _demand({11: 1428, 12: 967})
    rows[1]["unconfirmed_order_daily"] = _demand({11: 10, 12: 12})
    [unit] = build_reconciliation_unit_rows(rows)
    client = row_to_client_dict(unit, AS_OF)

    stock = float(client["stock_qty"])
    demand = {p["date"]: p["qty"] for p in client["unconfirmedOrderDaily"]}
    first_negative = None
    day = AS_OF + timedelta(days=1)
    while day <= date(2026, 12, 31):
        stock -= demand.get(day.isoformat(), 0)
        if stock < 0:
            first_negative = day
            break
        day += timedelta(days=1)

    assert first_negative == date(2026, 12, 10)
    assert client["stockoutDate"] == "2026/12/10"


def test_d056_counts_are_unit_rows():
    rows = _unit_a_rows() + _unit_b_rows() + [_single_s_row()]
    units = build_reconciliation_unit_rows(rows)
    for unit in units:
        if unit["item_cd"] in ("P", "Q"):
            unit["response_class"] = "要発注"

    counts = count_rows(units)

    assert counts.total == 3
    assert counts.order_overdue == 1
    assert counts.order_needed == 1
