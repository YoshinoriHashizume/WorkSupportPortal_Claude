from __future__ import annotations

from application.asset_inventory.domain.value_objects.dates import parse_inventory_datetime
from application.asset_inventory.domain.value_objects.match_key import build_match_key
from application.asset_inventory.domain.repositories.ports import Record


def dedupe_inventory_records(records: list[Record]) -> dict[str, Record]:
    """同一突合キーに複数行ある場合、最新棚卸日時の行を採用する。"""
    grouped: dict[str, list[Record]] = {}
    for record in records:
        key = build_match_key(record.get("資産番号", ""), record.get("資産枝番", ""))
        grouped.setdefault(key, []).append(record)

    result: dict[str, Record] = {}
    for key, rows in grouped.items():
        result[key] = _pick_latest_row(rows)
    return result


def _pick_latest_row(rows: list[Record]) -> Record:
    def sort_key(row: Record) -> tuple[int, str, str]:
        parsed = parse_inventory_datetime(row.get("棚卸日時", ""))
        ts = int(parsed.timestamp()) if parsed else 0
        unparsable = 0 if parsed else 1
        data_id = row.get("データID", "")
        return (unparsable, -ts, data_id)

    return sorted(rows, key=sort_key)[0]
