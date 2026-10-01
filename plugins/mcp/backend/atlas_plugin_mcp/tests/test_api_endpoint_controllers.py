"""`search_api_endpoints`/`get_api_endpoint`/`get_endpoint_consumers` and their
Operation equivalents (`mcp-plugin` spec's API Endpoint/Operation requirements).
Routes through `atlas_plugin_apis.extension_points`, so rows are built with the
`apis` models directly, as that plugin's own extension-point tests do."""

import atlas_plugin_api.pat as pat_module
import pytest
from atlas_plugin_api.pat import ResolvedPersonalAccessToken, bind_pat_validator
from atlas_plugin_apis import permissions
from atlas_plugin_apis.models import (
    ApiEndpoint,
    ApiOperation,
    ServiceEndpointUsage,
    ServiceOperationUsage,
)
from server.apps.catalog.tests.factories import create_api, create_component

pytestmark = pytest.mark.django_db

BASE = "/api/plugins/atlas.mcp"


@pytest.fixture
def api(group, system):
    return create_api(name="invoices-api", owner=group, system=system)


@pytest.fixture
def endpoint(api):
    return ApiEndpoint.objects.create(
        api=api,
        method=ApiEndpoint.METHOD_GET,
        path="/v1/invoices",
        summary="List invoices",
        responses=[{"statusCode": "200", "description": "ok"}],
    )


@pytest.fixture
def operation(api):
    return ApiOperation.objects.create(
        api=api,
        channel_address="orders.created",
        direction=ApiOperation.DIRECTION_SEND,
        operation_key="orders.created:send",
    )


@pytest.fixture
def consumer(group, system):
    return create_component(name="reporting-service", owner=group, system=system)


@pytest.fixture
def whole_api_consumer(group, system, api):
    return create_component(
        name="whole-api-consumer", owner=group, system=system, consumes_apis=[api]
    )


@pytest.fixture
def no_scope_pat_header(owner_account):
    previous = pat_module._pat_validator
    token = "atlaspat_mcp-test-no-scope-token"

    def _validator(raw_token):
        if raw_token != token:
            return None
        return ResolvedPersonalAccessToken(user=owner_account, scopes=frozenset())

    bind_pat_validator(_validator)
    try:
        yield {"HTTP_AUTHORIZATION": f"Bearer {token}"}
    finally:
        pat_module._pat_validator = previous


class _DenyAll:
    def check(self, user, permission, resource=None):
        return False


def test_search_api_endpoints_is_cross_api_and_api_scoped(
    dmr_client, pat_auth_header, endpoint, api, group, system
):
    other = create_api(name="payments-api", owner=group, system=system)
    ApiEndpoint.objects.create(
        api=other, method=ApiEndpoint.METHOD_POST, path="/v1/payments"
    )

    everywhere = dmr_client.get(f"{BASE}/endpoints/search/", **pat_auth_header)
    scoped = dmr_client.get(
        f"{BASE}/endpoints/search/", {"apiId": str(api.id)}, **pat_auth_header
    )

    assert everywhere.status_code == 200
    assert everywhere.json()["count"] == 2
    results = scoped.json()["page"]["objectList"]
    assert [r["id"] for r in results] == [str(endpoint.id)]
    assert results[0]["api"] == api.ref


def test_get_api_endpoint_returns_full_detail(dmr_client, pat_auth_header, endpoint):
    response = dmr_client.get(f"{BASE}/endpoints/{endpoint.id}/", **pat_auth_header)

    assert response.status_code == 200
    body = response.json()
    assert body["path"] == "/v1/invoices"
    assert body["responses"] == [{"statusCode": "200", "description": "ok"}]


def test_get_api_endpoint_returns_404_for_unknown_id(dmr_client, pat_auth_header):
    response = dmr_client.get(
        f"{BASE}/endpoints/00000000-0000-0000-0000-000000000000/", **pat_auth_header
    )

    assert response.status_code == 404


def test_get_endpoint_consumers_returns_only_explicitly_linked_services(
    dmr_client, pat_auth_header, endpoint, consumer, whole_api_consumer
):
    ServiceEndpointUsage.objects.create(endpoint=endpoint, service=consumer)

    response = dmr_client.get(
        f"{BASE}/endpoints/{endpoint.id}/consumers/", **pat_auth_header
    )

    assert response.status_code == 200
    services = response.json()["services"]
    assert [s["id"] for s in services] == [str(consumer.id)]


def test_get_endpoint_consumers_is_empty_without_links(
    dmr_client, pat_auth_header, endpoint, whole_api_consumer
):
    response = dmr_client.get(
        f"{BASE}/endpoints/{endpoint.id}/consumers/", **pat_auth_header
    )

    assert response.json()["services"] == []


def test_search_and_get_api_operations(dmr_client, pat_auth_header, operation, api):
    search = dmr_client.get(
        f"{BASE}/operations/search/", {"apiId": str(api.id)}, **pat_auth_header
    )
    detail = dmr_client.get(f"{BASE}/operations/{operation.id}/", **pat_auth_header)

    assert [r["id"] for r in search.json()["page"]["objectList"]] == [str(operation.id)]
    assert detail.status_code == 200
    assert detail.json()["channelAddress"] == "orders.created"


def test_get_operation_consumers_carries_roles_and_skips_whole_api_consumers(
    dmr_client, pat_auth_header, operation, consumer, whole_api_consumer
):
    ServiceOperationUsage.objects.create(
        operation=operation,
        service=consumer,
        role=ServiceOperationUsage.ROLE_SUBSCRIBER,
    )

    response = dmr_client.get(
        f"{BASE}/operations/{operation.id}/consumers/", **pat_auth_header
    )

    assert response.status_code == 200
    participants = {
        (p["service"]["id"], p["role"]) for p in response.json()["participants"]
    }
    assert participants == {(str(consumer.id), "subscriber")}


@pytest.mark.parametrize(
    "url",
    [
        "endpoints/search/",
        "endpoints/{endpoint}/",
        "endpoints/{endpoint}/consumers/",
        "operations/search/",
        "operations/{operation}/",
        "operations/{operation}/consumers/",
    ],
)
def test_a_pat_with_no_scopes_can_call_every_api_tool(
    dmr_client, no_scope_pat_header, endpoint, operation, url
):
    response = dmr_client.get(
        f"{BASE}/{url.format(endpoint=endpoint.id, operation=operation.id)}",
        **no_scope_pat_header,
    )

    assert response.status_code == 200


@pytest.mark.parametrize(
    "url",
    [
        "endpoints/search/",
        "endpoints/{endpoint}/",
        "endpoints/{endpoint}/consumers/",
        "operations/search/",
        "operations/{operation}/",
        "operations/{operation}/consumers/",
    ],
)
def test_a_user_without_read_permission_is_rejected_like_rest(
    dmr_client, pat_auth_header, endpoint, operation, url, monkeypatch
):
    monkeypatch.setattr(permissions, "get_policy_evaluator", lambda: _DenyAll())

    response = dmr_client.get(
        f"{BASE}/{url.format(endpoint=endpoint.id, operation=operation.id)}",
        **pat_auth_header,
    )

    assert response.status_code == 403
