"""Tests for the Service<->Operation dependency API
including duplicate-link
rejection, multiple-services-same-role, self-link-of-document-owner
rejection, search/filter/sort/pagination, the channel-scoped
consumers aggregation across API documents, and per-role unlink.
"""

import pytest
from server.apps.catalog.tests.factories import (
    create_api,
    create_component,
    create_group,
    create_system,
)

from atlas_plugin_apis.models import ApiOperation, ServiceOperationUsage

pytestmark = pytest.mark.django_db


@pytest.fixture
def system(group):
    return create_system(name="core", owner=group)


@pytest.fixture
def api(group, system):
    return create_api(name="booking-api", owner=group, system=system, type="asyncapi")


@pytest.fixture
def service(group, system):
    return create_component(name="reporting-service", owner=group, system=system)


@pytest.fixture
def operation(api):
    return ApiOperation.objects.create(
        api=api,
        channel_address="booking.created",
        direction=ApiOperation.DIRECTION_SEND,
        operation_key="onBookingCreated",
    )


def _link(client, operation, service, role="subscriber"):
    return client.post(
        f"/api/operations/{operation.id}/services/",
        {"serviceId": str(service.id), "role": role},
    )


def _seed_link(operation, service, role="subscriber"):
    """Create a `ServiceOperationUsage` directly, bypassing the create API's
    authorization — for tests below that only exercise reads (list/consumers)
    and need a link owned by a team the test's client isn't a member of."""
    return ServiceOperationUsage.objects.create(
        operation=operation, service=service, role=role
    )


# --- Link / unlink CRUD ------------------------------


def test_link_creates_a_service_operation_usage(owner_client, operation, service):
    response = _link(owner_client, operation, service, role="subscriber")

    assert response.status_code == 201
    body = response.json()
    assert body["service"]["id"] == str(service.id)
    assert body["role"] == "subscriber"
    assert ServiceOperationUsage.objects.filter(
        operation=operation,
        service=service,
        role="subscriber",
    ).exists()


def test_linking_the_same_operation_service_and_role_twice_is_rejected(
    owner_client, operation, service
):
    _link(owner_client, operation, service, role="subscriber")

    response = _link(owner_client, operation, service, role="subscriber")

    assert response.status_code == 409
    assert (
        ServiceOperationUsage.objects.filter(
            operation=operation,
            service=service,
            role="subscriber",
        ).count()
        == 1
    )


def test_multiple_services_can_hold_the_same_role(
    owner_client, operation, service, group, system
):
    other_service = create_component(
        name="analytics-service", owner=group, system=system
    )
    _link(owner_client, operation, service, role="subscriber")

    response = _link(owner_client, operation, other_service, role="subscriber")

    assert response.status_code == 201
    assert (
        ServiceOperationUsage.objects.filter(
            operation=operation, role="subscriber"
        ).count()
        == 2
    )


def test_a_service_can_hold_both_roles_on_one_operation(
    owner_client, operation, service
):
    _link(owner_client, operation, service, role="publisher")

    response = _link(owner_client, operation, service, role="subscriber")

    assert response.status_code == 201
    assert (
        ServiceOperationUsage.objects.filter(
            operation=operation, service=service
        ).count()
        == 2
    )


def test_linking_the_operations_own_document_owner_is_rejected(
    owner_client, operation, group, system, api
):
    provider = create_component(
        name="booking-service", owner=group, system=system, provides_apis=[api]
    )

    response = _link(owner_client, operation, provider, role="publisher")

    assert response.status_code == 409
    assert not ServiceOperationUsage.objects.filter(
        operation=operation, service=provider
    ).exists()


def test_unlink_removes_only_the_targeted_role(owner_client, operation, service):
    _link(owner_client, operation, service, role="publisher")
    _link(owner_client, operation, service, role="subscriber")

    response = owner_client.delete(
        f"/api/operations/{operation.id}/services/{service.id}/?role=publisher",
    )

    assert response.status_code == 204
    assert not ServiceOperationUsage.objects.filter(
        operation=operation,
        service=service,
        role="publisher",
    ).exists()
    assert ServiceOperationUsage.objects.filter(
        operation=operation,
        service=service,
        role="subscriber",
    ).exists()


def test_unlink_unknown_role_returns_404(owner_client, operation, service):
    _link(owner_client, operation, service, role="publisher")

    response = owner_client.delete(
        f"/api/operations/{operation.id}/services/{service.id}/?role=subscriber",
    )

    assert response.status_code == 404
    assert ServiceOperationUsage.objects.filter(
        operation=operation,
        service=service,
        role="publisher",
    ).exists()


def test_unauthenticated_request_is_rejected(dmr_client, operation, service):
    response = _link(dmr_client, operation, service)

    assert response.status_code in (401, 403)


def test_linking_requires_membership_in_the_services_owner_group(
    member_client, operation, service
):
    """A plain authenticated user who is not a member of `service`'s owner
    Group cannot link it to someone else's Operation (prerelease security
    audit finding: `.create` used to be unrestricted-if-authenticated,
    letting any user link any Service to any Operation)."""
    response = _link(member_client, operation, service)

    assert response.status_code == 403
    assert not ServiceOperationUsage.objects.filter(
        operation=operation, service=service
    ).exists()


def test_unlinking_requires_membership_in_the_services_owner_group(
    member_client, operation, service
):
    _seed_link(operation, service, role="publisher")

    response = member_client.delete(
        f"/api/operations/{operation.id}/services/{service.id}/?role=publisher",
    )

    assert response.status_code == 403
    assert ServiceOperationUsage.objects.filter(
        operation=operation, service=service, role="publisher"
    ).exists()


# --- Linked Services list: search/filter/sort/pagination --


@pytest.fixture
def other_team(group):
    return create_group(name="payments-team")


@pytest.fixture
def other_service(other_team, system):
    return create_component(name="analytics-service", owner=other_team, system=system)


def _list(client, operation, **params):
    return client.get(f"/api/operations/{operation.id}/services/", params)


def test_list_search_matches_service_name_or_title(
    member_client, operation, service, other_service
):
    _seed_link(operation, service, role="subscriber")
    _seed_link(operation, other_service, role="subscriber")

    response = _list(member_client, operation, search="reporting")

    body = response.json()
    assert body["page"]["objectList"][0]["service"]["id"] == str(service.id)
    assert len(body["page"]["objectList"]) == 1


def test_list_filters_by_team(
    member_client, operation, service, other_service, other_team
):
    _seed_link(operation, service, role="subscriber")
    _seed_link(operation, other_service, role="subscriber")

    response = _list(member_client, operation, team_id=str(other_team.id))

    ids = {item["service"]["id"] for item in response.json()["page"]["objectList"]}
    assert ids == {str(other_service.id)}


def test_list_filters_by_role(member_client, operation, service, other_service):
    _seed_link(operation, service, role="publisher")
    _seed_link(operation, other_service, role="subscriber")

    response = _list(member_client, operation, role="publisher")

    ids = {item["service"]["id"] for item in response.json()["page"]["objectList"]}
    assert ids == {str(service.id)}


def test_list_default_sort_is_service_display_name_ascending(
    member_client, operation, service, other_service
):
    _seed_link(operation, service, role="subscriber")
    _seed_link(operation, other_service, role="subscriber")

    response = _list(member_client, operation)

    names = [item["service"]["name"] for item in response.json()["page"]["objectList"]]
    assert names == sorted(names)


def test_list_sort_desc_reverses_order(
    member_client, operation, service, other_service
):
    _seed_link(operation, service, role="subscriber")
    _seed_link(operation, other_service, role="subscriber")

    response = _list(member_client, operation, order="desc")

    names = [item["service"]["name"] for item in response.json()["page"]["objectList"]]
    assert names == sorted(names, reverse=True)


def test_list_is_paginated(member_client, operation, service, other_service):
    _seed_link(operation, service, role="subscriber")
    _seed_link(operation, other_service, role="subscriber")

    response = _list(member_client, operation, page=1, page_size=1)

    body = response.json()
    assert body["count"] == 2
    assert body["numPages"] == 2
    assert len(body["page"]["objectList"]) == 1


# --- Channel-scoped consumers aggregation ----------------


@pytest.fixture
def other_api(group, system):
    return create_api(name="billing-api", owner=group, system=system, type="asyncapi")


def test_consumers_aggregates_across_operations_sharing_the_channel_on_a_different_api(
    member_client,
    operation,
    other_api,
    service,
):
    other_operation = ApiOperation.objects.create(
        api=other_api,
        channel_address=operation.channel_address,
        direction=ApiOperation.DIRECTION_RECEIVE,
        operation_key="onBookingCreatedReceive",
    )
    _seed_link(other_operation, service, role="subscriber")

    response = member_client.get(f"/api/operations/{operation.id}/consumers/")

    assert response.status_code == 200
    body = response.json()
    assert body["operation"]["id"] == str(operation.id)
    assert body["operation"]["channelAddress"] == operation.channel_address
    ids = {
        (participant["service"]["id"], participant["role"])
        for participant in body["participants"]
    }
    assert (str(service.id), "subscriber") in ids


def test_consumers_includes_each_operations_document_owner_implied_role(
    member_client,
    operation,
    other_api,
    group,
    system,
):
    provider = create_component(
        name="booking-service",
        owner=group,
        system=system,
        provides_apis=[operation.api],
    )
    other_provider = create_component(
        name="billing-service",
        owner=group,
        system=system,
        provides_apis=[other_api],
    )
    ApiOperation.objects.create(
        api=other_api,
        channel_address=operation.channel_address,
        direction=ApiOperation.DIRECTION_RECEIVE,
        operation_key="onBookingCreatedReceive",
    )

    response = member_client.get(f"/api/operations/{operation.id}/consumers/")

    body = response.json()
    participants = {(p["service"]["id"], p["role"]) for p in body["participants"]}
    assert (str(provider.id), "publisher") in participants
    assert (str(other_provider.id), "subscriber") in participants


def test_consumers_does_not_aggregate_operations_on_an_unrelated_channel(
    member_client,
    operation,
    api,
    service,
):
    unrelated = ApiOperation.objects.create(
        api=api,
        channel_address="payment.settled",
        direction=ApiOperation.DIRECTION_RECEIVE,
        operation_key="onPaymentSettled",
    )
    _seed_link(unrelated, service, role="subscriber")

    response = member_client.get(f"/api/operations/{operation.id}/consumers/")

    ids = {
        participant["service"]["id"] for participant in response.json()["participants"]
    }
    assert str(service.id) not in ids


def test_consumers_reflects_a_removed_operations_status(member_client, operation):
    operation.status = ApiOperation.STATUS_REMOVED
    operation.save(update_fields=["status"])

    response = member_client.get(f"/api/operations/{operation.id}/consumers/")

    assert response.json()["operation"]["status"] == "removed"
