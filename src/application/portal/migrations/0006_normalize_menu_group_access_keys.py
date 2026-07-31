from django.db import migrations


LEGACY_MENU_GROUP_KEYS = {
    "全社": "company",
    "人事": "hr",
    "総務": "general-affairs",
    "財務": "finance",
    "営業": "sales",
    "生産管理": "production",
    "品保": "quality",
    "管理": "management",
}


def normalize_menu_group_access_keys(apps, schema_editor):
    PortalMenuGroupAccess = apps.get_model("portal", "PortalMenuGroupAccess")
    for legacy_key, canonical_key in LEGACY_MENU_GROUP_KEYS.items():
        for access in PortalMenuGroupAccess.objects.filter(group_key=legacy_key).iterator():
            if PortalMenuGroupAccess.objects.filter(user_id=access.user_id, group_key=canonical_key).exists():
                access.delete()
            else:
                access.group_key = canonical_key
                access.save(update_fields=["group_key"])


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0005_portal_notice"),
    ]

    operations = [
        migrations.RunPython(normalize_menu_group_access_keys, migrations.RunPython.noop),
    ]
