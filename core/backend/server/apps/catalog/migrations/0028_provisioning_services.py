import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0027_group_membership_grants"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="externalidentitylink",
            name="revocation_generation",
            field=models.PositiveBigIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="externalidentitylink",
            name="last_applied_generation",
            field=models.PositiveBigIntegerField(default=0),
        ),
        migrations.CreateModel(
            name="AuthenticationSourceBinding",
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
                ("configuration_fingerprint", models.CharField(max_length=255)),
                (
                    "lock_digest",
                    models.CharField(blank=True, default="", max_length=255),
                ),
                ("generation", models.PositiveBigIntegerField(default=1)),
                ("activated_at", models.DateTimeField(auto_now_add=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("provider_id", "source_id"),
                        name="catalog_unique_auth_source_binding",
                    )
                ]
            },
        ),
        migrations.CreateModel(
            name="AuthenticationSecurityEvent",
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
                ("category", models.CharField(max_length=64)),
                (
                    "stage",
                    models.CharField(default="provisioning", max_length=64),
                ),
                ("provider_id", models.CharField(max_length=128)),
                ("source_id", models.CharField(max_length=512)),
                (
                    "correlation_id",
                    models.CharField(db_index=True, max_length=64),
                ),
                (
                    "principal_id",
                    models.PositiveBigIntegerField(blank=True, null=True),
                ),
                ("details", models.JSONField(blank=True, default=dict)),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ("-timestamp",)},
        ),
        migrations.CreateModel(
            name="ProvisioningAuditRecord",
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
                ("action", models.CharField(max_length=64)),
                ("provider_id", models.CharField(max_length=128)),
                ("source_id", models.CharField(max_length=512)),
                (
                    "principal_id",
                    models.PositiveBigIntegerField(
                        blank=True, db_index=True, null=True
                    ),
                ),
                (
                    "identity_link_id",
                    models.PositiveBigIntegerField(blank=True, null=True),
                ),
                ("actor_id", models.UUIDField(blank=True, null=True)),
                ("group_id", models.UUIDField(blank=True, null=True)),
                (
                    "correlation_id",
                    models.CharField(db_index=True, max_length=64),
                ),
                ("details", models.JSONField(blank=True, default=dict)),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
                (
                    "operator",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ("-timestamp",)},
        ),
    ]
