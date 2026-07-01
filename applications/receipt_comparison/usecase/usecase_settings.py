from __future__ import annotations

from dataclasses import dataclass

from applications.receipt_comparison.domain.comparison_type import SUPPLIED_PARTS, comparison_type_page_label
from applications.receipt_comparison.domain.comparison_urls import settings_redirect_path
from applications.receipt_comparison.domain.ports import ListSuppliersForSettings, ReceiptChoiceGateway, SettingsRepository
from applications.receipt_comparison.domain.settings_labels import settings_exclusion_label, settings_target_label
from applications.receipt_comparison.usecase.usecase_compare import FlashMessage


@dataclass(frozen=True)
class SettingsPageContext:
    type_slug: str
    comparison_type: str
    comparison_type_page_label: str
    customer_choices: list[dict[str, str]]
    choice_error: str
    vendor_choices: list[dict[str, str]]
    suppliers: list[object]
    supplier_rows: list[dict[str, object]]
    open_supplier_id: str
    settings_target_label: str
    settings_exclusion_label: str


@dataclass(frozen=True)
class SettingsPostOutcome:
    redirect_url: str
    messages: tuple[FlashMessage, ...]


class SettingsPageUsecase:
    def __init__(
        self,
        receipt_choices: ReceiptChoiceGateway,
        list_suppliers_for_settings: ListSuppliersForSettings,
        *,
        settings_base_path: str,
        customer_digit_length_for: callable,
    ) -> None:
        self._receipt_choices = receipt_choices
        self._list_suppliers_for_settings = list_suppliers_for_settings
        self._settings_base_path = settings_base_path
        self._customer_digit_length_for = customer_digit_length_for

    def execute(
        self,
        *,
        type_slug: str,
        comparison_type: str,
        open_supplier_id: str,
    ) -> SettingsPageContext:
        digit_length = self._customer_digit_length_for(comparison_type)
        customer_choices, choice_error = self._receipt_choices.list_customers(digit_length)
        vendor_choices: list[dict[str, str]] = []
        vendor_choice_error = ""
        if comparison_type == SUPPLIED_PARTS:
            vendor_choices, vendor_choice_error = self._receipt_choices.list_vendors()
        combined_choice_error = " / ".join(part for part in (choice_error, vendor_choice_error) if part)
        suppliers = self._list_suppliers_for_settings(comparison_type)
        return SettingsPageContext(
            type_slug=type_slug,
            comparison_type=comparison_type,
            comparison_type_page_label=comparison_type_page_label(comparison_type),
            customer_choices=customer_choices,
            choice_error=combined_choice_error,
            vendor_choices=vendor_choices,
            suppliers=suppliers,
            supplier_rows=[{"supplier": supplier} for supplier in suppliers],
            open_supplier_id=open_supplier_id,
            settings_target_label=settings_target_label(comparison_type),
            settings_exclusion_label=settings_exclusion_label(comparison_type),
        )


class SettingsPostUsecase:
    def __init__(self, settings_repository: SettingsRepository, *, settings_base_path: str) -> None:
        self._settings_repository = settings_repository
        self._settings_base_path = settings_base_path

    def execute(
        self,
        *,
        type_slug: str,
        comparison_type: str,
        action: str | None,
        post_data: dict[str, str],
        user: object,
    ) -> SettingsPostOutcome:
        action_messages = self._settings_repository.handle_post(comparison_type, action, post_data, user)
        supplier_id = post_data.get("supplier_id")
        if action == "delete_supplier":
            supplier_id = None
        return SettingsPostOutcome(
            redirect_url=settings_redirect_path(self._settings_base_path, type_slug, supplier_id),
            messages=tuple(FlashMessage(message.level, message.text) for message in action_messages),
        )
