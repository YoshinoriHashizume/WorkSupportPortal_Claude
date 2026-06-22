from __future__ import annotations

from apps.inventory_order_alert.views import _rows_for_template


def test_rows_for_template_sets_alert_row_class():
    rows = _rows_for_template(
        [
            {"alert_level": "重点", "confirmation_status": "確認済み"},
            {"alert_level": "警告（入荷）", "confirmation_status": "未確認"},
        ]
    )
    assert rows[0]["alert_row_class"] == "確認済"
    assert rows[1]["alert_row_class"] == "警告（出荷なし）"


def test_rows_for_template_sets_in_progress_alert_row_class():
    rows = _rows_for_template(
        [{"alert_level": "重点", "confirmation_status": "確認中"}]
    )
    assert rows[0]["alert_row_class"] == "確認中"
