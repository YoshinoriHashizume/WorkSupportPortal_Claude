from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("receipt_comparison", "0005_remove_receiving_setting_enabled"),
    ]

    operations = [
        migrations.AddField(
            model_name="suppliedpartssubcontractor",
            name="vendor_name",
            field=models.CharField(blank=True, max_length=120),
        ),
    ]
