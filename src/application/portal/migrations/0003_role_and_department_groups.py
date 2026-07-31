from django.db import migrations


DEFAULT_GROUPS = [
    "一般ユーザー",
    "管理者",
    "全社",
    "人事",
    "総務",
    "財務",
    "営業",
    "生産管理",
    "品保",
]


def create_role_and_department_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for name in DEFAULT_GROUPS:
        Group.objects.get_or_create(name=name)


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0002_user_access_request"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(create_role_and_department_groups, migrations.RunPython.noop),
    ]
