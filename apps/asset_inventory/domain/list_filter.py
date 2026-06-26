from __future__ import annotations

from apps.asset_inventory.domain.match_key import normalize_asset_number
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


def extract_asset_numbers_from_rows(rows: tuple[ReconcileRow, ...]) -> tuple[str, ...]:
    numbers: set[str] = set()
    for row in rows:
        display = (row.asset_number or "").strip()
        if not display:
            continue
        normalized = normalize_asset_number(display)
        if normalized:
            numbers.add(normalized)
    return tuple(sorted(numbers))


def filter_asset_number_options(
    options: tuple[str, ...],
    query: str,
) -> tuple[str, ...]:
    query_norm = normalize_asset_number(query)
    if not query_norm:
        return options
    return tuple(
        option
        for option in options
        if normalize_asset_number(option).startswith(query_norm)
    )


def matches_asset_number_filter(asset_number: str, asset_number_filter: str) -> bool:
    query = (asset_number_filter or "").strip()
    if not query:
        return True
    row_display = (asset_number or "").strip()
    if not row_display:
        return False
    query_norm = normalize_asset_number(query)
    row_norm = normalize_asset_number(row_display)
    if not query_norm:
        return True
    return row_norm.startswith(query_norm)


def apply_filters(
    rows: tuple[ReconcileRow, ...],
    *,
    status_filter: str,
    site_filter: str,
    plate_filter: str = "all",
    asset_number_filter: str = "",
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

    if asset_number_filter.strip():
        filtered = tuple(
            row for row in filtered if matches_asset_number_filter(row.asset_number, asset_number_filter)
        )

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
