from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from applications.asset_inventory.domain.ports import MatchStatus, ReconcileCounts, ReconcileRow, RowTone
from applications.asset_inventory.domain.row_detail import FieldComparisonItem

SESSION_KEY = "asset_inventory_reconcile_cache"


@dataclass(frozen=True)
class ReconcileCache:
    management_id: str
    rows: tuple[ReconcileRow, ...]
    counts: ReconcileCounts
    site_options: tuple[str, ...]
    asset_number_options: tuple[str, ...]


def _field_comparison_to_dict(item: FieldComparisonItem) -> dict[str, Any]:
    return {
        "label": item.label,
        "asset_value": item.asset_value,
        "inventory_value": item.inventory_value,
        "is_diff": item.is_diff,
    }


def _field_comparison_from_dict(payload: dict[str, Any]) -> FieldComparisonItem:
    return FieldComparisonItem(
        label=str(payload.get("label") or ""),
        asset_value=str(payload.get("asset_value") or ""),
        inventory_value=str(payload.get("inventory_value") or ""),
        is_diff=bool(payload.get("is_diff")),
    )


def reconcile_row_to_dict(row: ReconcileRow) -> dict[str, Any]:
    comparisons = row.field_comparisons or ()
    return {
        "match_status": row.match_status.value,
        "row_tone": row.row_tone.value,
        "status_label": row.status_label,
        "tone_label": row.tone_label,
        "asset_number": row.asset_number,
        "branch_number": row.branch_number,
        "site_name": row.site_name,
        "manufacturer": row.manufacturer,
        "model_name": row.model_name,
        "serial_number": row.serial_number,
        "old_asset_number": row.old_asset_number,
        "usage_category": row.usage_category,
        "summary": row.summary,
        "plate_created": row.plate_created,
        "inventory_operator": row.inventory_operator,
        "inventory_datetime": row.inventory_datetime,
        "asset_acquisition_date": row.asset_acquisition_date,
        "has_diff": row.has_diff,
        "factory_change": row.factory_change,
        "css_class": row.css_class,
        "plate_created_code": row.plate_created_code,
        "asset_photo_url": row.asset_photo_url,
        "plate_photo_url": row.plate_photo_url,
        "field_comparisons": [
            _field_comparison_to_dict(item) if isinstance(item, FieldComparisonItem) else item
            for item in comparisons
        ],
    }


def reconcile_row_from_dict(payload: dict[str, Any]) -> ReconcileRow:
    comparisons = tuple(
        _field_comparison_from_dict(item) if isinstance(item, dict) else item
        for item in (payload.get("field_comparisons") or [])
    )
    return ReconcileRow(
        match_status=MatchStatus(str(payload.get("match_status") or MatchStatus.MATCHED.value)),
        row_tone=RowTone(str(payload.get("row_tone") or RowTone.NONE.value)),
        status_label=str(payload.get("status_label") or ""),
        tone_label=str(payload.get("tone_label") or ""),
        asset_number=str(payload.get("asset_number") or ""),
        branch_number=str(payload.get("branch_number") or ""),
        site_name=str(payload.get("site_name") or ""),
        manufacturer=str(payload.get("manufacturer") or ""),
        model_name=str(payload.get("model_name") or ""),
        serial_number=str(payload.get("serial_number") or ""),
        old_asset_number=str(payload.get("old_asset_number") or ""),
        usage_category=str(payload.get("usage_category") or ""),
        summary=str(payload.get("summary") or ""),
        plate_created=str(payload.get("plate_created") or ""),
        inventory_operator=str(payload.get("inventory_operator") or ""),
        inventory_datetime=str(payload.get("inventory_datetime") or ""),
        asset_acquisition_date=str(payload.get("asset_acquisition_date") or ""),
        has_diff=bool(payload.get("has_diff")),
        factory_change=bool(payload.get("factory_change")),
        css_class=str(payload.get("css_class") or ""),
        plate_created_code=str(payload.get("plate_created_code") or ""),
        asset_photo_url=str(payload.get("asset_photo_url") or ""),
        plate_photo_url=str(payload.get("plate_photo_url") or ""),
        field_comparisons=comparisons,
    )


def reconcile_cache_to_session_payload(cache: ReconcileCache) -> dict[str, Any]:
    return {
        "management_id": cache.management_id,
        "rows": [reconcile_row_to_dict(row) for row in cache.rows],
        "counts": {
            "matched": cache.counts.matched,
            "asset_only": cache.counts.asset_only,
            "inventory_only": cache.counts.inventory_only,
        },
        "site_options": list(cache.site_options),
        "asset_number_options": list(cache.asset_number_options),
    }


def reconcile_cache_from_session_payload(payload: dict[str, Any]) -> ReconcileCache | None:
    management_id = str(payload.get("management_id") or "").strip()
    if not management_id:
        return None
    rows_payload = payload.get("rows")
    if not isinstance(rows_payload, list):
        return None
    counts_payload = payload.get("counts") or {}
    counts = ReconcileCounts(
        matched=int(counts_payload.get("matched") or 0),
        asset_only=int(counts_payload.get("asset_only") or 0),
        inventory_only=int(counts_payload.get("inventory_only") or 0),
    )
    return ReconcileCache(
        management_id=management_id,
        rows=tuple(reconcile_row_from_dict(row) for row in rows_payload if isinstance(row, dict)),
        counts=counts,
        site_options=tuple(str(value) for value in (payload.get("site_options") or [])),
        asset_number_options=tuple(str(value) for value in (payload.get("asset_number_options") or [])),
    )


def load_reconcile_cache(session: dict[str, Any] | None) -> ReconcileCache | None:
    if session is None:
        return None
    payload = session.get(SESSION_KEY)
    if not isinstance(payload, dict):
        return None
    return reconcile_cache_from_session_payload(payload)


def save_reconcile_cache(session: dict[str, Any], cache: ReconcileCache) -> None:
    session[SESSION_KEY] = reconcile_cache_to_session_payload(cache)
    if hasattr(session, "modified"):
        session.modified = True


def clear_reconcile_cache(session: dict[str, Any]) -> None:
    if SESSION_KEY in session:
        del session[SESSION_KEY]
        if hasattr(session, "modified"):
            session.modified = True
