"""Schema facets record creation and modification times (`database-schema-plugin` spec:
"Schema facets record creation and modification times")."""

import pytest
from django.contrib import admin
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from atlas_plugin_database_schema.models import DatabaseSchema

BEFORE = ("database_schema_plugin", "0001_initial")
AFTER = ("database_schema_plugin", "0002_databaseschema_timestamps")


def test_new_facet_has_both_times(resource):
    facet = DatabaseSchema.objects.create(entity=resource, source_sql="")

    assert facet.created_at is not None
    assert facet.updated_at is not None


def test_edit_updates_modification_time_only(resource):
    facet = DatabaseSchema.objects.create(entity=resource, source_sql="")
    created_at, updated_at = facet.created_at, facet.updated_at

    facet.source_sql = "CREATE TABLE t (id int);"
    facet.save()
    facet.refresh_from_db()

    assert facet.created_at == created_at
    assert facet.updated_at > updated_at


def test_admin_shows_times_read_only():
    facet_admin = admin.site._registry[DatabaseSchema]

    assert {"created_at", "updated_at"} <= set(facet_admin.readonly_fields)


@pytest.mark.django_db(transaction=True)
def test_existing_facets_get_times_at_migration(resource):
    executor = MigrationExecutor(connection)
    executor.migrate([BEFORE])
    try:
        old_facet = executor.loader.project_state([BEFORE]).apps.get_model(
            "database_schema_plugin", "DatabaseSchema"
        )
        old_facet.objects.create(entity_id=resource.pk, source_sql="")

        executor = MigrationExecutor(connection)
        executor.migrate([AFTER])
        new_facet = executor.loader.project_state([AFTER]).apps.get_model(
            "database_schema_plugin", "DatabaseSchema"
        )

        migrated = new_facet.objects.get(pk=resource.pk)
        assert migrated.created_at is not None
        assert migrated.updated_at is not None
    finally:
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
