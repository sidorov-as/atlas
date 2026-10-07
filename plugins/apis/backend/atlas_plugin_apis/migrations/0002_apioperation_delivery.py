from typing import ClassVar

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies: ClassVar[list] = [
        ("apis_plugin", "0001_initial"),
    ]

    operations: ClassVar[list] = [
        migrations.AddField(
            model_name="apioperation",
            name="delivery",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
