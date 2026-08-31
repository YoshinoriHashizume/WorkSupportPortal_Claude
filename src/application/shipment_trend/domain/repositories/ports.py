from __future__ import annotations

from typing import Protocol

from application.shipment_trend.domain.value_objects.app_settings import AppSettings
from application.shipment_trend.domain.value_objects.summary import SummaryLoadResult

#: 集計実行の履歴レコード。永続化層が発行する識別子であり、ドメインは中身を解釈しない。
RefreshRecord = object


class LoadAppSettings(Protocol):
    """アラート閾値設定を読み込む。"""

    def __call__(self) -> AppSettings: ...


class LoadLatestRows(Protocol):
    """最新の集計スナップショットを読み込む。未集計なら None。"""

    def __call__(self) -> SummaryLoadResult | None: ...


class CreateRefreshRecord(Protocol):
    """集計実行の履歴レコードを新規作成する。"""

    def __call__(self, *, user: object | None) -> RefreshRecord: ...


class RunAggregation(Protocol):
    """基幹 Oracle から出荷実績を集計する。(エラーメッセージ, 件数) を返す。"""

    def __call__(self, refresh_record: RefreshRecord) -> tuple[str, int]: ...


class SaveAlertSettingsFn(Protocol):
    """アラート閾値設定を保存する。"""

    def __call__(self, settings: AppSettings, *, updated_by: object | None) -> None: ...


class LoadBaselineOverrides(Protocol):
    """比較基準年オーバーライドを (得意先コード, 品目コード) -> 年度 で返す。"""

    def __call__(self) -> dict[tuple[str, str], int]: ...


class LoadBaselineYear(Protocol):
    """指定明細の比較基準年を返す。未設定なら None。"""

    def __call__(self, *, cust_code: str, item_cd: str) -> int | None: ...


class SaveBaselineYearFn(Protocol):
    """指定明細の比較基準年を保存する。"""

    def __call__(
        self,
        *,
        cust_code: str,
        item_cd: str,
        baseline_fiscal_year: int,
        updated_by: object | None,
    ) -> None: ...


class DeleteBaselineYearFn(Protocol):
    """指定明細の比較基準年を削除する。削除できたら True。"""

    def __call__(self, *, cust_code: str, item_cd: str) -> bool: ...
