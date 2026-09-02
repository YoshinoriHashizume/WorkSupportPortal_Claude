from __future__ import annotations

from dataclasses import dataclass

from application.inventory_order_alert.domain.value_objects.confirmation import STATUS_CHOICES, confirmation_status_key
from application.inventory_order_alert.domain.value_objects.dates import is_stock_stale
from application.inventory_order_alert.domain.value_objects.row_counts import RowCounts, count_rows
from application.inventory_order_alert.domain.value_objects.errors import ImportInProgressError
from application.inventory_order_alert.use_cases.import_stock import ImportStock
from application.inventory_order_alert.domain.value_objects.list_filter import (
    apply_list_filters,
    build_display_query_string,
    build_filter_options,
    parse_list_filter_params,
)
from application.inventory_order_alert.domain.repositories.ports import (
    LoadAppSettings,
    LoadSummary,
)
from application.inventory_order_alert.domain.value_objects.flow_quadrant import (
    EVALUATION_PERIODS,
    FLOW_AXIS_DORMANT,
    FLOW_AXIS_HELP_TEXTS,
    FLOW_AXIS_LABELS,
    FLOW_AXIS_LOW_FLOW,
    FlowSelection,
)
from application.inventory_order_alert.domain.value_objects.list_query import parse_list_query
from application.inventory_order_alert.domain.value_objects.list_rows import apply_flow_quadrants_to_rows
from application.inventory_order_alert.domain.value_objects.table_display import (
    PAGE_SIZE_OPTIONS,
    SORTABLE_COLUMNS,
    PaginatedRows,
    TableDisplayParams,
    apply_table_display,
    parse_table_display_params,
    single_column_sort_specs,
    sort_spec_label,
)
from application.inventory_order_alert.domain.value_objects.flow_quadrant_rules import (
    FlowQuadrantRuleRow,
    build_flow_quadrant_rule_rows,
)
from application.inventory_order_alert.domain.value_objects.dev_data_guard import looks_like_test_import
from application.inventory_order_alert.domain.value_objects.row_display import row_alert_class


@dataclass(frozen=True)
class FlowAxisOption:
    value: str
    label: str
    help_text: str


@dataclass(frozen=True)
class FlowPeriodOption:
    value: int
    key: str
    label: str


@dataclass(frozen=True)
class ListPageTableHeader:
    key: str
    label: str
    sorted: bool
    sort_index: int | None
    direction: str
    href: str


@dataclass(frozen=True)
class ListPageContext:
    rows: list[dict[str, object]]
    all_rows: list[dict[str, object]]
    paginated: PaginatedRows | None
    table_params: TableDisplayParams
    sort_spec_labels: list[str]
    list_filter: object
    filter_options: dict[str, list[str]]
    summary_total: int
    filtered_total: int
    table_headers: list[ListPageTableHeader]
    page_size_options: list[int]
    prev_href: str
    next_href: str
    counts: RowCounts
    error_message: str
    import_message: str
    stock_as_of_label: str
    stock_import_info: object | None
    has_slims_stock: bool
    has_summary: bool
    has_list_data: bool
    stock_stale: bool
    confirmation_status_choices: list[tuple[str, str]]
    flow_selection: FlowSelection
    flow_axis_options: list[FlowAxisOption]
    flow_period_options: dict[str, list[FlowPeriodOption]]
    flow_quadrant_filter: str
    flow_quadrant_rule_rows: list[FlowQuadrantRuleRow]
    test_data_warning: bool


def _rows_for_template(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    enriched: list[dict[str, object]] = []
    for row in rows:
        copied = dict(row)
        copied["alert_row_class"] = row_alert_class(row)
        copied["confirmation_status_key"] = confirmation_status_key(row)
        enriched.append(copied)
    return enriched


def _flow_axis_options() -> list[FlowAxisOption]:
    return [
        FlowAxisOption(
            value=axis,
            label=FLOW_AXIS_LABELS[axis],
            help_text=FLOW_AXIS_HELP_TEXTS[axis],
        )
        for axis in (FLOW_AXIS_LOW_FLOW, FLOW_AXIS_DORMANT)
    ]


def _flow_period_options() -> dict[str, list[FlowPeriodOption]]:
    return {
        axis: [
            FlowPeriodOption(value=period.value, key=period.key, label=period.label)
            for period in EVALUATION_PERIODS.for_axis(axis)
        ]
        for axis in (FLOW_AXIS_LOW_FLOW, FLOW_AXIS_DORMANT)
    }


class ListPage:
    def __init__(
        self,
        import_stock_usecase: ImportStock,
        load_summary: LoadSummary,
        load_app_settings: LoadAppSettings,
    ) -> None:
        self._import_stock = import_stock_usecase
        self._load_summary = load_summary
        self._load_app_settings = load_app_settings

    def execute(
        self,
        *,
        query_params: dict[str, str],
        uploaded_csv: tuple[str, bytes] | None = None,
        user: object | None = None,
    ) -> ListPageContext:
        app_settings = self._load_app_settings()
        error_message = ""
        import_message = ""
        summary = self._load_summary()
        stock_info = summary.stock_info if summary else None
        stock_as_of_label = stock_info.stock_as_of_label if stock_info else ""

        if uploaded_csv is not None:
            file_name, raw_bytes = uploaded_csv
            try:
                stock_info = self._import_stock.execute(raw_bytes, user=user, file_name=file_name)
                summary = self._load_summary()
                stock_as_of_label = stock_info.stock_as_of_label
                if stock_info.aggregation_error:
                    error_message = f"集計に失敗しました: {stock_info.aggregation_error}"
                else:
                    import_message = (
                        f"SLIMS 在庫 CSV を取り込み、{stock_info.summary_row_count} 件を集計しました"
                        f"（{stock_info.stock_as_of_label}）。"
                    )
                    if stock_info.confirmation_reset_count:
                        import_message += (
                            f" {stock_info.confirmation_reset_count} 件の確認状態を未確認に戻しました"
                            f"（アラート悪化）。"
                        )
            except ImportInProgressError as exc:
                # 排他ロックを取得できなかった場合は取込を行わず、既存スナップショットを保持する
                error_message = str(exc)
            except ValueError as exc:
                error_message = str(exc)

        all_rows: list[dict[str, object]] = summary.rows if summary else []
        if summary and summary.aggregation_error and not import_message:
            error_message = error_message or f"集計に失敗しました: {summary.aggregation_error}"

        # 判定軸・判定期間は利用者の選択で決まるため、読込時の基準判定条件から引き直す（design.md §3.1）。
        list_query = parse_list_query(query_params)
        if all_rows:
            as_of_date = (summary.as_of_date if summary else None) or list_query.as_of_date
            all_rows = apply_flow_quadrants_to_rows(
                all_rows,
                as_of_date=as_of_date,
                query=list_query,
            )

        summary_total = len(all_rows)
        filter_options = build_filter_options(all_rows)
        list_filter = parse_list_filter_params(query_params, filter_options)
        filtered_rows = apply_list_filters(all_rows, list_filter)
        counts = count_rows(filtered_rows) if filtered_rows else RowCounts()
        table_params = parse_table_display_params(query_params)
        has_list_data = bool(summary and summary.has_summary and not summary.aggregation_error)
        paginated = apply_table_display(filtered_rows, table_params) if has_list_data else None
        sort_index_map = {spec.column: index + 1 for index, spec in enumerate(table_params.sort_specs)}
        table_headers = [
            ListPageTableHeader(
                key=column,
                label=label,
                sorted=column in sort_index_map,
                sort_index=sort_index_map.get(column),
                direction=next(spec.direction for spec in table_params.sort_specs if spec.column == column)
                if column in sort_index_map
                else "",
                href="?" + build_display_query_string(
                    table_params=table_params,
                    filter_params=list_filter,
                    flow_selection=list_query.flow_selection,
                    flow_quadrant=list_query.flow_quadrant,
                    page=1,
                    sort_specs=single_column_sort_specs(table_params, column),
                ),
            )
            for column, label in SORTABLE_COLUMNS
        ]
        prev_href = ""
        next_href = ""
        if paginated:
            if paginated.has_previous:
                prev_href = "?" + build_display_query_string(
                    table_params=table_params,
                    filter_params=list_filter,
                    flow_selection=list_query.flow_selection,
                    flow_quadrant=list_query.flow_quadrant,
                    page=paginated.page - 1,
                )
            if paginated.has_next:
                next_href = "?" + build_display_query_string(
                    table_params=table_params,
                    filter_params=list_filter,
                    flow_selection=list_query.flow_selection,
                    flow_quadrant=list_query.flow_quadrant,
                    page=paginated.page + 1,
                )

        return ListPageContext(
            rows=_rows_for_template(paginated.rows) if paginated else [],
            all_rows=all_rows,
            paginated=paginated,
            table_params=table_params,
            sort_spec_labels=[sort_spec_label(spec) for spec in table_params.sort_specs],
            list_filter=list_filter,
            filter_options=filter_options,
            summary_total=summary_total,
            filtered_total=len(filtered_rows),
            table_headers=table_headers,
            page_size_options=PAGE_SIZE_OPTIONS,
            prev_href=prev_href,
            next_href=next_href,
            counts=counts,
            error_message=error_message,
            import_message=import_message,
            stock_as_of_label=stock_as_of_label,
            stock_import_info=stock_info,
            has_slims_stock=bool(stock_info and stock_info.has_data),
            has_summary=bool(summary and summary.has_summary and not summary.aggregation_error),
            has_list_data=has_list_data,
            stock_stale=is_stock_stale(
                stock_info.stock_as_of_date if stock_info else None,
                app_settings.stock_stale_days,
            ),
            confirmation_status_choices=list(STATUS_CHOICES),
            flow_selection=list_query.flow_selection,
            flow_axis_options=_flow_axis_options(),
            flow_period_options=_flow_period_options(),
            flow_quadrant_filter=list_query.flow_quadrant,
            flow_quadrant_rule_rows=build_flow_quadrant_rule_rows(),
            test_data_warning=looks_like_test_import(
                stock_info.file_name if stock_info else "",
                all_rows,
            ),
        )
