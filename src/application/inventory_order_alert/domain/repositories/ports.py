from __future__ import annotations

from collections.abc import Callable

from application.inventory_order_alert.domain.value_objects.app_settings import AppSettings
from application.inventory_order_alert.domain.value_objects.summary import EditableSummarySnapshot, SummaryLoadResult

LoadSummary = Callable[[], SummaryLoadResult | None]
LoadAppSettings = Callable[[], AppSettings]
LoadEditableSnapshot = Callable[[], EditableSummarySnapshot]
PersistEditableSnapshot = Callable[[EditableSummarySnapshot, list[dict[str, object]]], None]
