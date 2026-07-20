from __future__ import annotations

from application.receipt_comparison.domain.repositories.ports import ComparisonResultRepository


class UpdateResults:
    def __init__(self, comparison_result_repository: ComparisonResultRepository) -> None:
        self._comparison_result_repository = comparison_result_repository

    def execute(
        self,
        *,
        comparison_type: str,
        result_ids: list[str],
        post_values: dict[str, str],
        user_id: int,
    ) -> None:
        self._comparison_result_repository.update_existing_results_from_post(
            comparison_type,
            result_ids,
            post_values,
            user_id,
        )
