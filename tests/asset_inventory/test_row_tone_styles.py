from __future__ import annotations

import re
from pathlib import Path

CSS_PATH = Path(__file__).resolve().parents[2] / "static" / "css" / "app.css"

TABLE_ROW_BACKGROUNDS = {
    "aiv-row-diff": "#dbeafe",
    "aiv-row-factory": "#fef9c3",
}

DIALOG_ROW_BACKGROUNDS = {
    "aiv-row-color-rules-row--diff": "#dbeafe",
    "aiv-row-color-rules-row--factory": "#fef9c3",
}


def _read_css() -> str:
    return CSS_PATH.read_text(encoding="utf-8")


def test_TC_AIV_DOM_095_table_row_background_colors():
    css = _read_css()
    for cls, hex_color in TABLE_ROW_BACKGROUNDS.items():
        pattern = (
            rf"\.asset-inventory-page \.aiv-table tbody tr\.{cls}\s*{{\s*"
            rf"background:\s*{re.escape(hex_color)};"
        )
        assert re.search(pattern, css), f"{cls} should use background {hex_color}"


def test_TC_AIV_DOM_096_dialog_row_background_colors():
    css = _read_css()
    for cls, hex_color in DIALOG_ROW_BACKGROUNDS.items():
        pattern = (
            rf"body\.asset-inventory-page \.{cls} td:last-child\s*{{\s*"
            rf"background:\s*{re.escape(hex_color)};"
        )
        assert re.search(pattern, css), f"{cls} preview should use background {hex_color}"
