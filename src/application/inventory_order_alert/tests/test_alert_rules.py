from __future__ import annotations

from application.inventory_order_alert.domain.value_objects.alert_rules import build_alert_rule_rows


def test_build_alert_rule_rows_matches_six_patterns():
    rows = build_alert_rule_rows(warning_shipment_months=12, warning_incoming_months=12)
    assert [(row.has_incoming, row.has_shipment, row.level) for row in rows] == [
        ("なし", "なし", "アラート無し"),
        ("なし", "あり", "重点"),
        ("あり", "あり（12か月以上）", "警告（出荷あり）"),
        ("あり", "あり（12か月未満）", "アラート無し"),
        ("あり", "なし（12か月以上）", "警告（出荷なし）"),
        ("あり", "なし（12か月未満）", "アラート無し"),
    ]
