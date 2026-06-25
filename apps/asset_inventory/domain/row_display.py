from __future__ import annotations

from apps.asset_inventory.domain.plate_display import format_plate_created
from apps.asset_inventory.domain.ports import (
    MatchStatus,
    RowTone,
    ROW_TONE_CSS,
    STATUS_LABELS,
    TONE_LABELS,
    Record,
    ReconcileRow,
)


def derive_row_tone(status: MatchStatus, has_diff: bool, factory_change: bool) -> RowTone:
    if status in (MatchStatus.ASSET_ONLY, MatchStatus.INVENTORY_ONLY):
        return RowTone.NONE
    if not has_diff:
        return RowTone.MATCH_CLEAN
    if factory_change:
        return RowTone.MATCH_FACTORY
    return RowTone.MATCH_DIFF


def map_record_to_display(
    source: Record,
    *,
    status: MatchStatus,
    row_tone: RowTone,
    has_diff: bool,
    factory_change: bool,
    empty_inventory_fields: bool = False,
) -> ReconcileRow:
    if empty_inventory_fields:
        plate_code, plate_label = "", ""
    else:
        plate_code, plate_label = format_plate_created(source.get("プレート作成", ""))
    return ReconcileRow(
        match_status=status,
        row_tone=row_tone,
        status_label=STATUS_LABELS[status],
        tone_label=TONE_LABELS[row_tone],
        asset_number=source.get("資産番号", ""),
        branch_number=source.get("資産枝番", ""),
        site_name=source.get("管理部門名称", ""),
        manufacturer=source.get("メーカー", ""),
        model_name=source.get("管理者名称", ""),
        serial_number=source.get("型番", ""),
        old_asset_number=source.get("旧資産番号コード", ""),
        usage_category=source.get("使用区分", ""),
        summary=source.get("摘要", ""),
        plate_created=plate_label,
        plate_created_code=plate_code,
        inventory_operator="" if empty_inventory_fields else source.get("棚卸実施者", ""),
        inventory_datetime="" if empty_inventory_fields else source.get("棚卸日時", ""),
        has_diff=has_diff,
        factory_change=factory_change,
        css_class=ROW_TONE_CSS[row_tone],
    )
