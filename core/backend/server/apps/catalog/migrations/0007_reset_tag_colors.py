from django.db import migrations

from server.apps.catalog.models.tag import DEFAULT_TAG_COLOR


def reset_tag_colors(apps, schema_editor):
    """Reset every existing `Tag.color` to the default palette key.

    Existing rows may hold a pre-palette hex value (or, after this data
    migration ships, any other now-invalid value); a reset is the chosen
    strategy over an automatic nearest-color mapping.
    """
    Tag = apps.get_model("catalog", "Tag")
    Tag.objects.exclude(color=DEFAULT_TAG_COLOR).update(color=DEFAULT_TAG_COLOR)


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0006_tag_palette"),
    ]

    operations = [
        migrations.RunPython(reset_tag_colors, migrations.RunPython.noop),
    ]
