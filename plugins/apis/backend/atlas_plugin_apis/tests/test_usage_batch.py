"""Batch link/unlink functions (`mcp-api-usage-tools` spec): per-item statuses,
partial success, addressing by id or natural key, `dryRun`, request-level limits."""

import pytest
from dmr.response import APIError
from server.apps.catalog.tests.factories import (
    create_api,
    create_component,
    create_system,
)

from atlas_plugin_apis.extension_points import (
    MAX_USAGE_BATCH_SIZE,
    UsageBatchError,
    UsageItem,
    link_endpoints,
    link_operations,
    unlink_endpoints,
    unlink_operations,
)
from atlas_plugin_apis.models import (
    ApiEndpoint,
    ApiOperation,
    ServiceEndpointUsage,
    ServiceOperationUsage,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def actor(owner_user):
    return owner_user.actor_details.account


@pytest.fixture
def system(group):
    return create_system(name="core", owner=group)


@pytest.fixture
def api(group, system):
    return create_api(name="billing-api", owner=group, system=system)


@pytest.fixture
def service(group, system):
    return create_component(name="web", owner=group, system=system)


def _endpoint(api, path="/v1/a", method="GET", **kwargs):
    return ApiEndpoint.objects.create(api=api, method=method, path=path, **kwargs)


def _operation(api, key="one", channel="orders", direction="send", **kwargs):
    return ApiOperation.objects.create(
        api=api,
        channel_address=channel,
        direction=direction,
        operation_key=key,
        **kwargs,
    )


def _by_key(api, path="/v1/a", method="GET"):
    return UsageItem(api=api.ref, method=method, path=path)


def _statuses(result):
    return [item.status for item in result.items]


# --- endpoints ------------------------------------------------------------


def test_link_endpoints_by_id_and_by_key_and_rerun_is_unchanged(actor, service, api):
    first = _endpoint(api, "/v1/a")
    _endpoint(api, "/v1/b")
    items = [UsageItem(endpoint_id=str(first.id)), _by_key(api, "/v1/b")]

    result = link_endpoints(actor, service, items, source="mcp")

    assert _statuses(result) == ["created", "created"]
    assert result.counts == {"created": 2}
    assert (
        ServiceEndpointUsage.objects.filter(service=service, source="mcp").count() == 2
    )
    again = link_endpoints(actor, service, items, source="mcp")
    assert _statuses(again) == ["unchanged", "unchanged"]
    assert ServiceEndpointUsage.objects.filter(service=service).count() == 2


def test_partial_success_with_one_stale_item(actor, service, api):
    _endpoint(api, "/v1/a")
    items = [_by_key(api, "/v1/a"), _by_key(api, "/v1/gone"), _by_key(api, "/v1/a")]

    result = link_endpoints(actor, service, items, source="mcp")

    assert _statuses(result) == ["created", "not_found", "unchanged"]
    assert result.counts == {"created": 1, "not_found": 1, "unchanged": 1}
    assert "/v1/gone" in result.items[1].message


def test_consumes_api_reported_on_first_link_only(actor, service, api):
    _endpoint(api, "/v1/a")
    _endpoint(api, "/v1/b")

    result = link_endpoints(
        actor, service, [_by_key(api, "/v1/a"), _by_key(api, "/v1/b")], source="mcp"
    )

    assert [item.api_relation_created for item in result.items] == [True, False]


def test_invalid_item_shapes_do_not_stop_the_batch(actor, service, api):
    endpoint = _endpoint(api)
    items = [
        UsageItem(
            endpoint_id=str(endpoint.id), api=api.ref, method="GET", path="/v1/a"
        ),
        UsageItem(),
        UsageItem(api=api.ref, method="GET"),
        UsageItem(api=api.ref, method="FETCH", path="/v1/a"),
        UsageItem(endpoint_id="not-a-uuid"),
        UsageItem(api="component:web", method="GET", path="/v1/a"),
        UsageItem(endpoint_id=str(endpoint.id)),
    ]

    result = link_endpoints(actor, service, items, source="mcp")

    assert _statuses(result) == [
        "invalid",
        "invalid",
        "invalid",
        "invalid",
        "not_found",
        "invalid",
        "created",
    ]


def test_unknown_api_ref_is_not_found(actor, service):
    result = link_endpoints(
        actor,
        service,
        [UsageItem(api="api:nope", method="GET", path="/x")],
        source="mcp",
    )

    assert _statuses(result) == ["not_found"]


def test_removed_endpoint_is_a_conflict_to_link_and_removable(actor, service, api):
    removed = _endpoint(api, status=ApiEndpoint.STATUS_REMOVED)
    ServiceEndpointUsage.objects.create(endpoint=removed, service=service)
    by_id = UsageItem(endpoint_id=str(removed.id))

    linked = link_endpoints(actor, service, [by_id, _by_key(api)], source="mcp")
    unlinked = unlink_endpoints(actor, service, [_by_key(api)])

    assert _statuses(linked) == ["conflict", "conflict"]
    assert _statuses(unlinked) == ["removed"]
    assert not ServiceEndpointUsage.objects.exists()


def test_unlink_endpoints_statuses_and_consumes_api_kept(actor, service, api):
    endpoint = _endpoint(api)
    _endpoint(api, "/v1/b")
    link_endpoints(actor, service, [_by_key(api)], source="mcp")

    result = unlink_endpoints(actor, service, [_by_key(api), _by_key(api, "/v1/b")])

    assert _statuses(result) == ["removed", "unchanged"]
    assert not ServiceEndpointUsage.objects.filter(endpoint=endpoint).exists()
    assert service.component_details.consumes_apis.filter(pk=api.pk).exists()


def test_unlink_yaml_origin_endpoint_link_is_a_conflict(actor, service, api):
    endpoint = _endpoint(api)
    ServiceEndpointUsage.objects.create(
        endpoint=endpoint, service=service, origin="yaml"
    )

    result = unlink_endpoints(actor, service, [_by_key(api)])

    assert _statuses(result) == ["conflict"]
    assert "ingestion" in result.items[0].message
    assert ServiceEndpointUsage.objects.count() == 1


def test_dry_run_leaves_no_rows_and_no_consumes_api(actor, service, api):
    _endpoint(api, "/v1/a")
    _endpoint(api, "/v1/b")
    link_endpoints(actor, service, [_by_key(api, "/v1/a")], source="mcp")
    service.component_details.consumes_apis.remove(api)
    before = ServiceEndpointUsage.objects.count()

    result = link_endpoints(
        actor,
        service,
        [_by_key(api, "/v1/a"), _by_key(api, "/v1/b")],
        source="mcp",
        dry=True,
    )

    assert result.dry_run is True
    assert _statuses(result) == ["unchanged", "created"]
    assert result.items[1].api_relation_created is True
    assert ServiceEndpointUsage.objects.count() == before
    assert not service.component_details.consumes_apis.filter(pk=api.pk).exists()


def test_dry_run_unlink_keeps_every_link(actor, service, api):
    _endpoint(api)
    link_endpoints(actor, service, [_by_key(api)], source="mcp")

    result = unlink_endpoints(actor, service, [_by_key(api)], dry=True)

    assert _statuses(result) == ["removed"]
    assert ServiceEndpointUsage.objects.count() == 1


# --- request level --------------------------------------------------------


def test_oversized_batch_is_rejected_whole(actor, service, api):
    endpoint = _endpoint(api)
    items = [UsageItem(endpoint_id=str(endpoint.id))] * (MAX_USAGE_BATCH_SIZE + 1)

    with pytest.raises(UsageBatchError) as raised:
        link_endpoints(actor, service, items, source="mcp")

    assert str(MAX_USAGE_BATCH_SIZE) in str(raised.value.raw_data)
    assert not ServiceEndpointUsage.objects.exists()


def test_empty_batch_is_rejected(actor, service):
    with pytest.raises(UsageBatchError):
        link_endpoints(actor, service, [], source="mcp")


def test_non_component_service_is_rejected(actor, api, system):
    with pytest.raises(UsageBatchError):
        link_endpoints(actor, system, [UsageItem(endpoint_id="x")], source="mcp")


def test_missing_permission_on_the_service_rejects_the_request(
    member_account, service, api
):
    endpoint = _endpoint(api)

    with pytest.raises(APIError) as raised:
        link_endpoints(
            member_account,
            service,
            [UsageItem(endpoint_id=str(endpoint.id))],
            source="mcp",
        )

    assert raised.value.status_code == 403
    assert not ServiceEndpointUsage.objects.exists()


# --- operations -----------------------------------------------------------


def _op_key(api, channel="orders", direction="send", role="publisher"):
    return UsageItem(
        api=api.ref, channel_address=channel, direction=direction, role=role
    )


def test_link_operations_by_id_and_key_with_both_roles(actor, service, api):
    operation = _operation(api)
    items = [
        UsageItem(operation_id=str(operation.id), role="publisher"),
        _op_key(api, role="subscriber"),
    ]

    result = link_operations(actor, service, items, source="mcp")

    assert _statuses(result) == ["created", "created"]
    assert {item.api_relation_created for item in result.items} == {None}
    usages = ServiceOperationUsage.objects.filter(service=service)
    assert {(u.role, u.origin, u.source, u.created_by) for u in usages} == {
        ("publisher", "manual", "mcp", actor),
        ("subscriber", "manual", "mcp", actor),
    }
    assert not service.component_details.consumes_apis.exists()
    again = link_operations(actor, service, items, source="mcp")
    assert _statuses(again) == ["unchanged", "unchanged"]


def test_operation_item_without_role_is_invalid(actor, service, api):
    _operation(api)

    result = link_operations(
        actor,
        service,
        [UsageItem(api=api.ref, channel_address="orders", direction="send")],
        source="mcp",
    )

    assert _statuses(result) == ["invalid"]
    assert not ServiceOperationUsage.objects.exists()


def test_ambiguous_operation_key_lists_candidates(actor, service, api):
    first = _operation(api, key="one")
    second = _operation(api, key="two")

    result = link_operations(actor, service, [_op_key(api)], source="mcp")

    assert _statuses(result) == ["ambiguous"]
    assert sorted(result.items[0].candidates) == sorted([str(first.id), str(second.id)])
    assert not ServiceOperationUsage.objects.exists()


def test_operation_key_ignores_removed_operations(actor, service, api):
    _operation(api, key="gone", status=ApiOperation.STATUS_REMOVED)
    active = _operation(api, key="live")

    result = link_operations(actor, service, [_op_key(api)], source="mcp")

    assert _statuses(result) == ["created"]
    assert result.items[0].operation_id == str(active.id)


def test_document_owner_is_a_conflict(actor, group, system, api):
    owner = create_component(
        name="owner-svc", owner=group, system=system, provides_apis=[api]
    )
    _operation(api)

    result = link_operations(actor, owner, [_op_key(api)], source="mcp")

    assert _statuses(result) == ["conflict"]
    assert "document owner" in result.items[0].message


def test_unlink_operations_removes_only_the_role(actor, service, api):
    _operation(api)
    link_operations(
        actor,
        service,
        [_op_key(api, role="publisher"), _op_key(api, role="subscriber")],
        source="mcp",
    )

    result = unlink_operations(
        actor, service, [_op_key(api, role="publisher"), _op_key(api, role="publisher")]
    )

    assert _statuses(result) == ["removed", "unchanged"]
    assert list(ServiceOperationUsage.objects.values_list("role", flat=True)) == [
        "subscriber"
    ]


def test_unlink_yaml_origin_operation_link_is_a_conflict(actor, service, api):
    operation = _operation(api)
    ServiceOperationUsage.objects.create(
        operation=operation, service=service, role="publisher", origin="yaml"
    )

    result = unlink_operations(actor, service, [_op_key(api)])

    assert _statuses(result) == ["conflict"]
    assert ServiceOperationUsage.objects.count() == 1


def test_dry_run_of_operation_link_persists_nothing(actor, service, api):
    _operation(api)

    result = link_operations(actor, service, [_op_key(api)], source="mcp", dry=True)

    assert _statuses(result) == ["created"]
    assert not ServiceOperationUsage.objects.exists()
