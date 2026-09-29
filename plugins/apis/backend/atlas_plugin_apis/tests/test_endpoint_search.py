"""Tests for the cross-API Endpoint search endpoint."""

import pytest
from server.apps.catalog.tests.factories import create_api, create_system

from atlas_plugin_apis.models import ApiEndpoint

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


def test_search_matches_endpoints_across_multiple_apis(member_client, api, other_api):
    first = ApiEndpoint.objects.create(
        api=api,
        method=ApiEndpoint.METHOD_GET,
        path="/v1/invoices",
        summary="List invoices",
    )
    second = ApiEndpoint.objects.create(
        api=other_api,
        method=ApiEndpoint.METHOD_GET,
        path="/v1/invoice-payments",
        summary="List invoice payments",
    )

    response = member_client.get("/api/apis/endpoints/search/", {"search": "invoice"})

    assert response.status_code == 200
    ids = {item["endpoint"]["id"] for item in response.json()["page"]["objectList"]}
    assert ids == {str(first.id), str(second.id)}


def test_search_matches_on_path_summary_or_operation_id(member_client, api):
    by_path = ApiEndpoint.objects.create(
        api=api, method=ApiEndpoint.METHOD_GET, path="/v1/invoices"
    )
    by_summary = ApiEndpoint.objects.create(
        api=api,
        method=ApiEndpoint.METHOD_POST,
        path="/v1/payments",
        summary="Create invoice payment",
    )
    by_operation_id = ApiEndpoint.objects.create(
        api=api,
        method=ApiEndpoint.METHOD_DELETE,
        path="/v1/orders/{id}",
        operation_id="deleteInvoiceOrder",
    )
    unrelated = ApiEndpoint.objects.create(
        api=api, method=ApiEndpoint.METHOD_GET, path="/v1/users"
    )

    response = member_client.get("/api/apis/endpoints/search/", {"search": "invoice"})

    ids = {item["endpoint"]["id"] for item in response.json()["page"]["objectList"]}
    assert ids == {str(by_path.id), str(by_summary.id), str(by_operation_id.id)}
    assert str(unrelated.id) not in ids


def test_search_excludes_removed_endpoints_by_default(member_client, api):
    active = ApiEndpoint.objects.create(
        api=api, method=ApiEndpoint.METHOD_GET, path="/v1/invoices"
    )
    removed = ApiEndpoint.objects.create(
        api=api,
        method=ApiEndpoint.METHOD_DELETE,
        path="/v1/invoices/{id}",
        status=ApiEndpoint.STATUS_REMOVED,
    )

    response = member_client.get("/api/apis/endpoints/search/", {"search": "invoice"})

    ids = {item["endpoint"]["id"] for item in response.json()["page"]["objectList"]}
    assert ids == {str(active.id)}
    assert str(removed.id) not in ids


def test_search_result_includes_owning_api_ref_name_and_title(member_client, api):
    endpoint = ApiEndpoint.objects.create(
        api=api, method=ApiEndpoint.METHOD_GET, path="/v1/invoices"
    )

    response = member_client.get("/api/apis/endpoints/search/", {"search": "invoice"})

    [result] = response.json()["page"]["objectList"]
    assert result["endpoint"]["id"] == str(endpoint.id)
    assert result["api"]["ref"] == api.ref
    assert result["api"]["name"] == api.name
    assert result["api"]["title"] == api.title


def test_search_requires_authentication(dmr_client, api):
    response = dmr_client.get("/api/apis/endpoints/search/", {"search": "invoice"})

    assert response.status_code in (401, 403)


def test_search_second_page_returns_remaining_matches_without_overlap(
    member_client, api
):
    first = ApiEndpoint.objects.create(
        api=api, method=ApiEndpoint.METHOD_GET, path="/v1/invoices-a"
    )
    second = ApiEndpoint.objects.create(
        api=api, method=ApiEndpoint.METHOD_GET, path="/v1/invoices-b"
    )

    first_page = member_client.get(
        "/api/apis/endpoints/search/", {"search": "invoice", "page": 1, "page_size": 1}
    )
    second_page = member_client.get(
        "/api/apis/endpoints/search/", {"search": "invoice", "page": 2, "page_size": 1}
    )

    first_body = first_page.json()
    second_body = second_page.json()
    assert first_body["count"] == 2
    assert first_body["numPages"] == 2
    first_ids = {item["endpoint"]["id"] for item in first_body["page"]["objectList"]}
    second_ids = {item["endpoint"]["id"] for item in second_body["page"]["objectList"]}
    assert first_ids | second_ids == {str(first.id), str(second.id)}
    assert not (first_ids & second_ids)
