"""`list_relationships`/`create_relationship`/`update_relationship`/
`delete_relationship` controller tests (`mcp-relationship-tools` spec)."""

import pytest
from atlas_plugin_api import get_architecture_relationship_model
from server.apps.catalog.tests.factories import (
    create_api,
    create_component,
)

pytestmark = pytest.mark.django_db

_URL = "/api/plugins/atlas.mcp/relationships/"


@pytest.fixture
def component(group, system):
    return create_component(name="customer-portal", owner=group, system=system)


@pytest.fixture
def gateway(group, system):
    return create_component(name="api-gateway", owner=group, system=system)


@pytest.fixture
def api(group, system):
    return create_api(name="orders-api", owner=group, system=system)


def _body(source, target, **overrides):
    body = {
        "source": source.ref,
        "target": target.ref,
        "label": "Makes API calls to",
        "technology": "REST/HTTPS",
        "interactionKind": "synchronous",
        "tags": ["runtime"],
    }
    body.update(overrides)
    return body


def _post(dmr_client, body, header):
    return dmr_client.post(_URL, body, content_type="application/json", **header)


def _patch(dmr_client, relationship_id, body, header):
    return dmr_client.patch(
        f"{_URL}{relationship_id}/",
        body,
        content_type="application/json",
        **header,
    )


def _model():
    return get_architecture_relationship_model()


def test_create_persists_a_manual_relationship_and_returns_its_id(
    dmr_client, component, gateway, write_scoped_pat_auth_header
):
    response = _post(
        dmr_client,
        _body(component, gateway),
        write_scoped_pat_auth_header,
    )

    assert response.status_code == 201
    body = response.json()
    assert body == {
        "id": body["id"],
        "source": component.ref,
        "sourceKind": "component",
        "target": gateway.ref,
        "targetKind": "component",
        "label": "Makes API calls to",
        "technology": "REST/HTTPS",
        "interactionKind": "synchronous",
        "tags": ["runtime"],
        "origin": "manual",
    }
    assert _model().objects.get(pk=body["id"]).origin == "manual"


def test_partial_update_changes_only_the_given_field(
    dmr_client, component, gateway, write_scoped_pat_auth_header
):
    created = _post(
        dmr_client, _body(component, gateway), write_scoped_pat_auth_header
    ).json()

    response = _patch(
        dmr_client,
        created["id"],
        {"label": "Calls"},
        write_scoped_pat_auth_header,
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated["label"] == "Calls"
    assert updated["technology"] == "REST/HTTPS"
    assert updated["tags"] == ["runtime"]
    assert updated["interactionKind"] == "synchronous"


def test_delete_removes_the_relationship_from_both_listings(
    dmr_client, component, gateway, write_scoped_pat_auth_header
):
    created = _post(
        dmr_client, _body(component, gateway), write_scoped_pat_auth_header
    ).json()

    response = dmr_client.delete(
        f"{_URL}{created['id']}/", **write_scoped_pat_auth_header
    )

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]
    for entity in (component, gateway):
        listed = dmr_client.get(
            _URL, {"entity": entity.ref}, **write_scoped_pat_auth_header
        )
        assert listed.json() == []


def test_list_returns_both_directions_with_origin(
    dmr_client, component, gateway, api, pat_auth_header
):
    model = _model()
    outgoing = model.objects.create(
        source=component, target=gateway, label="Calls", origin="manual"
    )
    incoming = model.objects.create(
        source=api, target=component, label="Declared", origin="yaml"
    )
    model.objects.create(source=api, target=gateway, label="Unrelated")

    response = dmr_client.get(_URL, {"entity": component.ref}, **pat_auth_header)

    assert response.status_code == 200
    rows = response.json()
    assert [(r["id"], r["origin"]) for r in rows] == [
        (outgoing.id, "manual"),
        (incoming.id, "yaml"),
    ]
    assert rows[1]["source"] == api.ref
    assert rows[1]["target"] == component.ref


def test_list_unknown_entity_is_rejected(dmr_client, pat_auth_header):
    response = dmr_client.get(_URL, {"entity": "component:missing"}, **pat_auth_header)

    assert response.status_code == 400


def test_update_and_delete_reject_yaml_origin_relationships(
    dmr_client, component, gateway, write_scoped_pat_auth_header
):
    relationship = _model().objects.create(
        source=component, target=gateway, label="Declared", origin="yaml"
    )

    patched = _patch(
        dmr_client,
        relationship.id,
        {"label": "Edited"},
        write_scoped_pat_auth_header,
    )
    deleted = dmr_client.delete(
        f"{_URL}{relationship.id}/", **write_scoped_pat_auth_header
    )

    assert patched.status_code == 403
    assert deleted.status_code == 403
    assert "ingestion" in str(patched.json())
    relationship.refresh_from_db()
    assert relationship.label == "Declared"


def test_create_rejects_a_source_of_a_non_writable_kind(
    dmr_client, group, gateway, write_scoped_pat_auth_header
):
    response = _post(dmr_client, _body(group, gateway), write_scoped_pat_auth_header)

    assert response.status_code == 400
    assert not _model().objects.exists()


def test_create_rejects_an_unresolvable_target(
    dmr_client, component, write_scoped_pat_auth_header
):
    body = _body(component, component)
    body["target"] = "component:missing"

    response = _post(dmr_client, body, write_scoped_pat_auth_header)

    assert response.status_code == 400
    assert "component:missing" in str(response.json())
    assert not _model().objects.exists()


def test_create_without_write_permission_on_the_source_is_rejected(
    dmr_client, component, gateway, outsider_write_scoped_pat_auth_header
):
    response = _post(
        dmr_client,
        _body(component, gateway),
        outsider_write_scoped_pat_auth_header,
    )

    assert response.status_code == 403
    assert not _model().objects.exists()


def test_update_and_delete_unknown_id_are_404(dmr_client, write_scoped_pat_auth_header):
    patched = _patch(dmr_client, 999999, {"label": "x"}, write_scoped_pat_auth_header)
    deleted = dmr_client.delete(f"{_URL}999999/", **write_scoped_pat_auth_header)

    assert patched.status_code == 404
    assert deleted.status_code == 404


def test_create_rejects_an_unknown_field(
    dmr_client, component, gateway, write_scoped_pat_auth_header
):
    response = _post(
        dmr_client,
        _body(component, gateway, lable="typo"),
        write_scoped_pat_auth_header,
    )

    assert response.status_code in (400, 422)
    assert not _model().objects.exists()


def test_write_tools_reject_a_read_only_scoped_token(
    dmr_client, component, gateway, pat_auth_header
):
    relationship = _model().objects.create(
        source=component, target=gateway, label="Calls"
    )

    created = _post(dmr_client, _body(component, gateway), pat_auth_header)
    patched = _patch(dmr_client, relationship.id, {"label": "x"}, pat_auth_header)
    deleted = dmr_client.delete(f"{_URL}{relationship.id}/", **pat_auth_header)

    assert created.status_code == 403
    assert patched.status_code == 403
    assert deleted.status_code == 403
    assert _model().objects.count() == 1


def test_every_tool_rejects_a_request_with_no_token(dmr_client, component, gateway):
    assert dmr_client.get(_URL, {"entity": component.ref}).status_code in (
        401,
        403,
    )
    assert _post(dmr_client, _body(component, gateway), {}).status_code in (
        401,
        403,
    )
