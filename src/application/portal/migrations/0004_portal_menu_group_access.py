from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


MENU_GROUPS = {
    "全社": "company",
    "人事": "hr",
    "総務": "general-affairs",
    "財務": "finance",
    "営業": "sales",
    "生産管理": "production",
    "品保": "quality",
    "管理": "management",
}
ROLE_GROUPS = ["一般ユーザー", "管理者"]


def migrate_department_groups_to_menu_access(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    PortalMenuGroupAccess = apps.get_model("portal", "PortalMenuGroupAccess")
    for group_name, group_key in MENU_GROUPS.items():
        try:
            group = Group.objects.get(name=group_name)
        except Group.DoesNotExist:
            continue
        for user in group.user_set.all():
            PortalMenuGroupAccess.objects.get_or_create(user=user, group_key=group_key)
    Group.objects.exclude(name__in=ROLE_GROUPS).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0003_role_and_department_groups"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="PortalMenuGroupAccess",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("group_key", models.CharField(max_length=80)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="portal_menu_group_accesses",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["group_key"],
                "constraints": [
                    models.UniqueConstraint(fields=("user", "group_key"), name="unique_user_menu_group_access"),
                ],
                "indexes": [
                    models.Index(fields=["user", "group_key"], name="menu_group_access_user_idx"),
                ],
            },
        ),
        migrations.RunPython(migrate_department_groups_to_menu_access, migrations.RunPython.noop),
    ]
