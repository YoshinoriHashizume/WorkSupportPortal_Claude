from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import date

from application.gonenkukumi.domain.value_objects.errors import OracleNotConfiguredError, OracleQueryError
from application.receipt_comparison.domain.value_objects.comparison_display import pending_matches
from application.receipt_comparison.domain.value_objects.comparison_sort import default_sort_params
from application.receipt_comparison.domain.value_objects.comparison_urls import comparison_url_path
from application.receipt_comparison.domain.repositories.ports import ComparisonResultRepository, FileImportRepository, PendingComparisonStore
from application.receipt_comparison.use_cases.compare import FlashMessage


@dataclass(frozen=True)
class RegisterOutcome:
    redirect_url: str
    messages: tuple[FlashMessage, ...] = ()


class RegisterComparison:
    def __init__(
        self,
        comparison_result_repository: ComparisonResultRepository,
        file_import_repository: FileImportRepository,
        *,
        comparison_base_path: str,
    ) -> None:
        self._comparison_result_repository = comparison_result_repository
        self._file_import_repository = file_import_repository
        self._comparison_base_path = comparison_base_path

    def execute(
        self,
        pending_store: PendingComparisonStore,
        *,
        comparison_type: str,
        supplier: object,
        start_date: date,
        end_date: date,
        post_values: dict[str, str],
        user_id: int,
        sort_key: str | None = None,
        sort_direction: str | None = None,
    ) -> RegisterOutcome:
        pending = pending_store.get()
        if not pending_matches(pending, comparison_type, supplier.id, start_date, end_date):
            return RegisterOutcome(
                redirect_url=comparison_url_path(
                    self._comparison_base_path,
                    comparison_type,
                    supplier.id,
                    start_date,
                    end_date,
                ),
                messages=(FlashMessage("error", "登録する比較結果がありません。先に比較を実行してください。"),),
            )

        try:
            content = base64.b64decode(str(pending.get("file_content_b64") or ""))
            rows = pending_store.rows_for_register(pending, post_values)
            file_import_id = self._file_import_repository.save_upload_file(
                comparison_type,
                supplier.id,
                str(pending.get("file_name") or "receipt.dat"),
                content,
                end_date,
                user_id,
            )
            self._comparison_result_repository.save_comparison_rows(
                comparison_type,
                supplier.id,
                file_import_id,
                rows,
                user_id,
            )
        except (ValueError, OracleNotConfiguredError, OracleQueryError) as exc:
            return RegisterOutcome(
                redirect_url=comparison_url_path(
                    self._comparison_base_path,
                    comparison_type,
                    supplier.id,
                    start_date,
                    end_date,
                    compared=1,
                    sort_key=sort_key,
                    sort_direction=sort_direction,
                ),
                messages=(FlashMessage("error", str(exc)),),
            )

        pending_store.clear()
        default_key, default_direction = default_sort_params()
        return RegisterOutcome(
            redirect_url=comparison_url_path(
                self._comparison_base_path,
                comparison_type,
                supplier.id,
                start_date,
                end_date,
                display=1,
                sort_key=default_key,
                sort_direction=default_direction,
            ),
        )
