from __future__ import annotations

from django.conf import settings
from django.db import models


class ShipmentTrendSettings(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1)
    decrease_threshold_pct = models.FloatField(default=20.0)
    increase_threshold_pct = models.FloatField(default=20.0)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="shipment_trend_settings_updates",
    )

    class Meta:
        verbose_name = "出荷トレンド一覧設定"
        verbose_name_plural = "出荷トレンド一覧設定"


class ShipmentTrendRefresh(models.Model):
    refreshed_at = models.DateTimeField(auto_now_add=True)
    refreshed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="shipment_trend_refreshes",
    )
    row_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-refreshed_at"]


class ShipmentTrendSummarySnapshot(models.Model):
    refresh_record = models.OneToOneField(
        ShipmentTrendRefresh,
        on_delete=models.CASCADE,
        related_name="summary_snapshot",
    )
    as_of_date = models.DateField()
    rows = models.JSONField(default=list)
    total_count = models.PositiveIntegerField(default=0)
    aggregation_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "出荷トレンド集計スナップショット"
        verbose_name_plural = "出荷トレンド集計スナップショット"
