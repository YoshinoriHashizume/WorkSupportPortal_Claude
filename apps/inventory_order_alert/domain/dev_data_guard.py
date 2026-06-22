from __future__ import annotations

import re

KNOWN_TEST_IMPORT_FILE_NAMES = frozenset(
    {
        "sample.csv",
        "slims_stock_sample.csv",
        "slims_stock_sample_wkatqt.csv",
    }
)
_TEST_ITEM_CD_PATTERN = re.compile(r"^ITEM-\d{2}$")


def looks_like_test_import(file_name: str, rows: list[dict[str, object]] | None = None) -> bool:
    normalized = (file_name or "").strip().lower()
    if normalized in KNOWN_TEST_IMPORT_FILE_NAMES:
        return True
    if "slims_stock_sample" in normalized:
        return True
    if not rows:
        return False
    item_cds = [str(row.get("item_cd") or "").strip() for row in rows]
    if not item_cds:
        return False
    if all(_TEST_ITEM_CD_PATTERN.fullmatch(item_cd) for item_cd in item_cds if item_cd):
        return len(item_cds) <= 30
    return False
