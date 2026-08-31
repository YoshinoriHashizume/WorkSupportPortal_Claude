from __future__ import annotations

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("shipment_trend", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ShipmentTrendBaselineYear",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("cust_code", models.CharField(max_length=32)),
                ("item_cd", models.CharField(max_length=64)),
                ("baseline_fiscal_year", models.PositiveIntegerField()),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="shipment_trend_baseline_year_updates",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "出荷トレンド比較基準年",
                "verbose_name_plural": "出荷トレンド比較基準年",
            },
        ),
        migrations.AddConstraint(
            model_name="shipmenttrendbaselineyear",
            constraint=models.UniqueConstraint(
                fields=("cust_code", "item_cd"),
                name="shipment_trend_baseline_cust_item_uniq",
            ),
        ),
    ]
