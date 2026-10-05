"""Database schemas as searchable documents (`search-database-schema-source` spec)."""

import pytest
from atlas_plugin_api import STATUS_REMOVED, get_catalog_entity_model

from atlas_plugin_database_schema.models import DatabaseSchema
from atlas_plugin_database_schema.parser import parse_schema
from atlas_plugin_database_schema.search_source import (
    database_schema_search_source as source,
)
from atlas_plugin_database_schema.search_source import flatten_schema_text

pytestmark = pytest.mark.django_db

SQL = (
    "CREATE TABLE users (id uuid PRIMARY KEY, email_address varchar(255) NOT NULL); "
    "CREATE TABLE order_items (id uuid PRIMARY KEY, user_id uuid REFERENCES users(id));"
)


# --- flattening --------------------------------------------------------------


def test_flatten_guards_the_parser_output_shape():
    """Fails loudly if the parser's structure changes: the names must still be found."""
    text = flatten_schema_text(parse_schema(SQL, "postgresql"))

    for name in ("users", "email_address", "order_items", "user_id"):
        assert name in text.split()
    for part in ("email", "address", "order", "items"):
        assert part in text.split()


def test_flatten_puts_one_table_per_line_with_its_columns():
    lines = flatten_schema_text(parse_schema(SQL, "postgresql")).splitlines()

    assert len(lines) == 2
    assert lines[0].startswith("users ")
    assert "email_address" in lines[0]
    assert "user_id" in lines[1]
    assert "email_address" not in lines[1]


@pytest.mark.parametrize(
    "parsed",
    [
        {},
        None,
        "text",
        [],
        {"tables": None},
        {"tables": "x"},
        {"tables": [None, 3, "t", []]},
        {"tables": [{"name": None, "columns": None}]},
        {"tables": [{"name": "  ", "columns": [None, {"name": 5}, {}]}]},
    ],
)
def test_flatten_tolerates_empty_and_unexpected_shapes(parsed):
    assert flatten_schema_text(parsed) == ""


def test_flatten_keeps_valid_names_next_to_malformed_entries():
    parsed = {"tables": [None, {"name": "t", "columns": [5, {"name": "c"}]}]}

    assert flatten_schema_text(parsed) == "t c"


# --- documents ---------------------------------------------------------------


@pytest.fixture
def facet(resource):
    return DatabaseSchema.objects.create(
        entity=resource,
        source_sql=SQL,
        parsed_schema=parse_schema(SQL, "postgresql"),
    )


def test_document_is_keyed_to_the_owner_and_titled_with_its_name(facet, resource):
    [document] = source.documents([f"schema:{resource.pk}"])

    assert document.id == f"schema:{resource.pk}"
    assert document.kind == "schema"
    assert document.title == "primary-db"
    assert "order_items" in document.body
    assert "user_id" in document.body
    assert "CREATE TABLE" not in document.body


def test_failed_parse_is_indexed_from_its_title_only(resource):
    DatabaseSchema.objects.create(
        entity=resource,
        source_sql="not sql",
        parsed_schema={"tables": [{"name": "stale", "columns": []}]},
        parse_status=DatabaseSchema.PARSE_STATUS_FAILED,
    )

    [document] = source.documents([f"schema:{resource.pk}"])

    assert document.title == "primary-db"
    assert document.body == ""


def test_one_bad_facet_does_not_break_the_rest(facet, group):
    from server.apps.catalog.tests.factories import create_resource

    other = create_resource(name="other-db", owner=group, type="database")
    DatabaseSchema.objects.create(
        entity=other, parsed_schema={"tables": "garbage"}, parse_status="ok"
    )

    documents = {d.title: d for d in source.all_documents()}

    assert set(documents) == {"primary-db", "other-db"}
    assert documents["other-db"].body == ""


def test_documents_omit_unknown_ids_and_removed_owners(facet, resource):
    assert list(source.documents(["schema:not-a-uuid", "note:1", "schema"])) == []

    get_catalog_entity_model().objects.filter(pk=resource.pk).update(
        status=STATUS_REMOVED
    )

    assert list(source.documents([f"schema:{resource.pk}"])) == []
    assert list(source.all_documents()) == []


def test_owner_change_maps_to_its_schema_document(facet, resource, group):
    from server.apps.catalog.tests.factories import create_resource

    without_facet = create_resource(name="no-schema", owner=group, type="database")

    assert list(source.document_ids_for_instance(resource)) == [f"schema:{resource.pk}"]
    assert list(source.document_ids_for_instance(without_facet)) == []


def test_facet_change_maps_to_its_document(facet):
    assert list(source.document_ids_for_instance(facet)) == [f"schema:{facet.pk}"]


def test_watches_the_facet_and_catalog_entities():
    assert set(source.watched_models) == {
        "database_schema_plugin.DatabaseSchema",
        "catalog.CatalogEntity",
    }


# --- resolve -----------------------------------------------------------------


def test_resolve_links_to_the_owners_schema_tab(facet, resource, owner_user):
    [hit] = source.resolve([f"schema:{resource.pk}"], owner_user.actor_details.account)

    assert hit.link == f"/resources/{resource.pk}?tab=schema"
    assert hit.title == "primary-db"
    assert "order_items" in hit.text


def test_resolve_shows_a_renamed_owner_without_reindexing(facet, resource, owner_user):
    get_catalog_entity_model().objects.filter(pk=resource.pk).update(name="renamed-db")

    [hit] = source.resolve([f"schema:{resource.pk}"], owner_user.actor_details.account)

    assert hit.title == "renamed-db"


def test_resolve_omits_anonymous_actors_and_unreadable_owners(
    facet, resource, owner_user
):
    from django.contrib.auth.models import AnonymousUser

    assert source.resolve([f"schema:{resource.pk}"], AnonymousUser()) == []

    get_catalog_entity_model().objects.filter(pk=resource.pk).update(
        status=STATUS_REMOVED
    )

    assert (
        source.resolve([f"schema:{resource.pk}"], owner_user.actor_details.account)
        == []
    )


def test_resolve_omits_owners_of_a_kind_that_does_not_host_schemas(
    facet, resource, owner_user, monkeypatch
):
    from atlas_plugin_api import Ok

    monkeypatch.setattr(
        "atlas_plugin_database_schema.search_source.resolve_capability",
        lambda kind, capability: Ok(False),
    )

    assert (
        source.resolve([f"schema:{resource.pk}"], owner_user.actor_details.account)
        == []
    )
