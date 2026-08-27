import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0028_provisioning_services"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="authenticationattempt",
            name="policy_generation",
            field=models.PositiveBigIntegerField(default=1),
        ),
        migrations.AddField(
            model_name="authenticationattempt",
            name="source_generation",
            field=models.PositiveBigIntegerField(default=0),
        ),
        migrations.CreateModel(
            name="AuthenticationPolicyState",
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
                ("digest", models.CharField(max_length=64)),
                ("generation", models.PositiveBigIntegerField(default=1)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="AuthenticationPrincipalState",
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
                (
                    "revocation_generation",
                    models.PositiveBigIntegerField(default=0),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="authentication_state",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="AuthenticationRateLimit",
            fields=[
                (
                    "key_hash",
                    models.CharField(
                        max_length=64, primary_key=True, serialize=False
                    ),
                ),
                ("scope", models.CharField(db_index=True, max_length=32)),
                ("window_started_at", models.DateTimeField()),
                ("count", models.PositiveIntegerField(default=0)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
