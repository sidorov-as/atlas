from typing import ClassVar

from django.db import migrations, models
from django.db.models.functions import Now


class Migration(migrations.Migration):
    dependencies: ClassVar[list] = [
        ("database_schema_plugin", "0001_initial"),
    ]

    operations: ClassVar[list] = [
        # Existing rows get the migration time (real creation time is unknown)
        # from a database-side default that the AlterFields below drop.
        migrations.AddField(
            model_name="databaseschema",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, db_default=Now()),
        ),
        migrations.AddField(
            model_name="databaseschema",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, db_default=Now()),
        ),
        migrations.AlterField(
            model_name="databaseschema",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name="databaseschema",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
    ]
