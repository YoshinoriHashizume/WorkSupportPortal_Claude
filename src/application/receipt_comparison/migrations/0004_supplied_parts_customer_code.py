# Generated manually for Oracle-linked supplied parts suppliers.

from django.db import migrations, models


def migrate_vendor_to_customer_code(apps, schema_editor):
    SuppliedPartsReceiptSupplier = apps.get_model("receipt_comparison", "SuppliedPartsReceiptSupplier")
    for supplier in SuppliedPartsReceiptSupplier.objects.all():
        vendor_code = (getattr(supplier, "vendor_code", "") or "").strip()
        customer_code = (getattr(supplier, "customer_code", "") or "").strip()
        if not customer_code and vendor_code:
            supplier.customer_code = vendor_code
            supplier.save(update_fields=["customer_code"])


def drop_legacy_vendor_unique_constraint(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(
        'ALTER TABLE "receipt_comparison_suppliedpartsreceiptsupplier" '
        'DROP CONSTRAINT IF EXISTS "unique_sp_receipt_supplier_vendor_code"'
    )


class Migration(migrations.Migration):
    dependencies = [
        ("receipt_comparison", "0003_split_tables_by_comparison_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="suppliedpartsreceiptsupplier",
            name="customer_code",
            field=models.CharField(blank=True, default="", max_length=40),
        ),
        migrations.RunPython(migrate_vendor_to_customer_code, migrations.RunPython.noop),
        migrations.RunPython(drop_legacy_vendor_unique_constraint, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="suppliedpartsreceiptsupplier",
            name="vendor_code",
        ),
        migrations.AlterModelOptions(
            name="suppliedpartsreceiptsupplier",
            options={"ordering": ["customer_code", "name"]},
        ),
        migrations.AddConstraint(
            model_name="suppliedpartsreceiptsupplier",
            constraint=models.UniqueConstraint(
                fields=("customer_code",),
                name="unique_sp_receipt_supplier_customer_code",
            ),
        ),
    ]
