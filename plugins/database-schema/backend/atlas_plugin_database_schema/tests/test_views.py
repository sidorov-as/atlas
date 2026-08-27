"""Tests for the facet CRUD endpoint and the failed-parse-
preserves-input path (a failed parse preserves the saved SQL).
"""

import pytest
from atlas_plugin_api import SOURCE_YAML, get_catalog_entity_model
from atlas_plugin_standard_catalog.models import ResourceDetails

from atlas_plugin_database_schema.api.schemas import _SOURCE_SQL_MAX_LENGTH
from atlas_plugin_database_schema.models import DatabaseSchema

pytestmark = pytest.mark.django_db

VALID_SQL = "CREATE TABLE users (id uuid PRIMARY KEY, email varchar(255) NOT NULL);"
INVALID_SQL = "this is not sql"


def _url(resource) -> str:
    return f"/api/plugins/atlas.database-schema/resources/{resource.id}/schema/"


def test_post_creates_the_facet_with_a_successful_parse(owner_client, resource):
    response = owner_client.post(
        _url(resource),
        {"sourceSql": VALID_SQL},
        content_type="application/json",
    )
    assert response.status_code == 201
    body = response.json()
    assert body["parseStatus"] == "ok"
    assert body["sourceSql"] == VALID_SQL
    assert body["parsedSchema"]["tables"][0]["name"] == "users"
    assert DatabaseSchema.objects.filter(pk=resource.pk).exists()


def test_dialect_defaults_to_postgresql_when_not_specified(
    owner_client,
    resource,
):
    response = owner_client.post(
        _url(resource),
        {"sourceSql": VALID_SQL},
        content_type="application/json",
    )
    assert response.json()["dialect"] == "postgresql"


def test_selecting_a_non_default_dialect_parses_that_dialects_sql(
    owner_client,
    resource,
):
    mysql_sql = (
        "CREATE TABLE users "
        "(id INT PRIMARY KEY AUTO_INCREMENT, email VARCHAR(255) NOT NULL);"
    )
    response = owner_client.post(
        _url(resource),
        {"dialect": "mysql", "sourceSql": mysql_sql},
        content_type="application/json",
    )
    assert response.status_code == 201
    body = response.json()
    assert body["dialect"] == "mysql"
    assert body["parseStatus"] == "ok"
    assert body["parsedSchema"]["tables"][0]["name"] == "users"


def test_patch_can_change_the_dialect(owner_client, resource):
    owner_client.post(
        _url(resource),
        {"sourceSql": VALID_SQL},
        content_type="application/json",
    )

    mssql_sql = "CREATE TABLE users (id INT IDENTITY(1,1) PRIMARY KEY);"
    response = owner_client.patch(
        _url(resource),
        {"dialect": "mssql", "sourceSql": mssql_sql},
        content_type="application/json",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["dialect"] == "mssql"
    assert body["parseStatus"] == "ok"


def test_post_with_oversized_source_sql_is_rejected(owner_client, resource):
    response = owner_client.post(
        _url(resource),
        {"sourceSql": "x" * (_SOURCE_SQL_MAX_LENGTH + 1)},
        content_type="application/json",
    )
    assert response.status_code == 400
    assert not DatabaseSchema.objects.filter(pk=resource.pk).exists()


def test_patch_with_oversized_source_sql_is_rejected(owner_client, resource):
    owner_client.post(
        _url(resource), {"sourceSql": VALID_SQL}, content_type="application/json"
    )

    response = owner_client.patch(
        _url(resource),
        {"sourceSql": "x" * (_SOURCE_SQL_MAX_LENGTH + 1)},
        content_type="application/json",
    )

    assert response.status_code == 400
    facet = DatabaseSchema.objects.get(pk=resource.pk)
    assert facet.source_sql == VALID_SQL


def test_post_twice_returns_conflict(owner_client, resource):
    owner_client.post(
        _url(resource), {"sourceSql": VALID_SQL}, content_type="application/json"
    )
    response = owner_client.post(
        _url(resource), {"sourceSql": VALID_SQL}, content_type="application/json"
    )
    assert response.status_code == 409


def test_get_returns_404_when_no_facet_exists(owner_client, resource):
    response = owner_client.get(_url(resource))
    assert response.status_code == 404


def test_get_returns_the_facet(owner_client, resource):
    owner_client.post(
        _url(resource), {"sourceSql": VALID_SQL}, content_type="application/json"
    )
    response = owner_client.get(_url(resource))
    assert response.status_code == 200
    assert response.json()["sourceSql"] == VALID_SQL


def test_unknown_resource_returns_404(owner_client):
    response = owner_client.get(
        "/api/plugins/atlas.database-schema/resources/00000000-0000-0000-0000-000000000000/schema/",
    )
    assert response.status_code == 404


def test_unauthenticated_request_is_rejected(dmr_client, resource):
    response = dmr_client.get(_url(resource))
    assert response.status_code == 401


def test_failed_parse_is_saved_with_a_failure_indicator_not_rejected(
    owner_client, resource
):
    response = owner_client.post(
        _url(resource),
        {"sourceSql": INVALID_SQL},
        content_type="application/json",
    )
    assert response.status_code == 201
    body = response.json()
    assert body["parseStatus"] == "failed"
    assert body["sourceSql"] == INVALID_SQL

    facet = DatabaseSchema.objects.get(pk=resource.pk)
    assert facet.source_sql == INVALID_SQL
    assert facet.parse_status == DatabaseSchema.PARSE_STATUS_FAILED


def test_patch_with_invalid_sql_preserves_the_submitted_text(owner_client, resource):
    owner_client.post(
        _url(resource), {"sourceSql": VALID_SQL}, content_type="application/json"
    )

    response = owner_client.patch(
        _url(resource),
        {"sourceSql": INVALID_SQL},
        content_type="application/json",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["parseStatus"] == "failed"
    assert body["sourceSql"] == INVALID_SQL

    facet = DatabaseSchema.objects.get(pk=resource.pk)
    assert facet.source_sql == INVALID_SQL
    assert facet.parse_status == DatabaseSchema.PARSE_STATUS_FAILED


def test_patch_recovers_from_a_failed_parse(owner_client, resource):
    owner_client.post(
        _url(resource), {"sourceSql": INVALID_SQL}, content_type="application/json"
    )

    response = owner_client.patch(
        _url(resource),
        {"sourceSql": VALID_SQL},
        content_type="application/json",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["parseStatus"] == "ok"
    assert body["sourceSql"] == VALID_SQL


def test_patch_without_a_facet_returns_404(owner_client, resource):
    response = owner_client.patch(
        _url(resource),
        {"sourceSql": VALID_SQL},
        content_type="application/json",
    )
    assert response.status_code == 404


def test_post_is_rejected_once_the_resource_is_yaml_managed(owner_client, resource):
    """A manual write is rejected once the Resource is YAML-managed."""
    resource.source_kind = SOURCE_YAML
    resource.save(update_fields=["source_kind"])

    response = owner_client.post(
        _url(resource),
        {"sourceSql": VALID_SQL},
        content_type="application/json",
    )

    assert response.status_code == 403
    assert not DatabaseSchema.objects.filter(pk=resource.pk).exists()


def test_patch_is_rejected_once_the_resource_is_yaml_managed(owner_client, resource):
    """A previously-attached facet is frozen: existing data survives the transition, but a manual
    write to it is rejected."""
    owner_client.post(
        _url(resource), {"sourceSql": VALID_SQL}, content_type="application/json"
    )

    resource.source_kind = SOURCE_YAML
    resource.save(update_fields=["source_kind"])

    response = owner_client.patch(
        _url(resource),
        {"sourceSql": "CREATE TABLE other (id uuid PRIMARY KEY);"},
        content_type="application/json",
    )

    assert response.status_code == 403
    facet = DatabaseSchema.objects.get(pk=resource.pk)
    assert facet.source_sql == VALID_SQL


def test_get_is_unaffected_by_yaml_managed_rejection(owner_client, resource):
    owner_client.post(
        _url(resource), {"sourceSql": VALID_SQL}, content_type="application/json"
    )
    resource.source_kind = SOURCE_YAML
    resource.save(update_fields=["source_kind"])

    response = owner_client.get(_url(resource))

    assert response.status_code == 200
    assert response.json()["sourceSql"] == VALID_SQL


def test_deleting_the_facet_leaves_the_resources_own_core_and_kind_data_unaffected(
    owner_client,
    resource,
):
    """An entity's core lifecycle is unaffected by its facets — deleting a
    Facet is not exposed through this plugin's own API
    (the CRUD surface is POST/GET/PATCH only), so this exercises the
    guarantee at the model layer: the `DatabaseSchema` row is the referencing
    side of the `OneToOneField(CatalogEntity, ...)`, so deleting it
    cannot cascade back onto the entity or its `ResourceDetails`.
    """
    owner_client.post(
        _url(resource), {"sourceSql": VALID_SQL}, content_type="application/json"
    )
    assert DatabaseSchema.objects.filter(pk=resource.pk).exists()

    DatabaseSchema.objects.get(pk=resource.pk).delete()

    assert not DatabaseSchema.objects.filter(pk=resource.pk).exists()
    resource.refresh_from_db()
    assert resource.name == "primary-db"
    assert get_catalog_entity_model().objects.filter(pk=resource.pk).exists()
    assert ResourceDetails.objects.filter(entity=resource).exists()

    response = owner_client.get(_url(resource))
    assert response.status_code == 404
