"""集計期間（V-602）のテスト（TC-DOM-050〜058・060〜066）。"""

from __future__ import annotations

import dataclasses
from datetime import date

import pytest

from application.portal.domain.value_objects.usage_period import (
    AggregationPeriod,
    AggregationPeriodError,
    default_aggregation_period,
    parse_aggregation_period,
)

TODAY = date(2026, 8, 27)


def test_aggregation_period_allows_single_day():
    """TC-DOM-050: 開始日と終了日が同じ 1 日の集計期間を作れる。"""
    period = AggregationPeriod(start_date=date(2026, 8, 27), end_date=date(2026, 8, 27))

    assert period.days == 1


def test_aggregation_period_rejects_start_after_end():
    """TC-DOM-051: 開始日が終了日より後の集計期間は作れない（検証規則 3）。"""
    with pytest.raises(AggregationPeriodError) as excinfo:
        AggregationPeriod(start_date=date(2026, 8, 28), end_date=date(2026, 8, 27))

    assert excinfo.value.message == "開始日は終了日以前を指定してください。"


def test_aggregation_period_allows_365_days():
    """TC-DOM-052: 365 日の集計期間を作れる。"""
    period = AggregationPeriod(start_date=date(2025, 8, 28), end_date=date(2026, 8, 27))

    assert period.days == 365


def test_aggregation_period_allows_366_days():
    """TC-DOM-053: 上限ちょうどの 366 日の集計期間を作れる。"""
    period = AggregationPeriod(start_date=date(2025, 8, 27), end_date=date(2026, 8, 27))

    assert period.days == 366


def test_aggregation_period_rejects_367_days():
    """TC-DOM-054: 367 日の集計期間は作れない（検証規則 4）。"""
    with pytest.raises(AggregationPeriodError) as excinfo:
        AggregationPeriod(start_date=date(2025, 8, 26), end_date=date(2026, 8, 27))

    assert excinfo.value.message == "集計期間は最大 366 日です。期間を短くしてください。"


def test_aggregation_period_allows_future_end_date():
    """TC-DOM-055: 終了日が未来でも受け付ける（検証規則 5）。"""
    period = AggregationPeriod(start_date=TODAY, end_date=date(2026, 9, 30))

    assert period.end_date == date(2026, 9, 30)


def test_aggregation_period_is_immutable():
    """TC-DOM-056: 生成後に開始日を変更できない。"""
    period = AggregationPeriod(start_date=date(2026, 8, 1), end_date=date(2026, 8, 27))

    with pytest.raises(dataclasses.FrozenInstanceError):
        period.start_date = date(2026, 8, 2)


def test_aggregation_period_equals_when_same_dates():
    """TC-DOM-057: 同じ日付なら等価で、ハッシュも一致する。"""
    one = AggregationPeriod(start_date=date(2026, 8, 1), end_date=date(2026, 8, 27))
    other = AggregationPeriod(start_date=date(2026, 8, 1), end_date=date(2026, 8, 27))

    assert one == other
    assert hash(one) == hash(other)


def test_default_aggregation_period_covers_last_30_days():
    """TC-DOM-058: 既定の集計期間は当日を終了日とする直近 30 日。"""
    period = default_aggregation_period(TODAY)

    assert period.start_date == date(2026, 7, 29)
    assert period.end_date == TODAY
    assert period.days == 30


def test_parse_period_returns_default_when_both_blank():
    """TC-DOM-060: 開始日・終了日が両方空なら既定の集計期間を返す。"""
    period = parse_aggregation_period("", "", today=TODAY)

    assert period == AggregationPeriod(start_date=date(2026, 7, 29), end_date=TODAY)


def test_parse_period_rejects_blank_start():
    """TC-DOM-061: 開始日だけが空ならエラー（検証規則 1）。"""
    with pytest.raises(AggregationPeriodError) as excinfo:
        parse_aggregation_period("", "2026-08-27", today=TODAY)

    assert excinfo.value.message == "開始日と終了日の両方を指定してください。"


def test_parse_period_rejects_blank_end():
    """TC-DOM-062: 終了日だけが空ならエラー（検証規則 1）。"""
    with pytest.raises(AggregationPeriodError) as excinfo:
        parse_aggregation_period("2026-08-01", "", today=TODAY)

    assert excinfo.value.message == "開始日と終了日の両方を指定してください。"


def test_parse_period_rejects_malformed_date():
    """TC-DOM-063: yyyy-mm-dd として解釈できない日付はエラー（検証規則 2）。"""
    malformed = [
        ("2026/08/01", "2026-08-27"),
        ("2026-13-01", "2026-08-27"),
        ("abc", "2026-08-27"),
        ("2026-08-01", "2026-02-30"),
    ]

    for start, end in malformed:
        with pytest.raises(AggregationPeriodError) as excinfo:
            parse_aggregation_period(start, end, today=TODAY)
        assert excinfo.value.message == "日付の形式が正しくありません。", f"{start} / {end}"


def test_parse_period_returns_period_for_valid_dates():
    """TC-DOM-064: 正しい日付なら集計期間を返す。"""
    period = parse_aggregation_period("2026-08-01", "2026-08-27", today=TODAY)

    assert period == AggregationPeriod(start_date=date(2026, 8, 1), end_date=date(2026, 8, 27))


def test_parse_period_propagates_order_violation():
    """TC-DOM-065: 開始日 > 終了日はコンストラクタの検査がそのまま伝わる（検証規則 3）。"""
    with pytest.raises(AggregationPeriodError) as excinfo:
        parse_aggregation_period("2026-08-28", "2026-08-27", today=TODAY)

    assert excinfo.value.message == "開始日は終了日以前を指定してください。"


def test_parse_period_strips_surrounding_spaces():
    """TC-DOM-066: 前後の空白を除いて解釈する。"""
    period = parse_aggregation_period(" 2026-08-01 ", " 2026-08-27 ", today=TODAY)

    assert period == AggregationPeriod(start_date=date(2026, 8, 1), end_date=date(2026, 8, 27))
