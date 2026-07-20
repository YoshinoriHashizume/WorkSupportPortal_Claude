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
            name="InventoryOrderAlertSettings",
            fields=[
                ("id", models.PositiveSmallIntegerField(default=1, primary_key=True, serialize=False)),
                ("warning_days", models.PositiveIntegerField(default=365)),
                ("critical_enabled", models.BooleanField(default=True)),
                ("stock_stale_days", models.PositiveIntegerField(default=7)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="inventory_order_alert_settings_updates",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "在庫発注アラート設定",
                "verbose_name_plural": "在庫発注アラート設定",
            },
        ),
        migrations.CreateModel(
            name="InventoryOrderAlertConfirmation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("cust_code", models.CharField(max_length=40)),
                ("item_cd", models.CharField(max_length=80)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("unconfirmed", "未確認"),
                            ("in_progress", "確認中"),
                            ("confirmed", "確認済み"),
                        ],
                        default="unconfirmed",
                        max_length=20,
                    ),
                ),
                ("memo", models.CharField(blank=True, max_length=500)),
                ("confirmed_at", models.DateTimeField(blank=True, null=True)),
                ("confirmed_by", models.CharField(blank=True, max_length=40)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("cust_code", "item_cd"),
                        name="unique_inventory_order_alert_confirmation",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="SlimsStockImport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("imported_at", models.DateTimeField(auto_now_add=True)),
                ("file_name", models.CharField(blank=True, max_length=255)),
                ("row_count", models.PositiveIntegerField(default=0)),
                (
                    "imported_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="slims_stock_imports",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-imported_at"],
            },
        ),
        migrations.CreateModel(
            name="SlimsStockSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("item_cd", models.CharField(max_length=80)),
                ("wloccd", models.CharField(max_length=40)),
                ("stock_qty", models.DecimalField(decimal_places=4, max_digits=18)),
                (
                    "import_record",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="snapshots",
                        to="inventory_order_alert.slimsstockimport",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(fields=["item_cd"], name="ioa_slims_snapshot_item_idx"),
                ],
            },
        ),
    ]
