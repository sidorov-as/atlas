import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models import Q
from django.utils import timezone


def _legacy_pair_fields(GroupDetails):
    field = GroupDetails._meta.get_field("members")
    return (
        field.remote_field.through,
        field.m2m_field_name(),
        field.m2m_reverse_field_name(),
    )


def migrate_memberships_forward(apps, schema_editor):
    GroupDetails = apps.get_model("catalog", "GroupDetails")
    CatalogEntity = apps.get_model("catalog", "CatalogEntity")
    Grant = apps.get_model("catalog", "GroupMembershipGrant")
    through, group_field, actor_field = _legacy_pair_fields(GroupDetails)

    pairs = list(
        through.objects.using(schema_editor.connection.alias).values_list(
            f"{group_field}_id", f"{actor_field}_id"
        )
    )
    if len(pairs) != len(set(pairs)):
        raise RuntimeError(
            "duplicate Actor/Group membership pairs exist before migration"
        )
    group_ids = {group_id for group_id, _actor_id in pairs}
    actor_ids = {actor_id for _group_id, actor_id in pairs}
    if GroupDetails.objects.filter(pk__in=group_ids).count() != len(group_ids):
        raise RuntimeError(
            "orphaned Group membership rows exist before migration"
        )
    if CatalogEntity.objects.filter(pk__in=actor_ids).count() != len(actor_ids):
        raise RuntimeError(
            "orphaned Actor membership rows exist before migration"
        )

    confirmed_at = timezone.now()
    Grant.objects.bulk_create(
        [
            Grant(
                group_id=group_id,
                actor_id=actor_id,
                source_kind="manual",
                legacy_unclassified=True,
                last_confirmed_at=confirmed_at,
            )
            for group_id, actor_id in pairs
        ]
    )
    migrated_pairs = set(
        Grant.objects.values_list("group_id", "actor_id").distinct()
    )
    if migrated_pairs != set(pairs) or Grant.objects.count() != len(pairs):
        raise RuntimeError(
            "membership grant migration changed effective membership"
        )


def migrate_memberships_reverse(apps, schema_editor):
    GroupDetails = apps.get_model("catalog", "GroupDetails")
    Grant = apps.get_model("catalog", "GroupMembershipGrant")
    through, group_field, actor_field = _legacy_pair_fields(GroupDetails)
    database = schema_editor.connection.alias
    now = timezone.now()
    pairs = set(
        Grant.objects.using(database)
        .filter(revoked_at__isnull=True)
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
        .filter(
            Q(identity_link__isnull=True)
            | Q(identity_link__revoked_at__isnull=True)
        )
        .values_list("group_id", "actor_id")
    )
    through.objects.using(database).all().delete()
    through.objects.using(database).bulk_create(
        [
            through(
                **{f"{group_field}_id": group_id, f"{actor_field}_id": actor_id}
            )
            for group_id, actor_id in pairs
        ]
    )
    if through.objects.using(database).count() != len(pairs):
        raise RuntimeError(
            "membership rollback failed to restore effective pairs"
        )


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0026_authenticationattempt"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="externalidentitylink",
            name="unique_external_identity_per_provider",
        ),
        migrations.AddField(
            model_name="externalidentitylink",
            name="source_id",
            field=models.CharField(blank=True, default="", max_length=512),
        ),
        migrations.AddField(
            model_name="externalidentitylink",
            name="revoked_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddConstraint(
            model_name="externalidentitylink",
            constraint=models.UniqueConstraint(
                fields=("provider_id", "source_id", "external_subject"),
                name="catalog_unique_external_identity_source",
            ),
        ),
        migrations.CreateModel(
            name="GroupMembershipGrant",
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
                    "source_kind",
                    models.CharField(
                        choices=(
                            ("manual", "Manual"),
                            ("provider", "Authentication provider"),
                        ),
                        default="manual",
                        max_length=16,
                    ),
                ),
                (
                    "external_key",
                    models.CharField(blank=True, default="", max_length=512),
                ),
                ("legacy_unclassified", models.BooleanField(default=False)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "last_confirmed_at",
                    models.DateTimeField(default=timezone.now),
                ),
                (
                    "actor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="membership_grants",
                        to="catalog.catalogentity",
                    ),
                ),
                (
                    "group",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="membership_grants",
                        to="catalog.groupdetails",
                    ),
                ),
                (
                    "identity_link",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="membership_grants",
                        to="catalog.externalidentitylink",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=("actor", "group"),
                        name="catalog_grant_actor_group",
                    ),
                    models.Index(
                        fields=("group", "actor", "expires_at"),
                        name="catalog_grant_group_expiry",
                    ),
                    models.Index(
                        fields=("identity_link", "external_key"),
                        name="catalog_grant_link_key",
                    ),
                ],
                "constraints": [
                    models.CheckConstraint(
                        condition=Q(
                            Q(
                                ("expires_at__isnull", True),
                                ("external_key", ""),
                                ("identity_link__isnull", True),
                                ("source_kind", "manual"),
                            ),
                            Q(
                                ("identity_link__isnull", False),
                                ("legacy_unclassified", False),
                                ("source_kind", "provider"),
                            ),
                            _connector="OR",
                        ),
                        name="catalog_membership_grant_source_shape",
                    ),
                    models.UniqueConstraint(
                        condition=Q(("source_kind", "manual")),
                        fields=("group", "actor"),
                        name="catalog_unique_manual_membership_grant",
                    ),
                    models.UniqueConstraint(
                        condition=Q(("source_kind", "provider")),
                        fields=(
                            "group",
                            "actor",
                            "identity_link",
                            "external_key",
                        ),
                        name="catalog_unique_provider_membership_grant",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="MembershipGrantAuditRecord",
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
                ("grant_id", models.PositiveBigIntegerField(db_index=True)),
                ("group_id", models.UUIDField(db_index=True)),
                ("actor_id", models.UUIDField(db_index=True)),
                (
                    "identity_link_id",
                    models.PositiveBigIntegerField(blank=True, null=True),
                ),
                (
                    "action",
                    models.CharField(
                        choices=(
                            ("classify_manual", "Classify as manual"),
                            ("transfer_provider", "Transfer to provider"),
                        ),
                        max_length=32,
                    ),
                ),
                ("reason", models.TextField()),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
                ("details", models.JSONField(blank=True, default=dict)),
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
        migrations.RunPython(
            migrate_memberships_forward, migrate_memberships_reverse
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name="groupdetails",
                    name="members",
                    field=models.ManyToManyField(
                        blank=True,
                        related_name="member_of",
                        through="catalog.GroupMembershipGrant",
                        through_fields=("group", "actor"),
                        to="catalog.catalogentity",
                    ),
                ),
                migrations.CreateModel(
                    name="LegacyGroupMembershipPair",
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
                            "catalogentity",
                            models.ForeignKey(
                                db_column="catalogentity_id",
                                on_delete=django.db.models.deletion.CASCADE,
                                to="catalog.catalogentity",
                            ),
                        ),
                        (
                            "groupdetails",
                            models.ForeignKey(
                                db_column="groupdetails_id",
                                on_delete=django.db.models.deletion.CASCADE,
                                to="catalog.groupdetails",
                            ),
                        ),
                    ],
                    options={
                        "db_table": "catalog_groupdetails_members",
                        "unique_together": {("groupdetails", "catalogentity")},
                    },
                ),
            ],
        ),
    ]
