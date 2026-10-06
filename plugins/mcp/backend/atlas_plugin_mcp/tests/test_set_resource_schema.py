"""`set_resource_schema` (`mcp-upload-tools` spec)."""

import pytest
from atlas_plugin_api import SOURCE_YAML, get_catalog_entity_model
from atlas_plugin_database_schema import extension_points
from server.apps.catalog.tests.factories import create_resource

from atlas_plugin_mcp.api.openapi import build_openapi_schema

pytestmark = pytest.mark.django_db

_URL = "/api/plugins/atlas.mcp/resources/schema/"
VALID_SQL = "CREATE TABLE users (id uuid PRIMARY KEY);"


@pytest.fixture
def resource(group):
    return create_resource(name="primary-db", owner=group, type="database")


def _post(dmr_client, header, body, query=""):
    return dmr_client.post(
        f"{_URL}{query}", body, content_type="application/json", **header
    )


def _body(sql=VALID_SQL, **extra):
    return {"resource": "resource:primary-db", "sourceSql": sql, **extra}


def test_valid_ddl_is_saved_and_reports_ok(
    dmr_client, resource, write_scoped_pat_auth_header
):
    response = _post(dmr_client, write_scoped_pat_auth_header, _body())

    assert response.status_code == 200
    assert response.json() == {
        "resource": resource.ref,
        "dialect": "postgresql",
        "parseStatus": "ok",
        "parseError": "",
        "tableCount": 1,
    }
    assert extension_points.current_schema(resource)["sourceSql"] == VALID_SQL


def test_unparseable_sql_is_saved_with_the_reason(
    dmr_client, resource, write_scoped_pat_auth_header
):
    response = _post(dmr_client, write_scoped_pat_auth_header, _body("SELECT 1;"))

    assert response.status_code == 200
    body = response.json()
    assert body["parseStatus"] == "failed"
    assert body["parseError"] == "No CREATE TABLE statement found"
    assert extension_points.current_schema(resource)["sourceSql"] == "SELECT 1;"


def test_dry_run_persists_nothing(dmr_client, resource, write_scoped_pat_auth_header):
    response = _post(dmr_client, write_scoped_pat_auth_header, _body(), "?dryRun=true")

    assert response.status_code == 200
    assert response.json()["dryRun"] is True
    assert response.json()["result"]["parseStatus"] == "ok"
    assert extension_points.current_schema(resource) is None


def test_yaml_managed_resource_is_rejected(
    dmr_client, resource, write_scoped_pat_auth_header
):
    get_catalog_entity_model().objects.filter(pk=resource.pk).update(
        source_kind=SOURCE_YAML
    )

    response = _post(dmr_client, write_scoped_pat_auth_header, _body())

    assert response.status_code == 403
    assert extension_points.current_schema(resource) is None


def test_read_only_scope_is_rejected(dmr_client, resource, pat_auth_header):
    response = _post(dmr_client, pat_auth_header, _body())

    assert response.status_code == 403
    assert extension_points.current_schema(resource) is None


def test_unknown_resource_and_unknown_keys_are_rejected(
    dmr_client, resource, write_scoped_pat_auth_header
):
    missing = _post(
        dmr_client,
        write_scoped_pat_auth_header,
        {"resource": "resource:nope", "sourceSql": VALID_SQL},
    )
    typo = _post(dmr_client, write_scoped_pat_auth_header, _body(sourceSQL="x"))

    assert missing.status_code == 404, missing.json()
    assert typo.status_code in (400, 422)


def test_operation_is_absent_without_the_plugin(monkeypatch):
    monkeypatch.setattr(
        "atlas_plugin_mcp.api.urls.django_apps.is_installed",
        lambda name: name != "atlas_plugin_database_schema",
    )

    paths = set(build_openapi_schema().paths or {})

    assert not any("resources/schema" in path for path in paths)


def test_operation_is_present_with_the_plugin():
    assert any(
        "resources/schema" in path for path in (build_openapi_schema().paths or {})
    )
