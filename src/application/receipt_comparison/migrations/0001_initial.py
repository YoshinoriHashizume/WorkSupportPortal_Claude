from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ReceiptSupplier",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("comparison_type", models.CharField(choices=[("finished_product", "完成品"), ("supplied_parts", "支給品")], max_length=30)),
                ("name", models.CharField(max_length=120)),
                ("customer_code", models.CharField(max_length=40)),
                ("direct_delivery_customer_code", models.CharField(blank=True, max_length=40)),
                ("exclusion", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["comparison_type", "customer_code", "name"],
                "constraints": [
                    models.UniqueConstraint(fields=("comparison_type", "customer_code"), name="unique_receipt_supplier_type_code"),
                ],
            },
        ),
        migrations.CreateModel(
            name="ReceiptFileImport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("comparison_type", models.CharField(choices=[("finished_product", "完成品"), ("supplied_parts", "支給品")], max_length=30)),
                ("original_file_name", models.CharField(max_length=255)),
                ("stored_file_name", models.CharField(max_length=255)),
                ("receipt_date", models.DateField()),
                ("imported_at", models.DateTimeField(auto_now_add=True)),
                ("imported_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="receipt_file_imports", to=settings.AUTH_USER_MODEL)),
                ("supplier", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="receipt_file_imports", to="receipt_comparison.receiptsupplier")),
            ],
            options={
                "ordering": ["-receipt_date", "-imported_at"],
                "indexes": [
                    models.Index(fields=["comparison_type", "supplier", "receipt_date"], name="receipt_file_lookup_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="ReceiptReceivingSetting",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("delivery_place", models.CharField(max_length=80)),
                ("enabled", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_receipt_receiving_settings", to=settings.AUTH_USER_MODEL)),
                ("supplier", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="receiving_settings", to="receipt_comparison.receiptsupplier")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="updated_receipt_receiving_settings", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["delivery_place"],
                "constraints": [
                    models.UniqueConstraint(fields=("supplier", "delivery_place"), name="unique_receipt_receiving_place"),
                ],
            },
        ),
        migrations.CreateModel(
            name="ReceiptSubcontractor",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("customer_code", models.CharField(blank=True, max_length=40)),
                ("vendor_code", models.CharField(blank=True, max_length=40)),
                ("supplier", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="subcontractors", to="receipt_comparison.receiptsupplier")),
            ],
            options={
                "ordering": ["customer_code", "vendor_code"],
                "constraints": [
                    models.UniqueConstraint(fields=("supplier", "customer_code", "vendor_code"), name="unique_receipt_subcontractor"),
                ],
            },
        ),
        migrations.CreateModel(
            name="ReceiptComparisonResult",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("comparison_type", models.CharField(choices=[("finished_product", "完成品"), ("supplied_parts", "支給品")], max_length=30)),
                ("receipt_flag", models.PositiveSmallIntegerField(choices=[(0, "×"), (1, "〇"), (2, "△")], default=0)),
                ("mari_item_cd", models.CharField(blank=True, max_length=120)),
                ("mari_date", models.CharField(blank=True, max_length=20)),
                ("mari_qty", models.CharField(blank=True, max_length=40)),
                ("delivery_place", models.CharField(blank=True, max_length=80)),
                ("supplier_item_cd", models.CharField(blank=True, max_length=120)),
                ("supplier_delivery_month_day", models.CharField(blank=True, max_length=4)),
                ("supplier_qty", models.CharField(blank=True, max_length=40)),
                ("supplier_cancel_qty", models.CharField(blank=True, max_length=40)),
                ("supplier_name", models.CharField(blank=True, max_length=120)),
                ("remarks", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("file_import", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="results", to="receipt_comparison.receiptfileimport")),
                ("supplier", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="receipt_results", to="receipt_comparison.receiptsupplier")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="updated_receipt_results", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["receipt_flag", "mari_item_cd", "supplier_item_cd", "mari_date", "supplier_delivery_month_day"],
                "indexes": [
                    models.Index(fields=["comparison_type", "supplier", "receipt_flag"], name="receipt_result_flag_idx"),
                    models.Index(fields=["comparison_type", "supplier", "mari_item_cd"], name="receipt_result_item_idx"),
                ],
            },
        ),
    ]
