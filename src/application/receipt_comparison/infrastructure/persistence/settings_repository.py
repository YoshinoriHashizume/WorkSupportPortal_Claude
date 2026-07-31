from __future__ import annotations

from django.db import transaction
from django.shortcuts import get_object_or_404

from application.receipt_comparison.domain.value_objects.comparison_urls import is_fixed_digit_code
from application.receipt_comparison.infrastructure.oracle.receipt_choices import lookup_customer_name, lookup_vendor_name
from application.receipt_comparison.infrastructure.oracle.vendors import VENDOR_CODE_DIGIT_LENGTH
from application.receipt_comparison.models import (
    FinishedProductReceiptSupplier,
    ReceiptComparisonType,
    SuppliedPartsReceiptSupplier,
    SuppliedPartsSubcontractor,
)
from application.receipt_comparison.domain.value_objects.comparison_type import is_finished_product
from application.receipt_comparison.domain.value_objects.settings_labels import customer_digit_length, settings_target_label
from application.receipt_comparison.infrastructure.persistence.model_registry import (
    comparison_result_model,
    file_import_model,
    receiving_setting_model,
)


class SettingsActionError(ValueError):
    pass


class SettingsActionMessage:
    def __init__(self, level: str, text: str) -> None:
        self.level = level
        self.text = text


class DjangoSettingsRepository:
    def handle_post(self, comparison_type: str, action: str | None, post_data: dict[str, str], user: object) -> list[SettingsActionMessage]:
        if is_finished_product(comparison_type):
            return self._handle_finished_product(action, post_data, user)
        return self._handle_supplied_parts(action, post_data, user)

    def _handle_finished_product(self, action: str | None, post_data: dict[str, str], user: object) -> list[SettingsActionMessage]:
        if action == "add_supplier":
            customer_code = (post_data.get("customer_code") or "").strip()
            if not is_fixed_digit_code(customer_code, 3):
                return [SettingsActionMessage("error", "得意先は3桁で選択してください。")]
            direct_delivery_customer_code = (post_data.get("direct_delivery_customer_code") or "").strip()
            FinishedProductReceiptSupplier.objects.update_or_create(
                customer_code=customer_code,
                defaults={
                    "name": lookup_customer_name(
                        customer_code,
                        fallback="",
                    ),
                    "direct_delivery_customer_code": direct_delivery_customer_code,
                    "exclusion": post_data.get("exclusion") == "on",
                },
            )
            return [SettingsActionMessage("success", "得意先を保存しました。")]

        supplier = get_object_or_404(FinishedProductReceiptSupplier, id=post_data.get("supplier_id"))
        if action == "update_supplier":
            posted_customer_code = (post_data.get("customer_code") or "").strip()
            if posted_customer_code and posted_customer_code != supplier.customer_code:
                return [SettingsActionMessage("error", "得意先コードは編集できません。変更する場合は削除してから再度追加してください。")]
            supplier.direct_delivery_customer_code = (post_data.get("direct_delivery_customer_code") or "").strip()
            supplier.exclusion = post_data.get("exclusion") == "on"
            supplier.save(update_fields=["direct_delivery_customer_code", "exclusion", "updated_at"])
            return [SettingsActionMessage("success", "設定を更新しました。")]
        if action in {"add_receiving", "delete_receiving", "delete_supplier"}:
            return self._handle_supplier_child(action, supplier, ReceiptComparisonType.FINISHED_PRODUCT, post_data, user)
        return []

    def _handle_supplied_parts(self, action: str | None, post_data: dict[str, str], user: object) -> list[SettingsActionMessage]:
        digit_length = customer_digit_length(ReceiptComparisonType.SUPPLIED_PARTS)
        if action == "add_supplier":
            customer_code = (post_data.get("customer_code") or "").strip()
            if not is_fixed_digit_code(customer_code, digit_length):
                return [SettingsActionMessage("error", "得意先は3桁で選択してください。")]
            SuppliedPartsReceiptSupplier.objects.update_or_create(
                customer_code=customer_code,
                defaults={
                    "name": lookup_customer_name(customer_code, fallback=""),
                    "exclusion": post_data.get("exclusion") == "on",
                },
            )
            return [SettingsActionMessage("success", "得意先を保存しました。子取引先（購買取引先コード）を登録してください。")]

        supplier = get_object_or_404(SuppliedPartsReceiptSupplier, id=post_data.get("supplier_id"))
        if action == "update_supplier":
            posted_customer_code = (post_data.get("customer_code") or "").strip()
            if posted_customer_code and posted_customer_code != supplier.customer_code:
                return [SettingsActionMessage("error", "得意先コードは編集できません。変更する場合は削除してから再度追加してください。")]
            supplier.exclusion = post_data.get("exclusion") == "on"
            supplier.save(update_fields=["exclusion", "updated_at"])
            return [SettingsActionMessage("success", "設定を更新しました。")]
        if action in {"add_subcontractor", "delete_subcontractor"}:
            return self._handle_subcontractor(action, supplier, post_data)
        if action in {"add_receiving", "delete_receiving", "delete_supplier"}:
            return self._handle_supplier_child(action, supplier, ReceiptComparisonType.SUPPLIED_PARTS, post_data, user)
        return []

    def _handle_subcontractor(
        self,
        action: str,
        supplier: SuppliedPartsReceiptSupplier,
        post_data: dict[str, str],
    ) -> list[SettingsActionMessage]:
        if action == "add_subcontractor":
            vendor_code = (post_data.get("vendor_code") or "").strip()
            if not is_fixed_digit_code(vendor_code, VENDOR_CODE_DIGIT_LENGTH):
                return [SettingsActionMessage("error", "子取引先は4桁の購買取引先コードで選択してください。")]
            vendor_name = lookup_vendor_name(vendor_code)
            _, created = SuppliedPartsSubcontractor.objects.get_or_create(
                supplier=supplier,
                vendor_code=vendor_code,
                defaults={"vendor_name": vendor_name},
            )
            if created:
                return [SettingsActionMessage("success", "子取引先を追加しました。")]
            return [SettingsActionMessage("info", "同じ購買取引先コードは既に登録されています。")]

        subcontractor = get_object_or_404(
            SuppliedPartsSubcontractor,
            id=post_data.get("subcontractor_id"),
            supplier=supplier,
        )
        subcontractor.delete()
        return [SettingsActionMessage("success", "子取引先を削除しました。")]

    def _handle_supplier_child(
        self,
        action: str,
        supplier: FinishedProductReceiptSupplier | SuppliedPartsReceiptSupplier,
        comparison_type: str,
        post_data: dict[str, str],
        user: object,
    ) -> list[SettingsActionMessage]:
        if action == "add_receiving":
            delivery_place = (post_data.get("delivery_place") or "").strip()
            if not delivery_place:
                return []
            receiving_setting_model(comparison_type).objects.update_or_create(
                supplier=supplier,
                delivery_place=delivery_place,
                defaults={"updated_by": user, "created_by": user},
            )
            return [SettingsActionMessage("success", f"{settings_target_label(comparison_type)}を保存しました。")]
        if action == "delete_receiving":
            setting = get_object_or_404(
                receiving_setting_model(comparison_type),
                id=post_data.get("setting_id"),
                supplier=supplier,
            )
            setting.delete()
            return [SettingsActionMessage("success", f"{settings_target_label(comparison_type)}を削除しました。")]
        if action == "delete_supplier":
            with transaction.atomic():
                comparison_result_model(comparison_type).objects.filter(supplier=supplier).delete()
                file_import_model(comparison_type).objects.filter(supplier=supplier).delete()
                supplier.delete()
            return [SettingsActionMessage("success", "得意先を削除しました。")]
        return []
