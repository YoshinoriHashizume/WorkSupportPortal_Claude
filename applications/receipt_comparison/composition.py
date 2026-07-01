from __future__ import annotations

from django.urls import reverse

from applications.receipt_comparison.domain.comparison_type import UnknownComparisonTypeError, comparison_type_from_slug
from applications.receipt_comparison.domain.settings_labels import customer_digit_length
from applications.receipt_comparison.infrastructure.oracle.mari_gateway import OracleMariRowGateway
from applications.receipt_comparison.infrastructure.oracle.receipt_choices import OracleReceiptChoiceGateway
from applications.receipt_comparison.infrastructure.session.pending_comparison_store import HttpPendingComparisonStore
from applications.receipt_comparison.infrastructure.persistence.comparison_result_repository import (
    DjangoComparisonResultRepository,
    DjangoFileImportRepository,
)
from applications.receipt_comparison.infrastructure.persistence.settings_repository import DjangoSettingsRepository
from applications.receipt_comparison.infrastructure.persistence.supplier_lookup import DjangoSupplierLookup
from applications.receipt_comparison.infrastructure.persistence.model_registry import (
    list_suppliers,
    list_suppliers_for_settings,
    supplier_model,
)
from applications.receipt_comparison.usecase.usecase_compare import CompareUsecase
from applications.receipt_comparison.usecase.usecase_comparison_page import ComparisonPageUsecase
from applications.receipt_comparison.usecase.usecase_export_csv import ExportCsvUsecase
from applications.receipt_comparison.usecase.usecase_register import RegisterComparisonUsecase
from applications.receipt_comparison.usecase.usecase_settings import SettingsPageUsecase, SettingsPostUsecase
from applications.receipt_comparison.usecase.usecase_update_results import UpdateResultsUsecase


def pending_comparison_store(request) -> HttpPendingComparisonStore:
    return HttpPendingComparisonStore(request)


def _comparison_base_path() -> str:
    return reverse("receipt_comparison:comparison")


def _settings_base_path() -> str:
    return reverse("receipt_comparison:settings")


def comparison_page_usecase() -> ComparisonPageUsecase:
    return ComparisonPageUsecase(
        DjangoComparisonResultRepository(),
        lambda comparison_type: list(list_suppliers(comparison_type)),
        comparison_base_path=_comparison_base_path(),
    )


def compare_usecase() -> CompareUsecase:
    page = comparison_page_usecase()
    return CompareUsecase(
        page,
        DjangoComparisonResultRepository(),
        OracleMariRowGateway(),
        DjangoSupplierLookup(),
        comparison_base_path=_comparison_base_path(),
    )


def register_comparison_usecase() -> RegisterComparisonUsecase:
    return RegisterComparisonUsecase(
        DjangoComparisonResultRepository(),
        DjangoFileImportRepository(),
        comparison_base_path=_comparison_base_path(),
    )


def export_csv_usecase() -> ExportCsvUsecase:
    return ExportCsvUsecase(comparison_page_usecase())


def update_results_usecase() -> UpdateResultsUsecase:
    return UpdateResultsUsecase(DjangoComparisonResultRepository())


def settings_page_usecase() -> SettingsPageUsecase:
    return SettingsPageUsecase(
        OracleReceiptChoiceGateway(),
        lambda comparison_type: list(list_suppliers_for_settings(comparison_type)),
        settings_base_path=_settings_base_path(),
        customer_digit_length_for=customer_digit_length,
    )


def settings_post_usecase() -> SettingsPostUsecase:
    return SettingsPostUsecase(DjangoSettingsRepository(), settings_base_path=_settings_base_path())


def slug_to_comparison_type(slug: str) -> str:
    try:
        return comparison_type_from_slug(slug)
    except UnknownComparisonTypeError as exc:
        from django.http import Http404

        raise Http404 from exc
