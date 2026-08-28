from __future__ import annotations

from django.conf import settings
from django.db import models


class ConfirmationStatus(models.TextChoices):
    UNCONFIRMED = "unconfirmed", "未確認"
    IN_PROGRESS = "in_progress", "確認中"
    CONFIRMED = "confirmed", "確認済み"


class InventoryOrderAlertSettings(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1)
    warning_days = models.PositiveIntegerField(default=365)
    recent_incoming_days = models.PositiveIntegerField(default=90)
    recent_shipment_days = models.PositiveIntegerField(default=90)
    stale_incoming_days = models.PositiveIntegerField(default=180)
    balance_shipment_months = models.PositiveIntegerField(default=12)
    # 旧アラートレベル方式の残置カラム（未使用）。流動区分の判定には用いない（design.md §5.3）。
    warning_shipment_months = models.PositiveIntegerField(default=12)
    # 旧アラートレベル方式の残置カラム（未使用）。流動区分の判定には用いない（design.md §5.3）。
    warning_incoming_months = models.PositiveIntegerField(default=12)
    incoming_grace_days = models.PositiveIntegerField(default=30)
    # 旧アラートレベル方式の残置カラム（未使用）。重点は供給リスク品に置き換わった（design.md §5.3）。
    critical_enabled = models.BooleanField(default=True)
    stock_stale_days = models.PositiveIntegerField(default=7)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="inventory_order_alert_settings_updates",
    )

    class Meta:
        verbose_name = "在庫発注アラート設定"
        verbose_name_plural = "在庫発注アラート設定"


class InventoryOrderAlertConfirmation(models.Model):
    cust_code = models.CharField(max_length=40)
    item_cd = models.CharField(max_length=80)
    status = models.CharField(
        max_length=20,
        choices=ConfirmationStatus.choices,
        default=ConfirmationStatus.UNCONFIRMED,
    )
    memo = models.CharField(max_length=500, blank=True)
    #: 確認時点の流動区分（design.md §5.2）。旧データには旧アラートレベルのラベルが残る。
    confirmed_flow_quadrant = models.CharField(max_length=40, blank=True, default="")
    confirmed_at = models.DateTimeField(null=True, blank=True)
    confirmed_by = models.CharField(max_length=40, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["cust_code", "item_cd"],
                name="unique_inventory_order_alert_confirmation",
            ),
        ]


class InventoryOrderAlertConfirmationMemoEntry(models.Model):
    confirmation = models.ForeignKey(
        InventoryOrderAlertConfirmation,
        on_delete=models.CASCADE,
        related_name="memo_entries",
    )
    content = models.CharField(max_length=500)
    created_by = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = "在庫発注アラート確認メモ"
        verbose_name_plural = "在庫発注アラート確認メモ"


class SlimsStockImport(models.Model):
    imported_at = models.DateTimeField(auto_now_add=True)
    imported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="slims_stock_imports",
    )
    file_name = models.CharField(max_length=255, blank=True)
    row_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-imported_at"]


class SlimsStockSnapshot(models.Model):
    import_record = models.ForeignKey(
        SlimsStockImport,
        on_delete=models.CASCADE,
        related_name="snapshots",
    )
    item_cd = models.CharField(max_length=80)
    wloccd = models.CharField(max_length=40)
    stock_qty = models.DecimalField(max_digits=18, decimal_places=4)
    wnyudt = models.CharField(max_length=8, blank=True, default="")

    class Meta:
        indexes = [
            models.Index(fields=["item_cd"], name="ioa_slims_snapshot_item_idx"),
        ]


class InventoryOrderAlertSummarySnapshot(models.Model):
    import_record = models.OneToOneField(
        SlimsStockImport,
        on_delete=models.CASCADE,
        related_name="summary_snapshot",
    )
    as_of_date = models.DateField()
    rows = models.JSONField(default=list)
    total_count = models.PositiveIntegerField(default=0)
    critical_count = models.PositiveIntegerField(default=0)
    warning_count = models.PositiveIntegerField(default=0)
    aggregation_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "在庫発注アラート集計スナップショット"
        verbose_name_plural = "在庫発注アラート集計スナップショット"
