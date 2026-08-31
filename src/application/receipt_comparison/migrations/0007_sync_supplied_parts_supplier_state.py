"""マイグレーション状態を models.py に合わせる（DBスキーマは変更しない）。

0003 で `unique_sp_receipt_supplier_vendor_code` を `AddConstraint` した後、
0004 が `RunPython` の生SQL（`DROP CONSTRAINT IF EXISTS`）で同じ制約を落とした。
実DBからは消えているが Django のマイグレーション状態には残ったままのため、
`makemigrations --check` が毎回 `RemoveConstraint` を提案し続けていた。

素の `RemoveConstraint` を使うと、既に存在しない制約に対して
`ALTER TABLE ... DROP CONSTRAINT` を発行して本番 PostgreSQL でエラーになる。
そのため `SeparateDatabaseAndState` で**状態のみ**を同期する。
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("receipt_comparison", "0006_suppliedpartssubcontractor_vendor_name"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RemoveConstraint(
                    model_name="suppliedpartsreceiptsupplier",
                    name="unique_sp_receipt_supplier_vendor_code",
                ),
            ],
        ),
        # 0004 が blank=True / default="" 付きで追加した名残を models.py に合わせる。
        # いずれも Django レベルの属性であり、発行される DDL は列定義に影響しない。
        migrations.AlterField(
            model_name="suppliedpartsreceiptsupplier",
            name="customer_code",
            field=models.CharField(max_length=40),
        ),
    ]
