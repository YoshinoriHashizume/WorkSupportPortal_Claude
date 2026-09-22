from __future__ import annotations

from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    QUADRANT_LOW_FLOW_NO_SHIPMENT,
    QUADRANT_LOW_FLOW_NO_INCOMING,
)
from application.inventory_order_alert.use_cases.list_page import _rows_for_template


def test_rows_for_template_sets_alert_row_class_to_stockout_risk_key():
    # 行の色は在庫切れリスクのみ（2026/09/18 改訂）。旧行（キーなし）は監視
    rows = _rows_for_template(
        [
            {"flow_quadrant": QUADRANT_LOW_FLOW_NO_INCOMING, "confirmation_status": "未確認", "stockout_risk": "危険"},
            {"flow_quadrant": QUADRANT_LOW_FLOW_NO_SHIPMENT, "confirmation_status": "未確認"},
        ]
    )
    assert rows[0]["alert_row_class"] == "stockout-danger"
    assert rows[1]["alert_row_class"] == "stockout-watch"


def test_rows_for_template_prefers_confirmation_class_over_flow_quadrant():
    rows = _rows_for_template(
        [
            {"flow_quadrant": QUADRANT_LOW_FLOW_NO_INCOMING, "confirmation_status": "確認済み"},
            {"flow_quadrant": QUADRANT_LOW_FLOW_NO_INCOMING, "confirmation_status": "確認中"},
        ]
    )
    assert rows[0]["alert_row_class"] == "確認済"
    assert rows[1]["alert_row_class"] == "確認中"
