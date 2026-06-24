# Generated for initial Django implementation.

import uuid

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
            name="GonenKukumiSearchHistory",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("executed_at", models.DateTimeField(auto_now_add=True)),
                ("cust_code", models.CharField(max_length=3)),
                ("cust_item", models.CharField(blank=True, max_length=80)),
                ("option_change", models.BooleanField(default=False)),
                ("year_month", models.CharField(max_length=7)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="gonenkukumi_histories", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-executed_at"],
            },
        ),
        migrations.AddIndex(
            model_name="gonenkukumisearchhistory",
            index=models.Index(fields=["user", "-executed_at"], name="gonenkukumi_user_exe_idx"),
        ),
    ]
