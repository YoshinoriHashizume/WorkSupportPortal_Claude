from __future__ import annotations

from apps.asset_inventory.domain.ports import (
    MatchStatus,
    ReconcileCounts,
    ReconcileRow,
    Record,
)


def extract_site_names_from_assets(asset_records: list[Record]) -> tuple[str, ...]:
    names: set[str] = set()
    for row in asset_records:
        name = (row.get("管理部門名称") or "").strip()
        if name:
            names.add(name)
    return tuple(sorted(names))


def extract_site_names_from_rows(rows: tuple[ReconcileRow, ...]) -> tuple[str, ...]:
    names: set[str] = set()
    for row in rows:
        name = (row.site_name or "").strip()
        if name:
            names.add(name)
    return tuple(sorted(names))


def apply_filters(
    rows: tuple[ReconcileRow, ...],
    *,
    status_filter: str,
    site_filter: str,
    plate_filter: str = "all",
) -> tuple[ReconcileRow, ...]:
    filtered = rows
    if status_filter and status_filter != "all":
        status_map = {
            "matched": MatchStatus.MATCHED,
            "asset_only": MatchStatus.ASSET_ONLY,
            "inventory_only": MatchStatus.INVENTORY_ONLY,
        }
        target = status_map.get(status_filter)
        if target:
            filtered = tuple(row for row in filtered if row.match_status == target)

    if site_filter and site_filter != "all":
        site_name = site_filter.strip()
        filtered = tuple(
            row
            for row in filtered
            if (row.site_name or "").strip() == site_name
        )

    if plate_filter and plate_filter != "all":
        filtered = tuple(row for row in filtered if row.plate_created_code == plate_filter)

    return filtered


def count_rows(rows: tuple[ReconcileRow, ...]) -> ReconcileCounts:
    counts = ReconcileCounts()
    for row in rows:
        if row.match_status == MatchStatus.MATCHED:
            counts.matched += 1
        elif row.match_status == MatchStatus.ASSET_ONLY:
            counts.asset_only += 1
        elif row.match_status == MatchStatus.INVENTORY_ONLY:
            counts.inventory_only += 1
    return counts
