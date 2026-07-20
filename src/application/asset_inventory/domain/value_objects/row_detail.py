from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

from application.asset_inventory.domain.value_objects.field_compare import field_values_equal
from application.asset_inventory.domain.repositories.ports import Record, ReconcileRow

FIELD_COMPARISON_SPECS: tuple[tuple[str, str], ...] = (
    ("資産番号", "資産番号"),
    ("資産枝番", "資産枝番"),
    ("管理部門名称", "拠点名"),
    ("メーカー", "メーカー名"),
    ("管理者名称", "型番"),
    ("型番", "シリアルNo."),
    ("旧資産番号コード", "旧資産番号"),
    ("使用区分", "使用区分"),
    ("摘要", "摘要"),
)

# 変化点判定（§5.4）用。資産番号・枝番は突合キーのため比較対象外。
FIELD_DIFF_SPECS: tuple[tuple[str, str], ...] = FIELD_COMPARISON_SPECS[2:]


@dataclass(frozen=True)
class FieldComparisonItem:
    label: str
    asset_value: str
    inventory_value: str
    is_diff: bool


def build_field_comparisons(
    asset_row: Record | None,
    inventory_row: Record | None,
) -> tuple[FieldComparisonItem, ...]:
    asset = asset_row or {}
    inventory = inventory_row or {}
    items: list[FieldComparisonItem] = []
    for field_name, label in FIELD_COMPARISON_SPECS:
        asset_value = (asset.get(field_name) or "").strip()
        inventory_value = (inventory.get(field_name) or "").strip()
        items.append(
            FieldComparisonItem(
                label=label,
                asset_value=asset_value,
                inventory_value=inventory_value,
                is_diff=not field_values_equal(asset_value, inventory_value),
            )
        )
    return tuple(items)


def build_field_diffs(asset_row: Record, inventory_row: Record) -> tuple[FieldComparisonItem, ...]:
    return tuple(item for item in build_field_comparisons(asset_row, inventory_row) if item.is_diff)


def build_attachment_proxy_path(source_url: str, *, proxy_base_path: str) -> str:
    if not source_url:
        return ""
    return f"{proxy_base_path}?src={quote(source_url, safe='')}"


def build_row_detail_payload(
    row: ReconcileRow,
    *,
    attachment_proxy_base_path: str,
) -> dict[str, object]:
    photos = [
        {
            "label": "資産写真",
            "href": build_attachment_proxy_path(row.asset_photo_url, proxy_base_path=attachment_proxy_base_path),
        },
        {
            "label": "資産プレート写真",
            "href": build_attachment_proxy_path(row.plate_photo_url, proxy_base_path=attachment_proxy_base_path),
        },
    ]
    field_comparisons = [
        {
            "label": item.label,
            "asset_value": item.asset_value,
            "inventory_value": item.inventory_value,
            "is_diff": item.is_diff,
        }
        for item in row.field_comparisons
    ]
    return {
        "photos": photos,
        "field_comparisons": field_comparisons,
    }


def build_row_details_index(
    rows: tuple[ReconcileRow, ...],
    *,
    attachment_proxy_base_path: str,
) -> dict[str, dict[str, object]]:
    index: dict[str, dict[str, object]] = {}
    for row in rows:
        key = f"{row.asset_number}|{row.branch_number}"
        index[key] = build_row_detail_payload(row, attachment_proxy_base_path=attachment_proxy_base_path)
    return index
