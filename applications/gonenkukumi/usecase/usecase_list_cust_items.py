from __future__ import annotations

from datetime import date

from applications.gonenkukumi.domain.ports import GonenKukumiSearchGateway
from applications.gonenkukumi.domain.schemas import parse_as_of_date


class ListCustItemsUsecase:
    def __init__(self, search_gateway: GonenKukumiSearchGateway) -> None:
        self._search_gateway = search_gateway

    def execute(self, cust_code: str, keyword: str, as_of_date_raw: object, year_month_raw: object) -> list[dict[str, str]]:
        if not cust_code:
            raise ValueError("得意先コードを指定してください。")
        as_of_date = parse_as_of_date(
            as_of_date_raw,
            year_month_raw or date.today().strftime("%Y-%m"),
        )
        return self._search_gateway.list_cust_items(cust_code, keyword, as_of_date)
