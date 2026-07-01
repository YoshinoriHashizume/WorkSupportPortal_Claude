from __future__ import annotations

from typing import Callable

LoadAppSettings = Callable[[], object]
LoadLatestRows = Callable[[], object | None]
RunAggregation = Callable[[object], tuple[str, int]]
