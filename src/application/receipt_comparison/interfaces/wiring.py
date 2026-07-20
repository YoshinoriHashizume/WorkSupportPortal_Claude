from __future__ import annotations

from django.urls import reverse

from application.receipt_comparison.domain.value_objects.comparison_type import UnknownComparisonTypeError, comparison_type_from_slug
from application.receipt_comparison.domain.value_objects.settings_labels import customer_digit_length
from application.receipt_comparison.infrastructure.oracle.mari_gateway import OracleMariRowGateway
from application.receipt_comparison.infrastructure.oracle.receipt_choices import OracleReceiptChoiceGateway
from application.receipt_comparison.infrastructure.session.pending_comparison_store import HttpPendingComparisonStore
from application.receipt_comparison.infrastructure.persistence.comparison_result_repository import (
    DjangoComparisonResultRepository,
    DjangoFileImportRepository,
)
from application.receipt_comparison.infrastructure.persistence.settings_repository import DjangoSettingsRepository
from application.receipt_comparison.infrastructure.persistence.supplier_lookup import DjangoSupplierLookup
from application.receipt_comparison.infrastructure.persistence.model_registry import (
    list_suppliers,
    list_suppliers_for_settings,
    supplier_model,
)
from application.receipt_comparison.use_cases.compare import Compare
from application.receipt_comparison.use_cases.comparison_page import ComparisonPage
from application.receipt_comparison.use_cases.export_csv import ExportCsv
from application.receipt_comparison.use_cases.register import RegisterComparison
from application.receipt_comparison.use_cases.settings import SettingsPage, SettingsPost
from application.receipt_comparison.use_cases.update_results import UpdateResults


def pending_comparison_store(request) -> HttpPendingComparisonStore:
    return HttpPendingComparisonStore(request)


def _comparison_base_path() -> str:
    return reverse("receipt_comparison:comparison")


def _settings_base_path() -> str:
    return reverse("receipt_comparison:settings")


def comparison_page_usecase() -> ComparisonPage:
    return ComparisonPage(
        DjangoComparisonResultRepository(),
        lambda comparison_type: list(list_suppliers(comparison_type)),
        comparison_base_path=_comparison_base_path(),
    )


def compare_usecase() -> Compare:
    page = comparison_page_usecase()
    return Compare(
        page,
        DjangoComparisonResultRepository(),
        OracleMariRowGateway(),
        DjangoSupplierLookup(),
        comparison_base_path=_comparison_base_path(),
    )


def register_comparison_usecase() -> RegisterComparison:
    return RegisterComparison(
        DjangoComparisonResultRepository(),
        DjangoFileImportRepository(),
        comparison_base_path=_comparison_base_path(),
    )


def export_csv_usecase() -> ExportCsv:
    return ExportCsv(comparison_page_usecase())


def update_results_usecase() -> UpdateResults:
    return UpdateResults(DjangoComparisonResultRepository())


def settings_page_usecase() -> SettingsPage:
    return SettingsPage(
        OracleReceiptChoiceGateway(),
        lambda comparison_type: list(list_suppliers_for_settings(comparison_type)),
        settings_base_path=_settings_base_path(),
        customer_digit_length_for=customer_digit_length,
    )


def settings_post_usecase() -> SettingsPost:
    return SettingsPost(DjangoSettingsRepository(), settings_base_path=_settings_base_path())


def slug_to_comparison_type(slug: str) -> str:
    try:
        return comparison_type_from_slug(slug)
    except UnknownComparisonTypeError as exc:
        from django.http import Http404

        raise Http404 from exc
