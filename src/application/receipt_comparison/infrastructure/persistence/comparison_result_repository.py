from __future__ import annotations

from datetime import date
from typing import Any

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.utils import timezone
from pathlib import Path

from application.receipt_comparison.domain.value_objects.comparison import ComparisonRow
from application.receipt_comparison.models import ReceiptFlag
from application.receipt_comparison.infrastructure.persistence.model_registry import comparison_result_model, file_import_model


def existing_rows_for_display(
    comparison_type: str,
    supplier_id: int,
    start_date: date,
    end_date: date,
) -> list[Any]:
    from application.receipt_comparison.infrastructure.persistence.model_registry import supplier_model

    supplier = supplier_model(comparison_type).objects.get(id=supplier_id)
    result_model = comparison_result_model(comparison_type)
    in_range = result_model.objects.filter(
        supplier=supplier,
        file_import__receipt_date__range=(start_date, end_date),
    )
    carry_over = result_model.objects.filter(
        supplier=supplier,
        file_import__receipt_date__lt=start_date,
    ).exclude(receipt_flag=ReceiptFlag.OK)
    return list((in_range | carry_over).select_related("file_import").order_by("receipt_flag", "mari_item_cd", "supplier_item_cd"))


def existing_rows_for_comparison(
    comparison_type: str,
    supplier_id: int,
    start_date: date,
    end_date: date,
) -> list[ComparisonRow]:
    return [
        ComparisonRow(
            existing_id=row.id,
            receipt_flag=row.receipt_flag,
            mari_item_cd=row.mari_item_cd,
            mari_date=row.mari_date,
            mari_qty=row.mari_qty,
            delivery_place=row.delivery_place,
            supplier_item_cd=row.supplier_item_cd,
            supplier_delivery_month_day=row.supplier_delivery_month_day,
            supplier_qty=row.supplier_qty,
            supplier_cancel_qty=row.supplier_cancel_qty,
            supplier_name=row.supplier_name,
            remarks=row.remarks,
        )
        for row in existing_rows_for_display(comparison_type, supplier_id, start_date, end_date)
    ]


def save_comparison_rows(
    comparison_type: str,
    supplier_id: int,
    file_import_id: int,
    rows: list[ComparisonRow],
    user_id: int,
) -> None:
    from django.contrib.auth import get_user_model

    from application.receipt_comparison.infrastructure.persistence.model_registry import supplier_model

    supplier = supplier_model(comparison_type).objects.get(id=supplier_id)
    file_import = file_import_model(comparison_type).objects.get(id=file_import_id)
    user = get_user_model().objects.get(pk=user_id)
    result_model = comparison_result_model(comparison_type)
    for row in rows:
        values = {
            "supplier": supplier,
            "file_import": file_import,
            "receipt_flag": row.receipt_flag,
            "mari_item_cd": row.mari_item_cd,
            "mari_date": row.mari_date,
            "mari_qty": row.mari_qty,
            "delivery_place": row.delivery_place,
            "supplier_item_cd": row.supplier_item_cd,
            "supplier_delivery_month_day": row.supplier_delivery_month_day,
            "supplier_qty": row.supplier_qty,
            "supplier_cancel_qty": row.supplier_cancel_qty,
            "supplier_name": row.supplier_name,
            "remarks": row.remarks,
            "updated_by": user,
        }
        if row.existing_id:
            result_model.objects.filter(id=row.existing_id, supplier=supplier).update(**values)
        else:
            result_model.objects.create(**values)


def update_existing_results(
    comparison_type: str,
    updates: list[tuple[int, int, str]],
    user_id: int,
) -> None:
    from django.contrib.auth import get_user_model

    user = get_user_model().objects.get(pk=user_id)
    result_model = comparison_result_model(comparison_type)
    for result_id, receipt_flag, remarks in updates:
        result = result_model.objects.get(id=result_id)
        result.receipt_flag = receipt_flag
        result.remarks = remarks
        result.updated_by = user
        result.save(update_fields=["receipt_flag", "remarks", "updated_by", "updated_at"])


def update_existing_results_from_post(
    comparison_type: str,
    result_ids: list[str],
    post_values: dict[str, str],
    user_id: int,
) -> None:
    from django.contrib.auth import get_user_model

    user = get_user_model().objects.get(pk=user_id)
    result_model = comparison_result_model(comparison_type)
    for result_id in result_ids:
        result = result_model.objects.get(id=result_id)
        result.receipt_flag = int(post_values.get(f"receipt_flag_{result_id}", result.receipt_flag))
        result.remarks = post_values.get(f"remarks_{result_id}", "")
        result.updated_by = user
        result.save(update_fields=["receipt_flag", "remarks", "updated_by", "updated_at"])


class DjangoComparisonResultRepository:
    def existing_rows_for_display(
        self,
        comparison_type: str,
        supplier_id: int,
        start_date: date,
        end_date: date,
    ) -> list[Any]:
        return existing_rows_for_display(comparison_type, supplier_id, start_date, end_date)

    def existing_rows_for_comparison(
        self,
        comparison_type: str,
        supplier_id: int,
        start_date: date,
        end_date: date,
    ) -> list[ComparisonRow]:
        return existing_rows_for_comparison(comparison_type, supplier_id, start_date, end_date)

    def save_comparison_rows(
        self,
        comparison_type: str,
        supplier_id: int,
        file_import_id: int,
        rows: list[ComparisonRow],
        user_id: int,
    ) -> None:
        save_comparison_rows(comparison_type, supplier_id, file_import_id, rows, user_id)

    def update_existing_results(
        self,
        comparison_type: str,
        updates: list[tuple[int, int, str]],
        user_id: int,
    ) -> None:
        update_existing_results(comparison_type, updates, user_id)

    def update_existing_results_from_post(
        self,
        comparison_type: str,
        result_ids: list[str],
        post_values: dict[str, str],
        user_id: int,
    ) -> None:
        update_existing_results_from_post(comparison_type, result_ids, post_values, user_id)


def save_upload_file(
    comparison_type: str,
    supplier_id: int,
    original_name: str,
    content: bytes,
    receipt_date: date,
    user_id: int,
) -> int:
    from application.receipt_comparison.infrastructure.persistence.model_registry import supplier_model

    supplier = supplier_model(comparison_type).objects.get(id=supplier_id)
    storage = FileSystemStorage(location=Path(settings.BASE_DIR) / "var" / "receipt_uploads")
    stored_name = f"{timezone.localtime():%Y%m%d%H%M%S}_{comparison_type}_{supplier.id}_{Path(original_name).name}"
    storage.save(stored_name, content=ContentFile(content))
    file_import = file_import_model(comparison_type).objects.create(
        supplier=supplier,
        original_file_name=original_name,
        stored_file_name=stored_name,
        receipt_date=receipt_date,
        imported_by_id=user_id,
    )
    return file_import.id


class DjangoFileImportRepository:
    def save_upload_file(
        self,
        comparison_type: str,
        supplier_id: int,
        original_name: str,
        content: bytes,
        receipt_date: date,
        user_id: int,
    ) -> int:
        return save_upload_file(comparison_type, supplier_id, original_name, content, receipt_date, user_id)
