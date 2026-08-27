"""Introduce a single concrete `CatalogEntity` identity plus per-kind
`*Details` models, replacing the old one-table-per-kind layout
(ADR 0001). No existing catalog data is
preserved — the project has no production deployment yet;
`seed_booking_demo`/`seed_admin` repopulate a fresh database on
the new models.
"""

import uuid

import django.contrib.postgres.fields
import django.db.models.deletion
import django.db.models.functions.text
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("ingestion", "0002_conflictrecord"),
        ("catalog", "0011_architecture_relationship"),
    ]

    operations = [
        # Relation/ArchitectureRelationship stored polymorphic (kind, id) pairs
        # with no DB-level FK — dropped and recreated with real FKs below, same
        # as every other table in this migration (no existing data to preserve).
        migrations.DeleteModel(name="Relation"),
        migrations.DeleteModel(name="ArchitectureRelationship"),
        # Flow.system currently FKs to the old System table — drop it here so
        # System can be dropped below, then re-add pointing at CatalogEntity.
        migrations.RemoveField(model_name="flow", name="system"),
        # Drop the old one-table-per-kind models, most-dependent first so no
        # table is dropped while another still holds a live FK into it.
        migrations.DeleteModel(name="Component"),
        migrations.DeleteModel(name="API"),
        migrations.DeleteModel(name="Resource"),
        migrations.DeleteModel(name="System"),
        migrations.DeleteModel(name="Group"),
        migrations.DeleteModel(name="User"),
        migrations.CreateModel(
            name="CatalogEntity",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "kind",
                    models.CharField(
                        choices=[
                            ("system", "System"),
                            ("component", "Component"),
                            ("resource", "Resource"),
                            ("api", "API"),
                            ("group", "Group"),
                            ("user", "User"),
                        ],
                        max_length=16,
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                (
                    "namespace",
                    models.CharField(default="default", max_length=255),
                ),
                ("title", models.CharField(blank=True, max_length=255)),
                ("description", models.TextField(blank=True)),
                ("documentation", models.TextField(blank=True)),
                ("labels", models.JSONField(blank=True, default=dict)),
                (
                    "tags",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.CharField(max_length=100),
                        blank=True,
                        default=list,
                        size=None,
                    ),
                ),
                ("links", models.JSONField(blank=True, default=list)),
                (
                    "source_kind",
                    models.CharField(
                        choices=[("manual", "Manual"), ("yaml", "YAML")],
                        default="manual",
                        max_length=16,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "ingested_from",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="claimed_entities",
                        to="ingestion.registeredrepository",
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="owned_entities",
                        to="catalog.catalogentity",
                    ),
                ),
            ],
            options={
                "ordering": ["name"],
                "abstract": False,
            },
        ),
        migrations.AddConstraint(
            model_name="catalogentity",
            constraint=models.UniqueConstraint(
                django.db.models.functions.text.Lower("name"),
                models.F("namespace"),
                models.F("kind"),
                name="catalog_entity_unique_kind_namespace_name",
            ),
        ),
        migrations.CreateModel(
            name="SystemDetails",
            fields=[
                (
                    "entity",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        related_name="system_details",
                        serialize=False,
                        to="catalog.catalogentity",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ResourceDetails",
            fields=[
                (
                    "entity",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        related_name="resource_details",
                        serialize=False,
                        to="catalog.catalogentity",
                    ),
                ),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("database", "Database"),
                            ("cache", "Cache"),
                            ("bucket", "Bucket"),
                            ("queue", "Queue"),
                            ("cluster", "Cluster"),
                        ],
                        max_length=32,
                    ),
                ),
                (
                    "system",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="resources",
                        to="catalog.catalogentity",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ApiDetails",
            fields=[
                (
                    "entity",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        related_name="api_details",
                        serialize=False,
                        to="catalog.catalogentity",
                    ),
                ),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("openapi", "OpenAPI"),
                            ("grpc", "gRPC"),
                            ("asyncapi", "AsyncAPI"),
                            ("graphql", "GraphQL"),
                        ],
                        max_length=32,
                    ),
                ),
                (
                    "spec_source",
                    models.CharField(
                        choices=[
                            ("none", "None"),
                            ("inline", "Inline"),
                            ("url", "URL"),
                        ],
                        default="none",
                        max_length=16,
                    ),
                ),
                ("spec_url", models.URLField(blank=True)),
                (
                    "spec_content",
                    models.TextField(
                        blank=True,
                        help_text=(
                            "Resolved spec snapshot, regardless of source"
                        ),
                    ),
                ),
                (
                    "spec_resolved_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                ("spec_resolve_failed", models.BooleanField(default=False)),
                (
                    "system",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="apis",
                        to="catalog.catalogentity",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ComponentDetails",
            fields=[
                (
                    "entity",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        related_name="component_details",
                        serialize=False,
                        to="catalog.catalogentity",
                    ),
                ),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("service", "Service"),
                            ("website", "Website"),
                            ("library", "Library"),
                            ("worker", "Worker"),
                        ],
                        max_length=32,
                    ),
                ),
                (
                    "lifecycle",
                    models.CharField(
                        choices=[
                            ("experimental", "Experimental"),
                            ("production", "Production"),
                            ("deprecated", "Deprecated"),
                        ],
                        max_length=32,
                    ),
                ),
                (
                    "system",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="components",
                        to="catalog.catalogentity",
                    ),
                ),
                (
                    "provides_apis",
                    models.ManyToManyField(
                        blank=True,
                        related_name="provided_by",
                        to="catalog.catalogentity",
                    ),
                ),
                (
                    "consumes_apis",
                    models.ManyToManyField(
                        blank=True,
                        related_name="consumed_by",
                        to="catalog.catalogentity",
                    ),
                ),
                (
                    "depends_on",
                    models.ManyToManyField(
                        blank=True,
                        related_name="depended_on_by",
                        to="catalog.catalogentity",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="GroupDetails",
            fields=[
                (
                    "entity",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        related_name="group_details",
                        serialize=False,
                        to="catalog.catalogentity",
                    ),
                ),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("team", "Team"),
                            ("business-unit", "Business unit"),
                            ("product-area", "Product area"),
                            ("root", "Root"),
                        ],
                        max_length=32,
                    ),
                ),
                (
                    "members",
                    models.ManyToManyField(
                        blank=True,
                        related_name="member_of",
                        to="catalog.catalogentity",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ActorDetails",
            fields=[
                (
                    "entity",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        related_name="actor_details",
                        serialize=False,
                        to="catalog.catalogentity",
                    ),
                ),
                ("display_name", models.CharField(blank=True, max_length=255)),
                ("email", models.EmailField(blank=True, max_length=254)),
                (
                    "account",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="catalog_actor",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="flow",
            name="system",
            field=models.ForeignKey(
                default=None,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="flows",
                to="catalog.catalogentity",
            ),
            preserve_default=False,
        ),
        migrations.CreateModel(
            name="Relation",
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
                ("predicate", models.CharField(max_length=32)),
                (
                    "subject_entity",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="relations_as_subject",
                        to="catalog.catalogentity",
                    ),
                ),
                (
                    "object_entity",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="relations_as_object",
                        to="catalog.catalogentity",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["subject_entity", "predicate"],
                        name="catalog_rel_subject_a9b50a_idx",
                    ),
                    models.Index(
                        fields=["object_entity", "predicate"],
                        name="catalog_rel_object__aeab79_idx",
                    ),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("subject_entity", "predicate", "object_entity"),
                        name="catalog_relation_unique_edge",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="ArchitectureRelationship",
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
                ("label", models.CharField(max_length=255)),
                ("technology", models.CharField(blank=True, max_length=255)),
                (
                    "interaction_kind",
                    models.CharField(
                        choices=[
                            ("synchronous", "Synchronous"),
                            ("asynchronous", "Asynchronous"),
                            ("data-access", "Data access"),
                            ("manual", "Manual"),
                        ],
                        default="manual",
                        max_length=16,
                    ),
                ),
                (
                    "tags",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.CharField(max_length=100),
                        blank=True,
                        default=list,
                    ),
                ),
                (
                    "origin",
                    models.CharField(
                        choices=[("manual", "Manual"), ("yaml", "YAML")],
                        default="manual",
                        max_length=16,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "source",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="architecture_relationships_as_source",
                        to="catalog.catalogentity",
                    ),
                ),
                (
                    "target",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="architecture_relationships_as_target",
                        to="catalog.catalogentity",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["source"], name="catalog_arc_source__fa4746_idx"
                    ),
                    models.Index(
                        fields=["target"], name="catalog_arc_target__1fa295_idx"
                    ),
                ],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(("label", ""), _negated=True),
                        name="catalog_architecture_relationship_label_nonempty",
                    ),
                ],
            },
        ),
    ]
