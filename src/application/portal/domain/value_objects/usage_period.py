"""集計期間（V-602）。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

DEFAULT_AGGREGATION_DAYS = 30
MAX_AGGREGATION_DAYS = 366

MESSAGE_BOTH_REQUIRED = "開始日と終了日の両方を指定してください。"
MESSAGE_MALFORMED = "日付の形式が正しくありません。"
MESSAGE_OUT_OF_ORDER = "開始日は終了日以前を指定してください。"
MESSAGE_TOO_LONG = f"集計期間は最大 {MAX_AGGREGATION_DAYS} 日です。期間を短くしてください。"


class AggregationPeriodError(Exception):
    """不正な集計期間。`message` に画面表示用の文言を持つ。"""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass(frozen=True)
class AggregationPeriod:
    """集計の対象期間。開始日・終了日の両端を含む。"""

    start_date: date
    end_date: date

    def __post_init__(self) -> None:
        if self.start_date > self.end_date:
            raise AggregationPeriodError(MESSAGE_OUT_OF_ORDER)
        if self.days > MAX_AGGREGATION_DAYS:
            raise AggregationPeriodError(MESSAGE_TOO_LONG)

    @property
    def days(self) -> int:
        """集計期間の日数（両端を含む）。"""
        return (self.end_date - self.start_date).days + 1


def default_aggregation_period(today: date) -> AggregationPeriod:
    """既定の集計期間（当日を終了日とする直近 30 日）を返す。"""
    return AggregationPeriod(
        start_date=today - timedelta(days=DEFAULT_AGGREGATION_DAYS - 1),
        end_date=today,
    )


def parse_aggregation_period(start: str, end: str, *, today: date) -> AggregationPeriod:
    """画面入力の文字列を集計期間として解釈する（検証規則 1・2）。"""
    start_text = (start or "").strip()
    end_text = (end or "").strip()

    if not start_text and not end_text:
        return default_aggregation_period(today)
    if not start_text or not end_text:
        raise AggregationPeriodError(MESSAGE_BOTH_REQUIRED)

    return AggregationPeriod(
        start_date=_parse_date(start_text),
        end_date=_parse_date(end_text),
    )


def _parse_date(text: str) -> date:
    try:
        return date.fromisoformat(text)
    except ValueError as error:
        raise AggregationPeriodError(MESSAGE_MALFORMED) from error
