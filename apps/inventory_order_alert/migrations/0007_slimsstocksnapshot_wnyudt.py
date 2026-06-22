from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventory_order_alert", "0006_warning_month_settings"),
    ]

    operations = [
        migrations.AddField(
            model_name="slimsstocksnapshot",
            name="wnyudt",
            field=models.CharField(blank=True, default="", max_length=8),
        ),
    ]
