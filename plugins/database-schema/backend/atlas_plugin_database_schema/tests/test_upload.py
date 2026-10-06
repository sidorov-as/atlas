"""`(resource, schema)` upload target (`database-schema-plugin` spec),
exercising the adapter directly: ticket issuance, the `PUT` route, and
YAML/permission checks belong to Core and are covered by its upload-ticket
tests."""

import pytest
from atlas_plugin_api import UploadValidationError, get_upload_target

from atlas_plugin_database_schema.models import DatabaseSchema
from atlas_plugin_database_schema.writer import write_resource_schema

pytestmark = pytest.mark.django_db

VALID_SQL = "CREATE TABLE users (id uuid PRIMARY KEY, email varchar(255) NOT NULL);"
TWO_TABLES = VALID_SQL + "\nCREATE TABLE orders (id uuid PRIMARY KEY);"
NO_TABLE_SQL = "SELECT 1;"


@pytest.fixture
def adapter():
    return get_upload_target("resource", "schema").adapter


def _apply(adapter, resource, body, dialect="postgresql", user=None):
    params = adapter.validate_params({"dialect": dialect})
    return adapter.apply(resource, body.encode(), params, user)


def test_target_requires_catalog_write():
    assert get_upload_target("resource", "schema").required_scope == "catalog:write"


def test_unsupported_dialect_is_rejected_at_request_time(adapter):
    with pytest.raises(UploadValidationError, match="oracle"):
        adapter.validate_params({"dialect": "oracle"})


def test_dialect_defaults_to_postgresql(adapter):
    assert adapter.validate_params({}) == {"dialect": "postgresql"}


def test_upload_creates_the_facet(adapter, resource):
    result = _apply(adapter, resource, TWO_TABLES, dialect="mysql")

    assert result.summary == {
        "parse_status": "ok",
        "parse_error": "",
        "table_count": 2,
    }
    facet = DatabaseSchema.objects.get(pk=resource.pk)
    assert (facet.dialect, facet.source_sql) == ("mysql", TWO_TABLES)


def test_upload_replaces_an_existing_facet(adapter, resource):
    write_resource_schema(resource, dialect="mysql", source_sql=TWO_TABLES)

    _apply(adapter, resource, VALID_SQL)

    facet = DatabaseSchema.objects.get(pk=resource.pk)
    assert facet.dialect == "postgresql"
    assert facet.source_sql == VALID_SQL
    assert len(facet.parsed_schema["tables"]) == 1


def test_unparseable_upload_is_saved_and_reported(adapter, resource):
    result = _apply(adapter, resource, NO_TABLE_SQL)

    assert result.summary == {
        "parse_status": "failed",
        "parse_error": "No CREATE TABLE statement found",
        "table_count": 0,
    }
    assert DatabaseSchema.objects.get(pk=resource.pk).source_sql == NO_TABLE_SQL


def test_non_utf8_body_is_rejected(adapter, resource):
    with pytest.raises(UploadValidationError, match="UTF-8"):
        adapter.apply(resource, b"\xff\xfe", {"dialect": "postgresql"}, None)
    assert not DatabaseSchema.objects.filter(pk=resource.pk).exists()


def test_upload_stores_the_same_state_as_the_crud_endpoint(
    adapter, owner_client, resource, group
):
    from server.apps.catalog.tests.factories import create_resource

    other = create_resource(name="other-db", owner=group, type="database")
    owner_client.post(
        f"/api/plugins/atlas.database-schema/resources/{other.id}/schema/",
        {"dialect": "postgresql", "sourceSql": TWO_TABLES},
        content_type="application/json",
    )

    _apply(adapter, resource, TWO_TABLES)

    crud = DatabaseSchema.objects.get(pk=other.pk)
    uploaded = DatabaseSchema.objects.get(pk=resource.pk)
    assert (uploaded.dialect, uploaded.parsed_schema, uploaded.parse_status) == (
        crud.dialect,
        crud.parsed_schema,
        crud.parse_status,
    )
