from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("gonenkukumi", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="gonenkukumisearchhistory",
            name="option_change",
            field=models.CharField(default="*", max_length=20),
        ),
    ]
