from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory_order_alert", "0003_alert_threshold_settings"),
    ]

    operations = [
        migrations.AddField(
            model_name="inventoryorderalertsettings",
            name="balance_shipment_months",
            field=models.PositiveIntegerField(default=9),
        ),
    ]
