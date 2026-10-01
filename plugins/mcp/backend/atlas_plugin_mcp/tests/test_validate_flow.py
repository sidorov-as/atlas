"""`validate_flow` reports every flow-rule violation without saving
(`mcp-write-preview` spec)."""

import pytest
from atlas_plugin_flows.extension_points import get_flow_service
from server.apps.catalog.tests.factories import create_component

from atlas_plugin_mcp.api.openapi import build_openapi_schema

pytestmark = pytest.mark.django_db

_URL = "/api/plugins/atlas.mcp/flows/validate/"


@pytest.fixture
def component(group, system):
    return create_component(name="checkout-api", owner=group, system=system)


def _step(step_id, **extra):
    return {"id": step_id, "title": step_id, **extra}


def _validate(dmr_client, header, body):
    return dmr_client.post(_URL, body, content_type="application/json", **header)


def test_valid_flow_is_reported_valid_and_nothing_is_saved(
    dmr_client, system, pat_auth_header
):
    response = _validate(
        dmr_client,
        pat_auth_header,
        {
            "system": system.ref,
            "name": "checkout",
            "steps": [_step("a", next_step={"id": "b"}), _step("b")],
        },
    )

    assert response.status_code == 200
    assert response.json() == {"valid": True, "violations": []}
    assert get_flow_service().list().count() == 0


def test_several_violations_are_reported_together(dmr_client, system, pat_auth_header):
    response = _validate(
        dmr_client,
        pat_auth_header,
        {
            "system": system.ref,
            "name": "checkout",
            "steps": [
                _step("a", next_step={"id": "missing"}),
                _step("a"),
                {"id": "c", "entity_ref": "component:nowhere"},
            ],
        },
    )

    body = response.json()
    assert body["valid"] is False
    text = " | ".join(body["violations"])
    assert "Duplicate step id: 'a'" in text
    assert "transitions to unknown step id 'missing'" in text
    assert "unresolvable entity_ref" in text
    assert len(body["violations"]) >= 3


def test_cycle_is_reported_with_the_step_ids(dmr_client, system, pat_auth_header):
    response = _validate(
        dmr_client,
        pat_auth_header,
        {
            "system": system.ref,
            "name": "loop",
            "steps": [
                _step("a", next_step={"id": "b"}),
                _step("b", next_step={"id": "a"}),
            ],
        },
    )

    violations = response.json()["violations"]
    assert len(violations) == 1
    assert "cycle" in violations[0]
    assert "'a'" in violations[0] or "'b'" in violations[0]


def test_step_with_two_reference_fields_is_reported(
    dmr_client, system, component, pat_auth_header
):
    response = _validate(
        dmr_client,
        pat_auth_header,
        {
            "system": system.ref,
            "name": "mixed",
            "steps": [
                {
                    "id": "a",
                    "entity_ref": component.ref,
                    "external_label": "Stripe",
                }
            ],
        },
    )

    assert any("cannot have more than one" in v for v in response.json()["violations"])


def test_unknown_system_and_oversized_description_are_reported(
    dmr_client, pat_auth_header
):
    response = _validate(
        dmr_client,
        pat_auth_header,
        {"system": "system:nowhere", "name": "x", "description": "d" * 5000},
    )

    text = " | ".join(response.json()["violations"])
    assert "system" in text
    assert "description" in text


def test_updating_a_flow_does_not_collide_with_its_own_name(
    dmr_client, system, write_scoped_pat_auth_header
):
    created = dmr_client.post(
        "/api/plugins/atlas.mcp/flows/",
        {"system": system.ref, "name": "onboarding"},
        content_type="application/json",
        **write_scoped_pat_auth_header,
    ).json()
    body = {"system": system.ref, "name": "onboarding"}

    as_new = _validate(dmr_client, write_scoped_pat_auth_header, body).json()
    as_update = _validate(
        dmr_client, write_scoped_pat_auth_header, {**body, "flowId": created["id"]}
    ).json()

    assert any("already exists" in v for v in as_new["violations"])
    assert as_update["valid"] is True


def test_unknown_flow_id_is_404(dmr_client, system, pat_auth_header):
    response = _validate(
        dmr_client,
        pat_auth_header,
        {"system": system.ref, "name": "x", "flowId": 999999},
    )

    assert response.status_code == 404, response.json()


def test_flows_read_scope_is_required(dmr_client, system, owner_account):
    import atlas_plugin_api.pat as pat_module
    from atlas_plugin_api.pat import ResolvedPersonalAccessToken, bind_pat_validator

    previous = pat_module._pat_validator
    bind_pat_validator(
        lambda raw: (
            ResolvedPersonalAccessToken(
                user=owner_account, scopes=frozenset({"catalog:read"})
            )
            if raw == "atlaspat_no-flows-scope"
            else None
        )
    )
    try:
        response = _validate(
            dmr_client,
            {"HTTP_AUTHORIZATION": "Bearer atlaspat_no-flows-scope"},
            {"system": system.ref, "name": "x"},
        )
    finally:
        pat_module._pat_validator = previous

    assert response.status_code == 403


def test_unauthenticated_request_is_rejected(dmr_client, system):
    response = _validate(dmr_client, {}, {"system": system.ref, "name": "x"})

    assert response.status_code in (401, 403)


def test_operation_is_absent_without_atlas_flows(monkeypatch):
    monkeypatch.setattr(
        "atlas_plugin_mcp.api.urls.django_apps.is_installed", lambda _name: False
    )

    paths = set(build_openapi_schema().paths or {})

    assert not any("flows/validate" in path for path in paths)
