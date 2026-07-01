from __future__ import annotations

from collections.abc import Callable

from applications.inventory_order_alert.domain.app_settings import AppSettings
from applications.inventory_order_alert.domain.summary import EditableSummarySnapshot, SummaryLoadResult

LoadSummary = Callable[[], SummaryLoadResult | None]
LoadAppSettings = Callable[[], AppSettings]
LoadEditableSnapshot = Callable[[], EditableSummarySnapshot]
PersistEditableSnapshot = Callable[[EditableSummarySnapshot, list[dict[str, object]]], None]
