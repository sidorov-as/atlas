"""Unit tests for `DatabaseSchemaFacetWriter`: the
`atlas.ingestion.facet_writers.v1` implementation `plugin.register_runtime()`
registers under key `'database-schema'`.
"""

import pytest

from atlas_plugin_database_schema.facet_writer import DatabaseSchemaFacetWriter
from atlas_plugin_database_schema.models import DatabaseSchema

pytestmark = pytest.mark.django_db

VALID_SQL = "CREATE TABLE users (id uuid PRIMARY KEY, email varchar(255) NOT NULL);"
OTHER_SQL = "CREATE TABLE accounts (id uuid PRIMARY KEY);"
INVALID_SQL = "this is not sql"


def test_apply_creates_the_facet(resource):
    DatabaseSchemaFacetWriter().apply(resource, "postgresql", VALID_SQL)

    facet = DatabaseSchema.objects.get(pk=resource.pk)
    assert facet.dialect == "postgresql"
    assert facet.source_sql == VALID_SQL
    assert facet.parse_status == DatabaseSchema.PARSE_STATUS_OK
    assert facet.parsed_schema["tables"][0]["name"] == "users"


def test_apply_again_updates_the_existing_facet_in_place(resource):
    writer = DatabaseSchemaFacetWriter()
    writer.apply(resource, "postgresql", VALID_SQL)

    writer.apply(resource, "postgresql", OTHER_SQL)

    assert DatabaseSchema.objects.filter(pk=resource.pk).count() == 1
    facet = DatabaseSchema.objects.get(pk=resource.pk)
    assert facet.source_sql == OTHER_SQL
    assert facet.parsed_schema["tables"][0]["name"] == "accounts"


def test_apply_with_unparseable_sql_still_saves_it(resource):
    DatabaseSchemaFacetWriter().apply(resource, "postgresql", INVALID_SQL)

    facet = DatabaseSchema.objects.get(pk=resource.pk)
    assert facet.source_sql == INVALID_SQL
    assert facet.parse_status == DatabaseSchema.PARSE_STATUS_FAILED
    assert facet.parsed_schema == {}


def test_clear_removes_an_existing_facet(resource):
    writer = DatabaseSchemaFacetWriter()
    writer.apply(resource, "postgresql", VALID_SQL)

    writer.clear(resource)

    assert not DatabaseSchema.objects.filter(pk=resource.pk).exists()


def test_clear_is_a_no_op_when_no_facet_exists(resource):
    DatabaseSchemaFacetWriter().clear(resource)

    assert not DatabaseSchema.objects.filter(pk=resource.pk).exists()
