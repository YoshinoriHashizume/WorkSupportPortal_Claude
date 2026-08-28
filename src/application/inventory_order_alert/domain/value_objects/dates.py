from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

#: 業務日付は日本時間で判定する。
JST = ZoneInfo("Asia/Tokyo")


def today_jst() -> date:
    return datetime.now(JST).date()


def parse_optional_ymd(value: str, *, today: date | None = None) -> date:
    if not value.strip():
        return today or date.today()
    normalized = value.strip().replace("-", "/")
    return datetime.strptime(normalized, "%Y/%m/%d").date()


def to_date(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def format_stock_as_of_label(stock_date: date) -> str:
    return f"{stock_date.year}年{stock_date.month}月{stock_date.day}日時点の在庫"


def format_display_datetime(value: datetime | None) -> str:
    if value is None:
        return ""
    localized = value.astimezone() if value.tzinfo is not None else value
    return localized.strftime("%Y/%m/%d %H:%M")


def add_calendar_months(base: date, months: int) -> date:
    """base の暦上 N か月後の同日（末日は対象月の末日に合わせる）。"""
    month_index = base.month - 1 + months
    year = base.year + month_index // 12
    month = month_index % 12 + 1
    if month == 12:
        next_month_first = date(year + 1, 1, 1)
    else:
        next_month_first = date(year, month + 1, 1)
    last_day_of_month = next_month_first - timedelta(days=1)
    return date(year, month, min(base.day, last_day_of_month.day))


def has_passed_calendar_months(*, start: date, end: date, months: int) -> bool:
    return end >= add_calendar_months(start, months)


def is_within_calendar_months(*, start: date, end: date, months: int) -> bool:
    return start < end <= add_calendar_months(start, months)


def is_stock_stale(
    stock_as_of_date: date | None,
    stock_stale_days: int,
    *,
    today: date | None = None,
) -> bool:
    """SLIMS 在庫データが陳腐化しているか（§4.1.1 / §13.1）。

    在庫日付が未取得の場合は陳腐化とみなさない。
    """
    if stock_as_of_date is None:
        return False
    reference = today or today_jst()
    return (reference - stock_as_of_date).days > stock_stale_days
