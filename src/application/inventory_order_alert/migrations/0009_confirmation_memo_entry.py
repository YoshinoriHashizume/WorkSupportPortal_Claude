from __future__ import annotations

from django.db import migrations, models
import django.db.models.deletion


def migrate_legacy_memos(apps, schema_editor):
    Confirmation = apps.get_model("inventory_order_alert", "InventoryOrderAlertConfirmation")
    MemoEntry = apps.get_model("inventory_order_alert", "InventoryOrderAlertConfirmationMemoEntry")
    for confirmation in Confirmation.objects.exclude(memo=""):
        MemoEntry.objects.create(
            confirmation=confirmation,
            content=confirmation.memo,
            created_by=confirmation.confirmed_by or "",
            created_at=confirmation.updated_at,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("inventory_order_alert", "0008_confirmation_confirmed_alert_level"),
    ]

    operations = [
        migrations.CreateModel(
            name="InventoryOrderAlertConfirmationMemoEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("content", models.CharField(max_length=500)),
                ("created_by", models.CharField(blank=True, max_length=40)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "confirmation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="memo_entries",
                        to="inventory_order_alert.inventoryorderalertconfirmation",
                    ),
                ),
            ],
            options={
                "verbose_name": "在庫発注アラート確認メモ",
                "verbose_name_plural": "在庫発注アラート確認メモ",
                "ordering": ["created_at", "id"],
            },
        ),
        migrations.RunPython(migrate_legacy_memos, migrations.RunPython.noop),
    ]
