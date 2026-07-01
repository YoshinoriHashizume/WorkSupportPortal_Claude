from __future__ import annotations

from applications.asset_inventory.domain.row_color_rules import build_row_color_rule_rows


def test_TC_AIV_DOM_094_build_row_color_rule_rows():
    rows = build_row_color_rule_rows()
    assert len(rows) == 4
    expected = (
        ("棚卸済み", "変化点なし", "一致", "clean"),
        ("棚卸済み", "拠点変更あり", "拠点変更あり", "factory"),
        ("棚卸済み", "変化点あり（拠点以外）", "差異あり", "diff"),
        ("未棚卸・台帳外", "—", "未突合", "none"),
    )
    for row, (match_status, diff_status, tone_label, tone_key) in zip(rows, expected):
        assert row.match_status == match_status
        assert row.diff_status == diff_status
        assert row.tone_label == tone_label
        assert row.tone_key == tone_key
