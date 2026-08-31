from __future__ import annotations

from django.conf import settings
from django.db import models

from application.receipt_comparison.domain.value_objects.comparison_type import (
    COMPARISON_TYPE_PAGE_LABELS,
    ReceiptComparisonType as DomainComparisonType,
)
from application.receipt_comparison.domain.value_objects.receipt_flag import (
    ReceiptFlag as DomainReceiptFlag,
)


class ReceiptComparisonType(models.TextChoices):
    """ORM / フォーム用。値・表示は domain の ReceiptComparisonType を正とする。"""

    FINISHED_PRODUCT = (
        DomainComparisonType.FINISHED_PRODUCT.value,
        COMPARISON_TYPE_PAGE_LABELS[DomainComparisonType.FINISHED_PRODUCT.value],
    )
    SUPPLIED_PARTS = (
        DomainComparisonType.SUPPLIED_PARTS.value,
        COMPARISON_TYPE_PAGE_LABELS[DomainComparisonType.SUPPLIED_PARTS.value],
    )


class ReceiptFlag(models.IntegerChoices):
    """ORM / フォーム用。値・表示は domain の ReceiptFlag を正とする。"""

    NG = DomainReceiptFlag.NG.value, DomainReceiptFlag.NG.label
    OK = DomainReceiptFlag.OK.value, DomainReceiptFlag.OK.label
    PENDING = DomainReceiptFlag.PENDING.value, DomainReceiptFlag.PENDING.label


class FinishedProductReceiptSupplier(models.Model):
    name = models.CharField(max_length=120)
    customer_code = models.CharField(max_length=40)
    direct_delivery_customer_code = models.CharField(max_length=40, blank=True)
    exclusion = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["customer_code", "name"]
        constraints = [
            models.UniqueConstraint(fields=["customer_code"], name="unique_fp_receipt_supplier_customer_code"),
        ]

    def __str__(self) -> str:
        return self.customer_code

    @property
    def primary_code(self) -> str:
        return self.customer_code


class FinishedProductReceivingSetting(models.Model):
    supplier = models.ForeignKey(
        FinishedProductReceiptSupplier,
        on_delete=models.CASCADE,
        related_name="receiving_settings",
    )
    delivery_place = models.CharField(max_length=80)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_fp_receipt_receiving_settings",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="updated_fp_receipt_receiving_settings",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["delivery_place"]
        constraints = [
            models.UniqueConstraint(fields=["supplier", "delivery_place"], name="unique_fp_receipt_receiving_place"),
        ]


class FinishedProductFileImport(models.Model):
    supplier = models.ForeignKey(
        FinishedProductReceiptSupplier,
        on_delete=models.PROTECT,
        related_name="receipt_file_imports",
    )
    original_file_name = models.CharField(max_length=255)
    stored_file_name = models.CharField(max_length=255)
    receipt_date = models.DateField()
    imported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="fp_receipt_file_imports",
    )
    imported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-receipt_date", "-imported_at"]
        indexes = [
            models.Index(fields=["supplier", "receipt_date"], name="fp_receipt_file_lookup_idx"),
        ]


class FinishedProductComparisonResult(models.Model):
    supplier = models.ForeignKey(
        FinishedProductReceiptSupplier,
        on_delete=models.PROTECT,
        related_name="receipt_results",
    )
    file_import = models.ForeignKey(
        FinishedProductFileImport,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="results",
    )
    receipt_flag = models.PositiveSmallIntegerField(choices=ReceiptFlag.choices, default=ReceiptFlag.NG)
    mari_item_cd = models.CharField(max_length=120, blank=True)
    mari_date = models.CharField(max_length=20, blank=True)
    mari_qty = models.CharField(max_length=40, blank=True)
    delivery_place = models.CharField(max_length=80, blank=True)
    supplier_item_cd = models.CharField(max_length=120, blank=True)
    supplier_delivery_month_day = models.CharField(max_length=4, blank=True)
    supplier_qty = models.CharField(max_length=40, blank=True)
    supplier_cancel_qty = models.CharField(max_length=40, blank=True)
    supplier_name = models.CharField(max_length=120, blank=True)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="updated_fp_receipt_results",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["receipt_flag", "mari_item_cd", "supplier_item_cd", "mari_date", "supplier_delivery_month_day"]
        indexes = [
            models.Index(fields=["supplier", "receipt_flag"], name="fp_receipt_result_flag_idx"),
            models.Index(fields=["supplier", "mari_item_cd"], name="fp_receipt_result_item_idx"),
        ]

    @property
    def flag_label(self) -> str:
        return DomainReceiptFlag(self.receipt_flag).label


class SuppliedPartsReceiptSupplier(models.Model):
    name = models.CharField(max_length=120)
    customer_code = models.CharField(max_length=40)
    exclusion = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["customer_code", "name"]
        constraints = [
            models.UniqueConstraint(fields=["customer_code"], name="unique_sp_receipt_supplier_customer_code"),
        ]

    def __str__(self) -> str:
        return self.customer_code

    @property
    def primary_code(self) -> str:
        return self.customer_code


class SuppliedPartsSubcontractor(models.Model):
    supplier = models.ForeignKey(
        SuppliedPartsReceiptSupplier,
        on_delete=models.CASCADE,
        related_name="subcontractors",
    )
    vendor_code = models.CharField(max_length=40)
    vendor_name = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ["vendor_code"]
        constraints = [
            models.UniqueConstraint(fields=["supplier", "vendor_code"], name="unique_sp_receipt_subcontractor"),
        ]

    @property
    def display_label(self) -> str:
        name = (self.vendor_name or "").strip()
        if name:
            return f"{self.vendor_code} - {name}"
        return self.vendor_code


class SuppliedPartsReceivingSetting(models.Model):
    supplier = models.ForeignKey(
        SuppliedPartsReceiptSupplier,
        on_delete=models.CASCADE,
        related_name="receiving_settings",
    )
    delivery_place = models.CharField(max_length=80)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_sp_receipt_receiving_settings",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="updated_sp_receipt_receiving_settings",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["delivery_place"]
        constraints = [
            models.UniqueConstraint(fields=["supplier", "delivery_place"], name="unique_sp_receipt_receiving_place"),
        ]


class SuppliedPartsFileImport(models.Model):
    supplier = models.ForeignKey(
        SuppliedPartsReceiptSupplier,
        on_delete=models.PROTECT,
        related_name="receipt_file_imports",
    )
    original_file_name = models.CharField(max_length=255)
    stored_file_name = models.CharField(max_length=255)
    receipt_date = models.DateField()
    imported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sp_receipt_file_imports",
    )
    imported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-receipt_date", "-imported_at"]
        indexes = [
            models.Index(fields=["supplier", "receipt_date"], name="sp_receipt_file_lookup_idx"),
        ]


class SuppliedPartsComparisonResult(models.Model):
    supplier = models.ForeignKey(
        SuppliedPartsReceiptSupplier,
        on_delete=models.PROTECT,
        related_name="receipt_results",
    )
    file_import = models.ForeignKey(
        SuppliedPartsFileImport,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="results",
    )
    receipt_flag = models.PositiveSmallIntegerField(choices=ReceiptFlag.choices, default=ReceiptFlag.NG)
    mari_item_cd = models.CharField(max_length=120, blank=True)
    mari_date = models.CharField(max_length=20, blank=True)
    mari_qty = models.CharField(max_length=40, blank=True)
    delivery_place = models.CharField(max_length=80, blank=True)
    supplier_item_cd = models.CharField(max_length=120, blank=True)
    supplier_delivery_month_day = models.CharField(max_length=4, blank=True)
    supplier_qty = models.CharField(max_length=40, blank=True)
    supplier_cancel_qty = models.CharField(max_length=40, blank=True)
    supplier_name = models.CharField(max_length=120, blank=True)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="updated_sp_receipt_results",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["receipt_flag", "mari_item_cd", "supplier_item_cd", "mari_date", "supplier_delivery_month_day"]
        indexes = [
            models.Index(fields=["supplier", "receipt_flag"], name="sp_receipt_result_flag_idx"),
            models.Index(fields=["supplier", "mari_item_cd"], name="sp_receipt_result_item_idx"),
        ]

    @property
    def flag_label(self) -> str:
        return DomainReceiptFlag(self.receipt_flag).label
