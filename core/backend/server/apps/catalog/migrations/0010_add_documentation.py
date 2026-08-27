from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0009_api_spec_source"),
    ]

    operations = [
        migrations.AddField(
            model_name="api",
            name="documentation",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="component",
            name="documentation",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="flow",
            name="documentation",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="group",
            name="documentation",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="resource",
            name="documentation",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="system",
            name="documentation",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="user",
            name="documentation",
            field=models.TextField(blank=True),
        ),
    ]
