from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace

from .schemas import GonenKukumiSearchParams
from .year_month_nav import YearMonth


def year_month_index(year_month: str) -> int:
    parsed = YearMonth.parse(year_month)
    return parsed.year * 12 + parsed.month


def month_label(base_year_month: str, panel_year_month: str) -> str:
    delta = year_month_index(panel_year_month) - year_month_index(base_year_month)
    if delta == -2:
        return "前々月"
    if delta == -1:
        return "前月"
    if delta == 0:
        return "基準"
    if delta == 1:
        return "次月"
    if delta == 2:
        return "次々月"
    if delta < 0:
        return f"{abs(delta)}か月前"
    return f"{delta}か月後"


def params_for_month(params: GonenKukumiSearchParams, year_month: str) -> GonenKukumiSearchParams:
    parsed = YearMonth.parse(year_month)
    return replace(params, year_month=parsed.format())


def display_months_from_query(params: GonenKukumiSearchParams, raw_months: str) -> list[str]:
    base_year_month = YearMonth.parse(params.year_month).format()
    values = [base_year_month]
    if raw_months:
        values.extend(str(raw_months).split(","))

    unique_months = {YearMonth.parse(value.strip()).format() for value in values if str(value).strip()}
    return sorted(unique_months, key=year_month_index)


def block_group_key(block: dict[str, object]) -> tuple[object, ...]:
    meta = block.get("meta") if isinstance(block.get("meta"), dict) else {}
    if block.get("kind") == "supplier":
        return (
            "supplier",
            meta.get("kaiso"),
            meta.get("itemCd"),
            meta.get("vendCd"),
        )
    return (
        "customer",
        meta.get("custCode"),
        meta.get("custItem"),
    )


def build_multi_month_result(
    params: GonenKukumiSearchParams,
    year_months: Sequence[str],
    search: Callable[[GonenKukumiSearchParams], dict[str, object]],
) -> dict[str, object]:
    base_year_month = YearMonth.parse(params.year_month).format()
    month_specs = [
        (year_month, month_label(base_year_month, year_month), year_month)
        for year_month in year_months
    ]
    month_results = [
        {
            "key": key,
            "label": label,
            "result": search(params_for_month(params, year_month)),
        }
        for key, label, year_month in month_specs
    ]

    current_result = next(item["result"] for item in month_results if item["result"].get("yearMonth") == base_year_month)
    grouped_blocks: dict[tuple[object, ...], dict[str, object]] = {}

    for month_result in month_results:
        result = month_result["result"]
        for block in result.get("blocks", []):
            group_key = block_group_key(block)
            grouped_block = grouped_blocks.setdefault(
                group_key,
                {
                    "kind": block.get("kind", "customer"),
                    "label": block.get("label", ""),
                    "meta": block.get("meta", {}),
                    "theme": block.get("theme", {}),
                    "monthPanels": [],
                },
            )
            grouped_block["monthPanels"].append(
                {
                    "key": month_result["key"],
                    "label": month_result["label"],
                    "yearMonth": result.get("yearMonth"),
                    "activeDays": result.get("activeDays"),
                    "holidayDays": result.get("holidayDays", []),
                    "days": result.get("days", []),
                    "rows": block.get("rows", []),
                }
            )

    return {
        **current_result,
        "months": [
            {"key": item["key"], "label": item["label"], "yearMonth": item["result"].get("yearMonth")}
            for item in month_results
        ],
        "blocks": list(grouped_blocks.values()),
    }
