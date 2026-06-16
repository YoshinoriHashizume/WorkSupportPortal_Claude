from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("receipt_comparison", "0001_initial"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="receiptsupplier",
            name="unique_receipt_supplier_type_code",
        ),
        migrations.AddField(
            model_name="receiptsupplier",
            name="code_type",
            field=models.CharField(
                choices=[("customer", "customer_code"), ("vendor", "vendor_code")],
                default="customer",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="receiptsupplier",
            name="vendor_code",
            field=models.CharField(blank=True, max_length=40),
        ),
        migrations.AddConstraint(
            model_name="receiptsupplier",
            constraint=models.UniqueConstraint(
                fields=("comparison_type", "code_type", "customer_code", "vendor_code"),
                name="unique_receipt_supplier_code",
            ),
        ),
    ]
