from __future__ import annotations

import re
from collections.abc import Mapping

from django.utils import timezone

from applications.gonenkukumi.domain.excel_export import build_gonenkukumi_workbook
from applications.gonenkukumi.domain.ports import GonenKukumiSearchGateway
from applications.gonenkukumi.domain.result import build_multi_month_result, display_months_from_query
from applications.gonenkukumi.domain.schemas import GonenKukumiSearchParams
from applications.gonenkukumi.domain.search_params import _mapping_from_query, search_params_from_mapping
from applications.gonenkukumi.domain.year_month_nav import YearMonth

FILENAME_UNSAFE_PATTERN = re.compile(r'[\\/:*?"<>|]+')


def safe_filename_part(value: object) -> str:
    return FILENAME_UNSAFE_PATTERN.sub("_", str(value or "").strip()) or "-"


def export_filename(params: GonenKukumiSearchParams) -> str:
    year_month = YearMonth.parse(params.year_month)
    timestamp = timezone.localtime().strftime("%Y%m%d%H%M%S")
    return (
        f"{safe_filename_part(params.cust_code)}_"
        f"{safe_filename_part(params.cust_item)}_"
        f"{year_month.year:04d}_"
        f"{year_month.month:02d}_"
        f"{timestamp}.xlsx"
    )


class ExportExcelUsecase:
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
