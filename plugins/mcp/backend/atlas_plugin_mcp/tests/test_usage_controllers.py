"""`link_endpoint_consumers` / `unlink_endpoint_consumers` /
`link_operation_participants` / `unlink_operation_participants`
(`mcp-api-usage-tools` spec). Goes through the real controllers with a stub PAT
validator; rows are built with the `apis` models directly, as the other
`atlas.apis`-backed tests here do."""

import atlas_plugin_api.pat as pat_module
import pytest
from atlas_plugin_api.pat import ResolvedPersonalAccessToken, bind_pat_validator
from atlas_plugin_apis.extension_points import MAX_USAGE_BATCH_SIZE
from atlas_plugin_apis.models import (
    ApiEndpoint,
    ApiOperation,
    ServiceEndpointUsage,
    ServiceOperationUsage,
)
from server.apps.catalog.tests.factories import create_api, create_component

from atlas_plugin_mcp.api.openapi import build_openapi_schema

pytestmark = pytest.mark.django_db

BASE = "/api/plugins/atlas.mcp"
ENDPOINT_LINK = f"{BASE}/endpoints/consumers/link/"
ENDPOINT_UNLINK = f"{BASE}/endpoints/consumers/unlink/"
OPERATION_LINK = f"{BASE}/operations/participants/link/"
OPERATION_UNLINK = f"{BASE}/operations/participants/unlink/"


def _header(account, scopes, token):
    def _validator(raw_token):
        if raw_token != token:
            return None
        return ResolvedPersonalAccessToken(user=account, scopes=frozenset(scopes))

    bind_pat_validator(_validator)
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


@pytest.fixture
def apis_header(owner_user):
    previous = pat_module._pat_validator
    yield _header(
        owner_user.actor_details.account,
        {"catalog:read", "apis:write"},
        "atlaspat_apis-write",
    )
    pat_module._pat_validator = previous


@pytest.fixture
def catalog_write_only_header(owner_user):
    previous = pat_module._pat_validator
    yield _header(
        owner_user.actor_details.account,
        {"catalog:read", "catalog:write"},
        "atlaspat_catalog-write",
    )
    pat_module._pat_validator = previous


@pytest.fixture
def outsider_apis_header(outsider_account):
    previous = pat_module._pat_validator
    yield _header(outsider_account, {"apis:write"}, "atlaspat_outsider-apis")
    pat_module._pat_validator = previous


@pytest.fixture
def api(group, system):
    return create_api(name="invoices-api", owner=group, system=system)


@pytest.fixture
def service(group, system):
    return create_component(name="booking-web", owner=group, system=system)


@pytest.fixture
def endpoint(api):
    return ApiEndpoint.objects.create(api=api, method="GET", path="/v1/invoices")


@pytest.fixture
def operation(api):
    return ApiOperation.objects.create(
        api=api,
        channel_address="orders.created",
        direction="send",
        operation_key="orders.created:send",
    )


def _post(client, url, body, header, dry_run=False):
    suffix = "?dryRun=true" if dry_run else ""
    return client.post(f"{url}{suffix}", body, **header)


def _statuses(response):
    return [item["status"] for item in response.json()["items"]]


def test_link_endpoints_by_key_records_manual_mcp_and_the_pat_owner(
    dmr_client, apis_header, service, api, endpoint, owner_user
):
    body = {
        "service": service.ref,
        "items": [{"api": api.ref, "method": "GET", "path": "/v1/invoices"}],
    }

    response = _post(dmr_client, ENDPOINT_LINK, body, apis_header)

    assert response.status_code == 200, response.content
    payload = response.json()
    assert payload["counts"] == {"created": 1}
    assert payload["items"][0]["apiRelationCreated"] is True
    assert payload["items"][0]["endpointId"] == str(endpoint.id)
    usage = ServiceEndpointUsage.objects.get(endpoint=endpoint, service=service)
    assert (usage.origin, usage.source) == ("manual", "mcp")
    assert usage.created_by == owner_user.actor_details.account


def test_a_link_made_over_rest_is_unchanged_over_mcp(
    dmr_client, apis_header, service, endpoint
):
    ServiceEndpointUsage.objects.create(endpoint=endpoint, service=service)

    response = _post(
        dmr_client,
        ENDPOINT_LINK,
        {"service": service.ref, "items": [{"endpointId": str(endpoint.id)}]},
        apis_header,
    )

    assert _statuses(response) == ["unchanged"]
    assert ServiceEndpointUsage.objects.get().source == "ui"


def test_endpoint_dry_run_previews_and_saves_nothing(
    dmr_client, apis_header, service, endpoint
):
    response = _post(
        dmr_client,
        ENDPOINT_LINK,
        {"service": service.ref, "items": [{"endpointId": str(endpoint.id)}]},
        apis_header,
        dry_run=True,
    )

    payload = response.json()
    assert payload["dryRun"] is True
    assert _statuses(response) == ["created"]
    assert payload["items"][0]["apiRelationCreated"] is True
    assert not ServiceEndpointUsage.objects.exists()
    assert not service.component_details.consumes_apis.exists()


def test_unlink_endpoints_removes_the_link(dmr_client, apis_header, service, endpoint):
    ServiceEndpointUsage.objects.create(endpoint=endpoint, service=service)

    response = _post(
        dmr_client,
        ENDPOINT_UNLINK,
        {"service": service.ref, "items": [{"endpointId": str(endpoint.id)}]},
        apis_header,
    )

    assert _statuses(response) == ["removed"]
    assert not ServiceEndpointUsage.objects.exists()


def test_operation_links_by_key_with_both_roles_then_unlink_one(
    dmr_client, apis_header, service, api, operation
):
    key = {"api": api.ref, "channelAddress": "orders.created", "direction": "send"}
    body = {
        "service": service.ref,
        "items": [{**key, "role": "publisher"}, {**key, "role": "subscriber"}],
    }

    linked = _post(dmr_client, OPERATION_LINK, body, apis_header)
    unlinked = _post(
        dmr_client,
        OPERATION_UNLINK,
        {"service": service.ref, "items": [{**key, "role": "publisher"}]},
        apis_header,
    )

    assert _statuses(linked) == ["created", "created"]
    assert "apiRelationCreated" not in linked.json()["items"][0] or (
        linked.json()["items"][0]["apiRelationCreated"] is None
    )
    assert _statuses(unlinked) == ["removed"]
    remaining = ServiceOperationUsage.objects.get()
    assert (remaining.role, remaining.origin, remaining.source) == (
        "subscriber",
        "manual",
        "mcp",
    )
    assert not service.component_details.consumes_apis.exists()


def test_operation_item_without_a_role_rejects_the_request(
    dmr_client, apis_header, service, operation
):
    response = _post(
        dmr_client,
        OPERATION_LINK,
        {"service": service.ref, "items": [{"operationId": str(operation.id)}]},
        apis_header,
    )

    assert response.status_code == 400
    assert not ServiceOperationUsage.objects.exists()


def test_a_token_without_apis_write_is_rejected(
    dmr_client, catalog_write_only_header, service, endpoint
):
    response = _post(
        dmr_client,
        ENDPOINT_LINK,
        {"service": service.ref, "items": [{"endpointId": str(endpoint.id)}]},
        catalog_write_only_header,
    )

    assert response.status_code == 403
    assert not ServiceEndpointUsage.objects.exists()


def test_apis_write_cannot_exceed_the_owners_permissions(
    dmr_client, outsider_apis_header, service, endpoint
):
    response = _post(
        dmr_client,
        ENDPOINT_LINK,
        {"service": service.ref, "items": [{"endpointId": str(endpoint.id)}]},
        outsider_apis_header,
    )

    assert response.status_code == 403
    assert not ServiceEndpointUsage.objects.exists()


@pytest.mark.parametrize("kind_ref", ["system:user-management", "api:invoices-api"])
def test_a_non_component_service_is_rejected(
    dmr_client, apis_header, endpoint, kind_ref
):
    response = _post(
        dmr_client,
        ENDPOINT_LINK,
        {"service": kind_ref, "items": [{"endpointId": str(endpoint.id)}]},
        apis_header,
    )

    assert response.status_code == 400
    assert not ServiceEndpointUsage.objects.exists()


def test_an_unknown_service_is_404(dmr_client, apis_header, endpoint):
    response = _post(
        dmr_client,
        ENDPOINT_LINK,
        {"service": "component:nope", "items": [{"endpointId": str(endpoint.id)}]},
        apis_header,
    )

    assert response.status_code == 404, response.content


def test_an_oversized_batch_is_rejected_whole(
    dmr_client, apis_header, service, endpoint
):
    items = [{"endpointId": str(endpoint.id)}] * (MAX_USAGE_BATCH_SIZE + 1)

    response = _post(
        dmr_client, ENDPOINT_LINK, {"service": service.ref, "items": items}, apis_header
    )

    assert response.status_code == 400
    assert str(MAX_USAGE_BATCH_SIZE) in response.content.decode()
    assert not ServiceEndpointUsage.objects.exists()


def test_an_unknown_body_field_is_rejected(dmr_client, apis_header, service):
    response = _post(
        dmr_client,
        ENDPOINT_LINK,
        {"service": service.ref, "items": [{"source": "ui", "endpointId": "x"}]},
        apis_header,
    )

    assert response.status_code == 400


def test_tool_descriptions_state_scope_limit_and_consumes_api_side_effect():
    schema = build_openapi_schema()
    descriptions = {}
    for item in (schema.paths or {}).values():
        operation = getattr(item, "post", None)
        if operation is not None and operation.operation_id:
            descriptions[operation.operation_id] = operation.description

    for name in (
        "link_endpoint_consumers",
        "unlink_endpoint_consumers",
        "link_operation_participants",
        "unlink_operation_participants",
    ):
        text = descriptions[name]
        assert "apis:write" in text
        assert str(MAX_USAGE_BATCH_SIZE) in text
        assert "dryRun" in text
    assert "consumesAPI" in descriptions["link_endpoint_consumers"]
    assert "never removed" in descriptions["unlink_endpoint_consumers"]
