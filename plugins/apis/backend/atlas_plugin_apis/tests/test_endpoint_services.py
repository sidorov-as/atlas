"""Tests for the Service<->Endpoint dependency API
and its cross-plugin
auto-`consumesAPI` wiring (verify `recompute_relations` fires and
`GET /api/apis/{apiId}/relations/` reflects the new `apiConsumedBy`
immediately after an auto-created `consumesAPI`).

Also covers search/filter/sort/pagination on the Linked Services
list, the consumers-graph projection, and rejection of linking for
a `removed` Endpoint — the backend enforcement added alongside these tests,
since the UI-only hiding left the API itself unguarded).
"""

import pytest
from server.apps.catalog.tests.factories import (
    create_api,
    create_component,
    create_group,
    create_system,
)

from atlas_plugin_apis.models import ApiEndpoint, ServiceEndpointUsage

pytestmark = pytest.mark.django_db


@pytest.fixture
def system(group):
    return create_system(name="core", owner=group)


@pytest.fixture
def api(group, system):
    return create_api(name="billing-api", owner=group, system=system)


@pytest.fixture
def service(group, system):
    return create_component(name="billing-service", owner=group, system=system)


@pytest.fixture
def endpoint(api):
    return ApiEndpoint.objects.create(
        api=api,
        method=ApiEndpoint.METHOD_GET,
        path="/v1/invoices",
    )


def _link(client, endpoint, service):
    return client.post(
        f"/api/endpoints/{endpoint.id}/services/",
        {"serviceId": str(service.id)},
    )


def _seed_link(endpoint, service):
    """Create a `ServiceEndpointUsage` directly, bypassing the create API's
    authorization — for tests below that only exercise reads (list/consumers)
    and need a link owned by a team the test's client isn't a member of."""
    return ServiceEndpointUsage.objects.create(endpoint=endpoint, service=service)


def test_link_creates_usage_and_auto_creates_consumes_api(
    owner_client,
    endpoint,
    service,
    api,
):
    response = _link(owner_client, endpoint, service)

    assert response.status_code == 201
    body = response.json()
    assert body["apiRelationCreated"] is True
    assert body["service"]["id"] == str(service.id)
    assert ServiceEndpointUsage.objects.filter(
        endpoint=endpoint,
        service=service,
    ).exists()

    relations = owner_client.get(f"/api/apis/{api.id}/relations/").json()
    assert any(
        relation["predicate"] == "apiConsumedBy"
        and relation["targetId"] == str(service.id)
        for relation in relations
    )


def test_link_does_not_duplicate_consumes_api_for_a_second_endpoint(
    owner_client,
    api,
    service,
    endpoint,
):
    second_endpoint = ApiEndpoint.objects.create(
        api=api,
        method=ApiEndpoint.METHOD_POST,
        path="/v1/invoices",
    )
    _link(owner_client, endpoint, service)

    response = _link(owner_client, second_endpoint, service)

    assert response.status_code == 201
    assert response.json()["apiRelationCreated"] is False
    consumed = service.component_details.consumes_apis.filter(pk=api.id)
    assert consumed.count() == 1


def test_linking_the_same_endpoint_twice_is_rejected(
    owner_client,
    endpoint,
    service,
):
    _link(owner_client, endpoint, service)

    response = _link(owner_client, endpoint, service)

    assert response.status_code == 409
    assert (
        ServiceEndpointUsage.objects.filter(
            endpoint=endpoint,
            service=service,
        ).count()
        == 1
    )


def test_unlink_removes_the_link_but_not_consumes_api(
    owner_client,
    endpoint,
    service,
    api,
):
    _link(owner_client, endpoint, service)

    response = owner_client.delete(
        f"/api/endpoints/{endpoint.id}/services/{service.id}/",
    )

    assert response.status_code == 204
    assert not ServiceEndpointUsage.objects.filter(
        endpoint=endpoint,
        service=service,
    ).exists()
    assert service.component_details.consumes_apis.filter(pk=api.id).exists()


def test_unauthenticated_request_is_rejected(dmr_client, endpoint, service):
    response = _link(dmr_client, endpoint, service)

    assert response.status_code in (401, 403)


def test_linking_requires_membership_in_the_services_owner_group(
    member_client, endpoint, service
):
    """A plain authenticated user who is not a member of `service`'s owner
    Group cannot link it to someone else's Endpoint (prerelease security
    audit finding: `.create` used to be unrestricted-if-authenticated,
    letting any user link any Service to any Endpoint)."""
    response = _link(member_client, endpoint, service)

    assert response.status_code == 403
    assert not ServiceEndpointUsage.objects.filter(
        endpoint=endpoint,
        service=service,
    ).exists()


def test_unlinking_requires_membership_in_the_services_owner_group(
    member_client, endpoint, service
):
    _seed_link(endpoint, service)

    response = member_client.delete(
        f"/api/endpoints/{endpoint.id}/services/{service.id}/",
    )

    assert response.status_code == 403
    assert ServiceEndpointUsage.objects.filter(
        endpoint=endpoint,
        service=service,
    ).exists()


def test_linking_a_removed_endpoint_is_rejected(owner_client, endpoint, service):
    endpoint.status = ApiEndpoint.STATUS_REMOVED
    endpoint.save(update_fields=["status"])

    response = _link(owner_client, endpoint, service)

    assert response.status_code == 409
    assert not ServiceEndpointUsage.objects.filter(
        endpoint=endpoint,
        service=service,
    ).exists()


# --- Linked Services list: search/filter/sort/pagination -


@pytest.fixture
def other_team(group):
    return create_group(name="payments-team")


@pytest.fixture
def other_service(other_team, system):
    return create_component(name="payments-service", owner=other_team, system=system)


def _list(client, endpoint, **params):
    return client.get(f"/api/endpoints/{endpoint.id}/services/", params)


def test_list_search_matches_service_name_or_title(
    member_client, endpoint, service, other_service
):
    _seed_link(endpoint, service)
    _seed_link(endpoint, other_service)

    response = _list(member_client, endpoint, search="billing")

    body = response.json()
    assert body["page"]["objectList"][0]["service"]["id"] == str(service.id)
    assert len(body["page"]["objectList"]) == 1


def test_list_filters_by_team(
    member_client, endpoint, service, other_service, group, other_team
):
    _seed_link(endpoint, service)
    _seed_link(endpoint, other_service)

    response = _list(member_client, endpoint, team_id=str(other_team.id))

    ids = {item["service"]["id"] for item in response.json()["page"]["objectList"]}
    assert ids == {str(other_service.id)}


def test_list_default_sort_is_service_display_name_ascending(
    member_client, endpoint, service, other_service
):
    _seed_link(endpoint, service)
    _seed_link(endpoint, other_service)

    response = _list(member_client, endpoint)

    names = [item["service"]["name"] for item in response.json()["page"]["objectList"]]
    assert names == sorted(names)


def test_list_sort_desc_reverses_order(member_client, endpoint, service, other_service):
    _seed_link(endpoint, service)
    _seed_link(endpoint, other_service)

    response = _list(member_client, endpoint, order="desc")

    names = [item["service"]["name"] for item in response.json()["page"]["objectList"]]
    assert names == sorted(names, reverse=True)


def test_list_is_paginated(member_client, endpoint, service, other_service):
    _seed_link(endpoint, service)
    _seed_link(endpoint, other_service)

    response = _list(member_client, endpoint, page=1, page_size=1)

    body = response.json()
    assert body["count"] == 2
    assert body["numPages"] == 2
    assert len(body["page"]["objectList"]) == 1


# --- Compact consumers graph data -------------------------


def test_consumers_returns_endpoint_summary_and_linked_services(
    member_client,
    endpoint,
    service,
    other_service,
):
    _seed_link(endpoint, service)
    _seed_link(endpoint, other_service)

    response = member_client.get(f"/api/endpoints/{endpoint.id}/consumers/")

    assert response.status_code == 200
    body = response.json()
    assert body["endpoint"]["id"] == str(endpoint.id)
    assert body["endpoint"]["status"] == "active"
    ids = {item["id"] for item in body["services"]}
    assert ids == {str(service.id), str(other_service.id)}


def test_consumers_reflects_a_removed_endpoint_status(member_client, endpoint):
    endpoint.status = ApiEndpoint.STATUS_REMOVED
    endpoint.save(update_fields=["status"])

    response = member_client.get(f"/api/endpoints/{endpoint.id}/consumers/")

    assert response.json()["endpoint"]["status"] == "removed"


# --- Origin / source ---------------------------------------------------


def test_rest_link_records_manual_origin_and_ui_source(owner_client, endpoint, service):
    _link(owner_client, endpoint, service)

    usage = ServiceEndpointUsage.objects.get(endpoint=endpoint, service=service)
    assert (usage.origin, usage.source) == ("manual", "ui")


def test_unlinking_a_yaml_origin_link_is_a_conflict(owner_client, endpoint, service):
    usage = _seed_link(endpoint, service)
    usage.origin = ServiceEndpointUsage.ORIGIN_YAML
    usage.save()

    response = owner_client.delete(
        f"/api/endpoints/{endpoint.id}/services/{service.id}/"
    )

    assert response.status_code == 409
    assert "ingestion" in response.json()["detail"][0]["msg"]
    assert ServiceEndpointUsage.objects.filter(pk=usage.pk).exists()
