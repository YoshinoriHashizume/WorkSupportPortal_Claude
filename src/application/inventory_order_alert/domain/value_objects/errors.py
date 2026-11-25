from __future__ import annotations

IMPORT_IN_PROGRESS_CODE = "IMPORT_IN_PROGRESS"
IMPORT_IN_PROGRESS_MESSAGE = "別のユーザーが取込中です。しばらく待って再実行してください。"


class ImportInProgressError(RuntimeError):
    """SLIMS 取込が別ユーザーによって実行中で、排他ロックを取得できなかった。

    取込は既存スナップショットを全件削除してから INSERT するため、同時実行すると
    スナップショットが部分破壊されうる（機能仕様書 §3「取込の排他」・§7.2）。
    """

    code = IMPORT_IN_PROGRESS_CODE

    def __init__(self, message: str = IMPORT_IN_PROGRESS_MESSAGE) -> None:
        super().__init__(message)


VENDOR_LOOKUP_UNAVAILABLE_MESSAGE = (
    "基幹に接続できないため仕入先コードを確認できませんでした。時間をおいて保存し直してください。"
)


class VendorLookupUnavailableError(RuntimeError):
    """基幹に接続できず、仕入先マスタで仕入先コードを確かめられない（spec/12 design §6.2・§8）。"""

    def __init__(self, message: str = VENDOR_LOOKUP_UNAVAILABLE_MESSAGE) -> None:
        super().__init__(message)
