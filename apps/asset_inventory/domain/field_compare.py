from __future__ import annotations

from apps.asset_inventory.domain.ports import Record

COMPARE_FIELDS: tuple[tuple[str, str], ...] = (
    ("管理部門名称", "管理部門名称"),
    ("メーカー", "メーカー"),
    ("管理者名称", "管理者名称"),
    ("型番", "型番"),
    ("旧資産番号コード", "旧資産番号コード"),
    ("使用区分", "使用区分"),
    ("摘要", "摘要"),
)


def field_values_equal(left: str, right: str) -> bool:
    return (left or "").strip() == (right or "").strip()


def has_field_diff(asset_row: Record, inventory_row: Record) -> bool:
    for asset_field, inventory_field in COMPARE_FIELDS:
        if not field_values_equal(asset_row.get(asset_field, ""), inventory_row.get(inventory_field, "")):
            return True
    return False


def build_site_code_map(site_records: list[Record]) -> dict[str, str]:
    """管理部門コード -> 拠点識別子（データID）"""
    mapping: dict[str, str] = {}
    for row in site_records:
        code = (row.get("管理部門コード") or "").strip()
        site_id = (row.get("データID") or code).strip()
        if code:
            mapping[code] = site_id
    return mapping


def has_factory_change(
    asset_row: Record,
    inventory_row: Record,
    site_code_map: dict[str, str],
) -> bool:
    asset_code = (asset_row.get("管理部門コード") or "").strip()
    inventory_code = (inventory_row.get("管理部門コード") or "").strip()
    if not asset_code or not inventory_code:
        return False

    asset_site = site_code_map.get(asset_code)
    inventory_site = site_code_map.get(inventory_code)
    if asset_site and inventory_site:
        return asset_site != inventory_site

    # 拠点マスタで両方解決できない場合は、管理部門コードの直接比較で判定する。
    return asset_code != inventory_code
