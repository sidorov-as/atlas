"""Tests for the shared schema write function and permission guard."""

import pytest
from atlas_plugin_api import SOURCE_YAML, get_catalog_entity_model

from atlas_plugin_database_schema.facet_writer import DatabaseSchemaFacetWriter
from atlas_plugin_database_schema.models import DatabaseSchema
from atlas_plugin_database_schema.writer import (
    SchemaWriteForbiddenError,
    apply_schema_source,
    check_schema_write_permission,
)

pytestmark = pytest.mark.django_db

VALID_SQL = "CREATE TABLE users (id uuid PRIMARY KEY, email varchar(255) NOT NULL);"
NO_TABLE_SQL = "SELECT 1;"


def test_failed_parse_returns_the_parser_message_and_saves_the_sql(resource):
    facet = DatabaseSchema(entity=resource)

    status, error = apply_schema_source(
        facet, dialect="postgresql", source_sql=NO_TABLE_SQL
    )

    assert status == DatabaseSchema.PARSE_STATUS_FAILED
    assert error == "No CREATE TABLE statement found"
    saved = DatabaseSchema.objects.get(pk=resource.pk)
    assert saved.source_sql == NO_TABLE_SQL
    assert saved.parsed_schema == {}


def test_successful_parse_has_an_empty_error(resource):
    facet = DatabaseSchema(entity=resource)

    status, error = apply_schema_source(
        facet, dialect="postgresql", source_sql=VALID_SQL
    )

    assert status == DatabaseSchema.PARSE_STATUS_OK
    assert error == ""


def test_crud_and_ingestion_store_identical_state(owner_client, resource, group):
    from server.apps.catalog.tests.factories import create_resource

    other = create_resource(name="other-db", owner=group, type="database")
    owner_client.post(
        f"/api/plugins/atlas.database-schema/resources/{resource.id}/schema/",
        {"dialect": "mysql", "sourceSql": VALID_SQL},
        content_type="application/json",
    )
    DatabaseSchemaFacetWriter().apply(other, "mysql", VALID_SQL)

    crud = DatabaseSchema.objects.get(pk=resource.pk)
    ingested = DatabaseSchema.objects.get(pk=other.pk)
    assert (crud.dialect, crud.source_sql, crud.parsed_schema, crud.parse_status) == (
        ingested.dialect,
        ingested.source_sql,
        ingested.parsed_schema,
        ingested.parse_status,
    )


def test_permission_allows_an_owner(owner_user, owner_account, resource):
    check_schema_write_permission(owner_account, resource)


def test_permission_rejects_a_yaml_managed_resource(
    owner_user, owner_account, resource
):
    get_catalog_entity_model().objects.filter(pk=resource.pk).update(
        source_kind=SOURCE_YAML
    )
    resource.refresh_from_db()

    with pytest.raises(SchemaWriteForbiddenError, match="read-only"):
        check_schema_write_permission(owner_account, resource)


def test_permission_rejects_a_caller_outside_the_owner_group(db, resource):
    from django.contrib.auth import get_user_model

    stranger = get_user_model().objects.create_user(
        username="x", password="password123"
    )

    with pytest.raises(SchemaWriteForbiddenError):
        check_schema_write_permission(stranger, resource)
