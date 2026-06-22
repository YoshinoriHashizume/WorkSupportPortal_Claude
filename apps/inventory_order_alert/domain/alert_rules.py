from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AlertRuleRow:
    has_incoming: str
    has_shipment: str
    level: str
    level_key: str


def format_months_label(months: int) -> str:
    return f"{months}か月"


def build_alert_rule_rows(
    *,
    warning_shipment_months: int,
    warning_incoming_months: int,
) -> list[AlertRuleRow]:
    ship_period = format_months_label(warning_shipment_months)
    incoming_period = format_months_label(warning_incoming_months)
    ship_within = f"{ship_period}未満"
    ship_beyond = f"{ship_period}以上"
    incoming_within = f"{incoming_period}未満"
    incoming_beyond = f"{incoming_period}以上"
    return [
        AlertRuleRow("なし", "なし", "アラート無し", "none"),
        AlertRuleRow("なし", "あり", "重点", "critical"),
        AlertRuleRow("あり", f"あり（{ship_beyond}）", "警告（出荷あり）", "warning-ship"),
        AlertRuleRow("あり", f"あり（{ship_within}）", "アラート無し", "none"),
        AlertRuleRow("あり", f"なし（{incoming_beyond}）", "警告（出荷なし）", "warning-incoming"),
        AlertRuleRow("あり", f"なし（{incoming_within}）", "アラート無し", "none"),
    ]
