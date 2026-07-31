from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import datetime
from zoneinfo import ZoneInfo

from application.gonenkukumi.domain.value_objects.excel_export import build_gonenkukumi_workbook
from application.gonenkukumi.domain.repositories.ports import GonenKukumiSearchGateway
from application.gonenkukumi.domain.value_objects.result import build_multi_month_result, display_months_from_query
from application.gonenkukumi.domain.value_objects.schemas import GonenKukumiSearchParams
from application.gonenkukumi.domain.value_objects.search_params import _mapping_from_query, search_params_from_mapping
from application.gonenkukumi.domain.value_objects.year_month_nav import YearMonth

FILENAME_UNSAFE_PATTERN = re.compile(r'[\\/:*?"<>|]+')
_TZ = ZoneInfo("Asia/Tokyo")


def safe_filename_part(value: object) -> str:
    return FILENAME_UNSAFE_PATTERN.sub("_", str(value or "").strip()) or "-"


def export_filename(params: GonenKukumiSearchParams) -> str:
    year_month = YearMonth.parse(params.year_month)
    timestamp = datetime.now(_TZ).strftime("%Y%m%d%H%M%S")
    return (
        f"{safe_filename_part(params.cust_code)}_"
        f"{safe_filename_part(params.cust_item)}_"
        f"{year_month.year:04d}_"
        f"{year_month.month:02d}_"
        f"{timestamp}.xlsx"
    )


class ExportExcel:
    def __init__(self, search_gateway: GonenKukumiSearchGateway) -> None:
        self._search_gateway = search_gateway

    def execute(self, query: Mapping[str, object] | object) -> tuple[bytes, str]:
        query_map = _mapping_from_query(query)
        params = search_params_from_mapping(query_map)
        raw_months = str(query_map.get("months") or "")
        result = build_multi_month_result(
            params,
            display_months_from_query(params, raw_months),
            self._search_gateway.search,
        )
        return build_gonenkukumi_workbook(result), export_filename(params)
