from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from application.inventory_order_alert.domain.value_objects.app_settings import AppSettings
from application.inventory_order_alert.domain.value_objects.confirmation import (
    ConfirmationInput,
    ConfirmationRecord,
    MemoEntryRecord,
)
from application.inventory_order_alert.domain.value_objects.slims_stock import SlimsStockLocationLine
from application.inventory_order_alert.domain.value_objects.summary import (
    EditableSummarySnapshot,
    StockImportInfo,
    SummaryLoadResult,
)

LoadSummary = Callable[[], SummaryLoadResult | None]
LoadAppSettings = Callable[[], AppSettings]
LoadStockLines = Callable[[], tuple[list[SlimsStockLocationLine], StockImportInfo | None]]
LoadEditableSnapshot = Callable[[], EditableSummarySnapshot]
PersistEditableSnapshot = Callable[[EditableSummarySnapshot, list[dict[str, object]]], None]


class SaveAppSettings(Protocol):
    """設定画面（§4.2）・設定 API（§8.10）で更新できる項目を保存する。"""

    def __call__(
        self,
        *,
        warning_days: int,
        critical_enabled: bool,
        stock_stale_days: int,
        updated_by: object | None = ...,
    ) -> AppSettings: ...


class SaveWarningMonthSettings(Protocol):
    """アラート設定 API（§8.9）で更新できる月数を保存する。"""

    def __call__(
        self,
        *,
        warning_shipment_months: int,
        warning_incoming_months: int,
        updated_by: object | None = ...,
    ) -> AppSettings: ...


class StockImporter(Protocol):
    """SLIMS 在庫 CSV のテキストを取り込み、取込情報を返す。"""

    def __call__(
        self,
        text: str,
        *,
        user: object | None = ...,
        file_name: str = ...,
    ) -> StockImportInfo: ...


class HasResettableConfirmations(Protocol):
    """リセット対象の確認状況が 1 件以上あるか。"""

    def __call__(self) -> bool: ...


class SaveConfirmation(Protocol):
    """確認状況を保存する。"""

    def __call__(
        self,
        input_data: ConfirmationInput,
        *,
        confirmed_by: str,
        alert_level: str = ...,
    ) -> ConfirmationRecord: ...


class ResetAllConfirmations(Protocol):
    """全件の確認状況をリセットし、リセット件数を返す。"""

    def __call__(self) -> int: ...


class ReconcileConfirmationsAfterImport(Protocol):
    """取込後の明細に合わせて確認状況を突き合わせ、解除件数を返す。"""

    def __call__(self, rows: list[dict[str, object]]) -> int: ...


class ListConfirmationMemos(Protocol):
    """指定明細の確認メモを古い順で返す。"""

    def __call__(self, *, cust_code: str, item_cd: str) -> list[dict[str, str]]: ...


class AddConfirmationMemo(Protocol):
    """指定明細に確認メモを 1 件追加する。"""

    def __call__(
        self,
        *,
        cust_code: str,
        item_cd: str,
        content: str,
        created_by: str,
    ) -> MemoEntryRecord: ...


class ResolveUserDisplayNames(Protocol):
    """ユーザー名の集合を表示名の辞書に解決する。"""

    def __call__(self, usernames: set[str]) -> dict[str, str]: ...
