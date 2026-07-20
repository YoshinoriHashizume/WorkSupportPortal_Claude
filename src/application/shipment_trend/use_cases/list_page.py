from __future__ import annotations

from dataclasses import dataclass

from application.portal.domain.value_objects.list_table import build_table_query_string
from application.shipment_trend.domain.value_objects.alert_tier import build_alert_rule_rows
from application.shipment_trend.domain.value_objects.list_client_data import build_list_client_payload
from application.shipment_trend.domain.value_objects.list_rows import enrich_rows
from application.shipment_trend.domain.value_objects.list_filter import (
    ListFilterParams,
    apply_list_filters,
    build_display_query_string,
    build_filter_options,
    parse_list_filter_params,
)
from application.shipment_trend.domain.repositories.ports import LoadAppSettings, LoadLatestRows
from application.shipment_trend.domain.value_objects.table_display import (
    PAGE_SIZE_OPTIONS,
    apply_table_display,
    build_sort_links,
    parse_page_params,
    parse_table_display_params,
    sort_spec_labels,
)
from application.shipment_trend.domain.value_objects.trend_metrics import hydrate_rows_metrics
from application.shipment_trend.use_cases.refresh_data import RefreshData


THRESHOLD_OPTIONS = (5, 10, 15, 20, 25, 30, 40, 50)


@dataclass(frozen=True)
class ListPageContext:
    rows: list[dict[str, object]]
    all_rows: list[dict[str, object]]
    paginated: object
    sort_specs: tuple
    sort_spec_labels: list[str]
    list_filter: ListFilterParams
    filter_options: object
    summary_total: int
    filtered_total: int
    table_headers: list[dict[str, object]]
    page_size_options: tuple[int, ...]
    prev_href: str
    next_href: str
    error_message: str
    refresh_message: str
    has_list_data: bool
    has_summary: bool
    as_of_label: str
    alert_rule_rows: list[dict[str, str]]
    decrease_threshold_pct: float
    increase_threshold_pct: float
    threshold_options: tuple[int, ...]
    list_client_payload: dict[str, object] | None


class ListPage:
    def __init__(
        self,
        load_summary: LoadLatestRows,
        load_settings: LoadAppSettings,
        refresh_data: RefreshData,
    ) -> None:
        self._load_summary = load_summary
        self._load_settings = load_settings
        self._refresh_data = refresh_data

    def execute(
        self,
        *,
        query_params: dict[str, str],
        refresh_requested: bool,
        user: object,
    ) -> ListPageContext:
        refresh_message = ""
        error_message = ""
        if refresh_requested:
            result = self._refresh_data.execute(user=user)
            refresh_message = result.message
            if result.error:
                error_message = result.error

        summary = self._load_summary()
        settings = self._load_settings()
        raw_rows = summary.rows if summary else []
        as_of_date = summary.as_of_date if summary else None
        all_rows = hydrate_rows_metrics(raw_rows, as_of_date)
        if summary and summary.aggregation_error and not error_message:
            error_message = summary.aggregation_error

        filter_options = build_filter_options(all_rows)
        list_filter = parse_list_filter_params(query_params, filter_options)
        filtered_rows = apply_list_filters(all_rows, list_filter)
        sort_specs = parse_table_display_params(query_params)
        page, page_size = parse_page_params(query_params)
        paginated = apply_table_display(
            filtered_rows,
            sort_specs=sort_specs,
            page=page,
            page_size=page_size,
        )

        base_path = "/app/sales/shipment-trend"
        filter_query = build_display_query_string(
            filter_params=list_filter,
            sort_query="",
        )
        table_query = build_table_query_string(
            sort_specs=sort_specs,
            page=paginated.page,
            page_size=paginated.page_size,
        )
        prev_href = ""
        next_href = ""
        if paginated.has_previous:
            prev_query = build_table_query_string(
                sort_specs=sort_specs,
                page=paginated.page - 1,
                page_size=paginated.page_size,
            )
            prev_href = f"{base_path}?{prev_query}"
            if filter_query:
                prev_href = f"{prev_href}&{filter_query}"
        if paginated.has_next:
            next_query = build_table_query_string(
                sort_specs=sort_specs,
                page=paginated.page + 1,
                page_size=paginated.page_size,
            )
            next_href = f"{base_path}?{next_query}"
            if filter_query:
                next_href = f"{next_href}&{filter_query}"

        table_headers = build_sort_links(
            base_path=base_path,
            sort_specs=sort_specs,
            page=paginated.page,
            page_size=paginated.page_size,
            filter_query=filter_query,
        )

        as_of_label = ""
        if summary and summary.as_of_date:
            as_of_label = (
                f"{summary.as_of_date.year}年{summary.as_of_date.month}月{summary.as_of_date.day}日"
            )

        display_rows = enrich_rows(list(paginated.rows), settings)
        list_client_payload = (
            build_list_client_payload(
                all_rows=all_rows,
                filter_options=filter_options,
                settings=settings,
            )
            if all_rows
            else None
        )

        return ListPageContext(
            rows=display_rows,
            all_rows=all_rows,
            paginated=paginated,
            sort_specs=sort_specs,
            sort_spec_labels=sort_spec_labels(sort_specs),
            list_filter=list_filter,
            filter_options=filter_options,
            summary_total=len(all_rows),
            filtered_total=len(filtered_rows),
            table_headers=table_headers,
            page_size_options=PAGE_SIZE_OPTIONS,
            prev_href=prev_href,
            next_href=next_href,
            error_message=error_message,
            refresh_message=refresh_message,
            has_list_data=bool(all_rows),
            has_summary=summary is not None and bool(summary.rows or summary.aggregation_error),
            as_of_label=as_of_label,
            alert_rule_rows=build_alert_rule_rows(
                decrease_threshold_pct=settings.decrease_threshold_pct,
                increase_threshold_pct=settings.increase_threshold_pct,
            ),
            decrease_threshold_pct=settings.decrease_threshold_pct,
            increase_threshold_pct=settings.increase_threshold_pct,
            threshold_options=THRESHOLD_OPTIONS,
            list_client_payload=list_client_payload,
        )
