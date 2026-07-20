from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventory_order_alert", "0007_slimsstocksnapshot_wnyudt"),
    ]

    operations = [
        migrations.AddField(
            model_name="inventoryorderalertconfirmation",
            name="confirmed_alert_level",
            field=models.CharField(blank=True, default="", max_length=40),
        ),
    ]
