from __future__ import annotations

from application.inventory_order_alert.domain.value_objects.row_counts import RowCounts, count_rows


def test_count_rows_aggregates_alert_and_confirmation_statuses():
    rows = [
        {
            "alert_level": "重点",
            "confirmation_status": "未確認",
        },
        {
            "alert_level": "警告（出荷あり）",
            "confirmation_status": "確認中",
        },
        {
            "alert_level": "警告（出荷なし）",
            "confirmation_status": "確認済み",
        },
        {
            "alert_level": "アラート無し",
            "confirmation_status": "未確認",
        },
    ]

    counts = count_rows(rows)

    assert counts == RowCounts(
        total=4,
        critical=1,
        warning_ship=1,
        warning_incoming=1,
        alert_none=1,
        warning=2,
        alert=3,
        unconfirmed=2,
        in_progress=1,
        confirmed=1,
    )
