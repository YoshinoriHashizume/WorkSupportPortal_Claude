from __future__ import annotations

from datetime import date

from application.inventory_order_alert.domain.value_objects.export_csv import (
    EXPORT_COLUMNS,
    EXPORT_HEADER_LABELS,
    render_export_csv,
)
from application.inventory_order_alert.domain.value_objects.flow_quadrant import QUADRANT_SUPPLY_RISK

#: `confirmation_status` 以降は既存の CSV 読み込み手順を壊さないため順序を固定する（NF-002）。
TRAILING_COLUMNS = [
    "confirmation_status",
    "confirmed_at",
    "confirmed_by",
    "confirmation_memo",
    "confirmation_memo_history",
]


def _sample_row() -> dict[str, object]:
    return {
        "cust_code": "112",
        "cust_name": "テスト得意先",
        "cust_chrg_psn_cd": "A01",
        "item_cd": "90249-10112",
        "level1_item_cd": "90249-10112-9209",
        "level1_vend_cd": "9209",
        "level1_vend_name": "小野メッキ",
        "last_incoming_date": date(2026, 6, 11),
        "last_ship_date": date(2026, 6, 15),
        "post_shipment_count": 1,
        "post_shipment_total_qty": 250,
        "stock_qty": 100,
        "stock_location_summary": "2D0-03-5 他1",
        "stock_location_detail": "2D0-03-5=90@20161228;2E1-03-4=10@20161228",
        "stock_as_of_label": "2026年6月17日時点の在庫",
        "flow_quadrant": QUADRANT_SUPPLY_RISK,
        "flow_axis": "低流動判定軸",
        "evaluation_period": "3か月",
        "no_incoming_record": "あり",
        "responsible_department": "調達G・営業G・生産管理",
        "confirmation_status": "未確認",
        "confirmed_at": "",
        "confirmed_by": "",
        "confirmation_memo": "最新のみ",
        "confirmation_memo_history": "2026/06/19 10:00 10001: 最新のみ",
    }


def test_export_columns_replace_alert_level_with_flow_quadrant():
    columns = [column for column, _label in EXPORT_COLUMNS]

    assert ("flow_quadrant", "流動区分") in EXPORT_COLUMNS
    assert "alert_level" not in columns


def test_export_columns_include_flow_axis_and_evaluation_period():
    assert ("flow_axis", "判定軸") in EXPORT_COLUMNS
    assert ("evaluation_period", "判定期間") in EXPORT_COLUMNS


def test_export_columns_include_no_incoming_record_and_responsible_department():
    assert ("no_incoming_record", "入荷実績なし") in EXPORT_COLUMNS
    assert ("responsible_department", "責任部署") in EXPORT_COLUMNS


def test_export_columns_keep_order_after_confirmation_status():
    columns = [column for column, _label in EXPORT_COLUMNS]
    start = columns.index("confirmation_status")

    assert columns[start:] == TRAILING_COLUMNS


def test_export_headers_are_japanese():
    assert EXPORT_HEADER_LABELS["last_incoming_date"] == "最終入荷日"
    assert EXPORT_HEADER_LABELS["item_cd"] == "得意先品番"
    assert EXPORT_HEADER_LABELS["cust_chrg_psn_cd"] == "担当者コード"
    assert EXPORT_HEADER_LABELS["level1_item_cd"] == "仕入先品番"
    assert EXPORT_HEADER_LABELS["flow_quadrant"] == "流動区分"
    assert "stock_location_summary" not in EXPORT_HEADER_LABELS


def test_render_export_csv_has_utf8_bom():
    payload = render_export_csv([_sample_row()])
    assert payload.startswith(b"\xef\xbb\xbf")


def test_render_export_csv_includes_stock_and_flow_quadrant_columns():
    payload = render_export_csv([_sample_row()]).decode("utf-8-sig")
    lines = payload.strip().splitlines()
    header = lines[0]
    data = lines[1]
    assert "在庫数" in header
    assert "ロケーション" not in header
    assert "流動区分" in header
    assert "判定軸" in header
    assert "判定期間" in header
    assert "責任部署" in header
    assert "最新メモ" in header
    assert "メモ履歴" in header
    assert "90249-10112" in data
    assert QUADRANT_SUPPLY_RISK in data
    assert "250" in data


def test_render_export_csv_empty_rows_outputs_header_only():
    payload = render_export_csv([]).decode("utf-8-sig")
    lines = [line for line in payload.strip().splitlines() if line]
    assert len(lines) == 1
    assert "得意先コード" in lines[0]
