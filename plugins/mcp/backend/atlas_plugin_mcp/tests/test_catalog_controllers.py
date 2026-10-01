"""`search_catalog`/`get_entity`/`create_entity`/`update_entity`/
`remove_entity`/`purge_entity` controller tests (`mcp-plugin` spec).

Every request needs a valid Atlas Personal Access Token — no session, even
an authenticated one, satisfies `PATBearerAuth` (`mcp-plugin` spec: "Every
MCP API request is authenticated by an Atlas Personal Access Token"). Write
tools additionally need the `catalog:write` scope
(`write_scoped_pat_auth_header`) — `pat_auth_header`'s own token is scoped
`catalog:read` only, so it doubles as the "insufficiently-scoped token"
fixture for write-tool rejection tests.
"""

from uuid import uuid4

import pytest
from atlas_plugin_api import (
    KIND_SYSTEM,
    get_audit_record_model,
    get_entity_service,
    registry,
)
from atlas_plugin_api.schemas import MetadataIn
from server.apps.catalog.tests.factories import create_purge_grant

pytestmark = pytest.mark.django_db


def test_search_catalog_rejects_a_request_with_no_bearer_token(dmr_client, system):
    response = dmr_client.get("/api/plugins/atlas.mcp/catalog/search/")

    assert response.status_code in (401, 403)


def test_search_catalog_rejects_an_invalid_token(dmr_client, system):
    response = dmr_client.get(
        "/api/plugins/atlas.mcp/catalog/search/",
        HTTP_AUTHORIZATION="Bearer atlaspat_not-a-real-token",
    )

    assert response.status_code in (401, 403)


def test_search_catalog_returns_a_matching_entity_for_a_valid_token(
    dmr_client, system, pat_auth_header
):
    response = dmr_client.get(
        "/api/plugins/atlas.mcp/catalog/search/",
        {"q": "user-management"},
        **pat_auth_header,
    )

    assert response.status_code == 200
    body = response.json()
    refs = [entry["ref"] for entry in body["page"]["objectList"]]
    assert system.ref in refs


def test_search_catalog_filters_by_kind(dmr_client, system, pat_auth_header):
    response = dmr_client.get(
        "/api/plugins/atlas.mcp/catalog/search/",
        {"kind": "system"},
        **pat_auth_header,
    )

    assert response.status_code == 200
    kinds = {entry["kind"] for entry in response.json()["page"]["objectList"]}
    assert kinds <= {"system"}


def test_get_entity_returns_full_metadata_and_spec_for_a_valid_token(
    dmr_client, system, pat_auth_header
):
    response = dmr_client.get(
        f"/api/plugins/atlas.mcp/catalog/{system.id}/", **pat_auth_header
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(system.id)
    assert body["kind"] == "system"
    assert body["metadata"]["name"] == "user-management"
    assert body["unavailable"] is False


def test_get_entity_rejects_a_request_with_no_bearer_token(dmr_client, system):
    response = dmr_client.get(f"/api/plugins/atlas.mcp/catalog/{system.id}/")

    assert response.status_code in (401, 403)


def test_get_entity_returns_404_for_an_unknown_id(dmr_client, pat_auth_header):
    response = dmr_client.get(
        f"/api/plugins/atlas.mcp/catalog/{uuid4()}/", **pat_auth_header
    )

    assert response.status_code == 404


# --- create_entity ----------------------------------------------------------


def _system_body(name: str, owner_ref: str) -> dict:
    return {
        "kind": "system",
        "metadata": {"name": name},
        "spec": {"owner": owner_ref},
    }


def test_create_entity_rejects_a_request_with_no_bearer_token(dmr_client, group):
    response = dmr_client.post(
        "/api/plugins/atlas.mcp/catalog/",
        _system_body("checkout", group.ref),
        content_type="application/json",
    )

    assert response.status_code in (401, 403)


def test_create_entity_rejects_a_read_only_scoped_token(
    dmr_client, group, pat_auth_header
):
    response = dmr_client.post(
        "/api/plugins/atlas.mcp/catalog/",
        _system_body("checkout", group.ref),
        content_type="application/json",
        **pat_auth_header,
    )

    assert response.status_code == 403


def test_create_entity_rejects_a_kind_the_rest_api_does_not_expose_for_writing(
    dmr_client, write_scoped_pat_auth_header
):
    response = dmr_client.post(
        "/api/plugins/atlas.mcp/catalog/",
        {"kind": "group", "metadata": {"name": "new-team"}, "spec": {"type": "team"}},
        content_type="application/json",
        **write_scoped_pat_auth_header,
    )

    assert response.status_code == 400


def test_create_entity_rejects_a_write_the_underlying_user_rbac_would_deny(
    dmr_client, group, outsider_write_scoped_pat_auth_header
):
    """Scope-independent: `outsider_account` has every scope a write tool
    checks, but isn't a member of `group`, so `EntityWritePermission.
    check_create` still denies it — same as it would for any other caller
    (`mcp-plugin` spec: "A write rejected by RBAC through the web UI is also
    rejected through MCP")."""
    response = dmr_client.post(
        "/api/plugins/atlas.mcp/catalog/",
        _system_body("checkout", group.ref),
        content_type="application/json",
        **outsider_write_scoped_pat_auth_header,
    )

    assert response.status_code == 403


def test_create_entity_creates_a_system_through_entity_service(
    dmr_client, group, write_scoped_pat_auth_header
):
    response = dmr_client.post(
        "/api/plugins/atlas.mcp/catalog/",
        _system_body("checkout", group.ref),
        content_type="application/json",
        **write_scoped_pat_auth_header,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["kind"] == "system"
    assert body["metadata"]["name"] == "checkout"
    assert body["spec"]["owner"] == group.ref
    assert body["unavailable"] is False


def test_create_entity_produces_an_audit_record_matching_a_direct_entity_service_create(
    dmr_client, group, owner_account, write_scoped_pat_auth_header
):
    """`mcp-plugin` spec: "the resulting CatalogEntity and its audit record
    are indistinguishable in shape from one created through the existing
    REST API, other than the recorded actor" — here the actor is
    deliberately the *same* user on both sides (the PAT's owner), so the
    audit records should match in full, `actor` included.
    """
    system_spec_schema = registry.resolve(KIND_SYSTEM).spec_schema
    direct_entity = get_entity_service().create(
        kind_id="system",
        owner_ref=group.ref,
        metadata=MetadataIn(name="checkout-direct"),
        spec=system_spec_schema(owner=group.ref),
        actor=owner_account,
    )
    response = dmr_client.post(
        "/api/plugins/atlas.mcp/catalog/",
        _system_body("checkout-mcp", group.ref),
        content_type="application/json",
        **write_scoped_pat_auth_header,
    )
    assert response.status_code == 201
    mcp_entity_id = response.json()["id"]

    audit_model = get_audit_record_model()
    direct_record = audit_model.objects.get(
        entity_id=direct_entity.id, action=audit_model.ACTION_CREATE
    )
    mcp_record = audit_model.objects.get(
        entity_id=mcp_entity_id, action=audit_model.ACTION_CREATE
    )

    assert set(direct_record.diff) == set(mcp_record.diff)
    assert set(direct_record.diff["spec"]) == set(mcp_record.diff["spec"])
    assert direct_record.actor_id == mcp_record.actor_id == owner_account.id


# --- update_entity -----------------------------------------------------------


def test_update_entity_rejects_a_read_only_scoped_token(
    dmr_client, system, pat_auth_header
):
    response = dmr_client.patch(
        f"/api/plugins/atlas.mcp/catalog/{system.id}/",
        {"metadata": {"title": "Checkout"}},
        content_type="application/json",
        **pat_auth_header,
    )

    assert response.status_code == 403


def test_update_entity_returns_404_for_an_unknown_id(
    dmr_client, write_scoped_pat_auth_header
):
    response = dmr_client.patch(
        f"/api/plugins/atlas.mcp/catalog/{uuid4()}/",
        {"metadata": {"title": "Checkout"}},
        content_type="application/json",
        **write_scoped_pat_auth_header,
    )

    assert response.status_code == 404


def test_update_entity_applies_a_partial_metadata_patch(
    dmr_client, system, write_scoped_pat_auth_header
):
    response = dmr_client.patch(
        f"/api/plugins/atlas.mcp/catalog/{system.id}/",
        {"metadata": {"title": "Checkout System"}},
        content_type="application/json",
        **write_scoped_pat_auth_header,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["metadata"]["title"] == "Checkout System"
    # Untouched field survives the partial patch, matching the REST PATCH
    # endpoints' own semantics.
    assert body["metadata"]["name"] == system.name


# --- remove_entity / purge_entity --------------------------------------------


def test_remove_entity_flips_status_to_removed(
    dmr_client, system, write_scoped_pat_auth_header
):
    response = dmr_client.post(
        f"/api/plugins/atlas.mcp/catalog/{system.id}/remove/",
        **write_scoped_pat_auth_header,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "removed"


def test_purge_entity_rejects_a_read_only_scoped_token(
    dmr_client, system, pat_auth_header
):
    response = dmr_client.post(
        f"/api/plugins/atlas.mcp/catalog/{system.id}/purge/",
        **pat_auth_header,
    )

    assert response.status_code == 403


def test_purge_entity_permanently_deletes_a_removed_entity(
    dmr_client, group, system, owner_user, write_scoped_pat_auth_header
):
    # Purge requires a Purge Grant, not mere ownership/membership
    # (`EntityWritePermission.check_purge`) — Remove alone doesn't need one.
    create_purge_grant(group=group, grantee=owner_user.actor_details.account)

    remove_response = dmr_client.post(
        f"/api/plugins/atlas.mcp/catalog/{system.id}/remove/",
        **write_scoped_pat_auth_header,
    )
    assert remove_response.status_code == 200

    purge_response = dmr_client.post(
        f"/api/plugins/atlas.mcp/catalog/{system.id}/purge/",
        **write_scoped_pat_auth_header,
    )

    assert purge_response.status_code == 204
    get_response = dmr_client.get(
        f"/api/plugins/atlas.mcp/catalog/{system.id}/",
        **write_scoped_pat_auth_header,
    )
    assert get_response.status_code == 404
