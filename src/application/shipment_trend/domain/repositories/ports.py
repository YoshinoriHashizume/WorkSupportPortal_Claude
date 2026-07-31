from __future__ import annotations

from typing import Callable

LoadAppSettings = Callable[[], object]
LoadLatestRows = Callable[[], object | None]
RunAggregation = Callable[[object], tuple[str, int]]
CreateRefreshRecord = Callable[..., object]
SaveAlertSettingsFn = Callable[..., None]
LoadBaselineOverrides = Callable[[], dict[tuple[str, str], int]]
LoadBaselineYear = Callable[..., int | None]
SaveBaselineYearFn = Callable[..., None]
DeleteBaselineYearFn = Callable[..., bool]
