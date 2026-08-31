from __future__ import annotations

from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    QUADRANT_EXCESS_STOCK_RISK,
    QUADRANT_SUPPLY_RISK,
)
from application.inventory_order_alert.use_cases.list_page import _rows_for_template


def test_rows_for_template_sets_alert_row_class_to_flow_quadrant_key():
    rows = _rows_for_template(
        [
            {"flow_quadrant": QUADRANT_SUPPLY_RISK, "confirmation_status": "未確認"},
            {"flow_quadrant": QUADRANT_EXCESS_STOCK_RISK, "confirmation_status": "未確認"},
        ]
    )
    assert rows[0]["alert_row_class"] == "supply-risk"
    assert rows[1]["alert_row_class"] == "excess-stock-risk"


def test_rows_for_template_prefers_confirmation_class_over_flow_quadrant():
    rows = _rows_for_template(
        [
            {"flow_quadrant": QUADRANT_SUPPLY_RISK, "confirmation_status": "確認済み"},
            {"flow_quadrant": QUADRANT_SUPPLY_RISK, "confirmation_status": "確認中"},
        ]
    )
    assert rows[0]["alert_row_class"] == "確認済"
    assert rows[1]["alert_row_class"] == "確認中"
