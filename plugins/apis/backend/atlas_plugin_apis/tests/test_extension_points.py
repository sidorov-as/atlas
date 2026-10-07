"""Tests for `atlas_plugin_apis.extension_points`'s resolve/search/consumers functions."""

import uuid
from http import HTTPStatus

import pytest
from dmr.response import APIError
from server.apps.catalog.tests.factories import (
    create_api,
    create_component,
    create_system,
)

from atlas_plugin_apis import permissions
from atlas_plugin_apis.extension_points import (
    AlreadyLinkedError,
    NotLinkedError,
    find_endpoint,
    find_operations,
    get_endpoint,
    get_endpoint_consumers,
    get_operation,
    get_operation_consumers,
    link_endpoint,
    link_operation,
    resolve_endpoint,
    resolve_operation,
    search_endpoints,
    search_operations,
    unlink_endpoint,
    unlink_operation,
)
from atlas_plugin_apis.models import (
    ApiEndpoint,
    ApiOperation,
    ServiceEndpointUsage,
    ServiceOperationUsage,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def system(group):
    return create_system(name="core", owner=group)


@pytest.fixture
def api(group, system):
    return create_api(name="billing-api", owner=group, system=system)


def test_resolve_endpoint_returns_the_row_with_its_api(api):
    endpoint = ApiEndpoint.objects.create(
        api=api, method=ApiEndpoint.METHOD_GET, path="/v1/invoices"
    )

    resolved = resolve_endpoint(endpoint.id)

    assert resolved is not None
    assert resolved.id == endpoint.id
    assert resolved.api_id == api.id


def test_resolve_endpoint_returns_none_for_a_nonexistent_id(api):
    assert resolve_endpoint("00000000-0000-0000-0000-000000000000") is None


def test_resolve_endpoint_returns_none_for_a_malformed_id():
    assert resolve_endpoint("not-a-uuid") is None


def test_resolve_operation_returns_the_row_with_its_api(api):
    operation = ApiOperation.objects.create(
        api=api,
        channel_address="orders.created",
        direction=ApiOperation.DIRECTION_SEND,
        operation_key="orders.created:send",
    )

    resolved = resolve_operation(operation.id)

    assert resolved is not None
    assert resolved.id == operation.id
    assert resolved.api_id == api.id


def test_resolve_operation_returns_none_for_a_nonexistent_id(api):
    assert resolve_operation("00000000-0000-0000-0000-000000000000") is None


def test_resolve_operation_returns_none_for_a_malformed_id():
    assert resolve_operation("not-a-uuid") is None


# --- search_endpoints / search_operations / get_*_consumers ---------------------------------


class _DenyAll:
    def check(self, user, permission, resource=None):
        return False


@pytest.fixture
def deny_all(monkeypatch):
    monkeypatch.setattr(permissions, "get_policy_evaluator", lambda: _DenyAll())


@pytest.fixture
def actor(member_account):
    return member_account


@pytest.fixture
def other_api(group, system):
    return create_api(name="payments-api", owner=group, system=system)


@pytest.fixture
def provider(group, system, api):
    return create_component(
        name="billing-service", owner=group, system=system, provides_apis=[api]
    )


@pytest.fixture
def consumer(group, system):
    return create_component(name="reporting-service", owner=group, system=system)


def _endpoint(api, path="/v1/invoices", **kwargs):
    return ApiEndpoint.objects.create(
        api=api, method=ApiEndpoint.METHOD_GET, path=path, **kwargs
    )


def _operation(api, channel="orders.created", direction=ApiOperation.DIRECTION_SEND):
    return ApiOperation.objects.create(
        api=api,
        channel_address=channel,
        direction=direction,
        operation_key=f"{channel}:{direction}",
    )


def test_search_endpoints_is_cross_api_by_default_and_api_scoped_on_request(
    actor, api, other_api
):
    mine = _endpoint(api)
    theirs = _endpoint(other_api, path="/v1/payments")

    everywhere = search_endpoints(actor)
    scoped = search_endpoints(actor, api_id=api.id)

    assert {e.id for e in everywhere.object_list} == {mine.id, theirs.id}
    assert [e.id for e in scoped.object_list] == [mine.id]
    assert scoped.object_list[0].api_id == api.id


def test_search_endpoints_matches_query_and_skips_removed(actor, api):
    match = _endpoint(api, path="/v1/invoices")
    _endpoint(api, path="/v1/users")
    _endpoint(api, path="/v1/invoices/old", status=ApiEndpoint.STATUS_REMOVED)

    page = search_endpoints(actor, query="invoice")

    assert [e.id for e in page.object_list] == [match.id]


def test_search_endpoints_with_malformed_api_id_matches_nothing(actor, api):
    _endpoint(api)

    assert list(search_endpoints(actor, api_id="not-a-uuid").object_list) == []


def test_search_endpoints_rejects_without_read_permission(deny_all, actor, api):
    _endpoint(api)

    with pytest.raises(APIError) as exc:
        search_endpoints(actor)

    assert exc.value.status_code == HTTPStatus.FORBIDDEN


def test_search_operations_is_cross_api_by_default_and_api_scoped_on_request(
    actor, api, other_api
):
    mine = _operation(api)
    theirs = _operation(other_api, channel="payments.created")

    everywhere = search_operations(actor)
    scoped = search_operations(actor, api_id=api.id)

    assert {o.id for o in everywhere.object_list} == {mine.id, theirs.id}
    assert [o.id for o in scoped.object_list] == [mine.id]


def test_search_operations_matches_query_and_skips_removed(actor, api):
    match = _operation(api, channel="orders.created")
    _operation(api, channel="users.created")
    removed = _operation(api, channel="orders.cancelled")
    ApiOperation.objects.filter(pk=removed.pk).update(
        status=ApiOperation.STATUS_REMOVED
    )

    page = search_operations(actor, query="orders")

    assert [o.id for o in page.object_list] == [match.id]


def test_search_operations_rejects_without_read_permission(deny_all, actor, api):
    with pytest.raises(APIError) as exc:
        search_operations(actor)

    assert exc.value.status_code == HTTPStatus.FORBIDDEN


def test_get_endpoint_consumers_returns_only_explicitly_linked_services(
    actor, api, group, system, consumer
):
    endpoint = _endpoint(api)
    # Consumes the whole API at the Component level, but has no `ServiceEndpointUsage`.
    create_component(
        name="whole-api-consumer", owner=group, system=system, consumes_apis=[api]
    )
    ServiceEndpointUsage.objects.create(endpoint=endpoint, service=consumer)

    result = get_endpoint_consumers(actor, endpoint.id)

    assert [s.id for s in result] == [consumer.id]


def test_get_endpoint_consumers_returns_empty_list_without_links(actor, api):
    assert get_endpoint_consumers(actor, _endpoint(api).id) == []


def test_get_endpoint_consumers_returns_none_for_unresolvable_id(actor):
    assert get_endpoint_consumers(actor, "00000000-0000-0000-0000-000000000000") is None
    assert get_endpoint_consumers(actor, "not-a-uuid") is None


def test_get_endpoint_consumers_rejects_without_dependency_read_permission(
    deny_all, actor, api
):
    with pytest.raises(APIError) as exc:
        get_endpoint_consumers(actor, _endpoint(api).id)

    assert exc.value.status_code == HTTPStatus.FORBIDDEN


def test_get_operation_consumers_returns_linked_services_with_roles(
    actor, api, group, system, provider, consumer
):
    operation = _operation(api)
    create_component(
        name="whole-api-consumer", owner=group, system=system, consumes_apis=[api]
    )
    ServiceOperationUsage.objects.create(
        operation=operation,
        service=consumer,
        role=ServiceOperationUsage.ROLE_SUBSCRIBER,
    )

    result = get_operation_consumers(actor, operation.id)

    assert {(s.id, role) for s, role in result} == {
        (provider.id, "publisher"),  # implied by the operation's `send` direction
        (consumer.id, "subscriber"),
    }


def test_get_operation_consumers_excludes_removed_operations(
    actor, api, group, system, provider, consumer
):
    operation = _operation(api)
    other_api = create_api(
        name="other-api", owner=group, system=system, type="asyncapi"
    )
    removed = ApiOperation.objects.create(
        api=other_api,
        channel_address=operation.channel_address,
        direction=ApiOperation.DIRECTION_RECEIVE,
        operation_key="removed-op",
        status=ApiOperation.STATUS_REMOVED,
    )
    ServiceOperationUsage.objects.create(
        operation=removed,
        service=consumer,
        role=ServiceOperationUsage.ROLE_SUBSCRIBER,
    )

    result = get_operation_consumers(actor, operation.id)

    assert {(s.id, role) for s, role in result} == {(provider.id, "publisher")}


def test_get_operation_consumers_returns_empty_list_without_links(actor, api):
    assert get_operation_consumers(actor, _operation(api).id) == []


def test_get_operation_consumers_returns_none_for_unresolvable_id(actor):
    assert (
        get_operation_consumers(actor, "00000000-0000-0000-0000-000000000000") is None
    )


def test_get_operation_consumers_rejects_without_dependency_read_permission(
    deny_all, actor, api
):
    with pytest.raises(APIError) as exc:
        get_operation_consumers(actor, _operation(api).id)

    assert exc.value.status_code == HTTPStatus.FORBIDDEN


def test_get_endpoint_resolves_and_rejects_without_read_permission(
    actor, api, monkeypatch
):
    endpoint = _endpoint(api)

    assert get_endpoint(actor, endpoint.id) == endpoint
    assert get_endpoint(actor, uuid.uuid4()) is None

    monkeypatch.setattr(permissions, "get_policy_evaluator", lambda: _DenyAll())
    with pytest.raises(APIError) as exc:
        get_endpoint(actor, endpoint.id)
    assert exc.value.status_code == HTTPStatus.FORBIDDEN


def test_get_operation_resolves_and_rejects_without_read_permission(
    actor, api, monkeypatch
):
    operation = _operation(api)

    assert get_operation(actor, operation.id) == operation
    assert get_operation(actor, uuid.uuid4()) is None

    monkeypatch.setattr(permissions, "get_policy_evaluator", lambda: _DenyAll())
    with pytest.raises(APIError) as exc:
        get_operation(actor, operation.id)
    assert exc.value.status_code == HTTPStatus.FORBIDDEN


# --- find_endpoint / find_operations -----------------------------------


def test_find_endpoint_matches_method_and_path_including_removed(api):
    removed = _endpoint(api, status=ApiEndpoint.STATUS_REMOVED)

    assert find_endpoint(api, "get", "/v1/invoices") == removed
    assert find_endpoint(api, "POST", "/v1/invoices") is None


def test_find_endpoint_is_scoped_to_its_api(api, other_api):
    _endpoint(api)

    assert find_endpoint(other_api, "GET", "/v1/invoices") is None


def test_find_operations_returns_every_active_match_and_skips_removed(api):
    first = ApiOperation.objects.create(
        api=api, channel_address="a", direction="send", operation_key="one"
    )
    second = ApiOperation.objects.create(
        api=api, channel_address="a", direction="send", operation_key="two"
    )
    ApiOperation.objects.create(
        api=api,
        channel_address="a",
        direction="send",
        operation_key="gone",
        status=ApiOperation.STATUS_REMOVED,
    )
    ApiOperation.objects.create(
        api=api, channel_address="a", direction="receive", operation_key="rx"
    )

    assert find_operations(api, "a", "send") == [first, second]
    assert find_operations(api, "missing", "send") == []


# --- link / unlink -----------------------------------------------------


def test_link_endpoint_records_source_and_reports_the_consumes_api_side_effect(
    superuser_account, group, system, api
):
    service = create_component(name="svc", owner=group, system=system)
    endpoint = _endpoint(api)

    usage, created = link_endpoint(superuser_account, service, endpoint, source="mcp")

    assert (usage.origin, usage.source, usage.created_by) == (
        "manual",
        "mcp",
        superuser_account,
    )
    assert created is True
    other = _endpoint(api, path="/v1/other")
    _, created_again = link_endpoint(superuser_account, service, other, source="mcp")
    assert created_again is False


def test_link_endpoint_twice_raises_already_linked(
    superuser_account, group, system, api
):
    service = create_component(name="svc", owner=group, system=system)
    endpoint = _endpoint(api)
    link_endpoint(superuser_account, service, endpoint, source="mcp")

    with pytest.raises(AlreadyLinkedError):
        link_endpoint(superuser_account, service, endpoint, source="mcp")


def test_unlink_endpoint_without_a_link_raises_not_linked(
    superuser_account, group, system, api
):
    service = create_component(name="svc", owner=group, system=system)

    with pytest.raises(NotLinkedError):
        unlink_endpoint(superuser_account, service, _endpoint(api))


def test_link_operation_records_source_and_unlink_removes_one_role(
    superuser_account, group, system, api
):
    service = create_component(name="svc", owner=group, system=system)
    operation = ApiOperation.objects.create(
        api=api, channel_address="a", direction="send", operation_key="one"
    )

    usage = link_operation(
        superuser_account, service, operation, "publisher", source="mcp"
    )
    link_operation(superuser_account, service, operation, "subscriber", source="mcp")
    unlink_operation(superuser_account, service, operation, "publisher")

    assert (usage.origin, usage.source) == ("manual", "mcp")
    assert list(
        ServiceOperationUsage.objects.filter(service=service).values_list(
            "role", flat=True
        )
    ) == ["subscriber"]
