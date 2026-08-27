from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("catalog", "0025_accountaccess")]

    operations = [
        migrations.CreateModel(
            name="AuthenticationAttempt",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("provider_id", models.CharField(max_length=128)),
                ("source_id", models.CharField(max_length=512)),
                (
                    "state_digest",
                    models.CharField(max_length=64, null=True, unique=True),
                ),
                ("browser_session_digest", models.CharField(max_length=64)),
                ("return_url", models.TextField()),
                ("correlation_id", models.UUIDField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField()),
                ("consumed_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["provider_id", "expires_at"],
                        name="catalog_auth_attempt_expiry",
                    )
                ]
            },
        )
    ]
