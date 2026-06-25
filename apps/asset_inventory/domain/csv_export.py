from __future__ import annotations

import csv
import io

from apps.asset_inventory.domain.ports import DISPLAY_COLUMNS, ReconcileRow


def render_export_csv(rows: tuple[ReconcileRow, ...]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    headers = ["突合結果", "行色区分"] + [label for _, label in DISPLAY_COLUMNS[1:]]
    writer.writerow(headers)
    for row in rows:
        writer.writerow(
            [
                row.status_label,
                row.tone_label,
                row.asset_number,
                row.branch_number,
                row.site_name,
                row.manufacturer,
                row.model_name,
                row.serial_number,
                row.old_asset_number,
                row.usage_category,
                row.summary,
                row.plate_created,
                row.inventory_operator,
                row.inventory_datetime,
            ]
        )
    return ("\ufeff" + buffer.getvalue()).encode("utf-8")
