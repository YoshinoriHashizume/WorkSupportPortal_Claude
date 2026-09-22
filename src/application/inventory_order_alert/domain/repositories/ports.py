from __future__ import annotations

from collections.abc import Callable
from datetime import date
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
        stock_stale_days: int,
        safety_days: int = ...,
        default_lead_time_days: int = ...,
        watch_months: int = ...,
        updated_by: object | None = ...,
    ) -> AppSettings: ...


#: 集計行の後処理（行, 基準日）→ 行。取込側が集計 → 後処理 → 保存 の順に適用する（05 design §6.7）。
EnrichRows = Callable[[list[dict[str, object]], date], list[dict[str, object]]]


class StockImporter(Protocol):
    """SLIMS 在庫 CSV のテキストを取り込み、取込情報を返す。

    ``enrich_rows`` は集計行を保存する前に適用する後処理（需要予測の付与など）。
    集計と保存を infrastructure が一括で行う既存の構造を壊さず、業務計算を domain に置くための最小の接点。
    """

    def __call__(
        self,
        text: str,
        *,
        user: object | None = ...,
        file_name: str = ...,
        enrich_rows: EnrichRows | None = ...,
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
        flow_quadrant: str = ...,
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
