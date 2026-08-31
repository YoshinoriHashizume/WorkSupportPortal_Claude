from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from .year_month_nav import YearMonth, normalize_year_month

CUST_CODE_PATTERN = re.compile(r"^\d{3}$")


@dataclass(frozen=True)
class GonenKukumiSearchParams:
    cust_code: str
    cust_item: str
    option_change: str
    year_month: str
    as_of_date: date

    def to_api_dict(self) -> dict[str, object]:
        return {
            "custCode": self.cust_code,
            "custItem": self.cust_item,
            "optionChange": self.option_change,
            "yearMonth": self.year_month,
            "asOfDate": self.as_of_date.isoformat(),
        }


def parse_option_change(value: object) -> str:
    if isinstance(value, bool):
        return "1" if value else "*"
    normalized = str(value or "").strip()
    if not normalized or normalized.lower() in {"false", "off", "no"}:
        return "*"
    if normalized.lower() in {"true", "on", "yes"}:
        return "1"
    return normalized


def parse_as_of_date(value: object, year_month: str) -> date:
    text = str(value or "").strip()
    if not text:
        parsed = YearMonth.parse(year_month)
        return date(parsed.year, parsed.month, 1)
    normalized = text.replace("/", "-").replace(".", "-")
    parts = normalized.split("-")
    if len(parts) == 3 and all(part.isdigit() for part in parts):
        return date(int(parts[0]), int(parts[1]), int(parts[2]))
    raise ValueError("対象日付は YYYY-MM-DD 形式で指定してください。")


def validate_search_params(data: dict[str, object]) -> GonenKukumiSearchParams:
    cust_code = str(data.get("custCode") or data.get("cust_code") or "").strip()
    cust_item = str(data.get("custItem") or data.get("cust_item") or "").strip()
    raw_year_month = str(data.get("yearMonth") or data.get("year_month") or "").strip()
    year_month = normalize_year_month(raw_year_month)
    option_change = parse_option_change(data.get("optionChange", data.get("option_change", "*")))
    as_of_date = parse_as_of_date(data.get("asOfDate", data.get("as_of_date")), year_month)

    if not CUST_CODE_PATTERN.match(cust_code):
        raise ValueError("得意先コードは数字3桁で指定してください。")
    if len(option_change) > 20:
        raise ValueError("設変値は20文字以内で指定してください。")
    YearMonth.parse(year_month)
    return GonenKukumiSearchParams(cust_code, cust_item, option_change, year_month, as_of_date)
