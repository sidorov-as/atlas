"""Tests for the read-only Endpoint documentation API
and the Django
admin soft-delete flow.
"""

import pytest
from atlas_plugin_api import remove_entity
from django.contrib import admin
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.db import IntegrityError
from server.apps.catalog.tests.factories import (
    create_api,
    create_component,
    create_purge_grant,
    create_system,
)

from atlas_plugin_apis.admin import ApiEndpointAdmin
from atlas_plugin_apis.models import ApiEndpoint, ServiceEndpointUsage

pytestmark = pytest.mark.django_db


@pytest.fixture
def system(group):
    return create_system(name="core", owner=group)


@pytest.fixture
def api(group, system):
    return create_api(name="billing-api", owner=group, system=system)


@pytest.fixture
def other_api(group, system):
    return create_api(name="payments-api", owner=group, system=system)


@pytest.fixture
def endpoint(api):
    return ApiEndpoint.objects.create(
        api=api,
        method=ApiEndpoint.METHOD_GET,
        path="/v1/invoices",
        summary="List invoices",
        operation_id="listInvoices",
    )


# --- List ------------------------------------------------


def test_list_defaults_to_active_endpoints(member_client, api, endpoint):
    removed = ApiEndpoint.objects.create(
        api=api,
        method=ApiEndpoint.METHOD_DELETE,
        path="/v1/invoices/{id}",
        status=ApiEndpoint.STATUS_REMOVED,
    )

    response = member_client.get(f"/api/apis/{api.id}/endpoints/")

    assert response.status_code == 200
    ids = {item["id"] for item in response.json()}
    assert str(endpoint.id) in ids
    assert str(removed.id) not in ids


def test_list_can_surface_removed_endpoints_via_status_param(
    member_client, api, endpoint
):
    removed = ApiEndpoint.objects.create(
        api=api,
        method=ApiEndpoint.METHOD_DELETE,
        path="/v1/invoices/{id}",
        status=ApiEndpoint.STATUS_REMOVED,
    )

    response = member_client.get(
        f"/api/apis/{api.id}/endpoints/", {"status": "removed"}
    )

    ids = {item["id"] for item in response.json()}
    assert ids == {str(removed.id)}


def test_list_search_matches_path_summary_or_operation_id(member_client, api, endpoint):
    other = ApiEndpoint.objects.create(
        api=api,
        method=ApiEndpoint.METHOD_POST,
        path="/v1/payments",
        summary="Create payment",
    )

    response = member_client.get(
        f"/api/apis/{api.id}/endpoints/", {"search": "invoices"}
    )

    ids = {item["id"] for item in response.json()}
    assert ids == {str(endpoint.id)}
    assert str(other.id) not in ids


def test_list_filters_by_method_and_deprecated(member_client, api, endpoint):
    deprecated = ApiEndpoint.objects.create(
        api=api,
        method=ApiEndpoint.METHOD_POST,
        path="/v1/invoices",
        deprecated=True,
    )

    by_method = member_client.get(f"/api/apis/{api.id}/endpoints/", {"method": "POST"})
    assert {item["id"] for item in by_method.json()} == {str(deprecated.id)}

    by_deprecated = member_client.get(
        f"/api/apis/{api.id}/endpoints/", {"deprecated": "true"}
    )
    assert {item["id"] for item in by_deprecated.json()} == {str(deprecated.id)}


def test_list_is_scoped_to_its_own_api(member_client, api, other_api, endpoint):
    ApiEndpoint.objects.create(
        api=other_api, method=ApiEndpoint.METHOD_GET, path="/v1/invoices"
    )

    response = member_client.get(f"/api/apis/{api.id}/endpoints/")

    assert {item["id"] for item in response.json()} == {str(endpoint.id)}


def test_list_requires_authentication(dmr_client, api):
    response = dmr_client.get(f"/api/apis/{api.id}/endpoints/")

    assert response.status_code in (401, 403)


# --- Detail ----------------------------------------------


def test_detail_returns_endpoint_documentation(member_client, api, endpoint):
    response = member_client.get(f"/api/apis/{api.id}/endpoints/{endpoint.id}/")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(endpoint.id)
    assert body["method"] == "GET"
    assert body["path"] == "/v1/invoices"
    assert body["status"] == "active"


def test_detail_is_reachable_for_a_removed_endpoint(member_client, api, endpoint):
    endpoint.status = ApiEndpoint.STATUS_REMOVED
    endpoint.save(update_fields=["status"])

    response = member_client.get(f"/api/apis/{api.id}/endpoints/{endpoint.id}/")

    assert response.status_code == 200
    assert response.json()["status"] == "removed"


def test_detail_unknown_endpoint_returns_404(member_client, api):
    response = member_client.get(
        f"/api/apis/{api.id}/endpoints/00000000-0000-0000-0000-000000000000/"
    )

    assert response.status_code == 404


def test_detail_requires_authentication(dmr_client, api, endpoint):
    response = dmr_client.get(f"/api/apis/{api.id}/endpoints/{endpoint.id}/")

    assert response.status_code in (401, 403)


# --- Uniqueness ------------------------------------------


def test_duplicate_method_and_path_within_an_api_is_rejected(api, endpoint):
    with pytest.raises(IntegrityError):
        ApiEndpoint.objects.create(api=api, method=endpoint.method, path=endpoint.path)


def test_same_method_and_path_is_allowed_across_different_apis(
    api, other_api, endpoint
):
    same_shape = ApiEndpoint.objects.create(
        api=other_api, method=endpoint.method, path=endpoint.path
    )

    assert same_shape.pk != endpoint.pk


# --- Purge of a removed Endpoint ---------------------------------------------


@pytest.fixture
def removed_endpoint(endpoint):
    endpoint.status = ApiEndpoint.STATUS_REMOVED
    endpoint.save(update_fields=["status"])
    return endpoint


def test_purge_is_rejected_on_an_active_endpoint(
    owner_client, owner_account, group, endpoint
):
    create_purge_grant(group=group, grantee=owner_account)

    response = owner_client.post(
        f"/api/apis/{endpoint.api_id}/endpoints/{endpoint.id}/purge/"
    )

    assert response.status_code == 400
    assert ApiEndpoint.objects.filter(pk=endpoint.pk).exists()


def test_purge_requires_a_purge_grant_not_just_owner_group_membership(
    owner_client, removed_endpoint
):
    response = owner_client.post(
        f"/api/apis/{removed_endpoint.api_id}/endpoints/{removed_endpoint.id}/purge/",
    )

    assert response.status_code == 403
    assert ApiEndpoint.objects.filter(pk=removed_endpoint.pk).exists()


def test_purge_grant_holder_purges_a_removed_endpoint_with_no_links(
    owner_client, owner_account, group, removed_endpoint
):
    create_purge_grant(group=group, grantee=owner_account)

    response = owner_client.post(
        f"/api/apis/{removed_endpoint.api_id}/endpoints/{removed_endpoint.id}/purge/",
    )

    assert response.status_code == 204
    assert not ApiEndpoint.objects.filter(pk=removed_endpoint.pk).exists()


def test_global_admin_purges_without_a_grant(
    superuser_account, dmr_client, removed_endpoint
):
    dmr_client.force_login(superuser_account)

    response = dmr_client.post(
        f"/api/apis/{removed_endpoint.api_id}/endpoints/{removed_endpoint.id}/purge/",
    )

    assert response.status_code == 204
    assert not ApiEndpoint.objects.filter(pk=removed_endpoint.pk).exists()


def test_purge_is_blocked_by_an_active_service_link(
    owner_client,
    owner_account,
    group,
    system,
    removed_endpoint,
):
    service = create_component(name="billing-service", owner=group, system=system)
    ServiceEndpointUsage.objects.create(endpoint=removed_endpoint, service=service)
    create_purge_grant(group=group, grantee=owner_account)

    response = owner_client.post(
        f"/api/apis/{removed_endpoint.api_id}/endpoints/{removed_endpoint.id}/purge/",
    )

    assert response.status_code == 400
    assert "billing-service" in response.json()["detail"][0]["msg"]
    assert ApiEndpoint.objects.filter(pk=removed_endpoint.pk).exists()


def test_purge_cascades_a_link_from_an_already_removed_service(
    owner_client,
    owner_account,
    group,
    system,
    removed_endpoint,
):
    service = create_component(name="billing-service", owner=group, system=system)
    usage = ServiceEndpointUsage.objects.create(
        endpoint=removed_endpoint, service=service
    )
    remove_entity(service.id, owner_account)
    create_purge_grant(group=group, grantee=owner_account)

    response = owner_client.post(
        f"/api/apis/{removed_endpoint.api_id}/endpoints/{removed_endpoint.id}/purge/",
    )

    assert response.status_code == 204
    assert not ApiEndpoint.objects.filter(pk=removed_endpoint.pk).exists()
    assert not ServiceEndpointUsage.objects.filter(pk=usage.pk).exists()


def test_purge_requires_authentication(dmr_client, removed_endpoint):
    response = dmr_client.post(
        f"/api/apis/{removed_endpoint.api_id}/endpoints/{removed_endpoint.id}/purge/",
    )

    assert response.status_code in (401, 403)


# --- Admin soft-delete -----------------------------------


@pytest.fixture
def admin_request(rf, superuser_account):
    request = rf.get("/admin/apis_plugin/apiendpoint/")
    request.user = superuser_account
    SessionMiddleware(lambda _request: None).process_request(request)
    request.session.save()
    request._messages = FallbackStorage(request)
    return request


def test_mark_as_removed_admin_action_sets_status_and_preserves_links(
    admin_request,
    endpoint,
    group,
    system,
):
    service = create_component(name="billing-service", owner=group, system=system)
    usage = ServiceEndpointUsage.objects.create(endpoint=endpoint, service=service)

    ApiEndpointAdmin(ApiEndpoint, admin.site).mark_as_removed(
        admin_request,
        ApiEndpoint.objects.filter(pk=endpoint.pk),
    )

    endpoint.refresh_from_db()
    assert endpoint.status == ApiEndpoint.STATUS_REMOVED
    assert ApiEndpoint.objects.filter(pk=endpoint.pk).exists()
    assert ServiceEndpointUsage.objects.filter(pk=usage.pk).exists()


def test_admin_has_no_hard_delete_permission(admin_request):
    admin_instance = ApiEndpointAdmin(ApiEndpoint, admin.site)

    assert admin_instance.has_delete_permission(admin_request) is False


def test_admin_delete_action_is_not_registered(admin_request):
    admin_instance = ApiEndpointAdmin(ApiEndpoint, admin.site)

    assert "delete_selected" not in admin_instance.get_actions(admin_request)
