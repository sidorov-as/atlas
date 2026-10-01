"""`list_flows`/`get_flow`/`create_flow`/`update_flow`/`delete_flow`
controller tests (`mcp-plugin` spec's Flow-tool requirements). Routes
through the published `FlowService` contract, so a Flow created directly
against it is what these tools should see, and a Flow these tools create is
what `FlowService`/the REST controllers should in turn see.

Write tools additionally need the `flows:write` scope
(`write_scoped_pat_auth_header`) — `pat_auth_header`'s own token is scoped
`flows:read` only, so it doubles as the "insufficiently-scoped token"
fixture for write-tool rejection tests.
"""

import pytest
from atlas_plugin_flows.contracts import FlowIn
from atlas_plugin_flows.extension_points import get_flow_service

pytestmark = pytest.mark.django_db


@pytest.fixture
def flow(system, owner_user):
    return get_flow_service().create(
        body=FlowIn(system=system.ref, name="onboarding"),
        actor=owner_user.actor_details.account,
    )


def test_list_flows_returns_a_flow_created_through_flow_service(
    dmr_client, flow, pat_auth_header
):
    response = dmr_client.get("/api/plugins/atlas.mcp/flows/", **pat_auth_header)

    assert response.status_code == 200
    ids = [entry["id"] for entry in response.json()["page"]["objectList"]]
    assert flow.id in ids


def test_get_flow_returns_full_flow_detail(dmr_client, flow, pat_auth_header):
    response = dmr_client.get(
        f"/api/plugins/atlas.mcp/flows/{flow.id}/", **pat_auth_header
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == flow.id
    assert body["system"] == flow.system.ref
    assert body["name"] == "onboarding"


def test_get_flow_returns_404_for_an_unknown_id(dmr_client, pat_auth_header):
    response = dmr_client.get("/api/plugins/atlas.mcp/flows/999999/", **pat_auth_header)

    assert response.status_code == 404


def test_list_flows_rejects_a_request_with_no_bearer_token(dmr_client, flow):
    response = dmr_client.get("/api/plugins/atlas.mcp/flows/")

    assert response.status_code in (401, 403)


# --- create_flow --------------------------------------------------------


def test_create_flow_rejects_a_read_only_scoped_token(
    dmr_client, system, pat_auth_header
):
    response = dmr_client.post(
        "/api/plugins/atlas.mcp/flows/",
        {"system": system.ref, "name": "onboarding"},
        content_type="application/json",
        **pat_auth_header,
    )

    assert response.status_code == 403


def test_create_flow_rejects_a_write_the_underlying_user_rbac_would_deny(
    dmr_client, system, outsider_write_scoped_pat_auth_header
):
    """Scope-independent: `outsider_account` isn't a member of `system`'s
    owner Group, so `check_flow_write_permission` denies it regardless of
    the token's own `flows:write` scope (`mcp-plugin` spec: "Flow writes
    route through FlowService, applying the same authorization ... as the
    existing Flow REST controllers")."""
    response = dmr_client.post(
        "/api/plugins/atlas.mcp/flows/",
        {"system": system.ref, "name": "onboarding"},
        content_type="application/json",
        **outsider_write_scoped_pat_auth_header,
    )

    assert response.status_code == 403


def test_create_flow_creates_a_flow_through_flow_service(
    dmr_client, system, write_scoped_pat_auth_header
):
    response = dmr_client.post(
        "/api/plugins/atlas.mcp/flows/",
        {"system": system.ref, "name": "onboarding"},
        content_type="application/json",
        **write_scoped_pat_auth_header,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["system"] == system.ref
    assert body["name"] == "onboarding"

    created = get_flow_service().get(body["id"])
    assert created.name == "onboarding"


# --- update_flow ----------------------------------------------------------


def test_update_flow_rejects_a_read_only_scoped_token(
    dmr_client, flow, pat_auth_header
):
    response = dmr_client.patch(
        f"/api/plugins/atlas.mcp/flows/{flow.id}/",
        {"name": "onboarding-v2"},
        content_type="application/json",
        **pat_auth_header,
    )

    assert response.status_code == 403


def test_update_flow_returns_404_for_an_unknown_id(
    dmr_client, write_scoped_pat_auth_header
):
    response = dmr_client.patch(
        "/api/plugins/atlas.mcp/flows/999999/",
        {"name": "onboarding-v2"},
        content_type="application/json",
        **write_scoped_pat_auth_header,
    )

    assert response.status_code == 404


def test_update_flow_applies_a_partial_patch(
    dmr_client, flow, write_scoped_pat_auth_header
):
    response = dmr_client.patch(
        f"/api/plugins/atlas.mcp/flows/{flow.id}/",
        {"description": "Guides a new user through setup"},
        content_type="application/json",
        **write_scoped_pat_auth_header,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["description"] == "Guides a new user through setup"
    # Untouched field survives the partial patch.
    assert body["name"] == flow.name


# --- delete_flow ------------------------------------------------------------


def test_delete_flow_rejects_a_read_only_scoped_token(
    dmr_client, flow, pat_auth_header
):
    response = dmr_client.delete(
        f"/api/plugins/atlas.mcp/flows/{flow.id}/", **pat_auth_header
    )

    assert response.status_code == 403


def test_delete_flow_permanently_deletes_the_flow(
    dmr_client, flow, write_scoped_pat_auth_header
):
    response = dmr_client.delete(
        f"/api/plugins/atlas.mcp/flows/{flow.id}/", **write_scoped_pat_auth_header
    )

    assert response.status_code == 204
    get_response = dmr_client.get(
        f"/api/plugins/atlas.mcp/flows/{flow.id}/", **write_scoped_pat_auth_header
    )
    assert get_response.status_code == 404
