from __future__ import annotations

import csv
import io

from apps.asset_inventory.domain.ports import DISPLAY_COLUMNS, ReconcileRow


def render_export_csv(rows: tuple[ReconcileRow, ...]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    headers = [label for _key, label in DISPLAY_COLUMNS]
    writer.writerow(headers)
    for row in rows:
        writer.writerow([getattr(row, key) for key, _label in DISPLAY_COLUMNS])
    return ("\ufeff" + buffer.getvalue()).encode("utf-8")
