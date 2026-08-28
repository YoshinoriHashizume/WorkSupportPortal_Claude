"""確認記録のフィールド名を流動区分へ改める（design.md §5.2）。

`RenameField` 1件のみ。PostgreSQL の `ALTER TABLE ... RENAME COLUMN` は即時に完了し、
データを保持する。既存の値（旧アラートレベルのラベル）は書き換えない（NF-007）。
読み取り時に `normalize_flow_quadrant()` が流動区分へ正規化する。

`RemoveField` + `AddField` に置き換えるとデータが失われるため、
自動生成に頼らず手で `RenameField` を記述している。
"""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("inventory_order_alert", "0010_memo_entry_newest_first_ordering"),
    ]

    operations = [
        migrations.RenameField(
            model_name="inventoryorderalertconfirmation",
            old_name="confirmed_alert_level",
            new_name="confirmed_flow_quadrant",
        ),
    ]
