from __future__ import annotations

from datetime import date

from apps.inventory_order_alert.domain.export_csv import (
    EXPORT_HEADER_LABELS,
    render_export_csv,
)


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
        "alert_level": "重点",
        "confirmation_status": "未確認",
        "confirmed_at": "",
        "confirmed_by": "",
        "confirmation_memo": "最新のみ",
        "confirmation_memo_history": "2026/06/19 10:00 10001: 最新のみ",
    }


def test_export_headers_are_japanese():
    assert EXPORT_HEADER_LABELS["last_incoming_date"] == "最終入荷日"
    assert EXPORT_HEADER_LABELS["item_cd"] == "得意先品番"
    assert EXPORT_HEADER_LABELS["cust_chrg_psn_cd"] == "担当者コード"
    assert EXPORT_HEADER_LABELS["level1_item_cd"] == "仕入先品番"
    assert EXPORT_HEADER_LABELS["alert_level"] == "アラート"
    assert "stock_location_summary" not in EXPORT_HEADER_LABELS


def test_render_export_csv_has_utf8_bom():
    payload = render_export_csv([_sample_row()])
    assert payload.startswith(b"\xef\xbb\xbf")


def test_render_export_csv_includes_stock_and_alert_columns():
    payload = render_export_csv([_sample_row()]).decode("utf-8-sig")
    lines = payload.strip().splitlines()
    header = lines[0]
    data = lines[1]
    assert "在庫数" in header
    assert "ロケーション" not in header
    assert "アラート" in header
    assert "最新メモ" in header
    assert "メモ履歴" in header
    assert "90249-10112" in data
    assert "重点" in data
    assert "250" in data


def test_render_export_csv_empty_rows_outputs_header_only():
    payload = render_export_csv([]).decode("utf-8-sig")
    lines = [line for line in payload.strip().splitlines() if line]
    assert len(lines) == 1
    assert "得意先コード" in lines[0]
