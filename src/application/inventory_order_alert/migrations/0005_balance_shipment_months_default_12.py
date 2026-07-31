from django.db import migrations, models


def set_balance_shipment_months_to_twelve(apps, schema_editor):
    InventoryOrderAlertSettings = apps.get_model("inventory_order_alert", "InventoryOrderAlertSettings")
    InventoryOrderAlertSettings.objects.filter(balance_shipment_months=9).update(balance_shipment_months=12)


class Migration(migrations.Migration):

    dependencies = [
        ("inventory_order_alert", "0004_balance_shipment_months"),
    ]

    operations = [
        migrations.AlterField(
            model_name="inventoryorderalertsettings",
            name="balance_shipment_months",
            field=models.PositiveIntegerField(default=12),
        ),
        migrations.RunPython(set_balance_shipment_months_to_twelve, migrations.RunPython.noop),
    ]
