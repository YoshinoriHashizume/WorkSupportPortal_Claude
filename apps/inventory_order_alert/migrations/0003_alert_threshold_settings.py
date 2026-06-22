from __future__ import annotations

from django.db import migrations, models


def copy_warning_days_to_stale(apps, schema_editor):
    Settings = apps.get_model("inventory_order_alert", "InventoryOrderAlertSettings")
    for row in Settings.objects.all():
        row.stale_incoming_days = row.warning_days
        row.save(update_fields=["stale_incoming_days"])


class Migration(migrations.Migration):
    dependencies = [
        ("inventory_order_alert", "0002_inventoryorderalertsummarysnapshot"),
    ]

    operations = [
        migrations.AddField(
            model_name="inventoryorderalertsettings",
            name="recent_incoming_days",
            field=models.PositiveIntegerField(default=90),
        ),
        migrations.AddField(
            model_name="inventoryorderalertsettings",
            name="recent_shipment_days",
            field=models.PositiveIntegerField(default=90),
        ),
        migrations.AddField(
            model_name="inventoryorderalertsettings",
            name="stale_incoming_days",
            field=models.PositiveIntegerField(default=180),
        ),
        migrations.AddField(
            model_name="inventoryorderalertsettings",
            name="incoming_grace_days",
            field=models.PositiveIntegerField(default=30),
        ),
        migrations.RunPython(copy_warning_days_to_stale, migrations.RunPython.noop),
    ]
