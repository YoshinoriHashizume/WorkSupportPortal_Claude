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
            name="UserFavoriteMenu",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("menu_key", models.CharField(max_length=80)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="favorite_menus",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["sort_order", "created_at"],
                "constraints": [
                    models.UniqueConstraint(fields=("user", "menu_key"), name="unique_user_favorite_menu"),
                ],
                "indexes": [
                    models.Index(fields=["user", "sort_order"], name="favorite_menu_user_order_idx"),
                ],
            },
        ),
    ]
