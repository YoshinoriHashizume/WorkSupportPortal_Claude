from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("receipt_comparison", "0004_supplied_parts_customer_code"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="finishedproductreceivingsetting",
            name="enabled",
        ),
        migrations.RemoveField(
            model_name="suppliedpartsreceivingsetting",
            name="enabled",
        ),
    ]
