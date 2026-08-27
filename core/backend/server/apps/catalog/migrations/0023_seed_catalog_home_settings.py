from django.db import migrations

from server.apps.catalog.models.catalog_home_settings import (
    DEFAULT_ABOUT_MARKDOWN,
    CatalogHomeSettings,
)


def seed_catalog_home_settings(apps, schema_editor):
    """Seed the singleton `CatalogHomeSettings` row with default Atlas content.

    Follows the `RunPython` precedent at 0007_reset_tag_colors.py so a fresh
    deployment has real homepage content with no manual seed command
    """
    historical_model = apps.get_model("catalog", "CatalogHomeSettings")
    historical_model.objects.get_or_create(
        pk=CatalogHomeSettings.SINGLETON_PK,
        defaults={"about_markdown": DEFAULT_ABOUT_MARKDOWN},
    )


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0022_cataloghomesettings"),
    ]

    operations = [
        migrations.RunPython(
            seed_catalog_home_settings,
            migrations.RunPython.noop,
        ),
    ]
