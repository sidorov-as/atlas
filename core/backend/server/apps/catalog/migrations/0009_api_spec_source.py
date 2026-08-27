from django.db import migrations, models


def migrate_definition_to_spec_content(apps, schema_editor):
    API = apps.get_model("catalog", "API")
    for api in API.objects.all():
        if api.definition:
            api.spec_source = "inline"
            api.spec_content = api.definition
        else:
            api.spec_source = "none"
        api.save(update_fields=["spec_source", "spec_content"])


def reverse_spec_content_to_definition(apps, schema_editor):
    API = apps.get_model("catalog", "API")
    for api in API.objects.all():
        api.definition = api.spec_content
        api.save(update_fields=["definition"])


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0008_flow"),
    ]

    operations = [
        migrations.AddField(
            model_name="api",
            name="spec_source",
            field=models.CharField(
                choices=[
                    ("none", "None"),
                    ("inline", "Inline"),
                    ("url", "URL"),
                ],
                default="none",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="api",
            name="spec_url",
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name="api",
            name="spec_content",
            field=models.TextField(
                blank=True,
                help_text="Resolved spec snapshot, regardless of source",
            ),
        ),
        migrations.AddField(
            model_name="api",
            name="spec_resolved_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="api",
            name="spec_resolve_failed",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(
            migrate_definition_to_spec_content,
            reverse_spec_content_to_definition,
        ),
        migrations.RemoveField(
            model_name="api",
            name="definition",
        ),
    ]
