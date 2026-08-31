from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


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


def create_default_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for name in DEFAULT_GROUPS:
        Group.objects.get_or_create(name=name)


def remove_default_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=DEFAULT_GROUPS).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserAccessRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "status",
                    models.CharField(
                        choices=[("pending", "承認待ち"), ("approved", "許可"), ("rejected", "拒否")],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("requested_at", models.DateTimeField(auto_now_add=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("note", models.TextField(blank=True)),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reviewed_access_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="access_request",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["status", "-requested_at"],
                "indexes": [models.Index(fields=["status", "-requested_at"], name="access_req_status_idx")],
            },
        ),
        migrations.RunPython(create_default_groups, remove_default_groups),
    ]
