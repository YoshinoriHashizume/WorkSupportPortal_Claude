from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date

YEAR_MONTH_PATTERN = re.compile(r"^\d{4}-\d{2}$")
ESCAPED_UNICODE_PATTERN = re.compile(r"[\\¥]u[0-9a-fA-F]{4}")
COMPACT_YEAR_MONTH_PATTERN = re.compile(r"^(?P<year>\d{4})(?P<month>\d{2})$")
SEPARATED_YEAR_MONTH_PATTERN = re.compile(r"(?P<year>\d{4})\D+(?P<month>\d{1,2})")
MONTH_ONLY_PATTERN = re.compile(r"^\D*(?P<month>\d{1,2})\D*$")

FULLWIDTH_DIGITS = str.maketrans("０１２３４５６７８９", "0123456789")


def normalize_year_month(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", str(value or "")).strip().translate(FULLWIDTH_DIGITS)
    normalized = ESCAPED_UNICODE_PATTERN.sub("", normalized)
    compact = re.sub(r"\s+", "", normalized)

    compact_match = COMPACT_YEAR_MONTH_PATTERN.match(compact)
    if compact_match:
        month = int(compact_match.group("month"))
        if 1 <= month <= 12:
            return f"{int(compact_match.group('year')):04d}-{month:02d}"

    separated_match = SEPARATED_YEAR_MONTH_PATTERN.search(compact)
    if separated_match:
        month = int(separated_match.group("month"))
        if 1 <= month <= 12:
            return f"{int(separated_match.group('year')):04d}-{month:02d}"

    month_only_match = MONTH_ONLY_PATTERN.match(compact)
    if month_only_match:
        month = int(month_only_match.group("month"))
        if 1 <= month <= 12:
            return f"{date.today().year:04d}-{month:02d}"

    return compact


@dataclass(frozen=True)
class YearMonth:
    year: int
    month: int

    @classmethod
    def parse(cls, value: str) -> "YearMonth":
        value = normalize_year_month(value)
        if not YEAR_MONTH_PATTERN.match(value):
            raise ValueError("年月は YYYY-MM 形式で指定してください。")
        year, month = value.split("-", 1)
        ym = cls(int(year), int(month))
        if ym.month < 1 or ym.month > 12:
            raise ValueError("月は 01 から 12 の範囲で指定してください。")
        return ym

    def add_months(self, amount: int) -> "YearMonth":
        zero_based = self.year * 12 + (self.month - 1) + amount
        return YearMonth(zero_based // 12, zero_based % 12 + 1)

    def format(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"


def compare_ym(left: str, right: str) -> int:
    left_ym = YearMonth.parse(left)
    right_ym = YearMonth.parse(right)
    left_index = left_ym.year * 12 + left_ym.month
    right_index = right_ym.year * 12 + right_ym.month
    return (left_index > right_index) - (left_index < right_index)


def previous_month(value: str) -> str:
    return YearMonth.parse(value).add_months(-1).format()


def next_month(value: str) -> str:
    return YearMonth.parse(value).add_months(1).format()
