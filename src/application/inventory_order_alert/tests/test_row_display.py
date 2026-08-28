from __future__ import annotations

from application.inventory_order_alert.domain.value_objects import row_display
from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    QUADRANT_NORMAL_FLOW,
    QUADRANT_SUPPLY_RISK,
)
from application.inventory_order_alert.domain.value_objects.row_display import (
    display_flow_quadrant,
    row_alert_class,
)

LEGACY_CRITICAL_LABEL = "重点"


def test_display_flow_quadrant_returns_label_for_row():
    row = {"flow_quadrant": QUADRANT_SUPPLY_RISK}

    assert display_flow_quadrant(row) == QUADRANT_SUPPLY_RISK


def test_display_flow_quadrant_normalizes_legacy_label():
    row = {"flow_quadrant": LEGACY_CRITICAL_LABEL}

    assert display_flow_quadrant(row) == QUADRANT_SUPPLY_RISK


def test_row_alert_class_returns_confirmed_class_for_confirmed_row():
    row = {"flow_quadrant": QUADRANT_SUPPLY_RISK, "confirmation_status": "確認済み"}

    assert row_alert_class(row) == "確認済"


def test_row_alert_class_returns_in_progress_class_for_in_progress_row():
    row = {"flow_quadrant": QUADRANT_SUPPLY_RISK, "confirmation_status": "確認中"}

    assert row_alert_class(row) == "確認中"


def test_row_alert_class_returns_flow_quadrant_key_for_unconfirmed_row():
    row = {"flow_quadrant": QUADRANT_SUPPLY_RISK, "confirmation_status": "未確認"}

    assert row_alert_class(row) == "supply-risk"


def test_row_alert_class_returns_normal_flow_key_for_normal_flow_row():
    row = {"flow_quadrant": QUADRANT_NORMAL_FLOW, "confirmation_status": "未確認"}

    assert row_alert_class(row) == "normal-flow"


def test_row_display_module_has_no_counts_toward_alert_summary():
    assert not hasattr(row_display, "counts_toward_alert_summary")
