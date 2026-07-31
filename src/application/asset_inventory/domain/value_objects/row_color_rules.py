from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RowColorRuleRow:
    match_status: str
    diff_status: str
    tone_label: str
    tone_key: str


def build_row_color_rule_rows() -> tuple[RowColorRuleRow, ...]:
    return (
        RowColorRuleRow("棚卸済み", "変化点なし", "一致", "clean"),
        RowColorRuleRow("棚卸済み", "拠点変更あり", "拠点変更あり", "factory"),
        RowColorRuleRow("棚卸済み", "変化点あり（拠点以外）", "差異あり", "diff"),
        RowColorRuleRow("未棚卸・台帳外", "—", "未突合", "none"),
    )
