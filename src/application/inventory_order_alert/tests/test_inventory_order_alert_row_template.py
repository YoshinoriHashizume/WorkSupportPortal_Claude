from __future__ import annotations

from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    QUADRANT_LOW_FLOW_NO_SHIPMENT,
    QUADRANT_LOW_FLOW_NO_INCOMING,
)
from application.inventory_order_alert.use_cases.list_page import _rows_for_template


def test_rows_for_template_sets_alert_row_class_to_response_class_key():
    # 行の色は対応区分のみ（08 design §5）。旧行（キーなし）は対象外、旧称「危険」は発注遅れへ写す
    rows = _rows_for_template(
        [
            {"flow_quadrant": QUADRANT_LOW_FLOW_NO_INCOMING, "confirmation_status": "未確認", "response_class": "発注遅れ"},
            {"flow_quadrant": QUADRANT_LOW_FLOW_NO_INCOMING, "confirmation_status": "未確認", "stockout_risk": "危険"},
            {"flow_quadrant": QUADRANT_LOW_FLOW_NO_SHIPMENT, "confirmation_status": "未確認"},
        ]
    )
    assert rows[0]["alert_row_class"] == "response-order-overdue"
    assert rows[1]["alert_row_class"] == "response-order-overdue"
    assert rows[2]["alert_row_class"] == "response-none"


def test_rows_for_template_prefers_confirmation_class_over_flow_quadrant():
    rows = _rows_for_template(
        [
            {"flow_quadrant": QUADRANT_LOW_FLOW_NO_INCOMING, "confirmation_status": "確認済み"},
            {"flow_quadrant": QUADRANT_LOW_FLOW_NO_INCOMING, "confirmation_status": "確認中"},
        ]
    )
    assert rows[0]["alert_row_class"] == "確認済"
    assert rows[1]["alert_row_class"] == "確認中"
