from __future__ import annotations

from typing import Any

from django.db import models

from apps.receipt_comparison.domain.comparison_type import FINISHED_PRODUCT, SUPPLIED_PARTS
from apps.receipt_comparison.models import (
    FinishedProductComparisonResult,
    FinishedProductFileImport,
    FinishedProductReceiptSupplier,
    FinishedProductReceivingSetting,
    SuppliedPartsComparisonResult,
    SuppliedPartsFileImport,
    SuppliedPartsReceiptSupplier,
    SuppliedPartsReceivingSetting,
)


SupplierModel = type[FinishedProductReceiptSupplier] | type[SuppliedPartsReceiptSupplier]
ReceivingSettingModel = type[FinishedProductReceivingSetting] | type[SuppliedPartsReceivingSetting]
FileImportModel = type[FinishedProductFileImport] | type[SuppliedPartsFileImport]
ComparisonResultModel = type[FinishedProductComparisonResult] | type[SuppliedPartsComparisonResult]


def supplier_model(comparison_type: str) -> SupplierModel:
    if comparison_type == FINISHED_PRODUCT:
        return FinishedProductReceiptSupplier
    if comparison_type == SUPPLIED_PARTS:
        return SuppliedPartsReceiptSupplier
    raise ValueError("正しい比較区分が読み込まれませんでした。")


def receiving_setting_model(comparison_type: str) -> ReceivingSettingModel:
    if comparison_type == FINISHED_PRODUCT:
        return FinishedProductReceivingSetting
    if comparison_type == SUPPLIED_PARTS:
        return SuppliedPartsReceivingSetting
    raise ValueError("正しい比較区分が読み込まれませんでした。")


def file_import_model(comparison_type: str) -> FileImportModel:
    if comparison_type == FINISHED_PRODUCT:
        return FinishedProductFileImport
    if comparison_type == SUPPLIED_PARTS:
        return SuppliedPartsFileImport
    raise ValueError("正しい比較区分が読み込まれませんでした。")


def comparison_result_model(comparison_type: str) -> ComparisonResultModel:
    if comparison_type == FINISHED_PRODUCT:
        return FinishedProductComparisonResult
    if comparison_type == SUPPLIED_PARTS:
        return SuppliedPartsComparisonResult
    raise ValueError("正しい比較区分が読み込まれませんでした。")


def get_supplier(
    comparison_type: str,
    supplier_id: object,
) -> FinishedProductReceiptSupplier | SuppliedPartsReceiptSupplier:
    return supplier_model(comparison_type).objects.get(id=supplier_id)


def list_suppliers(comparison_type: str) -> models.QuerySet[Any]:
    return supplier_model(comparison_type).objects.all()


def list_suppliers_for_settings(comparison_type: str) -> models.QuerySet[Any]:
    queryset = list_suppliers(comparison_type).prefetch_related("receiving_settings")
    if comparison_type == SUPPLIED_PARTS:
        queryset = queryset.prefetch_related("subcontractors")
    return queryset
