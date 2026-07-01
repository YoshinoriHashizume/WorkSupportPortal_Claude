from __future__ import annotations

from applications.asset_inventory.domain.dates import format_asset_acquisition_date_display
from applications.asset_inventory.domain.plate_display import format_plate_created
from applications.asset_inventory.domain.row_detail import build_field_comparisons
from applications.asset_inventory.domain.ports import (
    ASSET_ACQUISITION_DATE_FIELD,
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


def _attachment_photo_url(record: Record, field_name: str) -> str:
    value = (record.get(field_name) or "").strip()
    if value.startswith("http://") or value.startswith("https://"):
        return value
    return ""


def map_record_to_display(
    source: Record,
    *,
    status: MatchStatus,
    row_tone: RowTone,
    has_diff: bool,
    factory_change: bool,
    empty_inventory_fields: bool = False,
    asset_row: Record | None = None,
    inventory_row: Record | None = None,
    photo_source: Record | None = None,
) -> ReconcileRow:
    if empty_inventory_fields:
        plate_code, plate_label = "", ""
    else:
        plate_code, plate_label = format_plate_created(source.get("プレート作成", ""))
    photo_record = photo_source or (source if not empty_inventory_fields else {})
    compare_asset = asset_row if asset_row is not None else (source if status == MatchStatus.ASSET_ONLY else None)
    compare_inventory = inventory_row if inventory_row is not None else (
        source if status in (MatchStatus.MATCHED, MatchStatus.INVENTORY_ONLY) else None
    )
    acquisition_source = asset_row if asset_row is not None else (
        source if status == MatchStatus.ASSET_ONLY else {}
    )
    field_comparisons = build_field_comparisons(compare_asset, compare_inventory)
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
        asset_acquisition_date=format_asset_acquisition_date_display(
            acquisition_source.get(ASSET_ACQUISITION_DATE_FIELD, ""),
        ),
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
        asset_photo_url=_attachment_photo_url(photo_record, "資産写真"),
        plate_photo_url=_attachment_photo_url(photo_record, "資産プレート写真"),
        field_comparisons=field_comparisons,
    )
