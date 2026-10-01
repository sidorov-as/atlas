"""`dryRun` on the authoring writes persists nothing and reports the
result (`mcp-write-preview` spec)."""

import pytest
from atlas_plugin_api import get_audit_record_model, get_catalog_entity_model
from server.apps.catalog.tests.factories import create_component

pytestmark = pytest.mark.django_db

_CATALOG = "/api/plugins/atlas.mcp/catalog/"


def _counts():
    return (
        get_catalog_entity_model().objects.count(),
        get_audit_record_model().objects.count(),
    )


@pytest.fixture
def component(group, system):
    return create_component(name="checkout-api", owner=group, system=system)


def _post(dmr_client, body, header, query=""):
    return dmr_client.post(
        f"{_CATALOG}{query}", body, content_type="application/json", **header
    )


def _patch(dmr_client, entity, body, header, query=""):
    return dmr_client.patch(
        f"{_CATALOG}{entity.id}/{query}",
        body,
        content_type="application/json",
        **header,
    )


def _system_body(group):
    return {
        "kind": "system",
        "metadata": {"name": "checkout"},
        "spec": {"owner": group.ref},
    }


def test_create_dry_run_persists_nothing(
    dmr_client, group, write_scoped_pat_auth_header
):
    before = _counts()

    response = _post(
        dmr_client, _system_body(group), write_scoped_pat_auth_header, "?dryRun=true"
    )

    assert response.status_code == 201
    body = response.json()
    assert body["dryRun"] is True
    assert body["result"]["id"] is None
    assert body["result"]["ref"] == "system:checkout"
    assert any(c["field"] == "ref" and c["before"] is None for c in body["changes"])
    assert _counts() == before


def test_update_dry_run_reports_before_and_after(
    dmr_client, component, write_scoped_pat_auth_header
):
    before = _counts()

    response = _patch(
        dmr_client,
        component,
        {"spec": {"lifecycle": "deprecated"}},
        write_scoped_pat_auth_header,
        "?dryRun=true",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["dryRun"] is True
    changes = {c["field"]: c for c in body["changes"]}
    assert changes["spec.lifecycle"]["after"] == "deprecated"
    assert changes["spec.lifecycle"]["before"] != "deprecated"
    component.refresh_from_db()
    assert component.component_details.lifecycle != "deprecated"
    assert _counts() == before


def test_dry_run_reports_the_same_error_as_a_real_write(
    dmr_client, group, write_scoped_pat_auth_header
):
    body = _system_body(group)
    body["spec"]["owner"] = "group:missing"

    real = _post(dmr_client, body, write_scoped_pat_auth_header)
    preview = _post(dmr_client, body, write_scoped_pat_auth_header, "?dryRun=true")

    assert real.status_code >= 400
    assert preview.status_code == real.status_code
    assert preview.json() == real.json()


def test_dry_run_rejected_by_rbac_like_a_real_write(
    dmr_client, group, outsider_write_scoped_pat_auth_header
):
    preview = _post(
        dmr_client,
        _system_body(group),
        outsider_write_scoped_pat_auth_header,
        "?dryRun=true",
    )

    assert preview.status_code == 403


def test_dry_run_still_requires_the_write_scope(dmr_client, group, pat_auth_header):
    response = _post(dmr_client, _system_body(group), pat_auth_header, "?dryRun=true")

    assert response.status_code == 403


def test_real_write_response_shape_is_unchanged(
    dmr_client, group, write_scoped_pat_auth_header
):
    response = _post(dmr_client, _system_body(group), write_scoped_pat_auth_header)

    assert response.status_code == 201
    assert "dryRun" not in response.json()
    assert response.json()["id"]


# --- relationships ---------------------------------------------------------

_REL = "/api/plugins/atlas.mcp/relationships/"


@pytest.fixture
def gateway(group, system):
    return create_component(name="gateway", owner=group, system=system)


def _rel_count() -> int:
    from atlas_plugin_api import get_architecture_relationship_model

    return get_architecture_relationship_model().objects.count()


def _rel_body(source, target):
    return {"source": source.ref, "target": target.ref, "label": "calls"}


def test_create_relationship_dry_run_persists_nothing(
    dmr_client, component, gateway, write_scoped_pat_auth_header
):
    response = dmr_client.post(
        f"{_REL}?dryRun=true",
        _rel_body(component, gateway),
        content_type="application/json",
        **write_scoped_pat_auth_header,
    )

    assert response.status_code == 201
    assert response.json()["dryRun"] is True
    assert response.json()["result"]["id"] is None
    assert _rel_count() == 0


def _create_rel(dmr_client, component, gateway, header):
    return dmr_client.post(
        _REL,
        _rel_body(component, gateway),
        content_type="application/json",
        **header,
    ).json()


def test_update_relationship_dry_run_reports_before_and_after(
    dmr_client, component, gateway, write_scoped_pat_auth_header
):
    created = _create_rel(dmr_client, component, gateway, write_scoped_pat_auth_header)

    response = dmr_client.patch(
        f"{_REL}{created['id']}/?dryRun=true",
        {"label": "publishes to"},
        content_type="application/json",
        **write_scoped_pat_auth_header,
    )

    assert response.status_code == 200
    changes = {c["field"]: c for c in response.json()["changes"]}
    assert changes["label"] == {
        "field": "label",
        "before": "calls",
        "after": "publishes to",
    }
    listed = dmr_client.get(
        _REL, data={"entity": component.ref}, **write_scoped_pat_auth_header
    ).json()
    assert listed[0]["label"] == "calls"


def test_delete_relationship_dry_run_deletes_nothing(
    dmr_client, component, gateway, write_scoped_pat_auth_header
):
    created = _create_rel(dmr_client, component, gateway, write_scoped_pat_auth_header)

    response = dmr_client.delete(
        f"{_REL}{created['id']}/?dryRun=true", **write_scoped_pat_auth_header
    )

    assert response.status_code == 200
    body = response.json()
    assert body["dryRun"] is True
    assert body["result"] is None
    assert any(c["field"] == "label" and c["after"] is None for c in body["changes"])
    assert _rel_count() == 1


def test_relationship_dry_run_requires_the_write_scope(
    dmr_client, component, gateway, pat_auth_header
):
    response = dmr_client.post(
        f"{_REL}?dryRun=true",
        _rel_body(component, gateway),
        content_type="application/json",
        **pat_auth_header,
    )

    assert response.status_code == 403


def test_relationship_dry_run_reports_the_same_error_as_a_real_write(
    dmr_client, component, write_scoped_pat_auth_header
):
    body = {"source": component.ref, "target": "component:missing", "label": "x"}

    real = dmr_client.post(
        _REL, body, content_type="application/json", **write_scoped_pat_auth_header
    )
    preview = dmr_client.post(
        f"{_REL}?dryRun=true",
        body,
        content_type="application/json",
        **write_scoped_pat_auth_header,
    )

    assert real.status_code == 400
    assert preview.status_code == 400
    assert preview.json() == real.json()


# --- flows ---------------------------------------------------------------

_FLOWS = "/api/plugins/atlas.mcp/flows/"


def _flow_count() -> int:
    from atlas_plugin_flows.extension_points import get_flow_service

    return get_flow_service().list().count()


def test_create_flow_dry_run_persists_nothing(
    dmr_client, system, write_scoped_pat_auth_header
):
    response = dmr_client.post(
        f"{_FLOWS}?dryRun=true",
        {"system": system.ref, "name": "onboarding"},
        content_type="application/json",
        **write_scoped_pat_auth_header,
    )

    assert response.status_code == 201
    assert response.json()["dryRun"] is True
    assert response.json()["result"]["id"] is None
    assert response.json()["result"]["name"] == "onboarding"
    assert _flow_count() == 0


def test_update_flow_dry_run_reports_before_and_after(
    dmr_client, system, write_scoped_pat_auth_header
):
    created = dmr_client.post(
        _FLOWS,
        {"system": system.ref, "name": "onboarding"},
        content_type="application/json",
        **write_scoped_pat_auth_header,
    ).json()

    response = dmr_client.patch(
        f"{_FLOWS}{created['id']}/?dryRun=true",
        {"name": "onboarding-v2"},
        content_type="application/json",
        **write_scoped_pat_auth_header,
    )

    assert response.status_code == 200
    assert response.json()["changes"] == [
        {"field": "name", "before": "onboarding", "after": "onboarding-v2"}
    ]
    stored = dmr_client.get(
        f"{_FLOWS}{created['id']}/", **write_scoped_pat_auth_header
    ).json()
    assert stored["name"] == "onboarding"


def test_flow_dry_run_requires_the_write_scope(dmr_client, system, pat_auth_header):
    response = dmr_client.post(
        f"{_FLOWS}?dryRun=true",
        {"system": system.ref, "name": "onboarding"},
        content_type="application/json",
        **pat_auth_header,
    )

    assert response.status_code == 403


def test_flow_dry_run_reports_the_same_error_as_a_real_write(
    dmr_client, write_scoped_pat_auth_header
):
    body = {"system": "system:missing", "name": "onboarding"}

    real = dmr_client.post(
        _FLOWS, body, content_type="application/json", **write_scoped_pat_auth_header
    )
    preview = dmr_client.post(
        f"{_FLOWS}?dryRun=true",
        body,
        content_type="application/json",
        **write_scoped_pat_auth_header,
    )

    assert real.status_code >= 400
    assert preview.status_code == real.status_code
    assert preview.json() == real.json()


# --- spec URL side effect ----------------------------------------------------


def test_dry_run_does_not_fetch_a_spec_url_and_warns(
    dmr_client, group, system, write_scoped_pat_auth_header, monkeypatch
):
    def _forbidden(*args, **kwargs):
        raise AssertionError("dry-run made an outbound request")

    monkeypatch.setattr("atlas_plugin_apis.spec_fetch.safe_request", _forbidden)
    before = _counts()

    response = _post(
        dmr_client,
        {
            "kind": "api",
            "metadata": {"name": "payments-api"},
            "spec": {
                "type": "openapi",
                "owner": group.ref,
                "system": system.ref,
                "specSource": "url",
                "specUrl": "https://example.com/openapi.yaml",
            },
        },
        write_scoped_pat_auth_header,
        "?dryRun=true",
    )

    assert response.status_code == 201
    warnings = response.json()["warnings"]
    assert len(warnings) == 1
    assert "https://example.com/openapi.yaml" in warnings[0]
    assert _counts() == before
