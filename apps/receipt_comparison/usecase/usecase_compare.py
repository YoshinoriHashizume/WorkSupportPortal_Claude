from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from apps.gonenkukumi.domain.errors import OracleNotConfiguredError, OracleQueryError
from apps.receipt_comparison.domain.comparison import compare_receipts
from apps.receipt_comparison.domain.comparison_sort import default_sort_params
from apps.receipt_comparison.domain.comparison_type import SUPPLIED_PARTS
from apps.receipt_comparison.domain.comparison_urls import comparison_url_path
from apps.receipt_comparison.domain.file_parser import parse_receipt_file
from apps.receipt_comparison.domain.ports import (
    ComparisonResultRepository,
    MariRowGateway,
    PendingComparisonStore,
    SupplierLookup,
)
from apps.receipt_comparison.models import SuppliedPartsReceiptSupplier
from apps.receipt_comparison.usecase.usecase_comparison_page import ComparisonPageContext, ComparisonPageUsecase


@dataclass(frozen=True)
class FlashMessage:
    level: str
    text: str


@dataclass(frozen=True)
class CompareOutcome:
    redirect_url: str | None = None
    page: ComparisonPageContext | None = None
    messages: tuple[FlashMessage, ...] = ()


class CompareUsecase:
    def __init__(
        self,
        comparison_page_usecase: ComparisonPageUsecase,
        comparison_result_repository: ComparisonResultRepository,
        mari_gateway: MariRowGateway,
        supplier_lookup: SupplierLookup,
        *,
        comparison_base_path: str,
    ) -> None:
        self._comparison_page_usecase = comparison_page_usecase
        self._comparison_result_repository = comparison_result_repository
        self._mari_gateway = mari_gateway
        self._supplier_lookup = supplier_lookup
        self._comparison_base_path = comparison_base_path

    def execute(
        self,
        pending_store: PendingComparisonStore,
        *,
        type_slug: str,
        comparison_type: str,
        supplier: object,
        start_date: date,
        end_date: date,
        file_name: str | None,
        file_content: bytes | None,
        sort_key: str,
        sort_direction: str,
        results_panel_active: bool,
    ) -> CompareOutcome:
        if file_content is None or file_name is None:
            return CompareOutcome(
                page=self._error_page(
                    pending_store,
                    type_slug,
                    comparison_type,
                    supplier,
                    start_date,
                    end_date,
                    sort_key,
                    sort_direction,
                    results_panel_active,
                ),
                messages=(FlashMessage("error", "受領書データを選択してください。"),),
            )

        messages: list[FlashMessage] = []
        try:
            receiving_places = self._supplier_lookup.receiving_places(supplier)
            match_codes = self._supplier_lookup.subcontractor_codes(supplier)
            if comparison_type == SUPPLIED_PARTS and not match_codes:
                messages.append(
                    FlashMessage(
                        "warning",
                        "子取引先が未登録です。設定画面で購買取引先コードを追加してください。",
                    )
                )
            parent_customer_code = getattr(supplier, "customer_code", "") if comparison_type == SUPPLIED_PARTS else ""
            receipt_rows = parse_receipt_file(
                comparison_type=comparison_type,
                file_name=file_name,
                content=file_content,
                subcontractor_codes=match_codes,
                receiving_places=receiving_places,
                exclusion=supplier.exclusion,
                parent_customer_code=parent_customer_code,
            )
            mari_rows = self._mari_gateway.fetch_mari_rows(
                comparison_type=comparison_type,
                supplier=supplier,
                start_date=start_date,
                end_date=end_date,
                receiving_places=receiving_places,
            )
            rows = compare_receipts(
                mari_rows,
                receipt_rows,
                self._comparison_result_repository.existing_rows_for_comparison(
                    comparison_type,
                    supplier.id,
                    start_date,
                    end_date,
                ),
                supplied_parts=comparison_type == SUPPLIED_PARTS,
            )
            if receipt_rows and mari_rows and not any(row.supplier_item_cd for row in rows if row.mari_item_cd):
                messages.append(
                    FlashMessage(
                        "warning",
                        "受領ファイルは読み取れましたが、MARIデータと一致する行がありませんでした。品番・日付・数量を確認してください。",
                    )
                )
            elif not receipt_rows and file_content.strip():
                messages.append(
                    FlashMessage(
                        "warning",
                        "取込ファイルから比較対象行を読み取れませんでした。子取引先・品番・品番設定を確認してください。",
                    )
                )
            pending_store.store(
                comparison_type=comparison_type,
                supplier_id=supplier.id,
                start_date=start_date,
                end_date=end_date,
                file_name=file_name,
                file_content=file_content,
                rows=rows,
            )
            default_key, default_direction = default_sort_params()
            return CompareOutcome(
                redirect_url=comparison_url_path(
                    self._comparison_base_path,
                    comparison_type,
                    supplier.id,
                    start_date,
                    end_date,
                    compared=1,
                    sort_key=default_key,
                    sort_direction=default_direction,
                ),
                messages=tuple(messages),
            )
        except (ValueError, OracleNotConfiguredError, OracleQueryError) as exc:
            messages.append(FlashMessage("error", str(exc)))

        return CompareOutcome(
            page=self._error_page(
                pending_store,
                type_slug,
                comparison_type,
                supplier,
                start_date,
                end_date,
                sort_key,
                sort_direction,
                results_panel_active,
            ),
            messages=tuple(messages),
        )

    def _error_page(
        self,
        pending_store: PendingComparisonStore,
        type_slug: str,
        comparison_type: str,
        supplier: object,
        start_date: date,
        end_date: date,
        sort_key: str,
        sort_direction: str,
        results_panel_active: bool,
    ) -> ComparisonPageContext:
        rows, has_pending = self._comparison_page_usecase.rows_for_page(
            pending_store,
            comparison_type,
            supplier,
            start_date,
            end_date,
            sort_key,
            sort_direction,
        )
        return self._comparison_page_usecase.build_context(
            type_slug=type_slug,
            comparison_type=comparison_type,
            supplier=supplier,
            start_date=start_date,
            end_date=end_date,
            rows=rows,
            has_pending=has_pending,
            results_panel_active=results_panel_active,
            sort_key=sort_key,
            sort_direction=sort_direction,
        )
