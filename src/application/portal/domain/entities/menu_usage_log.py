"""メニュー利用ログ（E-601）。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from application.portal.domain.value_objects.usage_record import USAGE_TYPES


@dataclass(frozen=True)
class MenuUsageLog:
    """メニューの利用を 1 件記録した追記専用のエンティティ。"""

    log_id: int | None
    user_id: int | None
    menu_key: str
    usage_type: str
    used_at: datetime

    def __post_init__(self) -> None:
        if self.usage_type not in USAGE_TYPES:
            raise ValueError(f"利用種別が不正です: {self.usage_type!r}")
