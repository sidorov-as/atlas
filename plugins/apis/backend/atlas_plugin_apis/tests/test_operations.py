"""Tests for the read-only Operation documentation API
and the
Django admin soft-delete flow.
"""

import pytest
from atlas_plugin_api import remove_entity
from django.contrib import admin
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from server.apps.catalog.tests.factories import (
    create_api,
    create_component,
    create_purge_grant,
    create_system,
)

from atlas_plugin_apis.admin import ApiOperationAdmin
from atlas_plugin_apis.models import ApiOperation, ServiceOperationUsage

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


@pytest.fixture
def operation(api):
    return ApiOperation.objects.create(
        api=api,
        channel_address="booking.created",
        channel_protocol="kafka",
        direction=ApiOperation.DIRECTION_SEND,
        operation_key="onBookingCreated",
        operation_id="onBookingCreated",
        summary="A booking was created",
    )


# --- List -------------------------------------------------


def test_list_defaults_to_active_operations(member_client, api, operation):
    removed = ApiOperation.objects.create(
        api=api,
        channel_address="booking.cancelled",
        direction=ApiOperation.DIRECTION_RECEIVE,
        operation_key="onBookingCancelled",
        status=ApiOperation.STATUS_REMOVED,
    )

    response = member_client.get(f"/api/apis/{api.id}/operations/")

    assert response.status_code == 200
    ids = {item["id"] for item in response.json()}
    assert str(operation.id) in ids
    assert str(removed.id) not in ids


def test_list_can_surface_removed_operations_via_status_param(
    member_client, api, operation
):
    removed = ApiOperation.objects.create(
        api=api,
        channel_address="booking.cancelled",
        direction=ApiOperation.DIRECTION_RECEIVE,
        operation_key="onBookingCancelled",
        status=ApiOperation.STATUS_REMOVED,
    )

    response = member_client.get(
        f"/api/apis/{api.id}/operations/", {"status": "removed"}
    )

    ids = {item["id"] for item in response.json()}
    assert ids == {str(removed.id)}


def test_list_search_matches_channel_summary_or_operation_id(
    member_client, api, operation
):
    other = ApiOperation.objects.create(
        api=api,
        channel_address="payment.settled",
        direction=ApiOperation.DIRECTION_RECEIVE,
        operation_key="onPaymentSettled",
        summary="A payment settled",
    )

    response = member_client.get(
        f"/api/apis/{api.id}/operations/", {"search": "booking"}
    )

    ids = {item["id"] for item in response.json()}
    assert ids == {str(operation.id)}
    assert str(other.id) not in ids


def test_list_filters_by_direction_and_tag(member_client, api, operation):
    tagged = ApiOperation.objects.create(
        api=api,
        channel_address="payment.settled",
        direction=ApiOperation.DIRECTION_RECEIVE,
        operation_key="onPaymentSettled",
        tags=["billing"],
    )

    by_direction = member_client.get(
        f"/api/apis/{api.id}/operations/", {"direction": "receive"}
    )
    assert {item["id"] for item in by_direction.json()} == {str(tagged.id)}

    by_tag = member_client.get(f"/api/apis/{api.id}/operations/", {"tag": "billing"})
    assert {item["id"] for item in by_tag.json()} == {str(tagged.id)}


def test_list_is_scoped_to_its_own_api(member_client, api, other_api, operation):
    ApiOperation.objects.create(
        api=other_api,
        channel_address="booking.created",
        direction=ApiOperation.DIRECTION_SEND,
        operation_key="onBookingCreated",
    )

    response = member_client.get(f"/api/apis/{api.id}/operations/")

    assert {item["id"] for item in response.json()} == {str(operation.id)}


def test_list_requires_authentication(dmr_client, api):
    response = dmr_client.get(f"/api/apis/{api.id}/operations/")

    assert response.status_code in (401, 403)


# --- Detail -----------------------------------------------


def test_detail_returns_operation_documentation(member_client, api, operation):
    response = member_client.get(f"/api/apis/{api.id}/operations/{operation.id}/")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(operation.id)
    assert body["direction"] == "send"
    assert body["channelAddress"] == "booking.created"
    assert body["status"] == "active"
    assert body["deprecated"] is False
    assert body["provider"] is None


def test_detail_includes_the_document_owners_implied_role(
    member_client, api, operation, group, system
):
    provider = create_component(
        name="booking-service",
        owner=group,
        system=system,
        provides_apis=[api],
    )

    response = member_client.get(f"/api/apis/{api.id}/operations/{operation.id}/")

    body = response.json()
    assert body["provider"]["service"]["id"] == str(provider.id)
    assert body["provider"]["role"] == "publisher"


def test_detail_implied_role_is_subscriber_for_a_receive_operation(
    member_client, api, group, system
):
    provider = create_component(
        name="booking-service",
        owner=group,
        system=system,
        provides_apis=[api],
    )
    receiving = ApiOperation.objects.create(
        api=api,
        channel_address="payment.settled",
        direction=ApiOperation.DIRECTION_RECEIVE,
        operation_key="onPaymentSettled",
    )

    response = member_client.get(f"/api/apis/{api.id}/operations/{receiving.id}/")

    body = response.json()
    assert body["provider"]["service"]["id"] == str(provider.id)
    assert body["provider"]["role"] == "subscriber"


def test_detail_is_reachable_for_a_removed_operation(member_client, api, operation):
    operation.status = ApiOperation.STATUS_REMOVED
    operation.save(update_fields=["status"])

    response = member_client.get(f"/api/apis/{api.id}/operations/{operation.id}/")

    assert response.status_code == 200
    assert response.json()["status"] == "removed"


def test_detail_unknown_operation_returns_404(member_client, api):
    response = member_client.get(
        f"/api/apis/{api.id}/operations/00000000-0000-0000-0000-000000000000/"
    )

    assert response.status_code == 404


def test_detail_requires_authentication(dmr_client, api, operation):
    response = dmr_client.get(f"/api/apis/{api.id}/operations/{operation.id}/")

    assert response.status_code in (401, 403)


# --- Uniqueness -------------------------------------------


def test_duplicate_operation_key_within_an_api_is_rejected(api, operation):
    with pytest.raises(IntegrityError):
        ApiOperation.objects.create(
            api=api,
            channel_address="some.other.channel",
            direction=ApiOperation.DIRECTION_RECEIVE,
            operation_key=operation.operation_key,
        )


def test_same_channel_address_is_allowed_across_different_apis(
    api, other_api, operation
):
    same_channel = ApiOperation.objects.create(
        api=other_api,
        channel_address=operation.channel_address,
        direction=ApiOperation.DIRECTION_RECEIVE,
        operation_key=operation.operation_key,
    )

    assert same_channel.pk != operation.pk


# --- Direction is a normalized enum, never publish/subscribe ---


def test_direction_choices_never_include_raw_publish_subscribe_words():
    stored_values = {value for value, _label in ApiOperation.DIRECTION_CHOICES}

    assert stored_values == {
        ApiOperation.DIRECTION_SEND,
        ApiOperation.DIRECTION_RECEIVE,
    }
    assert "publish" not in stored_values
    assert "subscribe" not in stored_values


def test_direction_field_rejects_a_raw_publish_value(api):
    operation = ApiOperation(
        api=api,
        channel_address="booking.created",
        direction="publish",
        operation_key="onBookingCreated",
    )

    with pytest.raises(ValidationError):
        operation.full_clean()


def test_direction_field_rejects_a_raw_subscribe_value(api):
    operation = ApiOperation(
        api=api,
        channel_address="booking.created",
        direction="subscribe",
        operation_key="onBookingCreated",
    )

    with pytest.raises(ValidationError):
        operation.full_clean()


# --- Manual `deprecated` override ---------------------------------------------


def test_deprecated_is_settable_administratively(operation):
    operation.deprecated = True
    operation.full_clean()
    operation.save(update_fields=["deprecated"])

    operation.refresh_from_db()
    assert operation.deprecated is True


def test_deprecated_defaults_to_false(operation):
    assert operation.deprecated is False


# --- Purge of a removed Operation ---------------------------------------------


@pytest.fixture
def removed_operation(operation):
    operation.status = ApiOperation.STATUS_REMOVED
    operation.save(update_fields=["status"])
    return operation


def test_purge_is_rejected_on_an_active_operation(
    owner_client, owner_account, group, operation
):
    create_purge_grant(group=group, grantee=owner_account)

    response = owner_client.post(
        f"/api/apis/{operation.api_id}/operations/{operation.id}/purge/"
    )

    assert response.status_code == 400
    assert ApiOperation.objects.filter(pk=operation.pk).exists()


def test_purge_requires_a_purge_grant_not_just_owner_group_membership(
    owner_client, removed_operation
):
    response = owner_client.post(
        f"/api/apis/{removed_operation.api_id}/operations/{removed_operation.id}/purge/",
    )

    assert response.status_code == 403
    assert ApiOperation.objects.filter(pk=removed_operation.pk).exists()


def test_purge_grant_holder_purges_a_removed_operation_with_no_links(
    owner_client, owner_account, group, removed_operation
):
    create_purge_grant(group=group, grantee=owner_account)

    response = owner_client.post(
        f"/api/apis/{removed_operation.api_id}/operations/{removed_operation.id}/purge/",
    )

    assert response.status_code == 204
    assert not ApiOperation.objects.filter(pk=removed_operation.pk).exists()


def test_global_admin_purges_without_a_grant(
    superuser_account, dmr_client, removed_operation
):
    dmr_client.force_login(superuser_account)

    response = dmr_client.post(
        f"/api/apis/{removed_operation.api_id}/operations/{removed_operation.id}/purge/",
    )

    assert response.status_code == 204
    assert not ApiOperation.objects.filter(pk=removed_operation.pk).exists()


def test_purge_is_blocked_by_an_active_service_link(
    owner_client,
    owner_account,
    group,
    system,
    removed_operation,
):
    service = create_component(name="reporting-service", owner=group, system=system)
    ServiceOperationUsage.objects.create(
        operation=removed_operation,
        service=service,
        role=ServiceOperationUsage.ROLE_SUBSCRIBER,
    )
    create_purge_grant(group=group, grantee=owner_account)

    response = owner_client.post(
        f"/api/apis/{removed_operation.api_id}/operations/{removed_operation.id}/purge/",
    )

    assert response.status_code == 400
    assert "reporting-service" in response.json()["detail"][0]["msg"]
    assert ApiOperation.objects.filter(pk=removed_operation.pk).exists()


def test_purge_cascades_a_link_from_an_already_removed_service(
    owner_client,
    owner_account,
    group,
    system,
    removed_operation,
):
    service = create_component(name="reporting-service", owner=group, system=system)
    usage = ServiceOperationUsage.objects.create(
        operation=removed_operation,
        service=service,
        role=ServiceOperationUsage.ROLE_SUBSCRIBER,
    )
    remove_entity(service.id, owner_account)
    create_purge_grant(group=group, grantee=owner_account)

    response = owner_client.post(
        f"/api/apis/{removed_operation.api_id}/operations/{removed_operation.id}/purge/",
    )

    assert response.status_code == 204
    assert not ApiOperation.objects.filter(pk=removed_operation.pk).exists()
    assert not ServiceOperationUsage.objects.filter(pk=usage.pk).exists()


def test_purge_requires_authentication(dmr_client, removed_operation):
    response = dmr_client.post(
        f"/api/apis/{removed_operation.api_id}/operations/{removed_operation.id}/purge/",
    )

    assert response.status_code in (401, 403)


# --- Admin soft-delete ------------------------------------


@pytest.fixture
def admin_request(rf, superuser_account):
    request = rf.get("/admin/atlas_plugin_apis/apioperation/")
    request.user = superuser_account
    SessionMiddleware(lambda _request: None).process_request(request)
    request.session.save()
    request._messages = FallbackStorage(request)
    return request


def test_mark_as_removed_admin_action_sets_status_and_preserves_links(
    admin_request,
    operation,
    group,
    system,
):
    service = create_component(name="reporting-service", owner=group, system=system)
    usage = ServiceOperationUsage.objects.create(
        operation=operation,
        service=service,
        role=ServiceOperationUsage.ROLE_SUBSCRIBER,
    )

    ApiOperationAdmin(ApiOperation, admin.site).mark_as_removed(
        admin_request,
        ApiOperation.objects.filter(pk=operation.pk),
    )

    operation.refresh_from_db()
    assert operation.status == ApiOperation.STATUS_REMOVED
    assert ApiOperation.objects.filter(pk=operation.pk).exists()
    assert ServiceOperationUsage.objects.filter(pk=usage.pk).exists()


def test_mark_as_removed_admin_action_records_a_log_entry(admin_request, operation):
    from django.contrib.admin.models import LogEntry

    ApiOperationAdmin(ApiOperation, admin.site).mark_as_removed(
        admin_request,
        ApiOperation.objects.filter(pk=operation.pk),
    )

    assert LogEntry.objects.filter(object_id=str(operation.pk)).exists()


def test_admin_has_no_hard_delete_permission(admin_request):
    admin_instance = ApiOperationAdmin(ApiOperation, admin.site)

    assert admin_instance.has_delete_permission(admin_request) is False


def test_admin_delete_action_is_not_registered(admin_request):
    admin_instance = ApiOperationAdmin(ApiOperation, admin.site)

    assert "delete_selected" not in admin_instance.get_actions(admin_request)
