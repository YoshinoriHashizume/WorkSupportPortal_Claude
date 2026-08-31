from __future__ import annotations

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventory_order_alert", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="InventoryOrderAlertSummarySnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("as_of_date", models.DateField()),
                ("rows", models.JSONField(default=list)),
                ("total_count", models.PositiveIntegerField(default=0)),
                ("critical_count", models.PositiveIntegerField(default=0)),
                ("warning_count", models.PositiveIntegerField(default=0)),
                ("aggregation_error", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "import_record",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="summary_snapshot",
                        to="inventory_order_alert.slimsstockimport",
                    ),
                ),
            ],
            options={
                "verbose_name": "在庫発注アラート集計スナップショット",
                "verbose_name_plural": "在庫発注アラート集計スナップショット",
            },
        ),
    ]
