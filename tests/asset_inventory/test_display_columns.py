from __future__ import annotations

from apps.asset_inventory.domain.ports import DISPLAY_COLUMNS


def test_TC_AIV_DOM_063_display_columns():
    labels = [label for _key, label in DISPLAY_COLUMNS]
    assert labels[:2] == ["棚卸結果", "変化状況"]
    assert len(labels) == 15
    assert labels[8] == "取得日付"
    assert labels.index("取得日付") == labels.index("シリアルNo.") + 1
