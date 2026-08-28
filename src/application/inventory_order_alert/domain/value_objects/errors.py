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
