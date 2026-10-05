"""直近入荷の窓（07 REQ-FQR-F-008）を設定項目にする。

`recent_incoming_days` は旧アラートレベル方式の残置カラム（既定 90）で、05 以降どこからも読まれていない。
意味（直近入荷とみなす日数）は同じなのでカラムを再利用するが、保存済みの 90 は旧方式の閾値であって
新しい窓の設定値ではないため、既定値を 30 に変え、既存行の値も新しい既定値に戻す（07 design §5.2）。
"""

from django.db import migrations, models

NEW_DEFAULT_RECENT_INCOMING_DAYS = 30
LEGACY_DEFAULT_RECENT_INCOMING_DAYS = 90


def reset_recent_incoming_days(apps, schema_editor):
    model = apps.get_model("inventory_order_alert", "InventoryOrderAlertSettings")
    model.objects.all().update(recent_incoming_days=NEW_DEFAULT_RECENT_INCOMING_DAYS)


def restore_legacy_recent_incoming_days(apps, schema_editor):
    model = apps.get_model("inventory_order_alert", "InventoryOrderAlertSettings")
    model.objects.all().update(recent_incoming_days=LEGACY_DEFAULT_RECENT_INCOMING_DAYS)


class Migration(migrations.Migration):

    dependencies = [
        ("inventory_order_alert", "0012_stockout_risk_settings"),
    ]

    operations = [
        migrations.AlterField(
            model_name="inventoryorderalertsettings",
            name="recent_incoming_days",
            field=models.PositiveIntegerField(default=NEW_DEFAULT_RECENT_INCOMING_DAYS),
        ),
        migrations.RunPython(reset_recent_incoming_days, restore_legacy_recent_incoming_days),
    ]
