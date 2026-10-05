"""安全日数・監視期間の設定を撤去する（08 design §2.4）。

対応区分（S-204）は内示のある範囲だけを日次で追う判定に変わり、安全日数（`safety_days`）と
監視期間（`watch_months`）はどこからも読まれなくなった。既定リードタイム（`default_lead_time_days`）は
発注期限（V-233）の算出に使い続けるため残す。
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("inventory_order_alert", "0013_recent_incoming_days_window"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="inventoryorderalertsettings",
            name="safety_days",
        ),
        migrations.RemoveField(
            model_name="inventoryorderalertsettings",
            name="watch_months",
        ),
    ]
