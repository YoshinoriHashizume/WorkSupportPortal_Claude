from __future__ import annotations

from applications.asset_inventory.domain.ports import Record

PLATE_CREATED_LABELS = {
    "0": "プレート有",
    "1": "プレート作成",
}


def format_plate_created(raw: str) -> tuple[str, str]:
    code = (raw or "").strip()
    if not code:
        return "", ""
    return code, PLATE_CREATED_LABELS.get(code, code)
