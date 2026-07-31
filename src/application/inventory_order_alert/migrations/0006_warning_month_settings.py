from django.db import migrations, models


def copy_balance_shipment_months(apps, schema_editor):
    Settings = apps.get_model("inventory_order_alert", "InventoryOrderAlertSettings")
    for row in Settings.objects.all():
        row.warning_shipment_months = row.balance_shipment_months
        row.warning_incoming_months = row.balance_shipment_months
        row.save(update_fields=["warning_shipment_months", "warning_incoming_months"])


class Migration(migrations.Migration):

    dependencies = [
        ("inventory_order_alert", "0005_balance_shipment_months_default_12"),
    ]

    operations = [
        migrations.AddField(
            model_name="inventoryorderalertsettings",
            name="warning_shipment_months",
            field=models.PositiveIntegerField(default=12),
        ),
        migrations.AddField(
            model_name="inventoryorderalertsettings",
            name="warning_incoming_months",
            field=models.PositiveIntegerField(default=12),
        ),
        migrations.RunPython(copy_balance_shipment_months, migrations.RunPython.noop),
    ]
