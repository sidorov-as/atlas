"""`create_entity`/`update_entity` reject unknown `spec`/`metadata` keys
instead of silently ignoring them (`mcp-plugin` spec: "Entity write
operations reject unknown fields instead of ignoring them")."""

import pytest
from atlas_plugin_api import get_catalog_entity_model
from server.apps.catalog.tests.factories import create_component

from atlas_plugin_mcp.api.strict_keys import check_spec_keys, writable_spec_keys

pytestmark = pytest.mark.django_db

_CATALOG = "/api/plugins/atlas.mcp/catalog/"


@pytest.fixture
def component(group, system):
    return create_component(name="checkout-api", owner=group, system=system)


def _entity_count() -> int:
    return get_catalog_entity_model().objects.count()


def _system_body(group, **spec):
    return {
        "kind": "system",
        "metadata": {"name": "checkout"},
        "spec": {"owner": group.ref, **spec},
    }


def _patch(dmr_client, entity, body, header):
    return dmr_client.patch(
        f"{_CATALOG}{entity.id}/",
        body,
        content_type="application/json",
        **header,
    )


def test_update_rejects_a_misspelled_spec_key_with_a_hint(
    dmr_client, component, write_scoped_pat_auth_header
):
    response = _patch(
        dmr_client,
        component,
        {"spec": {"dependOn": ["resource:db"]}},
        write_scoped_pat_auth_header,
    )

    assert response.status_code == 400
    message = str(response.json())
    assert "dependOn" in message
    assert "dependsOn" in message


def test_update_rejects_an_unknown_spec_key_and_changes_nothing(
    dmr_client, component, write_scoped_pat_auth_header
):
    response = _patch(
        dmr_client,
        component,
        {"metadata": {"title": "Changed"}, "spec": {"nonsense": 1}},
        write_scoped_pat_auth_header,
    )

    assert response.status_code == 400
    component.refresh_from_db()
    assert component.title != "Changed"


def test_update_accepts_valid_camel_case_spec_keys(
    dmr_client, component, write_scoped_pat_auth_header
):
    response = _patch(
        dmr_client,
        component,
        {"spec": {"lifecycle": "experimental"}},
        write_scoped_pat_auth_header,
    )

    assert response.status_code == 200
    assert response.json()["spec"]["lifecycle"] == "experimental"


def test_create_rejects_an_unknown_spec_key_and_creates_nothing(
    dmr_client, group, write_scoped_pat_auth_header
):
    before = _entity_count()

    response = dmr_client.post(
        _CATALOG,
        _system_body(group, nonsense="x"),
        content_type="application/json",
        **write_scoped_pat_auth_header,
    )

    assert response.status_code == 400
    assert "nonsense" in str(response.json())
    assert _entity_count() == before


def test_create_rejects_relationships_with_a_pointer_to_the_tools(
    dmr_client, group, write_scoped_pat_auth_header
):
    before = _entity_count()

    response = dmr_client.post(
        _CATALOG,
        _system_body(
            group,
            relationships=[{"target": "system:other", "label": "Calls"}],
        ),
        content_type="application/json",
        **write_scoped_pat_auth_header,
    )

    assert response.status_code == 400
    assert "create_relationship" in str(response.json())
    assert _entity_count() == before


def test_update_rejects_relationships_with_a_pointer_to_the_tools(
    dmr_client, component, write_scoped_pat_auth_header
):
    response = _patch(
        dmr_client,
        component,
        {"spec": {"relationships": []}},
        write_scoped_pat_auth_header,
    )

    assert response.status_code == 400
    assert "create_relationship" in str(response.json())


def test_create_rejects_an_unknown_metadata_key_and_creates_nothing(
    dmr_client, group, write_scoped_pat_auth_header
):
    before = _entity_count()
    body = _system_body(group)
    body["metadata"]["titel"] = "typo"

    response = dmr_client.post(
        _CATALOG,
        body,
        content_type="application/json",
        **write_scoped_pat_auth_header,
    )

    assert response.status_code in (400, 422)
    assert "titel" in str(response.json())
    assert _entity_count() == before


def test_update_rejects_an_unknown_metadata_key(
    dmr_client, component, write_scoped_pat_auth_header
):
    response = _patch(
        dmr_client,
        component,
        {"metadata": {"titel": "typo"}},
        write_scoped_pat_auth_header,
    )

    assert response.status_code in (400, 422)
    assert "titel" in str(response.json())


def test_writable_keys_exclude_relationships_without_changing_the_schema():
    from atlas_plugin_api import KIND_SYSTEM, registry

    schema = registry.resolve(KIND_SYSTEM).spec_schema

    assert "relationships" in schema.model_fields
    assert "relationships" not in writable_spec_keys(schema)
    check_spec_keys(schema, {"owner": "group:platform"})
