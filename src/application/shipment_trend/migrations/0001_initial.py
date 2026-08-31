from __future__ import annotations

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ShipmentTrendSettings",
            fields=[
                ("id", models.PositiveSmallIntegerField(default=1, primary_key=True, serialize=False)),
                ("decrease_threshold_pct", models.FloatField(default=20.0)),
                ("increase_threshold_pct", models.FloatField(default=20.0)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="shipment_trend_settings_updates",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "出荷トレンド一覧設定",
                "verbose_name_plural": "出荷トレンド一覧設定",
            },
        ),
        migrations.CreateModel(
            name="ShipmentTrendRefresh",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("refreshed_at", models.DateTimeField(auto_now_add=True)),
                ("row_count", models.PositiveIntegerField(default=0)),
                (
                    "refreshed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="shipment_trend_refreshes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-refreshed_at"],
            },
        ),
        migrations.CreateModel(
            name="ShipmentTrendSummarySnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("as_of_date", models.DateField()),
                ("rows", models.JSONField(default=list)),
                ("total_count", models.PositiveIntegerField(default=0)),
                ("aggregation_error", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "refresh_record",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="summary_snapshot",
                        to="shipment_trend.shipmenttrendrefresh",
                    ),
                ),
            ],
            options={
                "verbose_name": "出荷トレンド集計スナップショット",
                "verbose_name_plural": "出荷トレンド集計スナップショット",
            },
        ),
    ]
