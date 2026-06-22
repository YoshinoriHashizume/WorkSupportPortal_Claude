from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("inventory_order_alert", "0009_confirmation_memo_entry"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="inventoryorderalertconfirmationmemoentry",
            options={
                "ordering": ["-created_at", "-id"],
                "verbose_name": "在庫発注アラート確認メモ",
                "verbose_name_plural": "在庫発注アラート確認メモ",
            },
        ),
    ]
