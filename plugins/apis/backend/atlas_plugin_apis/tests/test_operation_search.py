"""Tests for the cross-API Operation search endpoint.
"""

import pytest
from server.apps.catalog.tests.factories import create_api, create_system

from atlas_plugin_apis.models import ApiOperation

pytestmark = pytest.mark.django_db


@pytest.fixture
def system(group):
    return create_system(name="core", owner=group)


@pytest.fixture
def api(group, system):
    return create_api(name="booking-api", owner=group, system=system, type="asyncapi")


@pytest.fixture
def other_api(group, system):
    return create_api(name="billing-api", owner=group, system=system, type="asyncapi")


def test_search_matches_operations_across_multiple_apis(member_client, api, other_api):
    first = ApiOperation.objects.create(
        api=api,
        channel_address="booking.created",
        direction=ApiOperation.DIRECTION_SEND,
        operation_key="onBookingCreated",
        summary="A booking was created",
    )
    second = ApiOperation.objects.create(
        api=other_api,
        channel_address="booking.invoiced",
        direction=ApiOperation.DIRECTION_SEND,
        operation_key="onBookingInvoiced",
        summary="A booking was invoiced",
    )

    response = member_client.get("/api/apis/operations/search/", {"search": "booking"})

    assert response.status_code == 200
    ids = {item["operation"]["id"] for item in response.json()["page"]["objectList"]}
    assert ids == {str(first.id), str(second.id)}


def test_search_matches_on_channel_address_summary_or_operation_id(member_client, api):
    by_channel = ApiOperation.objects.create(
        api=api,
        channel_address="booking.created",
        direction=ApiOperation.DIRECTION_SEND,
        operation_key="onBookingCreated",
    )
    by_summary = ApiOperation.objects.create(
        api=api,
        channel_address="orders.updated",
        direction=ApiOperation.DIRECTION_SEND,
        operation_key="onOrderUpdated",
        summary="A booking was updated",
    )
    by_operation_id = ApiOperation.objects.create(
        api=api,
        channel_address="payments.created",
        direction=ApiOperation.DIRECTION_RECEIVE,
        operation_key="onPaymentCreated",
        operation_id="onBookingPaymentCreated",
    )
    unrelated = ApiOperation.objects.create(
        api=api,
        channel_address="users.created",
        direction=ApiOperation.DIRECTION_SEND,
        operation_key="onUserCreated",
    )

    response = member_client.get("/api/apis/operations/search/", {"search": "booking"})

    ids = {item["operation"]["id"] for item in response.json()["page"]["objectList"]}
    assert ids == {str(by_channel.id), str(by_summary.id), str(by_operation_id.id)}
    assert str(unrelated.id) not in ids


def test_search_excludes_removed_operations_by_default(member_client, api):
    active = ApiOperation.objects.create(
        api=api,
        channel_address="booking.created",
        direction=ApiOperation.DIRECTION_SEND,
        operation_key="onBookingCreated",
    )
    removed = ApiOperation.objects.create(
        api=api,
        channel_address="booking.cancelled",
        direction=ApiOperation.DIRECTION_SEND,
        operation_key="onBookingCancelled",
        status=ApiOperation.STATUS_REMOVED,
    )

    response = member_client.get("/api/apis/operations/search/", {"search": "booking"})

    ids = {item["operation"]["id"] for item in response.json()["page"]["objectList"]}
    assert ids == {str(active.id)}
    assert str(removed.id) not in ids


def test_search_result_includes_owning_api_ref_name_and_title(member_client, api):
    operation = ApiOperation.objects.create(
        api=api,
        channel_address="booking.created",
        direction=ApiOperation.DIRECTION_SEND,
        operation_key="onBookingCreated",
    )

    response = member_client.get("/api/apis/operations/search/", {"search": "booking"})

    [result] = response.json()["page"]["objectList"]
    assert result["operation"]["id"] == str(operation.id)
    assert result["api"]["ref"] == api.ref
    assert result["api"]["name"] == api.name
    assert result["api"]["title"] == api.title


def test_search_requires_authentication(dmr_client, api):
    response = dmr_client.get("/api/apis/operations/search/", {"search": "booking"})

    assert response.status_code in (401, 403)


def test_search_second_page_returns_remaining_matches_without_overlap(
    member_client, api
):
    first = ApiOperation.objects.create(
        api=api,
        channel_address="booking.created",
        direction=ApiOperation.DIRECTION_SEND,
        operation_key="onBookingCreated",
    )
    second = ApiOperation.objects.create(
        api=api,
        channel_address="booking.invoiced",
        direction=ApiOperation.DIRECTION_SEND,
        operation_key="onBookingInvoiced",
    )

    first_page = member_client.get(
        "/api/apis/operations/search/", {"search": "booking", "page": 1, "page_size": 1}
    )
    second_page = member_client.get(
        "/api/apis/operations/search/", {"search": "booking", "page": 2, "page_size": 1}
    )

    first_body = first_page.json()
    second_body = second_page.json()
    assert first_body["count"] == 2
    assert first_body["numPages"] == 2
    first_ids = {item["operation"]["id"] for item in first_body["page"]["objectList"]}
    second_ids = {item["operation"]["id"] for item in second_body["page"]["objectList"]}
    assert first_ids | second_ids == {str(first.id), str(second.id)}
    assert not (first_ids & second_ids)
