from __future__ import annotations

from application.shipment_trend.domain.value_objects.alert_tier import (
    ROW_DECREASE_MILD,
    ROW_DECREASE_STRONG,
    ROW_INCREASE_STRONG,
    ROW_NEUTRAL,
    alert_row_class,
    build_alert_rule_rows,
)


def test_alert_row_class_decrease_strong():
    assert alert_row_class(-25.0, decrease_threshold_pct=20, increase_threshold_pct=20) == ROW_DECREASE_STRONG


def test_alert_row_class_decrease_mild():
    assert alert_row_class(-10.0, decrease_threshold_pct=20, increase_threshold_pct=20) == ROW_DECREASE_MILD


def test_alert_row_class_increase_strong():
    assert alert_row_class(30.0, decrease_threshold_pct=20, increase_threshold_pct=20) == ROW_INCREASE_STRONG


def test_alert_row_class_neutral():
    assert alert_row_class(5.0, decrease_threshold_pct=20, increase_threshold_pct=20) == ROW_NEUTRAL
    assert alert_row_class(None, decrease_threshold_pct=20, increase_threshold_pct=20) == ROW_NEUTRAL


def test_build_alert_rule_rows_includes_class_key():
    rows = build_alert_rule_rows(decrease_threshold_pct=20, increase_threshold_pct=20)
    assert len(rows) == 4
    assert rows[0]["class_key"] == "decrease-strong"
    assert "−20%" in rows[0]["condition"]
    assert rows[1]["class_key"] == "decrease-mild"
    assert rows[2]["class_key"] == "increase-strong"
    assert rows[3]["class_key"] == "neutral"
